# -*- coding: utf-8 -*-
import re
from urllib.parse import quote_plus, unquote

from plexapi import media, utils
from plexapi.base import Playable, PlexPartialObject
from plexapi.exceptions import BadRequest, NotFound, Unsupported
from plexapi.library import LibrarySection
from plexapi.mixins import SmartFilterMixin, ArtMixin, PosterMixin
from plexapi.playqueue import PlayQueue
from plexapi.utils import deprecated


@utils.registerPlexObject
class Playlist(
    PlexPartialObject, Playable,
    SmartFilterMixin,
    ArtMixin, PosterMixin
):
    """ Represents a single Playlist.

        Attributes:
            TAG (str): 'Playlist'
            TYPE (str): 'playlist'
            addedAt (datetime): Datetime the playlist was added to the server.
            allowSync (bool): True if you allow syncing playlists.
            composite (str): URL to composite image (/playlist/<ratingKey>/composite/<compositeid>)
            content (str): The filter URI string for smart playlists.
            duration (int): Duration of the playlist in milliseconds.
            durationInSeconds (int): Duration of the playlist in seconds.
            fields (List<:class:`~plexapi.media.Field`>): List of field objects.
            guid (str): Plex GUID for the playlist (com.plexapp.agents.none://XXXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXX).
            icon (str): Icon URI string for smart playlists.
            key (str): API URL (/playlist/<ratingkey>).
            leafCount (int): Number of items in the playlist view.
            librarySectionID (int): Library section identifier (radio only)
            librarySectionKey (str): Library section key (radio only)
            librarySectionTitle (str): Library section title (radio only)
            playlistType (str): 'audio', 'video', or 'photo'
            radio (bool): If this playlist represents a radio station
            ratingKey (int): Unique key identifying the playlist.
            smart (bool): True if the playlist is a smart playlist.
            summary (str): Summary of the playlist.
            title (str): Name of the playlist.
            type (str): 'playlist'
            updatedAt (datetime): Datetime the playlist was updated.
    """
    TAG = 'Playlist'
    TYPE = 'playlist'

    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        Playable._loadData(self, data)
        self.addedAt = utils.toDatetime(data.attrib.get('addedAt'))
        self.allowSync = utils.cast(bool, data.attrib.get('allowSync'))
        self.composite = data.attrib.get('composite')  # url to thumbnail
        self.content = data.attrib.get('content')
        self.duration = utils.cast(int, data.attrib.get('duration'))
        self.durationInSeconds = utils.cast(int, data.attrib.get('durationInSeconds'))
        self.fields = self.findItems(data, media.Field)
        self.guid = data.attrib.get('guid')
        self.icon = data.attrib.get('icon')
        self.key = data.attrib.get('key', '').replace('/items', '')  # FIX_BUG_50
        self.leafCount = utils.cast(int, data.attrib.get('leafCount'))
        self.librarySectionID = utils.cast(int, data.attrib.get('librarySectionID'))
        self.librarySectionKey = data.attrib.get('librarySectionKey')
        self.librarySectionTitle = data.attrib.get('librarySectionTitle')
        self.playlistType = data.attrib.get('playlistType')
        self.radio = utils.cast(bool, data.attrib.get('radio', 0))
        self.ratingKey = utils.cast(int, data.attrib.get('ratingKey'))
        self.smart = utils.cast(bool, data.attrib.get('smart'))
        self.summary = data.attrib.get('summary')
        self.title = data.attrib.get('title')
        self.type = data.attrib.get('type')
        self.updatedAt = utils.toDatetime(data.attrib.get('updatedAt'))
        self._items = None  # cache for self.items
        self._section = None  # cache for self.section
        self._filters = None  # cache for self.filters

    def __len__(self):  # pragma: no cover
        return len(self.items())

    def __iter__(self):  # pragma: no cover
        for item in self.items():
            yield item

    def __contains__(self, other):  # pragma: no cover
        return any(i.key == other.key for i in self.items())

    def __getitem__(self, key):  # pragma: no cover
        return self.items()[key]

    @property
    def thumb(self):
        """ Alias to self.composite. """
        return self.composite

    @property
    def metadataType(self):
        """ Returns the type of metadata in the playlist (movie, track, or photo). """
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
        """ Returns True if this is a video playlist. """
        return self.playlistType == 'video'

    @property
    def isAudio(self):
        """ Returns True if this is an audio playlist. """
        return self.playlistType == 'audio'

    @property
    def isPhoto(self):
        """ Returns True if this is a photo playlist. """
        return self.playlistType == 'photo'

    def _getPlaylistItemID(self, item):
        """ Match an item to a playlist item and return the item playlistItemID. """
        for _item in self.items():
            if _item.ratingKey == item.ratingKey:
                return _item.playlistItemID
        raise NotFound('Item with title "%s" not found in the playlist' % item.title)

    def filters(self):
        """ Returns the search filter dict for smart playlist.
            The filter dict be passed back into :func:`~plexapi.library.LibrarySection.search`
            to get the list of items.
        """
        if self.smart and self._filters is None:
            self._filters = self._parseFilters(self.content)
        return self._filters

    def section(self):
        """ Returns the :class:`~plexapi.library.LibrarySection` this smart playlist belongs to.

            Raises:
                :class:`plexapi.exceptions.BadRequest`: When trying to get the section for a regular playlist.
                :class:`plexapi.exceptions.Unsupported`: When unable to determine the library section.
        """
        if not self.smart:
            raise BadRequest('Regular playlists are not associated with a library.')

        if self._section is None:
            # Try to parse the library section from the content URI string
            match = re.search(r'/library/sections/(\d+)/all', unquote(self.content or ''))
            if match:
                sectionKey = int(match.group(1))
                self._section = self._server.library.sectionByID(sectionKey)
                return self._section
        
            # Try to get the library section from the first item in the playlist
            if self.items():
                self._section = self.items()[0].section()
                return self._section

            raise Unsupported('Unable to determine the library section')

        return self._section

    def item(self, title):
        """ Returns the item in the playlist that matches the specified title.

            Parameters:
                title (str): Title of the item to return.

            Raises:
                :class:`plexapi.exceptions.NotFound`: When the item is not found in the playlist.
        """
        for item in self.items():
            if item.title.lower() == title.lower():
                return item
        raise NotFound('Item with title "%s" not found in the playlist' % title)

    def items(self):
        """ Returns a list of all items in the playlist. """
        if self.radio:
            return []
        if self._items is None:
            key = '%s/items' % self.key
            items = self.fetchItems(key)
            self._items = items
        return self._items

    def get(self, title):
        """ Alias to :func:`~plexapi.playlist.Playlist.item`. """
        return self.item(title)

    def addItems(self, items):
        """ Add items to the playlist.

            Parameters:
                items (List): List of :class:`~plexapi.audio.Audio`, :class:`~plexapi.video.Video`,
                    or :class:`~plexapi.photo.Photo` objects to be added to the playlist.

            Raises:
                :class:`plexapi.exceptions.BadRequest`: When trying to add items to a smart playlist.
        """
        if self.smart:
            raise BadRequest('Cannot add items to a smart playlist.')

        if items and not isinstance(items, (list, tuple)):
            items = [items]

        ratingKeys = []
        for item in items:
            if item.listType != self.playlistType:  # pragma: no cover
                raise BadRequest('Can not mix media types when building a playlist: %s and %s' %
                    (self.playlistType, item.listType))
            ratingKeys.append(str(item.ratingKey))

        ratingKeys = ','.join(ratingKeys)
        uri = '%s/library/metadata/%s' % (self._server._uriRoot(), ratingKeys)

        key = '%s/items%s' % (self.key, utils.joinArgs({
            'uri': uri
        }))
        self._server.query(key, method=self._server._session.put)

    @deprecated('use "removeItems" instead', stacklevel=3)
    def removeItem(self, item):
        self.removeItems(item)

    def removeItems(self, items):
        """ Remove items from the playlist.

            Parameters:
                items (List): List of :class:`~plexapi.audio.Audio`, :class:`~plexapi.video.Video`,
                    or :class:`~plexapi.photo.Photo` objects to be removed from the playlist.

            Raises:
                :class:`plexapi.exceptions.BadRequest`: When trying to remove items from a smart playlist.
                :class:`plexapi.exceptions.NotFound`: When the item does not exist in the playlist.
        """
        if self.smart:
            raise BadRequest('Cannot remove items from a smart playlist.')

        if items and not isinstance(items, (list, tuple)):
            items = [items]

        for item in items:
            playlistItemID = self._getPlaylistItemID(item)
            key = '%s/items/%s' % (self.key, playlistItemID)
            self._server.query(key, method=self._server._session.delete)

    def moveItem(self, item, after=None):
        """ Move an item to a new position in the playlist.

            Parameters:
                items (obj): :class:`~plexapi.audio.Audio`, :class:`~plexapi.video.Video`,
                    or :class:`~plexapi.photo.Photo` objects to be moved in the playlist.
                after (obj): :class:`~plexapi.audio.Audio`, :class:`~plexapi.video.Video`,
                    or :class:`~plexapi.photo.Photo` objects to move the item after in the playlist.

            Raises:
                :class:`plexapi.exceptions.BadRequest`: When trying to move items in a smart playlist.
                :class:`plexapi.exceptions.NotFound`: When the item or item after does not exist in the playlist.
        """
        if self.smart:
            raise BadRequest('Cannot move items in a smart playlist.')

        playlistItemID = self._getPlaylistItemID(item)
        key = '%s/items/%s/move' % (self.key, playlistItemID)

        if after:
            afterPlaylistItemID = self._getPlaylistItemID(after)
            key += '?after=%s' % afterPlaylistItemID

        self._server.query(key, method=self._server._session.put)

    def updateFilters(self, limit=None, sort=None, filters=None, **kwargs):
        """ Update the filters for a smart playlist.

            Parameters:
                limit (int): Limit the number of items in the playlist.
                sort (str or list, optional): A string of comma separated sort fields
                    or a list of sort fields in the format ``column:dir``.
                    See :func:`~plexapi.library.LibrarySection.search` for more info.
                filters (dict): A dictionary of advanced filters.
                    See :func:`~plexapi.library.LibrarySection.search` for more info.
                **kwargs (dict): Additional custom filters to apply to the search results.
                    See :func:`~plexapi.library.LibrarySection.search` for more info.

            Raises:
                :class:`plexapi.exceptions.BadRequest`: When trying update filters for a regular playlist.
        """
        if not self.smart:
            raise BadRequest('Cannot update filters for a regular playlist.')

        section = self.section()
        searchKey = section._buildSearchKey(
            sort=sort, libtype=section.METADATA_TYPE, limit=limit, filters=filters, **kwargs)
        uri = '%s%s' % (self._server._uriRoot(), searchKey)

        key = '%s/items%s' % (self.key, utils.joinArgs({
            'uri': uri
        }))
        self._server.query(key, method=self._server._session.put)

    def _edit(self, **kwargs):
        """ Actually edit the playlist. """
        key = '%s%s' % (self.key, utils.joinArgs(kwargs))
        self._server.query(key, method=self._server._session.put)

    def edit(self, title=None, summary=None):
        """ Edit the playlist.
        
            Parameters:
                title (str, optional): The title of the playlist.
                summary (str, optional): The summary of the playlist.
        """
        args = {}
        if title:
            args['title'] = title
        if summary:
            args['summary'] = summary
        self._edit(**args)

    def delete(self):
        """ Delete the playlist. """
        self._server.query(self.key, method=self._server._session.delete)

    def playQueue(self, *args, **kwargs):
        """ Returns a new :class:`~plexapi.playqueue.PlayQueue` from the playlist. """
        return PlayQueue.create(self._server, self, *args, **kwargs)

    @classmethod
    def _create(cls, server, title, items):
        """ Create a regular playlist. """
        if not items:
            raise BadRequest('Must include items to add when creating new playlist.')

        if items and not isinstance(items, (list, tuple)):
            items = [items]

        listType = items[0].listType
        ratingKeys = []
        for item in items:
            if item.listType != listType:  # pragma: no cover
                raise BadRequest('Can not mix media types when building a playlist.')
            ratingKeys.append(str(item.ratingKey))

        ratingKeys = ','.join(ratingKeys)
        uri = '%s/library/metadata/%s' % (server._uriRoot(), ratingKeys)

        key = '/playlists%s' % utils.joinArgs({
            'uri': uri,
            'type': listType,
            'title': title,
            'smart': 0
        })
        data = server.query(key, method=server._session.post)[0]
        return cls(server, data, initpath=key)

    @classmethod
    def _createSmart(cls, server, title, section, limit=None, libtype=None, sort=None, filters=None, **kwargs):
        """ Create a smart playlist. """
        if not isinstance(section, LibrarySection):
            section = server.library.section(section)

        libtype = libtype or section.METADATA_TYPE

        searchKey = section._buildSearchKey(
            sort=sort, libtype=libtype, limit=limit, filters=filters, **kwargs)
        uri = '%s%s' % (server._uriRoot(), searchKey)

        key = '/playlists%s' % utils.joinArgs({
            'uri': uri,
            'type': section.CONTENT_TYPE,
            'title': title,
            'smart': 1,
        })
        data = server.query(key, method=server._session.post)[0]
        return cls(server, data, initpath=key)

    @classmethod
    def create(cls, server, title, section=None, items=None, smart=False, limit=None,
               libtype=None, sort=None, filters=None, **kwargs):
        """ Create a playlist.

            Parameters:
                server (:class:`~plexapi.server.PlexServer`): Server to create the playlist on.
                title (str): Title of the playlist.
                section (:class:`~plexapi.library.LibrarySection`, str): Smart playlists only,
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
                **kwargs (dict): Smart playlists only, additional custom filters to apply to the
                    search results. See :func:`~plexapi.library.LibrarySection.search` for more info.

            Raises:
                :class:`plexapi.exceptions.BadRequest`: When no items are included to create the playlist.
                :class:`plexapi.exceptions.BadRequest`: When mixing media types in the playlist.

            Returns:
                :class:`~plexapi.playlist.Playlist`: A new instance of the created Playlist.
        """
        if smart:
            return cls._createSmart(server, title, section, limit, libtype, sort, filters, **kwargs)
        else:
            return cls._create(server, title, items)

    def copyToUser(self, user):
        """ Copy playlist to another user account.
        
            Parameters:
                user (str): Username, email or user id of the user to copy the playlist to.
        """
        userServer = self._server.switchUser(user)
        return self.create(server=userServer, title=self.title, items=self.items())

    def sync(self, videoQuality=None, photoResolution=None, audioBitrate=None, client=None, clientId=None, limit=None,
             unwatched=False, title=None):
        """ Add the playlist as a sync item for the specified device.
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
                :class:`~plexapi.sync.SyncItem`: A new instance of the created sync item.
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

    def _getWebURL(self, base=None):
        """ Get the Plex Web URL with the correct parameters. """
        return self._server._buildWebURL(base=base, endpoint='playlist', key=self.key)
