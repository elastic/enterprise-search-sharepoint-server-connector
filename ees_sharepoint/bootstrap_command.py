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

from .base_command import BaseCommand


class BootstrapCommand(BaseCommand):
    """This class defines a method to create a content source.
    """
    def execute(self):
        """This function attempts to create a Content Source.

        It will use data from configuration file to determine
        which instance of Elastic Enterprise Search will be used
        to create a Content Source."""

        schema = {
            "title": "text",
            "body": "text",
            "url": "text",
            "created_at": "date",
            "name": "text",
            "description": "text",
        }
        display = {
            "title_field": "title",
            "description_field": "description",
            "url_field": "url",
            "detail_fields": [
                {"field_name": 'description', "label": 'Description'},
                {"field_name": 'body', "label": 'Content'},
                {"field_name": 'created_at', "label": 'Created At'}
            ],
            "color": "#000000"
        }
        self.workplace_search_custom_client.create_content_source(schema, display, name=self.args.name, is_searchable=True)
