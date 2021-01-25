# -*- coding: utf-8 -*-
from urllib.parse import quote_plus

from plexapi import media, utils, video
from plexapi.base import Playable, PlexPartialObject
from plexapi.exceptions import BadRequest


@utils.registerPlexObject
class Photoalbum(PlexPartialObject):
    """ Represents a single Photoalbum (collection of photos).

        Attributes:
            TAG (str): 'Directory'
            TYPE (str): 'photo'
            addedAt (datetime): Datetime the photo album was added to the library.
            art (str): URL to artwork image (/library/metadata/<ratingKey>/art/<artid>).
            composite (str): URL to composite image (/library/metadata/<ratingKey>/composite/<compositeid>)
            fields (List<:class:`~plexapi.media.Field`>): List of field objects.
            guid (str): Plex GUID for the photo album (local://229674).
            index (sting): Plex index number for the photo album.
            key (str): API URL (/library/metadata/<ratingkey>).
            librarySectionID (int): :class:`~plexapi.library.LibrarySection` ID.
            librarySectionKey (str): :class:`~plexapi.library.LibrarySection` key.
            librarySectionTitle (str): :class:`~plexapi.library.LibrarySection` title.
            listType (str): Hardcoded as 'photo' (useful for search filters).
            ratingKey (int): Unique key identifying the photo album.
            summary (str): Summary of the photoalbum.
            thumb (str): URL to thumbnail image (/library/metadata/<ratingKey>/thumb/<thumbid>).
            title (str): Name of the photo album. (Trip to Disney World)
            titleSort (str): Title to use when sorting (defaults to title).
            type (str): 'photo'
            updatedAt (datatime): Datetime the photo album was updated.
            userRating (float): Rating of the photoalbum (0.0 - 10.0) equaling (0 stars - 5 stars).
    """
    TAG = 'Directory'
    TYPE = 'photo'

    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        self.addedAt = utils.toDatetime(data.attrib.get('addedAt'))
        self.art = data.attrib.get('art')
        self.composite = data.attrib.get('composite')
        self.fields = self.findItems(data, media.Field)
        self.guid = data.attrib.get('guid')
        self.index = utils.cast(int, data.attrib.get('index'))
        self.key = data.attrib.get('key', '')
        self.librarySectionID = data.attrib.get('librarySectionID')
        self.librarySectionKey = data.attrib.get('librarySectionKey')
        self.librarySectionTitle = data.attrib.get('librarySectionTitle')
        self.listType = 'photo'
        self.ratingKey = utils.cast(int, data.attrib.get('ratingKey'))
        self.summary = data.attrib.get('summary')
        self.thumb = data.attrib.get('thumb')
        self.title = data.attrib.get('title')
        self.titleSort = data.attrib.get('titleSort', self.title)
        self.type = data.attrib.get('type')
        self.updatedAt = utils.toDatetime(data.attrib.get('updatedAt'))
        self.userRating = utils.cast(float, data.attrib.get('userRating', 0))

    def album(self, title):
        """ Returns the :class:`~plexapi.photo.Photoalbum` that matches the specified title.

            Parameters:
                title (str): Title of the photo album to return.
        """
        key = '/library/metadata/%s/children' % self.ratingKey
        return self.fetchItem(key, Photoalbum, title__iexact=title)

    def albums(self, **kwargs):
        """ Returns a list of :class:`~plexapi.photo.Photoalbum` objects in the album. """
        key = '/library/metadata/%s/children' % self.ratingKey
        return self.fetchItems(key, Photoalbum, **kwargs)

    def photo(self, title):
        """ Returns the :class:`~plexapi.photo.Photo` that matches the specified title.

            Parameters:
                title (str): Title of the photo to return.
        """
        key = '/library/metadata/%s/children' % self.ratingKey
        return self.fetchItem(key, Photo, title__iexact=title)

    def photos(self, **kwargs):
        """ Returns a list of :class:`~plexapi.photo.Photo` objects in the album. """
        key = '/library/metadata/%s/children' % self.ratingKey
        return self.fetchItems(key, Photo, **kwargs)

    def clip(self, title):
        """ Returns the :class:`~plexapi.video.Clip` that matches the specified title.

            Parameters:
                title (str): Title of the clip to return.
        """
        key = '/library/metadata/%s/children' % self.ratingKey
        return self.fetchItem(key, video.Clip, title__iexact=title)

    def clips(self, **kwargs):
        """ Returns a list of :class:`~plexapi.video.Clip` objects in the album. """
        key = '/library/metadata/%s/children' % self.ratingKey
        return self.fetchItems(key, video.Clip, **kwargs)

    def get(self, title):
        """ Alias to :func:`~plexapi.photo.Photoalbum.photo`. """
        return self.episode(title)

    def iterParts(self):
        """ Iterates over the parts of the media item. """
        for album in self.albums():
            for photo in album.photos():
                for part in photo.iterParts():
                    yield part

    def download(self, savepath=None, keep_original_name=False, showstatus=False):
        """ Download photo files to specified directory.

            Parameters:
                savepath (str): Defaults to current working dir.
                keep_original_name (bool): True to keep the original file name otherwise
                    a friendlier is generated.
                showstatus(bool): Display a progressbar.
        """
        filepaths = []
        locations = [i for i in self.iterParts() if i]
        for location in locations:
            name = location.file
            if not keep_original_name:
                title = self.title.replace(' ', '.')
                name = '%s.%s' % (title, location.container)
            url = self._server.url('%s?download=1' % location.key)
            filepath = utils.download(url, self._server._token, filename=name, showstatus=showstatus,
                                      savepath=savepath, session=self._server._session)
            if filepath:
                filepaths.append(filepath)
        return filepaths


