
from elastic_enterprise_search import WorkplaceSearch
import requests
import argparse
import getpass
from requests.auth import HTTPBasicAuth
parser = argparse.ArgumentParser(description='Create a custom content source.')
parser.add_argument("--host", required=True, type=str,
                    help="workplace search host url")
parser.add_argument("--name", required=True, type=str,
                    help="Name of the content source to be created")
parser.add_argument("--user", required=True, type=str,
                    help="username of the workplce search admin account ")

args = parser.parse_args()
if args.host:
    password = getpass.getpass(prompt='Password: ', stream=None)
workplace_search = WorkplaceSearch(
    f"{args.host}/api/ws/v1/sources", http_auth=(args.user, password)
)

resp = workplace_search.create_content_source(
    body={
        "name": args.name,
        "schema": {
            "title": "text",
            "body": "text",
            "url": "text",
            "created_at": "date",
            "name": "text",
            "description": "text"
        },
        "display": {
            "title_field": "title",
            "description_field": "description",
            "url_field": "url",
            "detail_fields": [
                {"field_name": 'description', "label": 'Description'},
                {"field_name": 'body', "label": 'Content'},
                {"field_name": 'created_at', "label": 'Created At'}
            ],
            "color": "#000000"
        },
        "is_searchable": True
    }
)

content_source_id = resp.get('id')
print(
    f"Created ContentSource with ID {content_source_id}. You may now begin indexing with content-source-id= {content_source_id}")
