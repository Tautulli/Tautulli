# -*- coding: utf-8 -*-
import time
from xml.etree import ElementTree

import requests
from plexapi import BASE_HEADERS, CONFIG, TIMEOUT, log, logfilter, utils
from plexapi.base import PlexObject
from plexapi.exceptions import BadRequest, NotFound, Unauthorized, Unsupported
from plexapi.playqueue import PlayQueue
from requests.status_codes import _codes as codes

DEFAULT_MTYPE = 'video'


@utils.registerPlexObject
class PlexClient(PlexObject):
    """ Main class for interacting with a Plex client. This class can connect
        directly to the client and control it or proxy commands through your
        Plex Server. To better understand the Plex client API's read this page:
        https://github.com/plexinc/plex-media-player/wiki/Remote-control-API

        Parameters:
            server (:class:`~plexapi.server.PlexServer`): PlexServer this client is connected to (optional).
            data (ElementTree): Response from PlexServer used to build this object (optional).
            initpath (str): Path used to generate data.
            baseurl (str): HTTP URL to connect dirrectly to this client.
            token (str): X-Plex-Token used for authenication (optional).
            session (:class:`~requests.Session`): requests.Session object if you want more control (optional).
            timeout (int): timeout in seconds on initial connect to client (default config.TIMEOUT).

        Attributes:
            TAG (str): 'Player'
            key (str): '/resources'
            device (str): Best guess on the type of device this is (PS, iPhone, Linux, etc).
            deviceClass (str): Device class (pc, phone, etc).
            machineIdentifier (str): Unique ID for this device.
            model (str): Unknown
            platform (str): Unknown
            platformVersion (str): Description
            product (str): Client Product (Plex for iOS, etc).
            protocol (str): Always seems ot be 'plex'.
            protocolCapabilities (list<str>): List of client capabilities (navigation, playback,
                timeline, mirror, playqueues).
            protocolVersion (str): Protocol version (1, future proofing?)
            server (:class:`~plexapi.server.PlexServer`): Server this client is connected to.
            session (:class:`~requests.Session`): Session object used for connection.
            state (str): Unknown
            title (str): Name of this client (Johns iPhone, etc).
            token (str): X-Plex-Token used for authenication
            vendor (str): Unknown
            version (str): Device version (4.6.1, etc).
            _baseurl (str): HTTP address of the client.
            _token (str): Token used to access this client.
            _session (obj): Requests session object used to access this client.
            _proxyThroughServer (bool): Set to True after calling
                :func:`~plexapi.client.PlexClient.proxyThroughServer` (default False).
    """
    TAG = 'Player'
    key = '/resources'

    def __init__(self, server=None, data=None, initpath=None, baseurl=None,
          token=None, connect=True, session=None, timeout=None):
        super(PlexClient, self).__init__(server, data, initpath)
        self._baseurl = baseurl.strip('/') if baseurl else None
        self._token = logfilter.add_secret(token)
        self._showSecrets = CONFIG.get('log.show_secrets', '').lower() == 'true'
        server_session = server._session if server else None
        self._session = session or server_session or requests.Session()
        self._proxyThroughServer = False
        self._commandId = 0
        self._last_call = 0
        self._timeline_cache = []
        self._timeline_cache_timestamp = 0
        if not any([data is not None, initpath, baseurl, token]):
            self._baseurl = CONFIG.get('auth.client_baseurl', 'http://localhost:32433')
            self._token = logfilter.add_secret(CONFIG.get('auth.client_token'))
        if connect and self._baseurl:
            self.connect(timeout=timeout)

    def _nextCommandId(self):
        self._commandId += 1
        return self._commandId

    def connect(self, timeout=None):
        """ Alias of reload as any subsequent requests to this client will be
            made directly to the device even if the object attributes were initially
            populated from a PlexServer.
        """
        if not self.key:
            raise Unsupported('Cannot reload an object not built from a URL.')
        self._initpath = self.key
        data = self.query(self.key, timeout=timeout)
        self._loadData(data[0])
        return self

    def reload(self):
        """ Alias to self.connect(). """
        return self.connect()

    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        self._data = data
        self.deviceClass = data.attrib.get('deviceClass')
        self.machineIdentifier = data.attrib.get('machineIdentifier')
        self.product = data.attrib.get('product')
        self.protocol = data.attrib.get('protocol')
        self.protocolCapabilities = data.attrib.get('protocolCapabilities', '').split(',')
        self.protocolVersion = data.attrib.get('protocolVersion')
        self.platform = data.attrib.get('platform')
        self.platformVersion = data.attrib.get('platformVersion')
        self.title = data.attrib.get('title') or data.attrib.get('name')
        # Active session details
        # Since protocolCapabilities is missing from /sessions we cant really control this player without
        # creating a client manually.
        # Add this in next breaking release.
        # if self._initpath == 'status/sessions':
        self.device = data.attrib.get('device')         # session
        self.model = data.attrib.get('model')           # session
        self.state = data.attrib.get('state')           # session
        self.vendor = data.attrib.get('vendor')         # session
        self.version = data.attrib.get('version')       # session
        self.local = utils.cast(bool, data.attrib.get('local', 0))
        self.address = data.attrib.get('address')        # session
        self.remotePublicAddress = data.attrib.get('remotePublicAddress')
        self.userID = data.attrib.get('userID')

    def _headers(self, **kwargs):
        """ Returns a dict of all default headers for Client requests. """
        headers = BASE_HEADERS
        if self._token:
            headers['X-Plex-Token'] = self._token
        headers.update(kwargs)
        return headers

    def proxyThroughServer(self, value=True, server=None):
        """ Tells this PlexClient instance to proxy all future commands through the PlexServer.
            Useful if you do not wish to connect directly to the Client device itself.

            Parameters:
                value (bool): Enable or disable proxying (optional, default True).

            Raises:
                :exc:`~plexapi.exceptions.Unsupported`: Cannot use client proxy with unknown server.
        """
        if server:
            self._server = server
        if value is True and not self._server:
            raise Unsupported('Cannot use client proxy with unknown server.')
        self._proxyThroughServer = value

    def query(self, path, method=None, headers=None, timeout=None, **kwargs):
        """ Main method used to handle HTTPS requests to the Plex client. This method helps
            by encoding the response to utf-8 and parsing the returned XML into and
            ElementTree object. Returns None if no data exists in the response.
        """
        url = self.url(path)
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

    def sendCommand(self, command, proxy=None, **params):
        """ Convenience wrapper around :func:`~plexapi.client.PlexClient.query` to more easily
            send simple commands to the client. Returns an ElementTree object containing
            the response.

            Parameters:
                command (str): Command to be sent in for format '<controller>/<command>'.
                proxy (bool): Set True to proxy this command through the PlexServer.
                **params (dict): Additional GET parameters to include with the command.

            Raises:
                :exc:`~plexapi.exceptions.Unsupported`: When we detect the client doesn't support this capability.
        """
        command = command.strip('/')
        controller = command.split('/')[0]
        headers = {'X-Plex-Target-Client-Identifier': self.machineIdentifier}
        if controller not in self.protocolCapabilities:
            log.debug('Client %s doesnt support %s controller.'
                      'What your trying might not work' % (self.title, controller))

        proxy = self._proxyThroughServer if proxy is None else proxy
        query = self._server.query if proxy else self.query

        # Workaround for ptp. See https://github.com/pkkid/python-plexapi/issues/244
        t = time.time()
        if command == 'timeline/poll':
            self._last_call = t
        elif t - self._last_call >= 80 and self.product in ('ptp', 'Plex Media Player'):
            self._last_call = t
            self.sendCommand(ClientTimeline.key, wait=0)

        params['commandID'] = self._nextCommandId()
        key = '/player/%s%s' % (command, utils.joinArgs(params))

        try:
            return query(key, headers=headers)
        except ElementTree.ParseError:
            # Workaround for players which don't return valid XML on successful commands
            #   - Plexamp, Plex for Android: `b'OK'`
            #   - Plex for Samsung: `b'<?xml version="1.0"?><Response code="200" status="OK">'`
            if self.product in (
                'Plexamp',
                'Plex for Android (TV)',
                'Plex for Android (Mobile)',
                'Plex for Samsung',
            ):
                return
            raise

    def url(self, key, includeToken=False):
        """ Build a URL string with proper token argument. Token will be appended to the URL
            if either includeToken is True or CONFIG.log.show_secrets is 'true'.
        """
        if not self._baseurl:
            raise BadRequest('PlexClient object missing baseurl.')
        if self._token and (includeToken or self._showSecrets):
            delim = '&' if '?' in key else '?'
            return '%s%s%sX-Plex-Token=%s' % (self._baseurl, key, delim, self._token)
        return '%s%s' % (self._baseurl, key)

    # ---------------------
    # Navigation Commands
    # These commands navigate around the user-interface.
    def contextMenu(self):
        """ Open the context menu on the client. """
        self.sendCommand('navigation/contextMenu')

    def goBack(self):
        """ Navigate back one position. """
        self.sendCommand('navigation/back')

    def goToHome(self):
        """ Go directly to the home screen. """
        self.sendCommand('navigation/home')

    def goToMusic(self):
        """ Go directly to the playing music panel. """
        self.sendCommand('navigation/music')

    def moveDown(self):
        """ Move selection down a position. """
        self.sendCommand('navigation/moveDown')

    def moveLeft(self):
        """ Move selection left a position. """
        self.sendCommand('navigation/moveLeft')

    def moveRight(self):
        """ Move selection right a position. """
        self.sendCommand('navigation/moveRight')

    def moveUp(self):
        """ Move selection up a position. """
        self.sendCommand('navigation/moveUp')

    def nextLetter(self):
        """ Jump to next letter in the alphabet. """
        self.sendCommand('navigation/nextLetter')

    def pageDown(self):
        """ Move selection down a full page. """
        self.sendCommand('navigation/pageDown')

    def pageUp(self):
        """ Move selection up a full page. """
        self.sendCommand('navigation/pageUp')

    def previousLetter(self):
        """ Jump to previous letter in the alphabet. """
        self.sendCommand('navigation/previousLetter')

    def select(self):
        """ Select element at the current position. """
        self.sendCommand('navigation/select')

    def toggleOSD(self):
        """ Toggle the on screen display during playback. """
        self.sendCommand('navigation/toggleOSD')

    def goToMedia(self, media, **params):
        """ Navigate directly to the specified media page.

            Parameters:
                media (:class:`~plexapi.media.Media`): Media object to navigate to.
                **params (dict): Additional GET parameters to include with the command.

            Raises:
                :exc:`~plexapi.exceptions.Unsupported`: When no PlexServer specified in this object.
        """
        if not self._server:
            raise Unsupported('A server must be specified before using this command.')
        server_url = media._server._baseurl.split(':')
        self.sendCommand('mirror/details', **dict({
            'machineIdentifier': self._server.machineIdentifier,
            'address': server_url[1].strip('/'),
            'port': server_url[-1],
            'key': media.key,
            'protocol': server_url[0],
            'token': media._server.createToken()
        }, **params))

    # -------------------
    # Playback Commands
    # Most of the playback commands take a mandatory mtype {'music','photo','video'} argument,
    # to specify which media type to apply the command to, (except for playMedia). This
    # is in case there are multiple things happening (e.g. music in the background, photo
    # slideshow in the foreground).
    def pause(self, mtype=DEFAULT_MTYPE):
        """ Pause the currently playing media type.

            Parameters:
                mtype (str): Media type to take action against (music, photo, video).
        """
        self.sendCommand('playback/pause', type=mtype)

    def play(self, mtype=DEFAULT_MTYPE):
        """ Start playback for the specified media type.

            Parameters:
                mtype (str): Media type to take action against (music, photo, video).
        """
        self.sendCommand('playback/play', type=mtype)

    def refreshPlayQueue(self, playQueueID, mtype=DEFAULT_MTYPE):
        """ Refresh the specified Playqueue.

            Parameters:
                playQueueID (str): Playqueue ID.
                mtype (str): Media type to take action against (music, photo, video).
        """
        self.sendCommand(
            'playback/refreshPlayQueue', playQueueID=playQueueID, type=mtype)

    def seekTo(self, offset, mtype=DEFAULT_MTYPE):
        """ Seek to the specified offset (ms) during playback.

            Parameters:
                offset (int): Position to seek to (milliseconds).
                mtype (str): Media type to take action against (music, photo, video).
        """
        self.sendCommand('playback/seekTo', offset=offset, type=mtype)

    def skipNext(self, mtype=DEFAULT_MTYPE):
        """ Skip to the next playback item.

            Parameters:
                mtype (str): Media type to take action against (music, photo, video).
        """
        self.sendCommand('playback/skipNext', type=mtype)

    def skipPrevious(self, mtype=DEFAULT_MTYPE):
        """ Skip to previous playback item.

            Parameters:
                mtype (str): Media type to take action against (music, photo, video).
        """
        self.sendCommand('playback/skipPrevious', type=mtype)

    def skipTo(self, key, mtype=DEFAULT_MTYPE):
        """ Skip to the playback item with the specified key.

            Parameters:
                key (str): Key of the media item to skip to.
                mtype (str): Media type to take action against (music, photo, video).
        """
        self.sendCommand('playback/skipTo', key=key, type=mtype)

    def stepBack(self, mtype=DEFAULT_MTYPE):
        """ Step backward a chunk of time in the current playback item.

            Parameters:
                mtype (str): Media type to take action against (music, photo, video).
        """
        self.sendCommand('playback/stepBack', type=mtype)

    def stepForward(self, mtype=DEFAULT_MTYPE):
        """ Step forward a chunk of time in the current playback item.

            Parameters:
                mtype (str): Media type to take action against (music, photo, video).
        """
        self.sendCommand('playback/stepForward', type=mtype)

    def stop(self, mtype=DEFAULT_MTYPE):
        """ Stop the currently playing item.

            Parameters:
                mtype (str): Media type to take action against (music, photo, video).
        """
        self.sendCommand('playback/stop', type=mtype)

    def setRepeat(self, repeat, mtype=DEFAULT_MTYPE):
        """ Enable repeat for the specified playback items.

            Parameters:
                repeat (int): Repeat mode (0=off, 1=repeatone, 2=repeatall).
                mtype (str): Media type to take action against (music, photo, video).
        """
        self.setParameters(repeat=repeat, mtype=mtype)

    def setShuffle(self, shuffle, mtype=DEFAULT_MTYPE):
        """ Enable shuffle for the specified playback items.

            Parameters:
                shuffle (int): Shuffle mode (0=off, 1=on)
                mtype (str): Media type to take action against (music, photo, video).
        """
        self.setParameters(shuffle=shuffle, mtype=mtype)

    def setVolume(self, volume, mtype=DEFAULT_MTYPE):
        """ Enable volume for the current playback item.

            Parameters:
                volume (int): Volume level (0-100).
                mtype (str): Media type to take action against (music, photo, video).
        """
        self.setParameters(volume=volume, mtype=mtype)

    def setAudioStream(self, audioStreamID, mtype=DEFAULT_MTYPE):
        """ Select the audio stream for the current playback item (only video).

            Parameters:
                audioStreamID (str): ID of the audio stream from the media object.
                mtype (str): Media type to take action against (music, photo, video).
        """
        self.setStreams(audioStreamID=audioStreamID, mtype=mtype)

    def setSubtitleStream(self, subtitleStreamID, mtype=DEFAULT_MTYPE):
        """ Select the subtitle stream for the current playback item (only video).

            Parameters:
                subtitleStreamID (str): ID of the subtitle stream from the media object.
                mtype (str): Media type to take action against (music, photo, video).
        """
        self.setStreams(subtitleStreamID=subtitleStreamID, mtype=mtype)

    def setVideoStream(self, videoStreamID, mtype=DEFAULT_MTYPE):
        """ Select the video stream for the current playback item (only video).

            Parameters:
                videoStreamID (str): ID of the video stream from the media object.
                mtype (str): Media type to take action against (music, photo, video).
        """
        self.setStreams(videoStreamID=videoStreamID, mtype=mtype)

    def playMedia(self, media, offset=0, **params):
        """ Start playback of the specified media item. See also:

            Parameters:
                media (:class:`~plexapi.media.Media`): Media item to be played back
                    (movie, music, photo, playlist, playqueue).
                offset (int): Number of milliseconds at which to start playing with zero
                    representing the beginning (default 0).
                **params (dict): Optional additional parameters to include in the playback request. See
                    also: https://github.com/plexinc/plex-media-player/wiki/Remote-control-API#modified-commands

            Raises:
                :exc:`~plexapi.exceptions.Unsupported`: When no PlexServer specified in this object.
        """
        if not self._server:
            raise Unsupported('A server must be specified before using this command.')
        server_url = media._server._baseurl.split(':')
        server_port = server_url[-1].strip('/')

        if hasattr(media, "playlistType"):
            mediatype = media.playlistType
        else:
            if isinstance(media, PlayQueue):
                mediatype = media.items[0].listType
            else:
                mediatype = media.listType

        # mediatype must be in ["video", "music", "photo"]
        if mediatype == "audio":
            mediatype = "music"

        playqueue = media if isinstance(media, PlayQueue) else self._server.createPlayQueue(media)
        self.sendCommand('playback/playMedia', **dict({
            'machineIdentifier': self._server.machineIdentifier,
            'address': server_url[1].strip('/'),
            'port': server_port,
            'offset': offset,
            'key': media.key,
            'token': media._server.createToken(),
            'type': mediatype,
            'containerKey': '/playQueues/%s?window=100&own=1' % playqueue.playQueueID,
        }, **params))

    def setParameters(self, volume=None, shuffle=None, repeat=None, mtype=DEFAULT_MTYPE):
        """ Set multiple playback parameters at once.

            Parameters:
                volume (int): Volume level (0-100; optional).
                shuffle (int): Shuffle mode (0=off, 1=on; optional).
                repeat (int): Repeat mode (0=off, 1=repeatone, 2=repeatall; optional).
                mtype (str): Media type to take action against (optional music, photo, video).
        """
        params = {}
        if repeat is not None:
            params['repeat'] = repeat
        if shuffle is not None:
            params['shuffle'] = shuffle
        if volume is not None:
            params['volume'] = volume
        if mtype is not None:
            params['type'] = mtype
        self.sendCommand('playback/setParameters', **params)

    def setStreams(self, audioStreamID=None, subtitleStreamID=None, videoStreamID=None, mtype=DEFAULT_MTYPE):
        """ Select multiple playback streams at once.

            Parameters:
                audioStreamID (str): ID of the audio stream from the media object.
                subtitleStreamID (str): ID of the subtitle stream from the media object.
                videoStreamID (str): ID of the video stream from the media object.
                mtype (str): Media type to take action against (optional music, photo, video).
        """
        params = {}
        if audioStreamID is not None:
            params['audioStreamID'] = audioStreamID
        if subtitleStreamID is not None:
            params['subtitleStreamID'] = subtitleStreamID
        if videoStreamID is not None:
            params['videoStreamID'] = videoStreamID
        if mtype is not None:
            params['type'] = mtype
        self.sendCommand('playback/setStreams', **params)

    # -------------------
    # Timeline Commands
    def timelines(self, wait=0):
        """Poll the client's timelines, create, and return timeline objects.
           Some clients may not always respond to timeline requests, believe this
           to be a Plex bug.
        """
        t = time.time()
        if t - self._timeline_cache_timestamp > 1:
            self._timeline_cache_timestamp = t
            timelines = self.sendCommand(ClientTimeline.key, wait=wait) or []
            self._timeline_cache = [ClientTimeline(self, data) for data in timelines]

        return self._timeline_cache

    @property
    def timeline(self):
        """Returns the active timeline object."""
        return next((x for x in self.timelines() if x.state != 'stopped'), None)

    def isPlayingMedia(self, includePaused=True):
        """Returns True if any media is currently playing.

            Parameters:
                includePaused (bool): Set True to treat currently paused items
                                      as playing (optional; default True).
        """
        state = getattr(self.timeline, "state", None)
        return bool(state == 'playing' or (includePaused and state == 'paused'))


