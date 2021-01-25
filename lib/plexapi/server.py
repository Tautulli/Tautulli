# -*- coding: utf-8 -*-
from urllib.parse import urlencode
from xml.etree import ElementTree

import requests
from plexapi import (BASE_HEADERS, CONFIG, TIMEOUT, X_PLEX_CONTAINER_SIZE, log,
                     logfilter)
from plexapi import utils
from plexapi.alert import AlertListener
from plexapi.base import PlexObject
from plexapi.client import PlexClient
from plexapi.exceptions import BadRequest, NotFound, Unauthorized
from plexapi.library import Hub, Library, Path, File
from plexapi.media import Conversion, Optimized
from plexapi.playlist import Playlist
from plexapi.playqueue import PlayQueue
from plexapi.settings import Settings
from plexapi.utils import cast
from requests.status_codes import _codes as codes

# Need these imports to populate utils.PLEXOBJECTS
from plexapi import audio as _audio  # noqa: F401; noqa: F401
from plexapi import media as _media  # noqa: F401
from plexapi import photo as _photo  # noqa: F401
from plexapi import playlist as _playlist  # noqa: F401
from plexapi import video as _video  # noqa: F401


class PlexServer(PlexObject):
    """ This is the main entry point to interacting with a Plex server. It allows you to
        list connected clients, browse your library sections and perform actions such as
        emptying trash. If you do not know the auth token required to access your Plex
        server, or simply want to access your server with your username and password, you
        can also create an PlexServer instance from :class:`~plexapi.myplex.MyPlexAccount`.

        Parameters:
            baseurl (str): Base url for to access the Plex Media Server (default: 'http://localhost:32400').
            token (str): Required Plex authentication token to access the server.
            session (requests.Session, optional): Use your own session object if you want to
                cache the http responses from PMS
            timeout (int): timeout in seconds on initial connect to server (default config.TIMEOUT).

        Attributes:
            allowCameraUpload (bool): True if server allows camera upload.
            allowChannelAccess (bool): True if server allows channel access (iTunes?).
            allowMediaDeletion (bool): True is server allows media to be deleted.
            allowSharing (bool): True is server allows sharing.
            allowSync (bool): True is server allows sync.
            backgroundProcessing (bool): Unknown
            certificate (bool): True if server has an HTTPS certificate.
            companionProxy (bool): Unknown
            diagnostics (bool): Unknown
            eventStream (bool): Unknown
            friendlyName (str): Human friendly name for this server.
            hubSearch (bool): True if `Hub Search <https://www.plex.tv/blog
                /seek-plex-shall-find-leveling-web-app/>`_ is enabled. I believe this
                is enabled for everyone
            machineIdentifier (str): Unique ID for this server (looks like an md5).
            multiuser (bool): True if `multiusers <https://support.plex.tv/hc/en-us/articles
                /200250367-Multi-User-Support>`_ are enabled.
            myPlex (bool): Unknown (True if logged into myPlex?).
            myPlexMappingState (str): Unknown (ex: mapped).
            myPlexSigninState (str): Unknown (ex: ok).
            myPlexSubscription (bool): True if you have a myPlex subscription.
            myPlexUsername (str): Email address if signed into myPlex (user@example.com)
            ownerFeatures (list): List of features allowed by the server owner. This may be based
                on your PlexPass subscription. Features include: camera_upload, cloudsync,
                content_filter, dvr, hardware_transcoding, home, lyrics, music_videos, pass,
                photo_autotags, premium_music_metadata, session_bandwidth_restrictions, sync,
                trailers, webhooks (and maybe more).
            photoAutoTag (bool): True if photo `auto-tagging <https://support.plex.tv/hc/en-us
                /articles/234976627-Auto-Tagging-of-Photos>`_ is enabled.
            platform (str): Platform the server is hosted on (ex: Linux)
            platformVersion (str): Platform version (ex: '6.1 (Build 7601)', '4.4.0-59-generic').
            pluginHost (bool): Unknown
            readOnlyLibraries (bool): Unknown
            requestParametersInCookie (bool): Unknown
            streamingBrainVersion (bool): Current `Streaming Brain <https://www.plex.tv/blog
                /mcstreamy-brain-take-world-two-easy-steps/>`_ version.
            sync (bool): True if `syncing to a device <https://support.plex.tv/hc/en-us/articles
                /201053678-Sync-Media-to-a-Device>`_ is enabled.
            transcoderActiveVideoSessions (int): Number of active video transcoding sessions.
            transcoderAudio (bool): True if audio transcoding audio is available.
            transcoderLyrics (bool): True if audio transcoding lyrics is available.
            transcoderPhoto (bool): True if audio transcoding photos is available.
            transcoderSubtitles (bool): True if audio transcoding subtitles is available.
            transcoderVideo (bool): True if audio transcoding video is available.
            transcoderVideoBitrates (bool): List of video bitrates.
            transcoderVideoQualities (bool): List of video qualities.
            transcoderVideoResolutions (bool): List of video resolutions.
            updatedAt (int): Datetime the server was updated.
            updater (bool): Unknown
            version (str): Current Plex version (ex: 1.3.2.3112-1751929)
            voiceSearch (bool): True if voice search is enabled. (is this Google Voice search?)
            _baseurl (str): HTTP address of the client.
            _token (str): Token used to access this client.
            _session (obj): Requests session object used to access this client.
    """
    key = '/'

    def __init__(self, baseurl=None, token=None, session=None, timeout=None):
        self._baseurl = baseurl or CONFIG.get('auth.server_baseurl', 'http://localhost:32400')
        self._baseurl = self._baseurl.rstrip('/')
        self._token = logfilter.add_secret(token or CONFIG.get('auth.server_token'))
        self._showSecrets = CONFIG.get('log.show_secrets', '').lower() == 'true'
        self._session = session or requests.Session()
        self._library = None   # cached library
        self._settings = None   # cached settings
        self._myPlexAccount = None   # cached myPlexAccount
        self._systemAccounts = None   # cached list of SystemAccount
        self._systemDevices = None   # cached list of SystemDevice
        data = self.query(self.key, timeout=timeout)
        super(PlexServer, self).__init__(self, data, self.key)

    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        self._data = data
        self.allowCameraUpload = cast(bool, data.attrib.get('allowCameraUpload'))
        self.allowChannelAccess = cast(bool, data.attrib.get('allowChannelAccess'))
        self.allowMediaDeletion = cast(bool, data.attrib.get('allowMediaDeletion'))
        self.allowSharing = cast(bool, data.attrib.get('allowSharing'))
        self.allowSync = cast(bool, data.attrib.get('allowSync'))
        self.backgroundProcessing = cast(bool, data.attrib.get('backgroundProcessing'))
        self.certificate = cast(bool, data.attrib.get('certificate'))
        self.companionProxy = cast(bool, data.attrib.get('companionProxy'))
        self.diagnostics = utils.toList(data.attrib.get('diagnostics'))
        self.eventStream = cast(bool, data.attrib.get('eventStream'))
        self.friendlyName = data.attrib.get('friendlyName')
        self.hubSearch = cast(bool, data.attrib.get('hubSearch'))
        self.machineIdentifier = data.attrib.get('machineIdentifier')
        self.multiuser = cast(bool, data.attrib.get('multiuser'))
        self.myPlex = cast(bool, data.attrib.get('myPlex'))
        self.myPlexMappingState = data.attrib.get('myPlexMappingState')
        self.myPlexSigninState = data.attrib.get('myPlexSigninState')
        self.myPlexSubscription = cast(bool, data.attrib.get('myPlexSubscription'))
        self.myPlexUsername = data.attrib.get('myPlexUsername')
        self.ownerFeatures = utils.toList(data.attrib.get('ownerFeatures'))
        self.photoAutoTag = cast(bool, data.attrib.get('photoAutoTag'))
        self.platform = data.attrib.get('platform')
        self.platformVersion = data.attrib.get('platformVersion')
        self.pluginHost = cast(bool, data.attrib.get('pluginHost'))
        self.readOnlyLibraries = cast(int, data.attrib.get('readOnlyLibraries'))
        self.requestParametersInCookie = cast(bool, data.attrib.get('requestParametersInCookie'))
        self.streamingBrainVersion = data.attrib.get('streamingBrainVersion')
        self.sync = cast(bool, data.attrib.get('sync'))
        self.transcoderActiveVideoSessions = int(data.attrib.get('transcoderActiveVideoSessions', 0))
        self.transcoderAudio = cast(bool, data.attrib.get('transcoderAudio'))
        self.transcoderLyrics = cast(bool, data.attrib.get('transcoderLyrics'))
        self.transcoderPhoto = cast(bool, data.attrib.get('transcoderPhoto'))
        self.transcoderSubtitles = cast(bool, data.attrib.get('transcoderSubtitles'))
        self.transcoderVideo = cast(bool, data.attrib.get('transcoderVideo'))
        self.transcoderVideoBitrates = utils.toList(data.attrib.get('transcoderVideoBitrates'))
        self.transcoderVideoQualities = utils.toList(data.attrib.get('transcoderVideoQualities'))
        self.transcoderVideoResolutions = utils.toList(data.attrib.get('transcoderVideoResolutions'))
        self.updatedAt = utils.toDatetime(data.attrib.get('updatedAt'))
        self.updater = cast(bool, data.attrib.get('updater'))
        self.version = data.attrib.get('version')
        self.voiceSearch = cast(bool, data.attrib.get('voiceSearch'))

    def _headers(self, **kwargs):
        """ Returns dict containing base headers for all requests to the server. """
        headers = BASE_HEADERS.copy()
        if self._token:
            headers['X-Plex-Token'] = self._token
        headers.update(kwargs)
        return headers

    @property
    def library(self):
        """ Library to browse or search your media. """
        if not self._library:
            try:
                data = self.query(Library.key)
                self._library = Library(self, data)
            except BadRequest:
                data = self.query('/library/sections/')
                # Only the owner has access to /library
                # so just return the library without the data.
                return Library(self, data)
        return self._library

    @property
    def settings(self):
        """ Returns a list of all server settings. """
        if not self._settings:
            data = self.query(Settings.key)
            self._settings = Settings(self, data)
        return self._settings

    def account(self):
        """ Returns the :class:`~plexapi.server.Account` object this server belongs to. """
        data = self.query(Account.key)
        return Account(self, data)

    @property
    def activities(self):
        """Returns all current PMS activities."""
        activities = []
        for elem in self.query(Activity.key):
            activities.append(Activity(self, elem))
        return activities

    def agents(self, mediaType=None):
        """ Returns the :class:`~plexapi.media.Agent` objects this server has available. """
        key = '/system/agents'
        if mediaType:
            key += '?mediaType=%s' % mediaType
        return self.fetchItems(key)

    def createToken(self, type='delegation', scope='all'):
        """Create a temp access token for the server."""
        if not self._token:
            # Handle unclaimed servers
            return None
        q = self.query('/security/token?type=%s&scope=%s' % (type, scope))
        return q.attrib.get('token')

    def systemAccounts(self):
        """ Returns a list of :class:`~plexapi.server.SystemAccounts` objects this server contains. """
        if self._systemAccounts is None:
            key = '/accounts'
            self._systemAccounts = self.fetchItems(key, SystemAccount)
        return self._systemAccounts

    def systemDevices(self):
        """ Returns a list of :class:`~plexapi.server.SystemDevices` objects this server contains. """
        if self._systemDevices is None:
            key = '/devices'
            self._systemDevices = self.fetchItems(key, SystemDevice)
        return self._systemDevices

    def myPlexAccount(self):
        """ Returns a :class:`~plexapi.myplex.MyPlexAccount` object using the same
            token to access this server. If you are not the owner of this PlexServer
            you're likley to recieve an authentication error calling this.
        """
        if self._myPlexAccount is None:
            from plexapi.myplex import MyPlexAccount
            self._myPlexAccount = MyPlexAccount(token=self._token)
        return self._myPlexAccount

    def _myPlexClientPorts(self):
        """ Sometimes the PlexServer does not properly advertise port numbers required
            to connect. This attemps to look up device port number from plex.tv.
            See issue #126: Make PlexServer.clients() more user friendly.
              https://github.com/pkkid/python-plexapi/issues/126
        """
        try:
            ports = {}
            account = self.myPlexAccount()
            for device in account.devices():
                if device.connections and ':' in device.connections[0][6:]:
                    ports[device.clientIdentifier] = device.connections[0].split(':')[-1]
            return ports
        except Exception as err:
            log.warning('Unable to fetch client ports from myPlex: %s', err)
            return ports

    def browse(self, path=None, includeFiles=True):
        """ Browse the system file path using the Plex API.
            Returns list of :class:`~plexapi.library.Path` and :class:`~plexapi.library.File` objects.

            Parameters:
                path (:class:`~plexapi.library.Path` or str, optional): Full path to browse.
                includeFiles (bool): True to include files when browsing (Default).
                                     False to only return folders.
        """
        if isinstance(path, Path):
            key = path.key
        elif path is not None:
            base64path = utils.base64str(path)
            key = '/services/browse/%s' % base64path
        else:
            key = '/services/browse'
        if includeFiles:
            key += '?includeFiles=1'
        return self.fetchItems(key)

    def walk(self, path=None):
        """ Walk the system file tree using the Plex API similar to `os.walk`.
            Yields a 3-tuple `(path, paths, files)` where
            `path` is a string of the directory path,
            `paths` is a list of :class:`~plexapi.library.Path` objects, and
            `files` is a list of :class:`~plexapi.library.File` objects.

            Parameters:
                path (:class:`~plexapi.library.Path` or str, optional): Full path to walk.
        """
        paths = []
        files = []
        for item in self.browse(path):
            if isinstance(item, Path):
                paths.append(item)
            elif isinstance(item, File):
                files.append(item)

        if isinstance(path, Path):
            path = path.path

        yield path or '', paths, files

        for _path in paths:
            for path, paths, files in self.walk(_path):
                yield path, paths, files

    def clients(self):
        """ Returns list of all :class:`~plexapi.client.PlexClient` objects connected to server. """
        items = []
        ports = None
        for elem in self.query('/clients'):
            port = elem.attrib.get('port')
            if not port:
                log.warning('%s did not advertise a port, checking plex.tv.', elem.attrib.get('name'))
                ports = self._myPlexClientPorts() if ports is None else ports
                port = ports.get(elem.attrib.get('machineIdentifier'))
            baseurl = 'http://%s:%s' % (elem.attrib['host'], port)
            items.append(PlexClient(baseurl=baseurl, server=self,
                                    token=self._token, data=elem, connect=False))

        return items

    def client(self, name):
        """ Returns the :class:`~plexapi.client.PlexClient` that matches the specified name.

            Parameters:
                name (str): Name of the client to return.

            Raises:
                :exc:`~plexapi.exceptions.NotFound`: Unknown client name.
        """
        for client in self.clients():
            if client and client.title == name:
                return client

        raise NotFound('Unknown client name: %s' % name)

    def createPlaylist(self, title, items=None, section=None, limit=None, smart=None, **kwargs):
        """ Creates and returns a new :class:`~plexapi.playlist.Playlist`.

            Parameters:
                title (str): Title of the playlist to be created.
                items (list<Media>): List of media items to include in the playlist.
        """
        return Playlist.create(self, title, items=items, limit=limit, section=section, smart=smart, **kwargs)

    def createPlayQueue(self, item, **kwargs):
        """ Creates and returns a new :class:`~plexapi.playqueue.PlayQueue`.

            Parameters:
                item (Media or Playlist): Media or playlist to add to PlayQueue.
                kwargs (dict): See `~plexapi.playqueue.PlayQueue.create`.
        """
        return PlayQueue.create(self, item, **kwargs)

    def downloadDatabases(self, savepath=None, unpack=False):
        """ Download databases.

            Parameters:
                savepath (str): Defaults to current working dir.
                unpack (bool): Unpack the zip file.
        """
        url = self.url('/diagnostics/databases')
        filepath = utils.download(url, self._token, None, savepath, self._session, unpack=unpack)
        return filepath

    def downloadLogs(self, savepath=None, unpack=False):
        """ Download server logs.

            Parameters:
                savepath (str): Defaults to current working dir.
                unpack (bool): Unpack the zip file.
        """
        url = self.url('/diagnostics/logs')
        filepath = utils.download(url, self._token, None, savepath, self._session, unpack=unpack)
        return filepath

    def check_for_update(self, force=True, download=False):
        """ Returns a :class:`~plexapi.base.Release` object containing release info.

           Parameters:
                force (bool): Force server to check for new releases
                download (bool): Download if a update is available.
        """
        part = '/updater/check?download=%s' % (1 if download else 0)
        if force:
            self.query(part, method=self._session.put)
        releases = self.fetchItems('/updater/status')
        if len(releases):
            return releases[0]

    def isLatest(self):
        """ Check if the installed version of PMS is the latest. """
        release = self.check_for_update(force=True)
        return release is None

    def installUpdate(self):
        """ Install the newest version of Plex Media Server. """
        # We can add this but dunno how useful this is since it sometimes
        # requires user action using a gui.
        part = '/updater/apply'
        release = self.check_for_update(force=True, download=True)
        if release and release.version != self.version:
            # figure out what method this is..
            return self.query(part, method=self._session.put)

    def history(self, maxresults=9999999, mindate=None, ratingKey=None, accountID=None, librarySectionID=None):
        """ Returns a list of media items from watched history. If there are many results, they will
            be fetched from the server in batches of X_PLEX_CONTAINER_SIZE amounts. If you're only
            looking for the first <num> results, it would be wise to set the maxresults option to that
            amount so this functions doesn't iterate over all results on the server.

            Parameters:
                maxresults (int): Only return the specified number of results (optional).
                mindate (datetime): Min datetime to return results from. This really helps speed
                    up the result listing. For example: datetime.now() - timedelta(days=7)
                ratingKey (int/str) Request history for a specific ratingKey item.
                accountID (int/str) Request history for a specific account ID.
                librarySectionID (int/str) Request history for a specific library section ID.
        """
        results, subresults = [], '_init'
        args = {'sort': 'viewedAt:desc'}
        if ratingKey:
            args['metadataItemID'] = ratingKey
        if accountID:
            args['accountID'] = accountID
        if librarySectionID:
            args['librarySectionID'] = librarySectionID
        if mindate:
            args['viewedAt>'] = int(mindate.timestamp())
        args['X-Plex-Container-Start'] = 0
        args['X-Plex-Container-Size'] = min(X_PLEX_CONTAINER_SIZE, maxresults)
        while subresults and maxresults > len(results):
            key = '/status/sessions/history/all%s' % utils.joinArgs(args)
            subresults = self.fetchItems(key)
            results += subresults[:maxresults - len(results)]
            args['X-Plex-Container-Start'] += args['X-Plex-Container-Size']
        return results

    def playlists(self):
        """ Returns a list of all :class:`~plexapi.playlist.Playlist` objects saved on the server. """
        # TODO: Add sort and type options?
        # /playlists/all?type=15&sort=titleSort%3Aasc&playlistType=video&smart=0
        return self.fetchItems('/playlists')

    def playlist(self, title):
        """ Returns the :class:`~plexapi.client.Playlist` that matches the specified title.

            Parameters:
                title (str): Title of the playlist to return.

            Raises:
                :exc:`~plexapi.exceptions.NotFound`: Invalid playlist title.
        """
        return self.fetchItem('/playlists', title=title)

    def optimizedItems(self, removeAll=None):
        """ Returns list of all :class:`~plexapi.media.Optimized` objects connected to server. """
        if removeAll is True:
            key = '/playlists/generators?type=42'
            self.query(key, method=self._server._session.delete)
        else:
            backgroundProcessing = self.fetchItem('/playlists?type=42')
            return self.fetchItems('%s/items' % backgroundProcessing.key, cls=Optimized)

    def optimizedItem(self, optimizedID):
        """ Returns single queued optimized item :class:`~plexapi.media.Video` object.
            Allows for using optimized item ID to connect back to source item.
        """

        backgroundProcessing = self.fetchItem('/playlists?type=42')
        return self.fetchItem('%s/items/%s/items' % (backgroundProcessing.key, optimizedID))

    def conversions(self, pause=None):
        """ Returns list of all :class:`~plexapi.media.Conversion` objects connected to server. """
        if pause is True:
            self.query('/:/prefs?BackgroundQueueIdlePaused=1', method=self._server._session.put)
        elif pause is False:
            self.query('/:/prefs?BackgroundQueueIdlePaused=0', method=self._server._session.put)
        else:
            return self.fetchItems('/playQueues/1', cls=Conversion)

    def currentBackgroundProcess(self):
        """ Returns list of all :class:`~plexapi.media.TranscodeJob` objects running or paused on server. """
        return self.fetchItems('/status/sessions/background')

    def query(self, key, method=None, headers=None, timeout=None, **kwargs):
        """ Main method used to handle HTTPS requests to the Plex server. This method helps
            by encoding the response to utf-8 and parsing the returned XML into and
            ElementTree object. Returns None if no data exists in the response.
        """
        url = self.url(key)
        method = method or self._session.get
        timeout = timeout or TIMEOUT
        log.debug('%s %s', method.__name__.upper(), url)
        headers = self._headers(**headers or {})
        response = method(url, headers=headers, timeout=timeout, **kwargs)
        if response.status_code not in (200, 201, 204):
            codename = codes.get(response.status_code)[0]
            errtext = response.text.replace('\n', ' ')
            message = '(%s) %s; %s %s' % (response.status_code, codename, response.url, errtext)
            if response.status_code == 401:
                raise Unauthorized(message)
            elif response.status_code == 404:
                raise NotFound(message)
            else:
                raise BadRequest(message)
        data = response.text.encode('utf8')
        return ElementTree.fromstring(data) if data.strip() else None

    def search(self, query, mediatype=None, limit=None):
        """ Returns a list of media items or filter categories from the resulting
            `Hub Search <https://www.plex.tv/blog/seek-plex-shall-find-leveling-web-app/>`_
            against all items in your Plex library. This searches genres, actors, directors,
            playlists, as well as all the obvious media titles. It performs spell-checking
            against your search terms (because KUROSAWA is hard to spell). It also provides
            contextual search results. So for example, if you search for 'Pernice', it’ll
            return 'Pernice Brothers' as the artist result, but we’ll also go ahead and
            return your most-listened to albums and tracks from the artist. If you type
            'Arnold' you’ll get a result for the actor, but also the most recently added
            movies he’s in.

            Parameters:
                query (str): Query to use when searching your library.
                mediatype (str): Optionally limit your search to the specified media type.
                    actor, album, artist, autotag, collection, director, episode, game, genre,
                    movie, photo, photoalbum, place, playlist, shared, show, tag, track
                limit (int): Optionally limit to the specified number of results per Hub.
        """
        results = []
        params = {
            'query': query,
            'includeCollections': 1,
            'includeExternalMedia': 1}
        if limit:
            params['limit'] = limit
        key = '/hubs/search?%s' % urlencode(params)
        for hub in self.fetchItems(key, Hub):
            if mediatype:
                if hub.type == mediatype:
                    return hub.items
            else:
                results += hub.items
        return results

    def sessions(self):
        """ Returns a list of all active session (currently playing) media objects. """
        return self.fetchItems('/status/sessions')

    def transcodeSessions(self):
        """ Returns a list of all active :class:`~plexapi.media.TranscodeSession` objects. """
        return self.fetchItems('/transcode/sessions')

    def startAlertListener(self, callback=None):
        """ Creates a websocket connection to the Plex Server to optionally recieve
            notifications. These often include messages from Plex about media scans
            as well as updates to currently running Transcode Sessions.

            NOTE: You need websocket-client installed in order to use this feature.
            >> pip install websocket-client

            Parameters:
                callback (func): Callback function to call on recieved messages.

            Raises:
                :exc:`~plexapi.exception.Unsupported`: Websocket-client not installed.
        """
        notifier = AlertListener(self, callback)
        notifier.start()
        return notifier

    def transcodeImage(self, media, height, width, opacity=100, saturation=100):
        """ Returns the URL for a transcoded image from the specified media object.
            Returns None if no media specified (needed if user tries to pass thumb
            or art directly).

            Parameters:
                height (int): Height to transcode the image to.
                width (int): Width to transcode the image to.
                opacity (int): Opacity of the resulting image (possibly deprecated).
                saturation (int): Saturating of the resulting image.
        """
        if media:
            transcode_url = '/photo/:/transcode?height=%s&width=%s&opacity=%s&saturation=%s&url=%s' % (
                height, width, opacity, saturation, media)
            return self.url(transcode_url, includeToken=True)

    def url(self, key, includeToken=None):
        """ Build a URL string with proper token argument.  Token will be appended to the URL
            if either includeToken is True or CONFIG.log.show_secrets is 'true'.
        """
        if self._token and (includeToken or self._showSecrets):
            delim = '&' if '?' in key else '?'
            return '%s%s%sX-Plex-Token=%s' % (self._baseurl, key, delim, self._token)
        return '%s%s' % (self._baseurl, key)

    def refreshSynclist(self):
        """ Force PMS to download new SyncList from Plex.tv. """
        return self.query('/sync/refreshSynclists', self._session.put)

    def refreshContent(self):
        """ Force PMS to refresh content for known SyncLists. """
        return self.query('/sync/refreshContent', self._session.put)

    def refreshSync(self):
        """ Calls :func:`~plexapi.server.PlexServer.refreshSynclist` and
            :func:`~plexapi.server.PlexServer.refreshContent`, just like the Plex Web UI does when you click 'refresh'.
        """
        self.refreshSynclist()
        self.refreshContent()

    def _allowMediaDeletion(self, toggle=False):
        """ Toggle allowMediaDeletion.
            Parameters:
                toggle (bool): True enables Media Deletion
                               False or None disable Media Deletion (Default)
        """
        if self.allowMediaDeletion and toggle is False:
            log.debug('Plex is currently allowed to delete media. Toggling off.')
        elif self.allowMediaDeletion and toggle is True:
            log.debug('Plex is currently allowed to delete media. Toggle set to allow, exiting.')
            raise BadRequest('Plex is currently allowed to delete media. Toggle set to allow, exiting.')
        elif self.allowMediaDeletion is None and toggle is True:
            log.debug('Plex is currently not allowed to delete media. Toggle set to allow.')
        else:
            log.debug('Plex is currently not allowed to delete media. Toggle set to not allow, exiting.')
            raise BadRequest('Plex is currently not allowed to delete media. Toggle set to not allow, exiting.')
        value = 1 if toggle is True else 0
        return self.query('/:/prefs?allowMediaDeletion=%s' % value, self._session.put)

    def bandwidth(self, timespan=None, **kwargs):
        """ Returns a list of :class:`~plexapi.server.StatisticsBandwidth` objects
            with the Plex server dashboard bandwidth data.

            Parameters:
                timespan (str, optional): The timespan to bin the bandwidth data. Default is seconds.
                    Available timespans: seconds, hours, days, weeks, months.
                **kwargs (dict, optional): Any of the available filters that can be applied to the bandwidth data.
                    The time frame (at) and bytes can also be filtered using less than or greater than (see examples below).

                    * accountID (int): The :class:`~plexapi.server.SystemAccount` ID to filter.
                    * at (datetime): The time frame to filter (inclusive). The time frame can be either:
                        1. An exact time frame (e.g. Only December 1st 2020 `at=datetime(2020, 12, 1)`).
                        2. Before a specific time (e.g. Before and including December 2020 `at<=datetime(2020, 12, 1)`).
                        3. After a specific time (e.g. After and including January 2021 `at>=datetime(2021, 1, 1)`).
                    * bytes (int): The amount of bytes to filter (inclusive). The bytes can be either:
                        1. An exact number of bytes (not very useful) (e.g. `bytes=1024**3`).
                        2. Less than or equal number of bytes (e.g. `bytes<=1024**3`).
                        3. Greater than or equal number of bytes (e.g. `bytes>=1024**3`).
                    * deviceID (int): The :class:`~plexapi.server.SystemDevice` ID to filter.
                    * lan (bool): True to only retrieve local bandwidth, False to only retrieve remote bandwidth.
                        Default returns all local and remote bandwidth.

            Raises:
                :exc:`~plexapi.exceptions.BadRequest`: When applying an invalid timespan or unknown filter.

            Example:

                .. code-block:: python

                    from plexapi.server import PlexServer
                    plex = PlexServer('http://localhost:32400', token='xxxxxxxxxxxxxxxxxxxx')

                    # Filter bandwidth data for December 2020 and later, and more than 1 GB used.
                    filters = {
                        'at>': datetime(2020, 12, 1),
                        'bytes>': 1024**3
                    }

                    # Retrieve bandwidth data in one day timespans.
                    bandwidthData = plex.bandwidth(timespan='days', **filters)

                    # Print out bandwidth usage for each account and device combination.
                    for bandwidth in sorted(bandwidthData, key=lambda x: x.at):
                        account = bandwidth.account()
                        device = bandwidth.device()
                        gigabytes = round(bandwidth.bytes / 1024**3, 3)
                        local = 'local' if bandwidth.lan else 'remote'
                        date = bandwidth.at.strftime('%Y-%m-%d')
                        print('%s used %s GB of %s bandwidth on %s from %s'
                              % (account.name, gigabytes, local, date, device.name))

        """
        params = {}

        if timespan is None:
            params['timespan'] = 6  # Default to seconds
        else:
            timespans = {
                'seconds': 6,
                'hours': 4,
                'days': 3,
                'weeks': 2,
                'months': 1
            }
            try:
                params['timespan'] = timespans[timespan]
            except KeyError:
                raise BadRequest('Invalid timespan specified: %s. '
                    'Available timespans: %s' % (timespan, ', '.join(timespans.keys())))

        filters = {'accountID', 'at', 'at<', 'at>', 'bytes', 'bytes<', 'bytes>', 'deviceID', 'lan'}

        for key, value in kwargs.items():
            if key not in filters:
                raise BadRequest('Unknown filter: %s=%s' % (key, value))
            if key.startswith('at'):
                try:
                    value = cast(int, value.timestamp())
                except AttributeError:
                    raise BadRequest('Time frame filter must be a datetime object: %s=%s' % (key, value))
            elif key.startswith('bytes') or key == 'lan':
                value = cast(int, value)
            elif key == 'accountID':
                if value == self.myPlexAccount().id:
                    value = 1  # The admin account is accountID=1
            params[key] = value

        key = '/statistics/bandwidth?%s' % urlencode(params)
        return self.fetchItems(key, StatisticsBandwidth)

    def resources(self):
        """ Returns a list of :class:`~plexapi.server.StatisticsResources` objects
            with the Plex server dashboard resources data. """
        key = '/statistics/resources?timespan=6'
        return self.fetchItems(key, StatisticsResources)


