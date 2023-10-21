# -*- coding: utf-8 -*-
"""
You can work with Mobile Sync on other devices straight away, but if you'd like to use your app as a `sync-target` (when
you can set items to be synced to your app) you need to init some variables.

.. code-block:: python

    def init_sync():
        import plexapi
        plexapi.X_PLEX_PROVIDES = 'sync-target'
        plexapi.BASE_HEADERS['X-Plex-Sync-Version'] = '2'
        plexapi.BASE_HEADERS['X-Plex-Provides'] = plexapi.X_PLEX_PROVIDES

        # mimic iPhone SE
        plexapi.X_PLEX_PLATFORM = 'iOS'
        plexapi.X_PLEX_PLATFORM_VERSION = '11.4.1'
        plexapi.X_PLEX_DEVICE = 'iPhone'

        plexapi.BASE_HEADERS['X-Plex-Platform'] = plexapi.X_PLEX_PLATFORM
        plexapi.BASE_HEADERS['X-Plex-Platform-Version'] = plexapi.X_PLEX_PLATFORM_VERSION
        plexapi.BASE_HEADERS['X-Plex-Device'] = plexapi.X_PLEX_DEVICE

You have to fake platform/device/model because transcoding profiles are hardcoded in Plex, and you obviously have
to explicitly specify that your app supports `sync-target`.
"""
import requests

import plexapi
from plexapi.base import PlexObject
from plexapi.exceptions import NotFound, BadRequest


class SyncItem(PlexObject):
    """
    Represents single sync item, for specified server and client. When you saying in the UI to sync "this" to "that"
    you're basically creating a sync item.

    Attributes:
        id (int): unique id of the item.
        clientIdentifier (str): an identifier of Plex Client device, to which the item is belongs.
        machineIdentifier (str): the id of server which holds all this content.
        version (int): current version of the item. Each time you modify the item (e.g. by changing amount if media to
                       sync) the new version is created.
        rootTitle (str): the title of library/media from which the sync item was created. E.g.:

            * when you create an item for an episode 3 of season 3 of show Example, the value would be `Title of
              Episode 3`
            * when you create an item for a season 3 of show Example, the value would be `Season 3`
            * when you set to sync all your movies in library named "My Movies" to value would be `My Movies`.

        title (str): the title which you've set when created the sync item.
        metadataType (str): the type of media which hides inside, can be `episode`, `movie`, etc.
        contentType (str): basic type of the content: `video` or `audio`.
        status (:class:`~plexapi.sync.Status`): current status of the sync.
        mediaSettings (:class:`~plexapi.sync.MediaSettings`): media transcoding settings used for the item.
        policy (:class:`~plexapi.sync.Policy`): the policy of which media to sync.
        location (str): plex-style library url with all required filters / sorting.
    """
    TAG = 'SyncItem'

    def __init__(self, server, data, initpath=None, clientIdentifier=None):
        super(SyncItem, self).__init__(server, data, initpath)
        self.clientIdentifier = clientIdentifier

    def _loadData(self, data):
        self._data = data
        self.id = plexapi.utils.cast(int, data.attrib.get('id'))
        self.version = plexapi.utils.cast(int, data.attrib.get('version'))
        self.rootTitle = data.attrib.get('rootTitle')
        self.title = data.attrib.get('title')
        self.metadataType = data.attrib.get('metadataType')
        self.contentType = data.attrib.get('contentType')
        self.machineIdentifier = data.find('Server').get('machineIdentifier')
        self.status = Status(**data.find('Status').attrib)
        self.mediaSettings = MediaSettings(**data.find('MediaSettings').attrib)
        self.policy = Policy(**data.find('Policy').attrib)
        self.location = data.find('Location').attrib.get('uri', '')

    def server(self):
        """ Returns :class:`~plexapi.myplex.MyPlexResource` with server of current item. """
        server = [s for s in self._server.resources() if s.clientIdentifier == self.machineIdentifier]
        if len(server) == 0:
            raise NotFound(f'Unable to find server with uuid {self.machineIdentifier}')
        return server[0]

    def getMedia(self):
        """ Returns list of :class:`~plexapi.base.Playable` which belong to this sync item. """
        server = self.server().connect()
        key = f'/sync/items/{self.id}'
        return server.fetchItems(key)

    def markDownloaded(self, media):
        """ Mark the file as downloaded (by the nature of Plex it will be marked as downloaded within
            any SyncItem where it presented).

            Parameters:
                media (base.Playable): the media to be marked as downloaded.
        """
        url = f'/sync/{self.clientIdentifier}/item/{media.ratingKey}/downloaded'
        media._server.query(url, method=requests.put)

    def delete(self):
        """ Removes current SyncItem """
        url = SyncList.key.format(clientId=self.clientIdentifier)
        url += '/' + str(self.id)
        self._server.query(url, self._server._session.delete)


