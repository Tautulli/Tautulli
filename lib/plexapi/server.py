# -*- coding: utf-8 -*-
import os
from functools import cached_property
from urllib.parse import urlencode
from xml.etree import ElementTree

import requests

from plexapi import BASE_HEADERS, CONFIG, TIMEOUT, log, logfilter
from plexapi import utils
from plexapi.alert import AlertListener
from plexapi.base import PlexObject
from plexapi.client import PlexClient
from plexapi.collection import Collection
from plexapi.exceptions import BadRequest, NotFound, Unauthorized
from plexapi.library import Hub, Library, Path, File
from plexapi.media import Conversion, Optimized
from plexapi.playlist import Playlist
from plexapi.playqueue import PlayQueue
from plexapi.settings import Settings
from plexapi.utils import deprecated
from requests.status_codes import _codes as codes

# Need these imports to populate utils.PLEXOBJECTS
from plexapi import audio as _audio  # noqa: F401
from plexapi import collection as _collection  # noqa: F401
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
                cache the http responses from the server.
            timeout (int, optional): Timeout in seconds on initial connection to the server
                (default config.TIMEOUT).

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
        self._timeout = timeout or TIMEOUT
        self._myPlexAccount = None   # cached myPlexAccount
        self._systemAccounts = None   # cached list of SystemAccount
        self._systemDevices = None   # cached list of SystemDevice
        data = self.query(self.key, timeout=self._timeout)
        super(PlexServer, self).__init__(self, data, self.key)

    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        self._data = data
        self.allowCameraUpload = utils.cast(bool, data.attrib.get('allowCameraUpload'))
        self.allowChannelAccess = utils.cast(bool, data.attrib.get('allowChannelAccess'))
        self.allowMediaDeletion = utils.cast(bool, data.attrib.get('allowMediaDeletion'))
        self.allowSharing = utils.cast(bool, data.attrib.get('allowSharing'))
        self.allowSync = utils.cast(bool, data.attrib.get('allowSync'))
        self.backgroundProcessing = utils.cast(bool, data.attrib.get('backgroundProcessing'))
        self.certificate = utils.cast(bool, data.attrib.get('certificate'))
        self.companionProxy = utils.cast(bool, data.attrib.get('companionProxy'))
        self.diagnostics = utils.toList(data.attrib.get('diagnostics'))
        self.eventStream = utils.cast(bool, data.attrib.get('eventStream'))
        self.friendlyName = data.attrib.get('friendlyName')
        self.hubSearch = utils.cast(bool, data.attrib.get('hubSearch'))
        self.machineIdentifier = data.attrib.get('machineIdentifier')
        self.multiuser = utils.cast(bool, data.attrib.get('multiuser'))
        self.myPlex = utils.cast(bool, data.attrib.get('myPlex'))
        self.myPlexMappingState = data.attrib.get('myPlexMappingState')
        self.myPlexSigninState = data.attrib.get('myPlexSigninState')
        self.myPlexSubscription = utils.cast(bool, data.attrib.get('myPlexSubscription'))
        self.myPlexUsername = data.attrib.get('myPlexUsername')
        self.ownerFeatures = utils.toList(data.attrib.get('ownerFeatures'))
        self.photoAutoTag = utils.cast(bool, data.attrib.get('photoAutoTag'))
        self.platform = data.attrib.get('platform')
        self.platformVersion = data.attrib.get('platformVersion')
        self.pluginHost = utils.cast(bool, data.attrib.get('pluginHost'))
        self.readOnlyLibraries = utils.cast(int, data.attrib.get('readOnlyLibraries'))
        self.requestParametersInCookie = utils.cast(bool, data.attrib.get('requestParametersInCookie'))
        self.streamingBrainVersion = data.attrib.get('streamingBrainVersion')
        self.sync = utils.cast(bool, data.attrib.get('sync'))
        self.transcoderActiveVideoSessions = int(data.attrib.get('transcoderActiveVideoSessions', 0))
        self.transcoderAudio = utils.cast(bool, data.attrib.get('transcoderAudio'))
        self.transcoderLyrics = utils.cast(bool, data.attrib.get('transcoderLyrics'))
        self.transcoderPhoto = utils.cast(bool, data.attrib.get('transcoderPhoto'))
        self.transcoderSubtitles = utils.cast(bool, data.attrib.get('transcoderSubtitles'))
        self.transcoderVideo = utils.cast(bool, data.attrib.get('transcoderVideo'))
        self.transcoderVideoBitrates = utils.toList(data.attrib.get('transcoderVideoBitrates'))
        self.transcoderVideoQualities = utils.toList(data.attrib.get('transcoderVideoQualities'))
        self.transcoderVideoResolutions = utils.toList(data.attrib.get('transcoderVideoResolutions'))
        self.updatedAt = utils.toDatetime(data.attrib.get('updatedAt'))
        self.updater = utils.cast(bool, data.attrib.get('updater'))
        self.version = data.attrib.get('version')
        self.voiceSearch = utils.cast(bool, data.attrib.get('voiceSearch'))

    def _headers(self, **kwargs):
        """ Returns dict containing base headers for all requests to the server. """
        headers = BASE_HEADERS.copy()
        if self._token:
            headers['X-Plex-Token'] = self._token
        headers.update(kwargs)
        return headers

    def _uriRoot(self):
        return f'server://{self.machineIdentifier}/com.plexapp.plugins.library'

    @cached_property
    def library(self):
        """ Library to browse or search your media. """
        try:
            data = self.query(Library.key)
        except BadRequest:
            # Only the owner has access to /library
            # so just return the library without the data.
            data = self.query('/library/sections/')
        return Library(self, data)

    @cached_property
    def settings(self):
        """ Returns a list of all server settings. """
        data = self.query(Settings.key)
        return Settings(self, data)

    def identity(self):
        """ Returns the Plex server identity. """
        data = self.query('/identity')
        return Identity(self, data)

    def account(self):
        """ Returns the :class:`~plexapi.server.Account` object this server belongs to. """
        data = self.query(Account.key)
        return Account(self, data)

    def claim(self, account):
        """ Claim the Plex server using a :class:`~plexapi.myplex.MyPlexAccount`.
            This will only work with an unclaimed server on localhost or the same subnet.

            Parameters:
                account (:class:`~plexapi.myplex.MyPlexAccount`): The account used to
                    claim the server.
        """
        key = '/myplex/claim'
        params = {'token': account.claimToken()}
        data = self.query(key, method=self._session.post, params=params)
        return Account(self, data)

    def unclaim(self):
        """ Unclaim the Plex server. This will remove the server from your
            :class:`~plexapi.myplex.MyPlexAccount`.
        """
        data = self.query(Account.key, method=self._session.delete)
        return Account(self, data)

    @property
    def activities(self):
        """Returns all current PMS activities."""
        activities = []
        for elem in self.query(Activity.key):
            activities.append(Activity(self, elem))
        return activities

    def agents(self, mediaType=None):
        """ Returns a list of :class:`~plexapi.media.Agent` objects this server has available. """
        key = '/system/agents'
        if mediaType:
            key += f'?mediaType={utils.searchType(mediaType)}'
        return self.fetchItems(key)

    def createToken(self, type='delegation', scope='all'):
        """ Create a temp access token for the server. """
        if not self._token:
            # Handle unclaimed servers
            return None
        q = self.query(f'/security/token?type={type}&scope={scope}')
        return q.attrib.get('token')

    def switchUser(self, user, session=None, timeout=None):
        """ Returns a new :class:`~plexapi.server.PlexServer` object logged in as the given username.
            Note: Only the admin account can switch to other users.

            Parameters:
                user (:class:`~plexapi.myplex.MyPlexUser` or str): `MyPlexUser` object, username,
                    email, or user id of the user to log in to the server.
                session (requests.Session, optional): Use your own session object if you want to
                    cache the http responses from the server. This will default to the same
                    session as the admin account if no new session is provided.
                timeout (int, optional): Timeout in seconds on initial connection to the server.
                    This will default to the same timeout as the admin account if no new timeout
                    is provided.

            Example:

                .. code-block:: python

                    from plexapi.server import PlexServer
                    # Login to the Plex server using the admin token
                    plex = PlexServer('http://plexserver:32400', token='2ffLuB84dqLswk9skLos')
                    # Login to the same Plex server using a different account
                    userPlex = plex.switchUser("Username")

        """
        from plexapi.myplex import MyPlexUser
        user = user if isinstance(user, MyPlexUser) else self.myPlexAccount().user(user)
        userToken = user.get_token(self.machineIdentifier)
        if session is None:
            session = self._session
        if timeout is None:
            timeout = self._timeout
        return PlexServer(self._baseurl, token=userToken, session=session, timeout=timeout)

    def systemAccounts(self):
        """ Returns a list of :class:`~plexapi.server.SystemAccount` objects this server contains. """
        if self._systemAccounts is None:
            key = '/accounts'
            self._systemAccounts = self.fetchItems(key, SystemAccount)
        return self._systemAccounts

    def systemAccount(self, accountID):
        """ Returns the :class:`~plexapi.server.SystemAccount` object for the specified account ID.

            Parameters:
                accountID (int): The :class:`~plexapi.server.SystemAccount` ID.
        """
        try:
            return next(account for account in self.systemAccounts() if account.id == accountID)
        except StopIteration:
            raise NotFound(f'Unknown account with accountID={accountID}') from None

    def systemDevices(self):
        """ Returns a list of :class:`~plexapi.server.SystemDevice` objects this server contains. """
        if self._systemDevices is None:
            key = '/devices'
            self._systemDevices = self.fetchItems(key, SystemDevice)
        return self._systemDevices

    def systemDevice(self, deviceID):
        """ Returns the :class:`~plexapi.server.SystemDevice` object for the specified device ID.

            Parameters:
                deviceID (int): The :class:`~plexapi.server.SystemDevice` ID.
        """
        try:
            return next(device for device in self.systemDevices() if device.id == deviceID)
        except StopIteration:
            raise NotFound(f'Unknown device with deviceID={deviceID}') from None

    def myPlexAccount(self):
        """ Returns a :class:`~plexapi.myplex.MyPlexAccount` object using the same
            token to access this server. If you are not the owner of this PlexServer
            you're likely to receive an authentication error calling this.
        """
        if self._myPlexAccount is None:
            from plexapi.myplex import MyPlexAccount
            self._myPlexAccount = MyPlexAccount(token=self._token, session=self._session)
        return self._myPlexAccount

    def _myPlexClientPorts(self):
        """ Sometimes the PlexServer does not properly advertise port numbers required
            to connect. This attempts to look up device port number from plex.tv.
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
            key = f'/services/browse/{base64path}'
        else:
            key = '/services/browse'
        key += f'?includeFiles={int(includeFiles)}'  # starting with PMS v1.32.7.7621 this must set explicitly
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

    def isBrowsable(self, path):
        """ Returns True if the Plex server can browse the given path.

            Parameters:
                path (:class:`~plexapi.library.Path` or str): Full path to browse.
        """
        if isinstance(path, Path):
            path = path.path
        paths = [p.path for p in self.browse(os.path.dirname(path), includeFiles=False)]
        return path in paths

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
            baseurl = f"http://{elem.attrib['host']}:{port}"
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

        raise NotFound(f'Unknown client name: {name}')

    def createCollection(self, title, section, items=None, smart=False, limit=None,
                         libtype=None, sort=None, filters=None, **kwargs):
        """ Creates and returns a new :class:`~plexapi.collection.Collection`.

            Parameters:
                title (str): Title of the collection.
                section (:class:`~plexapi.library.LibrarySection`, str): The library section to create the collection in.
                items (List): Regular collections only, list of :class:`~plexapi.audio.Audio`,
                    :class:`~plexapi.video.Video`, or :class:`~plexapi.photo.Photo` objects to be added to the collection.
                smart (bool): True to create a smart collection. Default False.
                limit (int): Smart collections only, limit the number of items in the collection.
                libtype (str): Smart collections only, the specific type of content to filter
                    (movie, show, season, episode, artist, album, track, photoalbum, photo).
                sort (str or list, optional): Smart collections only, a string of comma separated sort fields
                    or a list of sort fields in the format ``column:dir``.
                    See :func:`~plexapi.library.LibrarySection.search` for more info.
                filters (dict): Smart collections only, a dictionary of advanced filters.
                    See :func:`~plexapi.library.LibrarySection.search` for more info.
                **kwargs (dict): Smart collections only, additional custom filters to apply to the
                    search results. See :func:`~plexapi.library.LibrarySection.search` for more info.

            Raises:
                :class:`plexapi.exceptions.BadRequest`: When no items are included to create the collection.
                :class:`plexapi.exceptions.BadRequest`: When mixing media types in the collection.

            Returns:
                :class:`~plexapi.collection.Collection`: A new instance of the created Collection.

            Example:

                .. code-block:: python

                    # Create a regular collection
                    movies = plex.library.section("Movies")
                    movie1 = movies.get("Big Buck Bunny")
                    movie2 = movies.get("Sita Sings the Blues")
                    collection = plex.createCollection(
                        title="Favorite Movies",
                        section=movies,
                        items=[movie1, movie2]
                    )

                    # Create a smart collection
                    collection = plex.createCollection(
                        title="Recently Aired Comedy TV Shows",
                        section="TV Shows",
                        smart=True,
                        sort="episode.originallyAvailableAt:desc",
                        filters={"episode.originallyAvailableAt>>": "4w", "genre": "comedy"}
                    )

        """
        return Collection.create(
            self, title, section, items=items, smart=smart, limit=limit,
            libtype=libtype, sort=sort, filters=filters, **kwargs)

    def createPlaylist(self, title, section=None, items=None, smart=False, limit=None,
                       libtype=None, sort=None, filters=None, m3ufilepath=None, **kwargs):
        """ Creates and returns a new :class:`~plexapi.playlist.Playlist`.

            Parameters:
                title (str): Title of the playlist.
                section (:class:`~plexapi.library.LibrarySection`, str): Smart playlists and m3u import only,
                    the library section to create the playlist in.
                items (List): Regular playlists only, list of :class:`~plexapi.audio.Audio`,
                    :class:`~plexapi.video.Video`, or :class:`~plexapi.photo.Photo` objects to be added to the playlist.
                smart (bool): True to create a smart playlist. Default False.
                limit (int): Smart playlists only, limit the number of items in the playlist.
                libtype (str): Smart playlists only, the specific type of content to filter
                    (movie, show, season, episode, artist, album, track, photoalbum, photo).
                sort (str or list, optional): Smart playlists only, a string of comma separated sort fields
                    or a list of sort fields in the format ``column:dir``.
                    See :func:`~plexapi.library.LibrarySection.search` for more info.
                filters (dict): Smart playlists only, a dictionary of advanced filters.
                    See :func:`~plexapi.library.LibrarySection.search` for more info.
                m3ufilepath (str): Music playlists only, the full file path to an m3u file to import.
                    Note: This will overwrite any playlist previously created from the same m3u file.
                **kwargs (dict): Smart playlists only, additional custom filters to apply to the
                    search results. See :func:`~plexapi.library.LibrarySection.search` for more info.

            Raises:
                :class:`plexapi.exceptions.BadRequest`: When no items are included to create the playlist.
                :class:`plexapi.exceptions.BadRequest`: When mixing media types in the playlist.
                :class:`plexapi.exceptions.BadRequest`: When attempting to import m3u file into non-music library.
                :class:`plexapi.exceptions.BadRequest`: When failed to import m3u file.

            Returns:
                :class:`~plexapi.playlist.Playlist`: A new instance of the created Playlist.

            Example:

                .. code-block:: python

                    # Create a regular playlist
                    episodes = plex.library.section("TV Shows").get("Game of Thrones").episodes()
                    playlist = plex.createPlaylist(
                        title="GoT Episodes",
                        items=episodes
                    )

                    # Create a smart playlist
                    playlist = plex.createPlaylist(
                        title="Top 10 Unwatched Movies",
                        section="Movies",
                        smart=True,
                        limit=10,
                        sort="audienceRating:desc",
                        filters={"audienceRating>>": 8.0, "unwatched": True}
                    )

                    # Create a music playlist from an m3u file
                    playlist = plex.createPlaylist(
                        title="Favorite Tracks",
                        section="Music",
                        m3ufilepath="/path/to/playlist.m3u"
                    )

        """
        return Playlist.create(
            self, title, section=section, items=items, smart=smart, limit=limit,
            libtype=libtype, sort=sort, filters=filters, m3ufilepath=m3ufilepath, **kwargs)

    def createPlayQueue(self, item, **kwargs):
        """ Creates and returns a new :class:`~plexapi.playqueue.PlayQueue`.

            Parameters:
                item (Media or Playlist): Media or playlist to add to PlayQueue.
                kwargs (dict): See `~plexapi.playqueue.PlayQueue.create`.
        """
        return PlayQueue.create(self, item, **kwargs)

    def downloadDatabases(self, savepath=None, unpack=False, showstatus=False):
        """ Download databases.

            Parameters:
                savepath (str): Defaults to current working dir.
                unpack (bool): Unpack the zip file.
                showstatus(bool): Display a progressbar.
        """
        url = self.url('/diagnostics/databases')
        filepath = utils.download(url, self._token, None, savepath, self._session, unpack=unpack, showstatus=showstatus)
        return filepath

    def downloadLogs(self, savepath=None, unpack=False, showstatus=False):
        """ Download server logs.

            Parameters:
                savepath (str): Defaults to current working dir.
                unpack (bool): Unpack the zip file.
                showstatus(bool): Display a progressbar.
        """
        url = self.url('/diagnostics/logs')
        filepath = utils.download(url, self._token, None, savepath, self._session, unpack=unpack, showstatus=showstatus)
        return filepath

    def butlerTasks(self):
        """ Return a list of :class:`~plexapi.base.ButlerTask` objects. """
        return self.fetchItems('/butler')

    def runButlerTask(self, task):
        """ Manually run a butler task immediately instead of waiting for the scheduled task to run.
            Note: The butler task is run asynchronously. Check Plex Web to monitor activity.

            Parameters:
                task (str): The name of the task to run. (e.g. 'BackupDatabase')

            Example:

                .. code-block:: python

                    availableTasks = [task.name for task in plex.butlerTasks()]
                    print("Available butler tasks:", availableTasks)

        """
        validTasks = [_task.name for _task in self.butlerTasks()]
        if task not in validTasks:
            raise BadRequest(
                f'Invalid butler task: {task}. Available tasks are: {validTasks}'
            )
        self.query(f'/butler/{task}', method=self._session.post)
        return self

    @deprecated('use "checkForUpdate" instead')
    def check_for_update(self, force=True, download=False):
        return self.checkForUpdate(force=force, download=download)

    def checkForUpdate(self, force=True, download=False):
        """ Returns a :class:`~plexapi.server.Release` object containing release info
            if an update is available or None if no update is available.

            Parameters:
                force (bool): Force server to check for new releases
                download (bool): Download if a update is available.
        """
        part = f'/updater/check?download={1 if download else 0}'
        if force:
            self.query(part, method=self._session.put)
        releases = self.fetchItems('/updater/status')
        if len(releases):
            return releases[0]

    def isLatest(self):
        """ Returns True if the installed version of Plex Media Server is the latest. """
        release = self.checkForUpdate(force=True)
        return release is None

    def canInstallUpdate(self):
        """ Returns True if the newest version of Plex Media Server can be installed automatically.
            (e.g. Windows and Mac can install updates automatically, but Docker and NAS devices cannot.)
        """
        release = self.query('/updater/status')
        return utils.cast(bool, release.get('canInstall'))

    def installUpdate(self):
        """ Automatically install the newest version of Plex Media Server. """
        # We can add this but dunno how useful this is since it sometimes
        # requires user action using a gui.
        part = '/updater/apply'
        release = self.checkForUpdate(force=True, download=True)
        if release and release.version != self.version:
            # figure out what method this is..
            return self.query(part, method=self._session.put)

    def history(self, maxresults=None, mindate=None, ratingKey=None, accountID=None, librarySectionID=None):
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
        args = {'sort': 'viewedAt:desc'}
        if ratingKey:
            args['metadataItemID'] = ratingKey
        if accountID:
            args['accountID'] = accountID
        if librarySectionID:
            args['librarySectionID'] = librarySectionID
        if mindate:
            args['viewedAt>'] = int(mindate.timestamp())

        key = f'/status/sessions/history/all{utils.joinArgs(args)}'
        return self.fetchItems(key, maxresults=maxresults)

    def playlists(self, playlistType=None, sectionId=None, title=None, sort=None, **kwargs):
        """ Returns a list of all :class:`~plexapi.playlist.Playlist` objects on the server.

            Parameters:
                playlistType (str, optional): The type of playlists to return (audio, video, photo).
                    Default returns all playlists.
                sectionId (int, optional): The section ID (key) of the library to search within.
                title (str, optional): General string query to search for. Partial string matches are allowed.
                sort (str or list, optional): A string of comma separated sort fields in the format ``column:dir``.
        """
        args = {}
        if playlistType is not None:
            args['playlistType'] = playlistType
        if sectionId is not None:
            args['sectionID'] = sectionId
        if title is not None:
            args['title'] = title
        if sort is not None:
            # TODO: Automatically retrieve and validate sort field similar to LibrarySection.search()
            args['sort'] = sort

        key = f'/playlists{utils.joinArgs(args)}'
        return self.fetchItems(key, **kwargs)

    def playlist(self, title):
        """ Returns the :class:`~plexapi.client.Playlist` that matches the specified title.

            Parameters:
                title (str): Title of the playlist to return.

            Raises:
                :exc:`~plexapi.exceptions.NotFound`: Unable to find playlist.
        """
        try:
            return self.playlists(title=title, title__iexact=title)[0]
        except IndexError:
            raise NotFound(f'Unable to find playlist with title "{title}".') from None

    def optimizedItems(self, removeAll=None):
        """ Returns list of all :class:`~plexapi.media.Optimized` objects connected to server. """
        if removeAll is True:
            key = '/playlists/generators?type=42'
            self.query(key, method=self._server._session.delete)
        else:
            backgroundProcessing = self.fetchItem('/playlists?type=42')
            return self.fetchItems(f'{backgroundProcessing.key}/items', cls=Optimized)

    @deprecated('use "plexapi.media.Optimized.items()" instead')
    def optimizedItem(self, optimizedID):
        """ Returns single queued optimized item :class:`~plexapi.media.Video` object.
            Allows for using optimized item ID to connect back to source item.
        """

        backgroundProcessing = self.fetchItem('/playlists?type=42')
        return self.fetchItem(f'{backgroundProcessing.key}/items/{optimizedID}/items')

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
        timeout = timeout or self._timeout
        log.debug('%s %s', method.__name__.upper(), url)
        headers = self._headers(**headers or {})
        response = method(url, headers=headers, timeout=timeout, **kwargs)
        if response.status_code not in (200, 201, 204):
            codename = codes.get(response.status_code)[0]
            errtext = response.text.replace('\n', ' ')
            message = f'({response.status_code}) {codename}; {response.url} {errtext}'
            if response.status_code == 401:
                raise Unauthorized(message)
            elif response.status_code == 404:
                raise NotFound(message)
            else:
                raise BadRequest(message)
        data = response.text.encode('utf8')
        return ElementTree.fromstring(data) if data.strip() else None

    def search(self, query, mediatype=None, limit=None, sectionId=None):
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
                mediatype (str, optional): Limit your search to the specified media type.
                    actor, album, artist, autotag, collection, director, episode, game, genre,
                    movie, photo, photoalbum, place, playlist, shared, show, tag, track
                limit (int, optional): Limit to the specified number of results per Hub.
                sectionId (int, optional): The section ID (key) of the library to search within.
        """
        results = []
        params = {
            'query': query,
            'includeCollections': 1,
            'includeExternalMedia': 1}
        if limit:
            params['limit'] = limit
        if sectionId:
            params['sectionId'] = sectionId
        key = f'/hubs/search?{urlencode(params)}'
        for hub in self.fetchItems(key, Hub):
            if mediatype:
                if hub.type == mediatype:
                    return hub.items
            else:
                results += hub.items
        return results

    def continueWatching(self):
        """ Return a list of all items in the Continue Watching hub. """
        return self.fetchItems('/hubs/continueWatching/items')

    def sessions(self):
        """ Returns a list of all active session (currently playing) media objects. """
        return self.fetchItems('/status/sessions')

    def transcodeSessions(self):
        """ Returns a list of all active :class:`~plexapi.media.TranscodeSession` objects. """
        return self.fetchItems('/transcode/sessions')

    def startAlertListener(self, callback=None, callbackError=None):
        """ Creates a websocket connection to the Plex Server to optionally receive
            notifications. These often include messages from Plex about media scans
            as well as updates to currently running Transcode Sessions.

            Returns a new :class:`~plexapi.alert.AlertListener` object.

            Note: ``websocket-client`` must be installed in order to use this feature.

            .. code-block:: python

                >> pip install websocket-client

            Parameters:
                callback (func): Callback function to call on received messages.
                callbackError (func): Callback function to call on errors.

            Raises:
                :exc:`~plexapi.exception.Unsupported`: Websocket-client not installed.
        """
        notifier = AlertListener(self, callback, callbackError)
        notifier.start()
        return notifier

    def transcodeImage(self, imageUrl, height, width,
                       opacity=None, saturation=None, blur=None, background=None, blendColor=None,
                       minSize=True, upscale=True, imageFormat=None):
        """ Returns the URL for a transcoded image.

            Parameters:
                imageUrl (str): The URL to the image
                    (eg. returned by :func:`~plexapi.mixins.PosterUrlMixin.thumbUrl`
                    or :func:`~plexapi.mixins.ArtUrlMixin.artUrl`).
                    The URL can be an online image.
                height (int): Height to transcode the image to.
                width (int): Width to transcode the image to.
                opacity (int, optional): Change the opacity of the image (0 to 100)
                saturation (int, optional): Change the saturation of the image (0 to 100).
                blur (int, optional): The blur to apply to the image in pixels (e.g. 3).
                background (str, optional): The background hex colour to apply behind the opacity (e.g. '000000').
                blendColor (str, optional): The hex colour to blend the image with (e.g. '000000').
                minSize (bool, optional): Maintain smallest dimension. Default True.
                upscale (bool, optional): Upscale the image if required. Default True.
                imageFormat (str, optional): 'jpeg' (default) or 'png'.
        """
        params = {
            'url': imageUrl,
            'height': height,
            'width': width,
            'minSize': int(bool(minSize)),
            'upscale': int(bool(upscale))
        }
        if opacity is not None:
            params['opacity'] = opacity
        if saturation is not None:
            params['saturation'] = saturation
        if blur is not None:
            params['blur'] = blur
        if background is not None:
            params['background'] = str(background).strip('#')
        if blendColor is not None:
            params['blendColor'] = str(blendColor).strip('#')
        if imageFormat is not None:
            params['format'] = imageFormat.lower()

        key = f'/photo/:/transcode{utils.joinArgs(params)}'
        return self.url(key, includeToken=True)

    def url(self, key, includeToken=None):
        """ Build a URL string with proper token argument.  Token will be appended to the URL
            if either includeToken is True or CONFIG.log.show_secrets is 'true'.
        """
        if self._token and (includeToken or self._showSecrets):
            delim = '&' if '?' in key else '?'
            return f'{self._baseurl}{key}{delim}X-Plex-Token={self._token}'
        return f'{self._baseurl}{key}'

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
        return self.query(f'/:/prefs?allowMediaDeletion={value}', self._session.put)

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
                        print(f'{account.name} used {gigabytes} GB of {local} bandwidth on {date} from {device.name}')

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
                raise BadRequest(f"Invalid timespan specified: {timespan}. "
                                 f"Available timespans: {', '.join(timespans.keys())}")

        filters = {'accountID', 'at', 'at<', 'at>', 'bytes', 'bytes<', 'bytes>', 'deviceID', 'lan'}

        for key, value in kwargs.items():
            if key not in filters:
                raise BadRequest(f'Unknown filter: {key}={value}')
            if key.startswith('at'):
                try:
                    value = utils.cast(int, value.timestamp())
                except AttributeError:
                    raise BadRequest(f'Time frame filter must be a datetime object: {key}={value}')
            elif key.startswith('bytes') or key == 'lan':
                value = utils.cast(int, value)
            elif key == 'accountID':
                if value == self.myPlexAccount().id:
                    value = 1  # The admin account is accountID=1
            params[key] = value

        key = f'/statistics/bandwidth?{urlencode(params)}'
        return self.fetchItems(key, StatisticsBandwidth)

    def resources(self):
        """ Returns a list of :class:`~plexapi.server.StatisticsResources` objects
            with the Plex server dashboard resources data. """
        key = '/statistics/resources?timespan=6'
        return self.fetchItems(key, StatisticsResources)

    def _buildWebURL(self, base=None, endpoint=None, **kwargs):
        """ Build the Plex Web URL for the object.

            Parameters:
                base (str): The base URL before the fragment (``#!``).
                    Default is https://app.plex.tv/desktop.
                endpoint (str): The Plex Web URL endpoint.
                    None for server, 'playlist' for playlists, 'details' for all other media types.
                **kwargs (dict): Dictionary of URL parameters.
        """
        if base is None:
            base = 'https://app.plex.tv/desktop/'

        if endpoint:
            return f'{base}#!/server/{self.machineIdentifier}/{endpoint}{utils.joinArgs(kwargs)}'
        else:
            return f'{base}#!/media/{self.machineIdentifier}/com.plexapp.plugins.library{utils.joinArgs(kwargs)}'

    def getWebURL(self, base=None, playlistTab=None):
        """ Returns the Plex Web URL for the server.

            Parameters:
                base (str): The base URL before the fragment (``#!``).
                    Default is https://app.plex.tv/desktop.
                playlistTab (str): The playlist tab (audio, video, photo). Only used for the playlist URL.
        """
        if playlistTab is not None:
            params = {'source': 'playlists', 'pivot': f'playlists.{playlistTab}'}
        else:
            params = {'key': '/hubs', 'pageType': 'hub'}
        return self._buildWebURL(base=base, **params)


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
        self.subscriptionActive = utils.cast(bool, data.attrib.get('subscriptionActive'))
        self.subscriptionState = data.attrib.get('subscriptionState')


