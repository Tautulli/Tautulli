# -*- coding: utf-8 -*-
from plexapi import media, utils
from plexapi.base import PlexPartialObject
from plexapi.exceptions import BadRequest
from plexapi.mixins import ArtMixin, PosterMixin
from plexapi.mixins import LabelMixin
from plexapi.settings import Setting
from plexapi.utils import deprecated


@utils.registerPlexObject
class Collections(PlexPartialObject, ArtMixin, PosterMixin, LabelMixin):
    """ Represents a single Collection.

        Attributes:
            TAG (str): 'Directory'
            TYPE (str): 'collection'
            addedAt (datetime): Datetime the collection was added to the library.
            art (str): URL to artwork image (/library/metadata/<ratingKey>/art/<artid>).
            artBlurHash (str): BlurHash string for artwork image.
            childCount (int): Number of items in the collection.
            collectionMode (str): How the items in the collection are displayed.
            collectionSort (str): How to sort the items in the collection.
            contentRating (str) Content rating (PG-13; NR; TV-G).
            fields (List<:class:`~plexapi.media.Field`>): List of field objects.
            guid (str): Plex GUID for the collection (collection://XXXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXX).
            index (int): Plex index number for the collection.
            key (str): API URL (/library/metadata/<ratingkey>).
            labels (List<:class:`~plexapi.media.Label`>): List of label objects.
            librarySectionID (int): :class:`~plexapi.library.LibrarySection` ID.
            librarySectionKey (str): :class:`~plexapi.library.LibrarySection` key.
            librarySectionTitle (str): :class:`~plexapi.library.LibrarySection` title.
            maxYear (int): Maximum year for the items in the collection.
            minYear (int): Minimum year for the items in the collection.
            ratingKey (int): Unique key identifying the collection.
            subtype (str): Media type of the items in the collection (movie, show, artist, or album).
            summary (str): Summary of the collection.
            thumb (str): URL to thumbnail image (/library/metadata/<ratingKey>/thumb/<thumbid>).
            thumbBlurHash (str): BlurHash string for thumbnail image.
            title (str): Name of the collection.
            titleSort (str): Title to use when sorting (defaults to title).
            type (str): 'collection'
            updatedAt (datatime): Datetime the collection was updated.
    """

    TAG = 'Directory'
    TYPE = 'collection'

    def _loadData(self, data):
        self.addedAt = utils.toDatetime(data.attrib.get('addedAt'))
        self.art = data.attrib.get('art')
        self.artBlurHash = data.attrib.get('artBlurHash')
        self.childCount = utils.cast(int, data.attrib.get('childCount'))
        self.collectionMode = utils.cast(int, data.attrib.get('collectionMode', '-1'))
        self.collectionSort = utils.cast(int, data.attrib.get('collectionSort', '0'))
        self.contentRating = data.attrib.get('contentRating')
        self.fields = self.findItems(data, media.Field)
        self.guid = data.attrib.get('guid')
        self.index = utils.cast(int, data.attrib.get('index'))
        self.key = data.attrib.get('key', '').replace('/children', '')  # FIX_BUG_50
        self.labels = self.findItems(data, media.Label)
        self.librarySectionID = utils.cast(int, data.attrib.get('librarySectionID'))
        self.librarySectionKey = data.attrib.get('librarySectionKey')
        self.librarySectionTitle = data.attrib.get('librarySectionTitle')
        self.maxYear = utils.cast(int, data.attrib.get('maxYear'))
        self.minYear = utils.cast(int, data.attrib.get('minYear'))
        self.ratingKey = utils.cast(int, data.attrib.get('ratingKey'))
        self.subtype = data.attrib.get('subtype')
        self.summary = data.attrib.get('summary')
        self.thumb = data.attrib.get('thumb')
        self.thumbBlurHash = data.attrib.get('thumbBlurHash')
        self.title = data.attrib.get('title')
        self.titleSort = data.attrib.get('titleSort', self.title)
        self.type = data.attrib.get('type')
        self.updatedAt = utils.toDatetime(data.attrib.get('updatedAt'))

    @property
    @deprecated('use "items" instead', stacklevel=3)
    def children(self):
        return self.items()

    def item(self, title):
        """ Returns the item in the collection that matches the specified title.

            Parameters:
                title (str): Title of the item to return.
        """
        key = '/library/metadata/%s/children' % self.ratingKey
        return self.fetchItem(key, title__iexact=title)

    def items(self):
        """ Returns a list of all items in the collection. """
        key = '/library/metadata/%s/children' % self.ratingKey
        return self.fetchItems(key)

    def get(self, title):
        """ Alias to :func:`~plexapi.library.Collection.item`. """
        return self.item(title)

    def __len__(self):
        return self.childCount

    def _preferences(self):
        """ Returns a list of :class:`~plexapi.settings.Preferences` objects. """
        items = []
        data = self._server.query(self._details_key)
        for item in data.iter('Setting'):
            items.append(Setting(data=item, server=self._server))

        return items

    def modeUpdate(self, mode=None):
        """ Update Collection Mode

            Parameters:
                mode: default     (Library default)
                      hide        (Hide Collection)
                      hideItems   (Hide Items in this Collection)
                      showItems   (Show this Collection and its Items)
            Example:

                collection = 'plexapi.library.Collections'
                collection.updateMode(mode="hide")
        """
        mode_dict = {'default': -1,
                     'hide': 0,
                     'hideItems': 1,
                     'showItems': 2}
        key = mode_dict.get(mode)
        if key is None:
            raise BadRequest('Unknown collection mode : %s. Options %s' % (mode, list(mode_dict)))
        part = '/library/metadata/%s/prefs?collectionMode=%s' % (self.ratingKey, key)
        return self._server.query(part, method=self._server._session.put)

    def sortUpdate(self, sort=None):
        """ Update Collection Sorting

            Parameters:
                sort: realease     (Order Collection by realease dates)
                      alpha        (Order Collection alphabetically)
                      custom       (Custom collection order)

            Example:

                colleciton = 'plexapi.library.Collections'
                collection.updateSort(mode="alpha")
        """
        sort_dict = {'release': 0,
                     'alpha': 1,
                     'custom': 2}
        key = sort_dict.get(sort)
        if key is None:
            raise BadRequest('Unknown sort dir: %s. Options: %s' % (sort, list(sort_dict)))
        part = '/library/metadata/%s/prefs?collectionSort=%s' % (self.ratingKey, key)
        return self._server.query(part, method=self._server._session.put)
