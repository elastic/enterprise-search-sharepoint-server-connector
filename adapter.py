#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#

DEFAULT_SCHEMA = {
    'sites': {
        'created_at': 'Created',
        'id': 'Id',
        'last_updated': 'LastItemModifiedDate',
        'relative_url': 'ServerRelativeUrl',
        'title': 'Title',
        'url': 'Url'
    },
    'lists': {
        'created_at': 'Created',
        'id': 'Id',
        'relative_url': 'ParentWebUrl',
        'title': 'Title'
    },
    'list_items': {
        'title': 'Title',
        'id': 'GUID',
        'created_at': 'Created',
        'author_id': 'AuthorId'
    },
    'drive_items': {
        'title': 'Name',
        'id': 'GUID',
        'created_at': 'TimeCreated',
        'last_updated': 'TimeLastModified'
    }
}
