# -*- coding: utf-8 -*-
from urllib.parse import quote_plus

from plexapi import utils
from plexapi.base import Playable, PlexPartialObject
from plexapi.exceptions import BadRequest, NotFound, Unsupported
from plexapi.library import LibrarySection
from plexapi.playqueue import PlayQueue
from plexapi.utils import cast, toDatetime


@utils.registerPlexObject
class Playlist(PlexPartialObject, Playable):
    """ Represents a single Playlist.

        Attributes:
            TAG (str): 'Playlist'
            TYPE (str): 'playlist'
            addedAt (datetime): Datetime the playlist was added to the server.
            allowSync (bool): True if you allow syncing playlists.
            composite (str): URL to composite image (/playlist/<ratingKey>/composite/<compositeid>)
            duration (int): Duration of the playlist in milliseconds.
            durationInSeconds (int): Duration of the playlist in seconds.
            guid (str): Plex GUID for the playlist (com.plexapp.agents.none://XXXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXX).
            key (str): API URL (/playlist/<ratingkey>).
            leafCount (int): Number of items in the playlist view.
            playlistType (str): 'audio', 'video', or 'photo'
            ratingKey (int): Unique key identifying the playlist.
            smart (bool): True if the playlist is a smart playlist.
            summary (str): Summary of the playlist.
            title (str): Name of the playlist.
            type (str): 'playlist'
            updatedAt (datatime): Datetime the playlist was updated.
    """
    TAG = 'Playlist'
    TYPE = 'playlist'

    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        Playable._loadData(self, data)
        self.addedAt = toDatetime(data.attrib.get('addedAt'))
        self.allowSync = cast(bool, data.attrib.get('allowSync'))
        self.composite = data.attrib.get('composite')  # url to thumbnail
        self.duration = cast(int, data.attrib.get('duration'))
        self.durationInSeconds = cast(int, data.attrib.get('durationInSeconds'))
        self.guid = data.attrib.get('guid')
        self.key = data.attrib.get('key', '').replace('/items', '')  # FIX_BUG_50
        self.leafCount = cast(int, data.attrib.get('leafCount'))
        self.playlistType = data.attrib.get('playlistType')
        self.ratingKey = cast(int, data.attrib.get('ratingKey'))
        self.smart = cast(bool, data.attrib.get('smart'))
        self.summary = data.attrib.get('summary')
        self.title = data.attrib.get('title')
        self.type = data.attrib.get('type')
        self.updatedAt = toDatetime(data.attrib.get('updatedAt'))
        self._items = None  # cache for self.items

    def __len__(self):  # pragma: no cover
        return len(self.items())

    def __iter__(self):  # pragma: no cover
        for item in self.items():
            yield item

    @property
    def metadataType(self):
        if self.isVideo:
            return 'movie'
        elif self.isAudio:
            return 'track'
        elif self.isPhoto:
            return 'photo'
        else:
            raise Unsupported('Unexpected playlist type')

    @property
    def isVideo(self):
        return self.playlistType == 'video'

    @property
    def isAudio(self):
        return self.playlistType == 'audio'

    @property
    def isPhoto(self):
        return self.playlistType == 'photo'

    def __contains__(self, other):  # pragma: no cover
        return any(i.key == other.key for i in self.items())

    def __getitem__(self, key):  # pragma: no cover
        return self.items()[key]

    def item(self, title):
        """ Returns the item in the playlist that matches the specified title.

            Parameters:
                title (str): Title of the item to return.
        """
        for item in self.items():
            if item.title.lower() == title.lower():
                return item
        raise NotFound('Item with title "%s" not found in the playlist' % title)

    def items(self):
        """ Returns a list of all items in the playlist. """
        if self._items is None:
            key = '/playlists/%s/items' % self.ratingKey
            items = self.fetchItems(key)
            self._items = items
        return self._items

    def get(self, title):
        """ Alias to :func:`~plexapi.playlist.Playlist.item`. """
        return self.item(title)

    def addItems(self, items):
        """ Add items to a playlist. """
        if not isinstance(items, (list, tuple)):
            items = [items]
        ratingKeys = []
        for item in items:
            if item.listType != self.playlistType:  # pragma: no cover
                raise BadRequest('Can not mix media types when building a playlist: %s and %s' %
                    (self.playlistType, item.listType))
            ratingKeys.append(str(item.ratingKey))
        uuid = items[0].section().uuid
        ratingKeys = ','.join(ratingKeys)
        key = '%s/items%s' % (self.key, utils.joinArgs({
            'uri': 'library://%s/directory//library/metadata/%s' % (uuid, ratingKeys)
        }))
        result = self._server.query(key, method=self._server._session.put)
        self.reload()
        return result

    def removeItem(self, item):
        """ Remove a file from a playlist. """
        key = '%s/items/%s' % (self.key, item.playlistItemID)
        result = self._server.query(key, method=self._server._session.delete)
        self.reload()
        return result

    def moveItem(self, item, after=None):
        """ Move a to a new position in playlist. """
        key = '%s/items/%s/move' % (self.key, item.playlistItemID)
        if after:
            key += '?after=%s' % after.playlistItemID
        result = self._server.query(key, method=self._server._session.put)
        self.reload()
        return result

    def edit(self, title=None, summary=None):
        """ Edit playlist. """
        key = '/library/metadata/%s%s' % (self.ratingKey, utils.joinArgs({'title': title, 'summary': summary}))
        result = self._server.query(key, method=self._server._session.put)
        self.reload()
        return result

    def delete(self):
        """ Delete playlist. """
        return self._server.query(self.key, method=self._server._session.delete)

    def playQueue(self, *args, **kwargs):
        """ Create a playqueue from this playlist. """
        return PlayQueue.create(self._server, self, *args, **kwargs)

    @classmethod
    def _create(cls, server, title, items):
        """ Create a playlist. """
        if not items:
            raise BadRequest('Must include items to add when creating new playlist')
            
        if items and not isinstance(items, (list, tuple)):
            items = [items]
        ratingKeys = []
        for item in items:
            if item.listType != items[0].listType:  # pragma: no cover
                raise BadRequest('Can not mix media types when building a playlist')
            ratingKeys.append(str(item.ratingKey))
        ratingKeys = ','.join(ratingKeys)
        uuid = items[0].section().uuid
        key = '/playlists%s' % utils.joinArgs({
            'uri': 'library://%s/directory//library/metadata/%s' % (uuid, ratingKeys),
            'type': items[0].listType,
            'title': title,
            'smart': 0
        })
        data = server.query(key, method=server._session.post)[0]
        return cls(server, data, initpath=key)

    @classmethod
    def create(cls, server, title, items=None, section=None, limit=None, smart=False, **kwargs):
        """Create a playlist.

        Parameters:
            server (:class:`~plexapi.server.PlexServer`): Server your connected to.
            title (str): Title of the playlist.
            items (Iterable): Iterable of objects that should be in the playlist.
            section (:class:`~plexapi.library.LibrarySection`, str):
            limit (int): default None.
            smart (bool): default False.

            **kwargs (dict): is passed to the filters. For a example see the search method.
            
        Raises:
            :class:`plexapi.exceptions.BadRequest`: when no items are included in create request.

        Returns:
            :class:`~plexapi.playlist.Playlist`: an instance of created Playlist.
        """
        if smart:
            return cls._createSmart(server, title, section, limit, **kwargs)

        else:
            return cls._create(server, title, items)

    @classmethod
    def _createSmart(cls, server, title, section, limit=None, **kwargs):
        """ Create a Smart playlist. """

        if not isinstance(section, LibrarySection):
            section = server.library.section(section)

        sectionType = utils.searchType(section.type)
        sectionId = section.key
        uuid = section.uuid
        uri = 'library://%s/directory//library/sections/%s/all?type=%s' % (uuid,
                                                                           sectionId,
                                                                           sectionType)
        if limit:
            uri = uri + '&limit=%s' % str(limit)

        for category, value in kwargs.items():
            sectionChoices = section.listChoices(category)
            for choice in sectionChoices:
                if str(choice.title).lower() == str(value).lower():
                    uri = uri + '&%s=%s' % (category.lower(), str(choice.key))

        uri = uri + '&sourceType=%s' % sectionType
        key = '/playlists%s' % utils.joinArgs({
            'uri': uri,
            'type': section.CONTENT_TYPE,
            'title': title,
            'smart': 1,
        })
        data = server.query(key, method=server._session.post)[0]
        return cls(server, data, initpath=key)

    def copyToUser(self, user):
        """ Copy playlist to another user account. """
        from plexapi.server import PlexServer
        myplex = self._server.myPlexAccount()
        user = myplex.user(user)
        # Get the token for your machine.
        token = user.get_token(self._server.machineIdentifier)
        # Login to your server using your friends credentials.
        user_server = PlexServer(self._server._baseurl, token)
        return self.create(user_server, self.title, self.items())

    def sync(self, videoQuality=None, photoResolution=None, audioBitrate=None, client=None, clientId=None, limit=None,
             unwatched=False, title=None):
        """ Add current playlist as sync item for specified device.
            See :func:`~plexapi.myplex.MyPlexAccount.sync` for possible exceptions.

            Parameters:
                videoQuality (int): idx of quality of the video, one of VIDEO_QUALITY_* values defined in
                                    :mod:`~plexapi.sync` module. Used only when playlist contains video.
                photoResolution (str): maximum allowed resolution for synchronized photos, see PHOTO_QUALITY_* values in
                                       the module :mod:`~plexapi.sync`. Used only when playlist contains photos.
                audioBitrate (int): maximum bitrate for synchronized music, better use one of MUSIC_BITRATE_* values
                                    from the module :mod:`~plexapi.sync`. Used only when playlist contains audio.
                client (:class:`~plexapi.myplex.MyPlexDevice`): sync destination, see
                                                               :func:`~plexapi.myplex.MyPlexAccount.sync`.
                clientId (str): sync destination, see :func:`~plexapi.myplex.MyPlexAccount.sync`.
                limit (int): maximum count of items to sync, unlimited if `None`.
                unwatched (bool): if `True` watched videos wouldn't be synced.
                title (str): descriptive title for the new :class:`~plexapi.sync.SyncItem`, if empty the value would be
                             generated from metadata of current photo.

            Raises:
                :exc:`~plexapi.exceptions.BadRequest`: When playlist is not allowed to sync.
                :exc:`~plexapi.exceptions.Unsupported`: When playlist content is unsupported.

            Returns:
                :class:`~plexapi.sync.SyncItem`: an instance of created syncItem.
        """

        if not self.allowSync:
            raise BadRequest('The playlist is not allowed to sync')

        from plexapi.sync import SyncItem, Policy, MediaSettings

        myplex = self._server.myPlexAccount()
        sync_item = SyncItem(self._server, None)
        sync_item.title = title if title else self.title
        sync_item.rootTitle = self.title
        sync_item.contentType = self.playlistType
        sync_item.metadataType = self.metadataType
        sync_item.machineIdentifier = self._server.machineIdentifier

        sync_item.location = 'playlist:///%s' % quote_plus(self.guid)
        sync_item.policy = Policy.create(limit, unwatched)

        if self.isVideo:
            sync_item.mediaSettings = MediaSettings.createVideo(videoQuality)
        elif self.isAudio:
            sync_item.mediaSettings = MediaSettings.createMusic(audioBitrate)
        elif self.isPhoto:
            sync_item.mediaSettings = MediaSettings.createPhoto(photoResolution)
        else:
            raise Unsupported('Unsupported playlist content')

        return myplex.sync(sync_item, client=client, clientId=clientId)

    def posters(self):
        """ Returns list of available poster objects. :class:`~plexapi.media.Poster`. """

        return self.fetchItems('/library/metadata/%s/posters' % self.ratingKey)

    def uploadPoster(self, url=None, filepath=None):
        """ Upload poster from url or filepath. :class:`~plexapi.media.Poster` to :class:`~plexapi.video.Video`. """
        if url:
            key = '/library/metadata/%s/posters?url=%s' % (self.ratingKey, quote_plus(url))
            self._server.query(key, method=self._server._session.post)
        elif filepath:
            key = '/library/metadata/%s/posters?' % self.ratingKey
            data = open(filepath, 'rb').read()
            self._server.query(key, method=self._server._session.post, data=data)

    def setPoster(self, poster):
        """ Set . :class:`~plexapi.media.Poster` to :class:`~plexapi.video.Video` """
        poster.select()

    def arts(self):
        """ Returns list of available art objects. :class:`~plexapi.media.Poster`. """

        return self.fetchItems('/library/metadata/%s/arts' % self.ratingKey)

    def uploadArt(self, url=None, filepath=None):
        """ Upload art from url or filepath. :class:`~plexapi.media.Poster` to :class:`~plexapi.video.Video`. """
        if url:
            key = '/library/metadata/%s/arts?url=%s' % (self.ratingKey, quote_plus(url))
            self._server.query(key, method=self._server._session.post)
        elif filepath:
            key = '/library/metadata/%s/arts?' % self.ratingKey
            data = open(filepath, 'rb').read()
            self._server.query(key, method=self._server._session.post, data=data)

    def setArt(self, art):
        """ Set :class:`~plexapi.media.Poster` to :class:`~plexapi.video.Video` """
        art.select()