class SyncList(PlexObject):
    """ Represents a Mobile Sync state, specific for single client, within one SyncList may be presented
        items from different servers.

        Attributes:
            clientId (str): an identifier of the client.
            items (List<:class:`~plexapi.sync.SyncItem`>): list of registered items to sync.
    """
    key = 'https://plex.tv/devices/{clientId}/sync_items'
    TAG = 'SyncList'

    def _loadData(self, data):
        self._data = data
        self.clientId = data.attrib.get('clientIdentifier')
        self.items = []

        syncItems = data.find('SyncItems')
        if syncItems:
            for sync_item in syncItems.iter('SyncItem'):
                item = SyncItem(self._server, sync_item, clientIdentifier=self.clientId)
                self.items.append(item)


class Status:
    """ Represents a current status of specific :class:`~plexapi.sync.SyncItem`.

        Attributes:
            failureCode: unknown, never got one yet.
            failure: unknown.
            state (str): server-side status of the item, can be `completed`, `pending`, empty, and probably something
                         else.
            itemsCount (int): total items count.
            itemsCompleteCount (int): count of transcoded and/or downloaded items.
            itemsDownloadedCount (int): count of downloaded items.
            itemsReadyCount (int): count of transcoded items, which can be downloaded.
            totalSize (int): total size in bytes of complete items.
            itemsSuccessfulCount (int): unknown, in my experience it always was equal to `itemsCompleteCount`.
    """

    def __init__(self, itemsCount, itemsCompleteCount, state, totalSize, itemsDownloadedCount, itemsReadyCount,
                 itemsSuccessfulCount, failureCode, failure):
        self.itemsDownloadedCount = plexapi.utils.cast(int, itemsDownloadedCount)
        self.totalSize = plexapi.utils.cast(int, totalSize)
        self.itemsReadyCount = plexapi.utils.cast(int, itemsReadyCount)
        self.failureCode = failureCode
        self.failure = failure
        self.itemsSuccessfulCount = plexapi.utils.cast(int, itemsSuccessfulCount)
        self.state = state
        self.itemsCompleteCount = plexapi.utils.cast(int, itemsCompleteCount)
        self.itemsCount = plexapi.utils.cast(int, itemsCount)

    def __repr__(self):
        d = dict(
            itemsCount=self.itemsCount,
            itemsCompleteCount=self.itemsCompleteCount,
            itemsDownloadedCount=self.itemsDownloadedCount,
            itemsReadyCount=self.itemsReadyCount,
            itemsSuccessfulCount=self.itemsSuccessfulCount
        )
        return f'<{self.__class__.__name__}>:{d}'


class MediaSettings:
    """ Transcoding settings used for all media within :class:`~plexapi.sync.SyncItem`.

        Attributes:
            audioBoost (int): unknown.
            maxVideoBitrate (int|str): maximum bitrate for video, may be empty string.
            musicBitrate (int|str): maximum bitrate for music, may be an empty string.
            photoQuality (int): photo quality on scale 0 to 100.
            photoResolution (str): maximum photo resolution, formatted as WxH (e.g. `1920x1080`).
            videoResolution (str): maximum video resolution, formatted as WxH (e.g. `1280x720`, may be empty).
            subtitleSize (int): subtitle size on scale 0 to 100.
            videoQuality (int): video quality on scale 0 to 100.
    """

    def __init__(self, maxVideoBitrate=4000, videoQuality=100, videoResolution='1280x720', audioBoost=100,
                 musicBitrate=192, photoQuality=74, photoResolution='1920x1080', subtitleSize=100):
        self.audioBoost = plexapi.utils.cast(int, audioBoost)
        self.maxVideoBitrate = plexapi.utils.cast(int, maxVideoBitrate) if maxVideoBitrate != '' else ''
        self.musicBitrate = plexapi.utils.cast(int, musicBitrate) if musicBitrate != '' else ''
        self.photoQuality = plexapi.utils.cast(int, photoQuality) if photoQuality != '' else ''
        self.photoResolution = photoResolution
        self.videoResolution = videoResolution
        self.subtitleSize = plexapi.utils.cast(int, subtitleSize) if subtitleSize != '' else ''
        self.videoQuality = plexapi.utils.cast(int, videoQuality) if videoQuality != '' else ''

    @staticmethod
    def createVideo(videoQuality):
        """ Returns a :class:`~plexapi.sync.MediaSettings` object, based on provided video quality value.

            Parameters:
                videoQuality (int): idx of quality of the video, one of VIDEO_QUALITY_* values defined in this module.

            Raises:
                :exc:`~plexapi.exceptions.BadRequest`: When provided unknown video quality.
        """
        if videoQuality == VIDEO_QUALITY_ORIGINAL:
            return MediaSettings('', '', '')
        elif videoQuality < len(VIDEO_QUALITIES['bitrate']):
            return MediaSettings(VIDEO_QUALITIES['bitrate'][videoQuality],
                                 VIDEO_QUALITIES['videoQuality'][videoQuality],
                                 VIDEO_QUALITIES['videoResolution'][videoQuality])
        else:
            raise BadRequest('Unexpected video quality')

    @staticmethod
    def createMusic(bitrate):
        """ Returns a :class:`~plexapi.sync.MediaSettings` object, based on provided music quality value

            Parameters:
                bitrate (int): maximum bitrate for synchronized music, better use one of MUSIC_BITRATE_* values from the
                               module
        """
        return MediaSettings(musicBitrate=bitrate)

    @staticmethod
    def createPhoto(resolution):
        """ Returns a :class:`~plexapi.sync.MediaSettings` object, based on provided photo quality value.

            Parameters:
                resolution (str): maximum allowed resolution for synchronized photos, see PHOTO_QUALITY_* values in the
                                  module.

            Raises:
                :exc:`~plexapi.exceptions.BadRequest`: When provided unknown video quality.
        """
        if resolution in PHOTO_QUALITIES:
            return MediaSettings(photoQuality=PHOTO_QUALITIES[resolution], photoResolution=resolution)
        else:
            raise BadRequest('Unexpected photo quality')


