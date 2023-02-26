class Item(dict):
    def __init__(self, item_id=None, item_name=None):
        if item_id is None and item_name is None:
            raise ValueError("At least one of 'item_id' and 'item_name' is required.")
        if item_id is not None:
            self.set_parameter("item_id", str(item_id))
        if item_name is not None:
            self.set_parameter("item_name", item_name)

    def set_parameter(self, name, value):
        self[name] = value