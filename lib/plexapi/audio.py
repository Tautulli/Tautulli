# -*- coding: utf-8 -*-
from urllib.parse import quote_plus

from plexapi import library, media, utils
from plexapi.base import Playable, PlexPartialObject
from plexapi.exceptions import BadRequest


class Audio(PlexPartialObject):
    """ Base class for all audio objects including :class:`~plexapi.audio.Artist`,
        :class:`~plexapi.audio.Album`, and :class:`~plexapi.audio.Track`.

        Attributes:
            addedAt (datetime): Datetime the item was added to the library.
            art (str): URL to artwork image (/library/metadata/<ratingKey>/art/<artid>).
            artBlurHash (str): BlurHash string for artwork image.
            fields (List<:class:`~plexapi.media.Field`>): List of field objects.
            guid (str): Plex GUID for the artist, album, or track (plex://artist/5d07bcb0403c64029053ac4c).
            index (int): Plex index number (often the track number).
            key (str): API URL (/library/metadata/<ratingkey>).
            lastViewedAt (datetime): Datetime the item was last played.
            librarySectionID (int): :class:`~plexapi.library.LibrarySection` ID.
            librarySectionKey (str): :class:`~plexapi.library.LibrarySection` key.
            librarySectionTitle (str): :class:`~plexapi.library.LibrarySection` title.
            listType (str): Hardcoded as 'audio' (useful for search filters).
            moods (List<:class:`~plexapi.media.Mood`>): List of mood objects.
            ratingKey (int): Unique key identifying the item.
            summary (str): Summary of the artist, album, or track.
            thumb (str): URL to thumbnail image (/library/metadata/<ratingKey>/thumb/<thumbid>).
            thumbBlurHash (str): BlurHash string for thumbnail image.
            title (str): Name of the artist, album, or track (Jason Mraz, We Sing, Lucky, etc.).
            titleSort (str): Title to use when sorting (defaults to title).
            type (str): 'artist', 'album', or 'track'.
            updatedAt (datatime): Datetime the item was updated.
            userRating (float): Rating of the track (0.0 - 10.0) equaling (0 stars - 5 stars).
            viewCount (int): Count of times the item was played.
    """

    METADATA_TYPE = 'track'

    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        self._data = data
        self.addedAt = utils.toDatetime(data.attrib.get('addedAt'))
        self.art = data.attrib.get('art')
        self.artBlurHash = data.attrib.get('artBlurHash')
        self.fields = self.findItems(data, media.Field)
        self.guid = data.attrib.get('guid')
        self.index = utils.cast(int, data.attrib.get('index'))
        self.key = data.attrib.get('key', '')
        self.lastViewedAt = utils.toDatetime(data.attrib.get('lastViewedAt'))
        self.librarySectionID = data.attrib.get('librarySectionID')
        self.librarySectionKey = data.attrib.get('librarySectionKey')
        self.librarySectionTitle = data.attrib.get('librarySectionTitle')
        self.listType = 'audio'
        self.moods = self.findItems(data, media.Mood)
        self.ratingKey = utils.cast(int, data.attrib.get('ratingKey'))
        self.summary = data.attrib.get('summary')
        self.thumb = data.attrib.get('thumb')
        self.thumbBlurHash = data.attrib.get('thumbBlurHash')
        self.title = data.attrib.get('title')
        self.titleSort = data.attrib.get('titleSort', self.title)
        self.type = data.attrib.get('type')
        self.updatedAt = utils.toDatetime(data.attrib.get('updatedAt'))
        self.userRating = utils.cast(float, data.attrib.get('userRating', 0))
        self.viewCount = utils.cast(int, data.attrib.get('viewCount', 0))

    @property
    def thumbUrl(self):
        """ Return url to for the thumbnail image. """
        key = self.firstAttr('thumb', 'parentThumb', 'granparentThumb')
        return self._server.url(key, includeToken=True) if key else None

    @property
    def artUrl(self):
        """ Return the first art url starting on the most specific for that item."""
        art = self.firstAttr('art', 'grandparentArt')
        return self._server.url(art, includeToken=True) if art else None

    def url(self, part):
        """ Returns the full URL for the audio item. Typically used for getting a specific track. """
        return self._server.url(part, includeToken=True) if part else None

    def _defaultSyncTitle(self):
        """ Returns str, default title for a new syncItem. """
        return self.title

    def sync(self, bitrate, client=None, clientId=None, limit=None, title=None):
        """ Add current audio (artist, album or track) as sync item for specified device.
            See :func:`~plexapi.myplex.MyPlexAccount.sync` for possible exceptions.

            Parameters:
                bitrate (int): maximum bitrate for synchronized music, better use one of MUSIC_BITRATE_* values from the
                               module :mod:`~plexapi.sync`.
                client (:class:`~plexapi.myplex.MyPlexDevice`): sync destination, see
                                                               :func:`~plexapi.myplex.MyPlexAccount.sync`.
                clientId (str): sync destination, see :func:`~plexapi.myplex.MyPlexAccount.sync`.
                limit (int): maximum count of items to sync, unlimited if `None`.
                title (str): descriptive title for the new :class:`~plexapi.sync.SyncItem`, if empty the value would be
                             generated from metadata of current media.

            Returns:
                :class:`~plexapi.sync.SyncItem`: an instance of created syncItem.
        """

        from plexapi.sync import SyncItem, Policy, MediaSettings

        myplex = self._server.myPlexAccount()
        sync_item = SyncItem(self._server, None)
        sync_item.title = title if title else self._defaultSyncTitle()
        sync_item.rootTitle = self.title
        sync_item.contentType = self.listType
        sync_item.metadataType = self.METADATA_TYPE
        sync_item.machineIdentifier = self._server.machineIdentifier

        section = self._server.library.sectionByID(self.librarySectionID)

        sync_item.location = 'library://%s/item/%s' % (section.uuid, quote_plus(self.key))
        sync_item.policy = Policy.create(limit)
        sync_item.mediaSettings = MediaSettings.createMusic(bitrate)

        return myplex.sync(sync_item, client=client, clientId=clientId)


