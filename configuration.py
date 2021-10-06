import yaml
import datetime
import calendar

from yaml.error import YAMLError
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

    def validate_date(self, param_name, input_date):
        """Validates the date format in the parameter being passed 
        """
        current_time = int(
            calendar.timegm(datetime.datetime.utcnow().timetuple())
        )
        if input_date:
            try:
                input_date = int(
                    calendar.timegm(
                        datetime.datetime.strptime(
                            input_date, "%Y-%m-%dT%H:%M:%SZ"
                        ).timetuple()
                    )
                )
            except ValueError:
                self.logger.warn(
                    'The parameter %s is not in the right format. Expected format "YYYY-MM-DDThh:mm:ssZ", found: %s'
                    % (param_name, input_date)
                )
                return False

            if input_date > current_time:
                self.logger.warn(
                    "The parameter %s can not be greater than current Time"
                    % param_name
                )
                return False

            elif input_date < 0:
                self.logger.warn(
                    "The parameter %s should be greater than 01-Jan-1970 UTC"
                    % param_name
                )
                return False
        return True

    def validate_interval(self, param_name, interval):
        """Validates the indexing and de-indexing inervals specified in 
            the yaml configuration file
        """
        if not interval:
            self.logger.warn(
                "The parameter %s is not present. Considering the default value as 60 minutes"
                % param_name
            )
        elif not isinstance(interval, int):
            self.logger.warn(
                "The parameter %s should be a positive integer, found: %s. Considering the default value as 60 minutes"
                % (param_name, interval)
            )
        elif not interval > 0:
            self.logger.warn(
                "The parameter %s must be a positive integer, found: %s. Considering the default value as 60 minutes"
                % (param_name, interval)
            )

    def validate(self):
        self.logger.info("Validating the configuration parameters")
        # validating mandatory fields
        PROPS = [
            "sharepoint.client_id",
            "sharepoint.client_secret",
            "sharepoint.realm",
            "sharepoint.host_url",
            "workplace_search.access_token",
            "workplace_search.source_id",
            "enterprise_search.host_url",
            "sharepoint.site_collections",
        ]
        for prop in PROPS:
            if not self.configurations.get(prop):
                print_and_log(
                    self.logger, "error", "%s cannot be empty" % (prop)
                )
                return False

        # validating enable_document_permissions parameter
        enable_document_permissions = self.configurations.get(
            "enable_document_permission"
        )
        if enable_document_permissions is None:
            self.logger.warn(
                "The parameter enable_document_permissions is not present. Considering the default value as yes"
            )
        elif str(enable_document_permissions).lower() not in ["true", "false"]:
            self.logger.warn(
                "The parameter enable_document_permission does not contain a valid value. Expected values are yes/no, found: %s. Considering the default value as yes"
                % (enable_document_permissions)
            )

        # validating start_time parameter
        start_time = self.configurations.get("start_time")
        if not start_time:
            self.logger.warn(
                "The parameter start_time is not present. Considering the default value and bringing all the documents since the begining"
            )
        elif not self.validate_date("start_time", start_time):
            self.logger.warn(
                "The parameter start_time is not in the valid format. Considering the default value and bringing all the documents since the begining"
            )

        # validating end_time parameter
        end_time = self.configurations.get("end_time")
        if not end_time:
            self.logger.warn(
                "The parameter end_time is not present. Considering the default value and bringing all the documents till current time"
            )
        elif not self.validate_date("end_time", end_time):
            self.logger.warn(
                "The parameter end_time is not in the valid format. Considering the default value and bringing all the documents till current time"
            )

        # validating indexing_interval parameter
        self.validate_interval(
            "indexing_interval", self.configurations.get("indexing_interval")
        )
        # validating deletion_interval parameter
        self.validate_interval(
            "deletion_interval", self.configurations.get("deletion_interval")
        )

        # validating log_level
        log_level = self.configurations.get("log_level")
        if not log_level:
            self.logger.warn(
                "The parameter log_level is not present. Considering the default value as INFO"
            )
        elif log_level.lower() not in ["debug", "info", "warn", "error"]:
            self.logger.warn(
                "The parameter log_level does not contain a valid value. Expected values are debug/info/warn/error, found:{}. Considering the default value as INFO"
            )

        retry_count = self.configurations.get("retry_count")
        if not retry_count:
            self.logger.warn(
                "The parameter retry_count is not present. Considering the default value as 3"
            )
        else:
            try:
                retry_count = int(retry_count)
            except ValueError:
                self.logger.warn(
                    "The parameter retry_count does not contain a valid positive integer value, found: %s. Considering the default value as 3"
                    % retry_count
                )

        self.logger.info(
            "Successfully validated all the configuration parameters"
        )
        return True
        # validate object and include/exclude fields
        # TODO

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
