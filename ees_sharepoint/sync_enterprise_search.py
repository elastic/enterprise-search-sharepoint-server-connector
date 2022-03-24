#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#
from multiprocessing.pool import ThreadPool
from .utils import split_documents_into_equal_chunks
from .checkpointing import Checkpoint

BATCH_SIZE = 100


class SyncEnterpriseSearch:
    """This class allows ingesting documents to Elastic Enterprise Search."""

    def __init__(self, config, logger, workplace_search_client, queue):
        self.config = config
        self.logger = logger
        self.workplace_search_client = workplace_search_client
        self.ws_source = config.get_value("workplace_search.source_id")
        self.enterprise_search_thread_count = config.get_value("enterprise_search_sync_thread_count")
        self.thread_pool = ThreadPool(self.enterprise_search_thread_count)
        self.queue = queue

    def index_documents(self, documents):
        """This method indexes the documents to the Enterprise Search.
        :param documents: documents to be indexed
        """
        total_documents_indexed = 0
        if documents:
            responses = self.workplace_search_client.index_documents(
                content_source_id=self.ws_source, documents=documents
            )
            for response in responses["results"]:
                if not response["errors"]:
                    total_documents_indexed += 1
                else:
                    self.logger.error("Error while indexing %s. Error: %s" % (response["id"], response["errors"]))
        self.logger.info("Successfully indexed %s documents to the workplace" % (total_documents_indexed))

    def perform_sync(self):
        """Pull documents from the queue and synchronize it to the Enterprise Search."""
        checkpoint = Checkpoint(self.config, self.logger)
        signal_open = True
        while signal_open:
            for _ in range(0, self.enterprise_search_thread_count):
                documents_to_index = []
                while len(documents_to_index) < BATCH_SIZE:
                    documents = self.queue.get()
                    if documents.get("type") == "signal_close":
                        signal_open = False
                        break
                    elif documents.get("type") == "checkpoint":
                        checkpoint.set_checkpoint(
                            documents.get("data")[0], documents.get("data")[1], documents.get("data")[2]
                        )
                        break
                    else:
                        documents_to_index.extend(documents.get("data"))
                for chunk in split_documents_into_equal_chunks(documents_to_index, BATCH_SIZE):
                    self.thread_pool.apply_async(self.index_documents, (chunk,))
                if not signal_open:
                    break
        self.thread_pool.close()
        self.thread_pool.join()


def init_enterprise_search_sync(config, logger, workplace_search_client, queue):
    """Runs the indexing logic
    :param config: instance of Configuration class
    :param logger: instance of Logger class
    :param workplace_search_client: instance of WorkplaceSearch
    :param queue: Shared queue to push the objects fetched from SharePoint
    """
    indexer = SyncEnterpriseSearch(config, logger, workplace_search_client, queue)
    indexer.perform_sync()
