#!/usr/bin/env python
#
# vim: sw=2 ts=2 sts=2
#
# Copyright 2007 The Python-Twitter Developers
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

'''A library that provides a Python interface to the Twitter API'''

__author__ = 'python-twitter@googlegroups.com'
__version__ = '1.0.1'


import base64
import calendar
import datetime
import httplib
import os
import rfc822
import sys
import tempfile
import textwrap
import time
import urllib
import urllib2
import urlparse
import gzip
import StringIO

try:
  # Python >= 2.6
  import json as simplejson
except ImportError:
  try:
    # Python < 2.6
    import simplejson as simplejson
  except ImportError:
    try:
      # Google App Engine
      from django.utils import simplejson
    except ImportError:
      raise ImportError, "Unable to load a json library"

# parse_qsl moved to urlparse module in v2.6
try:
  from urlparse import parse_qsl, parse_qs
except ImportError:
  from cgi import parse_qsl, parse_qs

try:
  from hashlib import md5
except ImportError:
  from md5 import md5

import oauth2 as oauth


CHARACTER_LIMIT = 140

# A singleton representing a lazily instantiated FileCache.
DEFAULT_CACHE = object()

REQUEST_TOKEN_URL = 'https://api.twitter.com/oauth/request_token'
ACCESS_TOKEN_URL  = 'https://api.twitter.com/oauth/access_token'
AUTHORIZATION_URL = 'https://api.twitter.com/oauth/authorize'
SIGNIN_URL        = 'https://api.twitter.com/oauth/authenticate'


class TwitterError(Exception):
  '''Base class for Twitter errors'''

  @property
  def message(self):
    '''Returns the first argument used to construct this error.'''
    return self.args[0]


class Status(object):
  '''A class representing the Status structure used by the twitter API.

  The Status structure exposes the following properties:

    status.created_at
    status.created_at_in_seconds # read only
    status.favorited
    status.favorite_count
    status.in_reply_to_screen_name
    status.in_reply_to_user_id
    status.in_reply_to_status_id
    status.truncated
    status.source
    status.id
    status.text
    status.location
    status.relative_created_at # read only
    status.user
    status.urls
    status.user_mentions
    status.hashtags
    status.geo
    status.place
    status.coordinates
    status.contributors
  '''
  def __init__(self,
               created_at=None,
               favorited=None,
               favorite_count=None,
               id=None,
               text=None,
               location=None,
               user=None,
               in_reply_to_screen_name=None,
               in_reply_to_user_id=None,
               in_reply_to_status_id=None,
               truncated=None,
               source=None,
               now=None,
               urls=None,
               user_mentions=None,
               hashtags=None,
               media=None,
               geo=None,
               place=None,
               coordinates=None,
               contributors=None,
               retweeted=None,
               retweeted_status=None,
               current_user_retweet=None,
               retweet_count=None,
               possibly_sensitive=None,
               scopes=None,
               withheld_copyright=None,
               withheld_in_countries=None,
               withheld_scope=None):
    '''An object to hold a Twitter status message.

    This class is normally instantiated by the twitter.Api class and
    returned in a sequence.

    Note: Dates are posted in the form "Sat Jan 27 04:17:38 +0000 2007"

    Args:
      created_at:
        The time this status message was posted. [Optional]
      favorited:
        Whether this is a favorite of the authenticated user. [Optional]
      favorite_count:
        Number of times this status message has been favorited. [Optional]
      id:
        The unique id of this status message. [Optional]
      text:
        The text of this status message. [Optional]
      location:
        the geolocation string associated with this message. [Optional]
      relative_created_at:
        A human readable string representing the posting time. [Optional]
      user:
        A twitter.User instance representing the person posting the
        message. [Optional]
      now:
        The current time, if the client chooses to set it.
        Defaults to the wall clock time. [Optional]
      urls:
      user_mentions:
      hashtags:
      geo:
      place:
      coordinates:
      contributors:
      retweeted:
      retweeted_status:
      current_user_retweet:
      retweet_count:
      possibly_sensitive:
      scopes:
      withheld_copyright:
      withheld_in_countries:
      withheld_scope:
    '''
    self.created_at = created_at
    self.favorited = favorited
    self.favorite_count = favorite_count
    self.id = id
    self.text = text
    self.location = location
    self.user = user
    self.now = now
    self.in_reply_to_screen_name = in_reply_to_screen_name
    self.in_reply_to_user_id = in_reply_to_user_id
    self.in_reply_to_status_id = in_reply_to_status_id
    self.truncated = truncated
    self.retweeted = retweeted
    self.source = source
    self.urls = urls
    self.user_mentions = user_mentions
    self.hashtags = hashtags
    self.media = media
    self.geo = geo
    self.place = place
    self.coordinates = coordinates
    self.contributors = contributors
    self.retweeted_status = retweeted_status
    self.current_user_retweet = current_user_retweet
    self.retweet_count = retweet_count
    self.possibly_sensitive = possibly_sensitive
    self.scopes = scopes
    self.withheld_copyright = withheld_copyright
    self.withheld_in_countries = withheld_in_countries
    self.withheld_scope = withheld_scope

  def GetCreatedAt(self):
    '''Get the time this status message was posted.

    Returns:
      The time this status message was posted
    '''
    return self._created_at

  def SetCreatedAt(self, created_at):
    '''Set the time this status message was posted.

    Args:
      created_at:
        The time this status message was created
    '''
    self._created_at = created_at

  created_at = property(GetCreatedAt, SetCreatedAt,
                        doc='The time this status message was posted.')

  def GetCreatedAtInSeconds(self):
    '''Get the time this status message was posted, in seconds since the epoch.

    Returns:
      The time this status message was posted, in seconds since the epoch.
    '''
    return calendar.timegm(rfc822.parsedate(self.created_at))

  created_at_in_seconds = property(GetCreatedAtInSeconds,
                                   doc="The time this status message was "
                                       "posted, in seconds since the epoch")

  def GetFavorited(self):
    '''Get the favorited setting of this status message.

    Returns:
      True if this status message is favorited; False otherwise
    '''
    return self._favorited

  def SetFavorited(self, favorited):
    '''Set the favorited state of this status message.

    Args:
      favorited:
        boolean True/False favorited state of this status message
    '''
    self._favorited = favorited

  favorited = property(GetFavorited, SetFavorited,
                       doc='The favorited state of this status message.')

  def GetFavoriteCount(self):
    '''Get the favorite count of this status message.

    Returns:
      number of times this status message has been favorited
    '''
    return self._favorite_count

  def SetFavoriteCount(self, favorite_count):
    '''Set the favorited state of this status message.

    Args:
      favorite_count:
        int number of favorites for this status message
    '''
    self._favorite_count = favorite_count

  favorite_count = property(GetFavoriteCount, SetFavoriteCount,
                       doc='The number of favorites for this status message.')

  def GetId(self):
    '''Get the unique id of this status message.

    Returns:
      The unique id of this status message
    '''
    return self._id

  def SetId(self, id):
    '''Set the unique id of this status message.

    Args:
      id:
        The unique id of this status message
    '''
    self._id = id

  id = property(GetId, SetId,
                doc='The unique id of this status message.')

  def GetInReplyToScreenName(self):
    return self._in_reply_to_screen_name

  def SetInReplyToScreenName(self, in_reply_to_screen_name):
    self._in_reply_to_screen_name = in_reply_to_screen_name

  in_reply_to_screen_name = property(GetInReplyToScreenName, SetInReplyToScreenName,
                                     doc='')

  def GetInReplyToUserId(self):
    return self._in_reply_to_user_id

  def SetInReplyToUserId(self, in_reply_to_user_id):
    self._in_reply_to_user_id = in_reply_to_user_id

  in_reply_to_user_id = property(GetInReplyToUserId, SetInReplyToUserId,
                                 doc='')

  def GetInReplyToStatusId(self):
    return self._in_reply_to_status_id

  def SetInReplyToStatusId(self, in_reply_to_status_id):
    self._in_reply_to_status_id = in_reply_to_status_id

  in_reply_to_status_id = property(GetInReplyToStatusId, SetInReplyToStatusId,
                                   doc='')

  def GetTruncated(self):
    return self._truncated

  def SetTruncated(self, truncated):
    self._truncated = truncated

  truncated = property(GetTruncated, SetTruncated,
                       doc='')

  def GetRetweeted(self):
    return self._retweeted

  def SetRetweeted(self, retweeted):
    self._retweeted = retweeted

  retweeted = property(GetRetweeted, SetRetweeted,
                       doc='')

  def GetSource(self):
    return self._source

  def SetSource(self, source):
    self._source = source

  source = property(GetSource, SetSource,
                    doc='')

  def GetText(self):
    '''Get the text of this status message.

    Returns:
      The text of this status message.
    '''
    return self._text

  def SetText(self, text):
    '''Set the text of this status message.

    Args:
      text:
        The text of this status message
    '''
    self._text = text

  text = property(GetText, SetText,
                  doc='The text of this status message')

  def GetLocation(self):
    '''Get the geolocation associated with this status message

    Returns:
      The geolocation string of this status message.
    '''
    return self._location

  def SetLocation(self, location):
    '''Set the geolocation associated with this status message

    Args:
      location:
        The geolocation string of this status message
    '''
    self._location = location

  location = property(GetLocation, SetLocation,
                      doc='The geolocation string of this status message')

  def GetRelativeCreatedAt(self):
    '''Get a human readable string representing the posting time

    Returns:
      A human readable string representing the posting time
    '''
    fudge = 1.25
    delta  = long(self.now) - long(self.created_at_in_seconds)

    if delta < (1 * fudge):
      return 'about a second ago'
    elif delta < (60 * (1/fudge)):
      return 'about %d seconds ago' % (delta)
    elif delta < (60 * fudge):
      return 'about a minute ago'
    elif delta < (60 * 60 * (1/fudge)):
      return 'about %d minutes ago' % (delta / 60)
    elif delta < (60 * 60 * fudge) or delta / (60 * 60) == 1:
      return 'about an hour ago'
    elif delta < (60 * 60 * 24 * (1/fudge)):
      return 'about %d hours ago' % (delta / (60 * 60))
    elif delta < (60 * 60 * 24 * fudge) or delta / (60 * 60 * 24) == 1:
      return 'about a day ago'
    else:
      return 'about %d days ago' % (delta / (60 * 60 * 24))

  relative_created_at = property(GetRelativeCreatedAt,
                                 doc='Get a human readable string representing '
                                     'the posting time')

  def GetUser(self):
    '''Get a twitter.User representing the entity posting this status message.

    Returns:
      A twitter.User representing the entity posting this status message
    '''
    return self._user

  def SetUser(self, user):
    '''Set a twitter.User representing the entity posting this status message.

    Args:
      user:
        A twitter.User representing the entity posting this status message
    '''
    self._user = user

  user = property(GetUser, SetUser,
                  doc='A twitter.User representing the entity posting this '
                      'status message')

  def GetNow(self):
    '''Get the wallclock time for this status message.

    Used to calculate relative_created_at.  Defaults to the time
    the object was instantiated.

    Returns:
      Whatever the status instance believes the current time to be,
      in seconds since the epoch.
    '''
    if self._now is None:
      self._now = time.time()
    return self._now

  def SetNow(self, now):
    '''Set the wallclock time for this status message.

    Used to calculate relative_created_at.  Defaults to the time
    the object was instantiated.

    Args:
      now:
        The wallclock time for this instance.
    '''
    self._now = now

  now = property(GetNow, SetNow,
                 doc='The wallclock time for this status instance.')

  def GetGeo(self):
    return self._geo

  def SetGeo(self, geo):
    self._geo = geo

  geo = property(GetGeo, SetGeo,
                 doc='')

  def GetPlace(self):
    return self._place

  def SetPlace(self, place):
    self._place = place

  place = property(GetPlace, SetPlace,
                   doc='')

  def GetCoordinates(self):
    return self._coordinates

  def SetCoordinates(self, coordinates):
    self._coordinates = coordinates

  coordinates = property(GetCoordinates, SetCoordinates,
                         doc='')

  def GetContributors(self):
    return self._contributors

  def SetContributors(self, contributors):
    self._contributors = contributors

  contributors = property(GetContributors, SetContributors,
                          doc='')

  def GetRetweeted_status(self):
    return self._retweeted_status

  def SetRetweeted_status(self, retweeted_status):
    self._retweeted_status = retweeted_status

  retweeted_status = property(GetRetweeted_status, SetRetweeted_status,
                              doc='')

  def GetRetweetCount(self):
    return self._retweet_count

  def SetRetweetCount(self, retweet_count):
    self._retweet_count = retweet_count

  retweet_count = property(GetRetweetCount, SetRetweetCount,
                           doc='')

  def GetCurrent_user_retweet(self):
    return self._current_user_retweet

  def SetCurrent_user_retweet(self, current_user_retweet):
    self._current_user_retweet = current_user_retweet

  current_user_retweet = property(GetCurrent_user_retweet, SetCurrent_user_retweet,
                                  doc='')

  def GetPossibly_sensitive(self):
    return self._possibly_sensitive

  def SetPossibly_sensitive(self, possibly_sensitive):
    self._possibly_sensitive = possibly_sensitive

  possibly_sensitive = property(GetPossibly_sensitive, SetPossibly_sensitive,
                                doc='')

  def GetScopes(self):
    return self._scopes

  def SetScopes(self, scopes):
    self._scopes = scopes

  scopes = property(GetScopes, SetScopes, doc='')

  def GetWithheld_copyright(self):
    return self._withheld_copyright

  def SetWithheld_copyright(self, withheld_copyright):
    self._withheld_copyright = withheld_copyright

  withheld_copyright = property(GetWithheld_copyright, SetWithheld_copyright,
                                doc='')

  def GetWithheld_in_countries(self):
    return self._withheld_in_countries

  def SetWithheld_in_countries(self, withheld_in_countries):
    self._withheld_in_countries = withheld_in_countries

  withheld_in_countries = property(GetWithheld_in_countries, SetWithheld_in_countries,
                                doc='')

  def GetWithheld_scope(self):
    return self._withheld_scope

  def SetWithheld_scope(self, withheld_scope):
    self._withheld_scope = withheld_scope

  withheld_scope = property(GetWithheld_scope, SetWithheld_scope,
                                doc='')

  def __ne__(self, other):
    return not self.__eq__(other)

  def __eq__(self, other):
    try:
      return other and \
             self.created_at == other.created_at and \
             self.id == other.id and \
             self.text == other.text and \
             self.location == other.location and \
             self.user == other.user and \
             self.in_reply_to_screen_name == other.in_reply_to_screen_name and \
             self.in_reply_to_user_id == other.in_reply_to_user_id and \
             self.in_reply_to_status_id == other.in_reply_to_status_id and \
             self.truncated == other.truncated and \
             self.retweeted == other.retweeted and \
             self.favorited == other.favorited and \
             self.favorite_count == other.favorite_count and \
             self.source == other.source and \
             self.geo == other.geo and \
             self.place == other.place and \
             self.coordinates == other.coordinates and \
             self.contributors == other.contributors and \
             self.retweeted_status == other.retweeted_status and \
             self.retweet_count == other.retweet_count and \
             self.current_user_retweet == other.current_user_retweet and \
             self.possibly_sensitive == other.possibly_sensitive and \
             self.scopes == other.scopes and \
             self.withheld_copyright == other.withheld_copyright and \
             self.withheld_in_countries == other.withheld_in_countries and \
             self.withheld_scope == other.withheld_scope
    except AttributeError:
      return False

  def __str__(self):
    '''A string representation of this twitter.Status instance.

    The return value is the same as the JSON string representation.

    Returns:
      A string representation of this twitter.Status instance.
    '''
    return self.AsJsonString()

  def AsJsonString(self):
    '''A JSON string representation of this twitter.Status instance.

    Returns:
      A JSON string representation of this twitter.Status instance
   '''
    return simplejson.dumps(self.AsDict(), sort_keys=True)

  def AsDict(self):
    '''A dict representation of this twitter.Status instance.

    The return value uses the same key names as the JSON representation.

    Return:
      A dict representing this twitter.Status instance
    '''
    data = {}
    if self.created_at:
      data['created_at'] = self.created_at
    if self.favorited:
      data['favorited'] = self.favorited
    if self.favorite_count:
      data['favorite_count'] = self.favorite_count
    if self.id:
      data['id'] = self.id
    if self.text:
      data['text'] = self.text
    if self.location:
      data['location'] = self.location
    if self.user:
      data['user'] = self.user.AsDict()
    if self.in_reply_to_screen_name:
      data['in_reply_to_screen_name'] = self.in_reply_to_screen_name
    if self.in_reply_to_user_id:
      data['in_reply_to_user_id'] = self.in_reply_to_user_id
    if self.in_reply_to_status_id:
      data['in_reply_to_status_id'] = self.in_reply_to_status_id
    if self.truncated is not None:
      data['truncated'] = self.truncated
    if self.retweeted is not None:
      data['retweeted'] = self.retweeted
    if self.favorited is not None:
      data['favorited'] = self.favorited
    if self.source:
      data['source'] = self.source
    if self.geo:
      data['geo'] = self.geo
    if self.place:
      data['place'] = self.place
    if self.coordinates:
      data['coordinates'] = self.coordinates
    if self.contributors:
      data['contributors'] = self.contributors
    if self.hashtags:
      data['hashtags'] = [h.text for h in self.hashtags]
    if self.retweeted_status:
      data['retweeted_status'] = self.retweeted_status.AsDict()
    if self.retweet_count:
      data['retweet_count'] = self.retweet_count
    if self.urls:
      data['urls'] = dict([(url.url, url.expanded_url) for url in self.urls])
    if self.user_mentions:
      data['user_mentions'] = [um.AsDict() for um in self.user_mentions]
    if self.current_user_retweet:
      data['current_user_retweet'] = self.current_user_retweet
    if self.possibly_sensitive:
      data['possibly_sensitive'] = self.possibly_sensitive
    if self.scopes:
      data['scopes'] = self.scopes
    if self.withheld_copyright:
      data['withheld_copyright'] = self.withheld_copyright
    if self.withheld_in_countries:
      data['withheld_in_countries'] = self.withheld_in_countries
    if self.withheld_scope:
      data['withheld_scope'] = self.withheld_scope
    return data

  @staticmethod
  def NewFromJsonDict(data):
    '''Create a new instance based on a JSON dict.

    Args:
      data: A JSON dict, as converted from the JSON in the twitter API
    Returns:
      A twitter.Status instance
    '''
    if 'user' in data:
      user = User.NewFromJsonDict(data['user'])
    else:
      user = None
    if 'retweeted_status' in data:
      retweeted_status = Status.NewFromJsonDict(data['retweeted_status'])
    else:
      retweeted_status = None

    if 'current_user_retweet' in data:
      current_user_retweet = data['current_user_retweet']['id']
    else:
      current_user_retweet = None

    urls = None
    user_mentions = None
    hashtags = None
    media = None
    if 'entities' in data:
      if 'urls' in data['entities']:
        urls = [Url.NewFromJsonDict(u) for u in data['entities']['urls']]
      if 'user_mentions' in data['entities']:
        user_mentions = [User.NewFromJsonDict(u) for u in data['entities']['user_mentions']]
      if 'hashtags' in data['entities']:
        hashtags = [Hashtag.NewFromJsonDict(h) for h in data['entities']['hashtags']]
      if 'media' in data['entities']:
        media = data['entities']['media']
      else:
        media = []
    return Status(created_at=data.get('created_at', None),
                  favorited=data.get('favorited', None),
                  favorite_count=data.get('favorite_count', None),
                  id=data.get('id', None),
                  text=data.get('text', None),
                  location=data.get('location', None),
                  in_reply_to_screen_name=data.get('in_reply_to_screen_name', None),
                  in_reply_to_user_id=data.get('in_reply_to_user_id', None),
                  in_reply_to_status_id=data.get('in_reply_to_status_id', None),
                  truncated=data.get('truncated', None),
                  retweeted=data.get('retweeted', None),
                  source=data.get('source', None),
                  user=user,
                  urls=urls,
                  user_mentions=user_mentions,
                  hashtags=hashtags,
                  media=media,
                  geo=data.get('geo', None),
                  place=data.get('place', None),
                  coordinates=data.get('coordinates', None),
                  contributors=data.get('contributors', None),
                  retweeted_status=retweeted_status,
                  current_user_retweet=current_user_retweet,
                  retweet_count=data.get('retweet_count', None),
                  possibly_sensitive=data.get('possibly_sensitive', None),
                  scopes=data.get('scopes', None),
                  withheld_copyright=data.get('withheld_copyright', None),
                  withheld_in_countries=data.get('withheld_in_countries', None),
                  withheld_scope=data.get('withheld_scope', None))


