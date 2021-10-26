from elastic_enterprise_search import WorkplaceSearch
import argparse
import getpass
from configuration import Configuration
import logger_manager as log
logger = log.setup_logging("sharepoint_connector_bootstrap")


def main():
    config = Configuration("sharepoint_connector_config.yml", logger=logger)
    if not config.validate():
        print(
            "[Fail] Terminating the connector as the configuration parameters are not valid"
        )
        exit(0)
    data = config.reload_configs()
    parser = argparse.ArgumentParser(
        description='Create a custom content source.')
    parser.add_argument("--name", required=True, type=str,
                        help="Name of the content source to be created")
    parser.add_argument("--user", required=False, type=str,
                        help="username of the workplce search admin account ")

    host = data.get("enterprise_search.host_url")
    args = parser.parse_args()
    if args.user:
        password = getpass.getpass(prompt='Password: ', stream=None)
        workplace_search = WorkplaceSearch(
            f"{host}/api/ws/v1/sources", http_auth=(args.user, password)
        )
    else:
        workplace_search = WorkplaceSearch(
            f"{host}/api/ws/v1/sources", http_auth=data.get("workplace_search.access_token")
        )
    try:
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
                    "color": "#f00f00"
                },
                "is_searchable": True
            }
        )

        content_source_id = resp.get('id')
        print(
            f"Created ContentSource with ID {content_source_id}. You may now begin indexing with content-source-id= {content_source_id}")
    except Exception as exception:
        print("Could not create a content source, Error %s" % (exception))


if __name__ == "__main__":
    main()
