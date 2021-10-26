import datetime


def validate_date_new(input_date):
    if input_date:
        return datetime.datetime.strptime(input_date, "%Y-%m-%dT%H:%M:%SZ")


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
    'workplace_search.access_token': {
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
            'items': {
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
        'coerce': validate_date_new
    },
    'end_time': {
        'required': False,
        'type': 'datetime',
        'max': datetime.datetime.utcnow(),
        'default': (datetime.datetime.utcnow()).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'coerce': validate_date_new
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
    'log_level': {
        'required': False,
        'type': 'string',
        'default': 'info',
        'allowed': ['debug', 'info', 'warn', 'error']
    },
    'retry_count': {
        'required': False,
        'type': 'integer',
        'default': 3,
        'min': 1
    },
    'sharepoint_workplace_user_mapping': {
        'required': False,
        'type': 'string'
    },
    'worker_process': {
        'required': False,
        'type': 'integer'
    }
}