class User(object):
  '''A class representing the User structure used by the twitter API.

  The User structure exposes the following properties:

    user.id
    user.name
    user.screen_name
    user.location
    user.description
    user.profile_image_url
    user.profile_background_tile
    user.profile_background_image_url
    user.profile_sidebar_fill_color
    user.profile_background_color
    user.profile_link_color
    user.profile_text_color
    user.protected
    user.utc_offset
    user.time_zone
    user.url
    user.status
    user.statuses_count
    user.followers_count
    user.friends_count
    user.favourites_count
    user.geo_enabled
    user.verified
    user.lang
    user.notifications
    user.contributors_enabled
    user.created_at
    user.listed_count
  '''
  def __init__(self,
               id=None,
               name=None,
               screen_name=None,
               location=None,
               description=None,
               profile_image_url=None,
               profile_background_tile=None,
               profile_background_image_url=None,
               profile_sidebar_fill_color=None,
               profile_background_color=None,
               profile_link_color=None,
               profile_text_color=None,
               protected=None,
               utc_offset=None,
               time_zone=None,
               followers_count=None,
               friends_count=None,
               statuses_count=None,
               favourites_count=None,
               url=None,
               status=None,
               geo_enabled=None,
               verified=None,
               lang=None,
               notifications=None,
               contributors_enabled=None,
               created_at=None,
               listed_count=None):
    self.id = id
    self.name = name
    self.screen_name = screen_name
    self.location = location
    self.description = description
    self.profile_image_url = profile_image_url
    self.profile_background_tile = profile_background_tile
    self.profile_background_image_url = profile_background_image_url
    self.profile_sidebar_fill_color = profile_sidebar_fill_color
    self.profile_background_color = profile_background_color
    self.profile_link_color = profile_link_color
    self.profile_text_color = profile_text_color
    self.protected = protected
    self.utc_offset = utc_offset
    self.time_zone = time_zone
    self.followers_count = followers_count
    self.friends_count = friends_count
    self.statuses_count = statuses_count
    self.favourites_count = favourites_count
    self.url = url
    self.status = status
    self.geo_enabled = geo_enabled
    self.verified = verified
    self.lang = lang
    self.notifications = notifications
    self.contributors_enabled = contributors_enabled
    self.created_at = created_at
    self.listed_count = listed_count

  def GetId(self):
    '''Get the unique id of this user.

    Returns:
      The unique id of this user
    '''
    return self._id

  def SetId(self, id):
    '''Set the unique id of this user.

    Args:
      id: The unique id of this user.
    '''
    self._id = id

  id = property(GetId, SetId,
                doc='The unique id of this user.')

  def GetName(self):
    '''Get the real name of this user.

    Returns:
      The real name of this user
    '''
    return self._name

  def SetName(self, name):
    '''Set the real name of this user.

    Args:
      name: The real name of this user
    '''
    self._name = name

  name = property(GetName, SetName,
                  doc='The real name of this user.')

  def GetScreenName(self):
    '''Get the short twitter name of this user.

    Returns:
      The short twitter name of this user
    '''
    return self._screen_name

  def SetScreenName(self, screen_name):
    '''Set the short twitter name of this user.

    Args:
      screen_name: the short twitter name of this user
    '''
    self._screen_name = screen_name

  screen_name = property(GetScreenName, SetScreenName,
                         doc='The short twitter name of this user.')

  def GetLocation(self):
    '''Get the geographic location of this user.

    Returns:
      The geographic location of this user
    '''
    return self._location

  def SetLocation(self, location):
    '''Set the geographic location of this user.

    Args:
      location: The geographic location of this user
    '''
    self._location = location

  location = property(GetLocation, SetLocation,
                      doc='The geographic location of this user.')

  def GetDescription(self):
    '''Get the short text description of this user.

    Returns:
      The short text description of this user
    '''
    return self._description

  def SetDescription(self, description):
    '''Set the short text description of this user.

    Args:
      description: The short text description of this user
    '''
    self._description = description

  description = property(GetDescription, SetDescription,
                         doc='The short text description of this user.')

  def GetUrl(self):
    '''Get the homepage url of this user.

    Returns:
      The homepage url of this user
    '''
    return self._url

  def SetUrl(self, url):
    '''Set the homepage url of this user.

    Args:
      url: The homepage url of this user
    '''
    self._url = url

  url = property(GetUrl, SetUrl,
                 doc='The homepage url of this user.')

  def GetProfileImageUrl(self):
    '''Get the url of the thumbnail of this user.

    Returns:
      The url of the thumbnail of this user
    '''
    return self._profile_image_url

  def SetProfileImageUrl(self, profile_image_url):
    '''Set the url of the thumbnail of this user.

    Args:
      profile_image_url: The url of the thumbnail of this user
    '''
    self._profile_image_url = profile_image_url

  profile_image_url= property(GetProfileImageUrl, SetProfileImageUrl,
                              doc='The url of the thumbnail of this user.')

  def GetProfileBackgroundTile(self):
    '''Boolean for whether to tile the profile background image.

    Returns:
      True if the background is to be tiled, False if not, None if unset.
    '''
    return self._profile_background_tile

  def SetProfileBackgroundTile(self, profile_background_tile):
    '''Set the boolean flag for whether to tile the profile background image.

    Args:
      profile_background_tile: Boolean flag for whether to tile or not.
    '''
    self._profile_background_tile = profile_background_tile

  profile_background_tile = property(GetProfileBackgroundTile, SetProfileBackgroundTile,
                                     doc='Boolean for whether to tile the background image.')

  def GetProfileBackgroundImageUrl(self):
    return self._profile_background_image_url

  def SetProfileBackgroundImageUrl(self, profile_background_image_url):
    self._profile_background_image_url = profile_background_image_url

  profile_background_image_url = property(GetProfileBackgroundImageUrl, SetProfileBackgroundImageUrl,
                                          doc='The url of the profile background of this user.')

  def GetProfileSidebarFillColor(self):
    return self._profile_sidebar_fill_color

  def SetProfileSidebarFillColor(self, profile_sidebar_fill_color):
    self._profile_sidebar_fill_color = profile_sidebar_fill_color

  profile_sidebar_fill_color = property(GetProfileSidebarFillColor, SetProfileSidebarFillColor)

  def GetProfileBackgroundColor(self):
    return self._profile_background_color

  def SetProfileBackgroundColor(self, profile_background_color):
    self._profile_background_color = profile_background_color

  profile_background_color = property(GetProfileBackgroundColor, SetProfileBackgroundColor)

  def GetProfileLinkColor(self):
    return self._profile_link_color

  def SetProfileLinkColor(self, profile_link_color):
    self._profile_link_color = profile_link_color

  profile_link_color = property(GetProfileLinkColor, SetProfileLinkColor)

  def GetProfileTextColor(self):
    return self._profile_text_color

  def SetProfileTextColor(self, profile_text_color):
    self._profile_text_color = profile_text_color

  profile_text_color = property(GetProfileTextColor, SetProfileTextColor)

  def GetProtected(self):
    return self._protected

  def SetProtected(self, protected):
    self._protected = protected

  protected = property(GetProtected, SetProtected)

  def GetUtcOffset(self):
    return self._utc_offset

  def SetUtcOffset(self, utc_offset):
    self._utc_offset = utc_offset

  utc_offset = property(GetUtcOffset, SetUtcOffset)

  def GetTimeZone(self):
    '''Returns the current time zone string for the user.

    Returns:
      The descriptive time zone string for the user.
    '''
    return self._time_zone

  def SetTimeZone(self, time_zone):
    '''Sets the user's time zone string.

    Args:
      time_zone:
        The descriptive time zone to assign for the user.
    '''
    self._time_zone = time_zone

  time_zone = property(GetTimeZone, SetTimeZone)

  def GetStatus(self):
    '''Get the latest twitter.Status of this user.

    Returns:
      The latest twitter.Status of this user
    '''
    return self._status

  def SetStatus(self, status):
    '''Set the latest twitter.Status of this user.

    Args:
      status:
        The latest twitter.Status of this user
    '''
    self._status = status

  status = property(GetStatus, SetStatus,
                    doc='The latest twitter.Status of this user.')

  def GetFriendsCount(self):
    '''Get the friend count for this user.

    Returns:
      The number of users this user has befriended.
    '''
    return self._friends_count

  def SetFriendsCount(self, count):
    '''Set the friend count for this user.

    Args:
      count:
        The number of users this user has befriended.
    '''
    self._friends_count = count

  friends_count = property(GetFriendsCount, SetFriendsCount,
                           doc='The number of friends for this user.')

  def GetListedCount(self):
    '''Get the listed count for this user.

    Returns:
      The number of lists this user belongs to.
    '''
    return self._listed_count

  def SetListedCount(self, count):
    '''Set the listed count for this user.

    Args:
      count:
        The number of lists this user belongs to.
    '''
    self._listed_count = count

  listed_count = property(GetListedCount, SetListedCount,
                          doc='The number of lists this user belongs to.')

  def GetFollowersCount(self):
    '''Get the follower count for this user.

    Returns:
      The number of users following this user.
    '''
    return self._followers_count

  def SetFollowersCount(self, count):
    '''Set the follower count for this user.

    Args:
      count:
        The number of users following this user.
    '''
    self._followers_count = count

  followers_count = property(GetFollowersCount, SetFollowersCount,
                             doc='The number of users following this user.')

  def GetStatusesCount(self):
    '''Get the number of status updates for this user.

    Returns:
      The number of status updates for this user.
    '''
    return self._statuses_count

  def SetStatusesCount(self, count):
    '''Set the status update count for this user.

    Args:
      count:
        The number of updates for this user.
    '''
    self._statuses_count = count

  statuses_count = property(GetStatusesCount, SetStatusesCount,
                            doc='The number of updates for this user.')

  def GetFavouritesCount(self):
    '''Get the number of favourites for this user.

    Returns:
      The number of favourites for this user.
    '''
    return self._favourites_count

  def SetFavouritesCount(self, count):
    '''Set the favourite count for this user.

    Args:
      count:
        The number of favourites for this user.
    '''
    self._favourites_count = count

  favourites_count = property(GetFavouritesCount, SetFavouritesCount,
                              doc='The number of favourites for this user.')

  def GetGeoEnabled(self):
    '''Get the setting of geo_enabled for this user.

    Returns:
      True/False if Geo tagging is enabled
    '''
    return self._geo_enabled

  def SetGeoEnabled(self, geo_enabled):
    '''Set the latest twitter.geo_enabled of this user.

    Args:
      geo_enabled:
        True/False if Geo tagging is to be enabled
    '''
    self._geo_enabled = geo_enabled

  geo_enabled = property(GetGeoEnabled, SetGeoEnabled,
                         doc='The value of twitter.geo_enabled for this user.')

  def GetVerified(self):
    '''Get the setting of verified for this user.

    Returns:
      True/False if user is a verified account
    '''
    return self._verified

  def SetVerified(self, verified):
    '''Set twitter.verified for this user.

    Args:
      verified:
        True/False if user is a verified account
    '''
    self._verified = verified

  verified = property(GetVerified, SetVerified,
                      doc='The value of twitter.verified for this user.')

  def GetLang(self):
    '''Get the setting of lang for this user.

    Returns:
      language code of the user
    '''
    return self._lang

  def SetLang(self, lang):
    '''Set twitter.lang for this user.

    Args:
      lang:
        language code for the user
    '''
    self._lang = lang

  lang = property(GetLang, SetLang,
                  doc='The value of twitter.lang for this user.')

  def GetNotifications(self):
    '''Get the setting of notifications for this user.

    Returns:
      True/False for the notifications setting of the user
    '''
    return self._notifications

  def SetNotifications(self, notifications):
    '''Set twitter.notifications for this user.

    Args:
      notifications:
        True/False notifications setting for the user
    '''
    self._notifications = notifications

  notifications = property(GetNotifications, SetNotifications,
                           doc='The value of twitter.notifications for this user.')

  def GetContributorsEnabled(self):
    '''Get the setting of contributors_enabled for this user.

    Returns:
      True/False contributors_enabled of the user
    '''
    return self._contributors_enabled

  def SetContributorsEnabled(self, contributors_enabled):
    '''Set twitter.contributors_enabled for this user.

    Args:
      contributors_enabled:
        True/False contributors_enabled setting for the user
    '''
    self._contributors_enabled = contributors_enabled

  contributors_enabled = property(GetContributorsEnabled, SetContributorsEnabled,
                                  doc='The value of twitter.contributors_enabled for this user.')

  def GetCreatedAt(self):
    '''Get the setting of created_at for this user.

    Returns:
      created_at value of the user
    '''
    return self._created_at

  def SetCreatedAt(self, created_at):
    '''Set twitter.created_at for this user.

    Args:
      created_at:
        created_at value for the user
    '''
    self._created_at = created_at

  created_at = property(GetCreatedAt, SetCreatedAt,
                        doc='The value of twitter.created_at for this user.')

  def __ne__(self, other):
    return not self.__eq__(other)

  def __eq__(self, other):
    try:
      return other and \
             self.id == other.id and \
             self.name == other.name and \
             self.screen_name == other.screen_name and \
             self.location == other.location and \
             self.description == other.description and \
             self.profile_image_url == other.profile_image_url and \
             self.profile_background_tile == other.profile_background_tile and \
             self.profile_background_image_url == other.profile_background_image_url and \
             self.profile_sidebar_fill_color == other.profile_sidebar_fill_color and \
             self.profile_background_color == other.profile_background_color and \
             self.profile_link_color == other.profile_link_color and \
             self.profile_text_color == other.profile_text_color and \
             self.protected == other.protected and \
             self.utc_offset == other.utc_offset and \
             self.time_zone == other.time_zone and \
             self.url == other.url and \
             self.statuses_count == other.statuses_count and \
             self.followers_count == other.followers_count and \
             self.favourites_count == other.favourites_count and \
             self.friends_count == other.friends_count and \
             self.status == other.status and \
             self.geo_enabled == other.geo_enabled and \
             self.verified == other.verified and \
             self.lang == other.lang and \
             self.notifications == other.notifications and \
             self.contributors_enabled == other.contributors_enabled and \
             self.created_at == other.created_at and \
             self.listed_count == other.listed_count

    except AttributeError:
      return False

  def __str__(self):
    '''A string representation of this twitter.User instance.

    The return value is the same as the JSON string representation.

    Returns:
      A string representation of this twitter.User instance.
    '''
    return self.AsJsonString()

  def AsJsonString(self):
    '''A JSON string representation of this twitter.User instance.

    Returns:
      A JSON string representation of this twitter.User instance
   '''
    return simplejson.dumps(self.AsDict(), sort_keys=True)

  def AsDict(self):
    '''A dict representation of this twitter.User instance.

    The return value uses the same key names as the JSON representation.

    Return:
      A dict representing this twitter.User instance
    '''
    data = {}
    if self.id:
      data['id'] = self.id
    if self.name:
      data['name'] = self.name
    if self.screen_name:
      data['screen_name'] = self.screen_name
    if self.location:
      data['location'] = self.location
    if self.description:
      data['description'] = self.description
    if self.profile_image_url:
      data['profile_image_url'] = self.profile_image_url
    if self.profile_background_tile is not None:
      data['profile_background_tile'] = self.profile_background_tile
    if self.profile_background_image_url:
      data['profile_sidebar_fill_color'] = self.profile_background_image_url
    if self.profile_background_color:
      data['profile_background_color'] = self.profile_background_color
    if self.profile_link_color:
      data['profile_link_color'] = self.profile_link_color
    if self.profile_text_color:
      data['profile_text_color'] = self.profile_text_color
    if self.protected is not None:
      data['protected'] = self.protected
    if self.utc_offset:
      data['utc_offset'] = self.utc_offset
    if self.time_zone:
      data['time_zone'] = self.time_zone
    if self.url:
      data['url'] = self.url
    if self.status:
      data['status'] = self.status.AsDict()
    if self.friends_count:
      data['friends_count'] = self.friends_count
    if self.followers_count:
      data['followers_count'] = self.followers_count
    if self.statuses_count:
      data['statuses_count'] = self.statuses_count
    if self.favourites_count:
      data['favourites_count'] = self.favourites_count
    if self.geo_enabled:
      data['geo_enabled'] = self.geo_enabled
    if self.verified:
      data['verified'] = self.verified
    if self.lang:
      data['lang'] = self.lang
    if self.notifications:
      data['notifications'] = self.notifications
    if self.contributors_enabled:
      data['contributors_enabled'] = self.contributors_enabled
    if self.created_at:
      data['created_at'] = self.created_at
    if self.listed_count:
      data['listed_count'] = self.listed_count

    return data

  @staticmethod
  def NewFromJsonDict(data):
    '''Create a new instance based on a JSON dict.

    Args:
      data:
        A JSON dict, as converted from the JSON in the twitter API

    Returns:
      A twitter.User instance
    '''
    if 'status' in data:
      status = Status.NewFromJsonDict(data['status'])
    else:
      status = None
    return User(id=data.get('id', None),
                name=data.get('name', None),
                screen_name=data.get('screen_name', None),
                location=data.get('location', None),
                description=data.get('description', None),
                statuses_count=data.get('statuses_count', None),
                followers_count=data.get('followers_count', None),
                favourites_count=data.get('favourites_count', None),
                friends_count=data.get('friends_count', None),
                profile_image_url=data.get('profile_image_url_https', data.get('profile_image_url', None)),
                profile_background_tile = data.get('profile_background_tile', None),
                profile_background_image_url = data.get('profile_background_image_url', None),
                profile_sidebar_fill_color = data.get('profile_sidebar_fill_color', None),
                profile_background_color = data.get('profile_background_color', None),
                profile_link_color = data.get('profile_link_color', None),
                profile_text_color = data.get('profile_text_color', None),
                protected = data.get('protected', None),
                utc_offset = data.get('utc_offset', None),
                time_zone = data.get('time_zone', None),
                url=data.get('url', None),
                status=status,
                geo_enabled=data.get('geo_enabled', None),
                verified=data.get('verified', None),
                lang=data.get('lang', None),
                notifications=data.get('notifications', None),
                contributors_enabled=data.get('contributors_enabled', None),
                created_at=data.get('created_at', None),
                listed_count=data.get('listed_count', None))

