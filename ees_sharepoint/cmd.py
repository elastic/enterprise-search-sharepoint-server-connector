#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#
"""Cmd module contains entry points for the package.

Each endpoint provides a meaningful piece of functionallity
related to uploading data from Sharepoint Server 2016
to Elastic Enterprise Search"""

import sys

from . import create_content_source, fetch_index, deindex, sync_user_permissions

def bootstrap():
    """bootstrap function is responsible for Content Source creation.

    This function will attempt to create a Content Source in Enterprise Search
    instance that is specified in configuration file. After a Content
    Source is created, its id will be displated in the console."""
    create_content_source.start()
    sys.exit(0)

def test_connectivity():
    """test_connectivity function is responsible for testing service access.

    This function will attempt to check connectivity to all services used
    by the Connector, or only the services specified as an argument."""
    #TODO: implement, see test_connectivity.py
    print("Not yet implemented")
    sys.exit(0)

def full_sync():
    """full_sync function is responsible for syncing all data from remote system.

    This function will attempt to synchronize all data from Sharepoint Server 2016
    to Elastic Enterprise Search instance from the beginning of time."""
    fetch_index.start("full_sync")
    sys.exit(0)

def incremental_sync():
    """incremental_sync function is responsible for syncing data from remote system incrementally.

    This function will attempt to synchronize only data that was modified recently
    from Sharepoint Server 2016 to Elastic Enterprise Search instance."""
    fetch_index.start("incremental_sync")
    sys.exit(0)

def deletion_sync():
    """deletion_sync function is responsible for wiping deleted data from Enterprise Search.

    This function will attempt to delete the data that was deleted from Sharepoint Server 2016
    but is still available at Elastic Enterprise Search instance."""
    deindex.start()
    sys.exit(0)

def permission_sync():
    """permission_sync function is responsible for syncing Sharepoint Server user permissions.

    This function will attempt to fetch permissions for the users permissions from Sharepoint
    Server and sending them to Elastic Enterprise Search instance. This will effectively
    recalculate the permissions for all users in Elastic Enterprise Search."""
    sync_user_permissions.start()
    sys.exit(0)
