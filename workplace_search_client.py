

def wsclient(client,ws_url,ws_access_token,ws_source_id,response_data):
    
    client.workplace_search.index_documents(
            http_auth= ws_access_token,
            content_source_id=ws_source_id,
            documents= response_data)

# workplace_search.add_user_permissions(
#     content_source_id="<CONTENT_SOURCE_ID>",
#     http_auth="<CONTENT_SOURCE_ACCESS_TOKEN>",
#     user="example.user",
#     body={
#         "permissions": ["permission1", "permission2"]
#     }
# )