class List(object):
  '''A class representing the List structure used by the twitter API.

  The List structure exposes the following properties:

    list.id
    list.name
    list.slug
    list.description
    list.full_name
    list.mode
    list.uri
    list.member_count
    list.subscriber_count
    list.following
  '''
  def __init__(self,
               id=None,
               name=None,
               slug=None,
               description=None,
               full_name=None,
               mode=None,
               uri=None,
               member_count=None,
               subscriber_count=None,
               following=None,
               user=None):
    self.id = id
    self.name = name
    self.slug = slug
    self.description = description
    self.full_name = full_name
    self.mode = mode
    self.uri = uri
    self.member_count = member_count
    self.subscriber_count = subscriber_count
    self.following = following
    self.user = user

  def GetId(self):
    '''Get the unique id of this list.

    Returns:
      The unique id of this list
    '''
    return self._id

  def SetId(self, id):
    '''Set the unique id of this list.

    Args:
      id:
        The unique id of this list.
    '''
    self._id = id

  id = property(GetId, SetId,
                doc='The unique id of this list.')

  def GetName(self):
    '''Get the real name of this list.

    Returns:
      The real name of this list
    '''
    return self._name

  def SetName(self, name):
    '''Set the real name of this list.

    Args:
      name:
        The real name of this list
    '''
    self._name = name

  name = property(GetName, SetName,
                  doc='The real name of this list.')

  def GetSlug(self):
    '''Get the slug of this list.

    Returns:
      The slug of this list
    '''
    return self._slug

  def SetSlug(self, slug):
    '''Set the slug of this list.

    Args:
      slug:
        The slug of this list.
    '''
    self._slug = slug

  slug = property(GetSlug, SetSlug,
                  doc='The slug of this list.')

  def GetDescription(self):
    '''Get the description of this list.

    Returns:
      The description of this list
    '''
    return self._description

  def SetDescription(self, description):
    '''Set the description of this list.

    Args:
      description:
        The description of this list.
    '''
    self._description = description

  description = property(GetDescription, SetDescription,
                         doc='The description of this list.')

  def GetFull_name(self):
    '''Get the full_name of this list.

    Returns:
      The full_name of this list
    '''
    return self._full_name

  def SetFull_name(self, full_name):
    '''Set the full_name of this list.

    Args:
      full_name:
        The full_name of this list.
    '''
    self._full_name = full_name

  full_name = property(GetFull_name, SetFull_name,
                       doc='The full_name of this list.')

  def GetMode(self):
    '''Get the mode of this list.

    Returns:
      The mode of this list
    '''
    return self._mode

  def SetMode(self, mode):
    '''Set the mode of this list.

    Args:
      mode:
        The mode of this list.
    '''
    self._mode = mode

  mode = property(GetMode, SetMode,
                  doc='The mode of this list.')

  def GetUri(self):
    '''Get the uri of this list.

    Returns:
      The uri of this list
    '''
    return self._uri

  def SetUri(self, uri):
    '''Set the uri of this list.

    Args:
      uri:
        The uri of this list.
    '''
    self._uri = uri

  uri = property(GetUri, SetUri,
                 doc='The uri of this list.')

  def GetMember_count(self):
    '''Get the member_count of this list.

    Returns:
      The member_count of this list
    '''
    return self._member_count

  def SetMember_count(self, member_count):
    '''Set the member_count of this list.

    Args:
      member_count:
        The member_count of this list.
    '''
    self._member_count = member_count

  member_count = property(GetMember_count, SetMember_count,
                          doc='The member_count of this list.')

  def GetSubscriber_count(self):
    '''Get the subscriber_count of this list.

    Returns:
      The subscriber_count of this list
    '''
    return self._subscriber_count

  def SetSubscriber_count(self, subscriber_count):
    '''Set the subscriber_count of this list.

    Args:
      subscriber_count:
        The subscriber_count of this list.
    '''
    self._subscriber_count = subscriber_count

  subscriber_count = property(GetSubscriber_count, SetSubscriber_count,
                              doc='The subscriber_count of this list.')

  def GetFollowing(self):
    '''Get the following status of this list.

    Returns:
      The following status of this list
    '''
    return self._following

  def SetFollowing(self, following):
    '''Set the following status of this list.

    Args:
      following:
        The following of this list.
    '''
    self._following = following

  following = property(GetFollowing, SetFollowing,
                       doc='The following status of this list.')

  def GetUser(self):
    '''Get the user of this list.

    Returns:
      The owner of this list
    '''
    return self._user

  def SetUser(self, user):
    '''Set the user of this list.

    Args:
      user:
        The owner of this list.
    '''
    self._user = user

  user = property(GetUser, SetUser,
                  doc='The owner of this list.')

  def __ne__(self, other):
    return not self.__eq__(other)

  def __eq__(self, other):
    try:
      return other and \
             self.id == other.id and \
             self.name == other.name and \
             self.slug == other.slug and \
             self.description == other.description and \
             self.full_name == other.full_name and \
             self.mode == other.mode and \
             self.uri == other.uri and \
             self.member_count == other.member_count and \
             self.subscriber_count == other.subscriber_count and \
             self.following == other.following and \
             self.user == other.user

    except AttributeError:
      return False

  def __str__(self):
    '''A string representation of this twitter.List instance.

    The return value is the same as the JSON string representation.

    Returns:
      A string representation of this twitter.List instance.
    '''
    return self.AsJsonString()

  def AsJsonString(self):
    '''A JSON string representation of this twitter.List instance.

    Returns:
      A JSON string representation of this twitter.List instance
   '''
    return simplejson.dumps(self.AsDict(), sort_keys=True)

  def AsDict(self):
    '''A dict representation of this twitter.List instance.

    The return value uses the same key names as the JSON representation.

    Return:
      A dict representing this twitter.List instance
    '''
    data = {}
    if self.id:
      data['id'] = self.id
    if self.name:
      data['name'] = self.name
    if self.slug:
      data['slug'] = self.slug
    if self.description:
      data['description'] = self.description
    if self.full_name:
      data['full_name'] = self.full_name
    if self.mode:
      data['mode'] = self.mode
    if self.uri:
      data['uri'] = self.uri
    if self.member_count is not None:
      data['member_count'] = self.member_count
    if self.subscriber_count is not None:
      data['subscriber_count'] = self.subscriber_count
    if self.following is not None:
      data['following'] = self.following
    if self.user is not None:
      data['user'] = self.user.AsDict()
    return data

  @staticmethod
  def NewFromJsonDict(data):
    '''Create a new instance based on a JSON dict.

    Args:
      data:
        A JSON dict, as converted from the JSON in the twitter API

    Returns:
      A twitter.List instance
    '''
    if 'user' in data:
      user = User.NewFromJsonDict(data['user'])
    else:
      user = None
    return List(id=data.get('id', None),
                name=data.get('name', None),
                slug=data.get('slug', None),
                description=data.get('description', None),
                full_name=data.get('full_name', None),
                mode=data.get('mode', None),
                uri=data.get('uri', None),
                member_count=data.get('member_count', None),
                subscriber_count=data.get('subscriber_count', None),
                following=data.get('following', None),
                user=user)