class Account(PlexObject):
    """ Contains the locally cached MyPlex account information. The properties provided don't
        match the :class:`~plexapi.myplex.MyPlexAccount` object very well. I believe this exists
        because access to myplex is not required to get basic plex information. I can't imagine
        object is terribly useful except unless you were needed this information while offline.

        Parameters:
            server (:class:`~plexapi.server.PlexServer`): PlexServer this account is connected to (optional)
            data (ElementTree): Response from PlexServer used to build this object (optional).

        Attributes:
            authToken (str): Plex authentication token to access the server.
            mappingError (str): Unknown
            mappingErrorMessage (str): Unknown
            mappingState (str): Unknown
            privateAddress (str): Local IP address of the Plex server.
            privatePort (str): Local port of the Plex server.
            publicAddress (str): Public IP address of the Plex server.
            publicPort (str): Public port of the Plex server.
            signInState (str): Signin state for this account (ex: ok).
            subscriptionActive (str): True if the account subscription is active.
            subscriptionFeatures (str): List of features allowed by the server for this account.
                This may be based on your PlexPass subscription. Features include: camera_upload,
                cloudsync, content_filter, dvr, hardware_transcoding, home, lyrics, music_videos,
                pass, photo_autotags, premium_music_metadata, session_bandwidth_restrictions,
                sync, trailers, webhooks' (and maybe more).
            subscriptionState (str): 'Active' if this subscription is active.
            username (str): Plex account username (user@example.com).
    """
    key = '/myplex/account'

    def _loadData(self, data):
        self._data = data
        self.authToken = data.attrib.get('authToken')
        self.username = data.attrib.get('username')
        self.mappingState = data.attrib.get('mappingState')
        self.mappingError = data.attrib.get('mappingError')
        self.mappingErrorMessage = data.attrib.get('mappingErrorMessage')
        self.signInState = data.attrib.get('signInState')
        self.publicAddress = data.attrib.get('publicAddress')
        self.publicPort = data.attrib.get('publicPort')
        self.privateAddress = data.attrib.get('privateAddress')
        self.privatePort = data.attrib.get('privatePort')
        self.subscriptionFeatures = utils.toList(data.attrib.get('subscriptionFeatures'))
        self.subscriptionActive = cast(bool, data.attrib.get('subscriptionActive'))
        self.subscriptionState = data.attrib.get('subscriptionState')


