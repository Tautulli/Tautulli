# -*- coding: utf-8 -*-
import requests
from plexapi import CONFIG, X_PLEX_IDENTIFIER
from plexapi.client import PlexClient
from plexapi.exceptions import BadRequest
from plexapi.playqueue import PlayQueue


class PlexSonosClient(PlexClient):
    """ Class for interacting with a Sonos speaker via the Plex API. This class
        makes requests to an external Plex API which then forwards the
        Sonos-specific commands back to your Plex server & Sonos speakers. Use
        of this feature requires an active Plex Pass subscription and Sonos
        speakers linked to your Plex account. It also requires remote access to
        be working properly.

        More details on the Sonos integration are available here:
        https://support.plex.tv/articles/218237558-requirements-for-using-plex-for-sonos/

        The Sonos API emulates the Plex player control API closely:
        https://github.com/plexinc/plex-media-player/wiki/Remote-control-API

        Parameters:
            account (:class:`~plexapi.myplex.PlexAccount`): PlexAccount instance this
                Sonos speaker is associated with.
            data (ElementTree): Response from Plex Sonos API used to build this client.

        Attributes:
            deviceClass (str): "speaker"
            lanIP (str): Local IP address of speaker.
            machineIdentifier (str): Unique ID for this device.
            platform (str): "Sonos"
            platformVersion (str): Build version of Sonos speaker firmware.
            product (str): "Sonos"
            protocol (str): "plex"
            protocolCapabilities (list<str>): List of client capabilities (timeline, playback,
                playqueues, provider-playback)
            server (:class:`~plexapi.server.PlexServer`): Server this client is connected to.
            session (:class:`~requests.Session`): Session object used for connection.
            title (str): Name of this Sonos speaker.
            token (str): X-Plex-Token used for authentication
            _baseurl (str): Address of public Plex Sonos API endpoint.
            _commandId (int): Counter for commands sent to Plex API.
            _token (str): Token associated with linked Plex account.
            _session (obj): Requests session object used to access this client.
    """

    def __init__(self, account, data):
        self._data = data
        self.deviceClass = data.attrib.get("deviceClass")
        self.machineIdentifier = data.attrib.get("machineIdentifier")
        self.product = data.attrib.get("product")
        self.platform = data.attrib.get("platform")
        self.platformVersion = data.attrib.get("platformVersion")
        self.protocol = data.attrib.get("protocol")
        self.protocolCapabilities = data.attrib.get("protocolCapabilities")
        self.lanIP = data.attrib.get("lanIP")
        self.title = data.attrib.get("title")
        self._baseurl = "https://sonos.plex.tv"
        self._commandId = 0
        self._token = account._token
        self._session = account._session or requests.Session()

        # Dummy values for PlexClient inheritance
        self._last_call = 0
        self._proxyThroughServer = False
        self._showSecrets = CONFIG.get("log.show_secrets", "").lower() == "true"

    def playMedia(self, media, offset=0, **params):

        if hasattr(media, "playlistType"):
            mediatype = media.playlistType
        else:
            if isinstance(media, PlayQueue):
                mediatype = media.items[0].listType
            else:
                mediatype = media.listType

        if mediatype == "audio":
            mediatype = "music"
        else:
            raise BadRequest("Sonos currently only supports music for playback")

        server_protocol, server_address, server_port = media._server._baseurl.split(":")
        server_address = server_address.strip("/")
        server_port = server_port.strip("/")

        playqueue = (
            media
            if isinstance(media, PlayQueue)
            else media._server.createPlayQueue(media)
        )
        self.sendCommand(
            "playback/playMedia",
            **dict(
                {
                    "type": "music",
                    "providerIdentifier": "com.plexapp.plugins.library",
                    "containerKey": "/playQueues/{}?own=1".format(
                        playqueue.playQueueID
                    ),
                    "key": media.key,
                    "offset": offset,
                    "machineIdentifier": media._server.machineIdentifier,
                    "protocol": server_protocol,
                    "address": server_address,
                    "port": server_port,
                    "token": media._server.createToken(),
                    "commandID": self._nextCommandId(),
                    "X-Plex-Client-Identifier": X_PLEX_IDENTIFIER,
                    "X-Plex-Token": media._server._token,
                    "X-Plex-Target-Client-Identifier": self.machineIdentifier,
                },
                **params
            )
        )
