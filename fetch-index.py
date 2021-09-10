#import csv
import yaml
import requests
import json
from urllib.parse import urljoin
import os
from elastic_enterprise_search import WorkplaceSearch

from .checkpointing import checkpoint
from .sharepoint_client import sp_get
from .usergroup_permissions import permissions
from .text_extraction import text_fetch
#--------read config parameters from config.yaml and convert to json---------#

with open('sharepoint_connector.yaml', 'r') as f:
    data = yaml.load(f, Loader=yaml.SafeLoader)
# with open('Userdetails.json', 'w') as f:
#     json.dump(data, f, sort_keys=False)
# with open('Userdetails.json', 'r') as f:
#     json_data = json.load(f)

# sp config parameters
root_url = ""
objects= {'sites': [], 'lists' : [] , 'items':[]}
site_collection = {'Connector','WorkplaceSearch'}

query = checkpoint.get_checkpoint()

# ws config parameters
ws_url= data["ws.url"]
ws_source_id= ["ws.source_id"]
ws_access_token= ["ws.access_token"]
workplace_search = WorkplaceSearch(ws_url, http_auth=ws_access_token)

for collection in site_collection:
    
    host_url = urljoin(root_url,'/sites/{collection}/_api/')
    rel_url=urljoin(host_url,'web/roleassignments?$expand=Member/users,RoleDefinitionBindings')
    query='?select=LoginName'
    user_json= sp_get(rel_url,query)
    rel_url=urljoin(host_url,'web/sitegroups')
    user_group= sp_get(rel_url)

    for key in objects:
        if key=='sites':
            rel_url =urljoin(host_url,'web/webs')
            response=sp_get(rel_url,query)
            if response.status_code == requests.codes.ok:
                response_data = response.json()
                unique= permissions.check_permissions(key,rel_url)  
                if unique:
                    user_json= permissions.fetch_users(key,rel_url)
                    group_json= permissions.fetch_groups(key,rel_url)

        if key== 'lists':
            rel_url =urljoin(host_url,'web/lists')
            response=sp_get(rel_url,query)
            if response.status_code == requests.codes.ok:
                response_data = response.json()
                for key in response_data:
                    if key=="Title":
                        list=list.append(key.value())
                for ele in list:
                    unique= permissions.check_permissions(key,rel_url,ele)  
                    if unique:
                        user_json= permissions.fetch_users(key,rel_url)
                        group_json= permissions.fetch_groups(key,rel_url,ele)


        if key == 'items':
            for ele in list:
                rel_url =urljoin(host_url,'/web/lists/getbytitle({ele})/items')
                response=sp_get(rel_url,query)
                if response.status_code == requests.codes.ok:
                    response_data = response.json()
                    if sp_get(rel_url,'$select=Folder Eq null') or sp_get(rel_url,'select=File Eq null'):
                        text= text_fetch(response_data)
                with open('data.json', 'w') as fp:
                    json.dump(response_data, fp,indent=4)
                fp.close

        workplace_search.index_documents(http_auth= ws_access_token,content_source_id=ws_source_id,documents= response_data)
        for users in user_json:
            workplace_search.add_user_permissions(content_source_id=ws_source_id,http_auth=ws_access_token,user=users,
            body={
            "permissions": group_json
    }
)
checkpoint.set_checkpoint(checkpoint)
        