class Activity(PlexObject):
    """A currently running activity on the PlexServer."""
    key = '/activities'

    def _loadData(self, data):
        self._data = data
        self.cancellable = cast(bool, data.attrib.get('cancellable'))
        self.progress = cast(int, data.attrib.get('progress'))
        self.title = data.attrib.get('title')
        self.subtitle = data.attrib.get('subtitle')
        self.type = data.attrib.get('type')
        self.uuid = data.attrib.get('uuid')


class SystemAccount(PlexObject):
    """ Represents a single system account.

        Attributes:
            TAG (str): 'Account'
            autoSelectAudio (bool): True or False if the account has automatic audio language enabled.
            defaultAudioLanguage (str): The default audio language code for the account.
            defaultSubtitleLanguage (str): The default subtitle language code for the account.
            id (int): The Plex account ID.
            key (str): API URL (/accounts/<id>)
            name (str): The username of the account.
            subtitleMode (bool): The subtitle mode for the account.
            thumb (str): URL for the account thumbnail.
    """
    TAG = 'Account'

    def _loadData(self, data):
        self._data = data
        self.autoSelectAudio = cast(bool, data.attrib.get('autoSelectAudio'))
        self.defaultAudioLanguage = data.attrib.get('defaultAudioLanguage')
        self.defaultSubtitleLanguage = data.attrib.get('defaultSubtitleLanguage')
        self.id = cast(int, data.attrib.get('id'))
        self.key = data.attrib.get('key')
        self.name = data.attrib.get('name')
        self.subtitleMode = cast(int, data.attrib.get('subtitleMode'))
        self.thumb = data.attrib.get('thumb')
        # For backwards compatibility
        self.accountID = self.id
        self.accountKey = self.key


