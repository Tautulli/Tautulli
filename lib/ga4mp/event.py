from ga4mp.item import Item

class Event(dict):
    def __init__(self, name):
        self.set_event_name(name)

    def set_event_name(self, name):
        if len(name) > 40:
            raise ValueError("Event name cannot exceed 40 characters.")
        self["name"] = name

    def get_event_name(self):
        return self.get("name")

    def set_event_param(self, name, value):
        # Series of checks to comply with GA4 event collection limits: https://support.google.com/analytics/answer/9267744
        if len(name) > 40:
            raise ValueError("Event parameter name cannot exceed 40 characters.")
        if name in ["page_location", "page_referrer", "page_title"] and len(str(value)) > 300:
            raise ValueError("Event parameter value for page info cannot exceed 300 characters.")
        if name not in ["page_location", "page_referrer", "page_title"] and len(str(value)) > 100:
            raise ValueError("Event parameter value cannot exceed 100 characters.")
        if "params" not in self.keys():
            self["params"] = {}
        if len(self["params"]) >= 100:
            raise RuntimeError("Event cannot contain more than 100 parameters.")
        self["params"][name] = value

    def get_event_params(self):
        return self.get("params")

    def delete_event_param(self, name):
        # Since only 25 event parameters are allowed, this will allow the user to delete a parameter if necessary.
        self["params"].pop(name, None)

    def create_new_item(self, item_id=None, item_name=None):
        return Item(item_id=item_id, item_name=item_name)

    def add_item_to_event(self, item):
        if not isinstance(item, dict):
            raise ValueError("'item' must be an instance of a dictionary.")
        if "items" not in self["params"].keys():
            self.set_event_param("items", [])
        self["params"]["items"].append(item)