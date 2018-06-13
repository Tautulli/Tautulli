from collections import namedtuple
import re
try:
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse

from twitter.twitter_utils import enf_type

EndpointRateLimit = namedtuple('EndpointRateLimit',
                               ['limit', 'remaining', 'reset'])

ResourceEndpoint = namedtuple('ResourceEndpoint', ['regex', 'resource'])


GEO_ID_PLACE_ID = ResourceEndpoint(re.compile(r'/geo/id/\d+'), "/geo/id/:place_id")
SAVED_SEARCHES_DESTROY_ID = ResourceEndpoint(re.compile(r'/saved_searches/destroy/\d+'), "/saved_searches/destroy/:id")
SAVED_SEARCHES_SHOW_ID = ResourceEndpoint(re.compile(r'/saved_searches/show/\d+'), "/saved_searches/show/:id")
STATUSES_RETWEETS_ID = ResourceEndpoint(re.compile(r'/statuses/retweets/\d+'), "/statuses/retweets/:id")
STATUSES_SHOW_ID = ResourceEndpoint(re.compile(r'/statuses/show'), "/statuses/show/:id")
USERS_SHOW_ID = ResourceEndpoint(re.compile(r'/users/show'), "/users/show/:id")
USERS_SUGGESTIONS_SLUG = ResourceEndpoint(re.compile(r'/users/suggestions/\w+$'), "/users/suggestions/:slug")
USERS_SUGGESTIONS_SLUG_MEMBERS = ResourceEndpoint(re.compile(r'/users/suggestions/.+/members'), "/users/suggestions/:slug/members")

NON_STANDARD_ENDPOINTS = [
    GEO_ID_PLACE_ID,
    SAVED_SEARCHES_DESTROY_ID,
    SAVED_SEARCHES_SHOW_ID,
    STATUSES_RETWEETS_ID,
    STATUSES_SHOW_ID,
    USERS_SHOW_ID,
    USERS_SUGGESTIONS_SLUG,
    USERS_SUGGESTIONS_SLUG_MEMBERS,
]


class RateLimit(object):

    """ Object to hold the rate limit status of various endpoints for
    the twitter.Api object.

    This object is generally attached to the API as Api.rate_limit, but is not
    created until the user makes a method call that uses _RequestUrl() or calls
    Api.InitializeRateLimit(), after which it get created and populated with
    rate limit data from Twitter.

    Calling Api.InitializeRateLimit() populates the object with all of the
    rate limits for the endpoints defined by Twitter; more info is available
    here:

        https://dev.twitter.com/rest/public/rate-limits

        https://dev.twitter.com/rest/public/rate-limiting

        https://dev.twitter.com/rest/reference/get/application/rate_limit_status

    Once a resource (i.e., an endpoint) has been requested, Twitter's response
    will contain the current rate limit status as part of the headers, i.e.::

        x-rate-limit-limit
        x-rate-limit-remaining
        x-rate-limit-reset

    ``limit`` is the generic limit for that endpoint, ``remaining`` is how many
    more times you can make a call to that endpoint, and ``reset`` is the time
    (in seconds since the epoch) until remaining resets to its default for that
    endpoint.

    Generally speaking, each endpoint has a 15-minute reset time and endpoints
    can either make 180 or 15 requests per window. According to Twitter, any
    endpoint not defined in the rate limit chart or the response from a GET
    request to ``application/rate_limit_status.json`` should be assumed to be
    15 requests per 15 minutes.

    """

    def __init__(self, **kwargs):
        """ Instantiates the RateLimitObject. Takes a json dict as
        kwargs and maps to the object's dictionary. So for something like:

        {"resources": {
                "help": {
                    /help/privacy": {
                        "limit": 15,
                        "remaining": 15,
                        "reset": 1452254278
                    }
                }
            }
        }

        the RateLimit object will have an attribute 'resources' from which you
        can perform a lookup like:

            api.rate_limit.get('help').get('/help/privacy')

        and a dictionary of limit, remaining, and reset will be returned.

        """
        self.__dict__['resources'] = {}
        self.__dict__.update(kwargs)

    @staticmethod
    def url_to_resource(url):
        """ Take a fully qualified URL and attempts to return the rate limit
        resource family corresponding to it. For example:

            >>> RateLimit.url_to_resource('https://api.twitter.com/1.1/statuses/lookup.json?id=317')
            >>> '/statuses/lookup'

        Args:
            url (str): URL to convert to a resource family.

        Returns:
            string: Resource family corresponding to the URL.
        """
        resource = urlparse(url).path.replace('/1.1', '').replace('.json', '')
        for non_std_endpoint in NON_STANDARD_ENDPOINTS:
            if re.match(non_std_endpoint.regex, resource):
                return non_std_endpoint.resource
        return resource

    def set_unknown_limit(self, url, limit, remaining, reset):
        return self.set_limit(url, limit, remaining, reset)

    def set_limit(self, url, limit, remaining, reset):
        """ If a resource family is unknown, add it to the object's
        dictionary. This is to deal with new endpoints being added to
        the API, but not necessarily to the information returned by
        ``/account/rate_limit_status.json`` endpoint.

        For example, if Twitter were to add an endpoint
        ``/puppies/lookup.json``, the RateLimit object would create a resource
        family ``puppies`` and add ``/puppies/lookup`` as the endpoint, along
        with whatever limit, remaining hits available, and reset time would be
        applicable to that resource+endpoint pair.

        Args:
            url (str):
                URL of the endpoint being fetched.
            limit (int):
                Max number of times a user or app can hit the endpoint
                before being rate limited.
            remaining (int):
                Number of times a user or app can access the endpoint
                before being rate limited.
            reset (int):
                Epoch time at which the rate limit window will reset.
        """
        endpoint = self.url_to_resource(url)
        resource_family = endpoint.split('/')[1]
        new_endpoint = {endpoint: {
            "limit": enf_type('limit', int, limit),
            "remaining": enf_type('remaining', int, remaining),
            "reset": enf_type('reset', int, reset)
        }}

        if not self.resources.get(resource_family, None):
            self.resources[resource_family] = {}

        self.__dict__['resources'][resource_family].update(new_endpoint)

        return self.get_limit(url)

    def get_limit(self, url):
        """ Gets a EndpointRateLimit object for the given url.

        Args:
            url (str, optional):
                URL of the endpoint for which to return the rate limit
                status.

        Returns:
            namedtuple: EndpointRateLimit object containing rate limit
            information.
        """
        endpoint = self.url_to_resource(url)
        resource_family = endpoint.split('/')[1]

        try:
            family_rates = self.resources.get(resource_family).get(endpoint)
        except AttributeError:
            return EndpointRateLimit(limit=15, remaining=15, reset=0)

        if not family_rates:
            self.set_unknown_limit(url, limit=15, remaining=15, reset=0)
            return EndpointRateLimit(limit=15, remaining=15, reset=0)

        return EndpointRateLimit(family_rates['limit'],
                                 family_rates['remaining'],
                                 family_rates['reset'])