class SystemDevice(PlexObject):
    """ Represents a single system device.

        Attributes:
            TAG (str): 'Device'
            createdAt (datatime): Datetime the device was created.
            id (int): The ID of the device (not the same as :class:`~plexapi.myplex.MyPlexDevice` ID).
            key (str): API URL (/devices/<id>)
            name (str): The name of the device.
            platform (str): OS the device is running (Linux, Windows, Chrome, etc.)
    """
    TAG = 'Device'

    def _loadData(self, data):
        self._data = data
        self.createdAt = utils.toDatetime(data.attrib.get('createdAt'))
        self.id = cast(int, data.attrib.get('id'))
        self.key = '/devices/%s' % self.id
        self.name = data.attrib.get('name')
        self.platform = data.attrib.get('platform')


class StatisticsBandwidth(PlexObject):
    """ Represents a single statistics bandwidth data.

        Attributes:
            TAG (str): 'StatisticsBandwidth'
            accountID (int): The associated :class:`~plexapi.server.SystemAccount` ID.
            at (datatime): Datetime of the bandwidth data.
            bytes (int): The total number of bytes for the specified timespan.
            deviceID (int): The associated :class:`~plexapi.server.SystemDevice` ID.
            lan (bool): True or False wheter the bandwidth is local or remote.
            timespan (int): The timespan for the bandwidth data.
                1: months, 2: weeks, 3: days, 4: hours, 6: seconds.

    """
    TAG = 'StatisticsBandwidth'

    def _loadData(self, data):
        self._data = data
        self.accountID = cast(int, data.attrib.get('accountID'))
        self.at = utils.toDatetime(data.attrib.get('at'))
        self.bytes = cast(int, data.attrib.get('bytes'))
        self.deviceID = cast(int, data.attrib.get('deviceID'))
        self.lan = cast(bool, data.attrib.get('lan'))
        self.timespan = cast(int, data.attrib.get('timespan'))

    def __repr__(self):
        return '<%s>' % ':'.join([p for p in [
            self.__class__.__name__,
            self._clean(self.accountID),
            self._clean(self.deviceID),
            self._clean(int(self.at.timestamp()))
        ] if p])

    def account(self):
        """ Returns the :class:`~plexapi.server.SystemAccount` associated with the bandwidth data. """
        accounts = self._server.systemAccounts()
        try:
            return next(account for account in accounts if account.id == self.accountID)
        except StopIteration:
            raise NotFound('Unknown account for this bandwidth data: accountID=%s' % self.accountID)

    def device(self):
        """ Returns the :class:`~plexapi.server.SystemDevice` associated with the bandwidth data. """
        devices = self._server.systemDevices()
        try:
            return next(device for device in devices if device.id == self.deviceID)
        except StopIteration:
            raise NotFound('Unknown device for this bandwidth data: deviceID=%s' % self.deviceID)


