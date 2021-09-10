import json
import time
from sharepoint_utils import print_and_log
from urllib.parse import urljoin
from elastic_enterprise_search import WorkplaceSearch
from checkpointing import Checkpoint
from sharepoint_client import SharePoint
from sharepoint_utils import extract
from configuration import Configuration
import logger_manager as log
from usergroup_permissions import Permissions
from datetime import datetime

logger = log.setup_logging('workplace_search_index')


class FetchIndex:

    def __init__(self, data, query):
        logger.info('Initializing the Indexing class')
        self.is_error = False
        self.ws_host = data.get('ws.host_url')
        self.ws_token = data.get('ws.access_token')
        self.ws_source = data.get('ws.source_id')
        self.sharepoint_host = data.get('sharepoint.host_url')
        self.objects = data.get('objects')
        self.site_collections = data.get('site_collections')
        self.query = query
        self.start_time = data.get('start_time')
        self.end_time = data.get('end_time')

        self.checkpoint = Checkpoint(logger, data)
        self.sharepoint_client = SharePoint(logger)
        self.permissions = Permissions(logger, self.sharepoint_client)
        self.ws_client = WorkplaceSearch(self.ws_host, http_auth=self.ws_token)

    def index_sites(self, collection, index):
        rel_url = urljoin(self.sharepoint_host,
                          '/sites/{}/_api/web/webs'.format(collection))
        logger.info('Fetching the sites detail from url: {}'.format(rel_url))
        response = self.sharepoint_client.get(rel_url, self.query)
        if not response:
            logger.error('Could not fetch the sites, url: {}'.format(rel_url))
            return None
        try:
            response_data = response.json()
            response_data = response_data.get('d', {}).get('results')
        except Exception as exception:
            logger.error('Error while parsing the get sites response from url: {}. Error: {}'.format(
                rel_url, exception))
            return None
        logger.info(
            'Successfuly fetched and parsed the sites response from SharePoint')
        logger.info('Indexing the sites to the Workplace')

        for index in range(len(response_data)):
            response_data[index] = dict((k.lower(), v)
                                        for k, v in response_data[index].items())
            response_data[index].pop('__metadata')
            # response_data[index]["_allow_permissions"] =

        if index:
            try:
                json_object = json.dumps(response_data, indent=4)
                self.ws_client.index_documents(
                    http_auth=self.ws_token,
                    content_source_id=self.ws_source,
                    documents=json_object
                )
                logger.info('Successfully indexed the sites to the workplace')
            except Exception as exception:
                logger.error(
                    'Error while indexing the sites to the workplace. Error: {}'.format(exception))
                self.is_error = True

        return response_data

    def get_site_paths(self, collection, response_data=None):
        logger.info('Extracting sites name')
        if not response_data:
            logger.info(
                'Site response is not present. Fetching the list for sites')
            response_data = self.index_sites(collection, index=False) or []

        sites = []
        for result in response_data:
            sites.append(result.get('serverrelativeurl'))
        return sites

    def index_lists(self, sites, index):
        logger.info('Fetching lists for all the sites')
        responses = []
        for site in sites:
            rel_url = urljoin(self.sharepoint_host,
                              '{0}/_api/web/lists'.format(site))
            logger.info(
                'Fetching the lists for site: {} from url: {}'.format(site, rel_url))

            response = self.sharepoint_client.get(rel_url, self.query)
            if not response:
                logger.error(
                    'Could not fetch the list for site: {}'.format(site))
                return []
            try:
                response_data = response.json()
                response_data = response_data.get('d', {}).get('results')
            except Exception as exception:
                logger.error('Error while parsing the get list response for site: {} from url: {}. Error: {}'.format(
                    site, rel_url, exception))
                return []
            logger.info(
                'Successfuly fetched and parsed the list response for site: {} from SharePoint'.format(site))

            for index in range(len(response_data)):
                response_data[index] = dict((k.lower(), v)
                                            for k, v in response_data[index].items())
                response_data[index].pop('__metadata')

            if index:
                json_object = json.dumps(response_data, indent=4)
                logger.info(
                    'Indexing the list for site: {} to the Workplace'.format(site))
                try:
                    self.ws_client.index_documents(
                        http_auth=self.ws_token,
                        content_source_id=self.ws_source,
                        documents=json_object
                    )
                    logger.info(
                        'Successfully indexed the list for site: {} to the workplace'.format(site))
                except Exception as exception:
                    logger.error('Error while indexing the list for site: {} to the workplace. Error: {}'.format(
                        site, exception))
                    self.is_error = True
                    return []
            responses.append(response_data)
        return responses

    def get_lists_paths(self, sites, response_data=None):
        logger.info('Extracting list name')
        lists = {}
        if not response_data:
            logger.info(
                'List response is not present. Fetching the list for sites')
            response_data = self.index_lists(sites, index=False) or []

        lists = {}
        for response in response_data:
            for result in response:
                lists[result.get('title')] = result.get('parentweburl')

        return lists

    def index_items(self, lists, index):
        responses = []
        logger.info('Fetching all the items for the lists')
        for list_content, value in lists.items():
            rel_url = urljoin(
                self.sharepoint_host, "{}/_api/web/lists/getbytitle(\'{}\')/items".format(list_content, value))

            logger.info(
                'Fetching the items for list: {} from url: {}'.format(list, rel_url))

            # Condition to check if the list does not have a file/folder
            if self.sharepoint_client.get(rel_url, "?$select=Folder Eq null") or self.sharepoint_client.get(rel_url, "?$select=File Eq null"):
                logger.info(
                    'The list: {} does not have files/folder. Attempting to fetch the file/folder content'.format(list))
                response = self.sharepoint_client.get(rel_url, self.query)
                if not response:
                    logger.error(
                        'Could not fetch the items for list: {}'.format(list_content))
                    return []
                try:
                    response_data = response.json()
                    response_data = response_data.get('d', {}).get('results')
                except Exception as exception:
                    logger.error('Error while parsing the get items response for list: {} from url: {}. Error: {}'.format(
                        list_content, rel_url, exception))
                    return []
                logger.info(
                    'Successfuly fetched and parsed the listitem response for list: {} from SharePoint'.format(list_content))

            else:
                logger.info(
                    'The list: {} contains some files/folder'.format(list_content))
                # TODO: Change the rel_url and query to fetch the file/folder contents
                response_data = self.sharepoint_client.get(rel_url, self.query)
                # TODO: need to add logic to index text
                text = extract(response_data)

            for index in range(len(response_data)):
                response_data[index] = dict((k.lower(), v)
                                            for k, v in response_data[index].items())
                response_data[index].pop('__metadata')

            if index:
                json_object = json.dumps(response_data, indent=4)
                logger.info(
                    'Indexing the listitem for list: {} to the Workplace'.format(list_content))
                try:
                    self.ws_client.index_documents(
                        http_auth=self.ws_token,
                        content_source_id=self.ws_source,
                        documents=json_object
                    )
                    logger.info(
                        'Successfully indexed the listitem for list: {} to the workplace'.format(list_content))
                except Exception as exception:
                    logger.error('Error while indexing the listitem for list: {} to the workplace. Error: {}'.format(
                        list_content, exception))
                    self.is_error = True
                    return []
            responses.append(response_data)
        return responses

    def get_items_ids(self, lists, response_data=None):
        logger.info('Extracting items ids')
        items = {}
        if not response_data:
            logger.info(
                'ListItem response is not present. Fetching the items for the list')
            response_data = self.index_items(lists, index=False) or []

        items = {}
        listitems = []
        for response in response_data:
            for result in response:
                listitems.append(result.get('id'))
            items[result.get('title')] = listitems
        return items

    def index_permissions(self, key, sites, collection, lists=None, items=None):
        unique = False
        if key == 'sites':
            for site in sites:
                rel_url = urljoin(self.sharepoint_host, site)
                unique = self.permissions.check_permissions(key, rel_url)
                if unique:
                    user_json = self.permissions.fetch_users(key, rel_url)
                    group_json = self.permissions.fetch_groups(key, rel_url)
        elif key == 'lists':
            for list_content, value in lists.items():
                rel_url = urljoin(self.sharepoint_host, list_content)
                unique = self.permissions.check_permissions(
                    key, rel_url, value)
                if unique:
                    user_json = self.permissions.fetch_users(
                        key, rel_url, value)
                    group_json = self.permissions.fetch_groups(
                        key, rel_url, value)
        elif key == 'items':
            for list_name, value in items.items():
                for itemid in value:
                    rel_url = urljoin(self.sharepoint_host, list_name)
                    unique = self.permissions.check_permissions(
                        key, rel_url, list_name, itemid)
                    if unique:
                        user_json = self.permissions.fetch_users(
                            key, rel_url, value, itemid)
                        group_json = self.permissions.fetch_groups(
                            key, rel_url, value, itemid)
        if not unique:
            host_url = urljoin(self.sharepoint_host,
                               "/sites/{0}/_api/".format(collection))
            query = "?select=LoginName"
            user_json = self.sharepoint_client.get(urljoin(
                host_url, "web/roleassignments?$expand=Member/users,RoleDefinitionBindings"), query)
            group_json = self.sharepoint_client.get(
                urljoin(host_url, "web/sitegroups"), query)
        group_json = group_json.get('d', {}).get('results')
        user_json = user_json.get('d', {}).get('results')

        for user in user_json:
            logger.info(
                'Indexing the listitem for list: {} to the Workplace'.format(list_content))
            # TODO: Index only specific groups for each user
            try:
                self.ws_client.add_user_permissions(
                    content_source_id=self.ws_source_id,
                    http_auth=self.ws_access_token,
                    user=user,
                    body={"permissions": group_json},
                )
                logger.info(
                    'Successfully indexed the permissions for user {} to the workplace'.format(user))
            except Exception as exception:
                logger.error('Error while indexing the permissions for user: {} to the workplace. Error: {}'.format(
                    user, exception))
                self.is_error = True
                return []

    def indexing(self):
        current_time = (datetime.now()).strftime('%Y-%m-%dT%H:%M:%S')
        for collection in self.site_collections:
            logger.info(
                'Starting the data fetching for site collection: {}'.format(collection))
            sites = []
            lists = {}
            logger.info('Starting to index all the objects configured in the object field: {}'.format(
                str(self.objects)))
            for key in self.objects:
                if key == "sites":
                    response = self.index_sites(collection, index=True)
                    sites = self.get_site_paths(collection, response)
                    self.index_permissions(key, sites, collection)
                if key == "lists" and not self.is_error:
                    if not sites:
                        sites = self.get_site_paths(
                            collection, response_data=None)
                    responses = self.index_lists(sites, index=True)
                    lists = self.get_lists_paths(sites, responses)
                    self.index_permissions(key, sites, collection, lists)
                elif self.is_error:
                    self.is_error = False
                    continue

                if key == "items" and not self.is_error:
                    if not lists:
                        lists = self.get_lists_paths(sites)
                    responses = self.index_items(lists, index=True)
                    items = self.get_items_ids(lists, responses)

                    self.index_permissions(key, sites, collection, None, items)
                elif self.is_error:
                    self.is_error = False
                    continue
            logger.info(
                'Successfuly fetched all the objects for site collection: {}'.format(collection))
            logger.info(
                'Saving the checkpoint for the site collection: {}'.format(collection))
            if not self.is_error:
                self.checkpoint.set_checkpoint({collection: current_time})


def start():
    logger.info('Starting the indexing..')
    config = Configuration("sharepoint_connector_config.yml", logger)
    if not config.validate():
        print_and_log(
            logger, 'error', 'Terminating the indexing as the configuration parameters are not valid')
        exit(0)

    data = config.get_all_config()
    check = Checkpoint(logger, data)
    query = check.get_checkpoint()
    logger.info(
        'Successfully fetched the checkpoint details: {}, calling the indexing'.format(query))

    index = FetchIndex(data, query)
    index.indexing()


if __name__ == "__main__":
    start()
