#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#
"""Checkpointing module allows to start sync from point in time.

Checkpointing module contains functions that allow to manage checkpoints,
such as set a checkpoint and get a checkpoint.

Checkpoints help with incremental or interrupted synchronizations,
remembering the last moment of time when sync successfully finshed,
so that later next sync can continue from that place.
"""
import os
import json

CHECKPOINT_PATH = os.path.join(os.path.dirname(__file__), "checkpoint.json")

class Checkpoint:
    """Checkpoints class is responsible for checkpoint operations.

    This class allows to get and set checkpoints, storing them in
    file system."""
    def __init__(self, logger, config):
        self.logger = logger
        self.config = config

    def get_checkpoint(self, collection, current_time):
        """This method fetches the checkpoint from the checkpoint file in
        the local storage. If the file does not exist, it takes the
        checkpoint details from the configuration file.
        :param collection: collection name
        :param current_time: current time"""
        self.logger.info(
            "Fetching the checkpoint details from the checkpoint file: %s"
            % CHECKPOINT_PATH
        )

        if os.path.exists(CHECKPOINT_PATH) and os.path.getsize(CHECKPOINT_PATH) > 0:
            self.logger.info(
                "Checkpoint file exists and has contents, hence considering the checkpoint time instead of start_time and end_time"
            )
            with open(CHECKPOINT_PATH, "r", encoding="utf-8") as checkpoint_store:
                try:
                    checkpoint_list = json.load(checkpoint_store)

                    if not checkpoint_list.get(collection):
                        self.logger.info(
                            f"""Checkpoint file is present but does not contain start_time \
                            for the collection #{collection}. Using start_time and end_time \
                            from the configuration file instead of the last successful fetch time"""
                        )
                        start_time = self.config.get_value("start_time")
                        end_time = self.config.get_value("end_time")
                    else:
                        start_time = checkpoint_list.get(collection)
                        end_time = current_time
                except ValueError as exception:
                    self.logger.exception(
                        "Error while parsing the json file of the checkpoint store from path: %s. Error: %s"
                        % (CHECKPOINT_PATH, exception)
                    )
                    self.logger.info(
                        "Considering the start_time and end_time from the configuration file"
                    )
                    start_time = self.config.get_value("start_time")
                    end_time = self.config.get_value("end_time")

        else:
            self.logger.info(
                "Checkpoint file does not exist at %s, considering the start_time and end_time from the configuration file"
                % CHECKPOINT_PATH
            )
            start_time = self.config.get_value("start_time")
            end_time = self.config.get_value("end_time")

        self.logger.info(
            "Contents of the start_time: %s and end_time: %s for collection %s",
            start_time,
            end_time,
            collection,
        )
        return start_time, end_time

    def set_checkpoint(self, collection, current_time, index_type):
        """This method updates the existing checkpoint json file or creates
        a new checkpoint json file in case it is not present
        :param collection: collection name
        :param current_time: current time"""
        if os.path.exists(CHECKPOINT_PATH) and os.path.getsize(CHECKPOINT_PATH) > 0:
            self.logger.info(
                f"""Setting the checkpoint contents: {current_time} \
                    for the collection {collection} \
                    to the checkpoint path:{CHECKPOINT_PATH}"""
            )
            with open(CHECKPOINT_PATH, "r", encoding="utf-8") as checkpoint_store:
                try:
                    checkpoint_list = json.load(checkpoint_store)
                    checkpoint_list[collection] = current_time
                except ValueError as exception:
                    self.logger.exception(
                        "Error while parsing the json file of the checkpoint store from path: %s. Error: %s"
                        % (CHECKPOINT_PATH, exception)
                    )

        else:
            if index_type == "incremental":
                checkpoint_time = self.config.get_value("end_time")
            else:
                checkpoint_time = current_time
            self.logger.info(
                "Setting the checkpoint contents: %s for the collection %s to the checkpoint path:%s"
                % (checkpoint_time, collection, CHECKPOINT_PATH)
            )
            checkpoint_list = {collection: checkpoint_time}

        with open(CHECKPOINT_PATH, "w",encoding="utf-8") as checkpoint_store:
            try:
                json.dump(checkpoint_list, checkpoint_store, indent=4)
            except ValueError as exception:
                self.logger.exception(
                    "Error while updating the existing checkpoint json file. Adding the new content directly instead of updating. Error: %s"
                    % exception
                )

        self.logger.info("Successfully saved the checkpoint")
