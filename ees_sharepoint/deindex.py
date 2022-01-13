#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#
"""This module allows to remove recently deleted documents from Elastic Enterprise Search.

Documents that were deleted in Sharepoint Server instance will still be available in
Elastic Enterprise Search until a full sync happens, or until this module is used."""

import time
import json
import os
import requests

from elastic_enterprise_search import WorkplaceSearch

from .sharepoint_client import SharePoint
from .configuration import Configuration
from . import logger_manager as log

logger = log.setup_logging('sharepoint_connector_deindex')
IDS_PATH = os.path.join(os.path.dirname(__file__), 'doc_id.json')


class Deindex:
    """Deindex class allows to remove instances of specific Sharepoint Object types.

    It provides methods to remove from Elastic Enterprise Search items, lists and sites
    that were deleted in Sharepoint Server instance."""
    def __init__(self, config):
        logger.info('Initializing the Indexing class')
        self.ws_host = config.get_value('enterprise_search.host_url')
        self.ws_token = config.get_value('workplace_search.access_token')
        self.ws_source = config.get_value('workplace_search.source_id')
        self.sharepoint_host = config.get_value('sharepoint.host_url')
        self.sharepoint_client = SharePoint(logger)
        self.ws_client = WorkplaceSearch(self.ws_host, http_auth=self.ws_token)

    def deindexing_items(self, collection, ids, key):
        """Fetches the id's of deleted items from the sharepoint server and
           invokes delete documents api for those ids to remove them from
           workplace search"""
        delete_ids_items = ids["delete_keys"][collection].get(key)
        logger.info("Deindexing items...")
        if delete_ids_items:
            delete_site = []
            global_ids_items = ids["global_keys"][collection][key]
            for site_url, item_details in delete_ids_items.items():
                delete_list = []
                for list_id, items in item_details.items():
                    doc = []
                    for item_id in items:
                        url = f"{self.sharepoint_host}{site_url}/_api/web/lists(guid\'{list_id}\')/items"
                        resp = self.sharepoint_client.get(
                            url, f"?$filter= GUID eq  \'{item_id}\'", "deindex")
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
                    updated_items = global_ids_items[site_url].get(list_id)
                    if updated_items is None:
                        continue
                    for updated_item_id in doc:
                        if updated_item_id in updated_items:
                            updated_items.remove(updated_item_id)
                    if updated_items == []:
                        delete_list.append(list_id)
                for list_id in delete_list:
                    global_ids_items[site_url].pop(list_id)
                if global_ids_items[site_url] == {}:
                    delete_site.append(site_url)
            for site_url in delete_site:
                global_ids_items.pop(site_url)
        else:
            logger.info("No %s found to be deleted for collection: %s" % (key, collection))
        return ids

    def deindexing_lists(self, collection, ids):
        """Fetches the id's of deleted lists from the sharepoint server and
            further removes them from workplace search by invoking the delete
            document api.
            Returns:
                sites: list of site paths
        """
        delete_ids_lists = ids["delete_keys"][collection].get('lists')
        logger.info("Deindexing lists...")
        if delete_ids_lists:
            delete = []
            global_ids_lists = ids["global_keys"][collection]["lists"]
            for site_url, list_details in delete_ids_lists.items():
                doc = []
                for list_id in list_details.keys():
                    url = f"{self.sharepoint_host}{site_url}/_api/web/lists(guid\'{list_id}\')"
                    resp = self.sharepoint_client.get(url, '', "deindex")
                    if resp and resp.status_code == requests.codes['not_found']:
                        doc.append(list_id)
                self.ws_client.delete_documents(
                    http_auth=self.ws_token,
                    content_source_id=self.ws_source,
                    document_ids=doc)
                for list_id in doc:
                    if list_id in global_ids_lists[site_url]:
                        global_ids_lists[site_url].pop(list_id)
                if global_ids_lists[site_url] == {}:
                    delete.append(site_url)
            for site_url in delete:
                global_ids_lists.pop(site_url)
        else:
            logger.info("No list found to be deleted for collection: %s" % collection)
        return ids

    def deindexing_sites(self, collection, ids):
        """Fetches the ids' of deleted sites from the sharepoint server and
            invokes delete documents api for those ids to remove them from
            workplace search
        """
        site_details = ids["delete_keys"][collection].get("sites")
        logger.info("Deindexing sites...")
        if site_details:
            doc = []
            for site_id, site_url in site_details.items():
                url = f"{self.sharepoint_host}{site_url}/_api/web"
                resp = self.sharepoint_client.get(url, '', "deindex")
                if resp and resp.status_code == requests.codes['not_found']:
                    doc.append(site_id)
            self.ws_client.delete_documents(
                http_auth=self.ws_token,
                content_source_id=self.ws_source,
                document_ids=doc)
            for site_id in doc:
                ids["global_keys"][collection]["sites"].pop(site_id)
        else:
            logger.info("No sites found to be deleted for collection: %s" % collection)
        return ids


def start():
    """Runs the de-indexing logic regularly after a given interval
        or puts the connector to sleep"""
    logger.info('Starting the de-indexing...')
    config = Configuration("sharepoint_connector_config.yml", logger)
    while True:
        deindexer = Deindex(config)
        try:
            with open(IDS_PATH) as file:
                ids = json.load(file)
            for collection in config.get('sharepoint.site_collections'):
                logger.info(
                    'Starting the deindexing for site collection: %s' % collection)
                if ids["delete_keys"].get(collection):
                    ids = deindexer.deindexing_sites(collection, ids)
                    ids = deindexer.deindexing_lists(collection, ids)
                    ids = deindexer.deindexing_items(collection, ids, "list_items")
                    ids = deindexer.deindexing_items(collection, ids, "drive_items")
                else:
                    logger.info("No objects present to be deleted for the collection: %s" % collection)
            ids["delete_keys"] = {}
            with open(IDS_PATH, "w") as file:
                try:
                    json.dump(ids, file, indent=4)
                except ValueError as exception:
                    logger.exception(
                        "Error while updating the doc_id json file. Error: %s", exception
                    )
        except FileNotFoundError as exception:
            logger.warnig(
                "[Fail] File doc_id.json is not present, none of the objects are indexed. Error: %s"
                % exception
            )
        deindexing_interval = config.get_value('deletion_interval')
        # TODO: need to use schedule instead of time.sleep
        logger.info('Sleeping..')
        time.sleep(deindexing_interval * 60)