class DirectMessage(object):
  '''A class representing the DirectMessage structure used by the twitter API.

  The DirectMessage structure exposes the following properties:

    direct_message.id
    direct_message.created_at
    direct_message.created_at_in_seconds # read only
    direct_message.sender_id
    direct_message.sender_screen_name
    direct_message.recipient_id
    direct_message.recipient_screen_name
    direct_message.text
  '''

  def __init__(self,
               id=None,
               created_at=None,
               sender_id=None,
               sender_screen_name=None,
               recipient_id=None,
               recipient_screen_name=None,
               text=None):
    '''An object to hold a Twitter direct message.

    This class is normally instantiated by the twitter.Api class and
    returned in a sequence.

    Note: Dates are posted in the form "Sat Jan 27 04:17:38 +0000 2007"

    Args:
      id:
        The unique id of this direct message. [Optional]
      created_at:
        The time this direct message was posted. [Optional]
      sender_id:
        The id of the twitter user that sent this message. [Optional]
      sender_screen_name:
        The name of the twitter user that sent this message. [Optional]
      recipient_id:
        The id of the twitter that received this message. [Optional]
      recipient_screen_name:
        The name of the twitter that received this message. [Optional]
      text:
        The text of this direct message. [Optional]
    '''
    self.id = id
    self.created_at = created_at
    self.sender_id = sender_id
    self.sender_screen_name = sender_screen_name
    self.recipient_id = recipient_id
    self.recipient_screen_name = recipient_screen_name
    self.text = text

  def GetId(self):
    '''Get the unique id of this direct message.

    Returns:
      The unique id of this direct message
    '''
    return self._id

  def SetId(self, id):
    '''Set the unique id of this direct message.

    Args:
      id:
        The unique id of this direct message
    '''
    self._id = id

  id = property(GetId, SetId,
                doc='The unique id of this direct message.')

  def GetCreatedAt(self):
    '''Get the time this direct message was posted.

    Returns:
      The time this direct message was posted
    '''
    return self._created_at

  def SetCreatedAt(self, created_at):
    '''Set the time this direct message was posted.

    Args:
      created_at:
        The time this direct message was created
    '''
    self._created_at = created_at

  created_at = property(GetCreatedAt, SetCreatedAt,
                        doc='The time this direct message was posted.')

  def GetCreatedAtInSeconds(self):
    '''Get the time this direct message was posted, in seconds since the epoch.

    Returns:
      The time this direct message was posted, in seconds since the epoch.
    '''
    return calendar.timegm(rfc822.parsedate(self.created_at))

  created_at_in_seconds = property(GetCreatedAtInSeconds,
                                   doc="The time this direct message was "
                                       "posted, in seconds since the epoch")

  def GetSenderId(self):
    '''Get the unique sender id of this direct message.

    Returns:
      The unique sender id of this direct message
    '''
    return self._sender_id

  def SetSenderId(self, sender_id):
    '''Set the unique sender id of this direct message.

    Args:
      sender_id:
        The unique sender id of this direct message
    '''
    self._sender_id = sender_id

  sender_id = property(GetSenderId, SetSenderId,
                doc='The unique sender id of this direct message.')

  def GetSenderScreenName(self):
    '''Get the unique sender screen name of this direct message.

    Returns:
      The unique sender screen name of this direct message
    '''
    return self._sender_screen_name

  def SetSenderScreenName(self, sender_screen_name):
    '''Set the unique sender screen name of this direct message.

    Args:
      sender_screen_name:
        The unique sender screen name of this direct message
    '''
    self._sender_screen_name = sender_screen_name

  sender_screen_name = property(GetSenderScreenName, SetSenderScreenName,
                doc='The unique sender screen name of this direct message.')

  def GetRecipientId(self):
    '''Get the unique recipient id of this direct message.

    Returns:
      The unique recipient id of this direct message
    '''
    return self._recipient_id

  def SetRecipientId(self, recipient_id):
    '''Set the unique recipient id of this direct message.

    Args:
      recipient_id:
        The unique recipient id of this direct message
    '''
    self._recipient_id = recipient_id

  recipient_id = property(GetRecipientId, SetRecipientId,
                doc='The unique recipient id of this direct message.')

  def GetRecipientScreenName(self):
    '''Get the unique recipient screen name of this direct message.

    Returns:
      The unique recipient screen name of this direct message
    '''
    return self._recipient_screen_name

  def SetRecipientScreenName(self, recipient_screen_name):
    '''Set the unique recipient screen name of this direct message.

    Args:
      recipient_screen_name:
        The unique recipient screen name of this direct message
    '''
    self._recipient_screen_name = recipient_screen_name

  recipient_screen_name = property(GetRecipientScreenName, SetRecipientScreenName,
                doc='The unique recipient screen name of this direct message.')

  def GetText(self):
    '''Get the text of this direct message.

    Returns:
      The text of this direct message.
    '''
    return self._text

  def SetText(self, text):
    '''Set the text of this direct message.

    Args:
      text:
        The text of this direct message
    '''
    self._text = text

  text = property(GetText, SetText,
                  doc='The text of this direct message')

  def __ne__(self, other):
    return not self.__eq__(other)

  def __eq__(self, other):
    try:
      return other and \
          self.id == other.id and \
          self.created_at == other.created_at and \
          self.sender_id == other.sender_id and \
          self.sender_screen_name == other.sender_screen_name and \
          self.recipient_id == other.recipient_id and \
          self.recipient_screen_name == other.recipient_screen_name and \
          self.text == other.text
    except AttributeError:
      return False

  def __str__(self):
    '''A string representation of this twitter.DirectMessage instance.

    The return value is the same as the JSON string representation.

    Returns:
      A string representation of this twitter.DirectMessage instance.
    '''
    return self.AsJsonString()

  def AsJsonString(self):
    '''A JSON string representation of this twitter.DirectMessage instance.

    Returns:
      A JSON string representation of this twitter.DirectMessage instance
   '''
    return simplejson.dumps(self.AsDict(), sort_keys=True)

  def AsDict(self):
    '''A dict representation of this twitter.DirectMessage instance.

    The return value uses the same key names as the JSON representation.

    Return:
      A dict representing this twitter.DirectMessage instance
    '''
    data = {}
    if self.id:
      data['id'] = self.id
    if self.created_at:
      data['created_at'] = self.created_at
    if self.sender_id:
      data['sender_id'] = self.sender_id
    if self.sender_screen_name:
      data['sender_screen_name'] = self.sender_screen_name
    if self.recipient_id:
      data['recipient_id'] = self.recipient_id
    if self.recipient_screen_name:
      data['recipient_screen_name'] = self.recipient_screen_name
    if self.text:
      data['text'] = self.text
    return data

  @staticmethod
  def NewFromJsonDict(data):
    '''Create a new instance based on a JSON dict.

    Args:
      data:
        A JSON dict, as converted from the JSON in the twitter API

    Returns:
      A twitter.DirectMessage instance
    '''
    return DirectMessage(created_at=data.get('created_at', None),
                         recipient_id=data.get('recipient_id', None),
                         sender_id=data.get('sender_id', None),
                         text=data.get('text', None),
                         sender_screen_name=data.get('sender_screen_name', None),
                         id=data.get('id', None),
                         recipient_screen_name=data.get('recipient_screen_name', None))

class Hashtag(object):
  ''' A class representing a twitter hashtag
  '''
  def __init__(self,
               text=None):
    self.text = text

  @staticmethod
  def NewFromJsonDict(data):
    '''Create a new instance based on a JSON dict.

    Args:
      data:
        A JSON dict, as converted from the JSON in the twitter API

    Returns:
      A twitter.Hashtag instance
    '''
    return Hashtag(text = data.get('text', None))

class Trend(object):
  ''' A class representing a trending topic
  '''
  def __init__(self, name=None, query=None, timestamp=None, url=None):
    self.name = name
    self.query = query
    self.timestamp = timestamp
    self.url = url

  def __str__(self):
    return 'Name: %s\nQuery: %s\nTimestamp: %s\nSearch URL: %s\n' % (self.name, self.query, self.timestamp, self.url)

  def __ne__(self, other):
    return not self.__eq__(other)

  def __eq__(self, other):
    try:
      return other and \
          self.name == other.name and \
          self.query == other.query and \
          self.timestamp == other.timestamp and \
          self.url == self.url
    except AttributeError:
      return False

  @staticmethod
  def NewFromJsonDict(data, timestamp = None):
    '''Create a new instance based on a JSON dict

    Args:
      data:
        A JSON dict
      timestamp:
        Gets set as the timestamp property of the new object

    Returns:
      A twitter.Trend object
    '''
    return Trend(name=data.get('name', None),
                 query=data.get('query', None),
                 url=data.get('url', None),
                 timestamp=timestamp)

class Url(object):
  '''A class representing an URL contained in a tweet'''
  def __init__(self,
               url=None,
               expanded_url=None):
    self.url = url
    self.expanded_url = expanded_url

  @staticmethod
  def NewFromJsonDict(data):
    '''Create a new instance based on a JSON dict.

    Args:
      data:
        A JSON dict, as converted from the JSON in the twitter API

    Returns:
      A twitter.Url instance
    '''
    return Url(url=data.get('url', None),
               expanded_url=data.get('expanded_url', None))

