# -*- coding: utf-8 -*-
import os
from urllib.parse import quote_plus

from plexapi import media, utils
from plexapi.base import Playable, PlexPartialObject, PlexSession
from plexapi.exceptions import BadRequest, NotFound
from plexapi.mixins import (
    AdvancedSettingsMixin, SplitMergeMixin, UnmatchMatchMixin, ExtrasMixin, HubsMixin, PlayedUnplayedMixin, RatingMixin,
    ArtUrlMixin, ArtMixin, PosterUrlMixin, PosterMixin, ThemeMixin, ThemeUrlMixin,
    AddedAtMixin, OriginallyAvailableMixin, SortTitleMixin, StudioMixin, SummaryMixin, TitleMixin,
    TrackArtistMixin, TrackDiscNumberMixin, TrackNumberMixin,
    CollectionMixin, CountryMixin, GenreMixin, LabelMixin, MoodMixin, SimilarArtistMixin, StyleMixin
)
from plexapi.playlist import Playlist


class Audio(PlexPartialObject, PlayedUnplayedMixin, AddedAtMixin):
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
            lastRatedAt (datetime): Datetime the item was last rated.
            lastViewedAt (datetime): Datetime the item was last played.
            librarySectionID (int): :class:`~plexapi.library.LibrarySection` ID.
            librarySectionKey (str): :class:`~plexapi.library.LibrarySection` key.
            librarySectionTitle (str): :class:`~plexapi.library.LibrarySection` title.
            listType (str): Hardcoded as 'audio' (useful for search filters).
            moods (List<:class:`~plexapi.media.Mood`>): List of mood objects.
            musicAnalysisVersion (int): The Plex music analysis version for the item.
            ratingKey (int): Unique key identifying the item.
            summary (str): Summary of the artist, album, or track.
            thumb (str): URL to thumbnail image (/library/metadata/<ratingKey>/thumb/<thumbid>).
            thumbBlurHash (str): BlurHash string for thumbnail image.
            title (str): Name of the artist, album, or track (Jason Mraz, We Sing, Lucky, etc.).
            titleSort (str): Title to use when sorting (defaults to title).
            type (str): 'artist', 'album', or 'track'.
            updatedAt (datetime): Datetime the item was updated.
            userRating (float): Rating of the item (0.0 - 10.0) equaling (0 stars - 5 stars).
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
        self.lastRatedAt = utils.toDatetime(data.attrib.get('lastRatedAt'))
        self.lastViewedAt = utils.toDatetime(data.attrib.get('lastViewedAt'))
        self.librarySectionID = utils.cast(int, data.attrib.get('librarySectionID'))
        self.librarySectionKey = data.attrib.get('librarySectionKey')
        self.librarySectionTitle = data.attrib.get('librarySectionTitle')
        self.listType = 'audio'
        self.moods = self.findItems(data, media.Mood)
        self.musicAnalysisVersion = utils.cast(int, data.attrib.get('musicAnalysisVersion'))
        self.ratingKey = utils.cast(int, data.attrib.get('ratingKey'))
        self.summary = data.attrib.get('summary')
        self.thumb = data.attrib.get('thumb')
        self.thumbBlurHash = data.attrib.get('thumbBlurHash')
        self.title = data.attrib.get('title')
        self.titleSort = data.attrib.get('titleSort', self.title)
        self.type = data.attrib.get('type')
        self.updatedAt = utils.toDatetime(data.attrib.get('updatedAt'))
        self.userRating = utils.cast(float, data.attrib.get('userRating'))
        self.viewCount = utils.cast(int, data.attrib.get('viewCount', 0))

    def url(self, part):
        """ Returns the full URL for the audio item. Typically used for getting a specific track. """
        return self._server.url(part, includeToken=True) if part else None

    def _defaultSyncTitle(self):
        """ Returns str, default title for a new syncItem. """
        return self.title

    @property
    def hasSonicAnalysis(self):
        """ Returns True if the audio has been sonically analyzed. """
        return self.musicAnalysisVersion == 1

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

        sync_item.location = f'library://{section.uuid}/item/{quote_plus(self.key)}'
        sync_item.policy = Policy.create(limit)
        sync_item.mediaSettings = MediaSettings.createMusic(bitrate)

        return myplex.sync(sync_item, client=client, clientId=clientId)


