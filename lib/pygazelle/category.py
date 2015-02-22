class InvalidCategoryException(Exception):
    pass

class Category(object):
    def __init__(self, id, parent_api):
        self.id = id
        self.parent_api = parent_api
        self.name = None

        self.parent_api.cached_categories[self.id] = self # add self to cache of known Category objects

    def __repr__(self):
        return "Category: %s - id: %s" % (self.name, self.id)