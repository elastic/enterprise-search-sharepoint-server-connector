import yaml
import datetime
import calendar
import re
from sharepoint_utils import print_and_log


class Configuration:
    def __init__(self, file_name, logger=None):
        self.logger = logger
        try:
            with open(file_name, 'r') as stream:
                self.configurations = yaml.safe_load(stream)
        except Exception as exception:
            print_and_log(self.logger, 'error', "Error while reading the configurations from {}. Error: {}".format(
                file_name, exception))

    def validate_date(self, param_name, input_date):
        current_time = int(calendar.timegm(
            datetime.datetime.utcnow().timetuple()))
        if input_date:
            if not re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$", input_date):
                self.logger.warn(
                    "The parameter {} is not in the right format. Expected format \"YYYY-MM-DDThh:mm:ss\", found: {}".format(param_name, input_date))
                return False

            try:
                input_date = int(calendar.timegm(datetime.datetime.strptime(
                    input_date, "%Y-%m-%dT%H:%M:%S").timetuple()))
            except Exception:
                self.logger.warn(
                    "The parameter {} is not in the right format. Expected format \"YYYY-MM-DDThh:mm:ss\", found: {}".format(param_name, input_date))
                return False

            if input_date > current_time:
                self.logger.warn(
                    "The parameter {} can not be greater than current Time".format(param_name))
                return False

            elif input_date < 0:
                self.logger.warn(
                    "The parameter {} should be greater than 01-Jan-1970 UTC".format(param_name))
                return False
        return True

    def validate_interval(self, param_name, interval):
        if not interval:
            self.logger.warn(
                "The parameter {} is not present. Considering the default value as 60 minutes".format(param_name))
        elif not isinstance(interval, int):
            self.logger.warn("The parameter {} should be a positive integer, found: {}. Considering the default value as 60 minutes".format(
                param_name, interval))
        elif not interval > 0:
            self.logger.warn("The parameter {} should be a positive integer, found: {}. Considering the default value as 60 minutes".format(
                param_name, interval))

    def validate(self):
        self.logger.info('Validating the configuration parameters')
        # validating mandatory fields
        if not self.configurations.get('sharepoint.client_id'):
            print_and_log(self.logger, 'error',
                          'sharepoint.clien_id cannot be empty')
            return False
        if not self.configurations.get('sharepoint.client_secret'):
            print_and_log(self.logger, 'error',
                          'sharepoint.client_secret cannot be empty')
            return False
        if not self.configurations.get('sharepoint.realm'):
            print_and_log(self.logger, 'error',
                          'sharepoint.realm cannot be empty')
            return False
        if not self.configurations.get('sharepoint.host_url'):
            print_and_log(self.logger, 'error',
                          'sharepoint.host_url cannot be empty')
            return False
        if not self.configurations.get('ws.access_token'):
            print_and_log(self.logger, 'error',
                          'ws.access_token cannot be empty')
            return False
        if not self.configurations.get('ws.source_id'):
            print_and_log(self.logger, 'error', 'ws.source_id cannot be empty')
            return False
        if not self.configurations.get('ws.host_url'):
            print_and_log(self.logger, 'error', 'ws.host_url cannot be empty')
            return False
        if not self.configurations.get('sharepoint.site_collections'):
            print_and_log(self.logger, 'error',
                          'sharepoint.site_collections cannot be empty')
            return False

        # validating enable_document_permissions parameter
        enable_document_permissions = self.configurations.get(
            'enable_document_permission')
        if enable_document_permissions is None:
            self.logger.warn(
                "The parameter enable_document_permissions is not present. Considering the default value as yes")
        elif str(enable_document_permissions).lower() not in ['true', 'false']:
            self.logger.warn(
                "The parameter enable_document_permission does not contain a valid value. Expected values are yes/no, found: {}. Considering the default value as yes".format(enable_document_permissions))

        # validating start_time parameter
        start_time = self.configurations.get('start_time')
        if not start_time:
            self.logger.warn(
                "The parameter start_time is not present. Considering the default value and bringing all the documents since the begining")
        elif not self.validate_date("start_time", start_time):
            self.logger.warn(
                "The parameter start_time is not in the valid format. Considering the default value and bringing all the documents since the begining")

        # validating end_time parameter
        end_time = self.configurations.get('end_time')
        if not end_time:
            self.logger.warn(
                "The parameter end_time is not present. Considering the default value and bringing all the documents till current time")
        elif not self.validate_date("end_time", end_time):
            self.logger.warn(
                "The parameter end_time is not in the valid format. Considering the default value and bringing all the documents till current time")

        # validating indexing_interval parameter
        self.validate_interval("indexing_interval",
                               self.configurations.get('indexing_interval'))
        # validating deletion_interval parameter
        self.validate_interval("deletion_interval",
                               self.configurations.get('deletion_interval'))

        # validating log_level
        log_level = self.configurations.get('log_level')
        if not log_level:
            self.logger.warn(
                "The parameter log_level is not present. Considering the default value as INFO")
        elif log_level.lower() not in ['debug', 'info', 'warn', 'error']:
            self.logger.warn(
                "The parameter log_level does not contain a valid value. Expected values are debug/info/warn/error, found:{}. Considering the default value as INFO")

        retry_count = self.configurations.get('retry_count')
        if not retry_count:
            self.logger.warn(
                "The parameter retry_count is not present. Considering the default value as 3")
        else:
            try:
                retry_count = int(retry_count)
            except Exception:
                self.logger.warn(
                    "The parameter retry_count does not contain a valid positive integer value, found: {}. Considering the default value as 3".format(retry_count))

        self.logger.info(
            'Successdully validated all the configuration parameters')
        return True
        # validate object and include/exclude fields
        # TODO

    def get_all_config(self):
        return self.configurations