@utils.registerPlexObject
class Artist(
    Audio,
    AdvancedSettingsMixin, SplitMergeMixin, UnmatchMatchMixin, ExtrasMixin, HubsMixin, RatingMixin,
    ArtMixin, PosterMixin, ThemeMixin,
    SortTitleMixin, SummaryMixin, TitleMixin,
    CollectionMixin, CountryMixin, GenreMixin, LabelMixin, MoodMixin, SimilarArtistMixin, StyleMixin
):
    """ Represents a single Artist.

        Attributes:
            TAG (str): 'Directory'
            TYPE (str): 'artist'
            albumSort (int): Setting that indicates how albums are sorted for the artist
                (-1 = Library default, 0 = Newest first, 1 = Oldest first, 2 = By name).
            collections (List<:class:`~plexapi.media.Collection`>): List of collection objects.
            countries (List<:class:`~plexapi.media.Country`>): List country objects.
            genres (List<:class:`~plexapi.media.Genre`>): List of genre objects.
            guids (List<:class:`~plexapi.media.Guid`>): List of guid objects.
            key (str): API URL (/library/metadata/<ratingkey>).
            labels (List<:class:`~plexapi.media.Label`>): List of label objects.
            locations (List<str>): List of folder paths where the artist is found on disk.
            similar (List<:class:`~plexapi.media.Similar`>): List of similar objects.
            styles (List<:class:`~plexapi.media.Style`>): List of style objects.
            theme (str): URL to theme resource (/library/metadata/<ratingkey>/theme/<themeid>).
    """
    TAG = 'Directory'
    TYPE = 'artist'

    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        Audio._loadData(self, data)
        self.albumSort = utils.cast(int, data.attrib.get('albumSort', '-1'))
        self.collections = self.findItems(data, media.Collection)
        self.countries = self.findItems(data, media.Country)
        self.genres = self.findItems(data, media.Genre)
        self.guids = self.findItems(data, media.Guid)
        self.key = self.key.replace('/children', '')  # FIX_BUG_50
        self.labels = self.findItems(data, media.Label)
        self.locations = self.listAttrs(data, 'path', etag='Location')
        self.similar = self.findItems(data, media.Similar)
        self.styles = self.findItems(data, media.Style)
        self.theme = data.attrib.get('theme')

    def __iter__(self):
        for album in self.albums():
            yield album

    def album(self, title):
        """ Returns the :class:`~plexapi.audio.Album` that matches the specified title.

            Parameters:
                title (str): Title of the album to return.
        """
        try:
            return self.section().search(title, libtype='album', filters={'artist.id': self.ratingKey})[0]
        except IndexError:
            raise NotFound(f"Unable to find album '{title}'") from None

    def albums(self, **kwargs):
        """ Returns a list of :class:`~plexapi.audio.Album` objects by the artist. """
        return self.section().search(libtype='album', filters={'artist.id': self.ratingKey}, **kwargs)

    def track(self, title=None, album=None, track=None):
        """ Returns the :class:`~plexapi.audio.Track` that matches the specified title.

            Parameters:
                title (str): Title of the track to return.
                album (str): Album name (default: None; required if title not specified).
                track (int): Track number (default: None; required if title not specified).

            Raises:
                :exc:`~plexapi.exceptions.BadRequest`: If title or album and track parameters are missing.
        """
        key = f'{self.key}/allLeaves'
        if title is not None:
            return self.fetchItem(key, Track, title__iexact=title)
        elif album is not None and track is not None:
            return self.fetchItem(key, Track, parentTitle__iexact=album, index=track)
        raise BadRequest('Missing argument: title or album and track are required')

    def tracks(self, **kwargs):
        """ Returns a list of :class:`~plexapi.audio.Track` objects by the artist. """
        key = f'{self.key}/allLeaves'
        return self.fetchItems(key, Track, **kwargs)

    def get(self, title=None, album=None, track=None):
        """ Alias of :func:`~plexapi.audio.Artist.track`. """
        return self.track(title, album, track)

    def download(self, savepath=None, keep_original_name=False, subfolders=False, **kwargs):
        """ Download all tracks from the artist. See :func:`~plexapi.base.Playable.download` for details.

            Parameters:
                savepath (str): Defaults to current working dir.
                keep_original_name (bool): True to keep the original filename otherwise
                    a friendlier filename is generated.
                subfolders (bool): True to separate tracks in to album folders.
                **kwargs: Additional options passed into :func:`~plexapi.base.PlexObject.getStreamURL`.
        """
        filepaths = []
        for track in self.tracks():
            _savepath = os.path.join(savepath, track.parentTitle) if subfolders else savepath
            filepaths += track.download(_savepath, keep_original_name, **kwargs)
        return filepaths

    def station(self):
        """ Returns a :class:`~plexapi.playlist.Playlist` artist radio station or `None`. """
        key = f'{self.key}?includeStations=1'
        return next(iter(self.fetchItems(key, cls=Playlist, rtag="Stations")), None)


