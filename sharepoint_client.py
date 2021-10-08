import requests
import time
import json
from requests.exceptions import RequestException
from requests_ntlm import HttpNtlmAuth
from urllib.parse import urljoin
from configuration import Configuration
from sharepoint_utils import print_and_log

domain = '[REDACTED]'
username = '[REDACTED]'
password = '[REDACTED]'


class SharePoint:
    def __init__(self, logger):
        self.logger = logger
        configuration = Configuration(
            file_name="sharepoint_connector_config.yml", logger=logger
        )
        if not configuration.validate():
            print_and_log(
                self.logger,
                "exception",
                "[Fail] Terminating the connector as the configuration parameters are not valid"
            )
            exit(0)
        self.configs = configuration.get_all_config()
        self.retry_count = int(self.configs.get("retry_count"))

    def get(self, rel_url, query):
        """Invokes a GET call to the Sharepoint server
            Returns:
                    Response of the GET call
        """
        request_headers = {
            "accept": "application/json;odata=verbose",
            "content-type": "application/json;odata=verbose"
        }
        url = urljoin(rel_url, query)
        retry = 0
        while retry <= self.retry_count:
            try:
                response = requests.get(
                    url,
                    auth=HttpNtlmAuth(domain + "\\" + username, password),
                    headers=request_headers
                )
                if response.status_code == (requests.codes.ok or requests.codes.not_found):
                    return response
                else:
                    print_and_log(
                        self.logger,
                        "error",
                        "Error while fetching from the sharepoint, url: %s. Retry Count: %s. Error: %s"
                        % (url, retry, response.reason)
                    )
                    # This condition is to avoid sleeping for the last time
                    if retry < self.retry_count:
                        time.sleep(2 ** retry)
                    else:
                        return False
                    retry += 1
            except RequestException as exception:
                print_and_log(
                    self.logger,
                    "exception",
                    "Error while fetching from the sharepoint, url: %s. Retry Count: %s. Error: %s"
                    % (url, retry, exception)
                )
                # This condition is to avoid sleeping for the last time
                if retry < self.retry_count:
                    time.sleep(2 ** retry)
                else:
                    return False
                retry += 1