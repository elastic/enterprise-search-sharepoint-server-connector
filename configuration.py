import yaml

from yaml.error import YAMLError
from cerberus import Validator
from schema import schema
from sharepoint_utils import print_and_log


class Configuration:
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

    def validate(self):
        self.logger.info("Validating the configuration parameters")
        validator = Validator(schema)
        validator.validate(self.configurations, schema)
        if validator.errors:
            print_and_log(self.logger, "error", "Error while validating the config. Errors: %s" % (validator.errors))
            return False
        self.logger.info("Successfully validated the config file")
        return True

    def get_all_config(self):
        return self.configurations

    def reload_configs(self):
        try:
            with open(self.file_name) as stream:
                self.configurations = yaml.safe_load(stream)
        except YAMLError as exception:
            print_and_log(
                self.logger,
                "exception",
                "Error while reading the configurations from %s. Error: %s" % (
                    self.file_name, exception
                ),
            )
        return self.configurations