@utils.registerPlexObject
class Album(
    Audio,
    UnmatchMatchMixin, RatingMixin,
    ArtMixin, PosterMixin, ThemeUrlMixin,
    OriginallyAvailableMixin, SortTitleMixin, StudioMixin, SummaryMixin, TitleMixin,
    CollectionMixin, GenreMixin, LabelMixin, MoodMixin, StyleMixin
):
    """ Represents a single Album.

        Attributes:
            TAG (str): 'Directory'
            TYPE (str): 'album'
            collections (List<:class:`~plexapi.media.Collection`>): List of collection objects.
            formats (List<:class:`~plexapi.media.Format`>): List of format objects.
            genres (List<:class:`~plexapi.media.Genre`>): List of genre objects.
            guids (List<:class:`~plexapi.media.Guid`>): List of guid objects.
            key (str): API URL (/library/metadata/<ratingkey>).
            labels (List<:class:`~plexapi.media.Label`>): List of label objects.
            leafCount (int): Number of items in the album view.
            loudnessAnalysisVersion (int): The Plex loudness analysis version level.
            originallyAvailableAt (datetime): Datetime the album was released.
            parentGuid (str): Plex GUID for the album artist (plex://artist/5d07bcb0403c64029053ac4c).
            parentKey (str): API URL of the album artist (/library/metadata/<parentRatingKey>).
            parentRatingKey (int): Unique key identifying the album artist.
            parentTheme (str): URL to artist theme resource (/library/metadata/<parentRatingkey>/theme/<themeid>).
            parentThumb (str): URL to album artist thumbnail image (/library/metadata/<parentRatingKey>/thumb/<thumbid>).
            parentTitle (str): Name of the album artist.
            rating (float): Album rating (7.9; 9.8; 8.1).
            studio (str): Studio that released the album.
            styles (List<:class:`~plexapi.media.Style`>): List of style objects.
            subformats (List<:class:`~plexapi.media.Subformat`>): List of subformat objects.
            viewedLeafCount (int): Number of items marked as played in the album view.
            year (int): Year the album was released.
    """
    TAG = 'Directory'
    TYPE = 'album'

    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        Audio._loadData(self, data)
        self.collections = self.findItems(data, media.Collection)
        self.formats = self.findItems(data, media.Format)
        self.genres = self.findItems(data, media.Genre)
        self.guids = self.findItems(data, media.Guid)
        self.key = self.key.replace('/children', '')  # FIX_BUG_50
        self.labels = self.findItems(data, media.Label)
        self.leafCount = utils.cast(int, data.attrib.get('leafCount'))
        self.loudnessAnalysisVersion = utils.cast(int, data.attrib.get('loudnessAnalysisVersion'))
        self.originallyAvailableAt = utils.toDatetime(data.attrib.get('originallyAvailableAt'), '%Y-%m-%d')
        self.parentGuid = data.attrib.get('parentGuid')
        self.parentKey = data.attrib.get('parentKey')
        self.parentRatingKey = utils.cast(int, data.attrib.get('parentRatingKey'))
        self.parentTheme = data.attrib.get('parentTheme')
        self.parentThumb = data.attrib.get('parentThumb')
        self.parentTitle = data.attrib.get('parentTitle')
        self.rating = utils.cast(float, data.attrib.get('rating'))
        self.studio = data.attrib.get('studio')
        self.styles = self.findItems(data, media.Style)
        self.subformats = self.findItems(data, media.Subformat)
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
        key = f'{self.key}/children'
        if title is not None and not isinstance(title, int):
            return self.fetchItem(key, Track, title__iexact=title)
        elif track is not None or isinstance(title, int):
            if isinstance(title, int):
                index = title
            else:
                index = track
            return self.fetchItem(key, Track, parentTitle__iexact=self.title, index=index)
        raise BadRequest('Missing argument: title or track is required')

    def tracks(self, **kwargs):
        """ Returns a list of :class:`~plexapi.audio.Track` objects in the album. """
        key = f'{self.key}/children'
        return self.fetchItems(key, Track, **kwargs)

    def get(self, title=None, track=None):
        """ Alias of :func:`~plexapi.audio.Album.track`. """
        return self.track(title, track)

    def artist(self):
        """ Return the album's :class:`~plexapi.audio.Artist`. """
        return self.fetchItem(self.parentKey)

    def download(self, savepath=None, keep_original_name=False, **kwargs):
        """ Download all tracks from the album. See :func:`~plexapi.base.Playable.download` for details.

            Parameters:
                savepath (str): Defaults to current working dir.
                keep_original_name (bool): True to keep the original filename otherwise
                    a friendlier filename is generated.
                **kwargs: Additional options passed into :func:`~plexapi.base.PlexObject.getStreamURL`.
        """
        filepaths = []
        for track in self.tracks():
            filepaths += track.download(savepath, keep_original_name, **kwargs)
        return filepaths

    def _defaultSyncTitle(self):
        """ Returns str, default title for a new syncItem. """
        return f'{self.parentTitle} - {self.title}'


