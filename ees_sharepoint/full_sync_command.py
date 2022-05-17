#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#
"""This module allows to run a full sync against a Sharepoint Server instance.

It will attempt to sync absolutely all documents that are available in the
third-party system and ingest them into Enterprise Search instance."""
from datetime import datetime

from .base_command import BaseCommand
from .connector_queue import ConnectorQueue
from .sync_enterprise_search import SyncEnterpriseSearch
from .sync_sharepoint import SyncSharepoint
from .utils import split_date_range_into_chunks


class FullSyncCommand(BaseCommand):
    """This class start execution of fullsync feature."""

    def start_producer(self, queue):
        """This method starts async calls for the producer which is responsible for fetching documents from
        the SharePoint and pushing them in the shared queue
        :param queue: Shared queue to fetch the stored documents
        """
        self.logger.debug("Starting the full indexing..")
        current_time = (datetime.utcnow()).strftime("%Y-%m-%dT%H:%M:%SZ")

        thread_count = self.config.get_value("sharepoint_sync_thread_count")

        start_time, end_time = self.config.get_value("start_time"), current_time
        try:
            sync_sharepoint = SyncSharepoint(
                self.config,
                self.logger,
                self.workplace_search_custom_client,
                self.sharepoint_client,
                start_time,
                end_time,
                queue,
            )
            datelist = split_date_range_into_chunks(
                start_time,
                end_time,
                thread_count,
            )
            for collection in self.config.get_value("sharepoint.site_collections"):
                storage_with_collection = self.local_storage.get_storage_with_collection(collection)
                self.logger.info(
                    "Starting to index all the objects configured in the object field: %s"
                    % (str(self.config.get_value("objects")))
                )

                ids = storage_with_collection["global_keys"][collection]
                storage_with_collection["global_keys"][collection] = sync_sharepoint.fetch_records_from_sharepoint(self.producer, datelist, thread_count, ids, collection)

                queue.put_checkpoint(collection, end_time, "full")

            enterprise_thread_count = self.config.get_value("enterprise_search_sync_thread_count")
            for _ in range(enterprise_thread_count):
                queue.end_signal()
        except Exception as exception:
            self.logger.exception(f"Error while fetching the objects . Error {exception}")
            raise exception
        self.local_storage.update_storage(storage_with_collection)

    def start_consumer(self, queue):
        """This method starts async calls for the consumer which is responsible for indexing documents to the
        Enterprise Search
        :param queue: Shared queue to fetch the stored documents
        """
        thread_count = self.config.get_value("enterprise_search_sync_thread_count")
        sync_es = SyncEnterpriseSearch(self.config, self.logger, self.workplace_search_custom_client, queue)

        self.consumer(thread_count, sync_es.perform_sync)

    def execute(self):
        """This function execute the start function."""
        queue = ConnectorQueue(self.logger)

        self.start_producer(queue)
        self.start_consumer(queue)