@utils.registerPlexObject
class Artist(Audio):
    """ Represents a single Artist.

        Attributes:
            TAG (str): 'Directory'
            TYPE (str): 'artist'
            collections (List<:class:`~plexapi.media.Collection`>): List of collection objects.
            countries (List<:class:`~plexapi.media.Country`>): List country objects.
            genres (List<:class:`~plexapi.media.Genre`>): List of genre objects.
            key (str): API URL (/library/metadata/<ratingkey>).
            locations (List<str>): List of folder paths where the artist is found on disk.
            similar (List<:class:`~plexapi.media.Similar`>): List of similar objects.
            styles (List<:class:`~plexapi.media.Style`>): List of style objects.
    """
    TAG = 'Directory'
    TYPE = 'artist'

    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        Audio._loadData(self, data)
        self.collections = self.findItems(data, media.Collection)
        self.countries = self.findItems(data, media.Country)
        self.genres = self.findItems(data, media.Genre)
        self.key = self.key.replace('/children', '')  # FIX_BUG_50
        self.locations = self.listAttrs(data, 'path', etag='Location')
        self.similar = self.findItems(data, media.Similar)
        self.styles = self.findItems(data, media.Style)

    def __iter__(self):
        for album in self.albums():
            yield album

    def hubs(self):
        """ Returns a list of :class:`~plexapi.library.Hub` objects. """
        data = self._server.query(self._details_key)
        directory = data.find('Directory')
        if directory:
            related = directory.find('Related')
            if related:
                return self.findItems(related, library.Hub)

    def album(self, title):
        """ Returns the :class:`~plexapi.audio.Album` that matches the specified title.

            Parameters:
                title (str): Title of the album to return.
        """
        key = '/library/metadata/%s/children' % self.ratingKey
        return self.fetchItem(key, Album, title__iexact=title)

    def albums(self, **kwargs):
        """ Returns a list of :class:`~plexapi.audio.Album` objects by the artist. """
        key = '/library/metadata/%s/children' % self.ratingKey
        return self.fetchItems(key, Album, **kwargs)

    def track(self, title=None, album=None, track=None):
        """ Returns the :class:`~plexapi.audio.Track` that matches the specified title.

            Parameters:
                title (str): Title of the track to return.
                album (str): Album name (default: None; required if title not specified).
                track (int): Track number (default: None; required if title not specified).

            Raises:
                :exc:`~plexapi.exceptions.BadRequest`: If title or album and track parameters are missing.
        """
        key = '/library/metadata/%s/allLeaves' % self.ratingKey
        if title is not None:
            return self.fetchItem(key, Track, title__iexact=title)
        elif album is not None and track is not None:
            return self.fetchItem(key, Track, parentTitle__iexact=album, index=track)
        raise BadRequest('Missing argument: title or album and track are required')

    def tracks(self, **kwargs):
        """ Returns a list of :class:`~plexapi.audio.Track` objects by the artist. """
        key = '/library/metadata/%s/allLeaves' % self.ratingKey
        return self.fetchItems(key, Track, **kwargs)

    def get(self, title=None, album=None, track=None):
        """ Alias of :func:`~plexapi.audio.Artist.track`. """
        return self.track(title, album, track)

    def download(self, savepath=None, keep_original_name=False, **kwargs):
        """ Downloads all tracks for the artist to the specified location.

            Parameters:
                savepath (str): Title of the track to return.
                keep_original_name (bool): Set True to keep the original filename as stored in
                    the Plex server. False will create a new filename with the format
                    "<Atrist> - <Album> <Track>".
                kwargs (dict): If specified, a :func:`~plexapi.audio.Track.getStreamURL` will
                    be returned and the additional arguments passed in will be sent to that
                    function. If kwargs is not specified, the media items will be downloaded
                    and saved to disk.
        """
        filepaths = []
        for album in self.albums():
            for track in album.tracks():
                filepaths += track.download(savepath, keep_original_name, **kwargs)
        return filepaths


