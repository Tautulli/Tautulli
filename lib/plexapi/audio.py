# -*- coding: utf-8 -*-
from plexapi import media, utils
from plexapi.base import Playable, PlexPartialObject
from plexapi.compat import quote_plus


class Audio(PlexPartialObject):
    """ Base class for audio :class:`~plexapi.audio.Artist`, :class:`~plexapi.audio.Album`
        and :class:`~plexapi.audio.Track` objects.

        Attributes:
            addedAt (datetime): Datetime this item was added to the library.
            index (sting): Index Number (often the track number).
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

    METADATA_TYPE = 'track'

    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        self._data = data
        self.listType = 'audio'
        self.addedAt = utils.toDatetime(data.attrib.get('addedAt'))
        self.index = data.attrib.get('index')
        self.key = data.attrib.get('key')
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
        """ Returns the full URL for this audio item. Typically used for getting a specific track. """
        return self._server.url(part, includeToken=True) if part else None

    def _defaultSyncTitle(self):
        """ Returns str, default title for a new syncItem. """
        return self.title

    def sync(self, bitrate, client=None, clientId=None, limit=None, title=None):
        """ Add current audio (artist, album or track) as sync item for specified device.
            See :func:`plexapi.myplex.MyPlexAccount.sync()` for possible exceptions.

            Parameters:
                bitrate (int): maximum bitrate for synchronized music, better use one of MUSIC_BITRATE_* values from the
                               module :mod:`plexapi.sync`.
                client (:class:`plexapi.myplex.MyPlexDevice`): sync destination, see
                                                               :func:`plexapi.myplex.MyPlexAccount.sync`.
                clientId (str): sync destination, see :func:`plexapi.myplex.MyPlexAccount.sync`.
                limit (int): maximum count of items to sync, unlimited if `None`.
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
        sync_item.policy = Policy.create(limit)
        sync_item.mediaSettings = MediaSettings.createMusic(bitrate)

        return myplex.sync(sync_item, client=client, clientId=clientId)