@utils.registerPlexObject
class Track(
    Audio, Playable,
    ExtrasMixin, RatingMixin,
    ArtUrlMixin, PosterUrlMixin, ThemeUrlMixin,
    TitleMixin, TrackArtistMixin, TrackNumberMixin, TrackDiscNumberMixin,
    CollectionMixin, LabelMixin, MoodMixin
):
    """ Represents a single Track.

        Attributes:
            TAG (str): 'Directory'
            TYPE (str): 'track'
            chapterSource (str): Unknown
            collections (List<:class:`~plexapi.media.Collection`>): List of collection objects.
            duration (int): Length of the track in milliseconds.
            grandparentArt (str): URL to album artist artwork (/library/metadata/<grandparentRatingKey>/art/<artid>).
            grandparentGuid (str): Plex GUID for the album artist (plex://artist/5d07bcb0403c64029053ac4c).
            grandparentKey (str): API URL of the album artist (/library/metadata/<grandparentRatingKey>).
            grandparentRatingKey (int): Unique key identifying the album artist.
            grandparentTheme (str): URL to artist theme resource  (/library/metadata/<grandparentRatingkey>/theme/<themeid>).
                (/library/metadata/<grandparentRatingkey>/theme/<themeid>).
            grandparentThumb (str): URL to album artist thumbnail image
                (/library/metadata/<grandparentRatingKey>/thumb/<thumbid>).
            grandparentTitle (str): Name of the album artist for the track.
            guids (List<:class:`~plexapi.media.Guid`>): List of guid objects.
            labels (List<:class:`~plexapi.media.Label`>): List of label objects.
            media (List<:class:`~plexapi.media.Media`>): List of media objects.
            originalTitle (str): The artist for the track.
            parentGuid (str): Plex GUID for the album (plex://album/5d07cd8e403c640290f180f9).
            parentIndex (int): Disc number of the track.
            parentKey (str): API URL of the album (/library/metadata/<parentRatingKey>).
            parentRatingKey (int): Unique key identifying the album.
            parentThumb (str): URL to album thumbnail image (/library/metadata/<parentRatingKey>/thumb/<thumbid>).
            parentTitle (str): Name of the album for the track.
            primaryExtraKey (str) API URL for the primary extra for the track.
            ratingCount (int): Number of listeners who have scrobbled this track, as reported by Last.fm.
            skipCount (int): Number of times the track has been skipped.
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
        self.collections = self.findItems(data, media.Collection)
        self.duration = utils.cast(int, data.attrib.get('duration'))
        self.grandparentArt = data.attrib.get('grandparentArt')
        self.grandparentGuid = data.attrib.get('grandparentGuid')
        self.grandparentKey = data.attrib.get('grandparentKey')
        self.grandparentRatingKey = utils.cast(int, data.attrib.get('grandparentRatingKey'))
        self.grandparentTheme = data.attrib.get('grandparentTheme')
        self.grandparentThumb = data.attrib.get('grandparentThumb')
        self.grandparentTitle = data.attrib.get('grandparentTitle')
        self.guids = self.findItems(data, media.Guid)
        self.labels = self.findItems(data, media.Label)
        self.media = self.findItems(data, media.Media)
        self.originalTitle = data.attrib.get('originalTitle')
        self.parentGuid = data.attrib.get('parentGuid')
        self.parentIndex = utils.cast(int, data.attrib.get('parentIndex'))
        self.parentKey = data.attrib.get('parentKey')
        self.parentRatingKey = utils.cast(int, data.attrib.get('parentRatingKey'))
        self.parentThumb = data.attrib.get('parentThumb')
        self.parentTitle = data.attrib.get('parentTitle')
        self.primaryExtraKey = data.attrib.get('primaryExtraKey')
        self.ratingCount = utils.cast(int, data.attrib.get('ratingCount'))
        self.skipCount = utils.cast(int, data.attrib.get('skipCount'))
        self.viewOffset = utils.cast(int, data.attrib.get('viewOffset', 0))
        self.year = utils.cast(int, data.attrib.get('year'))

    def _prettyfilename(self):
        """ Returns a filename for use in download. """
        return f'{self.grandparentTitle} - {self.parentTitle} - {str(self.trackNumber).zfill(2)} - {self.title}'

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

            Returns:
                List<str> of file paths where the track is found on disk.
        """
        return [part.file for part in self.iterParts() if part]

    @property
    def trackNumber(self):
        """ Returns the track number. """
        return self.index

    def _defaultSyncTitle(self):
        """ Returns str, default title for a new syncItem. """
        return f'{self.grandparentTitle} - {self.parentTitle} - {self.title}'

    def _getWebURL(self, base=None):
        """ Get the Plex Web URL with the correct parameters. """
        return self._server._buildWebURL(base=base, endpoint='details', key=self.parentKey)


@utils.registerPlexObject
class TrackSession(PlexSession, Track):
    """ Represents a single Track session
        loaded from :func:`~plexapi.server.PlexServer.sessions`.
    """
    _SESSIONTYPE = True

    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        Track._loadData(self, data)
        PlexSession._loadData(self, data)