@utils.registerPlexObject
class Album(Audio):
    """ Represents a single Album.

        Attributes:
            TAG (str): 'Directory'
            TYPE (str): 'album'
            collections (List<:class:`~plexapi.media.Collection`>): List of collection objects.
            genres (List<:class:`~plexapi.media.Genre`>): List of genre objects.
            key (str): API URL (/library/metadata/<ratingkey>).
            labels (List<:class:`~plexapi.media.Label`>): List of label objects.
            leafCount (int): Number of items in the album view.
            loudnessAnalysisVersion (int): The Plex loudness analysis version level.
            originallyAvailableAt (datetime): Datetime the album was released.
            parentGuid (str): Plex GUID for the album artist (plex://artist/5d07bcb0403c64029053ac4c).
            parentKey (str): API URL of the album artist (/library/metadata/<parentRatingKey>).
            parentRatingKey (int): Unique key identifying the album artist.
            parentThumb (str): URL to album artist thumbnail image (/library/metadata/<parentRatingKey>/thumb/<thumbid>).
            parentTitle (str): Name of the album artist.
            rating (float): Album rating (7.9; 9.8; 8.1).
            studio (str): Studio that released the album.
            styles (List<:class:`~plexapi.media.Style`>): List of style objects.
            viewedLeafCount (int): Number of items marked as played in the album view.
            year (int): Year the album was released.
    """
    TAG = 'Directory'
    TYPE = 'album'

    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        Audio._loadData(self, data)
        self.collections = self.findItems(data, media.Collection)
        self.genres = self.findItems(data, media.Genre)
        self.key = self.key.replace('/children', '')  # FIX_BUG_50
        self.labels = self.findItems(data, media.Label)
        self.leafCount = utils.cast(int, data.attrib.get('leafCount'))
        self.loudnessAnalysisVersion = utils.cast(int, data.attrib.get('loudnessAnalysisVersion'))
        self.originallyAvailableAt = utils.toDatetime(data.attrib.get('originallyAvailableAt'), '%Y-%m-%d')
        self.parentGuid = data.attrib.get('parentGuid')
        self.parentKey = data.attrib.get('parentKey')
        self.parentRatingKey = utils.cast(int, data.attrib.get('parentRatingKey'))
        self.parentThumb = data.attrib.get('parentThumb')
        self.parentTitle = data.attrib.get('parentTitle')
        self.rating = utils.cast(float, data.attrib.get('rating'))
        self.studio = data.attrib.get('studio')
        self.styles = self.findItems(data, media.Style)
        self.viewedLeafCount = utils.cast(int, data.attrib.get('viewedLeafCount'))
        self.year = utils.cast(int, data.attrib.get('year'))

    def __iter__(self):
        for track in self.tracks():
            yield track

    def track(self, title=None, track=None):
        """ Returns the :class:`~plexapi.audio.Track` that matches the specified title.

            Parameters:
                title (str): Title of the track to return.
                track (int): Track number (default: None; required if title not specified).

            Raises:
                :exc:`~plexapi.exceptions.BadRequest`: If title or track parameter is missing.
        """
        key = '/library/metadata/%s/children' % self.ratingKey
        if title is not None:
            return self.fetchItem(key, Track, title__iexact=title)
        elif track is not None:
            return self.fetchItem(key, Track, parentTitle__iexact=self.title, index=track)
        raise BadRequest('Missing argument: title or track is required')

    def tracks(self, **kwargs):
        """ Returns a list of :class:`~plexapi.audio.Track` objects in the album. """
        key = '/library/metadata/%s/children' % self.ratingKey
        return self.fetchItems(key, Track, **kwargs)

    def get(self, title=None, track=None):
        """ Alias of :func:`~plexapi.audio.Album.track`. """
        return self.track(title, track)

    def artist(self):
        """ Return the album's :class:`~plexapi.audio.Artist`. """
        return self.fetchItem(self.parentKey)

    def download(self, savepath=None, keep_original_name=False, **kwargs):
        """ Downloads all tracks for the artist to the specified location.

            Parameters:
                savepath (str): Title of the track to return.
                keep_original_name (bool): Set True to keep the original filename as stored in
                    the Plex server. False will create a new filename with the format
                    "<Atrist> - <Album> <Track>".
                kwargs (dict): If specified, a :func:`~plexapi.audio.Track.getStreamURL` will
                    be returned and the additional arguments passed in will be sent to that
                    function. If kwargs is not specified, the media items will be downloaded
                    and saved to disk.
        """
        filepaths = []
        for track in self.tracks():
            filepaths += track.download(savepath, keep_original_name, **kwargs)
        return filepaths

    def _defaultSyncTitle(self):
        """ Returns str, default title for a new syncItem. """
        return '%s - %s' % (self.parentTitle, self.title)