class Activity(PlexObject):
    """A currently running activity on the PlexServer."""
    key = '/activities'

    def _loadData(self, data):
        self._data = data
        self.cancellable = utils.cast(bool, data.attrib.get('cancellable'))
        self.progress = utils.cast(int, data.attrib.get('progress'))
        self.title = data.attrib.get('title')
        self.subtitle = data.attrib.get('subtitle')
        self.type = data.attrib.get('type')
        self.uuid = data.attrib.get('uuid')


@utils.registerPlexObject
class Release(PlexObject):
    TAG = 'Release'
    key = '/updater/status'

    def _loadData(self, data):
        self.download_key = data.attrib.get('key')
        self.version = data.attrib.get('version')
        self.added = data.attrib.get('added')
        self.fixed = data.attrib.get('fixed')
        self.downloadURL = data.attrib.get('downloadURL')
        self.state = data.attrib.get('state')


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
        self.autoSelectAudio = utils.cast(bool, data.attrib.get('autoSelectAudio'))
        self.defaultAudioLanguage = data.attrib.get('defaultAudioLanguage')
        self.defaultSubtitleLanguage = data.attrib.get('defaultSubtitleLanguage')
        self.id = utils.cast(int, data.attrib.get('id'))
        self.key = data.attrib.get('key')
        self.name = data.attrib.get('name')
        self.subtitleMode = utils.cast(int, data.attrib.get('subtitleMode'))
        self.thumb = data.attrib.get('thumb')
        # For backwards compatibility
        self.accountID = self.id
        self.accountKey = self.key


