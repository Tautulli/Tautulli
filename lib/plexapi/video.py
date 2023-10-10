# -*- coding: utf-8 -*-
import os
from functools import cached_property
from pathlib import Path
from urllib.parse import quote_plus

from plexapi import media, utils
from plexapi.base import Playable, PlexPartialObject, PlexHistory, PlexSession
from plexapi.exceptions import BadRequest
from plexapi.mixins import (
    AdvancedSettingsMixin, SplitMergeMixin, UnmatchMatchMixin, ExtrasMixin, HubsMixin, PlayedUnplayedMixin, RatingMixin,
    ArtUrlMixin, ArtMixin, PosterUrlMixin, PosterMixin, ThemeUrlMixin, ThemeMixin,
    MovieEditMixins, ShowEditMixins, SeasonEditMixins, EpisodeEditMixins,
    WatchlistMixin
)


class Video(PlexPartialObject, PlayedUnplayedMixin):
    """ Base class for all video objects including :class:`~plexapi.video.Movie`,
        :class:`~plexapi.video.Show`, :class:`~plexapi.video.Season`,
        :class:`~plexapi.video.Episode`, and :class:`~plexapi.video.Clip`.

        Attributes:
            addedAt (datetime): Datetime the item was added to the library.
            art (str): URL to artwork image (/library/metadata/<ratingKey>/art/<artid>).
            artBlurHash (str): BlurHash string for artwork image.
            fields (List<:class:`~plexapi.media.Field`>): List of field objects.
            guid (str): Plex GUID for the movie, show, season, episode, or clip (plex://movie/5d776b59ad5437001f79c6f8).
            key (str): API URL (/library/metadata/<ratingkey>).
            lastRatedAt (datetime): Datetime the item was last rated.
            lastViewedAt (datetime): Datetime the item was last played.
            librarySectionID (int): :class:`~plexapi.library.LibrarySection` ID.
            librarySectionKey (str): :class:`~plexapi.library.LibrarySection` key.
            librarySectionTitle (str): :class:`~plexapi.library.LibrarySection` title.
            listType (str): Hardcoded as 'video' (useful for search filters).
            ratingKey (int): Unique key identifying the item.
            summary (str): Summary of the movie, show, season, episode, or clip.
            thumb (str): URL to thumbnail image (/library/metadata/<ratingKey>/thumb/<thumbid>).
            thumbBlurHash (str): BlurHash string for thumbnail image.
            title (str): Name of the movie, show, season, episode, or clip.
            titleSort (str): Title to use when sorting (defaults to title).
            type (str): 'movie', 'show', 'season', 'episode', or 'clip'.
            updatedAt (datetime): Datetime the item was updated.
            userRating (float): Rating of the item (0.0 - 10.0) equaling (0 stars - 5 stars).
            viewCount (int): Count of times the item was played.
    """

    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        self._data = data
        self.addedAt = utils.toDatetime(data.attrib.get('addedAt'))
        self.art = data.attrib.get('art')
        self.artBlurHash = data.attrib.get('artBlurHash')
        self.fields = self.findItems(data, media.Field)
        self.guid = data.attrib.get('guid')
        self.key = data.attrib.get('key', '')
        self.lastRatedAt = utils.toDatetime(data.attrib.get('lastRatedAt'))
        self.lastViewedAt = utils.toDatetime(data.attrib.get('lastViewedAt'))
        self.librarySectionID = utils.cast(int, data.attrib.get('librarySectionID'))
        self.librarySectionKey = data.attrib.get('librarySectionKey')
        self.librarySectionTitle = data.attrib.get('librarySectionTitle')
        self.listType = 'video'
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
        """ Returns the full url for something. Typically used for getting a specific image. """
        return self._server.url(part, includeToken=True) if part else None

    def augmentation(self):
        """ Returns a list of :class:`~plexapi.library.Hub` objects.
            Augmentation returns hub items relating to online media sources
            such as Tidal Music "Track from {item}" or "Soundtrack of {item}".
            Plex Pass and linked Tidal account are required.
        """
        account = self._server.myPlexAccount()
        tidalOptOut = next(
            (service.value for service in account.onlineMediaSources()
                if service.key == 'tv.plex.provider.music'),
            None
        )
        if account.subscriptionStatus != 'Active' or tidalOptOut == 'opt_out':
            raise BadRequest('Requires Plex Pass and Tidal Music enabled.')
        data = self._server.query(self.key + '?asyncAugmentMetadata=1')
        augmentationKey = data.attrib.get('augmentationKey')
        return self.fetchItems(augmentationKey)

    def _defaultSyncTitle(self):
        """ Returns str, default title for a new syncItem. """
        return self.title

    def videoStreams(self):
        """ Returns a list of :class:`~plexapi.media.videoStream` objects for all MediaParts. """
        streams = []

        if self.isPartialObject():
            self.reload()

        parts = self.iterParts()
        for part in parts:
            streams += part.videoStreams()
        return streams

    def audioStreams(self):
        """ Returns a list of :class:`~plexapi.media.AudioStream` objects for all MediaParts. """
        streams = []

        if self.isPartialObject():
            self.reload()

        parts = self.iterParts()
        for part in parts:
            streams += part.audioStreams()
        return streams

    def subtitleStreams(self):
        """ Returns a list of :class:`~plexapi.media.SubtitleStream` objects for all MediaParts. """
        streams = []

        if self.isPartialObject():
            self.reload()

        parts = self.iterParts()
        for part in parts:
            streams += part.subtitleStreams()
        return streams

    def uploadSubtitles(self, filepath):
        """ Upload Subtitle file for video. """
        url = f'{self.key}/subtitles'
        filename = os.path.basename(filepath)
        subFormat = os.path.splitext(filepath)[1][1:]
        with open(filepath, 'rb') as subfile:
            params = {'title': filename,
                      'format': subFormat
                      }
            headers = {'Accept': 'text/plain, */*'}
            self._server.query(url, self._server._session.post, data=subfile, params=params, headers=headers)
        return self

    def removeSubtitles(self, streamID=None, streamTitle=None):
        """ Remove Subtitle from movie's subtitles listing.

            Note: If subtitle file is located inside video directory it will bbe deleted.
            Files outside of video directory are not effected.
        """
        for stream in self.subtitleStreams():
            if streamID == stream.id or streamTitle == stream.title:
                self._server.query(stream.key, self._server._session.delete)
        return self

    def optimize(self, title='', target='', deviceProfile='', videoQuality=None,
                 locationID=-1, limit=None, unwatched=False):
        """ Create an optimized version of the video.

            Parameters:
                title (str, optional): Title of the optimized video.
                target (str, optional): Target quality profile:
                    "Optimized for Mobile" ("mobile"), "Optimized for TV" ("tv"), "Original Quality" ("original"),
                    or custom quality profile name (default  "Custom: {deviceProfile}").
                deviceProfile (str, optional): Custom quality device profile:
                    "Android", "iOS", "Universal Mobile", "Universal TV", "Windows Phone", "Windows", "Xbox One".
                    Required if ``target`` is custom.
                videoQuality (int, optional): Index of the quality profile, one of ``VIDEO_QUALITY_*``
                    values defined in the :mod:`~plexapi.sync` module. Only used if ``target`` is custom.
                locationID (int or :class:`~plexapi.library.Location`, optional): Default -1 for
                    "In folder with original items", otherwise a :class:`~plexapi.library.Location` object or ID.
                    See examples below.
                limit (int, optional): Maximum count of items to optimize, unlimited if ``None``.
                unwatched (bool, optional): ``True`` to only optimized unwatched videos.

            Raises:
                :exc:`~plexapi.exceptions.BadRequest`: Unknown quality profile target
                    or missing deviceProfile and videoQuality.
                :exc:`~plexapi.exceptions.BadRequest`: Unknown location ID.

            Example:

                .. code-block:: python

                    # Optimize for mobile using defaults
                    video.optimize(target="mobile")

                    # Optimize for Android at 10 Mbps 1080p
                    from plexapi.sync import VIDEO_QUALITY_10_MBPS_1080p
                    video.optimize(deviceProfile="Android", videoQuality=sync.VIDEO_QUALITY_10_MBPS_1080p)

                    # Optimize for iOS at original quality in library location
                    from plexapi.sync import VIDEO_QUALITY_ORIGINAL
                    locations = plex.library.section("Movies")._locations()
                    video.optimize(deviceProfile="iOS", videoQuality=VIDEO_QUALITY_ORIGINAL, locationID=locations[0])

                    # Optimize for tv the next 5 unwatched episodes
                    show.optimize(target="tv", limit=5, unwatched=True)

        """
        from plexapi.library import Location
        from plexapi.sync import Policy, MediaSettings

        backgroundProcessing = self.fetchItem('/playlists?type=42')
        key = f'{backgroundProcessing.key}/items'

        tags = {t.tag.lower(): t.id for t in self._server.library.tags('mediaProcessingTarget')}
        # Additional keys for shorthand values
        tags['mobile'] = tags['optimized for mobile']
        tags['tv'] = tags['optimized for tv']
        tags['original'] = tags['original quality']

        targetTagID = tags.get(target.lower(), '')
        if not targetTagID and (not deviceProfile or videoQuality is None):
            raise BadRequest('Unknown quality profile target or missing deviceProfile and videoQuality.')
        if targetTagID:
            target = ''
        elif deviceProfile and not target:
            target = f'Custom: {deviceProfile}'

        section = self.section()
        libraryLocationIDs = [-1] + [location.id for location in section._locations()]
        if isinstance(locationID, Location):
            locationID = locationID.id
        if locationID not in libraryLocationIDs:
            raise BadRequest(f'Unknown location ID "{locationID}" not in {libraryLocationIDs}')

        if isinstance(self, (Show, Season)):
            uri = f'library:///directory/{quote_plus(f"{self.key}/children")}'
        else:
            uri = f'library://{section.uuid}/item/{quote_plus(self.key)}'

        policy = Policy.create(limit, unwatched)

        params = {
            'Item[type]': 42,
            'Item[title]': title or self._defaultSyncTitle(),
            'Item[target]': target,
            'Item[targetTagID]': targetTagID,
            'Item[locationID]': locationID,
            'Item[Location][uri]': uri,
            'Item[Policy][scope]': policy.scope,
            'Item[Policy][value]': str(policy.value),
            'Item[Policy][unwatched]': str(int(policy.unwatched)),
        }

        if deviceProfile:
            params['Item[Device][profile]'] = deviceProfile

        if videoQuality:
            mediaSettings = MediaSettings.createVideo(videoQuality)
            params['Item[MediaSettings][videoQuality]'] = mediaSettings.videoQuality
            params['Item[MediaSettings][videoResolution]'] = mediaSettings.videoResolution
            params['Item[MediaSettings][maxVideoBitrate]'] = mediaSettings.maxVideoBitrate
            params['Item[MediaSettings][audioBoost]'] = ''
            params['Item[MediaSettings][subtitleSize]'] = ''
            params['Item[MediaSettings][musicBitrate]'] = ''
            params['Item[MediaSettings][photoQuality]'] = ''
            params['Item[MediaSettings][photoResolution]'] = ''

        url = key + utils.joinArgs(params)
        self._server.query(url, method=self._server._session.put)
        return self

    def sync(self, videoQuality, client=None, clientId=None, limit=None, unwatched=False, title=None):
        """ Add current video (movie, tv-show, season or episode) as sync item for specified device.
            See :func:`~plexapi.myplex.MyPlexAccount.sync` for possible exceptions.

            Parameters:
                videoQuality (int): idx of quality of the video, one of VIDEO_QUALITY_* values defined in
                                    :mod:`~plexapi.sync` module.
                client (:class:`~plexapi.myplex.MyPlexDevice`): sync destination, see
                                                               :func:`~plexapi.myplex.MyPlexAccount.sync`.
                clientId (str): sync destination, see :func:`~plexapi.myplex.MyPlexAccount.sync`.
                limit (int): maximum count of items to sync, unlimited if `None`.
                unwatched (bool): if `True` watched videos wouldn't be synced.
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
        sync_item.policy = Policy.create(limit, unwatched)
        sync_item.mediaSettings = MediaSettings.createVideo(videoQuality)

        return myplex.sync(sync_item, client=client, clientId=clientId)


@utils.registerPlexObject
class Movie(
    Video, Playable,
    AdvancedSettingsMixin, SplitMergeMixin, UnmatchMatchMixin, ExtrasMixin, HubsMixin, RatingMixin,
    ArtMixin, PosterMixin, ThemeMixin,
    MovieEditMixins,
    WatchlistMixin
):
    """ Represents a single Movie.

        Attributes:
            TAG (str): 'Video'
            TYPE (str): 'movie'
            audienceRating (float): Audience rating (usually from Rotten Tomatoes).
            audienceRatingImage (str): Key to audience rating image (rottentomatoes://image.rating.spilled).
            chapters (List<:class:`~plexapi.media.Chapter`>): List of Chapter objects.
            chapterSource (str): Chapter source (agent; media; mixed).
            collections (List<:class:`~plexapi.media.Collection`>): List of collection objects.
            contentRating (str) Content rating (PG-13; NR; TV-G).
            countries (List<:class:`~plexapi.media.Country`>): List of countries objects.
            directors (List<:class:`~plexapi.media.Director`>): List of director objects.
            duration (int): Duration of the movie in milliseconds.
            editionTitle (str): The edition title of the movie (e.g. Director's Cut, Extended Edition, etc.).
            enableCreditsMarkerGeneration (int): Setting that indicates if credits markers detection is enabled.
                (-1 = Library default, 0 = Disabled)
            genres (List<:class:`~plexapi.media.Genre`>): List of genre objects.
            guids (List<:class:`~plexapi.media.Guid`>): List of guid objects.
            labels (List<:class:`~plexapi.media.Label`>): List of label objects.
            languageOverride (str): Setting that indicates if a language is used to override metadata
                (eg. en-CA, None = Library default).
            markers (List<:class:`~plexapi.media.Marker`>): List of marker objects.
            media (List<:class:`~plexapi.media.Media`>): List of media objects.
            originallyAvailableAt (datetime): Datetime the movie was released.
            originalTitle (str): Original title, often the foreign title (転々; 엽기적인 그녀).
            primaryExtraKey (str) Primary extra key (/library/metadata/66351).
            producers (List<:class:`~plexapi.media.Producer`>): List of producers objects.
            rating (float): Movie critic rating (7.9; 9.8; 8.1).
            ratingImage (str): Key to critic rating image (rottentomatoes://image.rating.rotten).
            ratings (List<:class:`~plexapi.media.Rating`>): List of rating objects.
            roles (List<:class:`~plexapi.media.Role`>): List of role objects.
            similar (List<:class:`~plexapi.media.Similar`>): List of Similar objects.
            studio (str): Studio that created movie (Di Bonaventura Pictures; 21 Laps Entertainment).
            tagline (str): Movie tag line (Back 2 Work; Who says men can't change?).
            theme (str): URL to theme resource (/library/metadata/<ratingkey>/theme/<themeid>).
            useOriginalTitle (int): Setting that indicates if the original title is used for the movie
                (-1 = Library default, 0 = No, 1 = Yes).
            viewOffset (int): View offset in milliseconds.
            writers (List<:class:`~plexapi.media.Writer`>): List of writers objects.
            year (int): Year movie was released.
    """
    TAG = 'Video'
    TYPE = 'movie'
    METADATA_TYPE = 'movie'

    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        Video._loadData(self, data)
        Playable._loadData(self, data)
        self.audienceRating = utils.cast(float, data.attrib.get('audienceRating'))
        self.audienceRatingImage = data.attrib.get('audienceRatingImage')
        self.chapters = self.findItems(data, media.Chapter)
        self.chapterSource = data.attrib.get('chapterSource')
        self.collections = self.findItems(data, media.Collection)
        self.contentRating = data.attrib.get('contentRating')
        self.countries = self.findItems(data, media.Country)
        self.directors = self.findItems(data, media.Director)
        self.duration = utils.cast(int, data.attrib.get('duration'))
        self.editionTitle = data.attrib.get('editionTitle')
        self.enableCreditsMarkerGeneration = utils.cast(int, data.attrib.get('enableCreditsMarkerGeneration', '-1'))
        self.genres = self.findItems(data, media.Genre)
        self.guids = self.findItems(data, media.Guid)
        self.labels = self.findItems(data, media.Label)
        self.languageOverride = data.attrib.get('languageOverride')
        self.markers = self.findItems(data, media.Marker)
        self.media = self.findItems(data, media.Media)
        self.originallyAvailableAt = utils.toDatetime(data.attrib.get('originallyAvailableAt'), '%Y-%m-%d')
        self.originalTitle = data.attrib.get('originalTitle')
        self.primaryExtraKey = data.attrib.get('primaryExtraKey')
        self.producers = self.findItems(data, media.Producer)
        self.rating = utils.cast(float, data.attrib.get('rating'))
        self.ratingImage = data.attrib.get('ratingImage')
        self.ratings = self.findItems(data, media.Rating)
        self.roles = self.findItems(data, media.Role)
        self.similar = self.findItems(data, media.Similar)
        self.studio = data.attrib.get('studio')
        self.tagline = data.attrib.get('tagline')
        self.theme = data.attrib.get('theme')
        self.useOriginalTitle = utils.cast(int, data.attrib.get('useOriginalTitle', '-1'))
        self.viewOffset = utils.cast(int, data.attrib.get('viewOffset', 0))
        self.writers = self.findItems(data, media.Writer)
        self.year = utils.cast(int, data.attrib.get('year'))

    @property
    def actors(self):
        """ Alias to self.roles. """
        return self.roles

    @property
    def locations(self):
        """ This does not exist in plex xml response but is added to have a common
            interface to get the locations of the movie.

            Returns:
                List<str> of file paths where the movie is found on disk.
        """
        return [part.file for part in self.iterParts() if part]

    @property
    def hasCreditsMarker(self):
        """ Returns True if the movie has a credits marker. """
        return any(marker.type == 'credits' for marker in self.markers)

    @property
    def hasPreviewThumbnails(self):
        """ Returns True if any of the media parts has generated preview (BIF) thumbnails. """
        return any(part.hasPreviewThumbnails for media in self.media for part in media.parts)

    def _prettyfilename(self):
        """ Returns a filename for use in download. """
        return f'{self.title} ({self.year})'

    def reviews(self):
        """ Returns a list of :class:`~plexapi.media.Review` objects. """
        data = self._server.query(self._details_key)
        return self.findItems(data, media.Review, rtag='Video')

    def editions(self):
        """ Returns a list of :class:`~plexapi.video.Movie` objects
            for other editions of the same movie.
        """
        filters = {
            'guid': self.guid,
            'id!': self.ratingKey
        }
        return self.section().search(filters=filters)

    def removeFromContinueWatching(self):
        """ Remove the movie from continue watching. """
        key = '/actions/removeFromContinueWatching'
        params = {'ratingKey': self.ratingKey}
        self._server.query(key, params=params, method=self._server._session.put)
        return self

    @property
    def metadataDirectory(self):
        """ Returns the Plex Media Server data directory where the metadata is stored. """
        guid_hash = utils.sha1hash(self.guid)
        return str(Path('Metadata') / 'Movies' / guid_hash[0] / f'{guid_hash[1:]}.bundle')


@utils.registerPlexObject
class Show(
    Video,
    AdvancedSettingsMixin, SplitMergeMixin, UnmatchMatchMixin, ExtrasMixin, HubsMixin, RatingMixin,
    ArtMixin, PosterMixin, ThemeMixin,
    ShowEditMixins,
    WatchlistMixin
):
    """ Represents a single Show (including all seasons and episodes).

        Attributes:
            TAG (str): 'Directory'
            TYPE (str): 'show'
            audienceRating (float): Audience rating (TMDB or TVDB).
            audienceRatingImage (str): Key to audience rating image (tmdb://image.rating).
            audioLanguage (str): Setting that indicates the preferred audio language.
            autoDeletionItemPolicyUnwatchedLibrary (int): Setting that indicates the number of unplayed
                episodes to keep for the show (0 = All episodes, 5 = 5 latest episodes, 3 = 3 latest episodes,
                1 = 1 latest episode, -3 = Episodes added in the past 3 days, -7 = Episodes added in the
                past 7 days, -30 = Episodes added in the past 30 days).
            autoDeletionItemPolicyWatchedLibrary (int): Setting that indicates if episodes are deleted
                after being watched for the show (0 = Never, 1 = After a day, 7 = After a week,
                100 = On next refresh).
            childCount (int): Number of seasons (including Specials) in the show.
            collections (List<:class:`~plexapi.media.Collection`>): List of collection objects.
            contentRating (str) Content rating (PG-13; NR; TV-G).
            duration (int): Typical duration of the show episodes in milliseconds.
            enableCreditsMarkerGeneration (int): Setting that indicates if credits markers detection is enabled.
                (-1 = Library default, 0 = Disabled).
            episodeSort (int): Setting that indicates how episodes are sorted for the show
                (-1 = Library default, 0 = Oldest first, 1 = Newest first).
            flattenSeasons (int): Setting that indicates if seasons are set to hidden for the show
                (-1 = Library default, 0 = Hide, 1 = Show).
            genres (List<:class:`~plexapi.media.Genre`>): List of genre objects.
            guids (List<:class:`~plexapi.media.Guid`>): List of guid objects.
            index (int): Plex index number for the show.
            key (str): API URL (/library/metadata/<ratingkey>).
            labels (List<:class:`~plexapi.media.Label`>): List of label objects.
            languageOverride (str): Setting that indicates if a language is used to override metadata
                (eg. en-CA, None = Library default).
            leafCount (int): Number of items in the show view.
            locations (List<str>): List of folder paths where the show is found on disk.
            network (str): The network that distributed the show.
            originallyAvailableAt (datetime): Datetime the show was released.
            originalTitle (str): The original title of the show.
            rating (float): Show rating (7.9; 9.8; 8.1).
            ratings (List<:class:`~plexapi.media.Rating`>): List of rating objects.
            roles (List<:class:`~plexapi.media.Role`>): List of role objects.
            seasonCount (int): Number of seasons (excluding Specials) in the show.
            showOrdering (str): Setting that indicates the episode ordering for the show
                (None = Library default, tmdbAiring = The Movie Database (Aired),
                aired = TheTVDB (Aired), dvd = TheTVDB (DVD), absolute = TheTVDB (Absolute)).
            similar (List<:class:`~plexapi.media.Similar`>): List of Similar objects.
            studio (str): Studio that created show (Di Bonaventura Pictures; 21 Laps Entertainment).
            subtitleLanguage (str): Setting that indicates the preferred subtitle language.
            subtitleMode (int): Setting that indicates the auto-select subtitle mode.
                (-1 = Account default, 0 = Manually selected, 1 = Shown with foreign audio, 2 = Always enabled).
            tagline (str): Show tag line.
            theme (str): URL to theme resource (/library/metadata/<ratingkey>/theme/<themeid>).
            useOriginalTitle (int): Setting that indicates if the original title is used for the show
                (-1 = Library default, 0 = No, 1 = Yes).
            viewedLeafCount (int): Number of items marked as played in the show view.
            year (int): Year the show was released.
    """
    TAG = 'Directory'
    TYPE = 'show'
    METADATA_TYPE = 'episode'

    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        Video._loadData(self, data)
        self.audienceRating = utils.cast(float, data.attrib.get('audienceRating'))
        self.audienceRatingImage = data.attrib.get('audienceRatingImage')
        self.audioLanguage = data.attrib.get('audioLanguage', '')
        self.autoDeletionItemPolicyUnwatchedLibrary = utils.cast(
            int, data.attrib.get('autoDeletionItemPolicyUnwatchedLibrary', '0'))
        self.autoDeletionItemPolicyWatchedLibrary = utils.cast(
            int, data.attrib.get('autoDeletionItemPolicyWatchedLibrary', '0'))
        self.childCount = utils.cast(int, data.attrib.get('childCount'))
        self.collections = self.findItems(data, media.Collection)
        self.contentRating = data.attrib.get('contentRating')
        self.duration = utils.cast(int, data.attrib.get('duration'))
        self.enableCreditsMarkerGeneration = utils.cast(int, data.attrib.get('enableCreditsMarkerGeneration', '-1'))
        self.episodeSort = utils.cast(int, data.attrib.get('episodeSort', '-1'))
        self.flattenSeasons = utils.cast(int, data.attrib.get('flattenSeasons', '-1'))
        self.genres = self.findItems(data, media.Genre)
        self.guids = self.findItems(data, media.Guid)
        self.index = utils.cast(int, data.attrib.get('index'))
        self.key = self.key.replace('/children', '')  # FIX_BUG_50
        self.labels = self.findItems(data, media.Label)
        self.languageOverride = data.attrib.get('languageOverride')
        self.leafCount = utils.cast(int, data.attrib.get('leafCount'))
        self.locations = self.listAttrs(data, 'path', etag='Location')
        self.network = data.attrib.get('network')
        self.originallyAvailableAt = utils.toDatetime(data.attrib.get('originallyAvailableAt'), '%Y-%m-%d')
        self.originalTitle = data.attrib.get('originalTitle')
        self.rating = utils.cast(float, data.attrib.get('rating'))
        self.ratings = self.findItems(data, media.Rating)
        self.roles = self.findItems(data, media.Role)
        self.seasonCount = utils.cast(int, data.attrib.get('seasonCount', self.childCount))
        self.showOrdering = data.attrib.get('showOrdering')
        self.similar = self.findItems(data, media.Similar)
        self.studio = data.attrib.get('studio')
        self.subtitleLanguage = data.attrib.get('audioLanguage', '')
        self.subtitleMode = utils.cast(int, data.attrib.get('subtitleMode', '-1'))
        self.tagline = data.attrib.get('tagline')
        self.theme = data.attrib.get('theme')
        self.useOriginalTitle = utils.cast(int, data.attrib.get('useOriginalTitle', '-1'))
        self.viewedLeafCount = utils.cast(int, data.attrib.get('viewedLeafCount'))
        self.year = utils.cast(int, data.attrib.get('year'))

    def __iter__(self):
        for season in self.seasons():
            yield season

    @property
    def actors(self):
        """ Alias to self.roles. """
        return self.roles

    @property
    def isPlayed(self):
        """ Returns True if the show is fully played. """
        return bool(self.viewedLeafCount == self.leafCount)

    def onDeck(self):
        """ Returns show's On Deck :class:`~plexapi.video.Video` object or `None`.
            If show is unwatched, return will likely be the first episode.
        """
        data = self._server.query(self._details_key)
        return next(iter(self.findItems(data, rtag='OnDeck')), None)

    def season(self, title=None, season=None):
        """ Returns the season with the specified title or number.

            Parameters:
                title (str): Title of the season to return.
                season (int): Season number (default: None; required if title not specified).

            Raises:
                :exc:`~plexapi.exceptions.BadRequest`: If title or season parameter is missing.
        """
        key = f'{self.key}/children?excludeAllLeaves=1'
        if title is not None and not isinstance(title, int):
            return self.fetchItem(key, Season, title__iexact=title)
        elif season is not None or isinstance(title, int):
            if isinstance(title, int):
                index = title
            else:
                index = season
            return self.fetchItem(key, Season, index=index)
        raise BadRequest('Missing argument: title or season is required')

    def seasons(self, **kwargs):
        """ Returns a list of :class:`~plexapi.video.Season` objects in the show. """
        key = f'{self.key}/children?excludeAllLeaves=1'
        return self.fetchItems(key, Season, container_size=self.childCount, **kwargs)

    def episode(self, title=None, season=None, episode=None):
        """ Find a episode using a title or season and episode.

            Parameters:
                title (str): Title of the episode to return
                season (int): Season number (default: None; required if title not specified).
                episode (int): Episode number (default: None; required if title not specified).

            Raises:
                :exc:`~plexapi.exceptions.BadRequest`: If title or season and episode parameters are missing.
        """
        key = f'{self.key}/allLeaves'
        if title is not None:
            return self.fetchItem(key, Episode, title__iexact=title)
        elif season is not None and episode is not None:
            return self.fetchItem(key, Episode, parentIndex=season, index=episode)
        raise BadRequest('Missing argument: title or season and episode are required')

    def episodes(self, **kwargs):
        """ Returns a list of :class:`~plexapi.video.Episode` objects in the show. """
        key = f'{self.key}/allLeaves'
        return self.fetchItems(key, Episode, **kwargs)

    def get(self, title=None, season=None, episode=None):
        """ Alias to :func:`~plexapi.video.Show.episode`. """
        return self.episode(title, season, episode)

    def watched(self):
        """ Returns list of watched :class:`~plexapi.video.Episode` objects. """
        return self.episodes(viewCount__gt=0)

    def unwatched(self):
        """ Returns list of unwatched :class:`~plexapi.video.Episode` objects. """
        return self.episodes(viewCount=0)

    def download(self, savepath=None, keep_original_name=False, subfolders=False, **kwargs):
        """ Download all episodes from the show. See :func:`~plexapi.base.Playable.download` for details.

            Parameters:
                savepath (str): Defaults to current working dir.
                keep_original_name (bool): True to keep the original filename otherwise
                    a friendlier filename is generated.
                subfolders (bool): True to separate episodes in to season folders.
                **kwargs: Additional options passed into :func:`~plexapi.base.PlexObject.getStreamURL`.
        """
        filepaths = []
        for episode in self.episodes():
            _savepath = os.path.join(savepath, f'Season {str(episode.seasonNumber).zfill(2)}') if subfolders else savepath
            filepaths += episode.download(_savepath, keep_original_name, **kwargs)
        return filepaths

    @property
    def metadataDirectory(self):
        """ Returns the Plex Media Server data directory where the metadata is stored. """
        guid_hash = utils.sha1hash(self.guid)
        return str(Path('Metadata') / 'TV Shows' / guid_hash[0] / f'{guid_hash[1:]}.bundle')


@utils.registerPlexObject
class Season(
    Video,
    AdvancedSettingsMixin, ExtrasMixin, RatingMixin,
    ArtMixin, PosterMixin, ThemeUrlMixin,
    SeasonEditMixins
):
    """ Represents a single Season.

        Attributes:
            TAG (str): 'Directory'
            TYPE (str): 'season'
            audioLanguage (str): Setting that indicates the preferred audio language.
            collections (List<:class:`~plexapi.media.Collection`>): List of collection objects.
            guids (List<:class:`~plexapi.media.Guid`>): List of guid objects.
            index (int): Season number.
            key (str): API URL (/library/metadata/<ratingkey>).
            labels (List<:class:`~plexapi.media.Label`>): List of label objects.
            leafCount (int): Number of items in the season view.
            parentGuid (str): Plex GUID for the show (plex://show/5d9c086fe9d5a1001f4d9fe6).
            parentIndex (int): Plex index number for the show.
            parentKey (str): API URL of the show (/library/metadata/<parentRatingKey>).
            parentRatingKey (int): Unique key identifying the show.
            parentStudio (str): Studio that created show.
            parentTheme (str): URL to show theme resource (/library/metadata/<parentRatingkey>/theme/<themeid>).
            parentThumb (str): URL to show thumbnail image (/library/metadata/<parentRatingKey>/thumb/<thumbid>).
            parentTitle (str): Name of the show for the season.
            ratings (List<:class:`~plexapi.media.Rating`>): List of rating objects.
            subtitleLanguage (str): Setting that indicates the preferred subtitle language.
            subtitleMode (int): Setting that indicates the auto-select subtitle mode.
                (-1 = Series default, 0 = Manually selected, 1 = Shown with foreign audio, 2 = Always enabled).
            viewedLeafCount (int): Number of items marked as played in the season view.
            year (int): Year the season was released.
    """
    TAG = 'Directory'
    TYPE = 'season'
    METADATA_TYPE = 'episode'

    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        Video._loadData(self, data)
        self.audioLanguage = data.attrib.get('audioLanguage', '')
        self.collections = self.findItems(data, media.Collection)
        self.guids = self.findItems(data, media.Guid)
        self.index = utils.cast(int, data.attrib.get('index'))
        self.key = self.key.replace('/children', '')  # FIX_BUG_50
        self.labels = self.findItems(data, media.Label)
        self.leafCount = utils.cast(int, data.attrib.get('leafCount'))
        self.parentGuid = data.attrib.get('parentGuid')
        self.parentIndex = utils.cast(int, data.attrib.get('parentIndex'))
        self.parentKey = data.attrib.get('parentKey')
        self.parentRatingKey = utils.cast(int, data.attrib.get('parentRatingKey'))
        self.parentStudio = data.attrib.get('parentStudio')
        self.parentTheme = data.attrib.get('parentTheme')
        self.parentThumb = data.attrib.get('parentThumb')
        self.parentTitle = data.attrib.get('parentTitle')
        self.ratings = self.findItems(data, media.Rating)
        self.subtitleLanguage = data.attrib.get('audioLanguage', '')
        self.subtitleMode = utils.cast(int, data.attrib.get('subtitleMode', '-1'))
        self.viewedLeafCount = utils.cast(int, data.attrib.get('viewedLeafCount'))
        self.year = utils.cast(int, data.attrib.get('year'))

    def __iter__(self):
        for episode in self.episodes():
            yield episode

    def __repr__(self):
        return '<{}>'.format(
            ':'.join([p for p in [
                self.__class__.__name__,
                self.key.replace('/library/metadata/', '').replace('/children', ''),
                f"{self.parentTitle.replace(' ', '-')[:20]}-{self.seasonNumber}",
            ] if p])
        )

    @property
    def isPlayed(self):
        """ Returns True if the season is fully played. """
        return bool(self.viewedLeafCount == self.leafCount)

    @property
    def seasonNumber(self):
        """ Returns the season number. """
        return self.index

    def onDeck(self):
        """ Returns season's On Deck :class:`~plexapi.video.Video` object or `None`.
            Will only return a match if the show's On Deck episode is in this season.
        """
        data = self._server.query(self._details_key)
        return next(iter(self.findItems(data, rtag='OnDeck')), None)

    def episode(self, title=None, episode=None):
        """ Returns the episode with the given title or number.

            Parameters:
                title (str): Title of the episode to return.
                episode (int): Episode number (default: None; required if title not specified).

            Raises:
                :exc:`~plexapi.exceptions.BadRequest`: If title or episode parameter is missing.
        """
        key = f'{self.key}/children'
        if title is not None and not isinstance(title, int):
            return self.fetchItem(key, Episode, title__iexact=title)
        elif episode is not None or isinstance(title, int):
            if isinstance(title, int):
                index = title
            else:
                index = episode
            return self.fetchItem(key, Episode, parentIndex=self.index, index=index)
        raise BadRequest('Missing argument: title or episode is required')

    def episodes(self, **kwargs):
        """ Returns a list of :class:`~plexapi.video.Episode` objects in the season. """
        key = f'{self.key}/children'
        return self.fetchItems(key, Episode, **kwargs)

    def get(self, title=None, episode=None):
        """ Alias to :func:`~plexapi.video.Season.episode`. """
        return self.episode(title, episode)

    def show(self):
        """ Return the season's :class:`~plexapi.video.Show`. """
        return self.fetchItem(self.parentKey)

    def watched(self):
        """ Returns list of watched :class:`~plexapi.video.Episode` objects. """
        return self.episodes(viewCount__gt=0)

    def unwatched(self):
        """ Returns list of unwatched :class:`~plexapi.video.Episode` objects. """
        return self.episodes(viewCount=0)

    def download(self, savepath=None, keep_original_name=False, **kwargs):
        """ Download all episodes from the season. See :func:`~plexapi.base.Playable.download` for details.

            Parameters:
                savepath (str): Defaults to current working dir.
                keep_original_name (bool): True to keep the original filename otherwise
                    a friendlier filename is generated.
                **kwargs: Additional options passed into :func:`~plexapi.base.PlexObject.getStreamURL`.
        """
        filepaths = []
        for episode in self.episodes():
            filepaths += episode.download(savepath, keep_original_name, **kwargs)
        return filepaths

    def _defaultSyncTitle(self):
        """ Returns str, default title for a new syncItem. """
        return f'{self.parentTitle} - {self.title}'

    @property
    def metadataDirectory(self):
        """ Returns the Plex Media Server data directory where the metadata is stored. """
        guid_hash = utils.sha1hash(self.parentGuid)
        return str(Path('Metadata') / 'TV Shows' / guid_hash[0] / f'{guid_hash[1:]}.bundle')


@utils.registerPlexObject
class Episode(
    Video, Playable,
    ExtrasMixin, RatingMixin,
    ArtMixin, PosterMixin, ThemeUrlMixin,
    EpisodeEditMixins
):
    """ Represents a single Episode.

        Attributes:
            TAG (str): 'Video'
            TYPE (str): 'episode'
            audienceRating (float): Audience rating (TMDB or TVDB).
            audienceRatingImage (str): Key to audience rating image (tmdb://image.rating).
            chapters (List<:class:`~plexapi.media.Chapter`>): List of Chapter objects.
            chapterSource (str): Chapter source (agent; media; mixed).
            collections (List<:class:`~plexapi.media.Collection`>): List of collection objects.
            contentRating (str) Content rating (PG-13; NR; TV-G).
            directors (List<:class:`~plexapi.media.Director`>): List of director objects.
            duration (int): Duration of the episode in milliseconds.
            grandparentArt (str): URL to show artwork (/library/metadata/<grandparentRatingKey>/art/<artid>).
            grandparentGuid (str): Plex GUID for the show (plex://show/5d9c086fe9d5a1001f4d9fe6).
            grandparentKey (str): API URL of the show (/library/metadata/<grandparentRatingKey>).
            grandparentRatingKey (int): Unique key identifying the show.
            grandparentTheme (str): URL to show theme resource (/library/metadata/<grandparentRatingkey>/theme/<themeid>).
            grandparentThumb (str): URL to show thumbnail image (/library/metadata/<grandparentRatingKey>/thumb/<thumbid>).
            grandparentTitle (str): Name of the show for the episode.
            guids (List<:class:`~plexapi.media.Guid`>): List of guid objects.
            index (int): Episode number.
            labels (List<:class:`~plexapi.media.Label`>): List of label objects.
            markers (List<:class:`~plexapi.media.Marker`>): List of marker objects.
            media (List<:class:`~plexapi.media.Media`>): List of media objects.
            originallyAvailableAt (datetime): Datetime the episode was released.
            parentGuid (str): Plex GUID for the season (plex://season/5d9c09e42df347001e3c2a72).
            parentIndex (int): Season number of episode.
            parentKey (str): API URL of the season (/library/metadata/<parentRatingKey>).
            parentRatingKey (int): Unique key identifying the season.
            parentThumb (str): URL to season thumbnail image (/library/metadata/<parentRatingKey>/thumb/<thumbid>).
            parentTitle (str): Name of the season for the episode.
            parentYear (int): Year the season was released.
            producers (List<:class:`~plexapi.media.Producer`>): List of producers objects.
            rating (float): Episode rating (7.9; 9.8; 8.1).
            ratings (List<:class:`~plexapi.media.Rating`>): List of rating objects.
            roles (List<:class:`~plexapi.media.Role`>): List of role objects.
            skipParent (bool): True if the show's seasons are set to hidden.
            viewOffset (int): View offset in milliseconds.
            writers (List<:class:`~plexapi.media.Writer`>): List of writers objects.
            year (int): Year the episode was released.
    """
    TAG = 'Video'
    TYPE = 'episode'
    METADATA_TYPE = 'episode'

    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        Video._loadData(self, data)
        Playable._loadData(self, data)
        self.audienceRating = utils.cast(float, data.attrib.get('audienceRating'))
        self.audienceRatingImage = data.attrib.get('audienceRatingImage')
        self.chapters = self.findItems(data, media.Chapter)
        self.chapterSource = data.attrib.get('chapterSource')
        self.collections = self.findItems(data, media.Collection)
        self.contentRating = data.attrib.get('contentRating')
        self.directors = self.findItems(data, media.Director)
        self.duration = utils.cast(int, data.attrib.get('duration'))
        self.grandparentArt = data.attrib.get('grandparentArt')
        self.grandparentGuid = data.attrib.get('grandparentGuid')
        self.grandparentKey = data.attrib.get('grandparentKey')
        self.grandparentRatingKey = utils.cast(int, data.attrib.get('grandparentRatingKey'))
        self.grandparentTheme = data.attrib.get('grandparentTheme')
        self.grandparentThumb = data.attrib.get('grandparentThumb')
        self.grandparentTitle = data.attrib.get('grandparentTitle')
        self.guids = self.findItems(data, media.Guid)
        self.index = utils.cast(int, data.attrib.get('index'))
        self.labels = self.findItems(data, media.Label)
        self.markers = self.findItems(data, media.Marker)
        self.media = self.findItems(data, media.Media)
        self.originallyAvailableAt = utils.toDatetime(data.attrib.get('originallyAvailableAt'), '%Y-%m-%d')
        self.parentGuid = data.attrib.get('parentGuid')
        self.parentIndex = utils.cast(int, data.attrib.get('parentIndex'))
        self.parentTitle = data.attrib.get('parentTitle')
        self.parentYear = utils.cast(int, data.attrib.get('parentYear'))
        self.producers = self.findItems(data, media.Producer)
        self.rating = utils.cast(float, data.attrib.get('rating'))
        self.ratings = self.findItems(data, media.Rating)
        self.roles = self.findItems(data, media.Role)
        self.skipParent = utils.cast(bool, data.attrib.get('skipParent', '0'))
        self.viewOffset = utils.cast(int, data.attrib.get('viewOffset', 0))
        self.writers = self.findItems(data, media.Writer)
        self.year = utils.cast(int, data.attrib.get('year'))

        # If seasons are hidden, parentKey and parentRatingKey are missing from the XML response.
        # https://forums.plex.tv/t/parentratingkey-not-in-episode-xml-when-seasons-are-hidden/300553
        # Use cached properties below to return the correct values if they are missing to avoid auto-reloading.
        self._parentKey = data.attrib.get('parentKey')
        self._parentRatingKey = utils.cast(int, data.attrib.get('parentRatingKey'))
        self._parentThumb = data.attrib.get('parentThumb')

    @cached_property
    def parentKey(self):
        """ Returns the parentKey. Refer to the Episode attributes. """
        if self._parentKey:
            return self._parentKey
        if self.parentRatingKey:
            return f'/library/metadata/{self.parentRatingKey}'
        return None

    @cached_property
    def parentRatingKey(self):
        """ Returns the parentRatingKey. Refer to the Episode attributes. """
        if self._parentRatingKey is not None:
            return self._parentRatingKey
        # Parse the parentRatingKey from the parentThumb
        if self._parentThumb and self._parentThumb.startswith('/library/metadata/'):
            return utils.cast(int, self._parentThumb.split('/')[3])
        # Get the parentRatingKey from the season's ratingKey if available
        if self._season:
            return self._season.ratingKey
        return None

    @cached_property
    def parentThumb(self):
        """ Returns the parentThumb. Refer to the Episode attributes. """
        if self._parentThumb:
            return self._parentThumb
        if self._season:
            return self._season.thumb
        return None

    @cached_property
    def _season(self):
        """ Returns the :class:`~plexapi.video.Season` object by querying for the show's children. """
        if not self.grandparentKey:
            return None
        return self.fetchItem(
            f'{self.grandparentKey}/children?excludeAllLeaves=1&index={self.parentIndex}'
        )

    def __repr__(self):
        return '<{}>'.format(
            ':'.join([p for p in [
                self.__class__.__name__,
                self.key.replace('/library/metadata/', '').replace('/children', ''),
                f"{self.grandparentTitle.replace(' ', '-')[:20]}-{self.seasonEpisode}",
            ] if p])
        )

    def _prettyfilename(self):
        """ Returns a filename for use in download. """
        return f'{self.grandparentTitle} - {self.seasonEpisode} - {self.title}'

    @property
    def actors(self):
        """ Alias to self.roles. """
        return self.roles

    @property
    def locations(self):
        """ This does not exist in plex xml response but is added to have a common
            interface to get the locations of the episode.

            Returns:
                List<str> of file paths where the episode is found on disk.
        """
        return [part.file for part in self.iterParts() if part]

    @property
    def episodeNumber(self):
        """ Returns the episode number. """
        return self.index

    @cached_property
    def seasonNumber(self):
        """ Returns the episode's season number. """
        return self.parentIndex if isinstance(self.parentIndex, int) else self._season.seasonNumber

    @property
    def seasonEpisode(self):
        """ Returns the s00e00 string containing the season and episode numbers. """
        return f's{str(self.seasonNumber).zfill(2)}e{str(self.episodeNumber).zfill(2)}'

    @property
    def hasCommercialMarker(self):
        """ Returns True if the episode has a commercial marker. """
        return any(marker.type == 'commercial' for marker in self.markers)

    @property
    def hasIntroMarker(self):
        """ Returns True if the episode has an intro marker. """
        return any(marker.type == 'intro' for marker in self.markers)

    @property
    def hasCreditsMarker(self):
        """ Returns True if the episode has a credits marker. """
        return any(marker.type == 'credits' for marker in self.markers)

    @property
    def hasPreviewThumbnails(self):
        """ Returns True if any of the media parts has generated preview (BIF) thumbnails. """
        return any(part.hasPreviewThumbnails for media in self.media for part in media.parts)

    def season(self):
        """" Return the episode's :class:`~plexapi.video.Season`. """
        return self.fetchItem(self.parentKey)

    def show(self):
        """" Return the episode's :class:`~plexapi.video.Show`. """
        return self.fetchItem(self.grandparentKey)

    def _defaultSyncTitle(self):
        """ Returns str, default title for a new syncItem. """
        return f'{self.grandparentTitle} - {self.parentTitle} - ({self.seasonEpisode}) {self.title}'

    def removeFromContinueWatching(self):
        """ Remove the movie from continue watching. """
        key = '/actions/removeFromContinueWatching'
        params = {'ratingKey': self.ratingKey}
        self._server.query(key, params=params, method=self._server._session.put)
        return self

    @property
    def metadataDirectory(self):
        """ Returns the Plex Media Server data directory where the metadata is stored. """
        guid_hash = utils.sha1hash(self.grandparentGuid)
        return str(Path('Metadata') / 'TV Shows' / guid_hash[0] / f'{guid_hash[1:]}.bundle')


@utils.registerPlexObject
class Clip(
    Video, Playable,
    ArtUrlMixin, PosterUrlMixin
):
    """ Represents a single Clip.

        Attributes:
            TAG (str): 'Video'
            TYPE (str): 'clip'
            duration (int): Duration of the clip in milliseconds.
            extraType (int): Unknown.
            index (int): Plex index number for the clip.
            media (List<:class:`~plexapi.media.Media`>): List of media objects.
            originallyAvailableAt (datetime): Datetime the clip was released.
            skipDetails (int): Unknown.
            subtype (str): Type of clip (trailer, behindTheScenes, sceneOrSample, etc.).
            thumbAspectRatio (str): Aspect ratio of the thumbnail image.
            viewOffset (int): View offset in milliseconds.
            year (int): Year clip was released.
    """
    TAG = 'Video'
    TYPE = 'clip'
    METADATA_TYPE = 'clip'

    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        Video._loadData(self, data)
        Playable._loadData(self, data)
        self._data = data
        self.addedAt = utils.toDatetime(data.attrib.get('addedAt'))
        self.duration = utils.cast(int, data.attrib.get('duration'))
        self.extraType = utils.cast(int, data.attrib.get('extraType'))
        self.index = utils.cast(int, data.attrib.get('index'))
        self.media = self.findItems(data, media.Media)
        self.originallyAvailableAt = utils.toDatetime(
            data.attrib.get('originallyAvailableAt'), '%Y-%m-%d')
        self.skipDetails = utils.cast(int, data.attrib.get('skipDetails'))
        self.subtype = data.attrib.get('subtype')
        self.thumbAspectRatio = data.attrib.get('thumbAspectRatio')
        self.viewOffset = utils.cast(int, data.attrib.get('viewOffset', 0))
        self.year = utils.cast(int, data.attrib.get('year'))

    @property
    def locations(self):
        """ This does not exist in plex xml response but is added to have a common
            interface to get the locations of the clip.

            Returns:
                List<str> of file paths where the clip is found on disk.
        """
        return [part.file for part in self.iterParts() if part]

    def _prettyfilename(self):
        """ Returns a filename for use in download. """
        return self.title

    @property
    def metadataDirectory(self):
        """ Returns the Plex Media Server data directory where the metadata is stored. """
        guid_hash = utils.sha1hash(self.guid)
        return str(Path('Metadata') / 'Movies' / guid_hash[0] / f'{guid_hash[1:]}.bundle')


class Extra(Clip):
    """ Represents a single Extra (trailer, behindTheScenes, etc). """

    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        super(Extra, self)._loadData(data)
        parent = self._parent()
        self.librarySectionID = parent.librarySectionID
        self.librarySectionKey = parent.librarySectionKey
        self.librarySectionTitle = parent.librarySectionTitle

    def _prettyfilename(self):
        """ Returns a filename for use in download. """
        return f'{self.title} ({self.subtype})'


@utils.registerPlexObject
class MovieSession(PlexSession, Movie):
    """ Represents a single Movie session
        loaded from :func:`~plexapi.server.PlexServer.sessions`.
    """
    _SESSIONTYPE = True

    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        Movie._loadData(self, data)
        PlexSession._loadData(self, data)


@utils.registerPlexObject
class EpisodeSession(PlexSession, Episode):
    """ Represents a single Episode session
        loaded from :func:`~plexapi.server.PlexServer.sessions`.
    """
    _SESSIONTYPE = True

    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        Episode._loadData(self, data)
        PlexSession._loadData(self, data)


@utils.registerPlexObject
class ClipSession(PlexSession, Clip):
    """ Represents a single Clip session
        loaded from :func:`~plexapi.server.PlexServer.sessions`.
    """
    _SESSIONTYPE = True

    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        Clip._loadData(self, data)
        PlexSession._loadData(self, data)


@utils.registerPlexObject
class MovieHistory(PlexHistory, Movie):
    """ Represents a single Movie history entry
        loaded from :func:`~plexapi.server.PlexServer.history`.
    """
    _HISTORYTYPE = True

    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        Movie._loadData(self, data)
        PlexHistory._loadData(self, data)


@utils.registerPlexObject
class EpisodeHistory(PlexHistory, Episode):
    """ Represents a single Episode history entry
        loaded from :func:`~plexapi.server.PlexServer.history`.
    """
    _HISTORYTYPE = True

    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        Episode._loadData(self, data)
        PlexHistory._loadData(self, data)


@utils.registerPlexObject
class ClipHistory(PlexHistory, Clip):
    """ Represents a single Clip history entry
        loaded from :func:`~plexapi.server.PlexServer.history`.
    """
    _HISTORYTYPE = True

    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        Clip._loadData(self, data)
        PlexHistory._loadData(self, data)