class Api(object):
  '''A python interface into the Twitter API

  By default, the Api caches results for 1 minute.

  Example usage:

    To create an instance of the twitter.Api class, with no authentication:

      >>> import twitter
      >>> api = twitter.Api()

    To fetch the most recently posted public twitter status messages:

      >>> statuses = api.GetPublicTimeline()
      >>> print [s.user.name for s in statuses]
      [u'DeWitt', u'Kesuke Miyagi', u'ev', u'Buzz Andersen', u'Biz Stone'] #...

    To fetch a single user's public status messages, where "user" is either
    a Twitter "short name" or their user id.

      >>> statuses = api.GetUserTimeline(user)
      >>> print [s.text for s in statuses]

    To use authentication, instantiate the twitter.Api class with a
    consumer key and secret; and the oAuth key and secret:

      >>> api = twitter.Api(consumer_key='twitter consumer key',
                            consumer_secret='twitter consumer secret',
                            access_token_key='the_key_given',
                            access_token_secret='the_key_secret')

    To fetch your friends (after being authenticated):

      >>> users = api.GetFriends()
      >>> print [u.name for u in users]

    To post a twitter status message (after being authenticated):

      >>> status = api.PostUpdate('I love python-twitter!')
      >>> print status.text
      I love python-twitter!

    There are many other methods, including:

      >>> api.PostUpdates(status)
      >>> api.PostDirectMessage(user, text)
      >>> api.GetUser(user)
      >>> api.GetReplies()
      >>> api.GetUserTimeline(user)
      >>> api.GetHomeTimeLine()
      >>> api.GetStatus(id)
      >>> api.DestroyStatus(id)
      >>> api.GetFriendsTimeline(user)
      >>> api.GetFriends(user)
      >>> api.GetFollowers()
      >>> api.GetFeatured()
      >>> api.GetDirectMessages()
      >>> api.GetSentDirectMessages()
      >>> api.PostDirectMessage(user, text)
      >>> api.DestroyDirectMessage(id)
      >>> api.DestroyFriendship(user)
      >>> api.CreateFriendship(user)
      >>> api.GetUserByEmail(email)
      >>> api.VerifyCredentials()
  '''

  DEFAULT_CACHE_TIMEOUT = 60 # cache for 1 minute
  _API_REALM = 'Twitter API'

  def __init__(self,
               consumer_key=None,
               consumer_secret=None,
               access_token_key=None,
               access_token_secret=None,
               input_encoding=None,
               request_headers=None,
               cache=DEFAULT_CACHE,
               shortner=None,
               base_url=None,
               use_gzip_compression=False,
               debugHTTP=False):
    '''Instantiate a new twitter.Api object.

    Args:
      consumer_key:
        Your Twitter user's consumer_key.
      consumer_secret:
        Your Twitter user's consumer_secret.
      access_token_key:
        The oAuth access token key value you retrieved
        from running get_access_token.py.
      access_token_secret:
        The oAuth access token's secret, also retrieved
        from the get_access_token.py run.
      input_encoding:
        The encoding used to encode input strings. [Optional]
      request_header:
        A dictionary of additional HTTP request headers. [Optional]
      cache:
        The cache instance to use. Defaults to DEFAULT_CACHE.
        Use None to disable caching. [Optional]
      shortner:
        The shortner instance to use.  Defaults to None.
        See shorten_url.py for an example shortner. [Optional]
      base_url:
        The base URL to use to contact the Twitter API.
        Defaults to https://api.twitter.com. [Optional]
      use_gzip_compression:
        Set to True to tell enable gzip compression for any call
        made to Twitter.  Defaults to False. [Optional]
      debugHTTP:
        Set to True to enable debug output from urllib2 when performing
        any HTTP requests.  Defaults to False. [Optional]
    '''
    self.SetCache(cache)
    self._urllib         = urllib2
    self._cache_timeout  = Api.DEFAULT_CACHE_TIMEOUT
    self._input_encoding = input_encoding
    self._use_gzip       = use_gzip_compression
    self._debugHTTP      = debugHTTP
    self._oauth_consumer = None
    self._shortlink_size = 19

    self._InitializeRequestHeaders(request_headers)
    self._InitializeUserAgent()
    self._InitializeDefaultParameters()

    if base_url is None:
      self.base_url = 'https://api.twitter.com/1.1'
    else:
      self.base_url = base_url

    if consumer_key is not None and (access_token_key is None or
                                     access_token_secret is None):
      print >> sys.stderr, 'Twitter now requires an oAuth Access Token for API calls.'
      print >> sys.stderr, 'If your using this library from a command line utility, please'
      print >> sys.stderr, 'run the the included get_access_token.py tool to generate one.'

      raise TwitterError('Twitter requires oAuth Access Token for all API access')

    self.SetCredentials(consumer_key, consumer_secret, access_token_key, access_token_secret)

  def SetCredentials(self,
                     consumer_key,
                     consumer_secret,
                     access_token_key=None,
                     access_token_secret=None):
    '''Set the consumer_key and consumer_secret for this instance

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
    '''
    self._consumer_key        = consumer_key
    self._consumer_secret     = consumer_secret
    self._access_token_key    = access_token_key
    self._access_token_secret = access_token_secret
    self._oauth_consumer      = None

    if consumer_key is not None and consumer_secret is not None and \
       access_token_key is not None and access_token_secret is not None:
      self._signature_method_plaintext = oauth.SignatureMethod_PLAINTEXT()
      self._signature_method_hmac_sha1 = oauth.SignatureMethod_HMAC_SHA1()

      self._oauth_token    = oauth.Token(key=access_token_key, secret=access_token_secret)
      self._oauth_consumer = oauth.Consumer(key=consumer_key, secret=consumer_secret)

  def ClearCredentials(self):
    '''Clear the any credentials for this instance
    '''
    self._consumer_key        = None
    self._consumer_secret     = None
    self._access_token_key    = None
    self._access_token_secret = None
    self._oauth_consumer      = None

  def GetSearch(self,
                term=None,
                geocode=None,
                since_id=None,
                max_id=None,
                until=None,
                count=15,
                lang=None,
                locale=None,
                result_type="mixed",
                include_entities=None):
    '''Return twitter search results for a given term.

    Args:
      term:
        Term to search by. Optional if you include geocode.
      since_id:
        Returns results with an ID greater than (that is, more recent
        than) the specified ID. There are limits to the number of
        Tweets which can be accessed through the API. If the limit of
        Tweets has occurred since the since_id, the since_id will be
        forced to the oldest ID available. [Optional]
      max_id:
        Returns only statuses with an ID less than (that is, older
        than) or equal to the specified ID. [Optional]
      until:
        Returns tweets generated before the given date. Date should be
        formatted as YYYY-MM-DD. [Optional]
      geocode:
        Geolocation information in the form (latitude, longitude, radius)
        [Optional]
      count:
        Number of results to return.  Default is 15 [Optional]
      lang:
        Language for results as ISO 639-1 code.  Default is None (all languages)
        [Optional]
      locale:
        Language of the search query. Currently only 'ja' is effective. This is
        intended for language-specific consumers and the default should work in
        the majority of cases.
      result_type:
        Type of result which should be returned.  Default is "mixed".  Other
        valid options are "recent" and "popular". [Optional]
      include_entities:
        If True, each tweet will include a node called "entities,".
        This node offers a variety of metadata about the tweet in a
        discrete structure, including: user_mentions, urls, and
        hashtags. [Optional]

    Returns:
      A sequence of twitter.Status instances, one for each message containing
      the term
    '''
    # Build request parameters
    parameters = {}

    if since_id:
      try:
        parameters['since_id'] = long(since_id)
      except:
        raise TwitterError("since_id must be an integer")

    if max_id:
      try:
        parameters['max_id'] = long(max_id)
      except:
        raise TwitterError("max_id must be an integer")

    if until:
        parameters['until'] = until

    if lang:
      parameters['lang'] = lang

    if locale:
      parameters['locale'] = locale

    if term is None and geocode is None:
      return []

    if term is not None:
      parameters['q'] = term

    if geocode is not None:
      parameters['geocode'] = ','.join(map(str, geocode))

    if include_entities:
      parameters['include_entities'] = 1

    try:
        parameters['count'] = int(count)
    except:
        raise TwitterError("count must be an integer")

    if result_type in ["mixed", "popular", "recent"]:
      parameters['result_type'] = result_type

    # Make and send requests
    url  = '%s/search/tweets.json' % self.base_url
    json = self._FetchUrl(url, parameters=parameters)
    data = self._ParseAndCheckTwitter(json)

    # Return built list of statuses
    return [Status.NewFromJsonDict(x) for x in data['statuses']]

  def GetUsersSearch(self,
                     term=None,
                     page=1,
                     count=20,
                     include_entities=None):
    '''Return twitter user search results for a given term.

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
    '''
    # Build request parameters
    parameters = {}

    if term is not None:
      parameters['q'] = term

    if include_entities:
      parameters['include_entities'] = 1

    try:
      parameters['count'] = int(count)
    except:
      raise TwitterError("count must be an integer")

    # Make and send requests
    url  = '%s/users/search.json' % self.base_url
    json = self._FetchUrl(url, parameters=parameters)
    data = self._ParseAndCheckTwitter(json)
    return [User.NewFromJsonDict(x) for x in data]

  def GetTrendsCurrent(self, exclude=None):
    '''Get the current top trending topics (global)

    Args:
      exclude:
        Appends the exclude parameter as a request parameter.
        Currently only exclude=hashtags is supported. [Optional]

    Returns:
      A list with 10 entries. Each entry contains a trend.
    '''
    return self.GetTrendsWoeid(id=1, exclude=exclude)

  def GetTrendsWoeid(self, id, exclude=None):
    '''Return the top 10 trending topics for a specific WOEID, if trending
    information is available for it.

    Args:
      woeid:
        the Yahoo! Where On Earth ID for a location.
      exclude:
        Appends the exclude parameter as a request parameter.
        Currently only exclude=hashtags is supported. [Optional]

    Returns:
      A list with 10 entries. Each entry contains a trend.
    '''
    url  = '%s/trends/place.json' % (self.base_url)
    parameters = {'id': id}

    if exclude:
      parameters['exclude'] = exclude

    json = self._FetchUrl(url, parameters=parameters)
    data = self._ParseAndCheckTwitter(json)

    trends = []
    timestamp = data[0]['as_of']

    for trend in data[0]['trends']:
        trends.append(Trend.NewFromJsonDict(trend, timestamp = timestamp))
    return trends

  def GetHomeTimeline(self,
                         count=None,
                         since_id=None,
                         max_id=None,
                         trim_user=False,
                         exclude_replies=False,
                         contributor_details=False,
                         include_entities=True):
    '''
    Fetch a collection of the most recent Tweets and retweets posted by the
    authenticating user and the users they follow.

    The home timeline is central to how most users interact with the Twitter
    service.

    The twitter.Api instance must be authenticated.

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
        tweets before filtering out retweets and replies.
        [Optional]
      contributor_details:
        This parameter enhances the contributors element of the
        status response to include the screen_name of the contributor.
        By default only the user_id of the contributor is included.
        [Optional]
      include_entities:
        The entities node will be disincluded when set to false.
        This node offers a variety of metadata about the tweet in a
        discreet structure, including: user_mentions, urls, and
        hashtags. [Optional]

    Returns:
      A sequence of twitter.Status instances, one for each message
    '''
    url = '%s/statuses/home_timeline.json' % self.base_url

    if not self._oauth_consumer:
      raise TwitterError("API must be authenticated.")
    parameters = {}
    if count is not None:
      try:
        if int(count) > 200:
          raise TwitterError("'count' may not be greater than 200")
      except ValueError:
        raise TwitterError("'count' must be an integer")
      parameters['count'] = count
    if since_id:
      try:
        parameters['since_id'] = long(since_id)
      except ValueError:
        raise TwitterError("'since_id' must be an integer")
    if max_id:
      try:
        parameters['max_id'] = long(max_id)
      except ValueError:
        raise TwitterError("'max_id' must be an integer")
    if trim_user:
      parameters['trim_user'] = 1
    if exclude_replies:
      parameters['exclude_replies'] = 1
    if contributor_details:
      parameters['contributor_details'] = 1
    if not include_entities:
      parameters['include_entities'] = 'false'
    json = self._FetchUrl(url, parameters=parameters)
    data = self._ParseAndCheckTwitter(json)
    return [Status.NewFromJsonDict(x) for x in data]

  def GetUserTimeline(self,
                      user_id=None,
                      screen_name=None,
                      since_id=None,
                      max_id=None,
                      count=None,
                      include_rts=None,
                      trim_user=None,
                      exclude_replies=None):
    '''Fetch the sequence of public Status messages for a single user.

    The twitter.Api instance must be authenticated if the user is private.

    Args:
      user_id:
        Specifies the ID of the user for whom to return the
        user_timeline. Helpful for disambiguating when a valid user ID
        is also a valid screen name. [Optional]
      screen_name:
        Specifies the screen name of the user for whom to return the
        user_timeline. Helpful for disambiguating when a valid screen
        name is also a user ID. [Optional]
      since_id:
        Returns results with an ID greater than (that is, more recent
        than) the specified ID. There are limits to the number of
        Tweets which can be accessed through the API. If the limit of
        Tweets has occurred since the since_id, the since_id will be
        forced to the oldest ID available. [Optional]
      max_id:
        Returns only statuses with an ID less than (that is, older
        than) or equal to the specified ID. [Optional]
      count:
        Specifies the number of statuses to retrieve. May not be
        greater than 200.  [Optional]
      include_rts:
        If True, the timeline will contain native retweets (if they
        exist) in addition to the standard stream of tweets. [Optional]
      trim_user:
        If True, statuses will only contain the numerical user ID only.
        Otherwise a full user object will be returned for each status.
        [Optional]
      exclude_replies:
        If True, this will prevent replies from appearing in the returned
        timeline. Using exclude_replies with the count parameter will mean you
        will receive up-to count tweets - this is because the count parameter
        retrieves that many tweets before filtering out retweets and replies.
        This parameter is only supported for JSON and XML responses. [Optional]

    Returns:
      A sequence of Status instances, one for each message up to count
    '''
    parameters = {}

    url = '%s/statuses/user_timeline.json' % (self.base_url)

    if user_id:
      parameters['user_id'] = user_id
    elif screen_name:
      parameters['screen_name'] = screen_name

    if since_id:
      try:
        parameters['since_id'] = long(since_id)
      except:
        raise TwitterError("since_id must be an integer")

    if max_id:
      try:
        parameters['max_id'] = long(max_id)
      except:
        raise TwitterError("max_id must be an integer")

    if count:
      try:
        parameters['count'] = int(count)
      except:
        raise TwitterError("count must be an integer")

    if include_rts:
      parameters['include_rts'] = 1

    if trim_user:
      parameters['trim_user'] = 1

    if exclude_replies:
      parameters['exclude_replies'] = 1

    json = self._FetchUrl(url, parameters=parameters)
    data = self._ParseAndCheckTwitter(json)
    return [Status.NewFromJsonDict(x) for x in data]

  def GetStatus(self,
                id,
                trim_user=False,
                include_my_retweet=True,
                include_entities=True):
    '''Returns a single status message, specified by the id parameter.

    The twitter.Api instance must be authenticated.

    Args:
      id:
        The numeric ID of the status you are trying to retrieve.
      trim_user:
        When set to True, each tweet returned in a timeline will include
        a user object including only the status authors numerical ID.
        Omit this parameter to receive the complete user object.
        [Optional]
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
    '''
    url  = '%s/statuses/show.json' % (self.base_url)

    if not self._oauth_consumer:
      raise TwitterError("API must be authenticated.")

    parameters = {}

    try:
      parameters['id'] = long(id)
    except ValueError:
      raise TwitterError("'id' must be an integer.")

    if trim_user:
      parameters['trim_user'] = 1
    if include_my_retweet:
      parameters['include_my_retweet'] = 1
    if not include_entities:
      parameters['include_entities'] = 'none'

    json = self._FetchUrl(url, parameters=parameters)
    data = self._ParseAndCheckTwitter(json)
    return Status.NewFromJsonDict(data)

  def DestroyStatus(self, id, trim_user=False):
    '''Destroys the status specified by the required ID parameter.

    The twitter.Api instance must be authenticated and the
    authenticating user must be the author of the specified status.

    Args:
      id:
        The numerical ID of the status you're trying to destroy.

    Returns:
      A twitter.Status instance representing the destroyed status message
    '''
    if not self._oauth_consumer:
      raise TwitterError("API must be authenticated.")

    try:
      post_data = {'id': long(id)}
    except:
      raise TwitterError("id must be an integer")
    url  = '%s/statuses/destroy/%s.json' % (self.base_url, id)
    if trim_user:
      post_data['trim_user'] = 1
    json = self._FetchUrl(url, post_data=post_data)
    data = self._ParseAndCheckTwitter(json)
    return Status.NewFromJsonDict(data)

  @classmethod
  def _calculate_status_length(cls, status, linksize=19):
    dummy_link_replacement = 'https://-%d-chars%s/' % (linksize, '-'*(linksize - 18))
    shortened = ' '.join([x if not (x.startswith('http://') or
                                    x.startswith('https://'))
                            else
                                dummy_link_replacement
                            for x in status.split(' ')])
    return len(shortened)

  def PostUpdate(self, status, in_reply_to_status_id=None, latitude=None, longitude=None, place_id=None, display_coordinates=False, trim_user=False):
    '''Post a twitter status message from the authenticated user.

    The twitter.Api instance must be authenticated.

    https://dev.twitter.com/docs/api/1.1/post/statuses/update

    Args:
      status:
        The message text to be posted.
        Must be less than or equal to 140 characters.
      in_reply_to_status_id:
        The ID of an existing status that the status to be posted is
        in reply to.  This implicitly sets the in_reply_to_user_id
        attribute of the resulting status to the user ID of the
        message being replied to.  Invalid/missing status IDs will be
        ignored. [Optional]
      latitude:
        Latitude coordinate of the tweet in degrees. Will only work
        in conjunction with longitude argument. Both longitude and
        latitude will be ignored by twitter if the user has a false
        geo_enabled setting. [Optional]
      longitude:
        Longitude coordinate of the tweet in degrees. Will only work
        in conjunction with latitude argument. Both longitude and
        latitude will be ignored by twitter if the user has a false
        geo_enabled setting. [Optional]
      place_id:
        A place in the world. These IDs can be retrieved from
        GET geo/reverse_geocode. [Optional]
      display_coordinates:
        Whether or not to put a pin on the exact coordinates a tweet
        has been sent from. [Optional]
      trim_user:
        If True the returned payload will only contain the user IDs,
        otherwise the payload will contain the full user data item.
        [Optional]
    Returns:
      A twitter.Status instance representing the message posted.
    '''
    if not self._oauth_consumer:
      raise TwitterError("The twitter.Api instance must be authenticated.")

    url = '%s/statuses/update.json' % self.base_url

    if isinstance(status, unicode) or self._input_encoding is None:
      u_status = status
    else:
      u_status = unicode(status, self._input_encoding)

    #if self._calculate_status_length(u_status, self._shortlink_size) > CHARACTER_LIMIT:
    #  raise TwitterError("Text must be less than or equal to %d characters. "
    #                     "Consider using PostUpdates." % CHARACTER_LIMIT)

    data = {'status': status}
    if in_reply_to_status_id:
      data['in_reply_to_status_id'] = in_reply_to_status_id
    if latitude is not None and longitude is not None:
      data['lat']     = str(latitude)
      data['long']    = str(longitude)
    if place_id is not None:
      data['place_id'] = str(place_id)
    if display_coordinates:
      data['display_coordinates'] = 'true'
    if trim_user:
      data['trim_user'] = 'true'
    json = self._FetchUrl(url, post_data=data)
    data = self._ParseAndCheckTwitter(json)
    return Status.NewFromJsonDict(data)

  def PostUpdates(self, status, continuation=None, **kwargs):
    '''Post one or more twitter status messages from the authenticated user.

    Unlike api.PostUpdate, this method will post multiple status updates
    if the message is longer than 140 characters.

    The twitter.Api instance must be authenticated.

    Args:
      status:
        The message text to be posted.
        May be longer than 140 characters.
      continuation:
        The character string, if any, to be appended to all but the
        last message.  Note that Twitter strips trailing '...' strings
        from messages.  Consider using the unicode \u2026 character
        (horizontal ellipsis) instead. [Defaults to None]
      **kwargs:
        See api.PostUpdate for a list of accepted parameters.

    Returns:
      A of list twitter.Status instance representing the messages posted.
    '''
    results = list()
    if continuation is None:
      continuation = ''
    line_length = CHARACTER_LIMIT - len(continuation)
    lines = textwrap.wrap(status, line_length)
    for line in lines[0:-1]:
      results.append(self.PostUpdate(line + continuation, **kwargs))
    results.append(self.PostUpdate(lines[-1], **kwargs))
    return results

  def PostRetweet(self, original_id, trim_user=False):
    '''Retweet a tweet with the Retweet API.

    The twitter.Api instance must be authenticated.

    Args:
      original_id:
        The numerical id of the tweet that will be retweeted
      trim_user:
        If True the returned payload will only contain the user IDs,
        otherwise the payload will contain the full user data item.
        [Optional]

    Returns:
      A twitter.Status instance representing the original tweet with retweet details embedded.
    '''
    if not self._oauth_consumer:
      raise TwitterError("The twitter.Api instance must be authenticated.")

    try:
      if int(original_id) <= 0:
        raise TwitterError("'original_id' must be a positive number")
    except ValueError:
        raise TwitterError("'original_id' must be an integer")

    url = '%s/statuses/retweet/%s.json' % (self.base_url, original_id)

    data = {'id': original_id}
    if trim_user:
      data['trim_user'] = 'true'
    json = self._FetchUrl(url, post_data=data)
    data = self._ParseAndCheckTwitter(json)
    return Status.NewFromJsonDict(data)

  def GetUserRetweets(self, count=None, since_id=None, max_id=None, trim_user=False):
    '''Fetch the sequence of retweets made by the authenticated user.

    The twitter.Api instance must be authenticated.

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
    '''
    return self.GetUserTimeline(since_id=since_id, count=count, max_id=max_id, trim_user=trim_user, exclude_replies=True, include_rts=True)

  def GetReplies(self, since_id=None, count=None, max_id=None, trim_user=False):
    '''Get a sequence of status messages representing the 20 most
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
    '''
    return self.GetUserTimeline(since_id=since_id, count=count, max_id=max_id, trim_user=trim_user, exclude_replies=False, include_rts=False)

  def GetRetweets(self, statusid, count=None, trim_user=False):
    '''Returns up to 100 of the first retweets of the tweet identified
    by statusid

    Args:
      statusid:
        The ID of the tweet for which retweets should be searched for
      count:
        The number of status messages to retrieve. [Optional]
      trim_user:
        If True the returned payload will only contain the user IDs,
        otherwise the payload will contain the full user data item.
        [Optional]

    Returns:
      A list of twitter.Status instances, which are retweets of statusid
    '''
    if not self._oauth_consumer:
      raise TwitterError("The twitter.Api instsance must be authenticated.")
    url = '%s/statuses/retweets/%s.json' % (self.base_url, statusid)
    parameters = {}
    if trim_user:
      parameters['trim_user'] = 'true'
    if count:
      try:
        parameters['count'] = int(count)
      except:
        raise TwitterError("count must be an integer")
    json = self._FetchUrl(url, parameters=parameters)
    data = self._ParseAndCheckTwitter(json)
    return [Status.NewFromJsonDict(s) for s in data]

  def GetRetweetsOfMe(self,
                      count=None,
                      since_id=None,
                      max_id=None,
                      trim_user=False,
                      include_entities=True,
                      include_user_entities=True):
    '''Returns up to 100 of the most recent tweets of the user that have been
    retweeted by others.

    Args:
      count:
        The number of retweets to retrieve, up to 100. If omitted, 20 is
        assumed.
      since_id:
        Returns results with an ID greater than (newer than) this ID.
      max_id:
        Returns results with an ID less than or equal to this ID.
      trim_user:
        When True, the user object for each tweet will only be an ID.
      include_entities:
        When True, the tweet entities will be included.
      include_user_entities:
        When True, the user entities will be included.
    '''
    if not self._oauth_consumer:
      raise TwitterError("The twitter.Api instance must be authenticated.")
    url = '%s/statuses/retweets_of_me.json' % self.base_url
    parameters = {}
    if count is not None:
      try:
        if int(count) > 100:
          raise TwitterError("'count' may not be greater than 100")
      except ValueError:
        raise TwitterError("'count' must be an integer")
    if count:
      parameters['count'] = count
    if since_id:
      parameters['since_id'] = since_id
    if max_id:
      parameters['max_id'] = max_id
    if trim_user:
      parameters['trim_user'] = trim_user
    if not include_entities:
      parameters['include_entities'] = include_entities
    if not include_user_entities:
      parameters['include_user_entities'] = include_user_entities
    json = self._FetchUrl(url, parameters=parameters)
    data = self._ParseAndCheckTwitter(json)
    return [Status.NewFromJsonDict(s) for s in data]

  def GetFriends(self, user_id=None, screen_name=None, cursor=-1, skip_status=False, include_user_entities=False):
    '''Fetch the sequence of twitter.User instances, one for each friend.

    The twitter.Api instance must be authenticated.

    Args:
      user_id:
        The twitter id of the user whose friends you are fetching.
        If not specified, defaults to the authenticated user. [Optional]
      screen_name:
        The twitter name of the user whose friends you are fetching.
        If not specified, defaults to the authenticated user. [Optional]
      cursor:
        Should be set to -1 for the initial call and then is used to
        control what result page Twitter returns [Optional(ish)]
      skip_status:
        If True the statuses will not be returned in the user items.
        [Optional]
      include_user_entities:
        When True, the user entities will be included.

    Returns:
      A sequence of twitter.User instances, one for each friend
    '''
    if not self._oauth_consumer:
      raise TwitterError("twitter.Api instance must be authenticated")
    url = '%s/friends/list.json' % self.base_url
    result = []
    parameters = {}
    if user_id is not None:
      parameters['user_id'] = user_id
    if screen_name is not None:
      parameters['screen_name'] = screen_name
    if skip_status:
      parameters['skip_status'] = True
    if include_user_entities:
      parameters['include_user_entities'] = True
    while True:
      parameters['cursor'] = cursor
      json = self._FetchUrl(url, parameters=parameters)
      data = self._ParseAndCheckTwitter(json)
      result += [User.NewFromJsonDict(x) for x in data['users']]
      if 'next_cursor' in data:
        if data['next_cursor'] == 0 or data['next_cursor'] == data['previous_cursor']:
          break
        else:
          cursor = data['next_cursor']
      else:
        break
    return result

  def GetFriendIDs(self, user_id=None, screen_name=None, cursor=-1, stringify_ids=False, count=None):
      '''Returns a list of twitter user id's for every person
      the specified user is following.

      Args:
        user_id:
          The id of the user to retrieve the id list for
          [Optional]
        screen_name:
          The screen_name of the user to retrieve the id list for
          [Optional]
        cursor:
          Specifies the Twitter API Cursor location to start at.
          Note: there are pagination limits.
          [Optional]
        stringify_ids:
          if True then twitter will return the ids as strings instead of integers.
          [Optional]
        count:
          The number of status messages to retrieve. [Optional]

      Returns:
        A list of integers, one for each user id.
      '''
      url = '%s/friends/ids.json' % self.base_url
      if not self._oauth_consumer:
          raise TwitterError("twitter.Api instance must be authenticated")
      parameters = {}
      if user_id is not None:
        parameters['user_id'] = user_id
      if screen_name is not None:
        parameters['screen_name'] = screen_name
      if stringify_ids:
        parameters['stringify_ids'] = True
      if count is not None:
        parameters['count'] = count
      result = []
      while True:
        parameters['cursor'] = cursor
        json = self._FetchUrl(url, parameters=parameters)
        data = self._ParseAndCheckTwitter(json)
        result += [x for x in data['ids']]
        if 'next_cursor' in data:
          if data['next_cursor'] == 0 or data['next_cursor'] == data['previous_cursor']:
            break
          else:
            cursor = data['next_cursor']
        else:
          break
      return result


  def GetFollowerIDs(self, user_id=None, screen_name=None, cursor=-1, stringify_ids=False, count=None, total_count=None):
      '''Returns a list of twitter user id's for every person
      that is following the specified user.

      Args:
        user_id:
          The id of the user to retrieve the id list for
          [Optional]
        screen_name:
          The screen_name of the user to retrieve the id list for
          [Optional]
        cursor:
          Specifies the Twitter API Cursor location to start at.
          Note: there are pagination limits.
          [Optional]
        stringify_ids:
          if True then twitter will return the ids as strings instead of integers.
          [Optional]
        count:
          The number of user id's to retrieve per API request. Please be aware that
          this might get you rate-limited if set to a small number. By default Twitter
          will retrieve 5000 UIDs per call.
          [Optional]
        total_count:
          The total amount of UIDs to retrieve. Good if the account has many followers
          and you don't want to get rate limited. The data returned might contain more
          UIDs if total_count is not a multiple of count (5000 by default).
          [Optional]


      Returns:
        A list of integers, one for each user id.
      '''
      url = '%s/followers/ids.json' % self.base_url
      if not self._oauth_consumer:
          raise TwitterError("twitter.Api instance must be authenticated")
      parameters = {}
      if user_id is not None:
        parameters['user_id'] = user_id
      if screen_name is not None:
        parameters['screen_name'] = screen_name
      if stringify_ids:
        parameters['stringify_ids'] = True
      if count is not None:
        parameters['count'] = count
      result = []
      while True:
        if total_count and total_count < count:
          parameters['count'] = total_count
        parameters['cursor'] = cursor
        json = self._FetchUrl(url, parameters=parameters)
        data = self._ParseAndCheckTwitter(json)
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

  def GetFollowers(self, user_id=None, screen_name=None, cursor=-1, skip_status=False, include_user_entities=False):
    '''Fetch the sequence of twitter.User instances, one for each follower

    The twitter.Api instance must be authenticated.

    Args:
      user_id:
        The twitter id of the user whose followers you are fetching.
        If not specified, defaults to the authenticated user. [Optional]
      screen_name:
        The twitter name of the user whose followers you are fetching.
        If not specified, defaults to the authenticated user. [Optional]
      cursor:
        Should be set to -1 for the initial call and then is used to
        control what result page Twitter returns [Optional(ish)]
      skip_status:
        If True the statuses will not be returned in the user items.
        [Optional]
      include_user_entities:
        When True, the user entities will be included.

    Returns:
      A sequence of twitter.User instances, one for each follower
    '''
    if not self._oauth_consumer:
      raise TwitterError("twitter.Api instance must be authenticated")
    url = '%s/followers/list.json' % self.base_url
    result = []
    parameters = {}
    if user_id is not None:
      parameters['user_id'] = user_id
    if screen_name is not None:
      parameters['screen_name'] = screen_name
    if skip_status:
      parameters['skip_status'] = True
    if include_user_entities:
      parameters['include_user_entities'] = True
    while True:
      parameters['cursor'] = cursor
      json = self._FetchUrl(url, parameters=parameters)
      data = self._ParseAndCheckTwitter(json)
      result += [User.NewFromJsonDict(x) for x in data['users']]
      if 'next_cursor' in data:
        if data['next_cursor'] == 0 or data['next_cursor'] == data['previous_cursor']:
          break
        else:
          cursor = data['next_cursor']
      else:
        break
    return result

  def UsersLookup(self, user_id=None, screen_name=None, users=None, include_entities=True):
    '''Fetch extended information for the specified users.

    Users may be specified either as lists of either user_ids,
    screen_names, or twitter.User objects. The list of users that
    are queried is the union of all specified parameters.

    The twitter.Api instance must be authenticated.

    Args:
      user_id:
        A list of user_ids to retrieve extended information.
        [Optional]
      screen_name:
        A list of screen_names to retrieve extended information.
        [Optional]
      users:
        A list of twitter.User objects to retrieve extended information.
        [Optional]
      include_entities:
        The entities node that may appear within embedded statuses will be
        disincluded when set to False.
        [Optional]

    Returns:
      A list of twitter.User objects for the requested users
    '''

    if not self._oauth_consumer:
      raise TwitterError("The twitter.Api instance must be authenticated.")
    if not user_id and not screen_name and not users:
      raise TwitterError("Specify at least one of user_id, screen_name, or users.")
    url = '%s/users/lookup.json' % self.base_url
    parameters = {}
    uids = list()
    if user_id:
      uids.extend(user_id)
    if users:
      uids.extend([u.id for u in users])
    if len(uids):
      parameters['user_id'] = ','.join(["%s" % u for u in uids])
    if screen_name:
      parameters['screen_name'] = ','.join(screen_name)
    if not include_entities:
      parameters['include_entities'] = 'false'
    json = self._FetchUrl(url, parameters=parameters)
    try:
      data = self._ParseAndCheckTwitter(json)
    except TwitterError, e:
        _, e, _ = sys.exc_info()
        t = e.args[0]
        if len(t) == 1 and ('code' in t[0]) and (t[0]['code'] == 34):
          data = []
        else:
            raise

    return [User.NewFromJsonDict(u) for u in data]

  def GetUser(self, user_id=None, screen_name=None, include_entities=True):
    '''Returns a single user.

    The twitter.Api instance must be authenticated.

    Args:
      user_id:
        The id of the user to retrieve.
        [Optional]
      screen_name:
        The screen name of the user for whom to return results for. Either a
        user_id or screen_name is required for this method.
        [Optional]
      include_entities:
        if set to False, the 'entities' node will not be included.
        [Optional]


    Returns:
      A twitter.User instance representing that user
    '''
    url  = '%s/users/show.json' % (self.base_url)
    parameters = {}

    if not self._oauth_consumer:
      raise TwitterError("The twitter.Api instance must be authenticated.")

    if user_id:
      parameters['user_id'] = user_id
    elif screen_name:
      parameters['screen_name'] = screen_name
    else:
      raise TwitterError("Specify at least one of user_id or screen_name.")

    if not include_entities:
      parameters['include_entities'] = 'false'

    json = self._FetchUrl(url, parameters=parameters)
    data = self._ParseAndCheckTwitter(json)
    return User.NewFromJsonDict(data)

  def GetDirectMessages(self, since_id=None, max_id=None, count=None, include_entities=True, skip_status=False):
    '''Returns a list of the direct messages sent to the authenticating user.

    The twitter.Api instance must be authenticated.

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
        The entities node will not be included when set to False.
        [Optional]
      skip_status:
        When set to True statuses will not be included in the returned user
        objects. [Optional]

    Returns:
      A sequence of twitter.DirectMessage instances
    '''
    url = '%s/direct_messages.json' % self.base_url
    if not self._oauth_consumer:
      raise TwitterError("The twitter.Api instance must be authenticated.")
    parameters = {}
    if since_id:
      parameters['since_id'] = since_id
    if max_id:
      parameters['max_id'] = max_id
    if count:
      try:
        parameters['count'] = int(count)
      except:
        raise TwitterError("count must be an integer")
    if not include_entities:
      parameters['include_entities'] = 'false'
    if skip_status:
      parameters['skip_status'] = 1
    json = self._FetchUrl(url, parameters=parameters)
    data = self._ParseAndCheckTwitter(json)
    return [DirectMessage.NewFromJsonDict(x) for x in data]

  def GetSentDirectMessages(self, since_id=None, max_id=None, count=None, page=None, include_entities=True):
    '''Returns a list of the direct messages sent by the authenticating user.

    The twitter.Api instance must be authenticated.

    Args:
      since_id:
        Returns results with an ID greater than (that is, more recent
        than) the specified ID. There are limits to the number of
        Tweets which can be accessed through the API. If the limit of
        Tweets has occured since the since_id, the since_id will be
        forced to the oldest ID available. [Optional]
      max_id:
        Returns results with an ID less than (that is, older than) or
        equal to the specified ID. [Optional]
      count:
        Specifies the number of direct messages to try and retrieve, up to a
        maximum of 200. The value of count is best thought of as a limit to the
        number of Tweets to return because suspended or deleted content is
        removed after the count has been applied. [Optional]
      page:
        Specifies the page of results to retrieve.
        Note: there are pagination limits. [Optional]
      include_entities:
        The entities node will not be included when set to False.
        [Optional]

    Returns:
      A sequence of twitter.DirectMessage instances
    '''
    url = '%s/direct_messages/sent.json' % self.base_url
    if not self._oauth_consumer:
      raise TwitterError("The twitter.Api instance must be authenticated.")
    parameters = {}
    if since_id:
      parameters['since_id'] = since_id
    if page:
      parameters['page'] = page
    if max_id:
      parameters['max_id'] = max_id
    if count:
      try:
        parameters['count'] = int(count)
      except:
        raise TwitterError("count must be an integer")
    if not include_entities:
      parameters['include_entities'] = 'false'
    json = self._FetchUrl(url, parameters=parameters)
    data = self._ParseAndCheckTwitter(json)
    return [DirectMessage.NewFromJsonDict(x) for x in data]

  def PostDirectMessage(self, text, user_id=None, screen_name=None):
    '''Post a twitter direct message from the authenticated user

    The twitter.Api instance must be authenticated. user_id or screen_name
    must be specified.

    Args:
      text: The message text to be posted.  Must be less than 140 characters.
      user_id:
        The ID of the user who should receive the direct message.
        [Optional]
      screen_name:
        The screen name of the user who should receive the direct message.
        [Optional]

    Returns:
      A twitter.DirectMessage instance representing the message posted
    '''
    if not self._oauth_consumer:
      raise TwitterError("The twitter.Api instance must be authenticated.")
    url  = '%s/direct_messages/new.json' % self.base_url
    data = {'text': text}
    if user_id:
      data['user_id'] = user_id
    elif screen_name:
      data['screen_name'] = screen_name
    else:
      raise TwitterError("Specify at least one of user_id or screen_name.")
    json = self._FetchUrl(url, post_data=data)
    data = self._ParseAndCheckTwitter(json)
    return DirectMessage.NewFromJsonDict(data)

  def DestroyDirectMessage(self, id, include_entities=True):
    '''Destroys the direct message specified in the required ID parameter.

    The twitter.Api instance must be authenticated, and the
    authenticating user must be the recipient of the specified direct
    message.

    Args:
      id: The id of the direct message to be destroyed

    Returns:
      A twitter.DirectMessage instance representing the message destroyed
    '''
    url  = '%s/direct_messages/destroy.json' % self.base_url
    data = {'id': id}
    if not include_entities:
      data['include_entities'] = 'false'
    json = self._FetchUrl(url, post_data=data)
    data = self._ParseAndCheckTwitter(json)
    return DirectMessage.NewFromJsonDict(data)

  def CreateFriendship(self, user_id=None, screen_name=None, follow=True):
    '''Befriends the user specified by the user_id or screen_name.

    The twitter.Api instance must be authenticated.

    Args:
      user_id:
        A user_id to follow [Optional]
      screen_name:
        A screen_name to follow [Optional]
      follow:
        Set to False to disable notifications for the target user
    Returns:
      A twitter.User instance representing the befriended user.
    '''
    url  = '%s/friendships/create.json' % (self.base_url)
    data = {}
    if user_id:
      data['user_id'] = user_id
    elif screen_name:
      data['screen_name'] = screen_name
    else:
      raise TwitterError("Specify at least one of user_id or screen_name.")
    if follow:
      data['follow'] = 'true'
    else:
      data['follow'] = 'false'
    json = self._FetchUrl(url, post_data=data)
    data = self._ParseAndCheckTwitter(json)
    return User.NewFromJsonDict(data)

  def DestroyFriendship(self, user_id=None, screen_name=None):
    '''Discontinues friendship with a user_id or screen_name.

    The twitter.Api instance must be authenticated.

    Args:
      user_id:
        A user_id to unfollow [Optional]
      screen_name:
        A screen_name to unfollow [Optional]
    Returns:
      A twitter.User instance representing the discontinued friend.
    '''
    url  = '%s/friendships/destroy.json' % self.base_url
    data = {}
    if user_id:
      data['user_id'] = user_id
    elif screen_name:
      data['screen_name'] = screen_name
    else:
      raise TwitterError("Specify at least one of user_id or screen_name.")
    json = self._FetchUrl(url, post_data=data)
    data = self._ParseAndCheckTwitter(json)
    return User.NewFromJsonDict(data)

  def CreateFavorite(self, status=None, id=None, include_entities=True):
    '''Favorites the specified status object or id as the authenticating user.
    Returns the favorite status when successful.

    The twitter.Api instance must be authenticated.

    Args:
      id:
        The id of the twitter status to mark as a favorite.
        [Optional]
      status:
        The twitter.Status object to mark as a favorite.
        [Optional]
      include_entities:
        The entities node will be omitted when set to False.
    Returns:
      A twitter.Status instance representing the newly-marked favorite.
    '''
    url  = '%s/favorites/create.json' % self.base_url
    data = {}
    if id:
      data['id'] = id
    elif status:
      data['id'] = status.id
    else:
      raise TwitterError("Specify id or status")
    if not include_entities:
      data['include_entities'] = 'false'
    json = self._FetchUrl(url, post_data=data)
    data = self._ParseAndCheckTwitter(json)
    return Status.NewFromJsonDict(data)

  def DestroyFavorite(self, status=None, id=None, include_entities=True):
    '''Un-Favorites the specified status object or id as the authenticating user.
    Returns the un-favorited status when successful.

    The twitter.Api instance must be authenticated.

    Args:
      id:
        The id of the twitter status to unmark as a favorite.
        [Optional]
      status:
        The twitter.Status object to unmark as a favorite.
        [Optional]
      include_entities:
        The entities node will be omitted when set to False.
    Returns:
      A twitter.Status instance representing the newly-unmarked favorite.
    '''
    url  = '%s/favorites/destroy.json' % self.base_url
    data = {}
    if id:
      data['id'] = id
    elif status:
      data['id'] = status.id
    else:
      raise TwitterError("Specify id or status")
    if not include_entities:
      data['include_entities'] = 'false'
    json = self._FetchUrl(url, post_data=data)
    data = self._ParseAndCheckTwitter(json)
    return Status.NewFromJsonDict(data)

  def GetFavorites(self,
                   user_id=None,
                   screen_name=None,
                   count=None,
                   since_id=None,
                   max_id=None,
                   include_entities=True):
    '''Return a list of Status objects representing favorited tweets.
    By default, returns the (up to) 20 most recent tweets for the
    authenticated user.

    Args:
      user:
        The twitter name or id of the user whose favorites you are fetching.
        If not specified, defaults to the authenticated user. [Optional]
      page:
        Specifies the page of results to retrieve.
        Note: there are pagination limits. [Optional]
    '''
    parameters = {}

    url = '%s/favorites/list.json' % self.base_url

    if user_id:
      parameters['user_id'] = user_id
    elif screen_name:
      parameters['screen_name'] = user_id

    if since_id:
      try:
        parameters['since_id'] = long(since_id)
      except:
        raise TwitterError("since_id must be an integer")

    if max_id:
      try:
        parameters['max_id'] = long(max_id)
      except:
        raise TwitterError("max_id must be an integer")

    if count:
      try:
        parameters['count'] = int(count)
      except:
        raise TwitterError("count must be an integer")

    if include_entities:
        parameters['include_entities'] = True


    json = self._FetchUrl(url, parameters=parameters)
    data = self._ParseAndCheckTwitter(json)
    return [Status.NewFromJsonDict(x) for x in data]

  def GetMentions(self,
                  count=None,
                  since_id=None,
                  max_id=None,
                  trim_user=False,
                  contributor_details=False,
                  include_entities=True):
    '''Returns the 20 most recent mentions (status containing @screen_name)
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
        (that is, older than) the specified ID.  [Optional]
      trim_user:
        When set to True, each tweet returned in a timeline will include a user
        object including only the status authors numerical ID. Omit this
        parameter to receive the complete user object.
      contributor_details:
        If set to True, this parameter enhances the contributors element of the
        status response to include the screen_name of the contributor. By
        default only the user_id of the contributor is included.
      include_entities:
        The entities node will be disincluded when set to False.

    Returns:
      A sequence of twitter.Status instances, one for each mention of the user.
    '''

    url = '%s/statuses/mentions_timeline.json' % self.base_url

    if not self._oauth_consumer:
      raise TwitterError("The twitter.Api instance must be authenticated.")

    parameters = {}

    if count:
      try:
        parameters['count'] = int(count)
      except:
        raise TwitterError("count must be an integer")
    if since_id:
      try:
        parameters['since_id'] = long(since_id)
      except:
        raise TwitterError("since_id must be an integer")
    if max_id:
      try:
        parameters['max_id'] = long(max_id)
      except:
        raise TwitterError("max_id must be an integer")
    if trim_user:
      parameters['trim_user'] = 1
    if contributor_details:
      parameters['contributor_details'] = 'true'
    if not include_entities:
      parameters['include_entities'] = 'false'

    json = self._FetchUrl(url, parameters=parameters)
    data = self._ParseAndCheckTwitter(json)
    return [Status.NewFromJsonDict(x) for x in data]

  def CreateList(self, name, mode=None, description=None):
    '''Creates a new list with the give name for the authenticated user.

    The twitter.Api instance must be authenticated.

    Args:
      name:
        New name for the list
      mode:
        'public' or 'private'.
        Defaults to 'public'. [Optional]
      description:
        Description of the list. [Optional]

    Returns:
      A twitter.List instance representing the new list
    '''
    url = '%s/lists/create.json' % self.base_url

    if not self._oauth_consumer:
      raise TwitterError("The twitter.Api instance must be authenticated.")
    parameters = {'name': name}
    if mode is not None:
      parameters['mode'] = mode
    if description is not None:
      parameters['description'] = description
    json = self._FetchUrl(url, post_data=parameters)
    data = self._ParseAndCheckTwitter(json)
    return List.NewFromJsonDict(data)

  def DestroyList(self,
                  owner_screen_name=False,
                  owner_id=False,
                  list_id=None,
                  slug=None):
    '''
    Destroys the list identified by list_id or owner_screen_name/owner_id and
    slug.

    The twitter.Api instance must be authenticated.

    Args:
      owner_screen_name:
        The screen_name of the user who owns the list being requested by a slug.
      owner_id:
        The user ID of the user who owns the list being requested by a slug.
      list_id:
        The numerical id of the list.
      slug:
        You can identify a list by its slug instead of its numerical id. If you
        decide to do so, note that you'll also have to specify the list owner
        using the owner_id or owner_screen_name parameters.
    Returns:
      A twitter.List instance representing the removed list.
    '''
    url  = '%s/lists/destroy.json' % self.base_url
    data = {}
    if list_id:
      try:
        data['list_id']= long(list_id)
      except:
        raise TwitterError("list_id must be an integer")
    elif slug:
      data['slug'] = slug
      if owner_id:
        try:
          data['owner_id'] = long(owner_id)
        except:
          raise TwitterError("owner_id must be an integer")
      elif owner_screen_name:
        data['owner_screen_name'] = owner_screen_name
      else:
        raise TwitterError("Identify list by list_id or owner_screen_name/owner_id and slug")
    else:
      raise TwitterError("Identify list by list_id or owner_screen_name/owner_id and slug")

    json = self._FetchUrl(url, post_data=data)
    data = self._ParseAndCheckTwitter(json)
    return List.NewFromJsonDict(data)

  def CreateSubscription(self,
                  owner_screen_name=False,
                  owner_id=False,
                  list_id=None,
                  slug=None):
    '''Creates a subscription to a list by the authenticated user

    The twitter.Api instance must be authenticated.

    Args:
      owner_screen_name:
        The screen_name of the user who owns the list being requested by a slug.
      owner_id:
        The user ID of the user who owns the list being requested by a slug.
      list_id:
        The numerical id of the list.
      slug:
        You can identify a list by its slug instead of its numerical id. If you
        decide to do so, note that you'll also have to specify the list owner
        using the owner_id or owner_screen_name parameters.
    Returns:
      A twitter.List instance representing the list subscribed to
    '''
    url  = '%s/lists/subscribers/create.json' % (self.base_url)
    if not self._oauth_consumer:
      raise TwitterError("The twitter.Api instance must be authenticated.")
    data = {}
    if list_id:
      try:
        data['list_id']= long(list_id)
      except:
        raise TwitterError("list_id must be an integer")
    elif slug:
      data['slug'] = slug
      if owner_id:
        try:
          data['owner_id'] = long(owner_id)
        except:
          raise TwitterError("owner_id must be an integer")
      elif owner_screen_name:
        data['owner_screen_name'] = owner_screen_name
      else:
        raise TwitterError("Identify list by list_id or owner_screen_name/owner_id and slug")
    else:
      raise TwitterError("Identify list by list_id or owner_screen_name/owner_id and slug")
    json = self._FetchUrl(url, post_data=data)
    data = self._ParseAndCheckTwitter(json)
    return List.NewFromJsonDict(data)

  def DestroySubscription(self,
                  owner_screen_name=False,
                  owner_id=False,
                  list_id=None,
                  slug=None):
    '''Destroys the subscription to a list for the authenticated user

    The twitter.Api instance must be authenticated.

    Args:
      owner_screen_name:
        The screen_name of the user who owns the list being requested by a slug.
      owner_id:
        The user ID of the user who owns the list being requested by a slug.
      list_id:
        The numerical id of the list.
      slug:
        You can identify a list by its slug instead of its numerical id. If you
        decide to do so, note that you'll also have to specify the list owner
        using the owner_id or owner_screen_name parameters.
    Returns:
      A twitter.List instance representing the removed list.
    '''
    url  = '%s/lists/subscribers/destroy.json' % (self.base_url)
    if not self._oauth_consumer:
      raise TwitterError("The twitter.Api instance must be authenticated.")
    data = {}
    if list_id:
      try:
        data['list_id']= long(list_id)
      except:
        raise TwitterError("list_id must be an integer")
    elif slug:
      data['slug'] = slug
      if owner_id:
        try:
          data['owner_id'] = long(owner_id)
        except:
          raise TwitterError("owner_id must be an integer")
      elif owner_screen_name:
        data['owner_screen_name'] = owner_screen_name
      else:
        raise TwitterError("Identify list by list_id or owner_screen_name/owner_id and slug")
    else:
      raise TwitterError("Identify list by list_id or owner_screen_name/owner_id and slug")
    json = self._FetchUrl(url, post_data=data)
    data = self._ParseAndCheckTwitter(json)
    return List.NewFromJsonDict(data)

  def GetSubscriptions(self, user_id=None, screen_name=None, count=20, cursor=-1):
    '''
    Obtain a collection of the lists the specified user is subscribed to, 20
    lists per page by default. Does not include the user's own lists.

    The twitter.Api instance must be authenticated.

    Args:
      user_id:
        The ID of the user for whom to return results for. [Optional]
      screen_name:
        The screen name of the user for whom to return results for.
        [Optional]
      count:
       The amount of results to return per page. Defaults to 20.
       No more than 1000 results will ever be returned in a single page.
      cursor:
        "page" value that Twitter will use to start building the
        list sequence from.  -1 to start at the beginning.
        Twitter will return in the result the values for next_cursor
        and previous_cursor. [Optional]

    Returns:
      A sequence of twitter.List instances, one for each list
    '''
    if not self._oauth_consumer:
      raise TwitterError("twitter.Api instance must be authenticated")

    url = '%s/lists/subscriptions.json' % (self.base_url)
    parameters = {}

    try:
      parameters['cursor'] = int(cursor)
    except:
      raise TwitterError("cursor must be an integer")

    try:
      parameters['count'] = int(count)
    except:
      raise TwitterError("count must be an integer")

    if user_id is not None:
      try:
        parameters['user_id'] = long(user_id)
      except:
        raise TwitterError('user_id must be an integer')
    elif screen_name is not None:
      parameters['screen_name'] = screen_name
    else:
      raise TwitterError('Specify user_id or screen_name')

    json = self._FetchUrl(url, parameters=parameters)
    data = self._ParseAndCheckTwitter(json)
    return [List.NewFromJsonDict(x) for x in data['lists']]

  def GetLists(self, user_id=None, screen_name=None, count=None, cursor=-1):
    '''Fetch the sequence of lists for a user.

    The twitter.Api instance must be authenticated.

    Args:
      user_id:
        The ID of the user for whom to return results for. [Optional]
      screen_name:
        The screen name of the user for whom to return results for.
        [Optional]
      count:
        The amount of results to return per page. Defaults to 20. No more than
        1000 results will ever be returned in a single page.
        [Optional]
      cursor:
        "page" value that Twitter will use to start building the
        list sequence from.  -1 to start at the beginning.
        Twitter will return in the result the values for next_cursor
        and previous_cursor. [Optional]

    Returns:
      A sequence of twitter.List instances, one for each list
    '''
    if not self._oauth_consumer:
      raise TwitterError("twitter.Api instance must be authenticated")

    url = '%s/lists/ownerships.json' % self.base_url
    result = []
    parameters = {}
    if user_id is not None:
      try:
        parameters['user_id'] = long(user_id)
      except:
        raise TwitterError('user_id must be an integer')
    elif screen_name is not None:
      parameters['screen_name'] = screen_name
    else:
      raise TwitterError('Specify user_id or screen_name')
    if count is not None:
      parameters['count'] = count

    while True:
      parameters['cursor'] = cursor
      json = self._FetchUrl(url, parameters=parameters)
      data = self._ParseAndCheckTwitter(json)
      result += [List.NewFromJsonDict(x) for x in data['lists']]
      if 'next_cursor' in data:
        if data['next_cursor'] == 0 or data['next_cursor'] == data['previous_cursor']:
          break
        else:
          cursor = data['next_cursor']
      else:
        break
    return result

  def VerifyCredentials(self):
    '''Returns a twitter.User instance if the authenticating user is valid.

    Returns:
      A twitter.User instance representing that user if the
      credentials are valid, None otherwise.
    '''
    if not self._oauth_consumer:
      raise TwitterError("Api instance must first be given user credentials.")
    url = '%s/account/verify_credentials.json' % self.base_url
    try:
      json = self._FetchUrl(url, no_cache=True)
    except urllib2.HTTPError, http_error:
      if http_error.code == httplib.UNAUTHORIZED:
        return None
      else:
        raise http_error
    data = self._ParseAndCheckTwitter(json)
    return User.NewFromJsonDict(data)

  def SetCache(self, cache):
    '''Override the default cache.  Set to None to prevent caching.

    Args:
      cache:
        An instance that supports the same API as the twitter._FileCache
    '''
    if cache == DEFAULT_CACHE:
      self._cache = _FileCache()
    else:
      self._cache = cache

  def SetUrllib(self, urllib):
    '''Override the default urllib implementation.

    Args:
      urllib:
        An instance that supports the same API as the urllib2 module
    '''
    self._urllib = urllib

  def SetCacheTimeout(self, cache_timeout):
    '''Override the default cache timeout.

    Args:
      cache_timeout:
        Time, in seconds, that responses should be reused.
    '''
    self._cache_timeout = cache_timeout

  def SetUserAgent(self, user_agent):
    '''Override the default user agent

    Args:
      user_agent:
        A string that should be send to the server as the User-agent
    '''
    self._request_headers['User-Agent'] = user_agent

  def SetXTwitterHeaders(self, client, url, version):
    '''Set the X-Twitter HTTP headers that will be sent to the server.

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
    '''
    self._request_headers['X-Twitter-Client'] = client
    self._request_headers['X-Twitter-Client-URL'] = url
    self._request_headers['X-Twitter-Client-Version'] = version

  def SetSource(self, source):
    '''Suggest the "from source" value to be displayed on the Twitter web site.

    The value of the 'source' parameter must be first recognized by
    the Twitter server.  New source values are authorized on a case by
    case basis by the Twitter development team.

    Args:
      source:
        The source name as a string.  Will be sent to the server as
        the 'source' parameter.
    '''
    self._default_params['source'] = source

  def GetRateLimitStatus(self, resources=None):
    '''Fetch the rate limit status for the currently authorized user.

    Args:
      resources:
        A comma seperated list of resource families you want to know the current
        rate limit disposition of.
        [Optional]

    Returns:
      A dictionary containing the time the limit will reset (reset_time),
      the number of remaining hits allowed before the reset (remaining_hits),
      the number of hits allowed in a 60-minute period (hourly_limit), and
      the time of the reset in seconds since The Epoch (reset_time_in_seconds).
    '''
    parameters = {}
    if resources is not None:
      parameters['resources'] = resources

    url  = '%s/application/rate_limit_status.json' % self.base_url
    json = self._FetchUrl(url, parameters=parameters, no_cache=True)
    data = self._ParseAndCheckTwitter(json)
    return data

  def MaximumHitFrequency(self):
    '''Determines the minimum number of seconds that a program must wait
    before hitting the server again without exceeding the rate_limit
    imposed for the currently authenticated user.

    Returns:
      The minimum second interval that a program must use so as to not
      exceed the rate_limit imposed for the user.
    '''
    rate_status = self.GetRateLimitStatus()
    reset_time  = rate_status.get('reset_time', None)
    limit       = rate_status.get('remaining_hits', None)

    if reset_time:
      # put the reset time into a datetime object
      reset = datetime.datetime(*rfc822.parsedate(reset_time)[:7])

      # find the difference in time between now and the reset time + 1 hour
      delta = reset + datetime.timedelta(hours=1) - datetime.datetime.utcnow()

      if not limit:
          return int(delta.seconds)

      # determine the minimum number of seconds allowed as a regular interval
      max_frequency = int(delta.seconds / limit) + 1

      # return the number of seconds
      return max_frequency

    return 60

  def _BuildUrl(self, url, path_elements=None, extra_params=None):
    # Break url into constituent parts
    (scheme, netloc, path, params, query, fragment) = urlparse.urlparse(url)

    # Add any additional path elements to the path
    if path_elements:
      # Filter out the path elements that have a value of None
      p = [i for i in path_elements if i]
      if not path.endswith('/'):
        path += '/'
      path += '/'.join(p)

    # Add any additional query parameters to the query string
    if extra_params and len(extra_params) > 0:
      extra_query = self._EncodeParameters(extra_params)
      # Add it to the existing query
      if query:
        query += '&' + extra_query
      else:
        query = extra_query

    # Return the rebuilt URL
    return urlparse.urlunparse((scheme, netloc, path, params, query, fragment))

  def _InitializeRequestHeaders(self, request_headers):
    if request_headers:
      self._request_headers = request_headers
    else:
      self._request_headers = {}

  def _InitializeUserAgent(self):
    user_agent = 'Python-urllib/%s (python-twitter/%s)' % \
                 (self._urllib.__version__, __version__)
    self.SetUserAgent(user_agent)

  def _InitializeDefaultParameters(self):
    self._default_params = {}

  def _DecompressGzippedResponse(self, response):
    raw_data = response.read()
    if response.headers.get('content-encoding', None) == 'gzip':
      url_data = gzip.GzipFile(fileobj=StringIO.StringIO(raw_data)).read()
    else:
      url_data = raw_data
    return url_data

  def _Encode(self, s):
    if self._input_encoding:
      return unicode(s, self._input_encoding).encode('utf-8')
    else:
      return unicode(s).encode('utf-8')

  def _EncodeParameters(self, parameters):
    '''Return a string in key=value&key=value form

    Values of None are not included in the output string.

    Args:
      parameters:
        A dict of (key, value) tuples, where value is encoded as
        specified by self._encoding

    Returns:
      A URL-encoded string in "key=value&key=value" form
    '''
    if parameters is None:
      return None
    else:
      return urllib.urlencode(dict([(k, self._Encode(v)) for k, v in parameters.items() if v is not None]))

  def _EncodePostData(self, post_data):
    '''Return a string in key=value&key=value form

    Values are assumed to be encoded in the format specified by self._encoding,
    and are subsequently URL encoded.

    Args:
      post_data:
        A dict of (key, value) tuples, where value is encoded as
        specified by self._encoding

    Returns:
      A URL-encoded string in "key=value&key=value" form
    '''
    if post_data is None:
      return None
    else:
      return urllib.urlencode(dict([(k, self._Encode(v)) for k, v in post_data.items()]))

  def _ParseAndCheckTwitter(self, json):
    """Try and parse the JSON returned from Twitter and return
    an empty dictionary if there is any error. This is a purely
    defensive check because during some Twitter network outages
    it will return an HTML failwhale page."""
    try:
      data = simplejson.loads(json)
      self._CheckForTwitterError(data)
    except ValueError:
      if "<title>Twitter / Over capacity</title>" in json:
        raise TwitterError("Capacity Error")
      if "<title>Twitter / Error</title>" in json:
        raise TwitterError("Technical Error")
      raise TwitterError("json decoding")

    return data

  def _CheckForTwitterError(self, data):
    """Raises a TwitterError if twitter returns an error message.

    Args:
      data:
        A python dict created from the Twitter json response

    Raises:
      TwitterError wrapping the twitter error message if one exists.
    """
    # Twitter errors are relatively unlikely, so it is faster
    # to check first, rather than try and catch the exception
    if 'error' in data:
      raise TwitterError(data['error'])
    if 'errors' in data:
      raise TwitterError(data['errors'])

  def _FetchUrl(self,
                url,
                post_data=None,
                parameters=None,
                no_cache=None,
                use_gzip_compression=None):
    '''Fetch a URL, optionally caching for a specified time.

    Args:
      url:
        The URL to retrieve
      post_data:
        A dict of (str, unicode) key/value pairs.
        If set, POST will be used.
      parameters:
        A dict whose key/value pairs should encoded and added
        to the query string. [Optional]
      no_cache:
        If true, overrides the cache on the current request
      use_gzip_compression:
        If True, tells the server to gzip-compress the response.
        It does not apply to POST requests.
        Defaults to None, which will get the value to use from
        the instance variable self._use_gzip [Optional]

    Returns:
      A string containing the body of the response.
    '''
    # Build the extra parameters dict
    extra_params = {}
    if self._default_params:
      extra_params.update(self._default_params)
    if parameters:
      extra_params.update(parameters)

    if post_data:
      http_method = "POST"
    else:
      http_method = "GET"

    if self._debugHTTP:
      _debug = 1
    else:
      _debug = 0

    http_handler  = self._urllib.HTTPHandler(debuglevel=_debug)
    https_handler = self._urllib.HTTPSHandler(debuglevel=_debug)
    http_proxy = os.environ.get('http_proxy')
    https_proxy = os.environ.get('https_proxy')

    if http_proxy is None or  https_proxy is None :
      proxy_status = False
    else :
      proxy_status = True

    opener = self._urllib.OpenerDirector()
    opener.add_handler(http_handler)
    opener.add_handler(https_handler)

    if proxy_status is True :
      proxy_handler = self._urllib.ProxyHandler({'http':str(http_proxy),'https': str(https_proxy)})
      opener.add_handler(proxy_handler)

    if use_gzip_compression is None:
      use_gzip = self._use_gzip
    else:
      use_gzip = use_gzip_compression

    # Set up compression
    if use_gzip and not post_data:
      opener.addheaders.append(('Accept-Encoding', 'gzip'))

    if self._oauth_consumer is not None:
      if post_data and http_method == "POST":
        parameters = post_data.copy()

      req = oauth.Request.from_consumer_and_token(self._oauth_consumer,
                                                  token=self._oauth_token,
                                                  http_method=http_method,
                                                  http_url=url, parameters=parameters)

      req.sign_request(self._signature_method_hmac_sha1, self._oauth_consumer, self._oauth_token)

      headers = req.to_header()

      if http_method == "POST":
        encoded_post_data = req.to_postdata()
      else:
        encoded_post_data = None
        url = req.to_url()
    else:
      url = self._BuildUrl(url, extra_params=extra_params)
      encoded_post_data = self._EncodePostData(post_data)

    # Open and return the URL immediately if we're not going to cache
    if encoded_post_data or no_cache or not self._cache or not self._cache_timeout:
      response = opener.open(url, encoded_post_data)
      url_data = self._DecompressGzippedResponse(response)
      opener.close()
    else:
      # Unique keys are a combination of the url and the oAuth Consumer Key
      if self._consumer_key:
        key = self._consumer_key + ':' + url
      else:
        key = url

      # See if it has been cached before
      last_cached = self._cache.GetCachedTime(key)

      # If the cached version is outdated then fetch another and store it
      if not last_cached or time.time() >= last_cached + self._cache_timeout:
        try:
          response = opener.open(url, encoded_post_data)
          url_data = self._DecompressGzippedResponse(response)
          self._cache.Set(key, url_data)
        except urllib2.HTTPError, e:
          print e
        opener.close()
      else:
        url_data = self._cache.Get(key)

    # Always return the latest version
    return url_data

