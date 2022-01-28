#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#
"""This module allows to remove recently deleted documents from Elastic Enterprise Search.

Documents that were deleted in Sharepoint Server instance will still be available in
Elastic Enterprise Search until a full sync happens, or until this module is used."""

import json
import os
import requests

from .base_command import BaseCommand


IDS_PATH = os.path.join(os.path.dirname(__file__), 'doc_id.json')


class DeletionSyncCommand(BaseCommand):
    """DeletionSyncCommand class allows to remove instances of specific Sharepoint Object types.

    It provides a way to remove items, lists and sites from Elastic Enterprise Search
    that were deleted in Sharepoint Server instance."""

    def __init__(self, args):
        super().__init__(args)

        config = self.config

        self.ws_source = config.get_value("workplace_search.source_id")

    def deindexing_items(self, collection, ids, key):
        """Fetches the id's of deleted items from the sharepoint server and
           invokes delete documents api for those ids to remove them from
           workplace search"""
        logger = self.logger
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
                        url = f"{site_url}/_api/web/lists(guid\'{list_id}\')/items"
                        resp = self.sharepoint_client.get(
                            url, f"?$filter= GUID eq  \'{item_id}\'", "deindex")
                        if resp:
                            response = resp.json()
                            result = response.get('d', {}).get('results')
                        if resp.status_code == requests.codes['not_found'] or result == []:
                            doc.append(item_id)
                    if doc:
                        self.workplace_search_client.delete_documents(
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
        logger = self.logger

        delete_ids_lists = ids["delete_keys"][collection].get('lists')
        logger.info("Deindexing lists...")
        if delete_ids_lists:
            delete = []
            global_ids_lists = ids["global_keys"][collection]["lists"]
            for site_url, list_details in delete_ids_lists.items():
                doc = []
                for list_id in list_details.keys():
                    url = f"{site_url}/_api/web/lists(guid\'{list_id}\')"
                    resp = self.sharepoint_client.get(url, '', "deindex")
                    if resp and resp.status_code == requests.codes['not_found']:
                        doc.append(list_id)
                self.workplace_search_client.delete_documents(
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
        logger = self.logger

        site_details = ids["delete_keys"][collection].get("sites")
        logger.info("Deindexing sites...")
        if site_details:
            doc = []
            for site_id, site_url in site_details.items():
                url = f"{site_url}/_api/web"
                resp = self.sharepoint_client.get(url, '', "deindex")
                if resp and resp.status_code == requests.codes['not_found']:
                    doc.append(site_id)
            self.workplace_search_client.delete_documents(
                content_source_id=self.ws_source,
                document_ids=doc)
            for site_id in doc:
                ids["global_keys"][collection]["sites"].pop(site_id)
        else:
            logger.info("No sites found to be deleted for collection: %s" % collection)
        return ids

    def execute(self):
        """Runs the de-indexing logic"""
        logger = self.logger
        logger.info("Running deletion sync")

        try:
            with open(IDS_PATH) as file:
                ids = json.load(file)
            for collection in self.config.get_value('sharepoint.site_collections'):
                logger.info(
                    'Starting the deindexing for site collection: %s' % collection)
                if ids["delete_keys"].get(collection):
                    ids = self.deindexing_sites(collection, ids)
                    ids = self.deindexing_lists(collection, ids)
                    ids = self.deindexing_items(collection, ids, "list_items")
                    ids = self.deindexing_items(collection, ids, "drive_items")
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
            logger.warning(
                "[Fail] File doc_id.json is not present, none of the objects are indexed. Error: %s"
                % exception
            )
