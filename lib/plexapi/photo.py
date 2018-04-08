# -*- coding: utf-8 -*-
from plexapi import media, utils
from plexapi.base import PlexPartialObject
from plexapi.exceptions import NotFound


@utils.registerPlexObject
class Photoalbum(PlexPartialObject):
    """ Represents a photoalbum (collection of photos).

        Attributes:
            TAG (str): 'Directory'
            TYPE (str): 'photo'
            addedAt (datetime): Datetime this item was added to the library.
            art (str): Photo art (/library/metadata/<ratingkey>/art/<artid>)
            composite (str): Unknown
            guid (str): Unknown (unique ID)
            index (sting): Index number of this album.
            key (str): API URL (/library/metadata/<ratingkey>).
            librarySectionID (int): :class:`~plexapi.library.LibrarySection` ID.
            listType (str): Hardcoded as 'photo' (useful for search filters).
            ratingKey (int): Unique key identifying this item.
            summary (str): Summary of the photoalbum.
            thumb (str): URL to thumbnail image.
            title (str): Photoalbum title. (Trip to Disney World)
            type (str): Unknown
            updatedAt (datatime): Datetime this item was updated.
    """
    TAG = 'Directory'
    TYPE = 'photo'

    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        self.listType = 'photo'
        self.addedAt = utils.toDatetime(data.attrib.get('addedAt'))
        self.art = data.attrib.get('art')
        self.composite = data.attrib.get('composite')
        self.guid = data.attrib.get('guid')
        self.index = utils.cast(int, data.attrib.get('index'))
        self.key = data.attrib.get('key')
        self.librarySectionID = data.attrib.get('librarySectionID')
        self.ratingKey = data.attrib.get('ratingKey')
        self.summary = data.attrib.get('summary')
        self.thumb = data.attrib.get('thumb')
        self.title = data.attrib.get('title')
        self.type = data.attrib.get('type')
        self.updatedAt = utils.toDatetime(data.attrib.get('updatedAt'))

    def albums(self, **kwargs):
        """ Returns a list of :class:`~plexapi.photo.Photoalbum` objects in this album. """
        key = '/library/metadata/%s/children' % self.ratingKey
        return self.fetchItems(key, etag='Directory', **kwargs)

    def album(self, title):
        """ Returns the :class:`~plexapi.photo.Photoalbum` that matches the specified title. """
        for album in self.albums():
            if album.title.lower() == title.lower():
                return album
        raise NotFound('Unable to find album: %s' % title)

    def photos(self, **kwargs):
        """ Returns a list of :class:`~plexapi.photo.Photo` objects in this album. """
        key = '/library/metadata/%s/children' % self.ratingKey
        return self.fetchItems(key, etag='Photo', **kwargs)

    def photo(self, title):
        """ Returns the :class:`~plexapi.photo.Photo` that matches the specified title. """
        for photo in self.photos():
            if photo.title.lower() == title.lower():
                return photo
        raise NotFound('Unable to find photo: %s' % title)


@utils.registerPlexObject
class Photo(PlexPartialObject):
    """ Represents a single photo.

        Attributes:
            TAG (str): 'Photo'
            TYPE (str): 'photo'
            addedAt (datetime): Datetime this item was added to the library.
            index (sting): Index number of this photo.
            key (str): API URL (/library/metadata/<ratingkey>).
            listType (str): Hardcoded as 'photo' (useful for search filters).
            media (TYPE): Unknown
            originallyAvailableAt (datetime): Datetime this photo was added to Plex.
            parentKey (str): Photoalbum API URL.
            parentRatingKey (int): Unique key identifying the photoalbum.
            ratingKey (int): Unique key identifying this item.
            summary (str): Summary of the photo.
            thumb (str): URL to thumbnail image.
            title (str): Photo title.
            type (str): Unknown
            updatedAt (datatime): Datetime this item was updated.
            year (int): Year this photo was taken.
    """
    TAG = 'Photo'
    TYPE = 'photo'

    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        self.listType = 'photo'
        self.addedAt = utils.toDatetime(data.attrib.get('addedAt'))
        self.index = utils.cast(int, data.attrib.get('index'))
        self.key = data.attrib.get('key')
        self.originallyAvailableAt = utils.toDatetime(
            data.attrib.get('originallyAvailableAt'), '%Y-%m-%d')
        self.parentKey = data.attrib.get('parentKey')
        self.parentRatingKey = data.attrib.get('parentRatingKey')
        self.ratingKey = data.attrib.get('ratingKey')
        self.summary = data.attrib.get('summary')
        self.thumb = data.attrib.get('thumb')
        self.title = data.attrib.get('title')
        self.type = data.attrib.get('type')
        self.updatedAt = utils.toDatetime(data.attrib.get('updatedAt'))
        self.year = utils.cast(int, data.attrib.get('year'))
        self.media = self.findItems(data, media.Media)

    def photoalbum(self):
        """ Return this photo's :class:`~plexapi.photo.Photoalbum`. """
        return self.fetchItem(self.parentKey)

    def section(self):
        """ Returns the :class:`~plexapi.library.LibrarySection` this item belongs to. """
        return self._server.library.sectionByID(self.photoalbum().librarySectionID)
