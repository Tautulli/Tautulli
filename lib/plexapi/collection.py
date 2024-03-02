# -*- coding: utf-8 -*-
from pathlib import Path
from urllib.parse import quote_plus

from plexapi import media, utils
from plexapi.base import PlexPartialObject
from plexapi.exceptions import BadRequest, NotFound, Unsupported
from plexapi.library import LibrarySection, ManagedHub
from plexapi.mixins import (
    AdvancedSettingsMixin, SmartFilterMixin, HubsMixin, RatingMixin,
    ArtMixin, PosterMixin, ThemeMixin,
    CollectionEditMixins
)
from plexapi.utils import deprecated


@utils.registerPlexObject
class Collection(
    PlexPartialObject,
    AdvancedSettingsMixin, SmartFilterMixin, HubsMixin, RatingMixin,
    ArtMixin, PosterMixin, ThemeMixin,
    CollectionEditMixins
):
    """ Represents a single Collection.

        Attributes:
            TAG (str): 'Directory'
            TYPE (str): 'collection'
            addedAt (datetime): Datetime the collection was added to the library.
            art (str): URL to artwork image (/library/metadata/<ratingKey>/art/<artid>).
            artBlurHash (str): BlurHash string for artwork image.
            childCount (int): Number of items in the collection.
            collectionFilterBasedOnUser (int): Which user's activity is used for the collection filtering.
            collectionMode (int): How the items in the collection are displayed.
            collectionPublished (bool): True if the collection is published to the Plex homepage.
            collectionSort (int): How to sort the items in the collection.
            content (str): The filter URI string for smart collections.
            contentRating (str) Content rating (PG-13; NR; TV-G).
            fields (List<:class:`~plexapi.media.Field`>): List of field objects.
            guid (str): Plex GUID for the collection (collection://XXXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXX).
            index (int): Plex index number for the collection.
            key (str): API URL (/library/metadata/<ratingkey>).
            labels (List<:class:`~plexapi.media.Label`>): List of label objects.
            lastRatedAt (datetime): Datetime the collection was last rated.
            librarySectionID (int): :class:`~plexapi.library.LibrarySection` ID.
            librarySectionKey (str): :class:`~plexapi.library.LibrarySection` key.
            librarySectionTitle (str): :class:`~plexapi.library.LibrarySection` title.
            maxYear (int): Maximum year for the items in the collection.
            minYear (int): Minimum year for the items in the collection.
            ratingCount (int): The number of ratings.
            ratingKey (int): Unique key identifying the collection.
            smart (bool): True if the collection is a smart collection.
            subtype (str): Media type of the items in the collection (movie, show, artist, or album).
            summary (str): Summary of the collection.
            theme (str): URL to theme resource (/library/metadata/<ratingkey>/theme/<themeid>).
            thumb (str): URL to thumbnail image (/library/metadata/<ratingKey>/thumb/<thumbid>).
            thumbBlurHash (str): BlurHash string for thumbnail image.
            title (str): Name of the collection.
            titleSort (str): Title to use when sorting (defaults to title).
            type (str): 'collection'
            updatedAt (datetime): Datetime the collection was updated.
            userRating (float): Rating of the collection (0.0 - 10.0) equaling (0 stars - 5 stars).
    """
    TAG = 'Directory'
    TYPE = 'collection'

    def _loadData(self, data):
        self._data = data
        self.addedAt = utils.toDatetime(data.attrib.get('addedAt'))
        self.art = data.attrib.get('art')
        self.artBlurHash = data.attrib.get('artBlurHash')
        self.childCount = utils.cast(int, data.attrib.get('childCount'))
        self.collectionFilterBasedOnUser = utils.cast(int, data.attrib.get('collectionFilterBasedOnUser', '0'))
        self.collectionMode = utils.cast(int, data.attrib.get('collectionMode', '-1'))
        self.collectionPublished = utils.cast(bool, data.attrib.get('collectionPublished', '0'))
        self.collectionSort = utils.cast(int, data.attrib.get('collectionSort', '0'))
        self.content = data.attrib.get('content')
        self.contentRating = data.attrib.get('contentRating')
        self.fields = self.findItems(data, media.Field)
        self.guid = data.attrib.get('guid')
        self.index = utils.cast(int, data.attrib.get('index'))
        self.key = data.attrib.get('key', '').replace('/children', '')  # FIX_BUG_50
        self.labels = self.findItems(data, media.Label)
        self.lastRatedAt = utils.toDatetime(data.attrib.get('lastRatedAt'))
        self.librarySectionID = utils.cast(int, data.attrib.get('librarySectionID'))
        self.librarySectionKey = data.attrib.get('librarySectionKey')
        self.librarySectionTitle = data.attrib.get('librarySectionTitle')
        self.maxYear = utils.cast(int, data.attrib.get('maxYear'))
        self.minYear = utils.cast(int, data.attrib.get('minYear'))
        self.ratingCount = utils.cast(int, data.attrib.get('ratingCount'))
        self.ratingKey = utils.cast(int, data.attrib.get('ratingKey'))
        self.smart = utils.cast(bool, data.attrib.get('smart', '0'))
        self.subtype = data.attrib.get('subtype')
        self.summary = data.attrib.get('summary')
        self.theme = data.attrib.get('theme')
        self.thumb = data.attrib.get('thumb')
        self.thumbBlurHash = data.attrib.get('thumbBlurHash')
        self.title = data.attrib.get('title')
        self.titleSort = data.attrib.get('titleSort', self.title)
        self.type = data.attrib.get('type')
        self.updatedAt = utils.toDatetime(data.attrib.get('updatedAt'))
        self.userRating = utils.cast(float, data.attrib.get('userRating'))
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
    def listType(self):
        """ Returns the listType for the collection. """
        if self.isVideo:
            return 'video'
        elif self.isAudio:
            return 'audio'
        elif self.isPhoto:
            return 'photo'
        else:
            raise Unsupported('Unexpected collection type')

    @property
    def metadataType(self):
        """ Returns the type of metadata in the collection. """
        return self.subtype

    @property
    def isVideo(self):
        """ Returns True if this is a video collection. """
        return self.subtype in {'movie', 'show', 'season', 'episode'}

    @property
    def isAudio(self):
        """ Returns True if this is an audio collection. """
        return self.subtype in {'artist', 'album', 'track'}

    @property
    def isPhoto(self):
        """ Returns True if this is a photo collection. """
        return self.subtype in {'photoalbum', 'photo'}

    @property
    @deprecated('use "items" instead', stacklevel=3)
    def children(self):
        return self.items()

    def filters(self):
        """ Returns the search filter dict for smart collection.
            The filter dict be passed back into :func:`~plexapi.library.LibrarySection.search`
            to get the list of items.
        """
        if self.smart and self._filters is None:
            self._filters = self._parseFilters(self.content)
        return self._filters

    def section(self):
        """ Returns the :class:`~plexapi.library.LibrarySection` this collection belongs to.
        """
        if self._section is None:
            self._section = super(Collection, self).section()
        return self._section

    def item(self, title):
        """ Returns the item in the collection that matches the specified title.

            Parameters:
                title (str): Title of the item to return.

            Raises:
                :class:`plexapi.exceptions.NotFound`: When the item is not found in the collection.
        """
        for item in self.items():
            if item.title.lower() == title.lower():
                return item
        raise NotFound(f'Item with title "{title}" not found in the collection')

    def items(self):
        """ Returns a list of all items in the collection. """
        if self._items is None:
            key = f'{self.key}/children'
            items = self.fetchItems(key)
            self._items = items
        return self._items

    def visibility(self):
        """ Returns the :class:`~plexapi.library.ManagedHub` for this collection. """
        key = f'/hubs/sections/{self.librarySectionID}/manage?metadataItemId={self.ratingKey}'
        data = self._server.query(key)
        hub = self.findItem(data, cls=ManagedHub)
        if hub is None:
            hub = ManagedHub(self._server, data, parent=self)
            hub.identifier = f'custom.collection.{self.librarySectionID}.{self.ratingKey}'
            hub.title = self.title
            hub._promoted = False
        return hub

    def get(self, title):
        """ Alias to :func:`~plexapi.library.Collection.item`. """
        return self.item(title)

    def filterUserUpdate(self, user=None):
        """ Update the collection filtering user advanced setting.

            Parameters:
                user (str): One of the following values:
                    "admin" (Always the server admin user),
                    "user" (User currently viewing the content)

            Example:

                .. code-block:: python

                    collection.updateMode(user="user")

        """
        if not self.smart:
            raise BadRequest('Cannot change collection filtering user for a non-smart collection.')

        user_dict = {
            'admin': 0,
            'user': 1
        }
        key = user_dict.get(user)
        if key is None:
            raise BadRequest(f'Unknown collection filtering user: {user}. Options {list(user_dict)}')
        return self.editAdvanced(collectionFilterBasedOnUser=key)

    def modeUpdate(self, mode=None):
        """ Update the collection mode advanced setting.

            Parameters:
                mode (str): One of the following values:
                    "default" (Library default),
                    "hide" (Hide Collection),
                    "hideItems" (Hide Items in this Collection),
                    "showItems" (Show this Collection and its Items)

            Example:

                .. code-block:: python

                    collection.updateMode(mode="hide")

        """
        mode_dict = {
            'default': -1,
            'hide': 0,
            'hideItems': 1,
            'showItems': 2
        }
        key = mode_dict.get(mode)
        if key is None:
            raise BadRequest(f'Unknown collection mode: {mode}. Options {list(mode_dict)}')
        return self.editAdvanced(collectionMode=key)

    def sortUpdate(self, sort=None):
        """ Update the collection order advanced setting.

            Parameters:
                sort (str): One of the following values:
                    "release" (Order Collection by release dates),
                    "alpha" (Order Collection alphabetically),
                    "custom" (Custom collection order)

            Example:

                .. code-block:: python

                    collection.sortUpdate(sort="alpha")

        """
        if self.smart:
            raise BadRequest('Cannot change collection order for a smart collection.')

        sort_dict = {
            'release': 0,
            'alpha': 1,
            'custom': 2
        }
        key = sort_dict.get(sort)
        if key is None:
            raise BadRequest(f'Unknown sort dir: {sort}. Options: {list(sort_dict)}')
        return self.editAdvanced(collectionSort=key)

    def addItems(self, items):
        """ Add items to the collection.

            Parameters:
                items (List): List of :class:`~plexapi.audio.Audio`, :class:`~plexapi.video.Video`,
                    or :class:`~plexapi.photo.Photo` objects to be added to the collection.

            Raises:
                :class:`plexapi.exceptions.BadRequest`: When trying to add items to a smart collection.
        """
        if self.smart:
            raise BadRequest('Cannot add items to a smart collection.')

        if items and not isinstance(items, (list, tuple)):
            items = [items]

        ratingKeys = []
        for item in items:
            if item.type != self.subtype:  # pragma: no cover
                raise BadRequest(f'Can not mix media types when building a collection: {self.subtype} and {item.type}')
            ratingKeys.append(str(item.ratingKey))

        ratingKeys = ','.join(ratingKeys)
        uri = f'{self._server._uriRoot()}/library/metadata/{ratingKeys}'

        args = {'uri': uri}
        key = f"{self.key}/items{utils.joinArgs(args)}"
        self._server.query(key, method=self._server._session.put)
        return self

    def removeItems(self, items):
        """ Remove items from the collection.

            Parameters:
                items (List): List of :class:`~plexapi.audio.Audio`, :class:`~plexapi.video.Video`,
                    or :class:`~plexapi.photo.Photo` objects to be removed from the collection.

            Raises:
                :class:`plexapi.exceptions.BadRequest`: When trying to remove items from a smart collection.
        """
        if self.smart:
            raise BadRequest('Cannot remove items from a smart collection.')

        if items and not isinstance(items, (list, tuple)):
            items = [items]

        for item in items:
            key = f'{self.key}/items/{item.ratingKey}'
            self._server.query(key, method=self._server._session.delete)
        return self

    def moveItem(self, item, after=None):
        """ Move an item to a new position in the collection.

            Parameters:
                item (obj): :class:`~plexapi.audio.Audio`, :class:`~plexapi.video.Video`,
                    or :class:`~plexapi.photo.Photo` object to be moved in the collection.
                after (obj): :class:`~plexapi.audio.Audio`, :class:`~plexapi.video.Video`,
                    or :class:`~plexapi.photo.Photo` object to move the item after in the collection.

            Raises:
                :class:`plexapi.exceptions.BadRequest`: When trying to move items in a smart collection.
        """
        if self.smart:
            raise BadRequest('Cannot move items in a smart collection.')

        key = f'{self.key}/items/{item.ratingKey}/move'

        if after:
            key += f'?after={after.ratingKey}'

        self._server.query(key, method=self._server._session.put)
        return self

    def updateFilters(self, libtype=None, limit=None, sort=None, filters=None, **kwargs):
        """ Update the filters for a smart collection.

            Parameters:
                libtype (str): The specific type of content to filter
                    (movie, show, season, episode, artist, album, track, photoalbum, photo, collection).
                limit (int): Limit the number of items in the collection.
                sort (str or list, optional): A string of comma separated sort fields
                    or a list of sort fields in the format ``column:dir``.
                    See :func:`~plexapi.library.LibrarySection.search` for more info.
                filters (dict): A dictionary of advanced filters.
                    See :func:`~plexapi.library.LibrarySection.search` for more info.
                **kwargs (dict): Additional custom filters to apply to the search results.
                    See :func:`~plexapi.library.LibrarySection.search` for more info.

            Raises:
                :class:`plexapi.exceptions.BadRequest`: When trying update filters for a regular collection.
        """
        if not self.smart:
            raise BadRequest('Cannot update filters for a regular collection.')

        section = self.section()
        searchKey = section._buildSearchKey(
            sort=sort, libtype=libtype, limit=limit, filters=filters, **kwargs)
        uri = f'{self._server._uriRoot()}{searchKey}'

        args = {'uri': uri}
        key = f"{self.key}/items{utils.joinArgs(args)}"
        self._server.query(key, method=self._server._session.put)
        return self

    @deprecated('use editTitle, editSortTitle, editContentRating, and editSummary instead')
    def edit(self, title=None, titleSort=None, contentRating=None, summary=None, **kwargs):
        """ Edit the collection.

            Parameters:
                title (str, optional): The title of the collection.
                titleSort (str, optional): The sort title of the collection.
                contentRating (str, optional): The summary of the collection.
                summary (str, optional): The summary of the collection.
        """
        args = {}
        if title is not None:
            args['title.value'] = title
            args['title.locked'] = 1
        if titleSort is not None:
            args['titleSort.value'] = titleSort
            args['titleSort.locked'] = 1
        if contentRating is not None:
            args['contentRating.value'] = contentRating
            args['contentRating.locked'] = 1
        if summary is not None:
            args['summary.value'] = summary
            args['summary.locked'] = 1

        args.update(kwargs)
        self._edit(**args)

    def delete(self):
        """ Delete the collection. """
        super(Collection, self).delete()

    @classmethod
    def _create(cls, server, title, section, items):
        """ Create a regular collection. """
        if not items:
            raise BadRequest('Must include items to add when creating new collection.')

        if not isinstance(section, LibrarySection):
            section = server.library.section(section)

        if items and not isinstance(items, (list, tuple)):
            items = [items]

        itemType = items[0].type
        ratingKeys = []
        for item in items:
            if item.type != itemType:  # pragma: no cover
                raise BadRequest('Can not mix media types when building a collection.')
            ratingKeys.append(str(item.ratingKey))

        ratingKeys = ','.join(ratingKeys)
        uri = f'{server._uriRoot()}/library/metadata/{ratingKeys}'

        args = {'uri': uri, 'type': utils.searchType(itemType), 'title': title, 'smart': 0, 'sectionId': section.key}
        key = f"/library/collections{utils.joinArgs(args)}"
        data = server.query(key, method=server._session.post)[0]
        return cls(server, data, initpath=key)

    @classmethod
    def _createSmart(cls, server, title, section, limit=None, libtype=None, sort=None, filters=None, **kwargs):
        """ Create a smart collection. """
        if not isinstance(section, LibrarySection):
            section = server.library.section(section)

        libtype = libtype or section.TYPE

        searchKey = section._buildSearchKey(
            sort=sort, libtype=libtype, limit=limit, filters=filters, **kwargs)
        uri = f'{server._uriRoot()}{searchKey}'

        args = {'uri': uri, 'type': utils.searchType(libtype), 'title': title, 'smart': 1, 'sectionId': section.key}
        key = f"/library/collections{utils.joinArgs(args)}"
        data = server.query(key, method=server._session.post)[0]
        return cls(server, data, initpath=key)

    @classmethod
    def create(cls, server, title, section, items=None, smart=False, limit=None,
               libtype=None, sort=None, filters=None, **kwargs):
        """ Create a collection.

            Parameters:
                server (:class:`~plexapi.server.PlexServer`): Server to create the collection on.
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
        """
        if smart:
            return cls._createSmart(server, title, section, limit, libtype, sort, filters, **kwargs)
        else:
            return cls._create(server, title, section, items)

    def sync(self, videoQuality=None, photoResolution=None, audioBitrate=None, client=None, clientId=None, limit=None,
             unwatched=False, title=None):
        """ Add the collection as sync item for the specified device.
            See :func:`~plexapi.myplex.MyPlexAccount.sync` for possible exceptions.

            Parameters:
                videoQuality (int): idx of quality of the video, one of VIDEO_QUALITY_* values defined in
                                    :mod:`~plexapi.sync` module. Used only when collection contains video.
                photoResolution (str): maximum allowed resolution for synchronized photos, see PHOTO_QUALITY_* values in
                                       the module :mod:`~plexapi.sync`. Used only when collection contains photos.
                audioBitrate (int): maximum bitrate for synchronized music, better use one of MUSIC_BITRATE_* values
                                    from the module :mod:`~plexapi.sync`. Used only when collection contains audio.
                client (:class:`~plexapi.myplex.MyPlexDevice`): sync destination, see
                                                               :func:`~plexapi.myplex.MyPlexAccount.sync`.
                clientId (str): sync destination, see :func:`~plexapi.myplex.MyPlexAccount.sync`.
                limit (int): maximum count of items to sync, unlimited if `None`.
                unwatched (bool): if `True` watched videos wouldn't be synced.
                title (str): descriptive title for the new :class:`~plexapi.sync.SyncItem`, if empty the value would be
                             generated from metadata of current photo.

            Raises:
                :exc:`~plexapi.exceptions.BadRequest`: When collection is not allowed to sync.
                :exc:`~plexapi.exceptions.Unsupported`: When collection content is unsupported.

            Returns:
                :class:`~plexapi.sync.SyncItem`: A new instance of the created sync item.
        """
        if not self.section().allowSync:
            raise BadRequest('The collection is not allowed to sync')

        from plexapi.sync import SyncItem, Policy, MediaSettings

        myplex = self._server.myPlexAccount()
        sync_item = SyncItem(self._server, None)
        sync_item.title = title if title else self.title
        sync_item.rootTitle = self.title
        sync_item.contentType = self.listType
        sync_item.metadataType = self.metadataType
        sync_item.machineIdentifier = self._server.machineIdentifier

        key = quote_plus(f'{self.key}/children?excludeAllLeaves=1')
        sync_item.location = f'library:///directory/{key}'
        sync_item.policy = Policy.create(limit, unwatched)

        if self.isVideo:
            sync_item.mediaSettings = MediaSettings.createVideo(videoQuality)
        elif self.isAudio:
            sync_item.mediaSettings = MediaSettings.createMusic(audioBitrate)
        elif self.isPhoto:
            sync_item.mediaSettings = MediaSettings.createPhoto(photoResolution)
        else:
            raise Unsupported('Unsupported collection content')

        return myplex.sync(sync_item, client=client, clientId=clientId)

    @property
    def metadataDirectory(self):
        """ Returns the Plex Media Server data directory where the metadata is stored. """
        guid_hash = utils.sha1hash(self.guid)
        return str(Path('Metadata') / 'Collections' / guid_hash[0] / f'{guid_hash[1:]}.bundle')
