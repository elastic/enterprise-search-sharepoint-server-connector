#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#

import time
from elastic_enterprise_search import WorkplaceSearch
from checkpointing import Checkpoint
from sharepoint_client import SharePoint
from configuration import Configuration
import logger_manager as log
from usergroup_permissions import Permissions
import os
import csv
from fetch_index import check_response

logger = log.setup_logging("sharepoint_index_permissions")


class SyncUserPermission:
    def __init__(self, data):
        logger.info("Initializing the Permission Indexing class")
        self.data = data
        self.ws_host = data.get("enterprise_search.host_url")
        self.ws_token = data.get("workplace_search.access_token")
        self.ws_source = data.get("workplace_search.source_id")
        self.sharepoint_host = data.get("sharepoint.host_url")
        self.objects = data.get("objects")
        self.site_collections = data.get("sharepoint.site_collections")
        self.enable_permission = data.get("enable_document_permission")
        self.checkpoint = Checkpoint(logger, data)
        self.sharepoint_client = SharePoint(logger)
        self.permissions = Permissions(logger, self.sharepoint_client)
        self.ws_client = WorkplaceSearch(self.ws_host, http_auth=self.ws_token)
        self.mapping_sheet_path = data.get("sharepoint_workplace_user_mapping")

    def get_users_id(self):
        """ This method returns the dictionary of dictionaries containing users and their id
            as a key value pair for all the site-collections.
        """
        user_ids = {}
        for collection in self.site_collections:
            user_id_collection = {}
            rel_url = f"{self.sharepoint_host}sites/{collection}/_api/web/siteusers"
            response = self.sharepoint_client.get(rel_url, "?", "permission_users")
            if not response:
                logger.error("Could not fetch the SharePoint users")
                continue
            users, _ = check_response(response.json(), "Could not fetch the SharePoint users.", "Error while parsing the response from url.", "sharepoint_users")

            for user in users:
                user_id_collection[user["Title"]] = user["Id"]
            user_ids.update({collection: user_id_collection})
        return user_ids

    def get_user_groups(self, user_ids):
        """ This method returns the groups of each user in all the site-collections
            :param user_ids: user ids to fetch the groups of the specific user
        """
        user_group = {}
        for collection in self.site_collections:
            user_group_collection = {}
            rel_url = f"{self.sharepoint_host}sites/{collection}/"
            for name, id in user_ids[collection].items():
                response = self.permissions.fetch_groups(rel_url, id)
                if response:
                    groups, _ = check_response(response.json(), "Could not fetch the SharePoint user groups.", "Error while parsing the response from url.", "user_groups")
                    if groups:
                        user_group_collection[name] = [group['Title'] for group in groups]
            user_group.update({collection: user_group_collection})
        return user_group

    def workplace_add_permission(self, permissions):
        """ This method when invoked would index the permission provided in the paramater
            for the user in paramter user_name
            :param permissions: dictionary of dictionaries containing permissions of all the users in each site-collection.
        """
        for collection in self.site_collections:
            for user_name, permission_list in permissions[collection].items():
                try:
                    self.ws_client.add_user_permissions(
                        content_source_id=self.ws_source,
                        user=user_name,
                        body={
                            "permissions": permission_list
                        },
                    )
                    logger.info(
                        "Successfully indexed the permissions for user %s to the workplace" % (
                            user_name
                        )
                    )
                except Exception as exception:
                    logger.exception(
                        "Error while indexing the permissions for user: %s to the workplace. Error: %s" % (
                            user_name, exception
                        )
                    )

    def sync_permissions(self):
        """ This method when invoked, checks the permission of SharePoint users and update those user
            permissions in the Workplace Search.
        """
        rows = {}
        if (os.path.exists(self.mapping_sheet_path) and os.path.getsize(self.mapping_sheet_path) > 0):
            with open(self.mapping_sheet_path) as file:
                csvreader = csv.reader(file)
                for row in csvreader:
                    rows[row[0]] = row[1]

        users = self.get_users_id()
        user_names = {}
        user_groups = {}
        if users:
            for collection in self.site_collections:
                user_name_collection = {}
                for user, id in users[collection].items():
                    user_name_collection.update({rows.get(user, user): id})
                user_names.update({collection: user_name_collection})
            user_groups = self.get_user_groups(user_names)
            # delete all the permissions present in workplace search
            self.permissions.remove_all_permissions(data=self.data)
            if user_groups:
                # add all the updated permissions
                self.workplace_add_permission(user_groups)


def start():
    """ Runs the permission indexing logic regularly after a given interval
        or puts the connector to sleep
    """
    logger.info("Starting the permission indexing..")
    config = Configuration("sharepoint_connector_config.yml", logger)
    data = config.configurations

    while True:
        enable_permission = data.get("enable_document_permission")
        if not enable_permission:
            logger.info('Exiting as the enable permission flag is set to False')
            exit(0)
        permission_indexer = SyncUserPermission(data)
        permission_indexer.sync_permissions()

        try:
            sync_permission_interval = int(
                data.get('sync_permission_interval'))
        except Exception as exception:
            logger.warn('Error while converting the parameter sync_permission_interval: %s to integer. Considering the default value as 60 minutes. Error: %s' % (
                sync_permission_interval, exception))

        # TODO: need to use schedule instead of time.sleep
        logger.info('Sleeping..')
        time.sleep(sync_permission_interval * 60)


if __name__ == "__main__":
    start()
