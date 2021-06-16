# -*- coding: utf-8 -*-
import os
from urllib.parse import quote_plus, urlencode

from plexapi import library, media, utils
from plexapi.base import Playable, PlexPartialObject
from plexapi.exceptions import BadRequest
from plexapi.mixins import AdvancedSettingsMixin, ArtUrlMixin, ArtMixin, BannerMixin, PosterUrlMixin, PosterMixin
from plexapi.mixins import RatingMixin, SplitMergeMixin, UnmatchMatchMixin
from plexapi.mixins import CollectionMixin, CountryMixin, DirectorMixin, GenreMixin, LabelMixin, ProducerMixin, WriterMixin


class Video(PlexPartialObject):
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
            updatedAt (datatime): Datetime the item was updated.
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

    @property
    def isWatched(self):
        """ Returns True if this video is watched. """
        return bool(self.viewCount > 0) if self.viewCount else False

    def url(self, part):
        """ Returns the full url for something. Typically used for getting a specific image. """
        return self._server.url(part, includeToken=True) if part else None

    def markWatched(self):
        """ Mark the video as palyed. """
        key = '/:/scrobble?key=%s&identifier=com.plexapp.plugins.library' % self.ratingKey
        self._server.query(key)

    def markUnwatched(self):
        """ Mark the video as unplayed. """
        key = '/:/unscrobble?key=%s&identifier=com.plexapp.plugins.library' % self.ratingKey
        self._server.query(key)

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

    def subtitleStreams(self):
        """ Returns a list of :class:`~plexapi.media.SubtitleStream` objects for all MediaParts. """
        streams = []

        parts = self.iterParts()
        for part in parts:
            streams += part.subtitleStreams()
        return streams

    def uploadSubtitles(self, filepath):
        """ Upload Subtitle file for video. """
        url = '%s/subtitles' % self.key
        filename = os.path.basename(filepath)
        subFormat = os.path.splitext(filepath)[1][1:]
        with open(filepath, 'rb') as subfile:
            params = {'title': filename,
                      'format': subFormat
                      }
            headers = {'Accept': 'text/plain, */*'}
            self._server.query(url, self._server._session.post, data=subfile, params=params, headers=headers)

    def removeSubtitles(self, streamID=None, streamTitle=None):
        """ Remove Subtitle from movie's subtitles listing.

            Note: If subtitle file is located inside video directory it will bbe deleted.
            Files outside of video directory are not effected.
        """
        for stream in self.subtitleStreams():
            if streamID == stream.id or streamTitle == stream.title:
                self._server.query(stream.key, self._server._session.delete)

    def optimize(self, title=None, target="", targetTagID=None, locationID=-1, policyScope='all',
                 policyValue="", policyUnwatched=0, videoQuality=None, deviceProfile=None):
        """ Optimize item

            locationID (int): -1 in folder with original items
                               2 library path id
                                 library path id is found in library.locations[i].id

            target (str): custom quality name.
                          if none provided use "Custom: {deviceProfile}"

            targetTagID (int):  Default quality settings
                                1 Mobile
                                2 TV
                                3 Original Quality

            deviceProfile (str): Android, IOS, Universal TV, Universal Mobile, Windows Phone,
                                    Windows, Xbox One

            Example:
                Optimize for Mobile
                   item.optimize(targetTagID="Mobile") or item.optimize(targetTagID=1")
                Optimize for Android 10 MBPS 1080p
                   item.optimize(deviceProfile="Android", videoQuality=10)
                Optimize for IOS Original Quality
                   item.optimize(deviceProfile="IOS", videoQuality=-1)

            * see sync.py VIDEO_QUALITIES for additional information for using videoQuality
        """
        tagValues = [1, 2, 3]
        tagKeys = ["Mobile", "TV", "Original Quality"]
        tagIDs = tagKeys + tagValues

        if targetTagID not in tagIDs and (deviceProfile is None or videoQuality is None):
            raise BadRequest('Unexpected or missing quality profile.')

        libraryLocationIDs = [location.id for location in self.section()._locations()]
        libraryLocationIDs.append(-1)

        if locationID not in libraryLocationIDs:
            raise BadRequest('Unexpected library path ID. %s not in %s' %
                             (locationID, libraryLocationIDs))

        if isinstance(targetTagID, str):
            tagIndex = tagKeys.index(targetTagID)
            targetTagID = tagValues[tagIndex]

        if title is None:
            title = self.title

        backgroundProcessing = self.fetchItem('/playlists?type=42')
        key = '%s/items?' % backgroundProcessing.key
        params = {
            'Item[type]': 42,
            'Item[target]': target,
            'Item[targetTagID]': targetTagID if targetTagID else '',
            'Item[locationID]': locationID,
            'Item[Policy][scope]': policyScope,
            'Item[Policy][value]': policyValue,
            'Item[Policy][unwatched]': policyUnwatched
        }

        if deviceProfile:
            params['Item[Device][profile]'] = deviceProfile

        if videoQuality:
            from plexapi.sync import MediaSettings
            mediaSettings = MediaSettings.createVideo(videoQuality)
            params['Item[MediaSettings][videoQuality]'] = mediaSettings.videoQuality
            params['Item[MediaSettings][videoResolution]'] = mediaSettings.videoResolution
            params['Item[MediaSettings][maxVideoBitrate]'] = mediaSettings.maxVideoBitrate
            params['Item[MediaSettings][audioBoost]'] = ''
            params['Item[MediaSettings][subtitleSize]'] = ''
            params['Item[MediaSettings][musicBitrate]'] = ''
            params['Item[MediaSettings][photoQuality]'] = ''

        titleParam = {'Item[title]': title}
        section = self._server.library.sectionByID(self.librarySectionID)
        params['Item[Location][uri]'] = 'library://' + section.uuid + '/item/' + \
                                        quote_plus(self.key + '?includeExternalMedia=1')

        data = key + urlencode(params) + '&' + urlencode(titleParam)
        return self._server.query(data, method=self._server._session.put)

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

        sync_item.location = 'library://%s/item/%s' % (section.uuid, quote_plus(self.key))
        sync_item.policy = Policy.create(limit, unwatched)
        sync_item.mediaSettings = MediaSettings.createVideo(videoQuality)

        return myplex.sync(sync_item, client=client, clientId=clientId)