class Policy:
    """ Policy of syncing the media (how many items to sync and process watched media or not).

        Attributes:
            scope (str): type of limitation policy, can be `count` or `all`.
            value (int): amount of media to sync, valid only when `scope=count`.
            unwatched (bool): True means disallow to sync watched media.
    """

    def __init__(self, scope, unwatched, value=0):
        self.scope = scope
        self.unwatched = plexapi.utils.cast(bool, unwatched)
        self.value = plexapi.utils.cast(int, value)

    @staticmethod
    def create(limit=None, unwatched=False):
        """ Creates a :class:`~plexapi.sync.Policy` object for provided options and automatically sets proper `scope`
            value.

            Parameters:
                limit (int): limit items by count.
                unwatched (bool): if True then watched items wouldn't be synced.

            Returns:
                :class:`~plexapi.sync.Policy`.
        """
        scope = 'all'
        if limit is None:
            limit = 0
        else:
            scope = 'count'

        return Policy(scope, unwatched, limit)


VIDEO_QUALITIES = {
    'bitrate': [64, 96, 208, 320, 720, 1500, 2e3, 3e3, 4e3, 8e3, 1e4, 12e3, 2e4],
    'videoResolution': ['220x128', '220x128', '284x160', '420x240', '576x320', '720x480', '1280x720', '1280x720',
                        '1280x720', '1920x1080', '1920x1080', '1920x1080', '1920x1080'],
    'videoQuality': [10, 20, 30, 30, 40, 60, 60, 75, 100, 60, 75, 90, 100],
}

VIDEO_QUALITY_0_2_MBPS = 2
VIDEO_QUALITY_0_3_MBPS = 3
VIDEO_QUALITY_0_7_MBPS = 4
VIDEO_QUALITY_1_5_MBPS_480p = 5
VIDEO_QUALITY_2_MBPS_720p = 6
VIDEO_QUALITY_3_MBPS_720p = 7
VIDEO_QUALITY_4_MBPS_720p = 8
VIDEO_QUALITY_8_MBPS_1080p = 9
VIDEO_QUALITY_10_MBPS_1080p = 10
VIDEO_QUALITY_12_MBPS_1080p = 11
VIDEO_QUALITY_20_MBPS_1080p = 12
VIDEO_QUALITY_ORIGINAL = -1

AUDIO_BITRATE_96_KBPS = 96
AUDIO_BITRATE_128_KBPS = 128
AUDIO_BITRATE_192_KBPS = 192
AUDIO_BITRATE_320_KBPS = 320

PHOTO_QUALITIES = {
    '720x480': 24,
    '1280x720': 49,
    '1920x1080': 74,
    '3840x2160': 99,
}

PHOTO_QUALITY_HIGHEST = PHOTO_QUALITY_2160p = '3840x2160'
PHOTO_QUALITY_HIGH = PHOTO_QUALITY_1080p = '1920x1080'
PHOTO_QUALITY_MEDIUM = PHOTO_QUALITY_720p = '1280x720'
PHOTO_QUALITY_LOW = PHOTO_QUALITY_480p = '720x480'
