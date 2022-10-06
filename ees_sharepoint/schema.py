#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#
"""schema module contains Connector configuration file schema."""

import datetime


def coerce_rfc_3339_date(input_date):
    """This function returns true if its argument is a valid RFC 3339 date."""
    if input_date:
        return datetime.datetime.strptime(input_date, "%Y-%m-%dT%H:%M:%SZ")
    return False


schema = {
    'sharepoint.domain': {
        'required': True,
        'type': 'string'
    },
    'sharepoint.username': {
        'required': True,
        'type': 'string'
    },
    'sharepoint.password': {
        'required': True,
        'type': 'string'
    },
    'sharepoint.host_url': {
        'required': True,
        'type': 'string'
    },
    'sharepoint.site_collections': {
        'required': True,
        'type': 'list'
    },
    'workplace_search.api_key': {
        'required': True,
        'type': 'string'
    },
    'workplace_search.source_id': {
        'required': True,
        'type': 'string'
    },
    'enterprise_search.host_url': {
        'required': True,
        'type': 'string'
    },
    "sharepoint.secure_connection": {
        "required": True,
        "type": "boolean",
        "default": True,
    },
    "sharepoint.certificate_path": {
        "required": False,
        "type": "string",
        "empty": True
    },
    'enable_document_permission': {
        'required': False,
        'type': 'boolean',
        'default': True
    },
    'objects': {
        'type': 'dict',
        'nullable': True,
        'schema': {
            'sites': {
                'nullable': True,
                'type': 'dict',
                'schema': {
                    'include_fields': {
                        'nullable': True,
                        'type': 'list'
                    },
                    'exclude_fields': {
                        'nullable': True,
                        'type': 'list'
                    }
                }
            },
            'lists': {
                'type': 'dict',
                'nullable': True,
                'schema': {
                    'include_fields': {
                        'nullable': True,
                        'type': 'list'
                    },
                    'exclude_fields': {
                        'nullable': True,
                        'type': 'list'
                    }
                }
            },
            'list_items': {
                'type': 'dict',
                'nullable': True,
                'schema': {
                    'include_fields': {
                        'nullable': True,
                        'type': 'list'
                    },
                    'exclude_fields': {
                        'nullable': True,
                        'type': 'list'
                    }
                }
            },
            'drive_items': {
                'type': 'dict',
                'nullable': True,
                'schema': {
                    'include_fields': {
                        'nullable': True,
                        'type': 'list'
                    },
                    'exclude_fields': {
                        'nullable': True,
                        'type': 'list'
                    }
                }
            }
        }
    },
    'start_time': {
        'required': False,
        'type': 'datetime',
        'max': datetime.datetime.utcnow(),
        'default': (datetime.datetime.utcnow() - datetime.timedelta(days=180)).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'coerce': coerce_rfc_3339_date
    },
    'end_time': {
        'required': False,
        'type': 'datetime',
        'max': datetime.datetime.utcnow(),
        'default': (datetime.datetime.utcnow()).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'coerce': coerce_rfc_3339_date
    },
    'indexing_interval': {
        'required': False,
        'type': 'integer',
        'default': 60,
        'min': 1
    },
    'deletion_interval': {
        'required': False,
        'type': 'integer',
        'default': 60,
        'min': 1
    },
    'full_sync_interval': {
        'required': False,
        'type': 'integer',
        'default': 2880,
        'min': 60
    },
    'sync_permission_interval': {
        'required': False,
        'type': 'integer',
        'default': 60,
        'min': 1
    },
    'log_level': {
        'required': False,
        'type': 'string',
        'default': 'INFO',
        'allowed': ['DEBUG', 'INFO', 'WARN', 'ERROR']
    },
    'retry_count': {
        'required': False,
        'type': 'integer',
        'default': 3,
        'min': 1
    },
    'sharepoint_sync_thread_count': {
        'required': False,
        'type': 'integer',
        'default': 5,
        'min': 1
    },
    'enterprise_search_sync_thread_count': {
        'required': False,
        'type': 'integer',
        'default': 5,
        'min': 1
    },
    'sharepoint_workplace_user_mapping': {
        'required': False,
        'type': 'string'
    }
}
