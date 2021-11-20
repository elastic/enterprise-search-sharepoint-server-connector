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
SITES = "sites"
LISTS = "lists"
ITEMS = "items"
LISTITEMS = "list_items"


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
        """ This method returns the dictionary having the users as a key and it's unique id as a value
        """
        user_ids = {}
        for collection in self.site_collections:
            rel_url = f"{self.sharepoint_host}sites/{collection}/_api/web/siteusers"
            response = self.sharepoint_client.get(rel_url, "?", "permission_users")
            users = check_response(response.json(), "Could not fetch the SharePoint users.", "Error while parsing the response from url.", "sharepoint_users")
            for user in users:
                user_ids[user["Title"]] = user["Id"]
        return user_ids

    def get_user_groups(self, user_ids):
        """ This method returns the groups of each user
            :param user_ids: user ids to fetch the groups of the specific user
        """
        user_group = {}
        for collection in self.site_collections:
            rel_url = f"{self.sharepoint_host}sites/{collection}/"
            for name, id in user_ids.items():
                response = self.permissions.fetch_groups(rel_url, id)
                groups = check_response(response.json(), "Could not fetch the SharePoint user groups.", "Error while parsing the response from url.", "user_groups")
                user_group[name] = [group['Title'] for group in groups]
        return user_group

    def workplace_add_permission(self, permissions):
        """ This method when invoked would index the permission provided in the paramater
            for the user in paramter user_name
            :param permissions: dictionary containing permissions of all the users
        """
        for user_name, permission_list in permissions.items():
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
        for user, id in users.items():
            user_names.update({rows.get(user, user): id})
        user_groups = self.get_user_groups(user_names)

        # delete all the permissions present in workplace search
        self.permissions.remove_all_permissions(data=self.data)

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
        permission_indexer = SyncUserPermission(data)
        if not enable_permission:
            logger.info('Exiting as the enable permission flag is set to False')
            exit(0)
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