class SystemDevice(PlexObject):
    """ Represents a single system device.

        Attributes:
            TAG (str): 'Device'
            clientIdentifier (str): The unique identifier for the device.
            createdAt (datetime): Datetime the device was created.
            id (int): The ID of the device (not the same as :class:`~plexapi.myplex.MyPlexDevice` ID).
            key (str): API URL (/devices/<id>)
            name (str): The name of the device.
            platform (str): OS the device is running (Linux, Windows, Chrome, etc.)
    """
    TAG = 'Device'

    def _loadData(self, data):
        self._data = data
        self.clientIdentifier = data.attrib.get('clientIdentifier')
        self.createdAt = utils.toDatetime(data.attrib.get('createdAt'))
        self.id = utils.cast(int, data.attrib.get('id'))
        self.key = f'/devices/{self.id}'
        self.name = data.attrib.get('name')
        self.platform = data.attrib.get('platform')


class StatisticsBandwidth(PlexObject):
    """ Represents a single statistics bandwidth data.

        Attributes:
            TAG (str): 'StatisticsBandwidth'
            accountID (int): The associated :class:`~plexapi.server.SystemAccount` ID.
            at (datetime): Datetime of the bandwidth data.
            bytes (int): The total number of bytes for the specified time span.
            deviceID (int): The associated :class:`~plexapi.server.SystemDevice` ID.
            lan (bool): True or False whether the bandwidth is local or remote.
            timespan (int): The time span for the bandwidth data.
                1: months, 2: weeks, 3: days, 4: hours, 6: seconds.

    """
    TAG = 'StatisticsBandwidth'

    def _loadData(self, data):
        self._data = data
        self.accountID = utils.cast(int, data.attrib.get('accountID'))
        self.at = utils.toDatetime(data.attrib.get('at'))
        self.bytes = utils.cast(int, data.attrib.get('bytes'))
        self.deviceID = utils.cast(int, data.attrib.get('deviceID'))
        self.lan = utils.cast(bool, data.attrib.get('lan'))
        self.timespan = utils.cast(int, data.attrib.get('timespan'))

    def __repr__(self):
        return '<{}>'.format(
            ':'.join([p for p in [
                self.__class__.__name__,
                self._clean(self.accountID),
                self._clean(self.deviceID),
                self._clean(int(self.at.timestamp()))
            ] if p])
        )

    def account(self):
        """ Returns the :class:`~plexapi.server.SystemAccount` associated with the bandwidth data. """
        return self._server.systemAccount(self.accountID)

    def device(self):
        """ Returns the :class:`~plexapi.server.SystemDevice` associated with the bandwidth data. """
        return self._server.systemDevice(self.deviceID)


