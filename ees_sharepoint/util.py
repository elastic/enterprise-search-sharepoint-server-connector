#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#
"""util module contains general utility classes."""

import os
import logging
import logging.config

# Uncomment this line to include dependency that allows to
# output logs in ECS-compatible format
# import ecs_logging

logger = None

def _init_logger():
    global logger
    if logger:
        return

    log_level = os.environ.get("LOGLEVEL", "WARN")
    logger = logging.getLogger(__name__)
    logger.propagate = False
    logger.setLevel(log_level)

    handler = logging.StreamHandler()
    # Uncomment the following lines to output logs in ECS-compatible format
    # formatter = ecs_logging.StdlibFormatter()
    # handler.setFormatter(formatter)
    handler.setLevel(log_level)
    logger.addHandler(handler)

_init_logger()

class Singleton(type):
    """Singleton class provides a metaclass for Singeton pattern.

    Can be used by defining class Something(metaclass=Singleton)"""
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]
