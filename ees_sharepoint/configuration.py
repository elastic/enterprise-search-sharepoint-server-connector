#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#
"""Configuration module allows manipulations with application configuration.

This module can be used to read and validate configuration file that defines
the settings of the Sharepoint Server connector."""

import yaml
from yaml.error import YAMLError
from cerberus import Validator

from .log import logger
from .schema import schema
from .util import Singleton


class ConfigurationInvalidException(Exception):
    """Exception raised when configuration was invalid.

    Attributes:
        errors - errors found in the configuration
        message -- explanation of the error
    """

    def __init__(self, errors, message="Provided configuration was invalid"):
        self.errors = errors
        self.message = message
        super().__init__(f"{message}. Errors: {errors}.")


class Configuration(metaclass=Singleton):
    """Configuration class is responsible for parsing, validating and accessing
    configuration options from connector configuration file."""

    __configurations = {}

    def __init__(self, file_name):
        self.file_name = file_name

        try:
            with open(file_name) as stream:
                self.__configurations = yaml.safe_load(stream)
        except YAMLError as exception:
            if hasattr(exception, 'problem_mark'):
                logger.exception(
                    f"""Error while reading the configurations from {file_name} file \
                    at line {exception.problem_mark.line}."""
                )
            else:
                logger.exception(
                    f"""Something went wrong while parsing yaml file {file_name}. \
                    Error: {exception}"""
                )
        self.__configurations = self.validate()
        # Converting datetime object to string
        for date_config in ["start_time", "end_time"]:
            value = self.__configurations[date_config]
            self.__configurations[date_config] = self.__parse_date_config_value(value)

    def validate(self):
        """Validates each property defined in the yaml configuration file"""
        logger.info("Validating the configuration parameters")
        validator = Validator(schema)
        validator.validate(self.__configurations, schema)
        if validator.errors:
            logger.error(f"Error while validating the config. Errors: {validator.errors}")
            raise ConfigurationInvalidException(validator.errors)
        logger.info("Successfully validated the config file")
        return validator.document

    def get_value(self, key):
        """Returns a configuration value that matches the key argument"""
        return self.__configurations.get(key)

    @staticmethod
    def __parse_date_config_value(string):
        return string.strftime('%Y-%m-%dT%H:%M:%SZ')
