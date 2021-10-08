from requests.exceptions import RequestException
from sharepoint_client import SharePoint
import argparse
import time
import logger_manager as log
from elastic_enterprise_search import WorkplaceSearch
from configuration import Configuration
from sharepoint_utils import print_and_log
from urllib.parse import urljoin

logger = log.setup_logging("sharepoint_connector_test")


class Tests:
    def __init__(self):
        configuration = Configuration(
            file_name="sharepoint_connector_config.yml", logger=logger
        )
        if not configuration.validate():
            print_and_log(
                logger,
                "error",
                "[Fail] Terminating the tests as the configuration parameters are not valid",
            )
            exit(0)
        self.configs = configuration.get_all_config()
        self.retry_count = int(self.configs.get("retry_count"))

    def test_sharepoint_conn(self):
        """ Tests the connection to the sharepoint server by calling a basic get request to fetch sites in a collection and logs proper messages
        """
        logger.info("Starting SharePoint connectivity tests..")
        sharepoint_client = SharePoint(logger)
        response = sharepoint_client.get(urljoin(self.configs.get("sharepoint.host_url"), "/sites/Connector/_api/web/webs"), query="?")
        if response:
            print_and_log(
                logger,
                "info",
                "[Pass] Successfully connected to the SharePoint server: %s"
                % (self.configs.get("sharepoint.host_url")),
            )
        else:
            print_and_log(
                logger,
                "error",
                "[Fail] Error connecting to the SharePoint server: %s"
                % (self.configs.get("sharepoint.host_url")),
            )
        logger.info("SharePoint connectivity tests completed..")

    def test_ws_conn(self):
        """ Tests the connection to the Enterprise search host
        """
        logger.info("Starting Workplace connectivity tests..")
        retry = 0
        while retry <= self.retry_count:
            try:
                workplace_search = WorkplaceSearch(
                    self.configs.get("enterprise_search.host_url"),
                    http_auth=self.configs.get(
                        "workplace_search.access_token"
                    ),
                )
                _ = workplace_search.get_content_source(
                    content_source_id=self.configs.get(
                        "workplace_search.source_id"
                    )
                )
                break
            except RequestException as exception:
                print_and_log(
                    logger,
                    "exception",
                    "[Fail] Error while connecting to the workplace host %s. Retry Count: %s. Error: %s"
                    % (
                        self.configs.get("enterprise_search.host_url"),
                        retry,
                        exception,
                    ),
                )
                # This condition is to avoid sleeping for the last time
                if retry < self.retry_count:
                    time.sleep(2 ** retry)
                else:
                    return
                retry += 1

        print_and_log(
            logger,
            "info",
            "[Pass] Successfully connected to the Workplace server: %s"
            % (self.configs.get("enterprise_search.host_url")),
        )
        logger.info("Workplace connectivity tests completed..")

    def test_ingestion(self):
        """ Tests the successful ingestion of a sample document to the Workplace search 
        """
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
        workplace_search = WorkplaceSearch(
            self.configs.get("enterprise_search.host_url")
        )

        retry = 0
        while retry <= self.retry_count:
            try:
                response = workplace_search.index_documents(
                    http_auth=self.configs.get(
                        "workplace_search.access_token"
                    ),
                    content_source_id=self.configs.get(
                        "workplace_search.source_id"
                    ),
                    documents=document,
                )
                logger.info(
                    "Successfully indexed a dummy document with id 1234 in the Workplace"
                )
                break
            except Exception as exception:
                print_and_log(
                    logger,
                    "exception",
                    "[Fail] Error while ingesting document to the workplace host %s. Retry Count: %s. Error: %s"
                    % (
                        self.configs.get("enterprise_search.host_url"),
                        retry,
                        exception,
                    ),
                )
                # This condition is to avoid sleeping for the last time
                if retry < self.retry_count:
                    time.sleep(2 ** retry)
                else:
                    return
                retry += 1

        if response:
            logger.info(
                "Attempting to delete the dummy document 1234 from the Workplace for cleanup"
            )
            retry = 0
            while retry <= self.retry_count:
                try:
                    response = workplace_search.delete_documents(
                        http_auth=self.configs.get(
                            "workplace_search.access_token"
                        ),
                        content_source_id=self.configs.get(
                            "workplace_search.source_id"
                        ),
                        document_ids=[1234],
                    )
                    logger.info(
                        "Successfully deleted the dummy document with id 1234 from the Workplace"
                    )
                    break
                except Exception as exception:
                    print_and_log(
                        logger,
                        "exception",
                        "[Fail] Error while deleting document id 1234 from the workplace host %s. Retry Count: %s. Error: %s"
                        % (
                            self.configs.get("enterprise_search.host_url"),
                            retry,
                            exception,
                        ),
                    )
                    # This condition is to avoid sleeping for the last time
                    if retry < self.retry_count:
                        time.sleep(2 ** retry)
                    else:
                        return
                    retry += 1

        print_and_log(
            logger,
            "info",
            "[Pass] Successfully ingested and cleand up from the Workplace server: %s"
            % (self.configs.get("enterprise_search.host_url")),
        )
        logger.info("Workplace ingestion tests completed..")

    def test_all(self):
        self.test_sharepoint_conn()
        self.test_ws_conn()
        self.test_ingestion()


def start():
    help_text = """Type of the test to run. The possible options for mode are
    'sharepoint' -> To run the connectivity test with the SharePoint server,
    'workplace' -> To run the connectivity test with the Workplace, and
    'ingestion' -> To run the ingestion test with the Workplace
    """
    parser = argparse.ArgumentParser(
        description="Run tests for the SharePoint Connector"
    )
    parser.add_argument("--mode", "-m", required=False, help=help_text)
    mode = parser.parse_args().mode
    test = Tests()
    if not mode:
        test.test_all()
    elif mode.lower() == "workplace":
        test.test_ws_conn()
    elif mode.lower() == "sharepoint":
        test.test_sharepoint_conn()
    elif mode.lower() == "ingestion":
        test.test_ingestion()
    else:
        print_and_log(
            logger,
            "error",
            "[Fail] Invalid argument found. Allowed arguments are sharepoint, workplace, and ingestion, but found %s"
            % (mode),
        )


if __name__ == "__main__":
    start()
