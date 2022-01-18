#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#
"""This module provides the tooling to synchronize data
from Sharepoint Server 2016 to Elastic Enterprise Search."""
__version__ = "0.1.0"

import os
import logging
import logging.config

# Uncomment this line to include dependency that allows to
# output logs in ECS-compatible format
# import ecs_logging

log_level = os.environ.get("LOGLEVEL", "WARN")
logger = logging.getLogger()
logger.propagate = False
logger.setLevel(log_level)

handler = logging.StreamHandler()
# Uncomment the following lines to output logs in ECS-compatible format
# formatter = ecs_logging.StdlibFormatter()
# handler.setFormatter(formatter)
handler.setLevel(log_level)
logger.addHandler(handler)
