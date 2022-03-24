#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#
"""This module allows to run a deletion sync against a Sharepoint Server instance.

It will attempt to remove from Enterprise Search instance the documents
that have been deleted from the third-party system."""
import csv
import os

from ees_sharepoint.base_command import BaseCommand

from .checkpointing import Checkpoint
from .sync_sharepoint import get_results
from .usergroup_permissions import Permissions


class PermissionSyncDisabledException(Exception):
    """Exception raised when permission sync is disabled, but expected to be enabled.

    Attributes:
        message -- explanation of the error
    """

    def __init__(self, message="Provided configuration was invalid"):
        super().__init__(message)
        self.message = message


class PermissionSyncCommand(BaseCommand):
    """This class contains logic to sync user permissions from Sharepoint Server.

    It can be used to run the job that will periodically sync permissions
    from Sharepoint Server to Elastic Enteprise Search."""

    def __init__(self, args):
        super().__init__(args)

        config = self.config

        self.ws_source = config.get_value("workplace_search.source_id")
        self.objects = config.get_value("objects")
        self.site_collections = config.get_value("sharepoint.site_collections")
        self.enable_permission = config.get_value("enable_document_permission")
        self.mapping_sheet_path = config.get_value("sharepoint_workplace_user_mapping")
        self.checkpoint = Checkpoint(config, self.logger)
        self.permissions = Permissions(self.sharepoint_client, self.workplace_search_client, self.logger)

    def get_users_id(self):
        """This method returns the dictionary of dictionaries containing users and their id
        as a key value pair for all the site-collections."""
        user_ids = {}
        for collection in self.site_collections:
            user_id_collection = {}
            rel_url = f"sites/{collection}/_api/web/siteusers"
            response = self.sharepoint_client.get(rel_url, "?", "permission_users")
            if not response:
                self.logger.error("Could not fetch the SharePoint users")
                continue
            users = get_results(self.logger, response.json(), "sharepoint_users")

            for user in users:
                user_id_collection[user["Title"]] = user["Id"]
            user_ids.update({collection: user_id_collection})
        return user_ids

    def get_user_groups(self, user_ids):
        """This method returns the groups of each user in all the site-collections
        :param user_ids: user ids to fetch the groups of the specific user"""
        user_group = {}
        for collection in self.site_collections:
            user_group_collection = {}
            rel_url = f"sites/{collection}/"
            for name, user_id in user_ids[collection].items():
                response = self.permissions.fetch_groups(rel_url, user_id)
                if response:
                    groups = get_results(self.logger, response.json(), "user_groups")
                    if groups:
                        user_group_collection[name] = [group["Title"] for group in groups]
            user_group.update({collection: user_group_collection})
        return user_group

    def workplace_add_permission(self, permissions):
        """This method when invoked would index the permission provided in the paramater
        for the user in paramter user_name
        :param permissions: dictionary of dictionaries containing permissions of all the users in each site-collection."""
        for collection in self.site_collections:
            for user_name, permission_list in permissions[collection].items():
                try:
                    self.workplace_search_client.add_user_permissions(
                        content_source_id=self.ws_source,
                        user=user_name,
                        body={"permissions": permission_list},
                    )
                    self.logger.info("Successfully indexed the permissions for user %s to the workplace" % (user_name))
                except Exception as exception:
                    self.logger.exception(
                        "Error while indexing the permissions for user: %s to the workplace. Error: %s"
                        % (user_name, exception)
                    )

    def sync_permissions(self):
        """This method when invoked, checks the permission of SharePoint users and update those user
        permissions in the Workplace Search."""
        rows = {}
        if os.path.exists(self.mapping_sheet_path) and os.path.getsize(self.mapping_sheet_path) > 0:
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
                for user, user_id in users[collection].items():
                    user_name_collection.update({rows.get(user, user): user_id})
                user_names.update({collection: user_name_collection})
            user_groups = self.get_user_groups(user_names)
            # delete all the permissions present in workplace search
            self.permissions.remove_all_permissions(config=self.config)
            if user_groups:
                # add all the updated permissions
                self.workplace_add_permission(user_groups)

    def execute(self):
        """Runs the permission indexing logic"""

        logger = self.logger
        config = self.config
        logger.info("Starting the permission indexing..")

        enable_permission = config.get_value("enable_document_permission")
        if not enable_permission:
            logger.warn("Exiting as the enable permission flag is set to False")
            raise PermissionSyncDisabledException
        self.sync_permissions()
