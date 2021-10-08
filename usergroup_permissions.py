from urllib.parse import urljoin

SITES = "sites"
LISTS = "lists"
ITEMS = "items"


class Permissions:
    def __init__(self, logger, sharepoint_client):
        self.logger = logger
        self.sharepoint_client = sharepoint_client
        self.logger.info("Initilized Permissions class")

    def check_permissions(self, key, rel_url, title=None, id=None):
        self.logger.info("Checking the permissions for object: %s" % (key))
        maps = {
            SITES: "_api/web/HasUniqueRoleAssignments",
            LISTS: f"_api/web/lists/getbytitle(\'{title}\')/HasUniqueRoleAssignments",
            ITEMS: f"_api/web/lists/getbytitle(\'{title}\')/items({id})/HasUniqueRoleAssignments"
        }
        if not rel_url.endswith("/"):
            rel_url = rel_url + "/"
        unique = self.sharepoint_client.get(urljoin(rel_url, maps[key]), query="?")
        
        self.logger.info("Checked the permissions for object: %s" % (key))
        unique = unique.json()
        unique = unique['d'].get("HasUniqueRoleAssignments")
        return unique

    def fetch_users(self, key, rel_url, title=None, id=None):
        self.logger.info("Fetching the user roles for key: %s" % (key))
        maps = {
            SITES: "_api/web/roleassignments?$expand=Member/users,RoleDefinitionBindings",
            LISTS: f"_api/web/lists/getbytitle(\'{title}\')/roleassignments?$expand=Member/users,RoleDefinitionBindings",
            ITEMS: f"_api/web/lists/getbytitle(\'{title}\')/items({id})/roleassignments?$expand=Member/users,RoleDefinitionBindings"
        }
        if not rel_url.endswith("/"):
            rel_url = rel_url + "/"
        return self.sharepoint_client.get(rel_url, maps[key])

    def fetch_groups(self, rel_url, userid):
        self.logger.info("Fetching the group roles for userid: %s" % (userid))
        self.sharepoint_client.get(rel_url, f"_api/web/GetUserById({userid})/groups")