class ClientTimeline(PlexObject):
    """Get the timeline's attributes."""

    key = 'timeline/poll'

    def _loadData(self, data):
        self._data = data
        self.address = data.attrib.get('address')
        self.audioStreamId = utils.cast(int, data.attrib.get('audioStreamId'))
        self.autoPlay = utils.cast(bool, data.attrib.get('autoPlay'))
        self.containerKey = data.attrib.get('containerKey')
        self.controllable = data.attrib.get('controllable')
        self.duration = utils.cast(int, data.attrib.get('duration'))
        self.itemType = data.attrib.get('itemType')
        self.key = data.attrib.get('key')
        self.location = data.attrib.get('location')
        self.machineIdentifier = data.attrib.get('machineIdentifier')
        self.partCount = utils.cast(int, data.attrib.get('partCount'))
        self.partIndex = utils.cast(int, data.attrib.get('partIndex'))
        self.playQueueID = utils.cast(int, data.attrib.get('playQueueID'))
        self.playQueueItemID = utils.cast(int, data.attrib.get('playQueueItemID'))
        self.playQueueVersion = utils.cast(int, data.attrib.get('playQueueVersion'))
        self.port = utils.cast(int, data.attrib.get('port'))
        self.protocol = data.attrib.get('protocol')
        self.providerIdentifier = data.attrib.get('providerIdentifier')
        self.ratingKey = utils.cast(int, data.attrib.get('ratingKey'))
        self.repeat = utils.cast(bool, data.attrib.get('repeat'))
        self.seekRange = data.attrib.get('seekRange')
        self.shuffle = utils.cast(bool, data.attrib.get('shuffle'))
        self.state = data.attrib.get('state')
        self.subtitleColor = data.attrib.get('subtitleColor')
        self.subtitlePosition = data.attrib.get('subtitlePosition')
        self.subtitleSize = utils.cast(int, data.attrib.get('subtitleSize'))
        self.time = utils.cast(int, data.attrib.get('time'))
        self.type = data.attrib.get('type')
        self.volume = utils.cast(int, data.attrib.get('volume'))
