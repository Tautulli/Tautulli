#!/usr/bin/env python

#
#
# Copyright 2007-2016, 2018 The Python-Twitter Developers
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""A library that provides a Python interface to the Twitter API"""
from __future__ import division
from __future__ import print_function

import json
import sys
import gzip
import time
import base64
import re
import logging
import requests
from requests_oauthlib import OAuth1, OAuth2
import io
import warnings
from uuid import uuid4
import os

try:
    # python 3
    from urllib.parse import urlparse, urlunparse, urlencode, quote_plus
    from urllib.request import __version__ as urllib_version
except ImportError:
    from urlparse import urlparse, urlunparse
    from urllib import urlencode, quote_plus
    from urllib import __version__ as urllib_version

from twitter import (
    __version__,
    _FileCache,
    Category,
    DirectMessage,
    List,
    Status,
    Trend,
    User,
    UserStatus,
)

from twitter.ratelimit import RateLimit

from twitter.twitter_utils import (
    calc_expected_status_length,
    is_url,
    parse_media_file,
    enf_type,
    parse_arg_list)

from twitter.error import (
    TwitterError,
    PythonTwitterDeprecationWarning330,
)

if sys.version_info > (3,):
    long = int  # pylint: disable=invalid-name,redefined-builtin

CHARACTER_LIMIT = 280

# A singleton representing a lazily instantiated FileCache.
DEFAULT_CACHE = object()

logger = logging.getLogger(__name__)


class Api(object):
    """A python interface into the Twitter API

    By default, the Api caches results for 1 minute.

    Example usage:

      To create an instance of the twitter.Api class, with no authentication:

        >>> import twitter
        >>> api = twitter.Api()

      To fetch a single user's public status messages, where "user" is either
      a Twitter "short name" or their user id.

        >>> statuses = api.GetUserTimeline(user)
        >>> print([s.text for s in statuses])

      To use authentication, instantiate the twitter.Api class with a
      consumer key and secret; and the oAuth key and secret:

        >>> api = twitter.Api(consumer_key='twitter consumer key',
                              consumer_secret='twitter consumer secret',
                              access_token_key='the_key_given',
                              access_token_secret='the_key_secret')

      To fetch your friends (after being authenticated):

        >>> users = api.GetFriends()
        >>> print([u.name for u in users])

      To post a twitter status message (after being authenticated):

        >>> status = api.PostUpdate('I love python-twitter!')
        >>> print(status.text)
        I love python-twitter!

      There are many other methods, including:

        >>> api.PostUpdates(status)
        >>> api.PostDirectMessage(user, text)
        >>> api.GetUser(user)
        >>> api.GetReplies()
        >>> api.GetUserTimeline(user)
        >>> api.GetHomeTimeline()
        >>> api.GetStatus(status_id)
        >>> api.GetStatuses(status_ids)
        >>> api.DestroyStatus(status_id)
        >>> api.GetFriends(user)
        >>> api.GetFollowers()
        >>> api.GetFeatured()
        >>> api.GetDirectMessages()
        >>> api.GetSentDirectMessages()
        >>> api.PostDirectMessage(user, text)
        >>> api.DestroyDirectMessage(message_id)
        >>> api.DestroyFriendship(user)
        >>> api.CreateFriendship(user)
        >>> api.LookupFriendship(user)
        >>> api.VerifyCredentials()
    """

    DEFAULT_CACHE_TIMEOUT = 60  # cache for 1 minute
    _API_REALM = 'Twitter API'

    def __init__(self,
                 consumer_key=None,
                 consumer_secret=None,
                 access_token_key=None,
                 access_token_secret=None,
                 application_only_auth=False,
                 input_encoding=None,
                 request_headers=None,
                 cache=DEFAULT_CACHE,
                 base_url=None,
                 stream_url=None,
                 upload_url=None,
                 chunk_size=1024 * 1024,
                 use_gzip_compression=False,
                 debugHTTP=False,
                 timeout=None,
                 sleep_on_rate_limit=False,
                 tweet_mode='compat',
                 proxies=None):
        """Instantiate a new twitter.Api object.

        Args:
          consumer_key (str):
            Your Twitter user's consumer_key.
          consumer_secret (str):
            Your Twitter user's consumer_secret.
          access_token_key (str):
            The oAuth access token key value you retrieved
            from running get_access_token.py.
          access_token_secret (str):
            The oAuth access token's secret, also retrieved
            from the get_access_token.py run.
          application_only_auth:
             Use Application-Only Auth instead of User Auth.
             Defaults to False [Optional]
          input_encoding (str, optional):
            The encoding used to encode input strings.
          request_header (dict, optional):
            A dictionary of additional HTTP request headers.
          cache (object, optional):
            The cache instance to use. Defaults to DEFAULT_CACHE.
            Use None to disable caching.
          base_url (str, optional):
            The base URL to use to contact the Twitter API.
            Defaults to https://api.twitter.com.
          stream_url (str, optional):
            The base URL to use for streaming endpoints.
            Defaults to 'https://stream.twitter.com/1.1'.
          upload_url (str, optional):
            The base URL to use for uploads. Defaults to 'https://upload.twitter.com/1.1'.
          chunk_size (int, optional):
            Chunk size to use for chunked (multi-part) uploads of images/videos/gifs.
            Defaults to 1MB. Anything under 16KB and you run the risk of erroring out
            on 15MB files.
          use_gzip_compression (bool, optional):
            Set to True to tell enable gzip compression for any call
            made to Twitter.  Defaults to False.
          debugHTTP (bool, optional):
            Set to True to enable debug output from urllib2 when performing
            any HTTP requests.  Defaults to False.
          timeout (int, optional):
            Set timeout (in seconds) of the http/https requests. If None the
            requests lib default will be used.  Defaults to None.
          sleep_on_rate_limit (bool, optional):
            Whether to sleep an appropriate amount of time if a rate limit is hit for
            an endpoint.
          tweet_mode (str, optional):
            Whether to use the new (as of Sept. 2016) extended tweet mode. See docs for
            details. Choices are ['compatibility', 'extended'].
          proxies (dict, optional):
            A dictionary of proxies for the request to pass through, if not specified
            allows requests lib to use environmental variables for proxy if any.
        """

        # check to see if the library is running on a Google App Engine instance
        # see GAE.rst for more information
        if os.environ:
            if 'APPENGINE_RUNTIME' in os.environ.keys():
                # Adapter ensures requests use app engine's urlfetch
                import requests_toolbelt.adapters.appengine
                requests_toolbelt.adapters.appengine.monkeypatch()
                # App Engine does not like this caching strategy, disable caching
                cache = None

        self.SetCache(cache)
        self._cache_timeout = Api.DEFAULT_CACHE_TIMEOUT
        self._input_encoding = input_encoding
        self._use_gzip = use_gzip_compression
        self._debugHTTP = debugHTTP
        self._shortlink_size = 19
        if timeout and timeout < 30:
            warnings.warn("Warning: The Twitter streaming API sends 30s keepalives, the given timeout is shorter!")
        self._timeout = timeout
        self.__auth = None

        self._InitializeRequestHeaders(request_headers)
        self._InitializeUserAgent()
        self._InitializeDefaultParameters()

        self.rate_limit = RateLimit()
        self.sleep_on_rate_limit = sleep_on_rate_limit
        self.tweet_mode = tweet_mode
        self.proxies = proxies

        if base_url is None:
            self.base_url = 'https://api.twitter.com/1.1'
        else:
            self.base_url = base_url

        if stream_url is None:
            self.stream_url = 'https://stream.twitter.com/1.1'
        else:
            self.stream_url = stream_url

        if upload_url is None:
            self.upload_url = 'https://upload.twitter.com/1.1'
        else:
            self.upload_url = upload_url

        self.chunk_size = chunk_size

        if self.chunk_size < 1024 * 16:
            warnings.warn((
                "A chunk size lower than 16384 may result in too many "
                "requests to the Twitter API when uploading videos. You are "
                "strongly advised to increase it above 16384"))

        if (consumer_key and not
           (application_only_auth or all([access_token_key, access_token_secret]))):
            raise TwitterError({'message': "Missing oAuth Consumer Key or Access Token"})

        self.SetCredentials(consumer_key, consumer_secret, access_token_key, access_token_secret,
                            application_only_auth)

        if debugHTTP:
            try:
                import http.client as http_client  # python3
            except ImportError:
                import httplib as http_client  # python2

            http_client.HTTPConnection.debuglevel = 1

            logging.basicConfig()  # you need to initialize logging, otherwise you will not see anything from requests
            logging.getLogger().setLevel(logging.DEBUG)
            requests_log = logging.getLogger("requests.packages.urllib3")
            requests_log.setLevel(logging.DEBUG)
            requests_log.propagate = True

        self._session = requests.Session()

    @staticmethod
    def GetAppOnlyAuthToken(consumer_key, consumer_secret):
        """
        Generate a Bearer Token from consumer_key and consumer_secret
        """
        key = quote_plus(consumer_key)
        secret = quote_plus(consumer_secret)
        bearer_token = base64.b64encode('{}:{}'.format(key, secret).encode('utf8'))

        post_headers = {
            'Authorization': 'Basic {0}'.format(bearer_token.decode('utf8')),
            'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8'
        }

        res = requests.post(url='https://api.twitter.com/oauth2/token',
                            data={'grant_type': 'client_credentials'},
                            headers=post_headers)
        bearer_creds = res.json()
        return bearer_creds

    def SetCredentials(self,
                       consumer_key,
                       consumer_secret,
                       access_token_key=None,
                       access_token_secret=None,
                       application_only_auth=False):
        """Set the consumer_key and consumer_secret for this instance

        Args:
          consumer_key:
            The consumer_key of the twitter account.
          consumer_secret:
            The consumer_secret for the twitter account.
          access_token_key:
            The oAuth access token key value you retrieved
            from running get_access_token.py.
          access_token_secret:
            The oAuth access token's secret, also retrieved
            from the get_access_token.py run.
          application_only_auth:
            Whether to generate a bearer token and use Application-Only Auth
        """
        self._consumer_key = consumer_key
        self._consumer_secret = consumer_secret
        self._access_token_key = access_token_key
        self._access_token_secret = access_token_secret

        if application_only_auth:
            self._bearer_token = self.GetAppOnlyAuthToken(consumer_key, consumer_secret)
            self.__auth = OAuth2(token=self._bearer_token)
        else:
            auth_list = [consumer_key, consumer_secret,
                         access_token_key, access_token_secret]
            if all(auth_list):
                self.__auth = OAuth1(consumer_key, consumer_secret,
                                     access_token_key, access_token_secret)

        self._config = None

    def GetHelpConfiguration(self):
        """Get basic help configuration details from Twitter.

        Args:
            None

        Returns:
            dict: Sets self._config and returns dict of help config values.
        """
        if self._config is None:
            url = '%s/help/configuration.json' % self.base_url
            resp = self._RequestUrl(url, 'GET')
            data = self._ParseAndCheckTwitter(resp.content.decode('utf-8'))
            self._config = data
        return self._config

    def GetShortUrlLength(self, https=False):
        """Returns number of characters reserved per URL included in a tweet.

        Args:
            https (bool, optional):
                If True, return number of characters reserved for https urls
                or, if False, return number of character reserved for http urls.
        Returns:
            (int): Number of characters reserved per URL.
        """
        config = self.GetHelpConfiguration()
        if https:
            return config['short_url_length_https']
        else:
            return config['short_url_length']

    def ClearCredentials(self):
        """Clear any credentials for this instance
        """
        self._consumer_key = None
        self._consumer_secret = None
        self._access_token_key = None
        self._access_token_secret = None
        self._bearer_token = None
        self.__auth = None  # for request upgrade

    def GetSearch(self,
                  term=None,
                  raw_query=None,
                  geocode=None,
                  since_id=None,
                  max_id=None,
                  until=None,
                  since=None,
                  count=15,
                  lang=None,
                  locale=None,
                  result_type="mixed",
                  include_entities=None,
                  return_json=False):
        """Return twitter search results for a given term. You must specify one
        of term, geocode, or raw_query.

        Args:
          term (str, optional):
            Term to search by. Optional if you include geocode.
          raw_query (str, optional):
            A raw query as a string. This should be everything after the "?" in
            the URL (i.e., the query parameters). You are responsible for all
            type checking and ensuring that the query string is properly
            formatted, as it will only be URL-encoded before be passed directly
            to Twitter with no other checks performed. For advanced usage only.
            *This will override any other parameters passed*
          since_id (int, optional):
            Returns results with an ID greater than (that is, more recent
            than) the specified ID. There are limits to the number of
            Tweets which can be accessed through the API. If the limit of
            Tweets has occurred since the since_id, the since_id will be
            forced to the oldest ID available.
          max_id (int, optional):
            Returns only statuses with an ID less than (that is, older
            than) or equal to the specified ID.
          until (str, optional):
            Returns tweets generated before the given date. Date should be
            formatted as YYYY-MM-DD.
          since (str, optional):
            Returns tweets generated since the given date. Date should be
            formatted as YYYY-MM-DD.
          geocode (str or list or tuple, optional):
            Geolocation within which to search for tweets. Can be either a
            string in the form of "latitude,longitude,radius" where latitude
            and longitude are floats and radius is a string such as "1mi" or
            "1km" ("mi" or "km" are the only units allowed). For example:
              >>> api.GetSearch(geocode="37.781157,-122.398720,1mi").
            Otherwise, you can pass a list of either floats or strings for
            lat/long and a string for radius:
              >>> api.GetSearch(geocode=[37.781157, -122.398720, "1mi"])
              >>> # or:
              >>> api.GetSearch(geocode=(37.781157, -122.398720, "1mi"))
              >>> # or:
              >>> api.GetSearch(geocode=("37.781157", "-122.398720", "1mi"))
          count (int, optional):
            Number of results to return.  Default is 15 and maxmimum that
            Twitter returns is 100 irrespective of what you type in.
          lang (str, optional):
            Language for results as ISO 639-1 code.  Default is None
            (all languages).
          locale (str, optional):
            Language of the search query. Currently only 'ja' is effective.
            This is intended for language-specific consumers and the default
            should work in the majority of cases.
          result_type (str, optional):
            Type of result which should be returned. Default is "mixed".
            Valid options are "mixed, "recent", and "popular".
          include_entities (bool, optional):
            If True, each tweet will include a node called "entities".
            This node offers a variety of metadata about the tweet in a
            discrete structure, including: user_mentions, urls, and
            hashtags.
          return_json (bool, optional):
            If True JSON data will be returned, instead of twitter.Userret
        Returns:
          list: A sequence of twitter.Status instances, one for each message
          containing the term, within the bounds of the geocoded area, or
          given by the raw_query.
        """

        url = '%s/search/tweets.json' % self.base_url
        parameters = {}

        if since_id:
            parameters['since_id'] = enf_type('since_id', int, since_id)

        if max_id:
            parameters['max_id'] = enf_type('max_id', int, max_id)

        if until:
            parameters['until'] = enf_type('until', str, until)

        if since:
            parameters['since'] = enf_type('since', str, since)

        if lang:
            parameters['lang'] = enf_type('lang', str, lang)

        if locale:
            parameters['locale'] = enf_type('locale', str, locale)

        if term is None and geocode is None and raw_query is None:
            return []

        if term is not None:
            parameters['q'] = term

        if geocode is not None:
            if isinstance(geocode, list) or isinstance(geocode, tuple):
                parameters['geocode'] = ','.join([str(geo) for geo in geocode])
            else:
                parameters['geocode'] = enf_type('geocode', str, geocode)

        if include_entities:
            parameters['include_entities'] = enf_type('include_entities',
                                                      bool,
                                                      include_entities)

        parameters['count'] = enf_type('count', int, count)

        if result_type in ["mixed", "popular", "recent"]:
            parameters['result_type'] = result_type

        if raw_query is not None:
            url = "{url}?{raw_query}".format(
                url=url,
                raw_query=raw_query)
            resp = self._RequestUrl(url, 'GET')
        else:
            resp = self._RequestUrl(url, 'GET', data=parameters)

        data = self._ParseAndCheckTwitter(resp.content.decode('utf-8'))
        if return_json:
            return data
        else:
            return [Status.NewFromJsonDict(x) for x in data.get('statuses', '')]

    def GetUsersSearch(self,
                       term=None,
                       page=1,
                       count=20,
                       include_entities=None):
        """Return twitter user search results for a given term.

        Args:
          term:
            Term to search by.
          page:
            Page of results to return. Default is 1
            [Optional]
          count:
            Number of results to return.  Default is 20
            [Optional]
          include_entities:
            If True, each tweet will include a node called "entities,".
            This node offers a variety of metadata about the tweet in a
            discrete structure, including: user_mentions, urls, and hashtags.
            [Optional]

        Returns:
          A sequence of twitter.User instances, one for each message containing
          the term
        """
        # Build request parameters
        parameters = {}

        if term is not None:
            parameters['q'] = term

        if page != 1:
            parameters['page'] = page

        if include_entities:
            parameters['include_entities'] = 1

        try:
            parameters['count'] = int(count)
        except ValueError:
            raise TwitterError({'message': "count must be an integer"})

        # Make and send requests
        url = '%s/users/search.json' % self.base_url
        resp = self._RequestUrl(url, 'GET', data=parameters)
        data = self._ParseAndCheckTwitter(resp.content.decode('utf-8'))
        return [User.NewFromJsonDict(x) for x in data]

    def GetTrendsCurrent(self, exclude=None):
        """Get the current top trending topics (global)

        Args:
          exclude:
            Appends the exclude parameter as a request parameter.
            Currently only exclude=hashtags is supported. [Optional]

        Returns:
          A list with 10 entries. Each entry contains a trend.
        """
        return self.GetTrendsWoeid(woeid=1, exclude=exclude)

    def GetTrendsWoeid(self, woeid, exclude=None):
        """Return the top 10 trending topics for a specific WOEID, if trending
        information is available for it.

        Args:
          woeid:
            the Yahoo! Where On Earth ID for a location.
          exclude:
            Appends the exclude parameter as a request parameter.
            Currently only exclude=hashtags is supported. [Optional]

        Returns:
          A list with 10 entries. Each entry contains a trend.
        """
        url = '%s/trends/place.json' % (self.base_url)
        parameters = {'id': woeid}

        if exclude:
            parameters['exclude'] = exclude

        resp = self._RequestUrl(url, verb='GET', data=parameters)
        data = self._ParseAndCheckTwitter(resp.content.decode('utf-8'))
        trends = []
        timestamp = data[0]['as_of']

        for trend in data[0]['trends']:
            trends.append(Trend.NewFromJsonDict(trend, timestamp=timestamp))
        return trends

    def GetUserSuggestionCategories(self):
        """ Return the list of suggested user categories, this can be used in
            GetUserSuggestion function
        Returns:
            A list of categories
        """
        url = '%s/users/suggestions.json' % (self.base_url)
        resp = self._RequestUrl(url, verb='GET')
        data = self._ParseAndCheckTwitter(resp.content.decode('utf-8'))

        categories = []

        for category in data:
            categories.append(Category.NewFromJsonDict(category))
        return categories

    def GetUserSuggestion(self, category):
        """ Returns a list of users in a category
        Args:
            category:
                The Category object to limit the search by
        Returns:
            A list of users in that category
        """
        url = '%s/users/suggestions/%s.json' % (self.base_url, category.slug)

        resp = self._RequestUrl(url, verb='GET')
        data = self._ParseAndCheckTwitter(resp.content.decode('utf-8'))

        users = []
        for user in data['users']:
            users.append(User.NewFromJsonDict(user))
        return users

    def GetHomeTimeline(self,
                        count=None,
                        since_id=None,
                        max_id=None,
                        trim_user=False,
                        exclude_replies=False,
                        contributor_details=False,
                        include_entities=True):
        """Fetch a collection of the most recent Tweets and retweets posted
        by the authenticating user and the users they follow.

        The home timeline is central to how most users interact with Twitter.

        Args:
          count:
            Specifies the number of statuses to retrieve. May not be
            greater than 200. Defaults to 20. [Optional]
          since_id:
            Returns results with an ID greater than (that is, more recent
            than) the specified ID. There are limits to the number of
            Tweets which can be accessed through the API. If the limit of
            Tweets has occurred since the since_id, the since_id will be
            forced to the oldest ID available. [Optional]
          max_id:
            Returns results with an ID less than (that is, older than) or
            equal to the specified ID. [Optional]
          trim_user:
            When True, each tweet returned in a timeline will include a user
            object including only the status authors numerical ID. Omit this
            parameter to receive the complete user object. [Optional]
          exclude_replies:
            This parameter will prevent replies from appearing in the
            returned timeline. Using exclude_replies with the count
            parameter will mean you will receive up-to count tweets -
            this is because the count parameter retrieves that many
            tweets before filtering out retweets and replies. [Optional]
          contributor_details:
            This parameter enhances the contributors element of the
            status response to include the screen_name of the contributor.
            By default only the user_id of the contributor is included. [Optional]
          include_entities:
            The entities node will be disincluded when set to false.
            This node offers a variety of metadata about the tweet in a
            discreet structure, including: user_mentions, urls, and
            hashtags. [Optional]

        Returns:
          A sequence of twitter.Status instances, one for each message
        """
        url = '%s/statuses/home_timeline.json' % self.base_url

        parameters = {}
        if count is not None:
            try:
                if int(count) > 200:
                    raise TwitterError({'message': "'count' may not be greater than 200"})
            except ValueError:
                raise TwitterError({'message': "'count' must be an integer"})
            parameters['count'] = count
        if since_id:
            try:
                parameters['since_id'] = int(since_id)
            except ValueError:
                raise TwitterError({'message': "'since_id' must be an integer"})
        if max_id:
            try:
                parameters['max_id'] = int(max_id)
            except ValueError:
                raise TwitterError({'message': "'max_id' must be an integer"})
        if trim_user:
            parameters['trim_user'] = 1
        if exclude_replies:
            parameters['exclude_replies'] = 1
        if contributor_details:
            parameters['contributor_details'] = 1
        if not include_entities:
            parameters['include_entities'] = 'false'
        resp = self._RequestUrl(url, 'GET', data=parameters)
        data = self._ParseAndCheckTwitter(resp.content.decode('utf-8'))

        return [Status.NewFromJsonDict(x) for x in data]

    def GetUserTimeline(self,
                        user_id=None,
                        screen_name=None,
                        since_id=None,
                        max_id=None,
                        count=None,
                        include_rts=True,
                        trim_user=False,
                        exclude_replies=False):
        """Fetch the sequence of public Status messages for a single user.

        The twitter.Api instance must be authenticated if the user is private.

        Args:
          user_id (int, optional):
            Specifies the ID of the user for whom to return the
            user_timeline. Helpful for disambiguating when a valid user ID
            is also a valid screen name.
          screen_name (str, optional):
            Specifies the screen name of the user for whom to return the
            user_timeline. Helpful for disambiguating when a valid screen
            name is also a user ID.
          since_id (int, optional):
            Returns results with an ID greater than (that is, more recent
            than) the specified ID. There are limits to the number of
            Tweets which can be accessed through the API. If the limit of
            Tweets has occurred since the since_id, the since_id will be
            forced to the oldest ID available.
          max_id (int, optional):
            Returns only statuses with an ID less than (that is, older
            than) or equal to the specified ID.
          count (int, optional):
            Specifies the number of statuses to retrieve. May not be
            greater than 200.
          include_rts (bool, optional):
            If True, the timeline will contain native retweets (if they
            exist) in addition to the standard stream of tweets.
          trim_user (bool, optional):
            If True, statuses will only contain the numerical user ID only.
            Otherwise a full user object will be returned for each status.
          exclude_replies (bool, optional)
            If True, this will prevent replies from appearing in the returned
            timeline. Using exclude_replies with the count parameter will mean you
            will receive up-to count tweets - this is because the count parameter
            retrieves that many tweets before filtering out retweets and replies.
            This parameter is only supported for JSON and XML responses.

        Returns:
          A sequence of Status instances, one for each message up to count
        """
        url = '%s/statuses/user_timeline.json' % (self.base_url)
        parameters = {}

        if user_id:
            parameters['user_id'] = enf_type('user_id', int, user_id)
        elif screen_name:
            parameters['screen_name'] = screen_name
        if since_id:
            parameters['since_id'] = enf_type('since_id', int, since_id)
        if max_id:
            parameters['max_id'] = enf_type('max_id', int, max_id)
        if count:
            parameters['count'] = enf_type('count', int, count)

        parameters['include_rts'] = enf_type('include_rts', bool, include_rts)
        parameters['trim_user'] = enf_type('trim_user', bool, trim_user)
        parameters['exclude_replies'] = enf_type('exclude_replies', bool, exclude_replies)

        resp = self._RequestUrl(url, 'GET', data=parameters)
        data = self._ParseAndCheckTwitter(resp.content.decode('utf-8'))

        return [Status.NewFromJsonDict(x) for x in data]

    def GetStatus(self,
                  status_id,
                  trim_user=False,
                  include_my_retweet=True,
                  include_entities=True,
                  include_ext_alt_text=True):
        """Returns a single status message, specified by the status_id parameter.

        Args:
          status_id:
            The numeric ID of the status you are trying to retrieve.
          trim_user:
            When set to True, each tweet returned in a timeline will include
            a user object including only the status authors numerical ID.
            Omit this parameter to receive the complete user object. [Optional]
          include_my_retweet:
            When set to True, any Tweets returned that have been retweeted by
            the authenticating user will include an additional
            current_user_retweet node, containing the ID of the source status
            for the retweet. [Optional]
          include_entities:
            If False, the entities node will be disincluded.
            This node offers a variety of metadata about the tweet in a
            discreet structure, including: user_mentions, urls, and
            hashtags. [Optional]
        Returns:
          A twitter.Status instance representing that status message
        """
        url = '%s/statuses/show.json' % (self.base_url)

        parameters = {
            'id': enf_type('status_id', int, status_id),
            'trim_user': enf_type('trim_user', bool, trim_user),
            'include_my_retweet': enf_type('include_my_retweet', bool, include_my_retweet),
            'include_entities': enf_type('include_entities', bool, include_entities),
            'include_ext_alt_text': enf_type('include_ext_alt_text', bool, include_ext_alt_text)
        }

        resp = self._RequestUrl(url, 'GET', data=parameters)
        data = self._ParseAndCheckTwitter(resp.content.decode('utf-8'))

        return Status.NewFromJsonDict(data)

    def GetStatuses(self,
                    status_ids,
                    trim_user=False,
                    include_entities=True,
                    map=False):
        """Returns a list of status messages, specified by the status_ids parameter.

        Args:
          status_ids:
            A list of the numeric ID of the statuses you are trying to retrieve.
          trim_user:
            When set to True, each tweet returned in a timeline will include
            a user object including only the status authors numerical ID.
            Omit this parameter to receive the complete user object. [Optional]
          include_entities:
            If False, the entities node will be disincluded.
            This node offers a variety of metadata about the tweet in a
            discreet structure, including: user_mentions, urls, and
            hashtags. [Optional]
          map:
            If True, returns a dictionary with status id as key and returned
            status data (or None if tweet does not exist or is inaccessible)
            as value. Otherwise returns an unordered list of successfully
            retrieved Tweets. [Optional]
        Returns:
          A dictionary or unordered list (depending on the parameter 'map') of
          twitter Status instances representing the status messages.
        """
        url = '%s/statuses/lookup.json' % (self.base_url)

        map = enf_type('map', bool, map)

        if map:
            result = {}
        else:
            result = []
        offset = 0
        parameters = {
            'trim_user': enf_type('trim_user', bool, trim_user),
            'include_entities': enf_type('include_entities', bool, include_entities),
            'map': map
        }
        while offset < len(status_ids):
            parameters['id'] = ','.join([str(enf_type('status_id', int, status_id)) for status_id in status_ids[offset:offset + 100]])

            resp = self._RequestUrl(url, 'GET', data=parameters)
            data = self._ParseAndCheckTwitter(resp.content.decode('utf-8'))
            if map:
                result.update({int(key): (Status.NewFromJsonDict(value) if value else None) for key, value in data['id'].items()})
            else:
                result += [Status.NewFromJsonDict(dataitem) for dataitem in data]

            offset += 100

        return result

    def GetStatusOembed(self,
                        status_id=None,
                        url=None,
                        maxwidth=None,
                        hide_media=False,
                        hide_thread=False,
                        omit_script=False,
                        align=None,
                        related=None,
                        lang=None):
        """Returns information allowing the creation of an embedded representation of a
        Tweet on third party sites.

        Specify tweet by the id or url parameter.

        Args:
          status_id:
            The numeric ID of the status you are trying to embed.
          url:
            The url of the status you are trying to embed.
          maxwidth:
            The maximum width in pixels that the embed should be rendered at.
            This value is constrained to be between 250 and 550 pixels. [Optional]
          hide_media:
            Specifies whether the embedded Tweet should automatically expand images. [Optional]
          hide_thread:
            Specifies whether the embedded Tweet should automatically show the original
            message in the case that the embedded Tweet is a reply. [Optional]
          omit_script:
            Specifies whether the embedded Tweet HTML should include a <script>
            element pointing to widgets.js. [Optional]
          align:
            Specifies whether the embedded Tweet should be left aligned, right aligned,
            or centered in the page. [Optional]
          related:
            A comma sperated string of related screen names. [Optional]
          lang:
            Language code for the rendered embed. [Optional]

        Returns:
          A dictionary with the response.
        """
        request_url = '%s/statuses/oembed.json' % (self.base_url)

        parameters = {}

        if status_id is not None:
            try:
                parameters['id'] = int(status_id)
            except ValueError:
                raise TwitterError({'message': "'status_id' must be an integer."})
        elif url is not None:
            parameters['url'] = url
        else:
            raise TwitterError({'message': "Must specify either 'status_id' or 'url'"})

        if maxwidth is not None:
            parameters['maxwidth'] = maxwidth
        if hide_media is True:
            parameters['hide_media'] = 'true'
        if hide_thread is True:
            parameters['hide_thread'] = 'true'
        if omit_script is True:
            parameters['omit_script'] = 'true'
        if align is not None:
            if align not in ('left', 'center', 'right', 'none'):
                raise TwitterError({'message': "'align' must be 'left', 'center', 'right', or 'none'"})
            parameters['align'] = align
        if related:
            if not isinstance(related, str):
                raise TwitterError({'message': "'related' should be a string of comma separated screen names"})
            parameters['related'] = related
        if lang is not None:
            if not isinstance(lang, str):
                raise TwitterError({'message': "'lang' should be string instance"})
            parameters['lang'] = lang

        resp = self._RequestUrl(request_url, 'GET', data=parameters, enforce_auth=False)
        data = self._ParseAndCheckTwitter(resp.content.decode('utf-8'))

        return data

    def DestroyStatus(self, status_id, trim_user=False):
        """Destroys the status specified by the required ID parameter.

        The authenticating user must be the author of the specified
        status.

        Args:
          status_id (int):
            The numerical ID of the status you're trying to destroy.
          trim_user (bool, optional):
            When set to True, each tweet returned in a timeline will include
            a user object including only the status authors numerical ID.

        Returns:
          A twitter.Status instance representing the destroyed status message
        """
        url = '%s/statuses/destroy/%s.json' % (self.base_url, status_id)

        post_data = {
            'id': enf_type('status_id', int, status_id),
            'trim_user': enf_type('trim_user', bool, trim_user)
        }

        resp = self._RequestUrl(url, 'POST', data=post_data)
        data = self._ParseAndCheckTwitter(resp.content.decode('utf-8'))

        return Status.NewFromJsonDict(data)

    def PostUpdate(self,
                   status,
                   media=None,
                   media_additional_owners=None,
                   media_category=None,
                   in_reply_to_status_id=None,
                   auto_populate_reply_metadata=False,
                   exclude_reply_user_ids=None,
                   latitude=None,
                   longitude=None,
                   place_id=None,
                   display_coordinates=False,
                   trim_user=False,
                   verify_status_length=True,
                   attachment_url=None):
        """Post a twitter status message from the authenticated user.

        https://dev.twitter.com/docs/api/1.1/post/statuses/update

        Args:
            status (str):
                The message text to be posted. Must be less than or equal to
                CHARACTER_LIMIT characters.
            media (int, str, fp, optional):
                A URL, a local file, or a file-like object (something with a
                read() method), or a list of any combination of the above.
            media_additional_owners (list, optional):
                A list of user ids representing Twitter users that should be able
                to use the uploaded media in their tweets. If you pass a list of
                media, then additional_owners will apply to each object. If you
                need more granular control, please use the UploadMedia* methods.
            media_category (str, optional):
                Only for use with the AdsAPI. See
                https://dev.twitter.com/ads/creative/promoted-video-overview if
                this applies to your application.
            in_reply_to_status_id (int, optional):
                The ID of an existing status that the status to be posted is
                in reply to.  This implicitly sets the in_reply_to_user_id
                attribute of the resulting status to the user ID of the
                message being replied to.  Invalid/missing status IDs will be
                ignored.
            auto_populate_reply_metadata (bool, optional):
                Automatically include the @usernames of the users mentioned or
                participating in the tweet to which this tweet is in reply.
            exclude_reply_user_ids (list, optional):
                Remove given user_ids (*not* @usernames) from the tweet's
                automatically generated reply metadata.
            attachment_url (str, optional):
                URL to an attachment resource: one to four photos, a GIF,
                video, Quote Tweet, or DM deep link. If not specified and
                media parameter is not None, we will attach the first media
                object as the attachment URL. If a bad URL is passed, Twitter
                will raise an error.
            latitude (float, optional):
                Latitude coordinate of the tweet in degrees. Will only work
                in conjunction with longitude argument. Both longitude and
                latitude will be ignored by twitter if the user has a false
                geo_enabled setting.
            longitude (float, optional):
                Longitude coordinate of the tweet in degrees. Will only work
                in conjunction with latitude argument. Both longitude and
                latitude will be ignored by twitter if the user has a false
                geo_enabled setting.
            place_id (int, optional):
                A place in the world. These IDs can be retrieved from
                GET geo/reverse_geocode.
            display_coordinates (bool, optional):
                Whether or not to put a pin on the exact coordinates a tweet
                has been sent from.
            trim_user (bool, optional):
                If True the returned payload will only contain the user IDs,
                otherwise the payload will contain the full user data item.
            verify_status_length (bool, optional):
                If True, api throws a hard error that the status is over
                CHARACTER_LIMIT characters. If False, Api will attempt to post
                the status.
        Returns:
            (twitter.Status) A twitter.Status instance representing the
            message posted.
        """
        url = '%s/statuses/update.json' % self.base_url

        if isinstance(status, str) or self._input_encoding is None:
            u_status = status
        else:
            u_status = str(status, self._input_encoding)

        if verify_status_length and calc_expected_status_length(u_status) > CHARACTER_LIMIT:
            raise TwitterError("Text must be less than or equal to CHARACTER_LIMIT characters.")

        if auto_populate_reply_metadata and not in_reply_to_status_id:
            raise TwitterError("If auto_populate_reply_metadata is True, you must set in_reply_to_status_id")

        parameters = {
            'status': u_status,
            'in_reply_to_status_id': in_reply_to_status_id,
            'auto_populate_reply_metadata': auto_populate_reply_metadata,
            'place_id': place_id,
            'display_coordinates': display_coordinates,
            'trim_user': trim_user,
            'exclude_reply_user_ids': ','.join([str(u) for u in exclude_reply_user_ids or []]),
        }

        if attachment_url:
            parameters['attachment_url'] = attachment_url

        if media:
            chunked_types = ['video/mp4', 'video/quicktime', 'image/gif']
            media_ids = []
            if isinstance(media, (int, long)):
                media_ids.append(media)

            elif isinstance(media, list):
                for media_file in media:

                    # If you want to pass just a media ID, it should be an int
                    if isinstance(media_file, (int, long)):
                        media_ids.append(media_file)
                        continue

                    _, _, file_size, media_type = parse_media_file(media_file)
                    if (media_type == 'image/gif' or media_type == 'video/mp4') and len(media) > 1:
                        raise TwitterError(
                            'You cannot post more than 1 GIF or 1 video in a single status.')
                    if file_size > self.chunk_size or media_type in chunked_types:
                        media_id = self.UploadMediaChunked(
                            media=media_file,
                            additional_owners=media_additional_owners,
                            media_category=media_category)
                    else:
                        media_id = self.UploadMediaSimple(
                            media=media_file,
                            additional_owners=media_additional_owners,
                            media_category=media_category)
                    media_ids.append(media_id)
            else:
                _, _, file_size, media_type = parse_media_file(media)
                if file_size > self.chunk_size or media_type in chunked_types:
                    media_ids.append(self.UploadMediaChunked(
                        media, media_additional_owners, media_category=media_category
                    ))
                else:
                    media_ids.append(self.UploadMediaSimple(
                        media, media_additional_owners, media_category=media_category
                    ))
            parameters['media_ids'] = ','.join([str(mid) for mid in media_ids])

        if latitude is not None and longitude is not None:
            parameters['lat'] = str(latitude)
            parameters['long'] = str(longitude)

        resp = self._RequestUrl(url, 'POST', data=parameters)
        data = self._ParseAndCheckTwitter(resp.content.decode('utf-8'))

        return Status.NewFromJsonDict(data)

    def UploadMediaSimple(self,
                          media,
                          additional_owners=None,
                          media_category=None):

        """ Upload a media file to Twitter in one request. Used for small file
        uploads that do not require chunked uploads.

        Args:
            media:
                File-like object to upload.
            additional_owners: additional Twitter users that are allowed to use
                The uploaded media. Should be a list of integers. Maximum
                number of additional owners is capped at 100 by Twitter.
            media_category:
                Category with which to identify media upload. Only use with Ads
                API & video files.

        Returns:
            media_id:
                ID of the uploaded media returned by the Twitter API or 0.

        """
        url = '%s/media/upload.json' % self.upload_url
        parameters = {}

        media_fp, _, _, _ = parse_media_file(media)

        parameters['media'] = media_fp.read()

        if additional_owners and len(additional_owners) > 100:
            raise TwitterError({'message': 'Maximum of 100 additional owners may be specified for a Media object'})
        if additional_owners:
            parameters['additional_owners'] = additional_owners
        if media_category:
            parameters['media_category'] = media_category

        resp = self._RequestUrl(url, 'POST', data=parameters)
        data = self._ParseAndCheckTwitter(resp.content.decode('utf-8'))

        try:
            return data['media_id']
        except KeyError:
            raise TwitterError({'message': 'Media could not be uploaded.'})

    def PostMediaMetadata(self,
                          media_id,
                          alt_text=None):
        """Provide addtional data for uploaded media.

        Args:
            media_id:
                ID of a previously uploaded media item.
            alt_text:
                Image Alternate Text.
        """
        url = '%s/media/metadata/create.json' % self.upload_url
        parameters = {}

        parameters['media_id'] = media_id

        if alt_text:
            parameters['alt_text'] = {"text": alt_text}

        resp = self._RequestUrl(url, 'POST', json=parameters)

        return resp

    def _UploadMediaChunkedInit(self,
                                media,
                                additional_owners=None,
                                media_category=None):
        """Start a chunked upload to Twitter.

        Args:
            media:
                File-like object to upload.
            additional_owners: additional Twitter users that are allowed to use
                The uploaded media. Should be a list of integers. Maximum
                number of additional owners is capped at 100 by Twitter.
            media_category:
                Category with which to identify media upload. Only use with Ads
                API & video files.

        Returns:
            tuple: media_id (returned from Twitter), file-handler object (i.e., has .read()
            method), filename media file.
        """
        url = '%s/media/upload.json' % self.upload_url

        media_fp, filename, file_size, media_type = parse_media_file(media, async_upload=True)

        if not all([media_fp, filename, file_size, media_type]):
            raise TwitterError({'message': 'Could not process media file'})

        parameters = {}

        if additional_owners and len(additional_owners) > 100:
            raise TwitterError({'message': 'Maximum of 100 additional owners may be specified for a Media object'})
        if additional_owners:
            parameters['additional_owners'] = additional_owners
        if media_category:
            parameters['media_category'] = media_category

        # INIT doesn't read in any data. It's purpose is to prepare Twitter to
        # receive the content in APPEND requests.
        parameters['command'] = 'INIT'
        parameters['media_type'] = media_type
        parameters['total_bytes'] = file_size

        resp = self._RequestUrl(url, 'POST', data=parameters)
        data = self._ParseAndCheckTwitter(resp.content.decode('utf-8'))

        try:
            media_id = data['media_id']
        except KeyError:
            raise TwitterError({'message': 'Media could not be uploaded'})

        return (media_id, media_fp, filename)

    def _UploadMediaChunkedAppend(self,
                                  media_id,
                                  media_fp,
                                  filename):
        """Appends (i.e., actually uploads) media file to Twitter.

        Args:
            media_id (int):
                ID of the media file received from Init method.
            media_fp (file):
                File-like object representing media file (must have .read() method)
            filename (str):
                Filename of the media file being uploaded.

        Returns:
            True if successful. Raises otherwise.
        """
        url = '%s/media/upload.json' % self.upload_url

        boundary = "--{0}".format(uuid4().hex).encode('utf-8')
        media_id_bytes = str(media_id).encode('utf-8')
        headers = {'Content-Type': 'multipart/form-data; boundary={0}'.format(
            boundary.decode('utf8')[2:]
        )}

        segment_id = 0
        while True:
            try:
                data = media_fp.read(self.chunk_size)
            except ValueError:
                break
            if not data:
                break
            body = [
                boundary,
                b'Content-Disposition: form-data; name="command"',
                b'',
                b'APPEND',
                boundary,
                b'Content-Disposition: form-data; name="media_id"',
                b'',
                media_id_bytes,
                boundary,
                b'Content-Disposition: form-data; name="segment_index"',
                b'',
                str(segment_id).encode('utf-8'),
                boundary,
                'Content-Disposition: form-data; name="media"; filename="{0!r}"'.format(filename).encode('utf8'),
                b'Content-Type: application/octet-stream',
                b'',
                data,
                boundary + b'--'
            ]
            body_data = b'\r\n'.join(body)
            headers['Content-Length'] = str(len(body_data))

            resp = self._RequestChunkedUpload(url=url,
                                              headers=headers,
                                              data=body_data)

            # The body of the response should be blank, but the normal decoding
            # raises a JSONDecodeError, so we should only do error checking
            # if the response is not blank.
            if resp.content.decode('utf-8'):
                return self._ParseAndCheckTwitter(resp.content.decode('utf-8'))

            segment_id += 1

        try:
            media_fp.close()
        except Exception as e:
            pass

        return True

    def _UploadMediaChunkedFinalize(self, media_id):
        """Finalize chunked upload to Twitter.

        Args:
            media_id (int):
                ID of the media file for which to finalize the upload.

        Returns:
            json: JSON string of data from Twitter.
        """
        url = '%s/media/upload.json' % self.upload_url

        parameters = {
            'command': 'FINALIZE',
            'media_id': media_id
        }

        resp = self._RequestUrl(url, 'POST', data=parameters)
        data = self._ParseAndCheckTwitter(resp.content.decode('utf-8'))

        return data

    def UploadMediaChunked(self,
                           media,
                           additional_owners=None,
                           media_category=None):
        """Upload a media file to Twitter in multiple requests.

        Args:
            media:
                File-like object to upload.
            additional_owners: additional Twitter users that are allowed to use
                The uploaded media. Should be a list of integers. Maximum
                number of additional owners is capped at 100 by Twitter.
            media_category:
                Category with which to identify media upload. Only use with Ads
                API & video files.

        Returns:
            media_id:
                ID of the uploaded media returned by the Twitter API. Raises if
                unsuccesful.
        """

        media_id, media_fp, filename = self._UploadMediaChunkedInit(media=media,
                                                                    additional_owners=additional_owners,
                                                                    media_category=media_category)

        append = self._UploadMediaChunkedAppend(media_id=media_id,
                                                media_fp=media_fp,
                                                filename=filename)

        if not append:
            TwitterError('Media could not be uploaded.')

        data = self._UploadMediaChunkedFinalize(media_id)

        try:
            return data['media_id']
        except KeyError:
            raise TwitterError('Media could not be uploaded.')

    def _TweetTextWrap(self,
                       status,
                       char_lim=CHARACTER_LIMIT):

        if not self._config:
            self.GetHelpConfiguration()

        tweets = []
        line = []
        line_length = 0
        words = re.split(r'\s', status)

        if len(words) == 1 and not is_url(words[0]):
            if len(words[0]) > CHARACTER_LIMIT:
                raise TwitterError("Unable to split status into tweetable parts. Word was: {0}/{1}".format(len(words[0]), char_lim))
            else:
                tweets.append(words[0])
                return tweets

        for word in words:
            if len(word) > char_lim:
                raise TwitterError("Unable to split status into tweetable parts. Word was: {0}/{1}".format(len(word), char_lim))
            new_len = line_length

            if is_url(word):
                new_len = line_length + self._config['short_url_length_https'] + 1
            else:
                new_len += len(word) + 1

            if new_len > CHARACTER_LIMIT:
                tweets.append(' '.join(line))
                line = [word]
                line_length = new_len - line_length
            else:
                line.append(word)
                line_length = new_len

        tweets.append(' '.join(line))
        return tweets

    def PostUpdates(self,
                    status,
                    continuation=None,
                    **kwargs):
        """Post one or more twitter status messages from the authenticated user.

        Unlike api.PostUpdate, this method will post multiple status updates
        if the message is longer than CHARACTER_LIMIT characters.

        Args:
          status:
            The message text to be posted.
            May be longer than CHARACTER_LIMIT characters.
          continuation:
            The character string, if any, to be appended to all but the
            last message.  Note that Twitter strips trailing '...' strings
            from messages.  Consider using the unicode \u2026 character
            (horizontal ellipsis) instead. [Defaults to None]
          **kwargs:
            See api.PostUpdate for a list of accepted parameters.

        Returns:
          A of list twitter.Status instance representing the messages posted.
        """
        results = list()

        if continuation is None:
            continuation = ''
        char_limit = CHARACTER_LIMIT - len(continuation)

        tweets = self._TweetTextWrap(status=status, char_lim=char_limit)

        if len(tweets) == 1:
            results.append(self.PostUpdate(status=tweets[0], **kwargs))
            return results

        for tweet in tweets[0:-1]:
            results.append(self.PostUpdate(status=tweet + continuation, **kwargs))
        results.append(self.PostUpdate(status=tweets[-1], **kwargs))

        return results

    def PostRetweet(self, status_id, trim_user=False):
        """Retweet a tweet with the Retweet API.

        Args:
          status_id:
            The numerical id of the tweet that will be retweeted
          trim_user:
            If True the returned payload will only contain the user IDs,
            otherwise the payload will contain the full user data item.
            [Optional]

        Returns:
          A twitter.Status instance representing the original tweet with retweet details embedded.
        """
        try:
            if int(status_id) <= 0:
                raise TwitterError({'message': "'status_id' must be a positive number"})
        except ValueError:
            raise TwitterError({'message': "'status_id' must be an integer"})

        url = '%s/statuses/retweet/%s.json' % (self.base_url, status_id)
        data = {'id': status_id}
        if trim_user:
            data['trim_user'] = 'true'
        resp = self._RequestUrl(url, 'POST', data=data)
        data = self._ParseAndCheckTwitter(resp.content.decode('utf-8'))

        return Status.NewFromJsonDict(data)

    def GetUserRetweets(self,
                        count=None,
                        since_id=None,
                        max_id=None,
                        trim_user=False):
        """Fetch the sequence of retweets made by the authenticated user.

        Args:
          count:
            The number of status messages to retrieve. [Optional]
          since_id:
            Returns results with an ID greater than (that is, more recent
            than) the specified ID. There are limits to the number of
            Tweets which can be accessed through the API. If the limit of
            Tweets has occurred since the since_id, the since_id will be
            forced to the oldest ID available. [Optional]
          max_id:
            Returns results with an ID less than (that is, older than) or
            equal to the specified ID. [Optional]
          trim_user:
            If True the returned payload will only contain the user IDs,
            otherwise the payload will contain the full user data item.
            [Optional]

        Returns:
          A sequence of twitter.Status instances, one for each message up to count
        """
        return self.GetUserTimeline(
            since_id=since_id,
            count=count,
            max_id=max_id,
            trim_user=trim_user,
            exclude_replies=True,
            include_rts=True)

    def GetReplies(self,
                   since_id=None,
                   count=None,
                   max_id=None,
                   trim_user=False):
        """Get a sequence of status messages representing the 20 most
        recent replies (status updates prefixed with @twitterID) to the
        authenticating user.

        Args:
          since_id:
            Returns results with an ID greater than (that is, more recent
            than) the specified ID. There are limits to the number of
            Tweets which can be accessed through the API. If the limit of
            Tweets has occurred since the since_id, the since_id will be
            forced to the oldest ID available. [Optional]
          max_id:
            Returns results with an ID less than (that is, older than) or
            equal to the specified ID. [Optional]
          trim_user:
            If True the returned payload will only contain the user IDs,
            otherwise the payload will contain the full user data item.
            [Optional]

        Returns:
          A sequence of twitter.Status instances, one for each reply to the user.
        """
        return self.GetUserTimeline(since_id=since_id, count=count, max_id=max_id, trim_user=trim_user,
                                    exclude_replies=False, include_rts=False)

    def GetRetweets(self,
                    statusid,
                    count=None,
                    trim_user=False):
        """Returns up to 100 of the first retweets of the tweet identified
        by statusid

        Args:
          statusid (int):
            The ID of the tweet for which retweets should be searched for
          count (int, optional):
            The number of status messages to retrieve.
          trim_user (bool, optional):
            If True the returned payload will only contain the user IDs,
            otherwise the payload will contain the full user data item.

        Returns:
          A list of twitter.Status instances, which are retweets of statusid
        """
        url = '%s/statuses/retweets/%s.json' % (self.base_url, statusid)
        parameters = {
            'trim_user': enf_type('trim_user', bool, trim_user),
        }

        if count:
            parameters['count'] = enf_type('count', int, count)

        resp = self._RequestUrl(url, 'GET', data=parameters)
        data = self._ParseAndCheckTwitter(resp.content.decode('utf-8'))

        return [Status.NewFromJsonDict(s) for s in data]

    def GetRetweeters(self,
                      status_id,
                      cursor=None,
                      count=100,
                      stringify_ids=False):
        """Returns a collection of up to 100 user IDs belonging to users who have
        retweeted the tweet specified by the status_id parameter.

        Args:
          status_id:
            the tweet's numerical ID
          cursor:
            breaks the ids into pages of no more than 100.
          stringify_ids:
            returns the IDs as unicode strings. [Optional]

        Returns:
          A list of user IDs
        """
        url = '%s/statuses/retweeters/ids.json' % (self.base_url)
        parameters = {
            'id': enf_type('id', int, status_id),
            'stringify_ids': enf_type('stringify_ids', bool, stringify_ids),
            'count': count,
        }

        result = []

        total_count = 0
        while True:
            if cursor:
                try:
                    parameters['cursor'] = int(cursor)
                except ValueError:
                    raise TwitterError({'message': "cursor must be an integer"})
            resp = self._RequestUrl(url, 'GET', data=parameters)
            data = self._ParseAndCheckTwitter(resp.content.decode('utf-8'))
            result += [x for x in data['ids']]
            if 'next_cursor' in data:
                if data['next_cursor'] == 0 or data['next_cursor'] == data['previous_cursor']:
                    break
                else:
                    cursor = data['next_cursor']
                    total_count -= len(data['ids'])
                    if total_count < 1:
                        break
            else:
                break

        return result

    def GetRetweetsOfMe(self,
                        count=None,
                        since_id=None,
                        max_id=None,
                        trim_user=False,
                        include_entities=True,
                        include_user_entities=True):
        """Returns up to 100 of the most recent tweets of the user that have been
        retweeted by others.

        Args:
          count:
            The number of retweets to retrieve, up to 100.
            Defaults to 20. [Optional]
          since_id:
            Returns results with an ID greater than
            (newer than) this ID. [Optional]
          max_id:
            Returns results with an ID less than or equal
            to this ID. [Optional]
          trim_user:
            When True, the user object for each tweet will
            only be an ID. [Optional]
          include_entities:
            When True, the tweet entities will be included. [Optional]
          include_user_entities:
            When True, the user entities will be included. [Optional]
        """
        url = '%s/statuses/retweets_of_me.json' % self.base_url
        if count is not None:
            try:
                if int(count) > 100:
                    raise TwitterError({'message': "'count' may not be greater than 100"})
            except ValueError:
                raise TwitterError({'message': "'count' must be an integer"})
        parameters = {
            'count': count,
            'since_id': since_id,
            'max_id': max_id,
            'trim_user': bool(trim_user),
            'include_entities': bool(include_entities),
            'include_user_entities': bool(include_user_entities),
        }

        resp = self._RequestUrl(url, 'GET', data=parameters)
        data = self._ParseAndCheckTwitter(resp.content.decode('utf-8'))

        return [Status.NewFromJsonDict(s) for s in data]

    def _GetBlocksMutesPaged(self,
                             endpoint,
                             action,
                             cursor=-1,
                             skip_status=False,
                             include_entities=True,
                             stringify_ids=False):
        """ Fetch a page of the users (as twitter.User instances)
        blocked or muted by the currently authenticated user.

        Args:
          endpoint (str):
            Either "mute" or "block".
          action (str):
            Either 'list' or 'ids' depending if you want to return fully-hydrated
            twitter.User objects or a list of user IDs as ints.
          cursor (int, optional):
            Should be set to -1 if you want the first page, thereafter denotes
            the page of users that you want to return.
          skip_status (bool, optional):
            If True the statuses will not be returned in the user items.
          include_entities (bool, optional):
            When True, the user entities will be included.

        Returns:
          next_cursor, previous_cursor, list of twitter.User instances,
          one for each user.
        """
        urls = {
            'mute': {
                'list': '%s/mutes/users/list.json' % self.base_url,
                'ids': '%s/mutes/users/ids.json' % self.base_url
            },
            'block': {
                'list': '%s/blocks/list.json' % self.base_url,
                'ids': '%s/blocks/ids.json' % self.base_url
            }
        }

        url = urls[endpoint][action]

        result = []
        parameters = {
            'skip_status': bool(skip_status),
            'include_entities': bool(include_entities),
            'stringify_ids': bool(stringify_ids),
            'cursor': cursor,
        }

        resp = self._RequestUrl(url, 'GET', data=parameters)
        data = self._ParseAndCheckTwitter(resp.content.decode('utf-8'))

        if action == 'ids':
            result += data.get('ids')
        else:
            result += [User.NewFromJsonDict(x) for x in data['users']]
        next_cursor = data.get('next_cursor', 0)
        previous_cursor = data.get('previous_cursor', 0)

        return next_cursor, previous_cursor, result

    def GetBlocks(self,
                  skip_status=False,
                  include_entities=False):
        """ Fetch the sequence of all users (as twitter.User instances),
        blocked by the currently authenticated user.

        Args:
          skip_status (bool, optional):
            If True the statuses will not be returned in the user items.
          include_entities (bool, optional):
            When True, the user entities will be included.

        Returns:
          A list of twitter.User instances, one for each blocked user.
        """
        result = []
        cursor = -1

        while True:
            next_cursor, previous_cursor, users = self.GetBlocksPaged(
                cursor=cursor,
                skip_status=skip_status,
                include_entities=include_entities)
            result += users
            if next_cursor == 0 or next_cursor == previous_cursor:
                break
            else:
                cursor = next_cursor

        return result

    def GetBlocksPaged(self,
                       cursor=-1,
                       skip_status=False,
                       include_entities=False):
        """ Fetch a page of the users (as twitter.User instances)
        blocked by the currently authenticated user.

        Args:
          cursor (int, optional):
            Should be set to -1 if you want the first page, thereafter denotes
            the page of blocked users that you want to return.
          skip_status (bool, optional):
            If True the statuses will not be returned in the user items.
          include_entities (bool, optional):
            When True, the user entities will be included.

        Returns:
          next_cursor, previous_cursor, list of twitter.User instances,
          one for each blocked user.
        """
        return self._GetBlocksMutesPaged(endpoint='block',
                                         action='list',
                                         cursor=cursor,
                                         skip_status=skip_status,
                                         include_entities=include_entities)

    def GetBlocksIDs(self,
                     stringify_ids=False):
        """Fetch the sequence of all user IDs blocked by the
        currently authenticated user.

        Args:
          stringify_ids (bool, optional):
            If True user IDs will be returned as strings rather than integers.

        Returns:
          A list of user IDs for all blocked users.
        """
        result = []
        cursor = -1

        while True:
            next_cursor, previous_cursor, user_ids = self.GetBlocksIDsPaged(
                cursor=cursor,
                stringify_ids=stringify_ids)
            result += user_ids
            if next_cursor == 0 or next_cursor == previous_cursor:
                break
            else:
                cursor = next_cursor

        return result

    def GetBlocksIDsPaged(self,
                          cursor=-1,
                          stringify_ids=False):
        """ Fetch a page of the user IDs blocked by the currently
        authenticated user.

        Args:
          cursor (int, optional):
            Should be set to -1 if you want the first page, thereafter denotes
            the page of blocked users that you want to return.
          stringify_ids (bool, optional):
            If True user IDs will be returned as strings rather than integers.

        Returns:
          next_cursor, previous_cursor, list of user IDs of blocked users.
        """
        return self._GetBlocksMutesPaged(endpoint='block',
                                         action='ids',
                                         cursor=cursor,
                                         stringify_ids=stringify_ids)

    def GetMutes(self,
                 skip_status=False,
                 include_entities=False):
        """ Fetch the sequence of all users (as twitter.User instances),
        muted by the currently authenticated user.

        Args:
          skip_status (bool, optional):
            If True the statuses will not be returned in the user items.
          include_entities (bool, optional):
            When True, the user entities will be included.

        Returns:
          A list of twitter.User instances, one for each muted user.
        """
        result = []
        cursor = -1

        while True:
            next_cursor, previous_cursor, users = self.GetMutesPaged(
                cursor=cursor,
                skip_status=skip_status,
                include_entities=include_entities)
            result += users
            if next_cursor == 0 or next_cursor == previous_cursor:
                break
            else:
                cursor = next_cursor

        return result

    def GetMutesPaged(self,
                      cursor=-1,
                      skip_status=False,
                      include_entities=False):
        """ Fetch a page of the users (as twitter.User instances)
        muted by the currently authenticated user.

        Args:
          cursor (int, optional):
            Should be set to -1 if you want the first page, thereafter denotes
            the page of muted users that you want to return.
          skip_status (bool, optional):
            If True the statuses will not be returned in the user items.
          include_entities (bool, optional):
            When True, the user entities will be included.

        Returns:
          next_cursor, previous_cursor, list of twitter.User instances,
          one for each muted user.
        """

        return self._GetBlocksMutesPaged(endpoint='mute',
                                         action='list',
                                         cursor=cursor,
                                         skip_status=skip_status,
                                         include_entities=include_entities)

    def GetMutesIDs(self,
                    stringify_ids=False):
        """Fetch the sequence of all user IDs muted by the
        currently authenticated user.

        Args:
          stringify_ids (bool, optional):
            If True user IDs will be returned as strings rather than integers.

        Returns:
          A list of user IDs for all muted users.
        """
        result = []
        cursor = -1

        while True:
            next_cursor, previous_cursor, user_ids = self.GetMutesIDsPaged(
                cursor=cursor,
                stringify_ids=stringify_ids)
            result += user_ids
            if next_cursor == 0 or next_cursor == previous_cursor:
                break
            else:
                cursor = next_cursor

        return result

    def GetMutesIDsPaged(self,
                         cursor=-1,
                         stringify_ids=False):
        """ Fetch a page of the user IDs muted by the currently
        authenticated user.

        Args:
          cursor (int, optional):
            Should be set to -1 if you want the first page, thereafter denotes
            the page of muted users that you want to return.
          stringify_ids (bool, optional):
            If True user IDs will be returned as strings rather than integers.

        Returns:
          next_cursor, previous_cursor, list of user IDs of muted users.
        """
        return self._GetBlocksMutesPaged(endpoint='mute',
                                         action='ids',
                                         cursor=cursor,
                                         stringify_ids=stringify_ids)

    def _BlockMute(self,
                   action,
                   endpoint,
                   user_id=None,
                   screen_name=None,
                   include_entities=True,
                   skip_status=False):
        """Create or destroy a block or mute on behalf of the authenticated user.

        Args:
          action (str):
            Either 'create' or 'destroy'.
          endpoint (str):
            Either 'block' or 'mute'.
          user_id (int, optional)
            The numerical ID of the user to block/mute.
          screen_name (str, optional):
            The screen name of the user to block/mute.
          include_entities (bool, optional):
            The entities node will not be included if set to False.
          skip_status (bool, optional):
              When set to False, the blocked User's statuses will not be included
              with the returned User object.
        Returns:
          twitter.User: twitter.User object representing the blocked/muted user.
        """

        urls = {
            'block': {
                'create': '%s/blocks/create.json' % (self.base_url),
                'destroy': '%s/blocks/destroy.json' % (self.base_url),
            },
            'mute': {
                'create': '%s/mutes/users/create.json' % (self.base_url),
                'destroy': '%s/mutes/users/destroy.json' % (self.base_url)
            }
        }

        url = urls[endpoint][action]
        post_data = {}

        if user_id:
            post_data['user_id'] = enf_type('user_id', int, user_id)
        elif screen_name:
            post_data['screen_name'] = screen_name
        else:
            raise TwitterError("You must specify either a user_id or screen_name")

        if include_entities:
            post_data['include_entities'] = enf_type('include_entities', bool, include_entities)
        if skip_status:
            post_data['skip_status'] = enf_type('skip_status', bool, skip_status)

        resp = self._RequestUrl(url, 'POST', data=post_data)
        data = self._ParseAndCheckTwitter(resp.content.decode('utf-8'))

        return User.NewFromJsonDict(data)

    def CreateBlock(self,
                    user_id=None,
                    screen_name=None,
                    include_entities=True,
                    skip_status=False):
        """Blocks the user specified by either user_id or screen_name.

        Args:
          user_id (int, optional)
            The numerical ID of the user to block.
          screen_name (str, optional):
            The screen name of the user to block.
          include_entities (bool, optional):
            The entities node will not be included if set to False.
          skip_status (bool, optional):
            When set to False, the blocked User's statuses will not be included
            with the returned User object.

        Returns:
          A twitter.User instance representing the blocked user.
        """
        return self._BlockMute(action='create',
                               endpoint='block',
                               user_id=user_id,
                               screen_name=screen_name,
                               include_entities=include_entities,
                               skip_status=skip_status)

    def DestroyBlock(self,
                     user_id=None,
                     screen_name=None,
                     include_entities=True,
                     skip_status=False):
        """Unlocks the user specified by either user_id or screen_name.

        Args:
          user_id (int, optional)
            The numerical ID of the user to block.
          screen_name (str, optional):
            The screen name of the user to block.
          include_entities (bool, optional):
            The entities node will not be included if set to False.
          skip_status (bool, optional):
            When set to False, the blocked User's statuses will not be included
            with the returned User object.

        Returns:
          A twitter.User instance representing the blocked user.
        """
        return self._BlockMute(action='destroy',
                               endpoint='block',
                               user_id=user_id,
                               screen_name=screen_name,
                               include_entities=include_entities,
                               skip_status=skip_status)

    def CreateMute(self,
                   user_id=None,
                   screen_name=None,
                   include_entities=True,
                   skip_status=False):
        """Mutes the user specified by either user_id or screen_name.

        Args:
          user_id (int, optional)
            The numerical ID of the user to mute.
          screen_name (str, optional):
            The screen name of the user to mute.
          include_entities (bool, optional):
            The entities node will not be included if set to False.
          skip_status (bool, optional):
            When set to False, the muted User's statuses will not be included
            with the returned User object.

        Returns:
          A twitter.User instance representing the muted user.
        """
        return self._BlockMute(action='create',
                               endpoint='mute',
                               user_id=user_id,
                               screen_name=screen_name,
                               include_entities=include_entities,
                               skip_status=skip_status)

    def DestroyMute(self,
                    user_id=None,
                    screen_name=None,
                    include_entities=True,
                    skip_status=False):
        """Unlocks the user specified by either user_id or screen_name.

        Args:
          user_id (int, optional)
            The numerical ID of the user to mute.
          screen_name (str, optional):
            The screen name of the user to mute.
          include_entities (bool, optional):
            The entities node will not be included if set to False.
          skip_status (bool, optional):
            When set to False, the muted User's statuses will not be included
            with the returned User object.

        Returns:
          A twitter.User instance representing the muted user.
        """
        return self._BlockMute(action='destroy',
                               endpoint='mute',
                               user_id=user_id,
                               screen_name=screen_name,
                               include_entities=include_entities,
                               skip_status=skip_status)

    def _GetIDsPaged(self,
                     url,
                     user_id,
                     screen_name,
                     cursor,
                     stringify_ids,
                     count):
        """
        This is the lowest level paging logic for fetching IDs. It is used
        solely by GetFollowerIDsPaged and GetFriendIDsPaged. It is not intended
        for other use.

        See GetFollowerIDsPaged or GetFriendIDsPaged for an explanation of the
        input arguments.
        """
        result = []

        parameters = {}
        if user_id is not None:
            parameters['user_id'] = user_id
        if screen_name is not None:
            parameters['screen_name'] = screen_name
        if count is not None:
            parameters['count'] = count
        parameters['stringify_ids'] = stringify_ids
        parameters['cursor'] = cursor

        resp = self._RequestUrl(url, 'GET', data=parameters)
        data = self._ParseAndCheckTwitter(resp.content.decode('utf-8'))

        if 'ids' in data:
            result.extend([x for x in data['ids']])

        next_cursor = data.get('next_cursor', 0)
        previous_cursor = data.get('previous_cursor', 0)

        return next_cursor, previous_cursor, result

    def GetFollowerIDsPaged(self,
                            user_id=None,
                            screen_name=None,
                            cursor=-1,
                            stringify_ids=False,
                            count=5000):
        """Make a cursor driven call to return a list of one page followers.

        The caller is responsible for handling the cursor value and looping
        to gather all of the data

        Args:
          user_id:
            The twitter id of the user whose followers you are fetching.
            If not specified, defaults to the authenticated user. [Optional]
          screen_name:
            The twitter name of the user whose followers you are fetching.
            If not specified, defaults to the authenticated user. [Optional]
          cursor:
            Should be set to -1 for the initial call and then is used to
            control what result page Twitter returns.
          stringify_ids:
            if True then twitter will return the ids as strings instead of
            integers. [Optional]
          count:
            The number of user id's to retrieve per API request. Please be aware
            that this might get you rate-limited if set to a small number.
            By default Twitter will retrieve 5000 UIDs per call. [Optional]

        Returns:
          next_cursor, previous_cursor, data sequence of user ids,
          one for each follower
        """
        url = '%s/followers/ids.json' % self.base_url
        return self._GetIDsPaged(url=url,
                                 user_id=user_id,
                                 screen_name=screen_name,
                                 cursor=cursor,
                                 stringify_ids=stringify_ids,
                                 count=count)

    def GetFriendIDsPaged(self,
                          user_id=None,
                          screen_name=None,
                          cursor=-1,
                          stringify_ids=False,
                          count=5000):
        """Make a cursor driven call to return the list of all friends

        The caller is responsible for handling the cursor value and looping
        to gather all of the data

        Args:
          user_id:
            The twitter id of the user whose friends you are fetching.
            If not specified, defaults to the authenticated user. [Optional]
          screen_name:
            The twitter name of the user whose friends you are fetching.
            If not specified, defaults to the authenticated user. [Optional]
          cursor:
            Should be set to -1 for the initial call and then is used to
            control what result page Twitter returns.
          stringify_ids:
            if True then twitter will return the ids as strings instead of
            integers. [Optional]
          count:
            The number of user id's to retrieve per API request. Please be aware
            that this might get you rate-limited if set to a small number.
            By default Twitter will retrieve 5000 UIDs per call. [Optional]

        Returns:
          next_cursor, previous_cursor, data sequence of twitter.User instances,
          one for each friend
        """
        url = '%s/friends/ids.json' % self.base_url
        return self._GetIDsPaged(url,
                                 user_id,
                                 screen_name,
                                 cursor,
                                 stringify_ids,
                                 count)

    def _GetFriendFollowerIDs(self,
                              url=None,
                              user_id=None,
                              screen_name=None,
                              cursor=None,
                              count=None,
                              stringify_ids=False,
                              total_count=None):
        """ Common method for GetFriendIDs and GetFollowerIDs """

        count = 5000
        cursor = -1
        result = []

        if total_count:
            total_count = enf_type('total_count', int, total_count)

        if total_count and total_count < count:
            count = total_count

        while True:
            if total_count is not None and len(result) + count > total_count:
                break

            next_cursor, previous_cursor, data = self._GetIDsPaged(
                url=url,
                user_id=user_id,
                screen_name=screen_name,
                cursor=cursor,
                stringify_ids=stringify_ids,
                count=count)

            result.extend([x for x in data])

            if next_cursor == 0 or next_cursor == previous_cursor:
                break
            else:
                cursor = next_cursor

        return result

    def GetFollowerIDs(self,
                       user_id=None,
                       screen_name=None,
                       cursor=None,
                       stringify_ids=False,
                       count=None,
                       total_count=None):
        """Returns a list of twitter user id's for every person
        that is following the specified user.

        Args:
          user_id:
            The id of the user to retrieve the id list for. [Optional]
          screen_name:
            The screen_name of the user to retrieve the id list for. [Optional]
          cursor:
            Specifies the Twitter API Cursor location to start at.
            Note: there are pagination limits. [Optional]
          stringify_ids:
            if True then twitter will return the ids as strings instead of
            integers. [Optional]
          count:
            The number of user id's to retrieve per API request. Please be aware
            that this might get you rate-limited if set to a small number.
            By default Twitter will retrieve 5000 UIDs per call. [Optional]
          total_count:
            The total amount of UIDs to retrieve. Good if the account has many
            followers and you don't want to get rate limited. The data returned
            might contain more UIDs if total_count is not a multiple of count
            (5000 by default). [Optional]

        Returns:
          A list of integers, one for each user id.
        """
        url = '%s/followers/ids.json' % self.base_url
        return self._GetFriendFollowerIDs(url=url,
                                          user_id=user_id,
                                          screen_name=screen_name,
                                          cursor=cursor,
                                          stringify_ids=stringify_ids,
                                          count=count,
                                          total_count=total_count)

    def GetFriendIDs(self,
                     user_id=None,
                     screen_name=None,
                     cursor=None,
                     count=None,
                     stringify_ids=False,
                     total_count=None):
        """ Fetch a sequence of user ids, one for each friend.
        Returns a list of all the given user's friends' IDs. If no user_id or
        screen_name is given, the friends will be those of the authenticated
        user.

        Args:
          user_id:
            The id of the user to retrieve the id list for. [Optional]
          screen_name:
            The screen_name of the user to retrieve the id list for. [Optional]
          cursor:
            Specifies the Twitter API Cursor location to start at.
            Note: there are pagination limits. [Optional]
          stringify_ids:
            if True then twitter will return the ids as strings instead of integers.
            [Optional]
          count:
            The number of user id's to retrieve per API request. Please be aware that
            this might get you rate-limited if set to a small number.
            By default Twitter will retrieve 5000 UIDs per call. [Optional]
          total_count:
            The total amount of UIDs to retrieve. Good if the account has many followers
            and you don't want to get rate limited. The data returned might contain more
            UIDs if total_count is not a multiple of count (5000 by default). [Optional]

        Returns:
          A list of integers, one for each user id.
        """
        url = '%s/friends/ids.json' % self.base_url
        return self._GetFriendFollowerIDs(url,
                                          user_id,
                                          screen_name,
                                          cursor,
                                          count,
                                          stringify_ids,
                                          total_count)

    def _GetFriendsFollowersPaged(self,
                                  url=None,
                                  user_id=None,
                                  screen_name=None,
                                  cursor=-1,
                                  count=200,
                                  skip_status=False,
                                  include_user_entities=True):

        """Make a cursor driven call to return the list of 1 page of friends
        or followers.

        Args:
          url:
            Endpoint from which to get data. Either
            base_url+'/followers/list.json' or base_url+'/friends/list.json'.
          user_id:
            The twitter id of the user whose followers you are fetching.
            If not specified, defaults to the authenticated user. [Optional]
          screen_name:
            The twitter name of the user whose followers you are fetching.
            If not specified, defaults to the authenticated user. [Optional]
          cursor:
            Should be set to -1 for the initial call and then is used to
            control what result page Twitter returns.
          count:
            The number of users to return per page, up to a maximum of 200.
            Defaults to 200. [Optional]
          skip_status:
            If True the statuses will not be returned in the user items.
            [Optional]
          include_user_entities:
            When True, the user entities will be included. [Optional]

        Returns:
          next_cursor, previous_cursor, data sequence of twitter.User
          instances, one for each follower
        """

        if user_id and screen_name:
            warnings.warn(
                "If both user_id and screen_name are specified, Twitter will "
                "return the followers of the user specified by screen_name, "
                "however this behavior is undocumented by Twitter and might "
                "change without warning.", stacklevel=2)

        parameters = {}

        if user_id is not None:
            parameters['user_id'] = user_id
        if screen_name is not None:
            parameters['screen_name'] = screen_name

        try:
            parameters['count'] = int(count)
        except ValueError:
            raise TwitterError({'message': "count must be an integer"})

        parameters['skip_status'] = skip_status
        parameters['include_user_entities'] = include_user_entities
        parameters['cursor'] = cursor

        resp = self._RequestUrl(url, 'GET', data=parameters)
        data = self._ParseAndCheckTwitter(resp.content.decode('utf-8'))

        if 'users' in data:
            users = [User.NewFromJsonDict(user) for user in data['users']]
        else:
            users = []

        if 'next_cursor' in data:
            next_cursor = data['next_cursor']
        else:
            next_cursor = 0
        if 'previous_cursor' in data:
            previous_cursor = data['previous_cursor']
        else:
            previous_cursor = 0

        return next_cursor, previous_cursor, users

    def GetFollowersPaged(self,
                          user_id=None,
                          screen_name=None,
                          cursor=-1,
                          count=200,
                          skip_status=False,
                          include_user_entities=True):
        """Make a cursor driven call to return the list of all followers

        Args:
          user_id:
            The twitter id of the user whose followers you are fetching.
            If not specified, defaults to the authenticated user. [Optional]
          screen_name:
            The twitter name of the user whose followers you are fetching.
            If not specified, defaults to the authenticated user. [Optional]
          cursor:
            Should be set to -1 for the initial call and then is used to
            control what result page Twitter returns.
          count:
            The number of users to return per page, up to a maximum of 200.
            Defaults to 200. [Optional]
          skip_status:
            If True the statuses will not be returned in the user items.
            [Optional]
          include_user_entities:
            When True, the user entities will be included. [Optional]

        Returns:
          next_cursor, previous_cursor, data sequence of twitter.User
          instances, one for each follower
        """
        url = '%s/followers/list.json' % self.base_url
        return self._GetFriendsFollowersPaged(url,
                                              user_id,
                                              screen_name,
                                              cursor,
                                              count,
                                              skip_status,
                                              include_user_entities)

    def GetFriendsPaged(self,
                        user_id=None,
                        screen_name=None,
                        cursor=-1,
                        count=200,
                        skip_status=False,
                        include_user_entities=True):
        """Make a cursor driven call to return the list of all friends.

        Args:
          user_id:
            The twitter id of the user whose friends you are fetching.
            If not specified, defaults to the authenticated user. [Optional]
          screen_name:
            The twitter name of the user whose friends you are fetching.
            If not specified, defaults to the authenticated user. [Optional]
          cursor:
            Should be set to -1 for the initial call and then is used to
            control what result page Twitter returns.
          count:
            The number of users to return per page, up to a current maximum of
            200. Defaults to 200. [Optional]
          skip_status:
            If True the statuses will not be returned in the user items.
            [Optional]
          include_user_entities:
            When True, the user entities will be included. [Optional]

        Returns:
          next_cursor, previous_cursor, data sequence of twitter.User
          instances, one for each follower
        """
        url = '%s/friends/list.json' % self.base_url
        return self._GetFriendsFollowersPaged(url,
                                              user_id,
                                              screen_name,
                                              cursor,
                                              count,
                                              skip_status,
                                              include_user_entities)

    def _GetFriendsFollowers(self,
                             url=None,
                             user_id=None,
                             screen_name=None,
                             cursor=None,
                             count=None,
                             total_count=None,
                             skip_status=False,
                             include_user_entities=True):

        """ Fetch the sequence of twitter.User instances, one for each friend
        or follower.

        Args:
          url:
            URL to get. Either base_url + ('/followers/list.json' or
            '/friends/list.json').
          user_id:
            The twitter id of the user whose friends you are fetching.
            If not specified, defaults to the authenticated user. [Optional]
          screen_name:
            The twitter name of the user whose friends you are fetching.
            If not specified, defaults to the authenticated user. [Optional]
          cursor:
            Should be set to -1 for the initial call and then is used to
            control what result page Twitter returns.
          count:
            The number of users to return per page, up to a maximum of 200.
            Defaults to 200. [Optional]
          total_count:
            The upper bound of number of users to return, defaults to None.
          skip_status:
            If True the statuses will not be returned in the user items.
            [Optional]
          include_user_entities:
            When True, the user entities will be included. [Optional]

        Returns:
          A sequence of twitter.User instances, one for each friend or follower
        """

        if cursor is not None or count is not None:
            warnings.warn(
                "Use of 'cursor' and 'count' parameters are deprecated as of "
                "python-twitter 3.0. Please use GetFriendsPaged or "
                "GetFollowersPaged instead.",
                PythonTwitterDeprecationWarning330)

        count = 200
        cursor = -1
        result = []

        if total_count:
            try:
                total_count = int(total_count)
            except ValueError:
                raise TwitterError({'message': "total_count must be an integer"})

            if total_count <= 200:
                count = total_count

        while True:
            if total_count is not None and len(result) + count > total_count:
                break

            next_cursor, previous_cursor, data = self._GetFriendsFollowersPaged(
                url,
                user_id,
                screen_name,
                cursor,
                count,
                skip_status,
                include_user_entities)

            if next_cursor:
                cursor = next_cursor

            result.extend(data)

            if next_cursor == 0 or next_cursor == previous_cursor:
                break

        return result

    def GetFollowers(self,
                     user_id=None,
                     screen_name=None,
                     cursor=None,
                     count=None,
                     total_count=None,
                     skip_status=False,
                     include_user_entities=True):
        """Fetch the sequence of twitter.User instances, one for each follower.

        If both user_id and screen_name are specified, this call will return
        the followers of the user specified by screen_name, however this
        behavior is undocumented by Twitter and may change without warning.

        Args:
          user_id:
            The twitter id of the user whose followers you are fetching.
            If not specified, defaults to the authenticated user. [Optional]
          screen_name:
            The twitter name of the user whose followers you are fetching.
            If not specified, defaults to the authenticated user. [Optional]
          cursor:
            Should be set to -1 for the initial call and then is used to
            control what result page Twitter returns.
          count:
            The number of users to return per page, up to a maximum of 200.
            Defaults to 200. [Optional]
          total_count:
            The upper bound of number of users to return, defaults to None.
          skip_status:
            If True the statuses will not be returned in the user items. [Optional]
          include_user_entities:
            When True, the user entities will be included. [Optional]

        Returns:
          A sequence of twitter.User instances, one for each follower
        """
        url = '%s/followers/list.json' % self.base_url
        return self._GetFriendsFollowers(url,
                                         user_id,
                                         screen_name,
                                         cursor,
                                         count,
                                         total_count,
                                         skip_status,
                                         include_user_entities)

    def GetFriends(self,
                   user_id=None,
                   screen_name=None,
                   cursor=None,
                   count=None,
                   total_count=None,
                   skip_status=False,
                   include_user_entities=True):
        """Fetch the sequence of twitter.User instances, one for each friend.

        If both user_id and screen_name are specified, this call will return
        the followers of the user specified by screen_name, however this
        behavior is undocumented by Twitter and may change without warning.

        Args:
          user_id:
            The twitter id of the user whose friends you are fetching.
            If not specified, defaults to the authenticated user. [Optional]
          screen_name:
            The twitter name of the user whose friends you are fetching.
            If not specified, defaults to the authenticated user. [Optional]
          cursor:
            Should be set to -1 for the initial call and then is used to
            control what result page Twitter returns.
          count:
            The number of users to return per page, up to a maximum of 200.
            Defaults to 200. [Optional]
          total_count:
            The upper bound of number of users to return, defaults to None.
          skip_status:
            If True the statuses will not be returned in the user items.
            [Optional]
          include_user_entities:
            When True, the user entities will be included. [Optional]

        Returns:
          A sequence of twitter.User instances, one for each friend
        """
        url = '%s/friends/list.json' % self.base_url
        return self._GetFriendsFollowers(url,
                                         user_id,
                                         screen_name,
                                         cursor,
                                         count,
                                         total_count,
                                         skip_status,
                                         include_user_entities)

    def UsersLookup(self,
                    user_id=None,
                    screen_name=None,
                    users=None,
                    include_entities=True,
                    return_json=False):
        """Fetch extended information for the specified users.

        Users may be specified either as lists of either user_ids,
        screen_names, or twitter.User objects. The list of users that
        are queried is the union of all specified parameters.

        No more than 100 users may be given per request.

        Args:
          user_id (int, list, optional):
            A list of user_ids to retrieve extended information.
          screen_name (str, list, optional):
            A list of screen_names to retrieve extended information.
          users (list, optional):
            A list of twitter.User objects to retrieve extended information.
          include_entities (bool, optional):
            The entities node that may appear within embedded statuses will be
            excluded when set to False.
          return_json (bool, optional):
            If True JSON data will be returned, instead of twitter.User

        Returns:
          A list of twitter.User objects for the requested users
        """
        if not any([user_id, screen_name, users]):
            raise TwitterError("Specify at least one of user_id, screen_name, or users.")

        url = '%s/users/lookup.json' % self.base_url
        parameters = {
            'include_entities': include_entities
        }
        uids = list()
        if user_id:
            uids.extend(user_id)
        if users:
            uids.extend([u.id for u in users])
        if len(uids):
            parameters['user_id'] = ','.join([str(u) for u in uids])
        if screen_name:
            parameters['screen_name'] = parse_arg_list(screen_name, 'screen_name')

        if len(uids) > 100:
            raise TwitterError("No more than 100 users may be requested per request.")

        resp = self._RequestUrl(url, 'GET', data=parameters)
        data = self._ParseAndCheckTwitter(resp.content.decode('utf-8'))

        if return_json:
            return data
        else:
            return [User.NewFromJsonDict(u) for u in data]

    def GetUser(self,
                user_id=None,
                screen_name=None,
                include_entities=True,
                return_json=False):
        """Returns a single user.

        Args:
          user_id (int, optional):
            The id of the user to retrieve.
          screen_name (str, optional):
            The screen name of the user for whom to return results for.
            Either a user_id or screen_name is required for this method.
          include_entities (bool, optional):
            The entities node will be omitted when set to False.
          return_json (bool, optional):
            If True JSON data will be returned, instead of twitter.User

        Returns:
          A twitter.User instance representing that user
        """
        url = '%s/users/show.json' % (self.base_url)
        parameters = {
            'include_entities': include_entities
        }
        if user_id:
            parameters['user_id'] = user_id
        elif screen_name:
            parameters['screen_name'] = screen_name
        else:
            raise TwitterError("Specify at least one of user_id or screen_name.")

        resp = self._RequestUrl(url, 'GET', data=parameters)
        data = self._ParseAndCheckTwitter(resp.content.decode('utf-8'))

        if return_json:
            return data
        else:
            return User.NewFromJsonDict(data)

    def GetDirectMessages(self,
                          since_id=None,
                          max_id=None,
                          count=None,
                          include_entities=True,
                          skip_status=False,
                          full_text=False,
                          page=None,
                          return_json=False):
        """Returns a list of the direct messages sent to the authenticating user.

        Args:
          since_id:
            Returns results with an ID greater than (that is, more recent
            than) the specified ID. There are limits to the number of
            Tweets which can be accessed through the API. If the limit of
            Tweets has occurred since the since_id, the since_id will be
            forced to the oldest ID available. [Optional]
          max_id:
            Returns results with an ID less than (that is, older than) or
            equal to the specified ID. [Optional]
          count:
            Specifies the number of direct messages to try and retrieve, up to a
            maximum of 200. The value of count is best thought of as a limit to the
            number of Tweets to return because suspended or deleted content is
            removed after the count has been applied. [Optional]
          include_entities:
            The entities node will be omitted when set to False.
            [Optional]
          skip_status:
            When set to True statuses will not be included in the returned user
            objects. [Optional]
          full_text:
            When set to True full message will be included in the returned message
            object if message length is bigger than CHARACTER_LIMIT characters. [Optional]
          page:
            If you want more than 200 messages, you can use this and get 20 messages
            each time. You must recall it and increment the page value until it
            return nothing. You can't use count option with it. First value is 1 and
            not 0.
          return_json (bool, optional):
            If True JSON data will be returned, instead of twitter.User

        Returns:
          A sequence of twitter.DirectMessage instances
        """
        url = '%s/direct_messages.json' % self.base_url
        parameters = {
            'full_text': bool(full_text),
            'include_entities': bool(include_entities),
            'max_id': max_id,
            'since_id': since_id,
            'skip_status': bool(skip_status),
        }

        if count:
            parameters['count'] = enf_type('count', int, count)
        if page:
            parameters['page'] = enf_type('page', int, page)

        resp = self._RequestUrl(url, 'GET', data=parameters)
        data = self._ParseAndCheckTwitter(resp.content.decode('utf-8'))

        if return_json:
            return data
        else:
            return [DirectMessage.NewFromJsonDict(x) for x in data]

    def GetSentDirectMessages(self,
                              since_id=None,
                              max_id=None,
                              count=None,
                              page=None,
                              include_entities=True,
                              return_json=False):
        """Returns a list of the direct messages sent by the authenticating user.

        Args:
          since_id (int, optional):
            Returns results with an ID greater than (that is, more recent
            than) the specified ID. There are limits to the number of
            Tweets which can be accessed through the API. If the limit of
            Tweets has occured since the since_id, the since_id will be
            forced to the oldest ID available.
          max_id (int, optional):
            Returns results with an ID less than (that is, older than) or
            equal to the specified ID.
          count (int, optional):
            Specifies the number of direct messages to try and retrieve, up to a
            maximum of 200. The value of count is best thought of as a limit to the
            number of Tweets to return because suspended or deleted content is
            removed after the count has been applied.
          page (int, optional):
            Specifies the page of results to retrieve.
            Note: there are pagination limits. [Optional]
          include_entities (bool, optional):
            The entities node will be omitted when set to False.
          return_json (bool, optional):
            If True JSON data will be returned, instead of twitter.User

        Returns:
          A sequence of twitter.DirectMessage instances
        """
        url = '%s/direct_messages/sent.json' % self.base_url

        parameters = {
            'include_entities': bool(include_entities),
            'max_id': max_id,
            'since_id': since_id,
        }

        if count:
            parameters['count'] = enf_type('count', int, count)
        if page:
            parameters['page'] = enf_type('page', int, page)

        resp = self._RequestUrl(url, 'GET', data=parameters)
        data = self._ParseAndCheckTwitter(resp.content.decode('utf-8'))

        if return_json:
            return data
        else:
            return [DirectMessage.NewFromJsonDict(x) for x in data]

    def PostDirectMessage(self,
                          text,
                          user_id=None,
                          screen_name=None,
                          return_json=False):
        """Post a twitter direct message from the authenticated user.

        Args:
          text: The message text to be posted.
          user_id:
            The ID of the user who should receive the direct message.
          return_json (bool, optional):
            If True JSON data will be returned, instead of twitter.DirectMessage
        Returns:
          A twitter.DirectMessage instance representing the message posted
        """
        url = '%s/direct_messages/events/new.json' % self.base_url

        # Hack to allow some sort of backwards compatibility with older versions
        # part of the fix for Issue #587
        if user_id is None and screen_name is not None:
            user_id = self.GetUser(screen_name=screen_name).id

        event = {
            'event': {
                'type': 'message_create',
                'message_create': {
                    'target': {
                        'recipient_id': user_id,
                    },
                    'message_data': {
                        'text': text
                    }
                }
            }
        }

        resp = self._RequestUrl(url, 'POST', json=event)
        data = resp.json()

        if return_json:
            return data
        else:
            dm = DirectMessage(
                created_at=data['event']['created_timestamp'],
                id=data['event']['id'],
                recipient_id=data['event']['message_create']['target']['recipient_id'],
                sender_id=data['event']['message_create']['sender_id'],
                text=data['event']['message_create']['message_data']['text'],
            )
            dm._json = data
            return dm

    def DestroyDirectMessage(self, message_id, include_entities=True, return_json=False):
        """Destroys the direct message specified in the required ID parameter.

        The twitter.Api instance must be authenticated, and the
        authenticating user must be the recipient of the specified direct
        message.

        Args:
          message_id:
            The id of the direct message to be destroyed
          return_json (bool, optional):
            If True JSON data will be returned, instead of twitter.User

        Returns:
          A twitter.DirectMessage instance representing the message destroyed
        """
        url = '%s/direct_messages/destroy.json' % self.base_url
        data = {
            'id': enf_type('message_id', int, message_id),
            'include_entities': enf_type('include_entities', bool, include_entities)
        }

        resp = self._RequestUrl(url, 'POST', data=data)
        data = self._ParseAndCheckTwitter(resp.content.decode('utf-8'))

        if return_json:
            return data
        else:
            return DirectMessage.NewFromJsonDict(data)

    def CreateFriendship(self, user_id=None, screen_name=None, follow=True, retweets=True, **kwargs):
        """Befriends the user specified by the user_id or screen_name.

        Args:
          user_id (int, optional):
            A user_id to follow
          screen_name (str, optional)
            A screen_name to follow
          follow (bool, optional):
            Set to False to disable notifications for the target user
          retweets (bool, optional):
            Enable or disable retweets from the target user.

        Returns:
          A twitter.User instance representing the befriended user.
        """
        return self._AddOrEditFriendship(user_id=user_id,
                                         screen_name=screen_name,
                                         follow=follow,
                                         retweets=retweets,
                                         **kwargs)

    def _AddOrEditFriendship(self,
                             user_id=None,
                             screen_name=None,
                             uri_end='create',
                             follow_key='follow',
                             follow=True,
                             **kwargs):
        """Shared method for Create/Update Friendship."""
        url = '%s/friendships/%s.json' % (self.base_url, uri_end)
        data = {}
        if user_id:
            data['user_id'] = user_id
        elif screen_name:
            data['screen_name'] = screen_name
        else:
            raise TwitterError("Specify at least one of user_id or screen_name.")

        follow_json = json.dumps(follow)
        data['{}'.format(follow_key)] = follow_json
        data.update(**kwargs)

        resp = self._RequestUrl(url, 'POST', data=data)
        data = self._ParseAndCheckTwitter(resp.content.decode('utf-8'))

        return User.NewFromJsonDict(data)

    def UpdateFriendship(self,
                         user_id=None,
                         screen_name=None,
                         follow=True,
                         retweets=True,
                         **kwargs):
        """Updates a friendship with the user specified by the user_id or screen_name.

        Args:
          user_id (int, optional):
            A user_id to update
          screen_name (str, optional):
            A screen_name to update
          follow (bool, optional):
            Set to False to disable notifications for the target user
          retweets (bool, optional):
            Enable or disable retweets from the target user.
          device:
            Set to False to disable notifications for the target user

        Returns:
          A twitter.User instance representing the befriended user.
        """
        return self._AddOrEditFriendship(user_id=user_id,
                                         screen_name=screen_name,
                                         follow=follow,
                                         follow_key='device',
                                         retweets=retweets,
                                         uri_end='update',
                                         **kwargs)

    def DestroyFriendship(self, user_id=None, screen_name=None):
        """Discontinues friendship with a user_id or screen_name.

        Args:
          user_id:
            A user_id to unfollow [Optional]
          screen_name:
            A screen_name to unfollow [Optional]

        Returns:
          A twitter.User instance representing the discontinued friend.
        """
        url = '%s/friendships/destroy.json' % self.base_url
        data = {}
        if user_id:
            data['user_id'] = user_id
        elif screen_name:
            data['screen_name'] = screen_name
        else:
            raise TwitterError("Specify at least one of user_id or screen_name.")

        resp = self._RequestUrl(url, 'POST', data=data)
        data = self._ParseAndCheckTwitter(resp.content.decode('utf-8'))

        return User.NewFromJsonDict(data)

    def ShowFriendship(self,
                       source_user_id=None,
                       source_screen_name=None,
                       target_user_id=None,
                       target_screen_name=None):
        """Returns information about the relationship between the two users.

        Args:
          source_id:
            The user_id of the subject user [Optional]
          source_screen_name:
            The screen_name of the subject user [Optional]
          target_id:
            The user_id of the target user [Optional]
          target_screen_name:
            The screen_name of the target user [Optional]

        Returns:
          A Twitter Json structure.
        """
        url = '%s/friendships/show.json' % self.base_url
        data = {}
        if source_user_id:
            data['source_id'] = source_user_id
        elif source_screen_name:
            data['source_screen_name'] = source_screen_name
        else:
            raise TwitterError({'message': "Specify at least one of source_user_id or source_screen_name."})
        if target_user_id:
            data['target_id'] = target_user_id
        elif target_screen_name:
            data['target_screen_name'] = target_screen_name
        else:
            raise TwitterError({'message': "Specify at least one of target_user_id or target_screen_name."})

        resp = self._RequestUrl(url, 'GET', data=data)
        data = self._ParseAndCheckTwitter(resp.content.decode('utf-8'))

        return data

    def LookupFriendship(self,
                         user_id=None,
                         screen_name=None,
                         return_json=False):
        """Lookup friendship status for user to authed user.

        Users may be specified either as lists of either user_ids,
        screen_names, or twitter.User objects. The list of users that
        are queried is the union of all specified parameters.

        Up to 100 users may be specified.

        Args:
          user_id (int, User, or list of ints or Users, optional):
            A list of user_ids to retrieve extended information.
          screen_name (string, User, or list of strings or Users, optional):
            A list of screen_names to retrieve extended information.
          return_json (bool, optional):
            If True JSON data will be returned, instead of twitter.User

        Returns:
          list: A list of twitter.UserStatus instance representing the
          friendship status between the specified users and the authenticated
          user.
        """
        url = '%s/friendships/lookup.json' % (self.base_url)
        parameters = {}

        if user_id:
            if isinstance(user_id, (list, tuple)):
                uids = list()
                for user in user_id:
                    if isinstance(user, User):
                        uids.append(user.id)
                    else:
                        uids.append(enf_type('user_id', int, user))
                parameters['user_id'] = ",".join([str(uid) for uid in uids])
            else:
                if isinstance(user_id, User):
                    parameters['user_id'] = user_id.id
                else:
                    parameters['user_id'] = enf_type('user_id', int, user_id)
        if screen_name:
            if isinstance(screen_name, (list, tuple)):
                sn_list = list()
                for user in screen_name:
                    if isinstance(user, User):
                        sn_list.append(user.screen_name)
                    else:
                        sn_list.append(enf_type('screen_name', str, user))
                parameters['screen_name'] = ','.join(sn_list)
            else:
                if isinstance(screen_name, User):
                    parameters['screen_name'] = screen_name.screen_name
                else:
                    parameters['screen_name'] = enf_type('screen_name', str, screen_name)
        if not user_id and not screen_name:
            raise TwitterError("Specify at least one of user_id or screen_name.")

        resp = self._RequestUrl(url, 'GET', data=parameters)
        data = self._ParseAndCheckTwitter(resp.content.decode('utf-8'))

        if return_json:
            return data
        else:
            return [UserStatus.NewFromJsonDict(x) for x in data]

    def IncomingFriendship(self,
                           cursor=None,
                           stringify_ids=None):
        """Returns a collection of user IDs belonging to users who have
        pending request to follow the authenticated user.

        Args:
          cursor:
            breaks the ids into pages of no more than 5000.
          stringify_ids:
            returns the IDs as unicode strings. [Optional]

        Returns:
          A list of user IDs
        """
        url = '%s/friendships/incoming.json' % (self.base_url)
        parameters = {}
        if stringify_ids:
            parameters['stringify_ids'] = 'true'
        result = []

        total_count = 0
        while True:
            if cursor:
                try:
                    parameters['count'] = int(cursor)
                except ValueError:
                    raise TwitterError({'message': "cursor must be an integer"})
            resp = self._RequestUrl(url, 'GET', data=parameters)
            data = self._ParseAndCheckTwitter(resp.content.decode('utf-8'))
            result += [x for x in data['ids']]
            if 'next_cursor' in data:
                if data['next_cursor'] == 0 or data['next_cursor'] == data['previous_cursor']:
                    break
                else:
                    cursor = data['next_cursor']
                    total_count -= len(data['ids'])
                    if total_count < 1:
                        break
            else:
                break

        return result

    def OutgoingFriendship(self,
                           cursor=None,
                           stringify_ids=None):
        """Returns a collection of user IDs for every protected user
        for whom the authenticated user has a pending follow request.

        Args:
          cursor:
            breaks the ids into pages of no more than 5000.
          stringify_ids:
            returns the IDs as unicode strings. [Optional]

        Returns:
          A list of user IDs
        """
        url = '%s/friendships/outgoing.json' % (self.base_url)
        parameters = {}
        if stringify_ids:
            parameters['stringify_ids'] = 'true'
        result = []

        total_count = 0
        while True:
            if cursor:
                try:
                    parameters['count'] = int(cursor)
                except ValueError:
                    raise TwitterError({'message': "cursor must be an integer"})
            resp = self._RequestUrl(url, 'GET', data=parameters)
            data = self._ParseAndCheckTwitter(resp.content.decode('utf-8'))
            result += [x for x in data['ids']]
            if 'next_cursor' in data:
                if data['next_cursor'] == 0 or data['next_cursor'] == data['previous_cursor']:
                    break
                else:
                    cursor = data['next_cursor']
                    total_count -= len(data['ids'])
                    if total_count < 1:
                        break
            else:
                break

        return result

    def CreateFavorite(self,
                       status=None,
                       status_id=None,
                       include_entities=True):
        """Favorites the specified status object or id as the authenticating user.

        Returns the favorite status when successful.

        Args:
          status_id (int, optional):
            The id of the twitter status to mark as a favorite.
          status (twitter.Status, optional):
            The twitter.Status object to mark as a favorite.
          include_entities (bool, optional):
            The entities node will be omitted when set to False.

        Returns:
          A twitter.Status instance representing the newly-marked favorite.
        """
        url = '%s/favorites/create.json' % self.base_url
        data = {}
        if status_id:
            data['id'] = status_id
        elif status:
            data['id'] = status.id
        else:
            raise TwitterError({'message': "Specify status_id or status"})
        data['include_entities'] = enf_type('include_entities', bool, include_entities)

        resp = self._RequestUrl(url, 'POST', data=data)
        data = self._ParseAndCheckTwitter(resp.content.decode('utf-8'))

        return Status.NewFromJsonDict(data)

    def DestroyFavorite(self,
                        status=None,
                        status_id=None,
                        include_entities=True):
        """Un-Favorites the specified status object or id as the authenticating user.

        Returns the un-favorited status when successful.

        Args:
          status_id (int, optional):
            The id of the twitter status to mark as a favorite.
          status (twitter.Status, optional):
            The twitter.Status object to mark as a favorite.
          include_entities (bool, optional):
            The entities node will be omitted when set to False.

        Returns:
          A twitter.Status instance representing the newly-unmarked favorite.
        """
        url = '%s/favorites/destroy.json' % self.base_url
        data = {}

        if status_id:
            data['id'] = status_id
        elif status:
            data['id'] = status.id
        else:
            raise TwitterError({'message': "Specify status_id or status"})
        data['include_entities'] = enf_type('include_entities', bool, include_entities)

        resp = self._RequestUrl(url, 'POST', data=data)
        data = self._ParseAndCheckTwitter(resp.content.decode('utf-8'))

        return Status.NewFromJsonDict(data)

    def GetFavorites(self,
                     user_id=None,
                     screen_name=None,
                     count=None,
                     since_id=None,
                     max_id=None,
                     include_entities=True,
                     return_json=False):
        """Return a list of Status objects representing favorited tweets.

        Returns up to 200 most recent tweets for the authenticated user.

        Args:
          user_id (int, optional):
            Specifies the ID of the user for whom to return the
            favorites. Helpful for disambiguating when a valid user ID
            is also a valid screen name.
          screen_name (str, optional):
            Specifies the screen name of the user for whom to return the
            favorites. Helpful for disambiguating when a valid screen
            name is also a user ID.
          since_id (int, optional):
            Returns results with an ID greater than (that is, more recent
            than) the specified ID. There are limits to the number of
            Tweets which can be accessed through the API. If the limit of
            Tweets has occurred since the since_id, the since_id will be
            forced to the oldest ID available.
          max_id (int, optional):
            Returns only statuses with an ID less than (that is, older
            than) or equal to the specified ID.
          count (int, optional):
            Specifies the number of statuses to retrieve. May not be
            greater than 200.
          include_entities (bool, optional):
            The entities node will be omitted when set to False.
          return_json (bool, optional):
            If True JSON data will be returned, instead of twitter.User

        Returns:
          A sequence of Status instances, one for each favorited tweet up to count
        """
        parameters = {}
        url = '%s/favorites/list.json' % self.base_url
        if user_id:
            parameters['user_id'] = enf_type('user_id', int, user_id)
        elif screen_name:
            parameters['screen_name'] = screen_name
        if since_id:
            parameters['since_id'] = enf_type('since_id', int, since_id)
        if max_id:
            parameters['max_id'] = enf_type('max_id', int, max_id)
        if count:
            parameters['count'] = enf_type('count', int, count)
        parameters['include_entities'] = enf_type('include_entities', bool, include_entities)

        resp = self._RequestUrl(url, 'GET', data=parameters)
        data = self._ParseAndCheckTwitter(resp.content.decode('utf-8'))

        if return_json:
            return data
        else:
            return [Status.NewFromJsonDict(x) for x in data]

    def GetMentions(self,
                    count=None,
                    since_id=None,
                    max_id=None,
                    trim_user=False,
                    contributor_details=False,
                    include_entities=True,
                    return_json=False):
        """Returns the 20 most recent mentions (status containing @screen_name)
        for the authenticating user.

        Args:
          count:
            Specifies the number of tweets to try and retrieve, up to a maximum of
            200. The value of count is best thought of as a limit to the number of
            tweets to return because suspended or deleted content is removed after
            the count has been applied. [Optional]
          since_id:
            Returns results with an ID greater than (that is, more recent
            than) the specified ID. There are limits to the number of
            Tweets which can be accessed through the API. If the limit of
            Tweets has occurred since the since_id, the since_id will be
            forced to the oldest ID available. [Optional]
          max_id:
            Returns only statuses with an ID less than
            (that is, older than) the specified ID. [Optional]
          trim_user:
            When set to True, each tweet returned in a timeline will include a user
            object including only the status authors numerical ID. Omit this
            parameter to receive the complete user object. [Optional]
          contributor_details:
            If set to True, this parameter enhances the contributors element of the
            status response to include the screen_name of the contributor. By
            default only the user_id of the contributor is included. [Optional]
          include_entities:
            The entities node will be disincluded when set to False. [Optional]
          return_json (bool, optional):
            If True JSON data will be returned, instead of twitter.User

        Returns:
          A sequence of twitter.Status instances, one for each mention of the user.
        """
        url = '%s/statuses/mentions_timeline.json' % self.base_url

        parameters = {
            'contributor_details': bool(contributor_details),
            'include_entities': bool(include_entities),
            'max_id': max_id,
            'since_id': since_id,
            'trim_user': bool(trim_user),
        }

        if count:
            parameters['count'] = enf_type('count', int, count)

        resp = self._RequestUrl(url, 'GET', data=parameters)
        data = self._ParseAndCheckTwitter(resp.content.decode('utf-8'))

        if return_json:
            return data
        else:
            return [Status.NewFromJsonDict(x) for x in data]

    @staticmethod
    def _IDList(list_id, slug, owner_id, owner_screen_name):
        parameters = {}
        if list_id is not None:
            parameters['list_id'] = enf_type('list_id', int, list_id)
        elif slug is not None:
            parameters['slug'] = slug
            if owner_id is not None:
                parameters['owner_id'] = enf_type('owner_id', int, owner_id)
            elif owner_screen_name is not None:
                parameters['owner_screen_name'] = owner_screen_name
            else:
                raise TwitterError({'message': (
                    'If specifying a list by slug, an owner_id or '
                    'owner_screen_name must also be given.')})
        else:
            raise TwitterError({'message': (
                'Either list_id or slug and one of owner_id and '
                'owner_screen_name must be passed.')})

        return parameters

    def CreateList(self, name, mode=None, description=None):
        """Creates a new list with the give name for the authenticated user.

        Args:
          name (str):
            New name for the list
          mode (str, optional):
            'public' or 'private'. Defaults to 'public'.
          description (str, optional):
            Description of the list.

        Returns:
          twitter.list.List: A twitter.List instance representing the new list
        """
        url = '%s/lists/create.json' % self.base_url
        parameters = {'name': name}
        if mode is not None:
            parameters['mode'] = mode
        if description is not None:
            parameters['description'] = description

        resp = self._RequestUrl(url, 'POST', data=parameters)
        data = self._ParseAndCheckTwitter(resp.content.decode('utf-8'))

        return List.NewFromJsonDict(data)

    def DestroyList(self,
                    owner_screen_name=None,
                    owner_id=None,
                    list_id=None,
                    slug=None):
        """Destroys the list identified by list_id or slug and one of
        owner_screen_name or owner_id.

        Args:
          owner_screen_name (str, optional):
            The screen_name of the user who owns the list being requested
            by a slug.
          owner_id (int, optional):
            The user ID of the user who owns the list being requested
            by a slug.
          list_id (int, optional):
            The numerical id of the list.
          slug (str, optional):
            You can identify a list by its slug instead of its numerical id.
            If you decide to do so, note that you'll also have to specify
            the list owner using the owner_id or owner_screen_name parameters.

        Returns:
          twitter.list.List: A twitter.List instance representing the
          removed list.
        """
        url = '%s/lists/destroy.json' % self.base_url
        parameters = {}

        parameters.update(self._IDList(list_id=list_id,
                                       slug=slug,
                                       owner_id=owner_id,
                                       owner_screen_name=owner_screen_name))

        resp = self._RequestUrl(url, 'POST', data=parameters)
        data = self._ParseAndCheckTwitter(resp.content.decode('utf-8'))

        return List.NewFromJsonDict(data)

    def CreateSubscription(self,
                           owner_screen_name=None,
                           owner_id=None,
                           list_id=None,
                           slug=None):
        """Creates a subscription to a list by the authenticated user.

        Args:
          owner_screen_name (str, optional):
            The screen_name of the user who owns the list being requested
            by a slug.
          owner_id (int, optional):
            The user ID of the user who owns the list being requested
            by a slug.
          list_id (int, optional):
            The numerical id of the list.
          slug (str, optional):
            You can identify a list by its slug instead of its numerical id.
            If you decide to do so, note that you'll also have to specify
            the list owner using the owner_id or owner_screen_name parameters.

        Returns:
          twitter.user.User: A twitter.User instance representing the user subscribed
        """
        url = '%s/lists/subscribers/create.json' % self.base_url
        parameters = {}

        parameters.update(self._IDList(list_id=list_id,
                                       slug=slug,
                                       owner_id=owner_id,
                                       owner_screen_name=owner_screen_name))

        resp = self._RequestUrl(url, 'POST', data=parameters)
        data = self._ParseAndCheckTwitter(resp.content.decode('utf-8'))

        return User.NewFromJsonDict(data)

    def DestroySubscription(self,
                            owner_screen_name=None,
                            owner_id=None,
                            list_id=None,
                            slug=None):
        """Destroys the subscription to a list for the authenticated user.

        Args:
          owner_screen_name (str, optional):
            The screen_name of the user who owns the list being requested
            by a slug.
          owner_id (int, optional):
            The user ID of the user who owns the list being requested
            by a slug.
          list_id (int, optional):
            The numerical id of the list.
          slug (str, optional):
            You can identify a list by its slug instead of its numerical id.
            If you decide to do so, note that you'll also have to specify the
            list owner using the owner_id or owner_screen_name parameters.

        Returns:
          twitter.list.List: A twitter.List instance representing
          the removed list.
        """
        url = '%s/lists/subscribers/destroy.json' % (self.base_url)
        parameters = {}

        parameters.update(self._IDList(list_id=list_id,
                                       slug=slug,
                                       owner_id=owner_id,
                                       owner_screen_name=owner_screen_name))

        resp = self._RequestUrl(url, 'POST', data=parameters)
        data = self._ParseAndCheckTwitter(resp.content.decode('utf-8'))

        return List.NewFromJsonDict(data)

    def ShowSubscription(self,
                         owner_screen_name=None,
                         owner_id=None,
                         list_id=None,
                         slug=None,
                         user_id=None,
                         screen_name=None,
                         include_entities=False,
                         skip_status=False,
                         return_json=False):
        """Check if the specified user is a subscriber of the specified list.

        Returns the user if they are subscriber.

        Args:
          owner_screen_name (str, optional):
            The screen_name of the user who owns the list being requested
            by a slug.
          owner_id (int, optional):
            The user ID of the user who owns the list being requested
            by a slug.
          list_id (int, optional):
            The numerical ID of the list.
          slug (str, optional):
            You can identify a list by its slug instead of its numerical ID.
            If you decide to do so, note that you'll also have to specify
            the list owner using the owner_id or owner_screen_name parameters.
          user_id (int, optional):
            The user_id or a list of user_id's to add to the list.
            If not given, then screen_name is required.
          screen_name (str, optional):
            The screen_name or a list of screen_name's to add to the list.
            If not given, then user_id is required.
          include_entities (bool, optional):
            If False, the timeline will not contain additional metadata.
            Defaults to True.
          skip_status (bool, optional):
            If True the statuses will not be returned in the user items.
          return_json (bool, optional):
            If True JSON data will be returned, instead of twitter.User

        Returns:
          twitter.user.User: A twitter.User instance representing the user
          requested.
        """
        url = '%s/lists/subscribers/show.json' % (self.base_url)
        parameters = {}

        parameters.update(self._IDList(list_id=list_id,
                                       slug=slug,
                                       owner_id=owner_id,
                                       owner_screen_name=owner_screen_name))

        if user_id:
            parameters['user_id'] = enf_type('user_id', int, user_id)
        elif screen_name:
            parameters['screen_name'] = screen_name
        if skip_status:
            parameters['skip_status'] = True
        if include_entities:
            parameters['include_entities'] = True

        resp = self._RequestUrl(url, 'GET', data=parameters)
        data = self._ParseAndCheckTwitter(resp.content.decode('utf-8'))

        if return_json:
            return data
        else:
            return User.NewFromJsonDict(data)

    def GetSubscriptions(self,
                         user_id=None,
                         screen_name=None,
                         count=20,
                         cursor=-1,
                         return_json=False):
        """Obtain a collection of the lists the specified user is
        subscribed to. If neither user_id or screen_name is specified, the
        data returned will be for the authenticated user.

        The list will contain a maximum of 20 lists per page by default.

        Does not include the user's own lists.

        Args:
          user_id (int, optional):
            The ID of the user for whom to return results for.
          screen_name (str, optional):
            The screen name of the user for whom to return results for.
          count (int, optional):
           The amount of results to return per page.
           No more than 1000 results will ever be returned in a single
           page. Defaults to 20.
          cursor (int, optional):
            The "page" value that Twitter will use to start building the
            list sequence from. Use the value of -1 to start at the
            beginning. Twitter will return in the result the values for
            next_cursor and previous_cursor.
          return_json (bool, optional):
            If True JSON data will be returned, instead of twitter.User

        Returns:
          twitter.list.List: A sequence of twitter.List instances,
          one for each list
        """
        url = '%s/lists/subscriptions.json' % (self.base_url)
        parameters = {}
        parameters['cursor'] = enf_type('cursor', int, cursor)
        parameters['count'] = enf_type('count', int, count)
        if user_id is not None:
            parameters['user_id'] = enf_type('user_id', int, user_id)
        elif screen_name is not None:
            parameters['screen_name'] = screen_name

        resp = self._RequestUrl(url, 'GET', data=parameters)
        data = self._ParseAndCheckTwitter(resp.content.decode('utf-8'))

        if return_json:
            return data
        else:
            return [List.NewFromJsonDict(x) for x in data['lists']]

    def GetMemberships(self,
                       user_id=None,
                       screen_name=None,
                       count=20,
                       cursor=-1,
                       filter_to_owned_lists=False,
                       return_json=False):
        """Obtain the lists the specified user is a member of. If no user_id or
        screen_name is specified, the data returned will be for the
        authenticated user.

        Returns a maximum of 20 lists per page by default.

        Args:
          user_id (int, optional):
            The ID of the user for whom to return results for.
          screen_name (str, optional):
            The screen name of the user for whom to return
            results for.
          count (int, optional):
           The amount of results to return per page.
           No more than 1000 results will ever be returned in a single page.
           Defaults to 20.
          cursor (int, optional):
            The "page" value that Twitter will use to start building the list
            sequence from. Use the value of -1 to start at the beginning.
            Twitter will return in the result the values for next_cursor and
            previous_cursor.
          filter_to_owned_lists (bool, optional):
            Set to True to return only the lists the authenticating user
            owns, and the user specified by user_id or screen_name is a
            member of. Default value is False.
          return_json (bool, optional):
            If True JSON data will be returned, instead of twitter.User

        Returns:
          list: A list of twitter.List instances, one for each list in which
          the user specified by user_id or screen_name is a member
        """
        url = '%s/lists/memberships.json' % (self.base_url)
        parameters = {}
        if cursor is not None:
            parameters['cursor'] = enf_type('cursor', int, cursor)
        if count is not None:
            parameters['count'] = enf_type('count', int, count)
        if filter_to_owned_lists:
            parameters['filter_to_owned_lists'] = enf_type(
                'filter_to_owned_lists', bool, filter_to_owned_lists)

        if user_id is not None:
            parameters['user_id'] = enf_type('user_id', int, user_id)
        elif screen_name is not None:
            parameters['screen_name'] = screen_name

        resp = self._RequestUrl(url, 'GET', data=parameters)
        data = self._ParseAndCheckTwitter(resp.content.decode('utf-8'))

        if return_json:
            return data
        else:
            return [List.NewFromJsonDict(x) for x in data['lists']]

    def GetListsList(self,
                     screen_name=None,
                     user_id=None,
                     reverse=False,
                     return_json=False):
        """Returns all lists the user subscribes to, including their own.
        If no user_id or screen_name is specified, the data returned will be
        for the authenticated user.

        Args:
          screen_name (str, optional):
            Specifies the screen name of the user for whom to return the
            user_timeline. Helpful for disambiguating when a valid screen
            name is also a user ID.
          user_id (int, optional):
            Specifies the ID of the user for whom to return the
            user_timeline. Helpful for disambiguating when a valid user ID
            is also a valid screen name.
          reverse (bool, optional):
            If False, the owned lists will be returned first, othewise
            subscribed lists will be at the top. Returns a maximum of 100
            entries regardless. Defaults to False.
          return_json (bool, optional):
            If True JSON data will be returned, instead of twitter.User

        Returns:
          list: A sequence of twitter.List instances.
        """
        url = '%s/lists/list.json' % (self.base_url)
        parameters = {}
        if user_id:
            parameters['user_id'] = enf_type('user_id', int, user_id)
        elif screen_name:
            parameters['screen_name'] = screen_name
        if reverse:
            parameters['reverse'] = enf_type('reverse', bool, reverse)

        resp = self._RequestUrl(url, 'GET', data=parameters)
        data = self._ParseAndCheckTwitter(resp.content.decode('utf-8'))

        if return_json:
            return data
        else:
            return [List.NewFromJsonDict(x) for x in data]

    def GetListTimeline(self,
                        list_id=None,
                        slug=None,
                        owner_id=None,
                        owner_screen_name=None,
                        since_id=None,
                        max_id=None,
                        count=None,
                        include_rts=True,
                        include_entities=True,
                        return_json=False):
        """Fetch the sequence of Status messages for a given List ID.

        Args:
          list_id (int, optional):
            Specifies the ID of the list to retrieve.
          slug (str, optional):
            The slug name for the list to retrieve. If you specify None for the
            list_id, then you have to provide either a owner_screen_name or
            owner_id.
          owner_id (int, optional):
            Specifies the ID of the user for whom to return the
            list timeline. Helpful for disambiguating when a valid user ID
            is also a valid screen name.
          owner_screen_name (str, optional):
            Specifies the screen name of the user for whom to return the
            user_timeline. Helpful for disambiguating when a valid screen
            name is also a user ID.
          since_id (int, optional):
            Returns results with an ID greater than (that is, more recent than)
            the specified ID. There are limits to the number of Tweets which
            can be accessed through the API.
            If the limit of Tweets has occurred since the since_id, the
            since_id will be forced to the oldest ID available.
          max_id (int, optional):
            Returns only statuses with an ID less than (that is, older than) or
            equal to the specified ID.
          count (int, optional):
            Specifies the number of statuses to retrieve.
            May not be greater than 200.
          include_rts (bool, optional):
            If True, the timeline will contain native retweets (if they exist)
            in addition to the standard stream of tweets.
          include_entities (bool, optional):
            If False, the timeline will not contain additional metadata.
            Defaults to True.
          return_json (bool, optional):
            If True JSON data will be returned, instead of twitter.User

        Returns:
          list: A list of twitter.status.Status instances, one for each
          message up to count.
        """
        url = '%s/lists/statuses.json' % self.base_url
        parameters = {}

        parameters.update(self._IDList(list_id=list_id,
                                       slug=slug,
                                       owner_id=owner_id,
                                       owner_screen_name=owner_screen_name))

        if since_id:
            parameters['since_id'] = enf_type('since_id', int, since_id)
        if max_id:
            parameters['max_id'] = enf_type('max_id', int, max_id)
        if count:
            parameters['count'] = enf_type('count', int, count)
        if not include_rts:
            parameters['include_rts'] = enf_type('include_rts', bool, include_rts)
        if not include_entities:
            parameters['include_entities'] = enf_type('include_entities', bool, include_entities)

        resp = self._RequestUrl(url, 'GET', data=parameters)
        data = self._ParseAndCheckTwitter(resp.content.decode('utf-8'))

        if return_json:
            return data
        else:
            return [Status.NewFromJsonDict(x) for x in data]

    def GetListMembersPaged(self,
                            list_id=None,
                            slug=None,
                            owner_id=None,
                            owner_screen_name=None,
                            cursor=-1,
                            count=100,
                            skip_status=False,
                            include_entities=True):
        """Fetch the sequence of twitter.User instances, one for each member
        of the given list_id or slug.

        Args:
          list_id (int, optional):
            Specifies the ID of the list to retrieve.
          slug (str, optional):
            The slug name for the list to retrieve. If you specify None for the
            list_id, then you have to provide either a owner_screen_name or
            owner_id.
          owner_id (int, optional):
            Specifies the ID of the user for whom to return the
            list timeline. Helpful for disambiguating when a valid user ID
            is also a valid screen name.
          owner_screen_name (str, optional):
            Specifies the screen name of the user for whom to return the
            user_timeline. Helpful for disambiguating when a valid screen
            name is also a user ID.
          cursor (int, optional):
            Should be set to -1 for the initial call and then is used to
            control what result page Twitter returns.
          skip_status (bool, optional):
            If True the statuses will not be returned in the user items.
          include_entities (bool, optional):
            If False, the timeline will not contain additional metadata.
            Defaults to True.

        Returns:
          list: A sequence of twitter.user.User instances, one for each
          member of the twitter.list.List.
        """
        url = '%s/lists/members.json' % self.base_url
        parameters = {}

        parameters.update(self._IDList(list_id=list_id,
                                       slug=slug,
                                       owner_id=owner_id,
                                       owner_screen_name=owner_screen_name))

        if count:
            parameters['count'] = enf_type('count', int, count)
        if cursor:
            parameters['cursor'] = enf_type('cursor', int, cursor)

        parameters['skip_status'] = enf_type('skip_status', bool, skip_status)
        parameters['include_entities'] = enf_type('include_entities', bool, include_entities)

        resp = self._RequestUrl(url, 'GET', data=parameters)
        data = self._ParseAndCheckTwitter(resp.content.decode('utf-8'))
        next_cursor = data.get('next_cursor', 0)
        previous_cursor = data.get('previous_cursor', 0)
        users = [User.NewFromJsonDict(user) for user in data.get('users', [])]

        return next_cursor, previous_cursor, users

    def GetListMembers(self,
                       list_id=None,
                       slug=None,
                       owner_id=None,
                       owner_screen_name=None,
                       skip_status=False,
                       include_entities=False):
        """Fetch the sequence of twitter.User instances, one for each member
        of the given list_id or slug.

        Args:
          list_id (int, optional):
            Specifies the ID of the list to retrieve.
          slug (str, optional):
            The slug name for the list to retrieve. If you specify None for the
            list_id, then you have to provide either a owner_screen_name or
            owner_id.
          owner_id (int, optional):
            Specifies the ID of the user for whom to return the
            list timeline. Helpful for disambiguating when a valid user ID
            is also a valid screen name.
          owner_screen_name (str, optional):
            Specifies the screen name of the user for whom to return the
            user_timeline. Helpful for disambiguating when a valid screen
            name is also a user ID.
          skip_status (bool, optional):
            If True the statuses will not be returned in the user items.
          include_entities (bool, optional):
            If False, the timeline will not contain additional metadata.
            Defaults to True.

        Returns:
          list: A sequence of twitter.user.User instances, one for each
          member of the twitter.list.List.
        """
        cursor = -1
        result = []
        while True:
            next_cursor, previous_cursor, users = self.GetListMembersPaged(
                list_id=list_id,
                slug=slug,
                owner_id=owner_id,
                owner_screen_name=owner_screen_name,
                cursor=cursor,
                skip_status=skip_status,
                include_entities=include_entities)
            result += users

            if next_cursor == 0 or next_cursor == previous_cursor:
                break
            else:
                cursor = next_cursor

        return result

    def CreateListsMember(self,
                          list_id=None,
                          slug=None,
                          user_id=None,
                          screen_name=None,
                          owner_screen_name=None,
                          owner_id=None):
        """Add a new member (or list of members) to the specified list.

        Args:
          list_id (int, optional):
            The numerical id of the list.
          slug (str, optional):
            You can identify a list by its slug instead of its numerical id.
            If you decide to do so, note that you'll also have to specify the
            list owner using the owner_id or owner_screen_name parameters.
          user_id (int, optional):
            The user_id or a list of user_id's to add to the list.
            If not given, then screen_name is required.
          screen_name (str, optional):
            The screen_name or a list of screen_name's to add to the list.
            If not given, then user_id is required.
          owner_screen_name (str, optional):
            The screen_name of the user who owns the list being requested by
            a slug.
          owner_id (int, optional):
            The user ID of the user who owns the list being requested by
            a slug.

        Returns:
          twitter.list.List: A twitter.List instance representing the list
          subscribed to.
        """
        is_list = False
        parameters = {}

        parameters.update(self._IDList(list_id=list_id,
                                       slug=slug,
                                       owner_id=owner_id,
                                       owner_screen_name=owner_screen_name))

        if user_id:
            if isinstance(user_id, list) or isinstance(user_id, tuple):
                is_list = True
                uids = [str(enf_type('user_id', int, uid)) for uid in user_id]
                parameters['user_id'] = ','.join(uids)
            else:
                parameters['user_id'] = enf_type('user_id', int, user_id)

        elif screen_name:
            if isinstance(screen_name, list) or isinstance(screen_name, tuple):
                is_list = True
                parameters['screen_name'] = ','.join(screen_name)
            else:
                parameters['screen_name'] = screen_name
        if is_list:
            url = '%s/lists/members/create_all.json' % self.base_url
        else:
            url = '%s/lists/members/create.json' % self.base_url

        resp = self._RequestUrl(url, 'POST', data=parameters)
        data = self._ParseAndCheckTwitter(resp.content.decode('utf-8'))

        return List.NewFromJsonDict(data)

    def DestroyListsMember(self,
                           list_id=None,
                           slug=None,
                           owner_screen_name=None,
                           owner_id=None,
                           user_id=None,
                           screen_name=None):
        """Destroys the subscription to a list for the authenticated user.

        Args:
          list_id (int, optional):
            The numerical id of the list.
          slug (str, optional):
            You can identify a list by its slug instead of its numerical id.
            If you decide to do so, note that you'll also have to specify
            the list owner using the owner_id or owner_screen_name parameters.
          owner_screen_name (str, optional):
            The screen_name of the user who owns the list being requested by a
            slug.
          owner_id (int, optional):
            The user ID of the user who owns the list being requested by a slug.
          user_id (int, optional):
            The user_id or a list of user_id's to remove from the list.
            If not given, then screen_name is required.
          screen_name (str, optional):
            The screen_name or a list of Screen_name's to remove from the list.
            If not given, then user_id is required.

        Returns:
          twitter.list.List: A twitter.List instance representing the
          removed list.
        """
        is_list = False
        parameters = {}

        parameters.update(self._IDList(list_id=list_id,
                                       slug=slug,
                                       owner_id=owner_id,
                                       owner_screen_name=owner_screen_name))

        if user_id:
            if isinstance(user_id, list) or isinstance(user_id, tuple):
                is_list = True
                uids = [str(enf_type('user_id', int, uid)) for uid in user_id]
                parameters['user_id'] = ','.join(uids)
            else:
                parameters['user_id'] = int(user_id)
        elif screen_name:
            if isinstance(screen_name, list) or isinstance(screen_name, tuple):
                is_list = True
                parameters['screen_name'] = ','.join(screen_name)
            else:
                parameters['screen_name'] = screen_name

        if is_list:
            url = '%s/lists/members/destroy_all.json' % self.base_url
        else:
            url = '%s/lists/members/destroy.json' % self.base_url

        resp = self._RequestUrl(url, 'POST', data=parameters)
        data = self._ParseAndCheckTwitter(resp.content.decode('utf-8'))

        return List.NewFromJsonDict(data)

    def GetListsPaged(self,
                      user_id=None,
                      screen_name=None,
                      cursor=-1,
                      count=20):
        """ Fetch the sequence of lists for a user. If no user_id or
        screen_name is passed, the data returned will be for the
        authenticated user.

        Args:
          user_id (int, optional):
            The ID of the user for whom to return results for.
          screen_name (str, optional):
            The screen name of the user for whom to return results
            for.
          count (int, optional):
            The amount of results to return per page. No more than 1000 results
            will ever be returned in a single page. Defaults to 20.
          cursor (int, optional):
            The "page" value that Twitter will use to start building the list
            sequence from. Use the value of -1 to start at the beginning.
            Twitter will return in the result the values for next_cursor and
            previous_cursor.

        Returns:
          next_cursor (int), previous_cursor (int), list of twitter.List
          instances, one for each list
        """
        url = '%s/lists/ownerships.json' % self.base_url
        parameters = {}
        if user_id is not None:
            parameters['user_id'] = enf_type('user_id', int, user_id)
        elif screen_name is not None:
            parameters['screen_name'] = screen_name

        if count is not None:
            parameters['count'] = enf_type('count', int, count)

        parameters['cursor'] = enf_type('cursor', int, cursor)

        resp = self._RequestUrl(url, 'GET', data=parameters)
        data = self._ParseAndCheckTwitter(resp.content.decode('utf-8'))

        next_cursor = data.get('next_cursor', 0)
        previous_cursor = data.get('previous_cursor', 0)
        lists = [List.NewFromJsonDict(x) for x in data.get('lists', [])]

        return next_cursor, previous_cursor, lists

    def GetLists(self,
                 user_id=None,
                 screen_name=None):
        """Fetch the sequence of lists for a user. If no user_id or screen_name
        is passed, the data returned will be for the authenticated user.

        Args:
          user_id:
            The ID of the user for whom to return results for. [Optional]
          screen_name:
            The screen name of the user for whom to return results
            for. [Optional]
          count:
            The amount of results to return per page.
            No more than 1000 results will ever be returned in a single page.
            Defaults to 20. [Optional]
          cursor:
            The "page" value that Twitter will use to start building the list
            sequence from. Use the value of -1 to start at the beginning.
            Twitter will return in the result the values for next_cursor and
            previous_cursor. [Optional]

        Returns:
          A sequence of twitter.List instances, one for each list
        """
        result = []
        cursor = -1

        while True:
            next_cursor, prev_cursor, lists = self.GetListsPaged(
                user_id=user_id,
                screen_name=screen_name,
                cursor=cursor)
            result += lists
            if next_cursor == 0 or next_cursor == prev_cursor:
                break
            else:
                cursor = next_cursor

        return result

    def UpdateProfile(self,
                      name=None,
                      profileURL=None,
                      location=None,
                      description=None,
                      profile_link_color=None,
                      include_entities=False,
                      skip_status=False):
        """Update's the authenticated user's profile data.

        Args:
          name (str, optional):
            Full name associated with the profile.
          profileURL (str, optional):
            URL associated with the profile.
            Will be prepended with "http://" if not present.
          location (str, optional):
            The city or country describing where the user of the account is located.
            The contents are not normalized or geocoded in any way.
          description (str, optional):
            A description of the user owning the account.
          profile_link_color (str, optional):
            hex value of profile color theme. formated without '#' or '0x'. Ex:  FF00FF
          include_entities (bool, optional):
            The entities node will be omitted when set to False.
          skip_status (bool, optional):
            When set to either True, t or 1 then statuses will not be included
            in the returned user objects.

        Returns:
          A twitter.User instance representing the modified user.
        """
        url = '%s/account/update_profile.json' % (self.base_url)
        data = {
            'name': name,
            'url': profileURL,
            'location': location,
            'description': description,
            'profile_link_color': profile_link_color,
            'include_entities': include_entities,
            'skip_status': skip_status,
        }

        resp = self._RequestUrl(url, 'POST', data=data)
        data = self._ParseAndCheckTwitter(resp.content.decode('utf-8'))

        return User.NewFromJsonDict(data)

    def UpdateImage(self,
                    image,
                    include_entities=False,
                    skip_status=False):
        """Update a User's profile image. Change may not be immediately
        reflected due to image processing on Twitter's side.

        Args:
            image (str):
                Location of local image file to use.
            include_entities (bool, optional):
                Include the entities node in the return data.
            skip_status (bool, optional):
                Include the User's last Status in the User entity returned.

        Returns:
            (twitter.models.User): Updated User object.
        """

        url = '%s/account/update_profile_image.json' % (self.base_url)
        with open(image, 'rb') as image_file:
            encoded_image = base64.b64encode(image_file.read())
        data = {
            'image': encoded_image
        }
        if include_entities:
            data['include_entities'] = 1
        if skip_status:
            data['skip_status'] = 1

        resp = self._RequestUrl(url, 'POST', data=data)

        if resp.status_code in [200, 201, 202]:
            return True
        if resp.status_code == 400:
            raise TwitterError({'message': "Image data could not be processed"})
        if resp.status_code == 422:
            raise TwitterError({'message': "The image could not be resized or is too large."})

    def UpdateBanner(self,
                     image,
                     include_entities=False,
                     skip_status=False):
        """Updates the authenticated users profile banner.

        Args:
          image:
            Location of image in file system
          include_entities:
            If True, each tweet will include a node called "entities."
            This node offers a variety of metadata about the tweet in a
            discrete structure, including: user_mentions, urls, and hashtags.
            [Optional]

        Returns:
          A twitter.List instance representing the list subscribed to
        """
        url = '%s/account/update_profile_banner.json' % (self.base_url)
        with open(image, 'rb') as image_file:
            encoded_image = base64.b64encode(image_file.read())
        data = {
            # When updated for API v1.1 use image, not banner
            # https://dev.twitter.com/docs/api/1.1/post/account/update_profile_banner
            # 'image': encoded_image
            'banner': encoded_image
        }
        if include_entities:
            data['include_entities'] = 1
        if skip_status:
            data['skip_status'] = 1

        resp = self._RequestUrl(url, 'POST', data=data)

        if resp.status_code in [200, 201, 202]:
            return True
        if resp.status_code == 400:
            raise TwitterError({'message': "Image data could not be processed"})
        if resp.status_code == 422:
            raise TwitterError({'message': "The image could not be resized or is too large."})

        raise TwitterError({'message': "Unkown banner image upload issue"})

    def GetStreamSample(self, delimited=False, stall_warnings=True):
        """Returns a small sample of public statuses.

        Args:
          delimited:
            Specifies a message length. [Optional]
          stall_warnings:
            Set to True to have Twitter deliver stall warnings. [Optional]

        Returns:
          A Twitter stream
        """
        url = '%s/statuses/sample.json' % self.stream_url
        parameters = {
            'delimited': bool(delimited),
            'stall_warnings': bool(stall_warnings)
        }
        resp = self._RequestStream(url, 'GET', data=parameters)
        for line in resp.iter_lines():
            if line:
                data = self._ParseAndCheckTwitter(line.decode('utf-8'))
                yield data

    def GetStreamFilter(self,
                        follow=None,
                        track=None,
                        locations=None,
                        languages=None,
                        delimited=None,
                        stall_warnings=None,
                        filter_level=None):
        """Returns a filtered view of public statuses.

        Args:
          follow:
            A list of user IDs to track. [Optional]
          track:
            A list of expressions to track. [Optional]
          locations:
            A list of Longitude,Latitude pairs (as strings) specifying
            bounding boxes for the tweets' origin. [Optional]
          delimited:
            Specifies a message length. [Optional]
          stall_warnings:
            Set to True to have Twitter deliver stall warnings. [Optional]
          languages:
            A list of Languages.
            Will only return Tweets that have been detected as being
            written in the specified languages. [Optional]
          filter_level:
            Specifies level of filtering applied to stream.
            Set to None, 'low' or 'medium'. [Optional]

        Returns:
          A twitter stream
        """
        if all((follow is None, track is None, locations is None)):
            raise ValueError({'message': "No filter parameters specified."})
        url = '%s/statuses/filter.json' % self.stream_url
        data = {}
        if follow is not None:
            data['follow'] = ','.join(follow)
        if track is not None:
            data['track'] = ','.join(track)
        if locations is not None:
            data['locations'] = ','.join(locations)
        if delimited is not None:
            data['delimited'] = str(delimited)
        if stall_warnings is not None:
            data['stall_warnings'] = str(stall_warnings)
        if languages is not None:
            data['language'] = ','.join(languages)
        if filter_level is not None:
            data['filter_level'] = filter_level

        resp = self._RequestStream(url, 'POST', data=data)
        for line in resp.iter_lines():
            if line:
                data = self._ParseAndCheckTwitter(line.decode('utf-8'))
                yield data

    def GetUserStream(self,
                      replies='all',
                      withuser='user',
                      track=None,
                      locations=None,
                      delimited=None,
                      stall_warnings=None,
                      stringify_friend_ids=False,
                      filter_level=None,
                      session=None,
                      include_keepalive=False):
        """Returns the data from the user stream.

        Args:
          replies:
            Specifies whether to return additional @replies in the stream.
            Defaults to 'all'.
          withuser:
            Specifies whether to return information for just the authenticating
            user, or include messages from accounts the user follows. [Optional]
          track:
            A list of expressions to track. [Optional]
          locations:
            A list of Latitude,Longitude pairs (as strings) specifying
            bounding boxes for the tweets' origin. [Optional]
          delimited:
            Specifies a message length. [Optional]
          stall_warnings:
            Set to True to have Twitter deliver stall warnings. [Optional]
          stringify_friend_ids:
            Specifies whether to send the friends list preamble as an array of
            integers or an array of strings. [Optional]
          filter_level:
            Specifies level of filtering applied to stream.
            Set to None, low or medium. [Optional]

        Returns:
          A twitter stream
        """
        url = 'https://userstream.twitter.com/1.1/user.json'
        data = {}
        if stringify_friend_ids:
            data['stringify_friend_ids'] = 'true'
        if replies is not None:
            data['replies'] = replies
        if withuser is not None:
            data['with'] = withuser
        if track is not None:
            data['track'] = ','.join(track)
        if locations is not None:
            data['locations'] = ','.join(locations)
        if delimited is not None:
            data['delimited'] = str(delimited)
        if stall_warnings is not None:
            data['stall_warnings'] = str(stall_warnings)
        if filter_level is not None:
            data['filter_level'] = filter_level

        resp = self._RequestStream(url, 'POST', data=data, session=session)
        # The Twitter streaming API sends keep-alive newlines every 30s if there has not been other
        # traffic, and specifies that streams should only be reset after three keep-alive ticks.
        #
        # The original implementation of this API didn't expose keep-alive signals to the user,
        # making it difficult to determine whether the connection should be hung up or not.
        #
        # https://dev.twitter.com/streaming/overview/connecting
        for line in resp.iter_lines():
            if line:
                data = self._ParseAndCheckTwitter(line.decode('utf-8'))
                yield data
            elif include_keepalive:
                yield None

    def VerifyCredentials(self, include_entities=None, skip_status=None, include_email=None):
        """Returns a twitter.User instance if the authenticating user is valid.

        Args:
          include_entities:
            Specifies whether to return additional @replies in the stream.
          skip_status:
            When set to either true, t or 1 statuses will not be included in the
            returned user object.
          include_email:
            Use of this parameter requires whitelisting.
            When set to true email will be returned in the user objects as a string.
            If the user does not have an email address on their account, or if the
            email address is un-verified, null will be returned. If your app is
            not whitelisted, then the 'email' key will not be present in the json
            response.

        Returns:
          A twitter.User instance representing that user if the
          credentials are valid, None otherwise.
        """
        url = '%s/account/verify_credentials.json' % self.base_url
        data = {
            'include_entities': enf_type('include_entities', bool, include_entities),
            'skip_status': enf_type('skip_status', bool, skip_status),
            'include_email': 'true' if enf_type('include_email', bool, include_email) else 'false',
        }

        resp = self._RequestUrl(url, 'GET', data)
        data = self._ParseAndCheckTwitter(resp.content.decode('utf-8'))

        return User.NewFromJsonDict(data)

    def SetCache(self, cache):
        """Override the default cache.  Set to None to prevent caching.

        Args:
          cache:
            An instance that supports the same API as the twitter._FileCache
        """
        if cache == DEFAULT_CACHE:
            self._cache = _FileCache()
        else:
            self._cache = cache

    def SetUrllib(self, urllib):
        """Override the default urllib implementation.

        Args:
          urllib:
            An instance that supports the same API as the urllib2 module
        """
        self._urllib = urllib

    def SetCacheTimeout(self, cache_timeout):
        """Override the default cache timeout.

        Args:
          cache_timeout:
            Time, in seconds, that responses should be reused.
        """
        self._cache_timeout = cache_timeout

    def SetUserAgent(self, user_agent):
        """Override the default user agent.

        Args:
          user_agent:
            A string that should be send to the server as the user-agent.
        """
        self._request_headers['User-Agent'] = user_agent

    def SetXTwitterHeaders(self, client, url, version):
        """Set the X-Twitter HTTP headers that will be sent to the server.

        Args:
          client:
             The client name as a string.  Will be sent to the server as
             the 'X-Twitter-Client' header.
          url:
             The URL of the meta.xml as a string.  Will be sent to the server
             as the 'X-Twitter-Client-URL' header.
          version:
             The client version as a string.  Will be sent to the server
             as the 'X-Twitter-Client-Version' header.
        """
        self._request_headers['X-Twitter-Client'] = client
        self._request_headers['X-Twitter-Client-URL'] = url
        self._request_headers['X-Twitter-Client-Version'] = version

    def SetSource(self, source):
        """Suggest the "from source" value to be displayed on the Twitter web site.

        The value of the 'source' parameter must be first recognized by
        the Twitter server.

        New source values are authorized on a case by case basis by the
        Twitter development team.

        Args:
          source:
            The source name as a string.  Will be sent to the server as
            the 'source' parameter.
        """
        self._default_params['source'] = source

    def InitializeRateLimit(self):
        """ Make a call to the Twitter API to get the rate limit
        status for the currently authenticated user or application.

        Returns:
            None.

        """
        _sleep = self.sleep_on_rate_limit
        if self.sleep_on_rate_limit:
            self.sleep_on_rate_limit = False

        url = '%s/application/rate_limit_status.json' % self.base_url

        resp = self._RequestUrl(url, 'GET')  # No-Cache
        data = self._ParseAndCheckTwitter(resp.content.decode('utf-8'))

        self.sleep_on_rate_limit = _sleep
        self.rate_limit = RateLimit(**data)

    def CheckRateLimit(self, url):
        """ Checks a URL to see the rate limit status for that endpoint.

        Args:
            url (str):
                URL to check against the current rate limits.

        Returns:
            namedtuple: EndpointRateLimit namedtuple.

        """
        if not self.rate_limit.__dict__.get('resources', None):
            self.InitializeRateLimit()

        if url:
            limit = self.rate_limit.get_limit(url)

        return limit

    def _BuildUrl(self, url, path_elements=None, extra_params=None):
        # Break url into constituent parts
        (scheme, netloc, path, params, query, fragment) = urlparse(url)

        # Add any additional path elements to the path
        if path_elements:
            # Filter out the path elements that have a value of None
            filtered_elements = [i for i in path_elements if i]
            if not path.endswith('/'):
                path += '/'
            path += '/'.join(filtered_elements)

        # Add any additional query parameters to the query string
        if extra_params and len(extra_params) > 0:
            extra_query = self._EncodeParameters(extra_params)
            # Add it to the existing query
            if query:
                query += '&' + extra_query
            else:
                query = extra_query

        # Return the rebuilt URL
        return urlunparse((scheme, netloc, path, params, query, fragment))

    def _InitializeRequestHeaders(self, request_headers):
        if request_headers:
            self._request_headers = request_headers
        else:
            self._request_headers = {}

    def _InitializeUserAgent(self):
        user_agent = 'Python-urllib/%s (python-twitter/%s)' % \
                     (urllib_version, __version__)
        self.SetUserAgent(user_agent)

    def _InitializeDefaultParameters(self):
        self._default_params = {}

    @staticmethod
    def _DecompressGzippedResponse(response):
        raw_data = response.read()
        if response.headers.get('content-encoding', None) == 'gzip':
            url_data = gzip.GzipFile(fileobj=io.StringIO(raw_data)).read()
        else:
            url_data = raw_data
        return url_data

    @staticmethod
    def _EncodeParameters(parameters):
        """Return a string in key=value&key=value form.

        Values of None are not included in the output string.

        Args:
          parameters (dict): dictionary of query parameters to be converted into a
          string for encoding and sending to Twitter.

        Returns:
          A URL-encoded string in "key=value&key=value" form
        """
        if parameters is None:
            return None
        if not isinstance(parameters, dict):
            raise TwitterError("`parameters` must be a dict.")
        else:
            params = dict()
            for k, v in parameters.items():
                if v is not None:
                    if getattr(v, 'encode', None):
                        v = v.encode('utf8')
                    params.update({k: v})
            return urlencode(params)

    def _ParseAndCheckTwitter(self, json_data):
        """Try and parse the JSON returned from Twitter and return
        an empty dictionary if there is any error.

        This is a purely defensive check because during some Twitter
        network outages it will return an HTML failwhale page.
        """
        try:
            data = json.loads(json_data)
        except ValueError:
            if "<title>Twitter / Over capacity</title>" in json_data:
                raise TwitterError({'message': "Capacity Error"})
            if "<title>Twitter / Error</title>" in json_data:
                raise TwitterError({'message': "Technical Error"})
            if "Exceeded connection limit for user" in json_data:
                raise TwitterError({'message': "Exceeded connection limit for user"})
            if "Error 401 Unauthorized" in json_data:
                raise TwitterError({'message': "Unauthorized"})
            raise TwitterError({'Unknown error': '{0}'.format(json_data)})
        self._CheckForTwitterError(data)
        return data

    @staticmethod
    def _CheckForTwitterError(data):
        """Raises a TwitterError if twitter returns an error message.

        Args:
            data (dict):
                A python dict created from the Twitter json response

        Raises:
            (twitter.TwitterError): TwitterError wrapping the twitter error
            message if one exists.
        """
        # Twitter errors are relatively unlikely, so it is faster
        # to check first, rather than try and catch the exception
        if 'error' in data:
            raise TwitterError(data['error'])
        if 'errors' in data:
            raise TwitterError(data['errors'])

    def _RequestChunkedUpload(self, url, headers, data):
        try:
            return requests.post(
                url,
                headers=headers,
                data=data,
                auth=self.__auth,
                timeout=self._timeout,
                proxies=self.proxies
            )
        except requests.RequestException as e:
            raise TwitterError(str(e))

    def _RequestUrl(self, url, verb, data=None, json=None, enforce_auth=True):
        """Request a url.

        Args:
            url:
                The web location we want to retrieve.
            verb:
                Either POST or GET.
            data:
                A dict of (str, unicode) key/value pairs.

        Returns:
            A JSON object.
        """
        if enforce_auth:
            if not self.__auth:
                raise TwitterError("The twitter.Api instance must be authenticated.")

            if url and self.sleep_on_rate_limit:
                limit = self.CheckRateLimit(url)

                if limit.remaining == 0:
                    try:
                        stime = max(int(limit.reset - time.time()) + 10, 0)
                        logger.debug('Rate limited requesting [%s], sleeping for [%s]', url, stime)
                        time.sleep(stime)
                    except ValueError:
                        pass

        if not data:
            data = {}

        if verb == 'POST':
            if data:
                if 'media_ids' in data:
                    url = self._BuildUrl(url, extra_params={'media_ids': data['media_ids']})
                    resp = self._session.post(url, data=data, auth=self.__auth, timeout=self._timeout, proxies=self.proxies)
                elif 'media' in data:
                    resp = self._session.post(url, files=data, auth=self.__auth, timeout=self._timeout, proxies=self.proxies)
                else:
                    resp = self._session.post(url, data=data, auth=self.__auth, timeout=self._timeout, proxies=self.proxies)
            elif json:
                resp = self._session.post(url, json=json, auth=self.__auth, timeout=self._timeout, proxies=self.proxies)
            else:
                resp = 0  # POST request, but without data or json

        elif verb == 'GET':
            data['tweet_mode'] = self.tweet_mode
            url = self._BuildUrl(url, extra_params=data)
            resp = self._session.get(url, auth=self.__auth, timeout=self._timeout, proxies=self.proxies)

        else:
            resp = 0  # if not a POST or GET request

        if url and self.rate_limit:
            limit = resp.headers.get('x-rate-limit-limit', 0)
            remaining = resp.headers.get('x-rate-limit-remaining', 0)
            reset = resp.headers.get('x-rate-limit-reset', 0)

            self.rate_limit.set_limit(url, limit, remaining, reset)

        return resp

    def _RequestStream(self, url, verb, data=None, session=None):
        """Request a stream of data.

           Args:
             url:
               The web location we want to retrieve.
             verb:
               Either POST or GET.
             data:
               A dict of (str, unicode) key/value pairs.

           Returns:
             A twitter stream.
        """
        session = session or requests.Session()

        if verb == 'POST':
            try:
                return session.post(url, data=data, stream=True,
                                    auth=self.__auth,
                                    timeout=self._timeout,
                                    proxies=self.proxies)
            except requests.RequestException as e:
                raise TwitterError(str(e))
        if verb == 'GET':
            url = self._BuildUrl(url, extra_params=data)
            try:
                return session.get(url, stream=True, auth=self.__auth,
                                   timeout=self._timeout, proxies=self.proxies)
            except requests.RequestException as e:
                raise TwitterError(str(e))
        return 0  # if not a POST or GET request
