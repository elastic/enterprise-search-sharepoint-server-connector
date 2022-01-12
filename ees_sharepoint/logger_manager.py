#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#
"""This module contains logging-related logic."""
#TODO: clean up

import os
import logging
import logging.handlers

import ecs_logging


def setup_logging(log_name, log_level=logging.INFO):
    """Setup logger.

    :param log_name: name for logger
    :param log_level: log level, a string
    :return: a logger object"""

    # Make path till log file
    log_name += ".log"
    log_file = os.path.join(os.path.dirname(__file__), log_name)
    # Get directory in which log file is present
    log_dir = os.path.dirname(log_file)
    # Create directory at the required path to store log file, if not found
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    logger = logging.getLogger(log_name)
    logger.propagate = False

    # Set log level
    logger.setLevel(log_level)

    handler_exists = any(
        h.baseFilename == log_file for h in logger.handlers
    )

    if not handler_exists:
        handler = logging.handlers.RotatingFileHandler(
            log_file, mode="a", maxBytes=10485760, backupCount=10
        )
        handler.setFormatter(ecs_logging.StdlibFormatter())
        logger.addHandler(handler)
        if log_level is not None:
            handler.setLevel(log_level)

    return logger