@utils.registerPlexObject
class Photo(PlexPartialObject, Playable):
    """ Represents a single Photo.

        Attributes:
            TAG (str): 'Photo'
            TYPE (str): 'photo'
            addedAt (datetime): Datetime the photo was added to the library.
            createdAtAccuracy (str): Unknown (local).
            createdAtTZOffset (int): Unknown (-25200).
            fields (List<:class:`~plexapi.media.Field`>): List of field objects.
            guid (str): Plex GUID for the photo (com.plexapp.agents.none://231714?lang=xn).
            index (sting): Plex index number for the photo.
            key (str): API URL (/library/metadata/<ratingkey>).
            librarySectionID (int): :class:`~plexapi.library.LibrarySection` ID.
            librarySectionKey (str): :class:`~plexapi.library.LibrarySection` key.
            librarySectionTitle (str): :class:`~plexapi.library.LibrarySection` title.
            listType (str): Hardcoded as 'photo' (useful for search filters).
            media (List<:class:`~plexapi.media.Media`>): List of media objects.
            originallyAvailableAt (datetime): Datetime the photo was added to Plex.
            parentGuid (str): Plex GUID for the photo album (local://229674).
            parentIndex (int): Plex index number for the photo album.
            parentKey (str): API URL of the photo album (/library/metadata/<parentRatingKey>).
            parentRatingKey (int): Unique key identifying the photo album.
            parentThumb (str): URL to photo album thumbnail image (/library/metadata/<parentRatingKey>/thumb/<thumbid>).
            parentTitle (str): Name of the photo album for the photo.
            ratingKey (int): Unique key identifying the photo.
            summary (str): Summary of the photo.
            tag (List<:class:`~plexapi.media.Tag`>): List of tag objects.
            thumb (str): URL to thumbnail image (/library/metadata/<ratingKey>/thumb/<thumbid>).
            title (str): Name of the photo.
            titleSort (str): Title to use when sorting (defaults to title).
            type (str): 'photo'
            updatedAt (datatime): Datetime the photo was updated.
            year (int): Year the photo was taken.
    """
    TAG = 'Photo'
    TYPE = 'photo'
    METADATA_TYPE = 'photo'

    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        Playable._loadData(self, data)
        self.addedAt = utils.toDatetime(data.attrib.get('addedAt'))
        self.createdAtAccuracy = data.attrib.get('createdAtAccuracy')
        self.createdAtTZOffset = utils.cast(int, data.attrib.get('createdAtTZOffset'))
        self.fields = self.findItems(data, media.Field)
        self.guid = data.attrib.get('guid')
        self.index = utils.cast(int, data.attrib.get('index'))
        self.key = data.attrib.get('key', '')
        self.librarySectionID = data.attrib.get('librarySectionID')
        self.librarySectionKey = data.attrib.get('librarySectionKey')
        self.librarySectionTitle = data.attrib.get('librarySectionTitle')
        self.listType = 'photo'
        self.media = self.findItems(data, media.Media)
        self.originallyAvailableAt = utils.toDatetime(data.attrib.get('originallyAvailableAt'), '%Y-%m-%d')
        self.parentGuid = data.attrib.get('parentGuid')
        self.parentIndex = utils.cast(int, data.attrib.get('parentIndex'))
        self.parentKey = data.attrib.get('parentKey')
        self.parentRatingKey = utils.cast(int, data.attrib.get('parentRatingKey'))
        self.parentThumb = data.attrib.get('parentThumb')
        self.parentTitle = data.attrib.get('parentTitle')
        self.ratingKey = utils.cast(int, data.attrib.get('ratingKey'))
        self.summary = data.attrib.get('summary')
        self.tag = self.findItems(data, media.Tag)
        self.thumb = data.attrib.get('thumb')
        self.title = data.attrib.get('title')
        self.titleSort = data.attrib.get('titleSort', self.title)
        self.type = data.attrib.get('type')
        self.updatedAt = utils.toDatetime(data.attrib.get('updatedAt'))
        self.year = utils.cast(int, data.attrib.get('year'))

    @property
    def thumbUrl(self):
        """Return URL for the thumbnail image."""
        key = self.firstAttr('thumb', 'parentThumb', 'granparentThumb')
        return self._server.url(key, includeToken=True) if key else None

    def photoalbum(self):
        """ Return the photo's :class:`~plexapi.photo.Photoalbum`. """
        return self.fetchItem(self.parentKey)

    def section(self):
        """ Returns the :class:`~plexapi.library.LibrarySection` the item belongs to. """
        if hasattr(self, 'librarySectionID'):
            return self._server.library.sectionByID(self.librarySectionID)
        elif self.parentKey:
            return self._server.library.sectionByID(self.photoalbum().librarySectionID)
        else:
            raise BadRequest('Unable to get section for photo, can`t find librarySectionID')

    @property
    def locations(self):
        """ This does not exist in plex xml response but is added to have a common
            interface to get the locations of the photo.

            Retruns:
                List<str> of file paths where the photo is found on disk.
        """
        return [part.file for item in self.media for part in item.parts if part]
        
    def iterParts(self):
        """ Iterates over the parts of the media item. """
        for item in self.media:
            for part in item.parts:
                yield part

    def sync(self, resolution, client=None, clientId=None, limit=None, title=None):
        """ Add current photo as sync item for specified device.
            See :func:`~plexapi.myplex.MyPlexAccount.sync` for possible exceptions.

            Parameters:
                resolution (str): maximum allowed resolution for synchronized photos, see PHOTO_QUALITY_* values in the
                                  module :mod:`~plexapi.sync`.
                client (:class:`~plexapi.myplex.MyPlexDevice`): sync destination, see
                                                               :func:`~plexapi.myplex.MyPlexAccount.sync`.
                clientId (str): sync destination, see :func:`~plexapi.myplex.MyPlexAccount.sync`.
                limit (int): maximum count of items to sync, unlimited if `None`.
                title (str): descriptive title for the new :class:`~plexapi.sync.SyncItem`, if empty the value would be
                             generated from metadata of current photo.

            Returns:
                :class:`~plexapi.sync.SyncItem`: an instance of created syncItem.
        """

        from plexapi.sync import SyncItem, Policy, MediaSettings

        myplex = self._server.myPlexAccount()
        sync_item = SyncItem(self._server, None)
        sync_item.title = title if title else self.title
        sync_item.rootTitle = self.title
        sync_item.contentType = self.listType
        sync_item.metadataType = self.METADATA_TYPE
        sync_item.machineIdentifier = self._server.machineIdentifier

        section = self.section()

        sync_item.location = 'library://%s/item/%s' % (section.uuid, quote_plus(self.key))
        sync_item.policy = Policy.create(limit)
        sync_item.mediaSettings = MediaSettings.createPhoto(resolution)

        return myplex.sync(sync_item, client=client, clientId=clientId)

    def download(self, savepath=None, keep_original_name=False, showstatus=False):
        """ Download photo files to specified directory.

            Parameters:
                savepath (str): Defaults to current working dir.
                keep_original_name (bool): True to keep the original file name otherwise
                    a friendlier is generated.
                showstatus(bool): Display a progressbar.
        """
        filepaths = []
        locations = [i for i in self.iterParts() if i]
        for location in locations:
            name = location.file
            if not keep_original_name:
                title = self.title.replace(' ', '.')
                name = '%s.%s' % (title, location.container)
            url = self._server.url('%s?download=1' % location.key)
            filepath = utils.download(url, self._server._token, filename=name, showstatus=showstatus,
                                      savepath=savepath, session=self._server._session)
            if filepath:
                filepaths.append(filepath)
        return filepaths