@utils.registerPlexObject
class Track(Audio, Playable):
    """ Represents a single Track.

        Attributes:
            TAG (str): 'Directory'
            TYPE (str): 'track'
            chapterSource (str): Unknown
            duration (int): Length of the track in milliseconds.
            grandparentArt (str): URL to album artist artwork (/library/metadata/<grandparentRatingKey>/art/<artid>).
            grandparentGuid (str): Plex GUID for the album artist (plex://artist/5d07bcb0403c64029053ac4c).
            grandparentKey (str): API URL of the album artist (/library/metadata/<grandparentRatingKey>).
            grandparentRatingKey (int): Unique key identifying the album artist.
            grandparentThumb (str): URL to album artist thumbnail image
                (/library/metadata/<grandparentRatingKey>/thumb/<thumbid>).
            grandparentTitle (str): Name of the album artist for the track.
            media (List<:class:`~plexapi.media.Media`>): List of media objects.
            originalTitle (str): The original title of the track (eg. a different language).
            parentGuid (str): Plex GUID for the album (plex://album/5d07cd8e403c640290f180f9).
            parentIndex (int): Album index.
            parentKey (str): API URL of the album (/library/metadata/<parentRatingKey>).
            parentRatingKey (int): Unique key identifying the album.
            parentThumb (str): URL to album thumbnail image (/library/metadata/<parentRatingKey>/thumb/<thumbid>).
            parentTitle (str): Name of the album for the track.
            primaryExtraKey (str) API URL for the primary extra for the track.
            ratingCount (int): Number of ratings contributing to the rating score.
            viewOffset (int): View offset in milliseconds.
            year (int): Year the track was released.
    """
    TAG = 'Track'
    TYPE = 'track'

    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        Audio._loadData(self, data)
        Playable._loadData(self, data)
        self.chapterSource = data.attrib.get('chapterSource')
        self.duration = utils.cast(int, data.attrib.get('duration'))
        self.grandparentArt = data.attrib.get('grandparentArt')
        self.grandparentGuid = data.attrib.get('grandparentGuid')
        self.grandparentKey = data.attrib.get('grandparentKey')
        self.grandparentRatingKey = utils.cast(int, data.attrib.get('grandparentRatingKey'))
        self.grandparentThumb = data.attrib.get('grandparentThumb')
        self.grandparentTitle = data.attrib.get('grandparentTitle')
        self.media = self.findItems(data, media.Media)
        self.originalTitle = data.attrib.get('originalTitle')
        self.parentGuid = data.attrib.get('parentGuid')
        self.parentIndex = data.attrib.get('parentIndex')
        self.parentKey = data.attrib.get('parentKey')
        self.parentRatingKey = utils.cast(int, data.attrib.get('parentRatingKey'))
        self.parentThumb = data.attrib.get('parentThumb')
        self.parentTitle = data.attrib.get('parentTitle')
        self.primaryExtraKey = data.attrib.get('primaryExtraKey')
        self.ratingCount = utils.cast(int, data.attrib.get('ratingCount'))
        self.viewOffset = utils.cast(int, data.attrib.get('viewOffset', 0))
        self.year = utils.cast(int, data.attrib.get('year'))

    def _prettyfilename(self):
        """ Returns a filename for use in download. """
        return '%s - %s %s' % (self.grandparentTitle, self.parentTitle, self.title)

    def album(self):
        """ Return the track's :class:`~plexapi.audio.Album`. """
        return self.fetchItem(self.parentKey)

    def artist(self):
        """ Return the track's :class:`~plexapi.audio.Artist`. """
        return self.fetchItem(self.grandparentKey)

    @property
    def locations(self):
        """ This does not exist in plex xml response but is added to have a common
            interface to get the locations of the track.

            Retruns:
                List<str> of file paths where the track is found on disk.
        """
        return [part.file for part in self.iterParts() if part]

    def _defaultSyncTitle(self):
        """ Returns str, default title for a new syncItem. """
        return '%s - %s - %s' % (self.grandparentTitle, self.parentTitle, self.title)
