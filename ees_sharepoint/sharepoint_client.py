#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#
"""sharepoint_client allows to call Sharepoint or make queries for it."""

import time
import requests
import logging

from requests.exceptions import RequestException
from requests_ntlm import HttpNtlmAuth

from .configuration import Configuration


class SharePoint:
    """This class encapsulates all module logic."""
    def __init__(self):
        configuration = Configuration(
            file_name="sharepoint_connector_config.yml"
        )

        self.retry_count = int(configuration.get_value("retry_count"))
        self.domain = configuration.get_value("sharepoint.domain")
        self.username = configuration.get_value("sharepoint.username")
        self.password = configuration.get_value("sharepoint.password")

    def get(self, rel_url, query, param_name):
        """ Invokes a GET call to the Sharepoint server
            :param rel_url: relative url to the sharepoint farm
            :param query: query for passing arguments to the url
            :param param_name: parameter name whether it is sites, lists, list_items, drive_items, permissions or deindex
            Returns:
                Response of the GET call"""
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
            elif skip == 0 and param_name in ["list_items", "drive_items"]:
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
                    if response.ok:
                        if param_name in ["sites", "lists"] and response:
                            response_data = response.json()
                            response_result = response_data.get("d", {}).get("results")
                            response_list["d"]["results"].extend(response_result)
                            if len(response_result) < 5000:
                                paginate_query = None
                            break
                        if param_name in ["list_items", "drive_items"] and response:
                            response_data = response.json()
                            response_list["d"]["results"].extend(response_data.get("d", {}).get("results"))
                            paginate_query = response_data.get("d", {}).get("__next", False)
                            break

                        return response

                    if response.status_code >= 400 and response.status_code < 500:
                        if not (param_name == 'deindex' and response.status_code == 404):
                            logging.exception(
                                f"Error: {response.reason}. Error while fetching from the sharepoint, url: {url}."
                            )
                        return response
                    logging.error(
                        f"Error while fetching from the sharepoint, url: {url}. Retry Count: {retry}. Error: {response.reason}"
                    )
                    # This condition is to avoid sleeping for the last time
                    if retry < self.retry_count:
                        time.sleep(2 ** retry)
                    retry += 1
                    paginate_query = None
                    continue
                except RequestException as exception:
                    logging.exception(
                        f"Error while fetching from the sharepoint, url: {url}. Retry Count: {retry}. Error: {response.reason}"
                    )
                    # This condition is to avoid sleeping for the last time
                    if retry < self.retry_count:
                        time.sleep(2 ** retry)
                    else:
                        return False
                    retry += 1
        if retry > self.retry_count:
            return response
        return response_list

    @staticmethod
    def get_query(start_time, end_time, param_name):
        """ returns the query for each objects
            :param start_time: start time of the interval for fetching the documents
            :param end_time: end time of the interval for fetching the documents
            Returns:
                query: query for each object"""
        query = ""
        if param_name in ["sites", "lists"]:
            query = f"?$filter=(LastItemModifiedDate ge datetime'{start_time}') and (LastItemModifiedDate le datetime'{end_time}')"
        else:
            query = f"$filter=(Modified ge datetime'{start_time}') and (Modified le datetime'{end_time}')"
            if param_name == "list_items":
                query = "?" + query
            else:
                query = "&" + query
        return query
