#!/usr/bin/env python
import errno
import os
import re
import tempfile

from hashlib import md5


class _FileCacheError(Exception):
    """Base exception class for FileCache related errors"""


class _FileCache(object):
    DEPTH = 3

    def __init__(self, root_directory=None):
        self._InitializeRootDirectory(root_directory)

    def Get(self, key):
        path = self._GetPath(key)
        if os.path.exists(path):
            with open(path) as f:
                return f.read()
        else:
            return None

    def Set(self, key, data):
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

    def Remove(self, key):
        path = self._GetPath(key)
        if not path.startswith(self._root_directory):
            raise _FileCacheError('%s does not appear to live under %s' %
                                  (path, self._root_directory ))
        if os.path.exists(path):
            os.remove(path)

    def GetCachedTime(self, key):
        path = self._GetPath(key)
        if os.path.exists(path):
            return os.path.getmtime(path)
        else:
            return None

    def _GetUsername(self):
        """Attempt to find the username in a cross-platform fashion."""
        try:
            return os.getenv('USER') or \
                   os.getenv('LOGNAME') or \
                   os.getenv('USERNAME') or \
                   os.getlogin() or \
                   'nobody'
        except (AttributeError, IOError, OSError):
            return 'nobody'

    def _GetTmpCachePath(self):
        username = self._GetUsername()
        cache_directory = 'python.cache_' + username
        return os.path.join(tempfile.gettempdir(), cache_directory)

    def _InitializeRootDirectory(self, root_directory):
        if not root_directory:
            root_directory = self._GetTmpCachePath()
        root_directory = os.path.abspath(root_directory)
        try:
            os.mkdir(root_directory)
        except OSError as e:
            if e.errno == errno.EEXIST and os.path.isdir(root_directory):
                # directory already exists
                pass
            else:
                # exists but is a file, or no permissions, or...
                raise
        self._root_directory = root_directory

    def _GetPath(self, key):
        try:
            hashed_key = md5(key.encode('utf-8')).hexdigest()
        except TypeError:
            hashed_key = md5.new(key).hexdigest()

        return os.path.join(self._root_directory,
                            self._GetPrefix(hashed_key),
                            hashed_key)

    def _GetPrefix(self, hashed_key):
        return os.path.sep.join(hashed_key[0:_FileCache.DEPTH])


class ParseTweet(object):
    # compile once on import
    regexp = {"RT": "^RT", "MT": r"^MT", "ALNUM": r"(@[a-zA-Z0-9_]+)",
              "HASHTAG": r"(#[\w\d]+)", "URL": r"([http://]?[a-zA-Z\d\/]+[\.]+[a-zA-Z\d\/\.]+)"}
    regexp = dict((key, re.compile(value)) for key, value in list(regexp.items()))

    def __init__(self, timeline_owner, tweet):
        """ timeline_owner : twitter handle of user account. tweet - 140 chars from feed; object does all computation on construction
            properties:
            RT, MT - boolean
            URLs - list of URL
            Hashtags - list of tags
        """
        self.Owner = timeline_owner
        self.tweet = tweet
        self.UserHandles = ParseTweet.getUserHandles(tweet)
        self.Hashtags = ParseTweet.getHashtags(tweet)
        self.URLs = ParseTweet.getURLs(tweet)
        self.RT = ParseTweet.getAttributeRT(tweet)
        self.MT = ParseTweet.getAttributeMT(tweet)

        # additional intelligence
        if ( self.RT and len(self.UserHandles) > 0 ):  # change the owner of tweet?
            self.Owner = self.UserHandles[0]
        return

    def __str__(self):
        """ for display method """
        return "owner %s, urls: %d, hashtags %d, user_handles %d, len_tweet %d, RT = %s, MT = %s" % (
                self.Owner, len(self.URLs), len(self.Hashtags), len(self.UserHandles),
                len(self.tweet), self.RT, self.MT)

    @staticmethod
    def getAttributeRT(tweet):
        """ see if tweet is a RT """
        return re.search(ParseTweet.regexp["RT"], tweet.strip()) is not None

    @staticmethod
    def getAttributeMT(tweet):
        """ see if tweet is a MT """
        return re.search(ParseTweet.regexp["MT"], tweet.strip()) is not None

    @staticmethod
    def getUserHandles(tweet):
        """ given a tweet we try and extract all user handles in order of occurrence"""
        return re.findall(ParseTweet.regexp["ALNUM"], tweet)

    @staticmethod
    def getHashtags(tweet):
        """ return all hashtags"""
        return re.findall(ParseTweet.regexp["HASHTAG"], tweet)

    @staticmethod
    def getURLs(tweet):
        """ URL : [http://]?[\w\.?/]+"""
        return re.findall(ParseTweet.regexp["URL"], tweet)