class StatisticsResources(PlexObject):
    """ Represents a single statistics resources data.

        Attributes:
            TAG (str): 'StatisticsResources'
            at (datetime): Datetime of the resource data.
            hostCpuUtilization (float): The system CPU usage %.
            hostMemoryUtilization (float): The Plex Media Server CPU usage %.
            processCpuUtilization (float): The system RAM usage %.
            processMemoryUtilization (float): The Plex Media Server RAM usage %.
            timespan (int): The time span for the resource data (6: seconds).
    """
    TAG = 'StatisticsResources'

    def _loadData(self, data):
        self._data = data
        self.at = utils.toDatetime(data.attrib.get('at'))
        self.hostCpuUtilization = utils.cast(float, data.attrib.get('hostCpuUtilization'))
        self.hostMemoryUtilization = utils.cast(float, data.attrib.get('hostMemoryUtilization'))
        self.processCpuUtilization = utils.cast(float, data.attrib.get('processCpuUtilization'))
        self.processMemoryUtilization = utils.cast(float, data.attrib.get('processMemoryUtilization'))
        self.timespan = utils.cast(int, data.attrib.get('timespan'))

    def __repr__(self):
        return f"<{':'.join([p for p in [self.__class__.__name__, self._clean(int(self.at.timestamp()))] if p])}>"


