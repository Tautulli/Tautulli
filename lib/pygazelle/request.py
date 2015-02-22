class InvalidRequestException(Exception):
    pass

class Request(object):
    def __init__(self, id, parent_api):
        self.id = id
        self.parent_api = parent_api
        self.category = None
        self.title = None
        self.year = None
        self.time_added = None
        self.votes = None
        self.bounty = None

        self.parent_api.cached_requests[self.id] = self # add self to cache of known Request objects

    def set_data(self, request_item_json_data):
        if self.id != request_item_json_data['requestId']:
            raise InvalidRequestException("Tried to update a Request's information from a request JSON item with a different id." +
                                         " Should be %s, got %s" % (self.id, request_item_json_data['requestId']) )
        self.category = self.parent_api.get_category(request_item_json_data['categoryId'])
        self.title = request_item_json_data['title']
        self.year = request_item_json_data['year']
        self.time_added = request_item_json_data['timeAdded']
        self.votes = request_item_json_data['votes']
        self.bounty = request_item_json_data['bounty']

    def __repr__(self):
        return "Request: %s - ID: %s" % (self.title, self.id)