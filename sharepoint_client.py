import requests
import time
from requests_ntlm import HttpNtlmAuth
from urllib.parse import urljoin
from configuration import Configuration
from sharepoint_utils import print_and_log

domain =   "[REDACTED]"
username = "[REDACTED]"
password = "[REDACTED]"


class SharePoint:
    def __init__(self, logger):
        self.logger = logger
        configuration = Configuration(
            file_name='sharepoint_connector_config.yml', logger=logger)
        if not configuration.validate():
            print_and_log(
                self.logger, 'error', '[Fail] Terminating the connector as the configuration parameters are not valid')
            exit(0)
        self.configs = configuration.get_all_config()
        self.retry_count = int(self.configs.get('retry_count'))

    def get(self, rel_url, query):
        request_headers = {'accept': "application/json;odata=verbose",
                           "content-type": "application/json;odata=verbose"}
        url = urljoin(rel_url, query)
        retry = 0
        while retry <= self.retry_count:
            try:
                response = requests.get(url, auth=HttpNtlmAuth(
                    domain + "\\" + username, password), headers=request_headers)
                if response.status_code == requests.codes.ok:
                    return response
                else:
                    print_and_log(self.logger, 'error', 'Error while fetching from the sharepoint, url: {}. Retry Count: {}. Error: {}'.format(
                        url, retry, response.text))
                    # This condition is to avoid sleeping for the last time
                    if retry < self.retry_count:
                        time.sleep(2**retry)
                    else:
                        return False
                    retry += 1
            except Exception as exception:
                print_and_log(
                    self.logger, 'error', 'Error while fetching from the sharepoint, url: {}. Retry Count: {}. Error: {}'.format(url, retry, exception))
                # This condition is to avoid sleeping for the last time
                if retry < self.retry_count:
                    time.sleep(2**retry)
                else:
                    return False
                retry += 1