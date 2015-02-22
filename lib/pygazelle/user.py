

class InvalidUserException(Exception):
    pass

class User(object):
    """
    This class represents a User, whether your own or someone else's. It is created knowing only its ID. To reduce
    API accesses, load information using User.update_index_data() or User.update_user_data only as needed.
    """
    def __init__(self, id, parent_api):
        self.id = id
        self.parent_api = parent_api
        self.username = None
        self.authkey = None
        self.passkey = None
        self.avatar = None
        self.is_friend = None
        self.profile_text = None
        self.notifications = None
        self.stats = None
        self.ranks = None
        self.personal = None
        self.community = None

        self.parent_api.cached_users[self.id] = self # add self to cache of known User objects

    def update_index_data(self):
        """
        Calls 'index' API action, then updates this User objects information with it.
        NOTE: Only call if this user is the logged-in user...throws InvalidUserException otherwise.
        """
        response = self.parent_api.request(action='index')
        self.set_index_data(response)

    def set_index_data(self, index_json_response):
        """
        Takes parsed JSON response from 'index' action on api, and updates the available subset of user information.
        ONLY callable if this User object represents the currently logged in user. Throws InvalidUserException otherwise.
        """
        if self.id != index_json_response['id']:
            raise InvalidUserException("Tried to update non-logged-in User's information from 'index' API call." +
                                       " Should be %s, got %s" % (self.id, index_json_response['id']) )

        self.username = index_json_response['username']

        self.authkey = index_json_response['authkey']
        self.passkey = index_json_response['passkey']
        self.notifications = index_json_response['notifications']
        if self.stats:
            self.stats = dict(self.stats.items() + index_json_response['userstats'].items()) # merge in new info
        else:
            self.stats = index_json_response['userstats']

        # cross pollinate some data that is located in multiple locations in API
        if self.personal:
            self.personal['class'] = self.stats['class']
            self.personal['passkey'] = self.passkey


    def update_user_data(self):
        response = self.parent_api.request(action='user', id=self.id)
        self.set_user_data(response)

    def set_user_data(self, user_json_response):
        """
        Takes parsed JSON response from 'user' action on api, and updates relevant user information.
        To avoid problems, only pass in user data from an API call that used this user's ID as an argument.
        """
        if self.username and self.username != user_json_response['username']:
            raise InvalidUserException("Tried to update a user's information from a 'user' API call with a different username." +
                                       " Should be %s, got %s" % (self.username, user_json_response['username']) )

        self.username = user_json_response['username']
        self.avatar = user_json_response['avatar']
        self.is_friend = user_json_response['isFriend']
        self.profile_text = user_json_response['profileText']
        if self.stats:
            self.stats = dict(self.stats.items() + user_json_response['stats'].items()) # merge in new info
        else:
            self.stats = user_json_response['stats']
        self.ranks = user_json_response['ranks']
        self.personal = user_json_response['personal']
        self.community = user_json_response['community']

        # cross pollinate some data that is located in multiple locations in API
        self.stats['class'] = self.personal['class']
        self.passkey = self.personal['passkey']

    def set_search_result_data(self, search_result_item):
        """
        Takes a single user result item from a 'usersearch' API call and updates user info.
        """
        if self.id != search_result_item['userId']:
            raise InvalidUserException("Tried to update existing user with another user's search result data (IDs don't match).")

        self.username = search_result_item['username']

        if not self.personal:
            self.personal = {}

        self.personal['donor'] = search_result_item['donor']
        self.personal['warned'] = search_result_item['warned']
        self.personal['enabled'] = search_result_item['enabled']
        self.personal['class'] = search_result_item['class']

    def __repr__(self):
        return "User: %s - ID: %s" % (self.username, self.id)
