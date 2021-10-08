import time
from sharepoint_utils import print_and_log
from urllib.parse import urljoin
from elastic_enterprise_search import WorkplaceSearch
from checkpointing import Checkpoint
from sharepoint_client import SharePoint
from configuration import Configuration
import logger_manager as log
from usergroup_permissions import Permissions
from datetime import datetime

logger = log.setup_logging("workplace_search_index")
SITE = "site"
LIST = "list"
ITEM = "item"
SITES = "sites"
LISTS = "lists"
ITEMS = "items"


def check_response(response, error_message, exception_message, param_name):
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

    def __init__(self, data, query):
        logger.info("Initializing the Indexing class")
        self.is_error = False
        self.ws_host = data.get("enterprise_search.host_url")
        self.ws_token = data.get("workplace_search.access_token")
        self.ws_source = data.get("workplace_search.source_id")
        self.sharepoint_host = data.get("sharepoint.host_url")
        self.objects = data.get("objects")
        self.site_collections = data.get("sharepoint.site_collections")
        self.query = query
        self.start_time = data.get("start_time")
        self.end_time = data.get("end_time")
        self.checkpoint = Checkpoint(logger, data)
        self.sharepoint_client = SharePoint(logger)
        self.permissions = Permissions(logger, self.sharepoint_client)
        self.ws_client = WorkplaceSearch(self.ws_host, http_auth=self.ws_token)

    def index_sites(self, collection, index):
        rel_url = urljoin(
            self.sharepoint_host, f"/sites/{collection}/_api/web/webs"
        )
        logger.info("Fetching the sites detail from url: %s" % (rel_url))
        response = self.sharepoint_client.get(rel_url, self.query)

        response_data = check_response(
            response,
            "Could not fetch the sites, url: %s" % (rel_url),
            "Error while parsing the get sites response from url: %s."
            % (rel_url),
            SITES,
        )

        logger.info(
            "Successfuly fetched and parsed the sites response from SharePoint"
        )
        logger.info("Indexing the sites to the Workplace")
        schema = ['Created', 'Id', 'LastItemModifiedDate',
                  'ServerRelativeUrl', 'Title', 'Url']
        document = []

        if index:
            for num in range(len(response_data)):
                doc = {'type': SITE}
                for field in schema:
                    doc[field.lower()] = response_data[num].get(field, None)
                doc["_allow_permissions"] = self.index_permissions(
                    key=SITES, collection=collection, site=doc['serverrelativeurl'])
                document.append(doc)

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
        return document

    def get_site_paths(self, collection, response_data=None):
        logger.info("Extracting sites name")
        if not response_data:
            logger.info(
                "Site response is not present. Fetching the list for sites"
            )
            response_data = self.index_sites(collection, index=False) or []

        sites = []
        for result in response_data:
            sites.append(result.get("serverrelativeurl"))
        return sites

    def index_lists(self, sites, collection, index):
        logger.info("Fetching lists for all the sites")
        responses = []
        document = []
        for site in sites:
            rel_url = urljoin(self.sharepoint_host, f"{site}/_api/web/lists")
            logger.info(
                "Fetching the lists for site: %s from url: %s"
                % (site, rel_url)
            )

            response = self.sharepoint_client.get(rel_url, self.query)

            response_data = check_response(
                response,
                "Could not fetch the list for site: %s" % (site),
                "Error while parsing the get list response for site: %s from url: %s."
                % (site, rel_url),
                LISTS,
            )

            logger.info(
                "Successfuly fetched and parsed the list response for site: %s from SharePoint"
                % (site)
            )
            schema_list = ['Created', 'Id', 'ParentWebUrl', 'Title']

            if index:
                for num in range(len(response_data)):
                    doc = {'type': LIST}
                    for field in schema_list:
                        doc[field.lower()] = response_data[num].get(field, None)
                    doc["_allow_permissions"] = self.index_permissions(
                        key=LISTS, collection=collection, site=site, list_name=doc['title'], list_url=doc['parentweburl'], itemid=None)
                    document.append(doc)

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
            responses.append(document)
        return responses

    def get_lists_paths(self, collection, sites, response_data=None):
        if not sites:
            sites = self.get_site_paths(collection)
        logger.info('Extracting list name')
        lists = {}
        if not response_data:
            logger.info(
                "List response is not present. Fetching the list for sites"
            )
            response_data = (
                self.index_lists(sites, collection, index=False) or []
            )

        lists = {}
        for response in response_data:
            for result in response:
                lists[result.get("title")] = result.get("parentweburl")
        return lists

    def index_items(self, lists, collection, index):
        responses = []
        logger.info("Fetching all the items for the lists")
        for list_content, value in lists.items():
            rel_url = urljoin(
                self.sharepoint_host,
                f"{value}/_api/web/lists/getbytitle('{list_content}')/items",
            )

            logger.info(
                "Fetching the items for list: %s from url: %s"
                % (list_content, rel_url)
            )

            response = self.sharepoint_client.get(rel_url, self.query)

            response_data = check_response(
                response,
                "Could not fetch the items for list: %s" % (list_content),
                "Error while parsing the get items response for list: %s from url: %s."
                % (list_content, rel_url),
                ITEMS,
            )

            logger.info(
                "Successfuly fetched and parsed the listitem response for list: %s from SharePoint"
                % (list_content)
            )

            schema_item = ['Title', 'GUID', 'Created', 'AuthorId', 'Id']
            document = []

            if index:
                for num in range(len(response_data)):
                    doc = {'type': ITEM}
                    for field in schema_item:
                        doc[field.lower()] = response_data[num].get(field, None)
                    doc["_allow_permissions"] = self.index_permissions(
                        key=ITEMS, collection=collection, list_name=list_content, list_url=value, itemid=doc['id'])
                    document.append(doc)

                logger.info(
                    "Indexing the listitem for list: %s to the Workplace"
                    % (list_content)
                )
                try:
                    response = self.ws_client.index_documents(
                        http_auth=self.ws_token,
                        content_source_id=self.ws_source,
                        documents=document
                    )
                    logger.info(
                        "Successfully indexed the listitem for list: %s to the workplace"
                        % (list_content)
                    )
                except Exception as exception:
                    logger.exception(
                        "Error while indexing the listitem for list: %s to the workplace. Error: %s"
                        % (list_content, exception)
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
        roles = roles.json()
        groups = []

        roles = roles.get("d", {}).get("results")

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

    def indexing(self, collection):
        current_time = (datetime.now()).strftime("%Y-%m-%dT%H:%M:%S")
        sites = []
        lists = {}
        logger.info(
            "Starting to index all the objects configured in the object field: %s"
            % (str(self.objects))
        )
        for key in self.objects:
            if key == SITES:
                response = self.index_sites(collection, index=True)
                sites = self.get_site_paths(collection, response)

            if key == LISTS and not self.is_error:
                if not sites:
                    sites = self.get_site_paths(collection, response_data=None)
                responses = self.index_lists(sites, collection, index=True)

                lists = self.get_lists_paths(
                    collection=collection, sites=sites, response_data=responses
                )
            elif self.is_error:
                self.is_error = False
                continue

            if key == ITEMS and not self.is_error:
                if not lists:
                    lists = self.get_lists_paths(collection, sites)
                self.index_items(lists, collection, index=True)
            elif self.is_error:
                self.is_error = False
                continue

        logger.info(
            "Successfuly fetched all the objects for site collection: %s"
            % (collection)
        )
        logger.info(
            "Saving the checkpoint for the site collection: %s" % (collection)
        )
        if not self.is_error:
            self.checkpoint.set_checkpoint(collection, current_time)


def start():
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
        data = config.reload_configs()
        for collection in data.get("sharepoint.site_collections"):
            logger.info(
                "Starting the data fetching for site collection: %s"
                % (collection)
            )
            check = Checkpoint(logger, data)
            query = check.get_checkpoint(collection)
            logger.info(
                "Successfully fetched the checkpoint details: %s, calling the indexing"
                % (query)
            )

            indexer = FetchIndex(data, query)
            indexer.indexing(collection)
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
