import time
import requests
from sharepoint_utils import print_and_log
from urllib.parse import urljoin
from elastic_enterprise_search import WorkplaceSearch
from checkpointing import Checkpoint
from sharepoint_client import SharePoint
from configuration import Configuration
import logger_manager as log
from usergroup_permissions import Permissions
from datetime import datetime
import os
import json
from sharepoint_utils import extract
import re
IDS_PATH = os.path.join(os.path.dirname(__file__), 'doc_id.json')

logger = log.setup_logging("sharepoint_connector_index")
SITE = "site"
LIST = "list"
ITEM = "item"
SITES = "sites"
LISTS = "lists"
ITEMS = "items"


def check_response(response, error_message, exception_message, param_name):
    """Checks the response received from sharepoint server
        Returns:
            response_data: response received from invoking
    """
    if not response:
        logger.error(error_message)
        return None if param_name == SITES else []
    try:
        response_data = response.json()
        response_data = response_data.get("d", {}).get("results")
        return response_data
    except ValueError as exception:
        logger.exception("%s Error: %s" % (exception_message, exception))
        return None if param_name == SITES else []


class FetchIndex:

    def __init__(self, data, start_time, end_time):
        logger.info("Initializing the Indexing class")
        self.is_error = False
        self.ws_host = data.get("enterprise_search.host_url")
        self.ws_token = data.get("workplace_search.access_token")
        self.ws_source = data.get("workplace_search.source_id")
        self.sharepoint_host = data.get("sharepoint.host_url")
        self.objects = data.get("objects")
        self.site_collections = data.get("sharepoint.site_collections")
        self.enable_permission = data.get("enable_document_permission")
        self.start_time = start_time
        self.end_time = end_time
        self.checkpoint = Checkpoint(logger, data)
        self.sharepoint_client = SharePoint(logger)
        self.permissions = Permissions(logger, self.sharepoint_client)
        self.ws_client = WorkplaceSearch(self.ws_host, http_auth=self.ws_token)

    def index_sites(self, collection, ids, index):
        """This method fetches sites from a collection and invokes the
            index permission method to get the document level permissions.
            If the fetching is not successful, it logs proper message.
            Returns:
                document: response of sharepoint GET call, with fields specified in the schema
        """
        rel_url = urljoin(
            self.sharepoint_host, f"/sites/{collection}/_api/web/webs"
        )
        logger.info("Fetching the sites detail from url: %s" % (rel_url))
        query = self.sharepoint_client.get_query(self.start_time, self.end_time, SITES)
        response = self.sharepoint_client.get(rel_url, query)

        response_data = check_response(
            response,
            "Could not fetch the sites, url: %s" % (rel_url),
            "Error while parsing the get sites response from url: %s."
            % (rel_url),
            SITES,
        )
        if not response_data:
            logger.info("No sites were created for this interval")
            return []
        logger.info(
            "Successfuly fetched and parsed the sites response from SharePoint"
        )
        logger.info("Indexing the sites to the Workplace")
        schema = {'created_at': 'Created', 'id': 'Id', 'last_updated': 'LastItemModifiedDate',
                  'relative_url': 'ServerRelativeUrl', 'title': 'Title', 'url': 'Url'}
        document = []

        if index:
            for num in range(len(response_data)):
                doc = {'type': SITE}
                for field, response_field in schema.items():
                    doc[field] = response_data[num].get(response_field, None)
                # need to convert date to iso else workplace search throws error on date format Invalid field value: Value '2021-09-29T08:13:00' cannot be parsed as a date (RFC 3339)"]}
                doc['created_at'] += 'Z'
                if self.enable_permission is True:
                    doc["_allow_permissions"] = self.index_permissions(
                        key=SITES, collection=collection, site=doc['relative_url'])
                document.append(doc)
                ids["sites"].update({doc["id"]: doc["relative_url"]})

            try:
                response = self.ws_client.index_documents(
                    http_auth=self.ws_token,
                    content_source_id=self.ws_source,
                    documents=document
                )

                logger.info("Successfully indexed the sites to the workplace")
            except Exception as exception:
                logger.exception(
                    "Error while indexing the sites to the workplace. Error: %s"
                    % (exception)
                )
                self.is_error = True
        return response_data

    def get_site_paths(self, collection, ids, response_data=None):
        """Extracts the server relative paths of all the sites present in a
            collection.
            Returns:
                sites: list of site paths
        """
        logger.info("Extracting sites name")
        if not response_data:
            logger.info(
                "Site response is not present. Fetching the list for sites"
            )
            response_data = self.index_sites(
                collection, ids, index=False) or []

        sites = []
        for result in response_data:
            sites.append(result.get("ServerRelativeUrl"))
        return sites

    def index_lists(self, sites, collection, ids, index):
        """This method fetches lists from all sites in a collection and invokes the
            index permission method to get the document level permissions.
            If the fetching is not successful, it logs proper message.
            Returns:
                document: response of sharepoint GET call, with fields specified in the schema
        """
        logger.info("Fetching lists for all the sites")
        responses = []
        document = []
        if not sites:
            logger.info("No list was created in this interval")
            return []
        for site in sites:
            rel_url = urljoin(self.sharepoint_host, f"{site}/_api/web/lists")
            logger.info(
                "Fetching the lists for site: %s from url: %s"
                % (site, rel_url)
            )

            query = self.sharepoint_client.get_query(self.start_time, self.end_time, LISTS)
            response = self.sharepoint_client.get(
                rel_url, query + " and BaseType ne 1 and Hidden eq false and ContentTypesEnabled eq false")

            response_data = check_response(
                response,
                "Could not fetch the list for site: %s" % (site),
                "Error while parsing the get list response for site: %s from url: %s."
                % (site, rel_url),
                LISTS,
            )
            if not response_data:
                logger.info("No list was created in this interval")
                return []
            logger.info(
                "Successfuly fetched and parsed the list response for site: %s from SharePoint"
                % (site)
            )

            base_list_url = urljoin(self.sharepoint_host, f"{site}/Lists/")
            schema_list = {'created_at': 'Created', 'id': 'Id',
                           'relative_url': 'ParentWebUrl', 'title': 'Title'}

            if index:
                ids["lists"].update({site: {}})
                for num in range(len(response_data)):
                    doc = {'type': LIST}
                    for field, response_field in schema_list.items():
                        doc[field] = response_data[num].get(
                            response_field, None)
                    if self.enable_permission is True:
                        doc["_allow_permissions"] = self.index_permissions(
                            key=LISTS, collection=collection, site=site, list_name=doc['title'], list_url=doc['relative_url'], itemid=None)
                    doc["url"] = urljoin(base_list_url, re.sub(r'[^ \w+]', '', doc["title"]))
                    document.append(doc)
                    ids["lists"][site].update({doc["id"]: doc["title"]})
                logger.info(
                    "Indexing the list for site: %s to the Workplace" % (site)
                )
                try:
                    response = self.ws_client.index_documents(
                        http_auth=self.ws_token,
                        content_source_id=self.ws_source,
                        documents=document
                    )
                    logger.info(
                        "Successfully indexed the list for site: %s to the workplace"
                        % (site)
                    )
                except Exception as exception:
                    logger.exception(
                        "Error while indexing the list for site: %s to the workplace. Error: %s"
                        % (site, exception)
                    )
                    self.is_error = True
                    return []
            responses.append(response_data)
        return responses

    def get_lists_paths(self, collection, ids, sites, response_data=None):
        """Extracts the server relative paths and name of all the lists present in the
            sites of a collection
            Returns:
                lists: list of dictionaries, each dictionary is a key-value pair of
                list path and list name
        """
        if not sites:
            sites = self.get_site_paths(collection, ids)
        logger.info('Extracting list name')
        lists = {}
        if not response_data:
            logger.info(
                "List response is not present. Fetching the list for sites"
            )
            response_data = (
                self.index_lists(sites, collection, ids, index=False) or []
            )

        lists = {}
        for response in response_data:
            for result in response:
                lists[result.get("Id")] = [result.get(
                    "ParentWebUrl"), result.get("Title")]
        return lists

    def index_items(self, lists, collection, ids, index):
        """This method fetches items from all the lists in a collection and
            invokes theindex permission method to get the document level permissions.
            If the fetching is not successful, it logs proper message.
            Returns:
                document: response of sharepoint GET call, with fields specified in the schema
        """
        responses = []
        #  here value is a list of url and title
        logger.info("Fetching all the items for the lists")
        if not lists:
            logger.info("No item was created in this interval")
            return []
        for value in lists.values():
            ids["list_items"].update({value[0]: {}})
        for list_content, value in lists.items():
            rel_url = urljoin(
                self.sharepoint_host,
                f"{value[0]}/_api/web/lists/getbytitle('{value[1]}')/items",
            )
            logger.info(
                "Fetching the items for list: %s from url: %s"
                % (value[1], rel_url)
            )

            query = self.sharepoint_client.get_query(self.start_time, self.end_time, ITEMS)
            response = self.sharepoint_client.get(rel_url, query)

            response_data = check_response(
                response,
                "Could not fetch the items for list: %s" % (value[1]),
                "Error while parsing the get items response for list: %s from url: %s."
                % (value[1], rel_url),
                ITEMS,
            )
            if not response_data:
                logger.info("No item was created in this interval")
                return []
            logger.info(
                "Successfuly fetched and parsed the listitem response for list: %s from SharePoint"
                % (value[1])
            )

            list_name = re.sub(r'[^ \w+]', '', value[1])
            base_item_url = urljoin(self.sharepoint_host, f"{value[0]}/Lists/{list_name}/DispForm.aspx?ID=")
            schema_item = {'title': 'Title', 'id': 'GUID', 'created_at': 'Created', 'author_id': 'AuthorId'}
            document = []

            if index:

                ids["list_items"][value[0]].update({value[1]: []})
                rel_url = urljoin(
                    self.sharepoint_host, f'{value[0]}/_api/web/lists/getbytitle(\'{value[1]}\')/items?$select=Attachments,AttachmentFiles,Title&$expand=AttachmentFiles')

                file_response = self.sharepoint_client.get(rel_url, query='?')
                file_response_data = check_response(file_response, "Cannot fetch the file at url %s" % (
                    rel_url), "Error while parsing file response for file at url %s." % (rel_url), "attachment")

                for num in range(len(response_data)):
                    doc = {'type': ITEM}
                    if response_data[num].get('Attachments'):
                        file_relative_url = file_response_data[num][
                            'AttachmentFiles']['results'][0]['ServerRelativeUrl']
                        url_s = f"{value[0]}/_api/web/GetFileByServerRelativeUrl(\'{file_relative_url}\')/$value"
                        response = self.sharepoint_client.get(
                            urljoin(self.sharepoint_host, url_s), query='?')
                        if response.status_code == requests.codes.ok:
                            doc['body'] = extract(response.content)
                    for field, response_field in schema_item.items():
                        doc[field] = response_data[num].get(
                            response_field, None)
                    if self.enable_permission is True:
                        doc["_allow_permissions"] = self.index_permissions(
                            key=ITEMS, collection=collection, list_name=value[1], list_url=value[0], itemid=doc['id'])
                    doc["url"] = base_item_url + str(response_data[num]["Id"])
                    document.append(doc)
                    ids["list_items"][value[0]][value[1]].append(
                        response_data[num].get("GUID"))
                logger.info(
                    "Indexing the listitem for list: %s to the Workplace"
                    % (value[1])
                )
                try:
                    response = self.ws_client.index_documents(
                        http_auth=self.ws_token,
                        content_source_id=self.ws_source,
                        documents=document
                    )
                    logger.info(
                        "Successfully indexed the listitem for list: %s to the workplace"
                        % (value[1])
                    )
                except Exception as exception:
                    logger.exception(
                        "Error while indexing the listitem for list: %s to the workplace. Error: %s"
                        % (value[1], exception)
                    )
                    self.is_error = True
                    return []
            responses.append(document)
        return responses

    def index_permissions(
        self,
        key,
        collection,
        site=None,
        list_name=None,
        list_url=None,
        itemid=None,
    ):
        """This method when invoked, checks the permission inheritance of each object.
            If the object has unique permissions, the list of users having access to it
            is fetched using sharepoint api else the permission levels of the that object
            is taken same as the permission level of the site collection.
            Returns:
                groups: list of users having access to the given object
        """
        unique = False
        if key == SITES:
            rel_url = urljoin(self.sharepoint_host, site)
            unique = self.permissions.check_permissions(key, rel_url)
            if unique:
                roles = self.permissions.fetch_users(key, rel_url)
        elif key == LISTS:
            rel_url = urljoin(self.sharepoint_host, list_url)
            unique = self.permissions.check_permissions(
                key, rel_url, title=list_name
            )
            if unique:
                roles = self.permissions.fetch_users(
                    key, rel_url, title=list_name
                )

        elif key == ITEMS:

            rel_url = urljoin(self.sharepoint_host, list_url)
            unique = self.permissions.check_permissions(
                key, rel_url, title=list_name, id=itemid
            )
            if unique:
                roles = self.permissions.fetch_users(
                    key, rel_url, title=list_name, id=itemid
                )

        if not unique:
            host_url = urljoin(
                self.sharepoint_host, f"/sites/{collection}/_api/"
            )
            roles = self.sharepoint_client.get(
                host_url,
                "web/roleassignments?$expand=Member/users,RoleDefinitionBindings",
            )

        groups = []
        roles = check_response(roles, "Cannot fetch the roles for the given object %s at url %s" % (
            key, rel_url), "Error while parsing response for fetch_users for %s at url %s." % (key, rel_url), "roles")
        for role in roles:
            groups.append(role["Member"]["LoginName"])
            users = role["Member"].get("Users")
            if users:
                users = users.get("results")
                for user in users:
                    try:
                        self.ws_client.add_user_permissions(
                            content_source_id=self.ws_source,
                            http_auth=self.ws_token,
                            user=user["Title"],
                            body={
                                "permissions": [role["Member"]["LoginName"]]
                            },
                        )
                        logger.info(
                            "Successfully indexed the permissions for user %s to the workplace" % (
                                user["Title"]
                            )
                        )
                    except Exception as exception:
                        logger.exception(
                            "Error while indexing the permissions for user: %s to the workplace. Error: %s" % (
                                user["Title"], exception
                            )
                        )
                        self.is_error = True
                        return []
        return groups

    def indexing(self, collection, current_time):
        """This method fetches all the objects from sharepoint server and
            ingests them into the workplace search
        """
        sites = []
        lists = {}
        logger.info(
            "Starting to index all the objects configured in the object field: %s"
            % (str(self.objects))
        )
        if (os.path.exists(IDS_PATH) and os.path.getsize(IDS_PATH) > 0):
            with open(IDS_PATH) as ids_store:
                try:
                    ids = json.load(ids_store)
                except ValueError as exception:
                    self.logger.exception(
                        "Error while parsing the json file of the ids store from path: %s. Error: %s"
                        % (IDS_PATH, exception)
                    )

        else:
            ids = {"sites": {}, "lists": {}, "list_items": {}}

        for key in self.objects:
            response = None
            if key == SITES:
                response = self.index_sites(collection, ids, index=True)
                sites = self.get_site_paths(collection, ids, response)

            if key == LISTS and not self.is_error:
                if not sites:
                    sites = self.get_site_paths(
                        collection, ids, response_data=None)
                responses = self.index_lists(
                    sites, collection, ids, index=True)

                lists = self.get_lists_paths(
                    collection=collection, ids=ids, sites=sites, response_data=responses
                )
            elif self.is_error:
                self.is_error = False
                continue

            if key == ITEMS and not self.is_error:
                if not lists:
                    lists = self.get_lists_paths(collection, ids, sites)
                self.index_items(lists, collection, ids, index=True)
            elif self.is_error:
                self.is_error = False
                continue

        logger.info(
            "Successfuly fetched all the objects for site collection: %s"
            % (collection)
        )
        with open(IDS_PATH, "w") as f:
            try:
                json.dump(ids, f, indent=4)
            except ValueError as exception:
                logger.warn(
                    'Error while adding ids to json file. Error: {}'.format(exception))
        logger.info(
            "Saving the checkpoint for the site collection: %s" % (collection)
        )
        if not self.is_error:
            self.checkpoint.set_checkpoint(collection, current_time)