@utils.registerPlexObject
class Artist(Audio):
    """ Represents a single audio artist.

        Attributes:
            TAG (str): 'Directory'
            TYPE (str): 'artist'
            art (str): Artist artwork (/library/metadata/<ratingkey>/art/<artid>)
            countries (list): List of :class:`~plexapi.media.Country` objects this artist respresents.
            genres (list): List of :class:`~plexapi.media.Genre` objects this artist respresents.
            guid (str): Unknown (unique ID; com.plexapp.agents.plexmusic://gracenote/artist/05517B8701668D28?lang=en)
            key (str): API URL (/library/metadata/<ratingkey>).
            location (str): Filepath this artist is found on disk.
            similar (list): List of :class:`~plexapi.media.Similar` artists.
    """
    TAG = 'Directory'
    TYPE = 'artist'

    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        Audio._loadData(self, data)
        self.art = data.attrib.get('art')
        self.guid = data.attrib.get('guid')
        self.key = self.key.replace('/children', '')  # FIX_BUG_50
        self.locations = self.listAttrs(data, 'path', etag='Location')
        self.countries = self.findItems(data, media.Country)
        self.genres = self.findItems(data, media.Genre)
        self.similar = self.findItems(data, media.Similar)
        self.collections = self.findItems(data, media.Collection)

    def __iter__(self):
        for album in self.albums():
            yield album

    def album(self, title):
        """ Returns the :class:`~plexapi.audio.Album` that matches the specified title.

            Parameters:
                title (str): Title of the album to return.
        """
        key = '%s/children' % self.key
        return self.fetchItem(key, title__iexact=title)

    def albums(self, **kwargs):
        """ Returns a list of :class:`~plexapi.audio.Album` objects by this artist. """
        key = '%s/children' % self.key
        return self.fetchItems(key, **kwargs)

    def track(self, title):
        """ Returns the :class:`~plexapi.audio.Track` that matches the specified title.

            Parameters:
                title (str): Title of the track to return.
        """
        key = '%s/allLeaves' % self.key
        return self.fetchItem(key, title__iexact=title)

    def tracks(self, **kwargs):
        """ Returns a list of :class:`~plexapi.audio.Track` objects by this artist. """
        key = '%s/allLeaves' % self.key
        return self.fetchItems(key, **kwargs)

    def get(self, title):
        """ Alias of :func:`~plexapi.audio.Artist.track`. """
        return self.track(title)

    def download(self, savepath=None, keep_original_name=False, **kwargs):
        """ Downloads all tracks for this artist to the specified location.

            Parameters:
                savepath (str): Title of the track to return.
                keep_original_name (bool): Set True to keep the original filename as stored in
                    the Plex server. False will create a new filename with the format
                    "<Atrist> - <Album> <Track>".
                kwargs (dict): If specified, a :func:`~plexapi.audio.Track.getStreamURL()` will
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
    """ Represents a single audio album.

        Attributes:
            TAG (str): 'Directory'
            TYPE (str): 'album'
            art (str): Album artwork (/library/metadata/<ratingkey>/art/<artid>)
            genres (list): List of :class:`~plexapi.media.Genre` objects this album respresents.
            key (str): API URL (/library/metadata/<ratingkey>).
            originallyAvailableAt (datetime): Datetime this album was released.
            parentKey (str): API URL of this artist.
            parentRatingKey (int): Unique key identifying artist.
            parentThumb (str): URL to artist thumbnail image.
            parentTitle (str): Name of the artist for this album.
            studio (str): Studio that released this album.
            year (int): Year this album was released.
    """
    TAG = 'Directory'
    TYPE = 'album'

    def __iter__(self):
        for track in self.tracks:
            yield track

    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        Audio._loadData(self, data)
        self.art = data.attrib.get('art')
        self.key = self.key.replace('/children', '')  # fixes bug #50
        self.originallyAvailableAt = utils.toDatetime(data.attrib.get('originallyAvailableAt'), '%Y-%m-%d')
        self.parentKey = data.attrib.get('parentKey')
        self.parentRatingKey = data.attrib.get('parentRatingKey')
        self.parentThumb = data.attrib.get('parentThumb')
        self.parentTitle = data.attrib.get('parentTitle')
        self.studio = data.attrib.get('studio')
        self.year = utils.cast(int, data.attrib.get('year'))
        self.genres = self.findItems(data, media.Genre)
        self.collections = self.findItems(data, media.Collection)
        self.labels = self.findItems(data, media.Label)

    def track(self, title):
        """ Returns the :class:`~plexapi.audio.Track` that matches the specified title.

            Parameters:
                title (str): Title of the track to return.
        """
        key = '%s/children' % self.key
        return self.fetchItem(key, title__iexact=title)

    def tracks(self, **kwargs):
        """ Returns a list of :class:`~plexapi.audio.Track` objects in this album. """
        key = '%s/children' % self.key
        return self.fetchItems(key, **kwargs)

    def get(self, title):
        """ Alias of :func:`~plexapi.audio.Album.track`. """
        return self.track(title)

    def artist(self):
        """ Return :func:`~plexapi.audio.Artist` of this album. """
        return self.fetchItem(self.parentKey)

    def download(self, savepath=None, keep_original_name=False, **kwargs):
        """ Downloads all tracks for this artist to the specified location.

            Parameters:
                savepath (str): Title of the track to return.
                keep_original_name (bool): Set True to keep the original filename as stored in
                    the Plex server. False will create a new filename with the format
                    "<Atrist> - <Album> <Track>".
                kwargs (dict): If specified, a :func:`~plexapi.audio.Track.getStreamURL()` will
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
    """ Represents a single audio track.

        Attributes:
            TAG (str): 'Directory'
            TYPE (str): 'track'
            art (str): Track artwork (/library/metadata/<ratingkey>/art/<artid>)
            chapterSource (TYPE): Unknown
            duration (int): Length of this album in seconds.
            grandparentArt (str): Artist artowrk.
            grandparentKey (str): Artist API URL.
            grandparentRatingKey (str): Unique key identifying artist.
            grandparentThumb (str): URL to artist thumbnail image.
            grandparentTitle (str): Name of the artist for this track.
            guid (str): Unknown (unique ID).
            media (list): List of :class:`~plexapi.media.Media` objects for this track.
            moods (list): List of :class:`~plexapi.media.Mood` objects for this track.
            originalTitle (str): Original track title (if translated).
            parentIndex (int): Album index.
            parentKey (str): Album API URL.
            parentRatingKey (int): Unique key identifying album.
            parentThumb (str): URL to album thumbnail image.
            parentTitle (str): Name of the album for this track.
            primaryExtraKey (str): Unknown
            ratingCount (int): Unknown
            userRating (float): Rating of this track (0.0 - 10.0) equaling (0 stars - 5 stars)
            viewOffset (int): Unknown
            year (int): Year this track was released.
            sessionKey (int): Session Key (active sessions only).
            usernames (str): Username of person playing this track (active sessions only).
            player (str): :class:`~plexapi.client.PlexClient` for playing track (active sessions only).
            transcodeSessions (None): :class:`~plexapi.media.TranscodeSession` for playing
                track (active sessions only).
    """
    TAG = 'Track'
    TYPE = 'track'

    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        Audio._loadData(self, data)
        Playable._loadData(self, data)
        self.art = data.attrib.get('art')
        self.chapterSource = data.attrib.get('chapterSource')
        self.duration = utils.cast(int, data.attrib.get('duration'))
        self.grandparentArt = data.attrib.get('grandparentArt')
        self.grandparentKey = data.attrib.get('grandparentKey')
        self.grandparentRatingKey = data.attrib.get('grandparentRatingKey')
        self.grandparentThumb = data.attrib.get('grandparentThumb')
        self.grandparentTitle = data.attrib.get('grandparentTitle')
        self.guid = data.attrib.get('guid')
        self.originalTitle = data.attrib.get('originalTitle')
        self.parentIndex = data.attrib.get('parentIndex')
        self.parentKey = data.attrib.get('parentKey')
        self.parentRatingKey = data.attrib.get('parentRatingKey')
        self.parentThumb = data.attrib.get('parentThumb')
        self.parentTitle = data.attrib.get('parentTitle')
        self.primaryExtraKey = data.attrib.get('primaryExtraKey')
        self.ratingCount = utils.cast(int, data.attrib.get('ratingCount'))
        self.userRating = utils.cast(float, data.attrib.get('userRating', 0))
        self.viewOffset = utils.cast(int, data.attrib.get('viewOffset', 0))
        self.year = utils.cast(int, data.attrib.get('year'))
        self.media = self.findItems(data, media.Media)
        self.moods = self.findItems(data, media.Mood)

    def _prettyfilename(self):
        """ Returns a filename for use in download. """
        return '%s - %s %s' % (self.grandparentTitle, self.parentTitle, self.title)

    def album(self):
        """ Return this track's :class:`~plexapi.audio.Album`. """
        return self.fetchItem(self.parentKey)

    def artist(self):
        """ Return this track's :class:`~plexapi.audio.Artist`. """
        return self.fetchItem(self.grandparentKey)

    def _defaultSyncTitle(self):
        """ Returns str, default title for a new syncItem. """
        return '%s - %s - %s' % (self.grandparentTitle, self.parentTitle, self.title)
