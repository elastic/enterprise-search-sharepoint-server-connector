from sharepoint_client import sp_get
class permissions():

    def check_permission(self,object,root_url, Title,id):

        if object=='site':
            unique = sp_get(root_url,'web/HasUniqueRoleAssignments',query='?select=Title')
        elif object=='list':
            unique = sp_get(root_url,'web/lists/getbytitle({Title})/HasUniqueRoleAssignments',query='?select=Title')
        elif object=='listitem':
            unique = sp_get(root_url,'web/lists/getbytitle({Title})/items({id})/HasUniqueRoleAssignments',query='?select=Title')

    def fetch_users(self,root_url,Title,id):
        if object == 'site':
           return sp_get(root_url,'web/roleassignments?$expand=Member/users,RoleDefinitionBindings')
        elif object == 'list':
          return sp_get(root_url,'web/lists/getbytitle({Title})/roleassignments?$expand=Member/users,RoleDefinitionBindings')
        else:
           return sp_get(root_url,'web/lists/getbytitle({Title})/items({id})/roleassignments?$expand=Member/users,RoleDefinitionBindings') 

    def fetch_groups(self,root_url,Title,id):
        if object == 'site':
           return sp_get(root_url,'web/sitegroups')
        elif object == 'list':
          return sp_get(root_url,'web/lists/getbytitle({Title})/groups')
        else:
           return sp_get(root_url,'web/lists/getbytitle({Title})/items({id})/roleassignments?$expand=Member/users,RoleDefinitionBindings') 
    # def get_members(self,grp_list):
    #     for grp in grp_list:
    #        /_api/web/site groups/getbyname('Group Name')/users
    #       http://localhost:3002/api/ws/v1/sources/[CONTENT_SOURCE_ID]/permissions/[USER_NAME]/add \
    #       -H "Authorization: Bearer [ACCESS_TOKEN]" \
    # -H "Content-Type: application/json" \
    # -d '{
    #   "permissions": ["permission2"]

