from sharepoint_utils import encode
SITES = "sites"
LISTS = "lists"
ITEMS = "items"


class Permissions:
    def __init__(self, logger, sharepoint_client):
        self.logger = logger
        self.sharepoint_client = sharepoint_client
        self.logger.info("Initilized Permissions class")

    def fetch_users(self, key, rel_url, title="", id=""):
        """ Invokes GET calls to fetch unique permissions assigned to an object
            :param key: object key
            :param rel_url: relative url to the sharepoint farm
            :param title: list title
            :param id: item id
            Returns:
                Response of the GET call
        """
        self.logger.info("Fetching the user roles for key: %s" % (key))
        maps = {
            SITES: "_api/web/roleassignments?$expand=Member/users,RoleDefinitionBindings",
            LISTS: f"_api/web/lists/getbytitle(\'{encode(title)}\')/roleassignments?$expand=Member/users,RoleDefinitionBindings",
            ITEMS: f"_api/web/lists/getbytitle(\'{encode(title)}\')/items({id})/roleassignments?$expand=Member/users,RoleDefinitionBindings"
        }
        if not rel_url.endswith("/"):
            rel_url = rel_url + "/"
        return self.sharepoint_client.get(rel_url, maps[key])

    def fetch_groups(self, rel_url, userid):
        """ Invokes GET calls to fetch the group roles for a user
            :param rel_url: relative url to the sharepoint farm
            :param userid: user id for fetching the roles
        """
        self.logger.info("Fetching the group roles for userid: %s" % (userid))
        self.sharepoint_client.get(
            rel_url, f"_api/web/GetUserById({userid})/groups")