def start():
    """Runs the indexing logic regularly after a given interval
        or puts the connector to sleep
    """
    logger.info("Starting the indexing..")
    config = Configuration("sharepoint_connector_config.yml", logger)

    if not config.validate():
        print_and_log(
            logger,
            "error",
            "Terminating the indexing as the configuration parameters are not valid",
        )
        exit(0)

    indexing_interval = 60

    while True:
        current_time = (datetime.utcnow()).strftime("%Y-%m-%dT%H:%M:%SZ")
        data = config.reload_configs()
        for collection in data.get("sharepoint.site_collections"):
            logger.info(
                "Starting the data fetching for site collection: %s"
                % (collection)
            )
            check = Checkpoint(logger, data)
            start_time, end_time = check.get_checkpoint(collection, current_time)
            logger.info(
                "Successfully fetched the checkpoint details: start_time: %s and end_time: %s, calling the indexing"
                % (start_time, end_time)
            )

            indexer = FetchIndex(data, start_time, end_time)
            indexer.indexing(collection, current_time)
        try:
            indexing_interval = int(data.get("indexing_interval", 60))
        except ValueError as exception:
            logger.exception(
                "Error while converting the parameter indexing_interval: %s to integer. Considering the default value as 60 minutes. Error: %s"
                % (indexing_interval, exception)
            )
        # TODO: need to use schedule instead of time.sleep
        logger.info("Sleeping..")
        time.sleep(indexing_interval * 60)


if __name__ == "__main__":
    start()