class StatisticsResources(PlexObject):
    """ Represents a single statistics resources data.

        Attributes:
            TAG (str): 'StatisticsResources'
            at (datatime): Datetime of the resource data.
            hostCpuUtilization (float): The system CPU usage %.
            hostMemoryUtilization (float): The Plex Media Server CPU usage %.
            processCpuUtilization (float): The system RAM usage %.
            processMemoryUtilization (float): The Plex Media Server RAM usage %.
            timespan (int): The timespan for the resource data (6: seconds).
    """
    TAG = 'StatisticsResources'

    def _loadData(self, data):
        self._data = data
        self.at = utils.toDatetime(data.attrib.get('at'))
        self.hostCpuUtilization = cast(float, data.attrib.get('hostCpuUtilization'))
        self.hostMemoryUtilization = cast(float, data.attrib.get('hostMemoryUtilization'))
        self.processCpuUtilization = cast(float, data.attrib.get('processCpuUtilization'))
        self.processMemoryUtilization = cast(float, data.attrib.get('processMemoryUtilization'))
        self.timespan = cast(int, data.attrib.get('timespan'))

    def __repr__(self):
        return '<%s>' % ':'.join([p for p in [
            self.__class__.__name__,
            self._clean(int(self.at.timestamp()))
        ] if p])
