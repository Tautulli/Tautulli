#!/usr/bin/env python
#
# PyGazelle - https://github.com/cohena/pygazelle
# A Python implementation of the What.cd Gazelle JSON API
#
# Loosely based on the API implementation from 'whatbetter', by Zachary Denton
# See https://github.com/zacharydenton/whatbetter
from HTMLParser import HTMLParser

import sys
import json
import time
import requests as requests

from .user import User
from .artist import Artist
from .tag import Tag
from .request import Request
from .torrent_group import TorrentGroup
from .torrent import Torrent
from .category import Category
from .inbox import Mailbox

class LoginException(Exception):
    pass

class RequestException(Exception):
    pass

class GazelleAPI(object):
    last_request = time.time() # share amongst all api objects
    default_headers = {
        'Connection': 'keep-alive',
        'Cache-Control': 'max-age=0',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_7_3)'\
                      'AppleWebKit/535.11 (KHTML, like Gecko) Chrome/17.0.963.79'\
                      'Safari/535.11',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9'\
                  ',*/*;q=0.8',
        'Accept-Encoding': 'gzip,deflate,sdch',
        'Accept-Language': 'en-US,en;q=0.8',
        'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3'}


    def __init__(self, username=None, password=None):
        self.session = requests.session()
        self.session.headers = self.default_headers
        self.username = username
        self.password = password
        self.authkey = None
        self.passkey = None
        self.userid = None
        self.logged_in_user = None
        self.default_timeout = 30
        self.cached_users = {}
        self.cached_artists = {}
        self.cached_tags = {}
        self.cached_torrent_groups = {}
        self.cached_torrents = {}
        self.cached_requests = {}
        self.cached_categories = {}
        self.site = "https://what.cd/"
        self.past_request_timestamps = []

    def wait_for_rate_limit(self):
        # maximum is 5 requests within 10 secs
        time_frame = 10
        max_reqs = 5

        slice_point = 0

        while len(self.past_request_timestamps) >= max_reqs:
            for i, timestamp in enumerate(self.past_request_timestamps):
                if timestamp < time.time() - time_frame:
                    slice_point = i + 1
                else:
                    break

            if slice_point:
                self.past_request_timestamps = self.past_request_timestamps[slice_point:]
            else:
                time.sleep(0.1)

    def logged_in(self):
        return self.logged_in_user is not None and self.logged_in_user.id == self.userid

    def _login(self):
        """
        Private method.
        Logs in user and gets authkey from server.
        """

        if self.logged_in():
            return

        self.wait_for_rate_limit()

        loginpage = 'https://what.cd/login.php'
        data = {'username': self.username,
                'password': self.password,
                'keeplogged': '1'}
        r = self.session.post(loginpage, data=data, timeout=self.default_timeout, headers=self.default_headers)
        self.past_request_timestamps.append(time.time())
        if r.status_code != 200:
            raise LoginException("Login returned status code %s" % r.status_code)

        try:
            accountinfo = self.request('index', autologin=False)
        except RequestException as e:
            raise LoginException("Login probably incorrect")
        if not accountinfo or 'id' not in accountinfo:
            raise LoginException("Login probably incorrect")
        self.userid = accountinfo['id']
        self.authkey = accountinfo['authkey']
        self.passkey = accountinfo['passkey']
        self.logged_in_user = User(self.userid, self)
        self.logged_in_user.set_index_data(accountinfo)

    def request(self, action, autologin=True, **kwargs):
        """
        Makes an AJAX request at a given action.
        Pass an action and relevant arguments for that action.
        """
        def make_request(action, **kwargs):
            ajaxpage = 'ajax.php'
            content = self.unparsed_request(ajaxpage, action, **kwargs)
            try:
                if not isinstance(content, text_type):
                    content = content.decode('utf-8')
                parsed = json.loads(content)
                if parsed['status'] != 'success':
                    raise RequestException
                return parsed['response']
            except ValueError:
                raise RequestException

        try:
            return make_request(action, **kwargs)
        except Exception as e:
            if autologin and not self.logged_in():
                self._login()
                return make_request(action, **kwargs)
            else:
                raise e

    def unparsed_request(self, sitepage, action, **kwargs):
        """
        Makes a generic HTTP request at a given page with a given action.
        Also pass relevant arguments for that action.
        """
        self.wait_for_rate_limit()

        url = "%s%s" % (self.site, sitepage)
        params = {'action': action}
        if self.authkey:
            params['auth'] = self.authkey
        params.update(kwargs)
        r = self.session.get(url, params=params, allow_redirects=False, timeout=self.default_timeout)

        if r.status_code == 302 and r.raw.headers['location'] == 'login.php':
            self.logged_in_user = None
            raise LoginException("User login expired")

        self.past_request_timestamps.append(time.time())
        return r.content

    def get_user(self, id):
        """
        Returns a User for the passed ID, associated with this API object. If the ID references the currently logged in
        user, the user returned will be pre-populated with the information from an 'index' API call. Otherwise, you'll
        need to call User.update_user_data(). This is done on demand to reduce unnecessary API calls.
        """
        id = int(id)
        if id == self.userid:
            return self.logged_in_user
        elif id in self.cached_users.keys():
            return self.cached_users[id]
        else:
            return User(id, self)

    def search_users(self, search_query):
        """
        Returns a list of users returned for the search query. You can search by name, part of name, and ID number. If
        one of the returned users is the currently logged-in user, that user object will be pre-populated with the
        information from an 'index' API call. Otherwise only the limited info returned by the search will be pre-pop'd.
        You can query more information with User.update_user_data(). This is done on demand to reduce unnecessary API calls.
        """
        response = self.request(action='usersearch', search=search_query)
        results = response['results']

        found_users = []
        for result in results:
            user = self.get_user(result['userId'])
            user.set_search_result_data(result)
            found_users.append(user)

        return found_users

    def get_inbox(self, page='1', sort='unread'):
        """
        Returns the inbox Mailbox for the logged in user
        """
        return Mailbox(self, 'inbox', page, sort)

    def get_sentbox(self, page='1', sort='unread'):
        """
        Returns the sentbox Mailbox for the logged in user
        """
        return Mailbox(self, 'sentbox', page, sort)

    def get_artist(self, id=None, name=None):
        """
        Returns an Artist for the passed ID, associated with this API object. You'll need to call Artist.update_data()
        if the artist hasn't already been cached. This is done on demand to reduce unnecessary API calls.
        """
        if id:
            id = int(id)
            if id in self.cached_artists.keys():
                artist = self.cached_artists[id]
            else:
                artist = Artist(id, self)
            if name:
                artist.name = HTMLParser().unescape(name)
        elif name:
            artist = Artist(-1, self)
            artist.name = HTMLParser().unescape(name)
        else:
            raise Exception("You must specify either an ID or a Name to get an artist.")

        return artist

    def get_tag(self, name):
        """
        Returns a Tag for the passed name, associated with this API object. If you know the count value for this tag,
        pass it to update the object. There is no way to query the count directly from the API, but it can be retrieved
        from other calls such as 'artist', however.
        """
        if name in self.cached_tags.keys():
            return self.cached_tags[name]
        else:
            return Tag(name, self)

    def get_request(self, id):
        """
        Returns a Request for the passed ID, associated with this API object. You'll need to call Request.update_data()
        if the request hasn't already been cached. This is done on demand to reduce unnecessary API calls.
        """
        id = int(id)
        if id in self.cached_requests.keys():
            return self.cached_requests[id]
        else:
            return Request(id, self)

    def get_torrent_group(self, id):
        """
        Returns a TorrentGroup for the passed ID, associated with this API object.
        """
        id = int(id)
        if id in self.cached_torrent_groups.keys():
            return self.cached_torrent_groups[id]
        else:
            return TorrentGroup(id, self)

    def get_torrent(self, id):
        """
        Returns a Torrent for the passed ID, associated with this API object.
        """
        id = int(id)
        if id in self.cached_torrents.keys():
            return self.cached_torrents[id]
        else:
            return Torrent(id, self)

    def get_torrent_from_info_hash(self, info_hash):
        """
        Returns a Torrent for the passed info hash (if one exists), associated with this API object.
        """
        try:
            response = self.request(action='torrent', hash=info_hash.upper())
        except RequestException:
            return None

        id = int(response['torrent']['id'])
        if id in self.cached_torrents.keys():
            torrent = self.cached_torrents[id]
        else:
            torrent = Torrent(id, self)

        torrent.set_torrent_complete_data(response)
        return torrent

    def get_category(self, id, name=None):
        """
        Returns a Category for the passed ID, associated with this API object.
        """
        id = int(id)
        if id in self.cached_categories.keys():
            cat = self.cached_categories[id]
        else:
            cat = Category(id, self)
        if name:
            cat.name = name
        return cat

    def get_top_10(self, type="torrents", limit=25):
        """
        Lists the top <limit> items of <type>. Type can be "torrents", "tags", or "users". Limit MUST be
        10, 25, or 100...it can't just be an arbitrary number (unfortunately). Results are organized into a list of hashes.
        Each hash contains the results for a specific time frame, like 'day', or 'week'. In the hash, the 'results' key
        contains a list of objects appropriate to the passed <type>.
        """

        response = self.request(action='top10', type=type, limit=limit)
        top_items = []
        if not response:
            raise RequestException
        for category in response:
            results = []
            if type == "torrents":
                for item in category['results']:
                    torrent = self.get_torrent(item['torrentId'])
                    torrent.set_torrent_top_10_data(item)
                    results.append(torrent)
            elif type == "tags":
                for item in category['results']:
                    tag = self.get_tag(item['name'])
                    results.append(tag)
            elif type == "users":
                for item in category['results']:
                    user = self.get_user(item['id'])
                    results.append(user)
            else:
                raise Exception("%s is an invalid type argument for GazelleAPI.get_top_ten()" % type)

            top_items.append({
                "caption": category['caption'],
                "tag": category['tag'],
                "limit": category['limit'],
                "results": results
            })

        return top_items

    def search_torrents(self, **kwargs):
        """
        Searches based on the args you pass and returns torrent groups filled with torrents.
        Pass strings unless otherwise specified.
        Valid search args:
            searchstr (any arbitrary string to search for)
            page (page to display -- default: 1)
            artistname (self explanatory)
            groupname (torrent group name, equivalent to album)
            recordlabel (self explanatory)
            cataloguenumber (self explanatory)
            year (self explanatory)
            remastertitle (self explanatory)
            remasteryear (self explanatory)
            remasterrecordlabel (self explanatory)
            remastercataloguenumber (self explanatory)
            filelist (can search for filenames found in torrent...unsure of formatting for multiple files)
            encoding (use constants in pygazelle.Encoding module)
            format (use constants in pygazelle.Format module)
            media (use constants in pygazelle.Media module)
            releasetype (use constants in pygazelle.ReleaseType module)
            haslog (int 1 or 0 to represent boolean, 100 for 100% only, -1 for < 100% / unscored)
            hascue (int 1 or 0 to represent boolean)
            scene (int 1 or 0 to represent boolean)
            vanityhouse (int 1 or 0 to represent boolean)
            freetorrent (int 1 or 0 to represent boolean)
            taglist (comma separated tag names)
            tags_type (0 for 'any' matching, 1 for 'all' matching)
            order_by (use constants in pygazelle.order module that start with by_ in their name)
            order_way (use way_ascending or way_descending constants in pygazelle.order)
            filter_cat (for each category you want to search, the param name must be filter_cat[catnum] and the value 1)
                        ex. filter_cat[1]=1 turns on Music.
                        filter_cat[1]=1, filter_cat[2]=1 turns on music and applications. (two separate params and vals!)
                        Category object ids return the correct int value for these. (verify?)

        Returns a dict containing keys 'curr_page', 'pages', and 'results'. Results contains a matching list of Torrents
        (they have a reference to their parent TorrentGroup).
        """

        response = self.request(action='browse', **kwargs)
        results = response['results']
        if len(results):
            curr_page = response['currentPage']
            pages = response['pages']
        else:
            curr_page = 1
            pages = 1

        matching_torrents = []
        for torrent_group_dict in results:
            torrent_group = self.get_torrent_group(torrent_group_dict['groupId'])
            torrent_group.set_torrent_search_data(torrent_group_dict)

            for torrent_dict in torrent_group_dict['torrents']:
                torrent_dict['groupId'] = torrent_group.id
                torrent = self.get_torrent(torrent_dict['torrentId'])
                torrent.set_torrent_search_data(torrent_dict)
                matching_torrents.append(torrent)

        return {'curr_page': curr_page, 'pages': pages, 'results': matching_torrents}

    def generate_torrent_link(self, id):
        url = "%storrents.php?action=download&id=%s&authkey=%s&torrent_pass=%s" %\
              (self.site, id, self.logged_in_user.authkey, self.logged_in_user.passkey)
        return url

    def save_torrent_file(self, id, dest):
        file_data = self.unparsed_request("torrents.php", 'download',
            id=id, authkey=self.logged_in_user.authkey, torrent_pass=self.logged_in_user.passkey)
        with open(dest, 'w+') as dest_file:
            dest_file.write(file_data)

if sys.version_info[0] == 3:
    text_type = str
else:
    text_type = unicode
