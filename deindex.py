import time
import json
import requests
import os
from sharepoint_utils import print_and_log
from elastic_enterprise_search import WorkplaceSearch
from sharepoint_client import SharePoint
from configuration import Configuration
import logger_manager as log
from fetch_index import FetchIndex

logger = log.setup_logging('sharepoint_connector_deindex')
IDS_PATH = os.path.join(os.path.dirname(__file__), 'doc_id.json')


class Deindex:
    def __init__(self, data):
        logger.info('Initializing the Indexing class')
        self.ws_host = data.get('enterprise_search.host_url')
        self.ws_token = data.get('workplace_search.access_token')
        self.ws_source = data.get('workplace_search.source_id')
        self.sharepoint_host = data.get('sharepoint.host_url')
        self.sharepoint_client = SharePoint(logger)
        self.ws_client = WorkplaceSearch(self.ws_host, http_auth=self.ws_token)

    def deindexing_items(self, collection, ids):
        """Fetches the id's of deleted items from the sharepoint server and
           invokes delete documents api for those ids to remove them from
           workplace search
        """
        lists_item_ids = ids.get('list_items')
        logger.info("Deindexing items...")
        delete_site = []
        for site_url, item_details in lists_item_ids.items():
            doc = []
            delete_list = []
            for list_name, items in item_details.items():
                for item_id in items:
                    url = f"{self.sharepoint_host}{site_url}/_api/web/lists/getbytitle(\'{list_name}\')/items"
                    resp = self.sharepoint_client.get(
                        url, f"?$filter= GUID eq  \'{item_id}\'")
                    if resp:
                        response = resp.json()
                        result = response.get('d', {}).get('results')
                    if resp.status_code == requests.codes['not_found'] or result == []:
                        doc.append(item_id)
                if doc:
                    self.ws_client.delete_documents(
                        http_auth=self.ws_token,
                        content_source_id=self.ws_source,
                        document_ids=doc)
                for id in doc:
                    items.remove(id)
                if items == []:
                    delete_list.append(list_name)
            for list_name in delete_list:
                item_details.pop(list_name)
            if item_details == {}:
                delete_site.append(site_url)
        for site_url in delete_site:
            lists_item_ids.pop(site_url)

    def deindexing_lists(self, collection, ids):
        """Fetches the id's of deleted lists from the sharepoint server and
            further removes them from workplace search by invoking the delete
            document api.
            Returns:
                sites: list of site paths
        """
        logger.info("Deindexing lists...")
        lists_ids = ids.get('lists')
        delete = []
        for site_url, list_details in lists_ids.items():
            doc = []
            for list_id, list_name in list_details.items():
                url = f"{self.sharepoint_host}{site_url}/_api/web/lists/getbytitle(\'{list_name}\')"
                resp = self.sharepoint_client.get(url, '?')
                if resp.status_code == requests.codes['not_found']:
                    doc.append(list_id)
            self.ws_client.delete_documents(
                http_auth=self.ws_token,
                content_source_id=self.ws_source,
                document_ids=doc)
            for id in doc:
                list_details.pop(id)
            if list_details == {}:
                delete.append(site_url)
        for site_url in delete:
            lists_ids.pop(site_url)

    def deindexing_sites(self, collection, ids):
        """Fetches the ids' of deleted sites from the sharepoint server and
            invokes delete documents api for those ids to remove them from
            workplace search
        """

        logger.info("Deindexing sites...")

        site_details = ids.get("sites")
        doc = []
        for site_id, site_url in site_details.items():
            url = f"{self.sharepoint_host}{site_url}/_api/web"
            resp = self.sharepoint_client.get(url, '?')
            if resp.status_code == requests.codes['not_found']:
                doc.append(site_id)
        self.ws_client.delete_documents(
            http_auth=self.ws_token,
            content_source_id=self.ws_source,
            document_ids=doc)
        for id in doc:
            site_details.pop(id)


def start():
    """Runs the de-indexing logic regularly after a given interval
        or puts the connector to sleep
    """
    logger.info('Starting the de-indexing..')
    config = Configuration("sharepoint_connector_config.yml", logger)

    if not config.validate():
        print_and_log(
            logger, 'error', 'Terminating the de-indexing as the configuration parameters are not valid')
        exit(0)
    deindexing_interval = 60
    while True:
        data = config.reload_configs()
        for collection in data.get('sharepoint.site_collections'):
            logger.info(
                'Starting the deindexing for site collection: %s' % collection)
            deindexer = Deindex(data)
            try:
                with open(IDS_PATH) as f:
                    ids = json.load(f)
                deindexer.deindexing_sites(collection, ids)
                deindexer.deindexing_lists(collection, ids)
                deindexer.deindexing_items(collection, ids)
                with open(IDS_PATH, "w") as f:
                    try:
                        json.dump(ids, f, indent=4)
                    except ValueError as exception:
                        logger.exception(
                            "Error while updating the doc_id json file. Error: %s"
                            % exception
                        )
            except FileNotFoundError as exception:
                logger.warn(
                    "[Fail] File doc_id.json is not present, none of the objects are indexed.")
            try:
                deindexing_interval = int(
                    data.get('deletion_interval', 60))
            except Exception as exception:
                logger.warn('Error while converting the parameter deindexing_interval: %s to integer. Considering the default value as 60 minutes. Error: %s' % (
                    deindexing_interval, exception))
            # TODO: need to use schedule instead of time.sleep
            logger.info('Sleeping..')
            # time.sleep(5)
            time.sleep(deindexing_interval * 60)


if __name__ == "__main__":
    start()
