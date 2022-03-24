#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#
"""This module allows to run a full sync against a Sharepoint Server instance.

It will attempt to sync absolutely all documents that are available in the
third-party system and ingest them into Enterprise Search instance."""
from .base_command import BaseCommand
from .sync_sharepoint import init_sharepoint_sync
from .connector_queue import ConnectorQueue
from .sync_enterprise_search import init_enterprise_search_sync
from multiprocessing import Process


class FullSyncCommand(BaseCommand):
    """This class start execution of fullsync feature."""

    def execute(self):
        """This function execute the start function."""
        config = self.config
        logger = self.logger
        workplace_search_client = self.workplace_search_client
        sharepoint_client = self.sharepoint_client

        queue = ConnectorQueue()
        producer = Process(
            name="producer",
            target=init_sharepoint_sync,
            args=("full", config, logger, workplace_search_client, sharepoint_client, queue),
        )
        producer.start()

        consumer = Process(
            name="consumer",
            target=init_enterprise_search_sync,
            args=(config, logger, workplace_search_client, queue),
        )
        consumer.start()

        producer.join()
        consumer.join()
