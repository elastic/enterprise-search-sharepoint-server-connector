
from urllib.parse import urljoin


class Permissions:
    def __init__(self, logger, sharepoint_client):
        self.logger = logger
        self.sharepoint_client = sharepoint_client
        self.logger.info('Initilized Permissions class')

    def check_permissions(self, key, rel_url, title=None, id=None):
        self.logger.info('Checking the permissions for object: {}'.format(key))
        if key == 'sites':
            unique = self.sharepoint_client.get(
                urljoin(rel_url, '/_api/web/HasUniqueRoleAssignments'), query='?select=title')
        elif key == 'lists':
            unique = self.sharepoint_client.get(
                urljoin(rel_url, '/_api/web/lists/getbytitle({0})/HasUniqueRoleAssignments'.format(title)), query='?select=title')
        elif key == 'items':
            unique = self.sharepoint_client.get(
                urljoin(rel_url, '/_api/web/lists/getbytitle({0})/items({1})/HasUniqueRoleAssignments'.format(title, id)), query='?select=title')
        self.logger.info('Checked the permissions for object: {}'.format(key))
        return unique

    def fetch_users(self, key, rel_url, title=None, id=None):
        self.logger.info('Fetching the user roles for key: {}'.format(key))
        if key == 'site':
            return self.sharepoint_client.get(urljoin(rel_url, '/_api/web/roleassignments?$expand=Member/users,RoleDefinitionBindings'), "?select=LoginName")
        elif key == 'list':
            return self.sharepoint_client.get(rel_url, '/_api/web/lists/getbytitle({0})/roleassignments?$expand=Member/users,RoleDefinitionBindings'.format(title))
        else:
            return self.sharepoint_client.get(rel_url, '/_api/web/lists/getbytitle({0})/items({1})/roleassignments?$expand=Member/users,RoleDefinitionBindings'.format(title, id))

    def fetch_groups(self, key, rel_url, title=None, id=None):
        self.logger.info('Fetching the group roles for key: {}'.format(key))
        if key == 'site':
            return self.sharepoint_client.get(rel_url, '/_api/web/sitegroups')
        elif key == 'list':
            return self.sharepoint_client.get(rel_url, '/_api/web/lists/getbytitle({0})/groups'.format(title))
        else:
            return self.sharepoint_client.get(rel_url, '/_api/web/lists/getbytitle({0})/items({1})/roleassignments?$expand=Member/users,RoleDefinitionBindings'.format(title, id))
