import json
import os

IDS_PATH = os.path.join(os.path.dirname(__file__), 'doc_id.json')


class LocalStorage:
    """This class contains all the methods to do operations on doc_id json file
    """

    def __init__(self, logger):
        self.logger = logger

    def load_storage(self):
        """This method fetches the contents of doc_id.json(local ids storage)
        """
        try:
            with open(IDS_PATH, encoding='utf-8') as ids_file:
                try:
                    return json.load(ids_file)
                except ValueError as exception:
                    self.logger.exception(
                        f"Error while parsing the json file of the ids store from path: {IDS_PATH}. Error: {exception}"
                    )
        except FileNotFoundError:
            self.logger.debug("Local storage for ids was not found.")
            return {"global_keys": {}}

    def update_storage(self, ids):
        """This method is used to update the ids stored in doc_id.json file
            :param ids: updated ids to be stored in the doc_id.json file
        """
        with open(IDS_PATH, "w", encoding='utf-8') as ids_file:
            try:
                json.dump(ids, ids_file, indent=4)
            except ValueError as exception:
                self.logger.exception(
                    f"Error while updating the doc_id json file. Error: {exception}"
                )
