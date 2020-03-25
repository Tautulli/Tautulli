# -*- coding: utf-8 -*-
from plexapi import media, utils
from plexapi.exceptions import BadRequest, NotFound
from plexapi.base import Playable, PlexPartialObject
from plexapi.compat import quote_plus


class Video(PlexPartialObject):
    """ Base class for all video objects including :class:`~plexapi.video.Movie`,
        :class:`~plexapi.video.Show`, :class:`~plexapi.video.Season`,
        :class:`~plexapi.video.Episode`.

        Attributes:
            addedAt (datetime): Datetime this item was added to the library.
            key (str): API URL (/library/metadata/<ratingkey>).
            lastViewedAt (datetime): Datetime item was last accessed.
            librarySectionID (int): :class:`~plexapi.library.LibrarySection` ID.
            listType (str): Hardcoded as 'audio' (useful for search filters).
            ratingKey (int): Unique key identifying this item.
            summary (str): Summary of the artist, track, or album.
            thumb (str): URL to thumbnail image.
            title (str): Artist, Album or Track title. (Jason Mraz, We Sing, Lucky, etc.)
            titleSort (str): Title to use when sorting (defaults to title).
            type (str): 'artist', 'album', or 'track'.
            updatedAt (datatime): Datetime this item was updated.
            viewCount (int): Count of times this item was accessed.
    """

    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        self._data = data
        self.listType = 'video'
        self.addedAt = utils.toDatetime(data.attrib.get('addedAt'))
        self.key = data.attrib.get('key', '')
        self.lastViewedAt = utils.toDatetime(data.attrib.get('lastViewedAt'))
        self.librarySectionID = data.attrib.get('librarySectionID')
        self.ratingKey = utils.cast(int, data.attrib.get('ratingKey'))
        self.summary = data.attrib.get('summary')
        self.thumb = data.attrib.get('thumb')
        self.title = data.attrib.get('title')
        self.titleSort = data.attrib.get('titleSort', self.title)
        self.type = data.attrib.get('type')
        self.updatedAt = utils.toDatetime(data.attrib.get('updatedAt'))
        self.viewCount = utils.cast(int, data.attrib.get('viewCount', 0))

    @property
    def isWatched(self):
        """ Returns True if this video is watched. """
        return bool(self.viewCount > 0) if self.viewCount else False

    @property
    def thumbUrl(self):
        """ Return the first first thumbnail url starting on
            the most specific thumbnail for that item.
        """
        thumb = self.firstAttr('thumb', 'parentThumb', 'granparentThumb')
        return self._server.url(thumb, includeToken=True) if thumb else None

    @property
    def artUrl(self):
        """ Return the first first art url starting on the most specific for that item."""
        art = self.firstAttr('art', 'grandparentArt')
        return self._server.url(art, includeToken=True) if art else None

    def url(self, part):
        """ Returns the full url for something. Typically used for getting a specific image. """
        return self._server.url(part, includeToken=True) if part else None

    def markWatched(self):
        """ Mark video as watched. """
        key = '/:/scrobble?key=%s&identifier=com.plexapp.plugins.library' % self.ratingKey
        self._server.query(key)
        self.reload()

    def markUnwatched(self):
        """ Mark video unwatched. """
        key = '/:/unscrobble?key=%s&identifier=com.plexapp.plugins.library' % self.ratingKey
        self._server.query(key)
        self.reload()

    def rate(self, rate):
        """ Rate video. """
        key = '/:/rate?key=%s&identifier=com.plexapp.plugins.library&rating=%s' % (self.ratingKey, rate)

        self._server.query(key)
        self.reload()

    def _defaultSyncTitle(self):
        """ Returns str, default title for a new syncItem. """
        return self.title

    def posters(self):
        """ Returns list of available poster objects. :class:`~plexapi.media.Poster`:"""

        return self.fetchItems('%s/posters' % self.key, cls=media.Poster)

    def sync(self, videoQuality, client=None, clientId=None, limit=None, unwatched=False, title=None):
        """ Add current video (movie, tv-show, season or episode) as sync item for specified device.
            See :func:`plexapi.myplex.MyPlexAccount.sync()` for possible exceptions.

            Parameters:
                videoQuality (int): idx of quality of the video, one of VIDEO_QUALITY_* values defined in
                                    :mod:`plexapi.sync` module.
                client (:class:`plexapi.myplex.MyPlexDevice`): sync destination, see
                                                               :func:`plexapi.myplex.MyPlexAccount.sync`.
                clientId (str): sync destination, see :func:`plexapi.myplex.MyPlexAccount.sync`.
                limit (int): maximum count of items to sync, unlimited if `None`.
                unwatched (bool): if `True` watched videos wouldn't be synced.
                title (str): descriptive title for the new :class:`plexapi.sync.SyncItem`, if empty the value would be
                             generated from metadata of current media.

            Returns:
                :class:`plexapi.sync.SyncItem`: an instance of created syncItem.
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
class Movie(Playable, Video):
    """ Represents a single Movie.

        Attributes:
            TAG (str): 'Video'
            TYPE (str): 'movie'
            art (str): Key to movie artwork (/library/metadata/<ratingkey>/art/<artid>)
            audienceRating (float): Audience rating (usually from Rotten Tomatoes).
            audienceRatingImage (str): Key to audience rating image (rottentomatoes://image.rating.spilled)
            chapterSource (str): Chapter source (agent; media; mixed).
            contentRating (str) Content rating (PG-13; NR; TV-G).
            duration (int): Duration of movie in milliseconds.
            guid: Plex GUID (com.plexapp.agents.imdb://tt4302938?lang=en).
            originalTitle (str): Original title, often the foreign title (転々; 엽기적인 그녀).
            originallyAvailableAt (datetime): Datetime movie was released.
            primaryExtraKey (str) Primary extra key (/library/metadata/66351).
            rating (float): Movie rating (7.9; 9.8; 8.1).
            ratingImage (str): Key to rating image (rottentomatoes://image.rating.rotten).
            studio (str): Studio that created movie (Di Bonaventura Pictures; 21 Laps Entertainment).
            tagline (str): Movie tag line (Back 2 Work; Who says men can't change?).
            userRating (float): User rating (2.0; 8.0).
            viewOffset (int): View offset in milliseconds.
            year (int): Year movie was released.
            collections (List<:class:`~plexapi.media.Collection`>): List of collections this media belongs.
            countries (List<:class:`~plexapi.media.Country`>): List of countries objects.
            directors (List<:class:`~plexapi.media.Director`>): List of director objects.
            fields (List<:class:`~plexapi.media.Field`>): List of field objects.
            genres (List<:class:`~plexapi.media.Genre`>): List of genre objects.
            media (List<:class:`~plexapi.media.Media`>): List of media objects.
            producers (List<:class:`~plexapi.media.Producer`>): List of producers objects.
            roles (List<:class:`~plexapi.media.Role`>): List of role objects.
            writers (List<:class:`~plexapi.media.Writer`>): List of writers objects.
            chapters (List<:class:`~plexapi.media.Chapter`>): List of Chapter objects.
            similar (List<:class:`~plexapi.media.Similar`>): List of Similar objects.
    """
    TAG = 'Video'
    TYPE = 'movie'
    METADATA_TYPE = 'movie'
    _include = ('?checkFiles=1&includeExtras=1&includeRelated=1'
                '&includeOnDeck=1&includeChapters=1&includePopularLeaves=1'
                '&includeConcerts=1&includePreferences=1')

    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        Video._loadData(self, data)
        Playable._loadData(self, data)

        self._details_key = self.key + self._include
        self.art = data.attrib.get('art')
        self.audienceRating = utils.cast(float, data.attrib.get('audienceRating'))
        self.audienceRatingImage = data.attrib.get('audienceRatingImage')
        self.chapterSource = data.attrib.get('chapterSource')
        self.contentRating = data.attrib.get('contentRating')
        self.duration = utils.cast(int, data.attrib.get('duration'))
        self.guid = data.attrib.get('guid')
        self.originalTitle = data.attrib.get('originalTitle')
        self.originallyAvailableAt = utils.toDatetime(
            data.attrib.get('originallyAvailableAt'), '%Y-%m-%d')
        self.primaryExtraKey = data.attrib.get('primaryExtraKey')
        self.rating = utils.cast(float, data.attrib.get('rating'))
        self.ratingImage = data.attrib.get('ratingImage')
        self.studio = data.attrib.get('studio')
        self.tagline = data.attrib.get('tagline')
        self.userRating = utils.cast(float, data.attrib.get('userRating'))
        self.viewOffset = utils.cast(int, data.attrib.get('viewOffset', 0))
        self.year = utils.cast(int, data.attrib.get('year'))
        self.collections = self.findItems(data, media.Collection)
        self.countries = self.findItems(data, media.Country)
        self.directors = self.findItems(data, media.Director)
        self.fields = self.findItems(data, media.Field)
        self.genres = self.findItems(data, media.Genre)
        self.media = self.findItems(data, media.Media)
        self.producers = self.findItems(data, media.Producer)
        self.roles = self.findItems(data, media.Role)
        self.writers = self.findItems(data, media.Writer)
        self.labels = self.findItems(data, media.Label)
        self.chapters = self.findItems(data, media.Chapter)
        self.similar = self.findItems(data, media.Similar)

    @property
    def actors(self):
        """ Alias to self.roles. """
        return self.roles

    @property
    def locations(self):
        """ This does not exist in plex xml response but is added to have a common
            interface to get the location of the Movie/Show/Episode
        """
        return [part.file for part in self.iterParts() if part]

    def subtitleStreams(self):
        """ Returns a list of :class:`~plexapi.media.SubtitleStream` objects for all MediaParts. """
        streams = []
        for elem in self.media:
            for part in elem.parts:
                streams += part.subtitleStreams()
        return streams

    def _prettyfilename(self):
        # This is just for compat.
        return self.title

    def download(self, savepath=None, keep_original_name=False, **kwargs):
        """ Download video files to specified directory.

            Parameters:
                savepath (str): Defaults to current working dir.
                keep_original_name (bool): True to keep the original file name otherwise
                    a friendlier is generated.
                **kwargs: Additional options passed into :func:`~plexapi.base.PlexObject.getStreamURL()`.
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
class Show(Video):
    """ Represents a single Show (including all seasons and episodes).

        Attributes:
            TAG (str): 'Directory'
            TYPE (str): 'show'
            art (str): Key to show artwork (/library/metadata/<ratingkey>/art/<artid>)
            banner (str): Key to banner artwork (/library/metadata/<ratingkey>/art/<artid>)
            childCount (int): Unknown.
            contentRating (str) Content rating (PG-13; NR; TV-G).
            collections (List<:class:`~plexapi.media.Collection`>): List of collections this media belongs.
            duration (int): Duration of show in milliseconds.
            guid (str): Plex GUID (com.plexapp.agents.imdb://tt4302938?lang=en).
            index (int): Plex index (?)
            leafCount (int): Unknown.
            locations (list<str>): List of locations paths.
            originallyAvailableAt (datetime): Datetime show was released.
            rating (float): Show rating (7.9; 9.8; 8.1).
            studio (str): Studio that created show (Di Bonaventura Pictures; 21 Laps Entertainment).
            theme (str): Key to theme resource (/library/metadata/<ratingkey>/theme/<themeid>)
            viewedLeafCount (int): Unknown.
            year (int): Year the show was released.
            genres (List<:class:`~plexapi.media.Genre`>): List of genre objects.
            roles (List<:class:`~plexapi.media.Role`>): List of role objects.
            similar (List<:class:`~plexapi.media.Similar`>): List of Similar objects.
    """
    TAG = 'Directory'
    TYPE = 'show'
    METADATA_TYPE = 'episode'

    def __iter__(self):
        for season in self.seasons():
            yield season

    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        Video._loadData(self, data)
        # fix key if loaded from search
        self.key = self.key.replace('/children', '')
        self.art = data.attrib.get('art')
        self.banner = data.attrib.get('banner')
        self.childCount = utils.cast(int, data.attrib.get('childCount'))
        self.contentRating = data.attrib.get('contentRating')
        self.collections = self.findItems(data, media.Collection)
        self.duration = utils.cast(int, data.attrib.get('duration'))
        self.guid = data.attrib.get('guid')
        self.index = data.attrib.get('index')
        self.leafCount = utils.cast(int, data.attrib.get('leafCount'))
        self.locations = self.listAttrs(data, 'path', etag='Location')
        self.originallyAvailableAt = utils.toDatetime(
            data.attrib.get('originallyAvailableAt'), '%Y-%m-%d')
        self.rating = utils.cast(float, data.attrib.get('rating'))
        self.studio = data.attrib.get('studio')
        self.theme = data.attrib.get('theme')
        self.viewedLeafCount = utils.cast(int, data.attrib.get('viewedLeafCount'))
        self.year = utils.cast(int, data.attrib.get('year'))
        self.genres = self.findItems(data, media.Genre)
        self.roles = self.findItems(data, media.Role)
        self.labels = self.findItems(data, media.Label)
        self.similar = self.findItems(data, media.Similar)

    @property
    def actors(self):
        """ Alias to self.roles. """
        return self.roles

    @property
    def isWatched(self):
        """ Returns True if this show is fully watched. """
        return bool(self.viewedLeafCount == self.leafCount)

    def seasons(self, **kwargs):
        """ Returns a list of :class:`~plexapi.video.Season` objects. """
        key = '/library/metadata/%s/children?excludeAllLeaves=1' % self.ratingKey
        return self.fetchItems(key, **kwargs)

    def season(self, title=None):
        """ Returns the season with the specified title or number.

            Parameters:
                title (str or int): Title or Number of the season to return.
        """
        key = '/library/metadata/%s/children' % self.ratingKey
        if isinstance(title, int):
            return self.fetchItem(key, etag='Directory', index__iexact=str(title))
        return self.fetchItem(key, etag='Directory', title__iexact=title)

    def episodes(self, **kwargs):
        """ Returns a list of :class:`~plexapi.video.Episode` objects. """
        key = '/library/metadata/%s/allLeaves' % self.ratingKey
        return self.fetchItems(key, **kwargs)

    def episode(self, title=None, season=None, episode=None):
        """ Find a episode using a title or season and episode.

           Parameters:
                title (str): Title of the episode to return
                season (int): Season number (default:None; required if title not specified).
                episode (int): Episode number (default:None; required if title not specified).

           Raises:
                :class:`plexapi.exceptions.BadRequest`: If season and episode is missing.
                :class:`plexapi.exceptions.NotFound`: If the episode is missing.
        """
        if title:
            key = '/library/metadata/%s/allLeaves' % self.ratingKey
            return self.fetchItem(key, title__iexact=title)
        elif season is not None and episode:
            results = [i for i in self.episodes() if i.seasonNumber == season and i.index == episode]
            if results:
                return results[0]
            raise NotFound('Couldnt find %s S%s E%s' % (self.title, season, episode))
        raise BadRequest('Missing argument: title or season and episode are required')

    def watched(self):
        """ Returns list of watched :class:`~plexapi.video.Episode` objects. """
        return self.episodes(viewCount__gt=0)

    def unwatched(self):
        """ Returns list of unwatched :class:`~plexapi.video.Episode` objects. """
        return self.episodes(viewCount=0)

    def get(self, title=None, season=None, episode=None):
        """ Alias to :func:`~plexapi.video.Show.episode()`. """
        return self.episode(title, season, episode)

    def download(self, savepath=None, keep_original_name=False, **kwargs):
        """ Download video files to specified directory.

            Parameters:
                savepath (str): Defaults to current working dir.
                keep_original_name (bool): True to keep the original file name otherwise
                    a friendlier is generated.
                **kwargs: Additional options passed into :func:`~plexapi.base.PlexObject.getStreamURL()`.
        """
        filepaths = []
        for episode in self.episodes():
            filepaths += episode.download(savepath, keep_original_name, **kwargs)
        return filepaths


@utils.registerPlexObject
class Season(Video):
    """ Represents a single Show Season (including all episodes).

        Attributes:
            TAG (str): 'Directory'
            TYPE (str): 'season'
            leafCount (int): Number of episodes in season.
            index (int): Season number.
            parentKey (str): Key to this seasons :class:`~plexapi.video.Show`.
            parentRatingKey (int): Unique key for this seasons :class:`~plexapi.video.Show`.
            parentTitle (str): Title of this seasons :class:`~plexapi.video.Show`.
            viewedLeafCount (int): Number of watched episodes in season.
    """
    TAG = 'Directory'
    TYPE = 'season'
    METADATA_TYPE = 'episode'

    def __iter__(self):
        for episode in self.episodes():
            yield episode

    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        Video._loadData(self, data)
        # fix key if loaded from search
        self.key = self.key.replace('/children', '')
        self.leafCount = utils.cast(int, data.attrib.get('leafCount'))
        self.index = utils.cast(int, data.attrib.get('index'))
        self.parentKey = data.attrib.get('parentKey')
        self.parentRatingKey = utils.cast(int, data.attrib.get('parentRatingKey'))
        self.parentTitle = data.attrib.get('parentTitle')
        self.viewedLeafCount = utils.cast(int, data.attrib.get('viewedLeafCount'))

    def __repr__(self):
        return '<%s>' % ':'.join([p for p in [
            self.__class__.__name__,
            self.key.replace('/library/metadata/', '').replace('/children', ''),
            '%s-s%s' % (self.parentTitle.replace(' ', '-')[:20], self.seasonNumber),
        ] if p])

    @property
    def isWatched(self):
        """ Returns True if this season is fully watched. """
        return bool(self.viewedLeafCount == self.leafCount)

    @property
    def seasonNumber(self):
        """ Returns season number. """
        return self.index

    def episodes(self, **kwargs):
        """ Returns a list of :class:`~plexapi.video.Episode` objects. """
        key = '/library/metadata/%s/children' % self.ratingKey
        return self.fetchItems(key, **kwargs)

    def episode(self, title=None, episode=None):
        """ Returns the episode with the given title or number.

            Parameters:
                title (str): Title of the episode to return.
                episode (int): Episode number (default:None; required if title not specified).
        """
        if not title and not episode:
            raise BadRequest('Missing argument, you need to use title or episode.')
        key = '/library/metadata/%s/children' % self.ratingKey
        if title:
            return self.fetchItem(key, title=title)
        return self.fetchItem(key, parentIndex=self.index, index=episode)

    def get(self, title=None, episode=None):
        """ Alias to :func:`~plexapi.video.Season.episode()`. """
        return self.episode(title, episode)

    def show(self):
        """ Return this seasons :func:`~plexapi.video.Show`.. """
        return self.fetchItem(self.parentKey)

    def watched(self):
        """ Returns list of watched :class:`~plexapi.video.Episode` objects. """
        return self.episodes(watched=True)

    def unwatched(self):
        """ Returns list of unwatched :class:`~plexapi.video.Episode` objects. """
        return self.episodes(watched=False)

    def download(self, savepath=None, keep_original_name=False, **kwargs):
        """ Download video files to specified directory.

            Parameters:
                savepath (str): Defaults to current working dir.
                keep_original_name (bool): True to keep the original file name otherwise
                    a friendlier is generated.
                **kwargs: Additional options passed into :func:`~plexapi.base.PlexObject.getStreamURL()`.
        """
        filepaths = []
        for episode in self.episodes():
            filepaths += episode.download(savepath, keep_original_name, **kwargs)
        return filepaths

    def _defaultSyncTitle(self):
        """ Returns str, default title for a new syncItem. """
        return '%s - %s' % (self.parentTitle, self.title)


@utils.registerPlexObject
class Episode(Playable, Video):
    """ Represents a single Shows Episode.

        Attributes:
            TAG (str): 'Video'
            TYPE (str): 'episode'
            art (str): Key to episode artwork (/library/metadata/<ratingkey>/art/<artid>)
            chapterSource (str): Unknown (media).
            contentRating (str) Content rating (PG-13; NR; TV-G).
            duration (int): Duration of episode in milliseconds.
            grandparentArt (str): Key to this episodes :class:`~plexapi.video.Show` artwork.
            grandparentKey (str): Key to this episodes :class:`~plexapi.video.Show`.
            grandparentRatingKey (str): Unique key for this episodes :class:`~plexapi.video.Show`.
            grandparentTheme (str): Key to this episodes :class:`~plexapi.video.Show` theme.
            grandparentThumb (str): Key to this episodes :class:`~plexapi.video.Show` thumb.
            grandparentTitle (str): Title of this episodes :class:`~plexapi.video.Show`.
            guid (str): Plex GUID (com.plexapp.agents.imdb://tt4302938?lang=en).
            index (int): Episode number.
            originallyAvailableAt (datetime): Datetime episode was released.
            parentIndex (str): Season number of episode.
            parentKey (str): Key to this episodes :class:`~plexapi.video.Season`.
            parentRatingKey (int): Unique key for this episodes :class:`~plexapi.video.Season`.
            parentThumb (str): Key to this episodes thumbnail.
            parentTitle (str): Name of this episode's season
            title (str): Name of this Episode
            rating (float): Movie rating (7.9; 9.8; 8.1).
            viewOffset (int): View offset in milliseconds.
            year (int): Year episode was released.
            directors (List<:class:`~plexapi.media.Director`>): List of director objects.
            media (List<:class:`~plexapi.media.Media`>): List of media objects.
            writers (List<:class:`~plexapi.media.Writer`>): List of writers objects.
    """
    TAG = 'Video'
    TYPE = 'episode'
    METADATA_TYPE = 'episode'

    _include = ('?checkFiles=1&includeExtras=1&includeRelated=1'
                '&includeOnDeck=1&includeChapters=1&includePopularLeaves=1'
                '&includeConcerts=1&includePreferences=1')

    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        Video._loadData(self, data)
        Playable._loadData(self, data)
        self._details_key = self.key + self._include
        self._seasonNumber = None  # cached season number
        self.art = data.attrib.get('art')
        self.chapterSource = data.attrib.get('chapterSource')
        self.contentRating = data.attrib.get('contentRating')
        self.duration = utils.cast(int, data.attrib.get('duration'))
        self.grandparentArt = data.attrib.get('grandparentArt')
        self.grandparentKey = data.attrib.get('grandparentKey')
        self.grandparentRatingKey = utils.cast(int, data.attrib.get('grandparentRatingKey'))
        self.grandparentTheme = data.attrib.get('grandparentTheme')
        self.grandparentThumb = data.attrib.get('grandparentThumb')
        self.grandparentTitle = data.attrib.get('grandparentTitle')
        self.guid = data.attrib.get('guid')
        self.index = utils.cast(int, data.attrib.get('index'))
        self.originallyAvailableAt = utils.toDatetime(data.attrib.get('originallyAvailableAt'), '%Y-%m-%d')
        self.parentIndex = data.attrib.get('parentIndex')
        self.parentKey = data.attrib.get('parentKey')
        self.parentRatingKey = utils.cast(int, data.attrib.get('parentRatingKey'))
        self.parentThumb = data.attrib.get('parentThumb')
        self.parentTitle = data.attrib.get('parentTitle')
        self.title = data.attrib.get('title')
        self.rating = utils.cast(float, data.attrib.get('rating'))
        self.viewOffset = utils.cast(int, data.attrib.get('viewOffset', 0))
        self.year = utils.cast(int, data.attrib.get('year'))
        self.directors = self.findItems(data, media.Director)
        self.media = self.findItems(data, media.Media)
        self.writers = self.findItems(data, media.Writer)
        self.labels = self.findItems(data, media.Label)
        self.collections = self.findItems(data, media.Collection)
        self.chapters = self.findItems(data, media.Chapter)

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
            interface to get the location of the Movie/Show
        """
        return [part.file for part in self.iterParts() if part]

    @property
    def seasonNumber(self):
        """ Returns this episodes season number. """
        if self._seasonNumber is None:
            self._seasonNumber = self.parentIndex if self.parentIndex else self.season().seasonNumber
        return utils.cast(int, self._seasonNumber)

    @property
    def seasonEpisode(self):
        """ Returns the s00e00 string containing the season and episode. """
        return 's%se%s' % (str(self.seasonNumber).zfill(2), str(self.index).zfill(2))

    def season(self):
        """" Return this episodes :func:`~plexapi.video.Season`.. """
        return self.fetchItem(self.parentKey)

    def show(self):
        """" Return this episodes :func:`~plexapi.video.Show`.. """
        return self.fetchItem(self.grandparentKey)

    def _defaultSyncTitle(self):
        """ Returns str, default title for a new syncItem. """
        return '%s - %s - (%s) %s' % (self.grandparentTitle, self.parentTitle, self.seasonEpisode, self.title)
