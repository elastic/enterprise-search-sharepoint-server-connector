from sharepoint_client import SharePoint
import time
import logger_manager as log
from elastic_enterprise_search import WorkplaceSearch
from configuration import Configuration
from sharepoint_utils import print_and_log
from urllib.parse import urljoin
import pytest

logger = log.setup_logging("sharepoint_connector_test")


@pytest.fixture
def settings():
    configuration = Configuration(
        file_name="sharepoint_connector_config.yml", logger=logger
    )
    if not configuration.validate():
        print_and_log(
            logger,
            "error",
            "[Fail] Terminating the tests as the configuration parameters are not valid",
        )
        assert False, "Invalid configuration parameters in the config file"
    configs = configuration.reload_configs()
    return configs, configs.get("retry_count")


@pytest.mark.sharepoint
def test_sharepoint(settings):
    """ Tests the connection to the sharepoint server by calling a basic get request to fetch sites in a collection and logs proper messages
    """
    configs, _ = settings
    logger.info("Starting SharePoint connectivity tests..")
    sharepoint_client = SharePoint(logger)
    collection = configs.get("sharepoint.site_collections")[0]
    response = sharepoint_client.get(urljoin(configs.get(
        "sharepoint.host_url"), f"/sites/{collection}/_api/web/webs"), query="?", param_name="sites")
    if not response:
        assert False, "Error while connecting to the Sharepoint server at %s" % (
            configs.get("sharepoint.host_url"))
    else:
        assert True
    logger.info("SharePoint connectivity tests completed..")


@pytest.mark.workplace
def test_workplace(settings):
    """ Tests the connection to the Enterprise search host
    """
    configs, retry_count = settings
    logger.info("Starting Workplace connectivity tests..")
    enterprise_search_host = configs.get("enterprise_search.host_url")
    retry = 0
    while retry <= retry_count:
        try:
            workplace_search = WorkplaceSearch(
                enterprise_search_host,
                http_auth=configs.get(
                    "workplace_search.access_token"
                ),
            )
            response = workplace_search.get_content_source(
                content_source_id=configs.get(
                    "workplace_search.source_id"
                )
            )
            if response:
                assert True
                break
        except Exception as exception:
            print_and_log(
                logger,
                "exception",
                "[Fail] Error while connecting to the workplace host %s. Retry Count: %s. Error: %s"
                % (
                    enterprise_search_host,
                    retry,
                    exception,
                ),
            )
            # This condition is to avoid sleeping for the last time
            if retry < retry_count:
                time.sleep(2 ** retry)
            else:
                assert False, "Error while connecting to the Enterprise Search at %s" % (
                    enterprise_search_host)
            retry += 1

    logger.info("Workplace connectivity tests completed..")


@pytest.mark.ingestion
def test_ingestion(settings):
    """ Tests the successful ingestion and deletion of a sample document to the Workplace search
    """
    configs, retry_count = settings
    enterprise_search_host = configs.get("enterprise_search.host_url")
    logger.info("Starting Workplace ingestion tests..")
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
                http_auth=configs.get("workplace_search.access_token"), content_source_id=configs.get("workplace_search.source_id"),
                documents=document,
            )
            logger.info(
                "Successfully indexed a dummy document with id 1234 in the Workplace")
            break
        except Exception as exception:
            print_and_log(
                logger,
                "exception",
                "[Fail] Error while ingesting document to the workplace host %s. Retry Count: %s. Error: %s"
                % (
                    enterprise_search_host,
                    retry,
                    exception,
                ),
            )
            # This condition is to avoid sleeping for the last time
            if retry < retry_count:
                time.sleep(2 ** retry)
            else:
                assert False, "Error while connecting to the Enterprise Search at %s" % (
                    enterprise_search_host)
            retry += 1

    if response:
        logger.info(
            "Attempting to delete the dummy document 1234 from the Workplace for cleanup"
        )
        retry = 0
        while retry <= retry_count:
            try:
                response = workplace_search.delete_documents(
                    http_auth=configs.get(
                        "workplace_search.access_token"
                    ),
                    content_source_id=configs.get(
                        "workplace_search.source_id"
                    ),
                    document_ids=[1234],
                )
                logger.info(
                    "Successfully deleted the dummy document with id 1234 from the Workplace"
                )
                if response:
                    assert True
                    break
            except Exception as exception:
                print_and_log(
                    logger,
                    "exception",
                    "[Fail] Error while deleting document id 1234 from the workplace host %s. Retry Count: %s. Error: %s"
                    % (
                        enterprise_search_host,
                        retry,
                        exception,
                    ),
                )
                # This condition is to avoid sleeping for the last time
                if retry < retry_count:
                    time.sleep(2 ** retry)
                else:
                    assert False, "Error while connecting to the Enterprise Search at %s" % (
                        enterprise_search_host)
                retry += 1

    logger.info("Workplace ingestion tests completed..")
