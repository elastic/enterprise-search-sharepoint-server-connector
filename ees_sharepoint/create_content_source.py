#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#
"""This module allows to create Content Source in Elastic Enterprise Search.

It can be used to create a Content Source that will be used to upload the
data from Sharepoint Server to Elastic Enterprise Search instance.

Otherwise, it's possible to use Content Source that was pre-created
in Elastic Enterprise Search"""

import argparse
import getpass

from elastic_enterprise_search import WorkplaceSearch

from .configuration import Configuration
from . import logger_manager as log

logger = log.setup_logging("sharepoint_connector_bootstrap")


def start():
    """This function attempts to create a Content Source.

    It will use data from configuration file to determine
    which instance of Elastic Enterprise Search will be used
    to create a Content Source."""

    config = Configuration("sharepoint_connector_config.yml", logger=logger)
    parser = argparse.ArgumentParser(
        description='Create a custom content source.')
    parser.add_argument("--name", required=True, type=str,
                        help="Name of the content source to be created")
    parser.add_argument("--user", required=False, type=str,
                        help="username of the workplce search admin account ")

    host = config.get_value("enterprise_search.host_url")
    args = parser.parse_args()
    if args.user:
        password = getpass.getpass(prompt='Password: ', stream=None)
        workplace_search = WorkplaceSearch(
            f"{host}/api/ws/v1/sources", http_auth=(args.user, password)
        )
    else:
        workplace_search = WorkplaceSearch(
            f"{host}/api/ws/v1/sources", http_auth=config.get_value("workplace_search.access_token")
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
                    "color": "#000000"
                },
                "is_searchable": True
            }
        )

        content_source_id = resp.get('id')
        print(
            f"Created ContentSource with ID {content_source_id}. You may now begin indexing with content-source-id= {content_source_id}")
    except Exception as exception:
        print("Could not create a content source, Error %s" % (exception))
