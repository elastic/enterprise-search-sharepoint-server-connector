#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#
import threading

from .checkpointing import Checkpoint
from .utils import split_documents_into_equal_chunks

BATCH_SIZE = 100
CONNECTION_TIMEOUT = 1000


class SyncEnterpriseSearch:
    """This class allows ingesting documents to Elastic Enterprise Search."""

    def __init__(self, config, logger, workplace_search_custom_client, queue):
        self.config = config
        self.logger = logger
        self.workplace_search_custom_client = workplace_search_custom_client
        self.queue = queue

    def index_documents(self, documents):
        """This method indexes the documents to the Enterprise Search.
        :param documents: documents to be indexed
        """
        total_documents_indexed = 0
        if documents:
            responses = self.workplace_search_custom_client.index_documents(
                documents=documents,
                timeout=CONNECTION_TIMEOUT,
            )
            for response in responses["results"]:
                if not response["errors"]:
                    total_documents_indexed += 1
                else:
                    self.logger.error(
                        "Error while indexing %s. Error: %s"
                        % (response["id"], response["errors"])
                    )
            self.logger.info(
                f"[{threading.get_ident()}] Successfully indexed {total_documents_indexed} documents to the workplace"
            )

    def perform_sync(self):
        """Pull documents from the queue and synchronize it to the Enterprise Search."""
        try:
            checkpoint = Checkpoint(self.config, self.logger)
            signal_open = True
            while signal_open:
                documents_to_index = []
                while len(documents_to_index) < BATCH_SIZE:
                    documents = self.queue.get()
                    if documents.get("type") == "signal_close":
                        self.logger.info(
                            f"Found an end signal in the queue. Closing Thread ID {threading.get_ident()}"
                        )
                        signal_open = False
                        break
                    elif documents.get("type") == "checkpoint":
                        checkpoint.set_checkpoint(
                            documents.get("data")[0],
                            documents.get("data")[1],
                            documents.get("data")[2],
                        )
                        break
                    else:
                        documents_to_index.extend(documents.get("data"))
                # This loop is to ensure if the last document fetched from the queue exceeds the size of
                # documents_to_index to more than the permitted chunk size, then we split the documents as per the limit
                for chunk in split_documents_into_equal_chunks(
                    documents_to_index, BATCH_SIZE
                ):
                    self.index_documents(chunk)
        except Exception as exception:
            self.logger.error(
                f"Error while indexing the documents to the Enterprise Search. Error {exception}"
            )
