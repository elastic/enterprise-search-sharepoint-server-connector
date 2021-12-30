#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License;
# you may not use this file except in compliance with the Elastic License.
#

python3 fullsync.py & python3 fetch_index.py & python3 deindex.py & python3 sync_user_permissions.py
