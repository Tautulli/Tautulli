import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class BaseStore(dict):
    def __init__(self):
        self.update([("user_properties", {}),("session_parameters", {})])

    def save(self):
        raise NotImplementedError("Subclass should be using this function, but it was called through the base class instead.")

    def _check_exists(self, key):
        # Helper function to make sure a key exists before trying to work with values within it.
        if key not in self.keys():
            self[key] = {}

    def _set(self, param_type, name, value):
        # Helper function to set a single parameter (user or session or other).
        self._check_exists(key=param_type)
        self[param_type][name] = value

    def _get_one(self, param_type, name):
        # Helper function to get a single parameter value (user or session).
        self._check_exists(key=param_type)
        return self[param_type].get(name, None)

    def _get_all(self, param_type=None):
        # Helper function to get all user or session parameters - or the entire dictionary if not specified.
        if param_type is not None:
            return self[param_type]
        else:
            return self

    # While redundant, the following make sure the distinction between session and user items is easier for the end user.
    def set_user_property(self, name, value):
        self._set(param_type="user_properties", name=name, value=value)

    def get_user_property(self, name):
        return self._get_one(param_type="user_properties", name=name)

    def get_all_user_properties(self):
        return self._get_all(param_type="user_properties")

    def clear_user_properties(self):
        self["user_properties"] = {}

    def set_session_parameter(self, name, value):
        self._set(param_type="session_parameters", name=name, value=value)

    def get_session_parameter(self, name):
        return self._get_one(param_type="session_parameters", name=name)

    def get_all_session_parameters(self):
        return self._get_all(param_type="session_parameters")

    def clear_session_parameters(self):
        self["session_parameters"] = {}

    # Similar functions for other items the user wants to store that don't fit the other two categories.
    def set_other_parameter(self, name, value):
        self._set(param_type="other", name=name, value=value)

    def get_other_parameter(self, name):
        return self._get_one(param_type="other", name=name)

    def get_all_other_parameters(self):
        return self._get_all(param_type="other")

    def clear_other_parameters(self):
        self["other"] = {}

class DictStore(BaseStore):
    # Class for working with dictionaries that persist for the life of the class.
    def __init__(self, data: dict = None):
        super().__init__()
        if data:
            self.update(data)

    def save(self):
        # Give the user back what's in the dictionary so they can decide how to save it.
        self._get_all()

class FileStore(BaseStore):
    # Class for working with dictionaries that get saved to a JSON file.
    def __init__(self, data_location: str = None):
        super().__init__()
        self.data_location = data_location
        try:
            self._load_file(data_location)
        except:
            logger.info(f"Failed to find file at location: {data_location}")

    def _load_file(self):
        # Function to get data from the object's initialized location.
        # If the provided or stored data_location exists, read the file and overwrite the object's contents.
        if Path(self.data_location).exists():
            with open(self.data_location, "r") as json_file:
                self = json.load(json_file)
        # If the data_location doesn't exist, try to create a new starter JSON file at the location given.
        else:
            starter_dict = '{"user_properties":{}, "session_parameters":{}}'
            starter_json = json.loads(starter_dict)
            Path(self.data_location).touch()
            with open(self.data_location, "w") as json_file:
                json.dumps(starter_json, json_file)

    def save(self):
        # Function to save the current dictionary to a JSON file at the object's initialized location.
        try:
            with open(self.data_location, "w") as outfile:
                json.dump(self, outfile)
        except:
            logger.info(f"Failed to save file at location: {self.data_location}")