class _FileCacheError(Exception):
  '''Base exception class for FileCache related errors'''

class _FileCache(object):

  DEPTH = 3

  def __init__(self,root_directory=None):
    self._InitializeRootDirectory(root_directory)

  def Get(self,key):
    path = self._GetPath(key)
    if os.path.exists(path):
      return open(path).read()
    else:
      return None

  def Set(self,key,data):
    path = self._GetPath(key)
    directory = os.path.dirname(path)
    if not os.path.exists(directory):
      os.makedirs(directory)
    if not os.path.isdir(directory):
      raise _FileCacheError('%s exists but is not a directory' % directory)
    temp_fd, temp_path = tempfile.mkstemp()
    temp_fp = os.fdopen(temp_fd, 'w')
    temp_fp.write(data)
    temp_fp.close()
    if not path.startswith(self._root_directory):
      raise _FileCacheError('%s does not appear to live under %s' %
                            (path, self._root_directory))
    if os.path.exists(path):
      os.remove(path)
    os.rename(temp_path, path)

  def Remove(self,key):
    path = self._GetPath(key)
    if not path.startswith(self._root_directory):
      raise _FileCacheError('%s does not appear to live under %s' %
                            (path, self._root_directory ))
    if os.path.exists(path):
      os.remove(path)

  def GetCachedTime(self,key):
    path = self._GetPath(key)
    if os.path.exists(path):
      return os.path.getmtime(path)
    else:
      return None

  def _GetUsername(self):
    '''Attempt to find the username in a cross-platform fashion.'''
    try:
      return os.getenv('USER') or \
             os.getenv('LOGNAME') or \
             os.getenv('USERNAME') or \
             os.getlogin() or \
             'nobody'
    except (AttributeError, IOError, OSError), e:
      return 'nobody'

  def _GetTmpCachePath(self):
    username = self._GetUsername()
    cache_directory = 'python.cache_' + username
    return os.path.join(tempfile.gettempdir(), cache_directory)

  def _InitializeRootDirectory(self, root_directory):
    if not root_directory:
      root_directory = self._GetTmpCachePath()
    root_directory = os.path.abspath(root_directory)
    if not os.path.exists(root_directory):
      os.mkdir(root_directory)
    if not os.path.isdir(root_directory):
      raise _FileCacheError('%s exists but is not a directory' %
                            root_directory)
    self._root_directory = root_directory

  def _GetPath(self,key):
    try:
        hashed_key = md5(key).hexdigest()
    except TypeError:
        hashed_key = md5.new(key).hexdigest()

    return os.path.join(self._root_directory,
                        self._GetPrefix(hashed_key),
                        hashed_key)

  def _GetPrefix(self,hashed_key):
    return os.path.sep.join(hashed_key[0:_FileCache.DEPTH])
