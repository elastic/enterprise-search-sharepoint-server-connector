import requests
import time
from requests.exceptions import RequestException
from requests_ntlm import HttpNtlmAuth
from configuration import Configuration
from sharepoint_utils import print_and_log


class SharePoint:
    def __init__(self, logger):
        self.logger = logger
        configuration = Configuration(
            file_name="sharepoint_connector_config.yml", logger=logger
        )
        self.configs = configuration.configurations
        self.retry_count = int(self.configs.get("retry_count"))
        self.domain = self.configs.get("sharepoint.domain")
        self.username = self.configs.get("sharepoint.username")
        self.password = self.configs.get("sharepoint.password")

    def get(self, rel_url, query, param_name):
        """ Invokes a GET call to the Sharepoint server
            :param rel_url: relative url to the sharepoint farm
            :param query: query for passing arguments to the url
            :param param_name: parameter name whether it is SITES, LISTS, ITEMS, permissions or deindex
            Returns:
                Response of the GET call
        """
        request_headers = {
            "accept": "application/json;odata=verbose",
            "content-type": "application/json;odata=verbose"
        }

        response_list = {"d": {"results": []}}
        paginate_query = True
        skip, top = 0, 5000
        while paginate_query:
            if param_name in ["sites", "lists"]:
                paginate_query = query + f"&$skip={skip}&$top={top}"
            elif skip == 0 and param_name == "items":
                paginate_query = query + f"&$top={top}"
            elif param_name in ["permission_users", "permission_groups", "deindex", "attachment"]:
                paginate_query = query
            url = rel_url + paginate_query
            skip += 5000
            retry = 0
            while retry <= self.retry_count:
                try:
                    response = requests.get(
                        url,
                        auth=HttpNtlmAuth(self.domain + "\\" + self.username, self.password),
                        headers=request_headers
                    )
                    if response.status_code == requests.codes.ok:
                        if param_name in ["sites", "lists"] and response:
                            response_data = response.json()
                            response_result = response_data.get("d", {}).get("results")
                            response_list["d"]["results"].extend(response_result)
                            if len(response_result) < 5000:
                                paginate_query = None
                            break
                        elif param_name == "items" and response:
                            response_data = response.json()
                            response_list["d"]["results"].extend(response_data.get("d", {}).get("results"))
                            paginate_query = response_data.get("d", {}).get("__next", False)
                            break
                        else:
                            return response
                    elif response.status_code >= 400 and response.status_code < 500:
                        if not (param_name == 'deindex' and response.status_code == 404):
                            print_and_log(
                                    self.logger,
                                    "exception",
                                    "Error: %s. Error while fetching from the sharepoint, url: %s."
                                    % (response.reason, url)
                                )
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
                        retry += 1
                        continue

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
        return response_list

    def get_query(self, start_time, end_time, param_name):
        """ returns the query for each objects
            :param start_time: start time of the interval for fetching the documents
            :param end_time: end time of the interval for fetching the documents
            Returns:
                query: query for each object
        """
        query = ""
        if param_name in ["sites", "lists"]:
            query = f"?$filter=(LastItemModifiedDate ge datetime'{start_time}') and (LastItemModifiedDate le datetime'{end_time}')"
        elif param_name == "items":
            query = f"?$filter=(Modified ge datetime'{start_time}') and (Modified le datetime'{end_time}')"
        return query
