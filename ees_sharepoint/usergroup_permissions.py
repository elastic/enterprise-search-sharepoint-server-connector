#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#
"""usergroup_permissions module allows to manage user permissions.

It can be used to fetch user permissions from Sharepoint Server
or clean permissions in Elastic Enterprise Search"""

SITES = "sites"
LISTS = "lists"
LIST_ITEMS = "list_items"
DRIVE_ITEMS = "drive_items"


class Permissions:
    """This class encapsulates all module logic."""
    def __init__(self, sharepoint_client, workplace_search_custom_client, logger):
        self.sharepoint_client = sharepoint_client
        self.workplace_search_custom_client = workplace_search_custom_client
        self.logger = logger

    def fetch_users(self, key, rel_url, list_id="", item_id=""):
        """ Invokes GET calls to fetch unique permissions assigned to an object
            :param key: object key
            :param rel_url: relative url to the sharepoint farm
            :param list_id: list guid
            :param item_id: item id
            Returns:
                Response of the GET call
        """
        self.logger.info("Fetching the user roles for key: %s" % (key))
        maps = {
            SITES: "_api/web/roleassignments?$expand=Member/users,RoleDefinitionBindings",
            LISTS: f"_api/web/lists(guid\'{list_id}\')/roleassignments?$expand=Member/users,RoleDefinitionBindings",
            LIST_ITEMS: f"_api/web/lists(guid\'{list_id}\')/items({item_id})/roleassignments?$expand=Member/users,RoleDefinitionBindings",
            DRIVE_ITEMS: f"_api/web/lists(guid\'{list_id}\')/items({item_id})/roleassignments?$expand=Member/users,RoleDefinitionBindings"
        }
        if not rel_url.endswith("/"):
            rel_url = rel_url + "/"
        return self.sharepoint_client.get(rel_url, maps[key], "permission_users")

    def remove_all_permissions(self):
        """ Removes all the permissions present in the workplace"""
        try:
            user_permission = self.workplace_search_custom_client.list_permissions()

            if user_permission:
                self.logger.info("Removing the permissions from the workplace...")
                permission_list = user_permission['results']
                for permission in permission_list:
                    self.workplace_search_custom_client.remove_permissions(permission)
        except Exception as exception:
            self.logger.exception("Error while removing the permissions from the workplace. Error: %s" % exception)

    def fetch_groups(self, rel_url, userid):
        """ Invokes GET calls to fetch the group roles for a user
            :param rel_url: relative url to the sharepoint farm
            :param userid: user id for fetching the roles
        """
        self.logger.info("Fetching the group roles for userid: %s" % (userid))
        return self.sharepoint_client.get(
            rel_url, f"_api/web/GetUserById({userid})/groups", "permission_groups")