@utils.registerPlexObject
class ButlerTask(PlexObject):
    """ Represents a single scheduled butler task.

        Attributes:
            TAG (str): 'ButlerTask'
            description (str): The description of the task.
            enabled (bool): Whether the task is enabled.
            interval (int): The interval the task is run in days.
            name (str): The name of the task.
            scheduleRandomized (bool): Whether the task schedule is randomized.
            title (str): The title of the task.
    """
    TAG = 'ButlerTask'

    def _loadData(self, data):
        self._data = data
        self.description = data.attrib.get('description')
        self.enabled = utils.cast(bool, data.attrib.get('enabled'))
        self.interval = utils.cast(int, data.attrib.get('interval'))
        self.name = data.attrib.get('name')
        self.scheduleRandomized = utils.cast(bool, data.attrib.get('scheduleRandomized'))
        self.title = data.attrib.get('title')


class Identity(PlexObject):
    """ Represents a server identity.

        Attributes:
            claimed (bool): True or False if the server is claimed.
            machineIdentifier (str): The Plex server machine identifier.
            version (str): The Plex server version.
    """

    def __repr__(self):
        return f"<{self.__class__.__name__}:{self.machineIdentifier}>"

    def _loadData(self, data):
        self._data = data
        self.claimed = utils.cast(bool, data.attrib.get('claimed'))
        self.machineIdentifier = data.attrib.get('machineIdentifier')
        self.version = data.attrib.get('version')
