#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#

import yaml
from yaml.error import YAMLError
from cerberus import Validator

from .schema import schema
from .sharepoint_utils import print_and_log


class Configuration:

    __instance = None

    def __new__(cls, *args, **kwargs):
        if not Configuration.__instance:
            Configuration.__instance = object.__new__(cls)
        return Configuration.__instance

    def __init__(self, file_name, logger=None):
        self.logger = logger
        self.file_name = file_name
        try:
            with open(file_name, "r", encoding="utf-8") as stream:
                self.configurations = yaml.safe_load(stream)
        except YAMLError as exception:
            if hasattr(exception, 'problem_mark'):
                mark = exception.problem_mark
                print_and_log(
                    self.logger,
                    "exception",
                    "Error while reading the configurations from %s file at line %s."
                    % (file_name, mark.line),
                )
            else:
                print_and_log(
                    self.logger,
                    "exception",
                    "Something went wrong while parsing yaml file %s. Error: %s"
                    % (file_name, exception),
                )
        self.configurations = self.validate()
        # Converting datetime object to string
        for date_config in ["start_time", "end_time"]:
            self.configurations[date_config] = self.configurations[date_config].strftime('%Y-%m-%dT%H:%M:%SZ')

    def validate(self):
        """Validates each properties defined in the yaml configuration file
        """
        self.logger.info("Validating the configuration parameters")
        validator = Validator(schema)
        validator.validate(self.configurations, schema)
        if validator.errors:
            print_and_log(self.logger, "error", "Error while validating the config. Errors: %s" % (
                validator.errors))
            exit(0)
        self.logger.info("Successfully validated the config file")
        return validator.document
