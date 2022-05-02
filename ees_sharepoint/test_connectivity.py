#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#
"""test_connectivity module allows to test that connector setup is correct.

It's possible to check connectivity to Sharepoint Server instance,
to Elastic Enterprise Search instance and check if ingestion of
documents works."""

import time
import logging

import pytest
from elastic_enterprise_search import WorkplaceSearch

from .sharepoint_client import SharePoint
from .configuration import Configuration


@pytest.fixture(name="settings")
def fixture_settings():
    """This function loads config from the file and returns it along with retry_count setting."""
    configuration = Configuration(
        file_name="sharepoint_server_connector.yml"
    )

    logger = logging.getLogger("test_connectivity")
    return configuration, logger


@pytest.mark.sharepoint
def test_sharepoint(settings):
    """ Tests the connection to the sharepoint server by calling a basic get request to fetch sites in a collection and logs proper messages"""
    configs, logger = settings
    print("Starting SharePoint connectivity tests..")
    sharepoint_client = SharePoint(configs, logger)
    collection = configs.get_value("sharepoint.site_collections")[0]
    response = sharepoint_client.get(f"_api/web/webs", query="?", param_name="sites")
    if not response:
        assert False, "Error while connecting to the Sharepoint server at %s" % (
            configs.get_value("sharepoint.host_url"))
    else:
        assert True
    print("SharePoint connectivity tests completed..")


@pytest.mark.workplace
def test_workplace(settings):
    """ Tests the connection to the Enterprise search host"""
    configs, _ = settings
    print("Starting Workplace connectivity tests..")
    retry_count = configs.get_value("retry_count")
    enterprise_search_host = configs.get_value("enterprise_search.host_url")
    retry = 0
    while retry <= retry_count:
        try:
            workplace_search = WorkplaceSearch(
                enterprise_search_host,
                http_auth=configs.get_value(
                    "workplace_search.api_key"
                ),
            )
            response = workplace_search.get_content_source(
                content_source_id=configs.get_value(
                    "workplace_search.source_id"
                )
            )
            if response:
                assert True
                break
        except Exception as exception:
            print(
                f"[Fail] Error while connecting to the workplace host {enterprise_search_host}. Retry Count: {retry}. Error: {exception}"
            )
            # This condition is to avoid sleeping for the last time
            if retry < retry_count:
                time.sleep(2 ** retry)
            else:
                assert False, "Error while connecting to the Enterprise Search at %s" % (
                    enterprise_search_host)
            retry += 1

    print("Workplace connectivity tests completed..")


@pytest.mark.ingestion
def test_ingestion(settings):
    """ Tests the successful ingestion and deletion of a sample document to the Workplace search"""
    configs, logger = settings
    retry_count = configs.get_value("retry_count")
    enterprise_search_host = configs.get_value("enterprise_search.host_url")
    print("Starting Workplace ingestion tests..")
    document = [
        {
            "id": 1234,
            "title": "The Meaning of Time",
            "body": "Not much. It is a made up thing.",
            "url": "https://example.com/meaning/of/time",
            "created_at": "2019-06-01T12:00:00+00:00",
            "type": "list",
        }
    ]
    workplace_search = WorkplaceSearch(enterprise_search_host)
    retry = 0
    response = None
    while retry <= retry_count:
        try:
            response = workplace_search.index_documents(
                http_auth=configs.get_value("workplace_search.api_key"), content_source_id=configs.get_value("workplace_search.source_id"),
                documents=document,
            )
            print(
                "Successfully indexed a dummy document with id 1234 in the Workplace")
            break
        except Exception as exception:
            print(
                f"[Fail] Error while ingesting document to the workplace host {enterprise_search_host}. Retry Count: {retry}. Error: {exception}"
            )
            # This condition is to avoid sleeping for the last time
            if retry < retry_count:
                time.sleep(2 ** retry)
            else:
                assert False, "Error while connecting to the Enterprise Search at %s" % (
                    enterprise_search_host)
            retry += 1

    if response:
        print(
            "Attempting to delete the dummy document 1234 from the Workplace for cleanup"
        )
        retry = 0
        while retry <= retry_count:
            try:
                response = workplace_search.delete_documents(
                    http_auth=configs.get_value(
                        "workplace_search.api_key"
                    ),
                    content_source_id=configs.get_value(
                        "workplace_search.source_id"
                    ),
                    document_ids=[1234],
                )
                print(
                    "Successfully deleted the dummy document with id 1234 from the Workplace"
                )
                if response:
                    assert True
                    break
            except Exception as exception:
                print(
                    f"[Fail] Error while deleting document id 1234 from the workplace host {enterprise_search_host}. Retry Count: {retry}. Error: {exception}"
                )
                # This condition is to avoid sleeping for the last time
                if retry < retry_count:
                    time.sleep(2 ** retry)
                else:
                    assert False, "Error while connecting to the Enterprise Search at %s" % (
                        enterprise_search_host)
                retry += 1

    print("Workplace ingestion tests completed..")