@utils.registerPlexObject
class Movie(Video, Playable, AdvancedSettingsMixin, ArtMixin, PosterMixin, RatingMixin, SplitMergeMixin, UnmatchMatchMixin,
        CollectionMixin, CountryMixin, DirectorMixin, GenreMixin, LabelMixin, ProducerMixin, WriterMixin):
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
            genres (List<:class:`~plexapi.media.Genre`>): List of genre objects.
            guids (List<:class:`~plexapi.media.Guid`>): List of guid objects.
            labels (List<:class:`~plexapi.media.Label`>): List of label objects.
            languageOverride (str): Setting that indicates if a languge is used to override metadata
                (eg. en-CA, None = Library default).
            media (List<:class:`~plexapi.media.Media`>): List of media objects.
            originallyAvailableAt (datetime): Datetime the movie was released.
            originalTitle (str): Original title, often the foreign title (転々; 엽기적인 그녀).
            primaryExtraKey (str) Primary extra key (/library/metadata/66351).
            producers (List<:class:`~plexapi.media.Producer`>): List of producers objects.
            rating (float): Movie critic rating (7.9; 9.8; 8.1).
            ratingImage (str): Key to critic rating image (rottentomatoes://image.rating.rotten).
            roles (List<:class:`~plexapi.media.Role`>): List of role objects.
            similar (List<:class:`~plexapi.media.Similar`>): List of Similar objects.
            studio (str): Studio that created movie (Di Bonaventura Pictures; 21 Laps Entertainment).
            tagline (str): Movie tag line (Back 2 Work; Who says men can't change?).
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
        self.genres = self.findItems(data, media.Genre)
        self.guids = self.findItems(data, media.Guid)
        self.labels = self.findItems(data, media.Label)
        self.languageOverride = data.attrib.get('languageOverride')
        self.media = self.findItems(data, media.Media)
        self.originallyAvailableAt = utils.toDatetime(data.attrib.get('originallyAvailableAt'), '%Y-%m-%d')
        self.originalTitle = data.attrib.get('originalTitle')
        self.primaryExtraKey = data.attrib.get('primaryExtraKey')
        self.producers = self.findItems(data, media.Producer)
        self.rating = utils.cast(float, data.attrib.get('rating'))
        self.ratingImage = data.attrib.get('ratingImage')
        self.roles = self.findItems(data, media.Role)
        self.similar = self.findItems(data, media.Similar)
        self.studio = data.attrib.get('studio')
        self.tagline = data.attrib.get('tagline')
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
    def hasPreviewThumbnails(self):
        """ Returns True if any of the media parts has generated preview (BIF) thumbnails. """
        return any(part.hasPreviewThumbnails for media in self.media for part in media.parts)

    def _prettyfilename(self):
        # This is just for compat.
        return self.title

    def reviews(self):
        """ Returns a list of :class:`~plexapi.media.Review` objects. """
        data = self._server.query(self._details_key)
        return self.findItems(data, media.Review, rtag='Video')

    def extras(self):
        """ Returns a list of :class:`~plexapi.video.Extra` objects. """
        data = self._server.query(self._details_key)
        return self.findItems(data, Extra, rtag='Extras')

    def hubs(self):
        """ Returns a list of :class:`~plexapi.library.Hub` objects. """
        data = self._server.query(self._details_key)
        return self.findItems(data, library.Hub, rtag='Related')

    def download(self, savepath=None, keep_original_name=False, **kwargs):
        """ Download video files to specified directory.

            Parameters:
                savepath (str): Defaults to current working dir.
                keep_original_name (bool): True to keep the original file name otherwise
                    a friendlier is generated.
                **kwargs: Additional options passed into :func:`~plexapi.base.PlexObject.getStreamURL`.
        """
        filepaths = []
        locations = [i for i in self.iterParts() if i]
        for location in locations:
            name = location.file
            if not keep_original_name:
                title = self.title.replace(' ', '.')
                name = '%s.%s' % (title, location.container)
            if kwargs is not None:
                url = self.getStreamURL(**kwargs)
            else:
                self._server.url('%s?download=1' % location.key)
            filepath = utils.download(url, self._server._token, filename=name,
                                      savepath=savepath, session=self._server._session)
            if filepath:
                filepaths.append(filepath)
        return filepaths


@utils.registerPlexObject
class Show(Video, AdvancedSettingsMixin, ArtMixin, BannerMixin, PosterMixin, RatingMixin, SplitMergeMixin, UnmatchMatchMixin,
        CollectionMixin, GenreMixin, LabelMixin):
    """ Represents a single Show (including all seasons and episodes).

        Attributes:
            TAG (str): 'Directory'
            TYPE (str): 'show'
            audienceRating (float): Audience rating (TMDB or TVDB).
            audienceRatingImage (str): Key to audience rating image (tmdb://image.rating).
            autoDeletionItemPolicyUnwatchedLibrary (int): Setting that indicates the number of unplayed
                episodes to keep for the show (0 = All episodes, 5 = 5 latest episodes, 3 = 3 latest episodes,
                1 = 1 latest episode, -3 = Episodes added in the past 3 days, -7 = Episodes added in the
                past 7 days, -30 = Episodes added in the past 30 days).
            autoDeletionItemPolicyWatchedLibrary (int): Setting that indicates if episodes are deleted
                after being watched for the show (0 = Never, 1 = After a day, 7 = After a week,
                100 = On next refresh).
            banner (str): Key to banner artwork (/library/metadata/<ratingkey>/banner/<bannerid>).
            childCount (int): Number of seasons in the show.
            collections (List<:class:`~plexapi.media.Collection`>): List of collection objects.
            contentRating (str) Content rating (PG-13; NR; TV-G).
            duration (int): Typical duration of the show episodes in milliseconds.
            episodeSort (int): Setting that indicates how episodes are sorted for the show
                (-1 = Library default, 0 = Oldest first, 1 = Newest first).
            flattenSeasons (int): Setting that indicates if seasons are set to hidden for the show
                (-1 = Library default, 0 = Hide, 1 = Show).
            genres (List<:class:`~plexapi.media.Genre`>): List of genre objects.
            guids (List<:class:`~plexapi.media.Guid`>): List of guid objects.
            index (int): Plex index number for the show.
            key (str): API URL (/library/metadata/<ratingkey>).
            labels (List<:class:`~plexapi.media.Label`>): List of label objects.
            languageOverride (str): Setting that indicates if a languge is used to override metadata
                (eg. en-CA, None = Library default).
            leafCount (int): Number of items in the show view.
            locations (List<str>): List of folder paths where the show is found on disk.
            network (str): The network that distributed the show.
            originallyAvailableAt (datetime): Datetime the show was released.
            originalTitle (str): The original title of the show.
            rating (float): Show rating (7.9; 9.8; 8.1).
            roles (List<:class:`~plexapi.media.Role`>): List of role objects.
            showOrdering (str): Setting that indicates the episode ordering for the show
                (None = Library default).
            similar (List<:class:`~plexapi.media.Similar`>): List of Similar objects.
            studio (str): Studio that created show (Di Bonaventura Pictures; 21 Laps Entertainment).
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
        self.autoDeletionItemPolicyUnwatchedLibrary = utils.cast(
            int, data.attrib.get('autoDeletionItemPolicyUnwatchedLibrary', '0'))
        self.autoDeletionItemPolicyWatchedLibrary = utils.cast(
            int, data.attrib.get('autoDeletionItemPolicyWatchedLibrary', '0'))
        self.banner = data.attrib.get('banner')
        self.childCount = utils.cast(int, data.attrib.get('childCount'))
        self.collections = self.findItems(data, media.Collection)
        self.contentRating = data.attrib.get('contentRating')
        self.duration = utils.cast(int, data.attrib.get('duration'))
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
        self.roles = self.findItems(data, media.Role)
        self.showOrdering = data.attrib.get('showOrdering')
        self.similar = self.findItems(data, media.Similar)
        self.studio = data.attrib.get('studio')
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
    def isWatched(self):
        """ Returns True if the show is fully watched. """
        return bool(self.viewedLeafCount == self.leafCount)

    def hubs(self):
        """ Returns a list of :class:`~plexapi.library.Hub` objects. """
        data = self._server.query(self._details_key)
        return self.findItems(data, library.Hub, rtag='Related')

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
        key = '/library/metadata/%s/children?excludeAllLeaves=1' % self.ratingKey
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
        key = '/library/metadata/%s/children?excludeAllLeaves=1' % self.ratingKey
        return self.fetchItems(key, Season, **kwargs)

    def episode(self, title=None, season=None, episode=None):
        """ Find a episode using a title or season and episode.

            Parameters:
                title (str): Title of the episode to return
                season (int): Season number (default: None; required if title not specified).
                episode (int): Episode number (default: None; required if title not specified).

            Raises:
                :exc:`~plexapi.exceptions.BadRequest`: If title or season and episode parameters are missing.
        """
        key = '/library/metadata/%s/allLeaves' % self.ratingKey
        if title is not None:
            return self.fetchItem(key, Episode, title__iexact=title)
        elif season is not None and episode is not None:
            return self.fetchItem(key, Episode, parentIndex=season, index=episode)
        raise BadRequest('Missing argument: title or season and episode are required')

    def episodes(self, **kwargs):
        """ Returns a list of :class:`~plexapi.video.Episode` objects in the show. """
        key = '/library/metadata/%s/allLeaves' % self.ratingKey
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

    def download(self, savepath=None, keep_original_name=False, **kwargs):
        """ Download video files to specified directory.

            Parameters:
                savepath (str): Defaults to current working dir.
                keep_original_name (bool): True to keep the original file name otherwise
                    a friendlier is generated.
                **kwargs: Additional options passed into :func:`~plexapi.base.PlexObject.getStreamURL`.
        """
        filepaths = []
        for episode in self.episodes():
            filepaths += episode.download(savepath, keep_original_name, **kwargs)
        return filepaths


@utils.registerPlexObject
class Season(Video, ArtMixin, PosterMixin, RatingMixin, CollectionMixin):
    """ Represents a single Show Season (including all episodes).

        Attributes:
            TAG (str): 'Directory'
            TYPE (str): 'season'
            collections (List<:class:`~plexapi.media.Collection`>): List of collection objects.
            guids (List<:class:`~plexapi.media.Guid`>): List of guid objects.
            index (int): Season number.
            key (str): API URL (/library/metadata/<ratingkey>).
            leafCount (int): Number of items in the season view.
            parentGuid (str): Plex GUID for the show (plex://show/5d9c086fe9d5a1001f4d9fe6).
            parentIndex (int): Plex index number for the show.
            parentKey (str): API URL of the show (/library/metadata/<parentRatingKey>).
            parentRatingKey (int): Unique key identifying the show.
            parentStudio (str): Studio that created show.
            parentTheme (str): URL to show theme resource (/library/metadata/<parentRatingkey>/theme/<themeid>).
            parentThumb (str): URL to show thumbnail image (/library/metadata/<parentRatingKey>/thumb/<thumbid>).
            parentTitle (str): Name of the show for the season.
            viewedLeafCount (int): Number of items marked as played in the season view.
            year (int): Year the season was released.
    """
    TAG = 'Directory'
    TYPE = 'season'
    METADATA_TYPE = 'episode'

    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        Video._loadData(self, data)
        self.collections = self.findItems(data, media.Collection)
        self.guids = self.findItems(data, media.Guid)
        self.index = utils.cast(int, data.attrib.get('index'))
        self.key = self.key.replace('/children', '')  # FIX_BUG_50
        self.leafCount = utils.cast(int, data.attrib.get('leafCount'))
        self.parentGuid = data.attrib.get('parentGuid')
        self.parentIndex = utils.cast(int, data.attrib.get('parentIndex'))
        self.parentKey = data.attrib.get('parentKey')
        self.parentRatingKey = utils.cast(int, data.attrib.get('parentRatingKey'))
        self.parentStudio = data.attrib.get('parentStudio')
        self.parentTheme = data.attrib.get('parentTheme')
        self.parentThumb = data.attrib.get('parentThumb')
        self.parentTitle = data.attrib.get('parentTitle')
        self.viewedLeafCount = utils.cast(int, data.attrib.get('viewedLeafCount'))
        self.year = utils.cast(int, data.attrib.get('year'))

    def __iter__(self):
        for episode in self.episodes():
            yield episode

    def __repr__(self):
        return '<%s>' % ':'.join([p for p in [
            self.__class__.__name__,
            self.key.replace('/library/metadata/', '').replace('/children', ''),
            '%s-s%s' % (self.parentTitle.replace(' ', '-')[:20], self.seasonNumber),
        ] if p])

    @property
    def isWatched(self):
        """ Returns True if the season is fully watched. """
        return bool(self.viewedLeafCount == self.leafCount)

    @property
    def seasonNumber(self):
        """ Returns the season number. """
        return self.index

    def episodes(self, **kwargs):
        """ Returns a list of :class:`~plexapi.video.Episode` objects in the season. """
        key = '/library/metadata/%s/children' % self.ratingKey
        return self.fetchItems(key, Episode, **kwargs)

    def episode(self, title=None, episode=None):
        """ Returns the episode with the given title or number.

            Parameters:
                title (str): Title of the episode to return.
                episode (int): Episode number (default: None; required if title not specified).

            Raises:
                :exc:`~plexapi.exceptions.BadRequest`: If title or episode parameter is missing.
        """
        key = '/library/metadata/%s/children' % self.ratingKey
        if title is not None and not isinstance(title, int):
            return self.fetchItem(key, Episode, title__iexact=title)
        elif episode is not None or isinstance(title, int):
            if isinstance(title, int):
                index = title
            else:
                index = episode
            return self.fetchItem(key, Episode, parentIndex=self.index, index=index)
        raise BadRequest('Missing argument: title or episode is required')

    def get(self, title=None, episode=None):
        """ Alias to :func:`~plexapi.video.Season.episode`. """
        return self.episode(title, episode)

    def onDeck(self):
        """ Returns season's On Deck :class:`~plexapi.video.Video` object or `None`.
            Will only return a match if the show's On Deck episode is in this season.
        """
        data = self._server.query(self._details_key)
        return next(iter(self.findItems(data, rtag='OnDeck')), None)

    def show(self):
        """ Return the season's :class:`~plexapi.video.Show`. """
        return self.fetchItem(self.parentRatingKey)

    def watched(self):
        """ Returns list of watched :class:`~plexapi.video.Episode` objects. """
        return self.episodes(viewCount__gt=0)

    def unwatched(self):
        """ Returns list of unwatched :class:`~plexapi.video.Episode` objects. """
        return self.episodes(viewCount=0)

    def download(self, savepath=None, keep_original_name=False, **kwargs):
        """ Download video files to specified directory.

            Parameters:
                savepath (str): Defaults to current working dir.
                keep_original_name (bool): True to keep the original file name otherwise
                    a friendlier is generated.
                **kwargs: Additional options passed into :func:`~plexapi.base.PlexObject.getStreamURL`.
        """
        filepaths = []
        for episode in self.episodes():
            filepaths += episode.download(savepath, keep_original_name, **kwargs)
        return filepaths

    def _defaultSyncTitle(self):
        """ Returns str, default title for a new syncItem. """
        return '%s - %s' % (self.parentTitle, self.title)


@utils.registerPlexObject
class Episode(Video, Playable, ArtMixin, PosterMixin, RatingMixin,
        CollectionMixin, DirectorMixin, WriterMixin):
    """ Represents a single Shows Episode.

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
            markers (List<:class:`~plexapi.media.Marker`>): List of marker objects.
            media (List<:class:`~plexapi.media.Media`>): List of media objects.
            originallyAvailableAt (datetime): Datetime the episode was released.
            parentGuid (str): Plex GUID for the season (plex://season/5d9c09e42df347001e3c2a72).
            parentIndex (int): Season number of episode.
            parentKey (str): API URL of the season (/library/metadata/<parentRatingKey>).
            parentRatingKey (int): Unique key  identifying the season.
            parentThumb (str): URL to season thumbnail image (/library/metadata/<parentRatingKey>/thumb/<thumbid>).
            parentTitle (str): Name of the season for the episode.
            parentYear (int): Year the season was released.
            rating (float): Episode rating (7.9; 9.8; 8.1).
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
        self._seasonNumber = None  # cached season number
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
        self.markers = self.findItems(data, media.Marker)
        self.media = self.findItems(data, media.Media)
        self.originallyAvailableAt = utils.toDatetime(data.attrib.get('originallyAvailableAt'), '%Y-%m-%d')
        self.parentGuid = data.attrib.get('parentGuid')
        self.parentIndex = utils.cast(int, data.attrib.get('parentIndex'))
        self.parentKey = data.attrib.get('parentKey')
        self.parentRatingKey = utils.cast(int, data.attrib.get('parentRatingKey'))
        self.parentThumb = data.attrib.get('parentThumb')
        self.parentTitle = data.attrib.get('parentTitle')
        self.parentYear = utils.cast(int, data.attrib.get('parentYear'))
        self.rating = utils.cast(float, data.attrib.get('rating'))
        self.skipParent = utils.cast(bool, data.attrib.get('skipParent', '0'))
        self.viewOffset = utils.cast(int, data.attrib.get('viewOffset', 0))
        self.writers = self.findItems(data, media.Writer)
        self.year = utils.cast(int, data.attrib.get('year'))

        # If seasons are hidden, parentKey and parentRatingKey are missing from the XML response.
        # https://forums.plex.tv/t/parentratingkey-not-in-episode-xml-when-seasons-are-hidden/300553
        if self.skipParent and not self.parentRatingKey:
            # Parse the parentRatingKey from the parentThumb
            if self.parentThumb and self.parentThumb.startswith('/library/metadata/'):
                self.parentRatingKey = utils.cast(int, self.parentThumb.split('/')[3])
            # Get the parentRatingKey from the season's ratingKey
            if not self.parentRatingKey and self.grandparentRatingKey:
                self.parentRatingKey = self.show().season(season=self.parentIndex).ratingKey
            if self.parentRatingKey:
                self.parentKey = '/library/metadata/%s' % self.parentRatingKey

    def __repr__(self):
        return '<%s>' % ':'.join([p for p in [
            self.__class__.__name__,
            self.key.replace('/library/metadata/', '').replace('/children', ''),
            '%s-%s' % (self.grandparentTitle.replace(' ', '-')[:20], self.seasonEpisode),
        ] if p])

    def _prettyfilename(self):
        """ Returns a human friendly filename. """
        return '%s.%s' % (self.grandparentTitle.replace(' ', '.'), self.seasonEpisode)

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

    @property
    def seasonNumber(self):
        """ Returns the episode's season number. """
        if self._seasonNumber is None:
            self._seasonNumber = self.parentIndex if self.parentIndex else self.season().seasonNumber
        return utils.cast(int, self._seasonNumber)

    @property
    def seasonEpisode(self):
        """ Returns the s00e00 string containing the season and episode numbers. """
        return 's%se%s' % (str(self.seasonNumber).zfill(2), str(self.episodeNumber).zfill(2))

    @property
    def hasIntroMarker(self):
        """ Returns True if the episode has an intro marker in the xml. """
        return any(marker.type == 'intro' for marker in self.markers)

    @property
    def hasPreviewThumbnails(self):
        """ Returns True if any of the media parts has generated preview (BIF) thumbnails. """
        return any(part.hasPreviewThumbnails for media in self.media for part in media.parts)

    def season(self):
        """" Return the episode's :class:`~plexapi.video.Season`. """
        return self.fetchItem(self.parentKey)

    def show(self):
        """" Return the episode's :class:`~plexapi.video.Show`. """
        return self.fetchItem(self.grandparentRatingKey)

    def _defaultSyncTitle(self):
        """ Returns str, default title for a new syncItem. """
        return '%s - %s - (%s) %s' % (self.grandparentTitle, self.parentTitle, self.seasonEpisode, self.title)


@utils.registerPlexObject
class Clip(Video, Playable, ArtUrlMixin, PosterUrlMixin):
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
        return self.title


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
        return '%s (%s)' % (self.title, self.subtype)
