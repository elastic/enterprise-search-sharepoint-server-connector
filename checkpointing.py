import os
import json

CHECKPOINT_PATH = os.path.join(os.getcwd(), 'checkpoint.json')


class Checkpoint:

    def __init__(self, logger, data):
        self.logger = logger
        self.data = data

    def get_checkpoint(self):
        self.logger.info(
            'Fetching the checkpoint details from the checkpoint file: {}'.format(CHECKPOINT_PATH))

        if os.path.exists(CHECKPOINT_PATH) and os.path.getsize(CHECKPOINT_PATH) > 0:
            self.logger.info(
                'Checkpoint file exists and has contents, hence considering the checkpoint time instead of start_time and end_time')
            with open(CHECKPOINT_PATH, 'r') as checkpoint_store:
                try:
                    checkpoint = json.load(checkpoint_store)
                except Exception as exception:
                    self.logger.error('Error while parsing the json file of the checkpoint store from path: {}. Error: {}'.format(
                        CHECKPOINT_PATH, exception))
                    self.logger.info(
                        'Considering the start_time and end_time from the configuration file')
                    checkpoint = {"start_time": self.data.get(
                        'start_time'), "end_time": self.data.get('end_time')}

                if not checkpoint.get('start_time'):
                    self.logger.info(
                        'The checkpoint file is present but it does not contain the start_time, hence considering the start_time and end_time from the configuration file instead of the last successful fetch time')
                    checkpoint = {"start_time": self.data.get(
                        'start_time'), "end_time": self.data.get('end_time')}

        else:
            self.logger.info(
                'Checkpoint file does not exist at {}, considering the start_time and end_time from the configuration file'.format(CHECKPOINT_PATH))
            checkpoint = {
                "start_time": self.data.get('start_time'), "end_time": self.data.get('end_time')}

        start_time = checkpoint.get('start_time')
        end_time = checkpoint.get('end_time')
        self.logger.info(
            'Contents of the start_time: {} and end_time: {}'.format(start_time, end_time))

        if start_time and not end_time:
            query = "?$filter=Created ge datetime\'{}\'".format(start_time)
        elif not start_time and end_time:
            query = "?$filter=Created le datetime\'{}\'".format(end_time)
        elif start_time and end_time:
            query = "?$filter= (Created ge datetime\'{}\') and (Created le datetime\'{}\')".format(
                start_time, end_time)
        else:
            query = "?"

        return query

    def set_checkpoint(self, checkpoint_content):
        self.logger.info('Setting the checkpoint contents: {} to the checkpoint path:{}'.format(
            str(checkpoint_content), CHECKPOINT_PATH))
        checkpoint = {}
        with open(CHECKPOINT_PATH, 'wr') as checkpoint_store:
            try:
                checkpoint = json.load(checkpoint_store)
            except Exception as exception:
                self.logger.warn(
                    'Error while updating the existing checkpoint json file. Adding the new content directly instead of updating. Error: {}'.format(exception))
            checkpoint.update(checkpoint_content)
            json.dump(checkpoint, checkpoint_store, indent=4)
        self.logger.info('Successfully saved the checkpoint')
