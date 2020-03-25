# -*- coding: utf-8 -*-
from plexapi import log, utils
from plexapi.base import PlexObject
from plexapi.exceptions import BadRequest
from plexapi.utils import cast


@utils.registerPlexObject
class Media(PlexObject):
    """ Container object for all MediaPart objects. Provides useful data about the
        video this media belong to such as video framerate, resolution, etc.

        Attributes:
            TAG (str): 'Media'
            server (:class:`~plexapi.server.PlexServer`): PlexServer object this is from.
            initpath (str): Relative path requested when retrieving specified data.
            video (str): Video this media belongs to.
            aspectRatio (float): Aspect ratio of the video (ex: 2.35).
            audioChannels (int): Number of audio channels for this video (ex: 6).
            audioCodec (str): Audio codec used within the video (ex: ac3).
            bitrate (int): Bitrate of the video (ex: 1624)
            container (str): Container this video is in (ex: avi).
            duration (int): Length of the video in milliseconds (ex: 6990483).
            height (int): Height of the video in pixels (ex: 256).
            id (int): Plex ID of this media item (ex: 46184).
            has64bitOffsets (bool): True if video has 64 bit offsets (?).
            optimizedForStreaming (bool): True if video is optimized for streaming.
            target (str): Media version target name.
            title (str): Media version title.
            videoCodec (str): Video codec used within the video (ex: ac3).
            videoFrameRate (str): Video frame rate (ex: 24p).
            videoResolution (str): Video resolution (ex: sd).
            videoProfile (str): Video profile (ex: high).
            width (int): Width of the video in pixels (ex: 608).
            parts (list<:class:`~plexapi.media.MediaPart`>): List of MediaParts in this video.
    """
    TAG = 'Media'

    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        self._data = data
        self.aspectRatio = cast(float, data.attrib.get('aspectRatio'))
        self.audioChannels = cast(int, data.attrib.get('audioChannels'))
        self.audioCodec = data.attrib.get('audioCodec')
        self.bitrate = cast(int, data.attrib.get('bitrate'))
        self.container = data.attrib.get('container')
        self.duration = cast(int, data.attrib.get('duration'))
        self.height = cast(int, data.attrib.get('height'))
        self.id = cast(int, data.attrib.get('id'))
        self.has64bitOffsets = cast(bool, data.attrib.get('has64bitOffsets'))
        self.optimizedForStreaming = cast(bool, data.attrib.get('optimizedForStreaming'))
        self.target = data.attrib.get('target')
        self.title = data.attrib.get('title')
        self.videoCodec = data.attrib.get('videoCodec')
        self.videoFrameRate = data.attrib.get('videoFrameRate')
        self.videoProfile = data.attrib.get('videoProfile')
        self.videoResolution = data.attrib.get('videoResolution')
        self.width = cast(int, data.attrib.get('width'))
        self.parts = self.findItems(data, MediaPart)

    def delete(self):
        part = self._initpath + '/media/%s' % self.id
        try:
            return self._server.query(part, method=self._server._session.delete)
        except BadRequest:
            log.error("Failed to delete %s. This could be because you havn't allowed "
                      "items to be deleted" % part)
            raise


@utils.registerPlexObject
class MediaPart(PlexObject):
    """ Represents a single media part (often a single file) for the media this belongs to.

        Attributes:
            TAG (str): 'Part'
            server (:class:`~plexapi.server.PlexServer`): PlexServer object this is from.
            initpath (str): Relative path requested when retrieving specified data.
            media (:class:`~plexapi.media.Media`): Media object this part belongs to.
            container (str): Container type of this media part (ex: avi).
            duration (int): Length of this media part in milliseconds.
            file (str): Path to this file on disk (ex: /media/Movies/Cars.(2006)/Cars.cd2.avi)
            id (int): Unique ID of this media part.
            indexes (str, None): None or SD.
            key (str): Key used to access this media part (ex: /library/parts/46618/1389985872/file.avi).
            size (int): Size of this file in bytes (ex: 733884416).
            streams (list<:class:`~plexapi.media.MediaPartStream`>): List of streams in this media part.
            exists (bool): Determine if file exists
            accessible (bool): Determine if file is accessible
    """
    TAG = 'Part'

    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        self._data = data
        self.container = data.attrib.get('container')
        self.duration = cast(int, data.attrib.get('duration'))
        self.file = data.attrib.get('file')
        self.id = cast(int, data.attrib.get('id'))
        self.indexes = data.attrib.get('indexes')
        self.key = data.attrib.get('key')
        self.size = cast(int, data.attrib.get('size'))
        self.decision = data.attrib.get('decision')
        self.optimizedForStreaming = cast(bool, data.attrib.get('optimizedForStreaming'))
        self.syncItemId = cast(int, data.attrib.get('syncItemId'))
        self.syncState = data.attrib.get('syncState')
        self.videoProfile = data.attrib.get('videoProfile')
        self.streams = self._buildStreams(data)
        self.exists = cast(bool, data.attrib.get('exists'))
        self.accessible = cast(bool, data.attrib.get('accessible'))

    def _buildStreams(self, data):
        streams = []
        for elem in data:
            for cls in (VideoStream, AudioStream, SubtitleStream):
                if elem.attrib.get('streamType') == str(cls.STREAMTYPE):
                    streams.append(cls(self._server, elem, self._initpath))
        return streams

    def videoStreams(self):
        """ Returns a list of :class:`~plexapi.media.VideoStream` objects in this MediaPart. """
        return [stream for stream in self.streams if stream.streamType == VideoStream.STREAMTYPE]

    def audioStreams(self):
        """ Returns a list of :class:`~plexapi.media.AudioStream` objects in this MediaPart. """
        return [stream for stream in self.streams if stream.streamType == AudioStream.STREAMTYPE]

    def subtitleStreams(self):
        """ Returns a list of :class:`~plexapi.media.SubtitleStream` objects in this MediaPart. """
        return [stream for stream in self.streams if stream.streamType == SubtitleStream.STREAMTYPE]

    def setDefaultAudioStream(self, stream):
        """ Set the default :class:`~plexapi.media.AudioStream` for this MediaPart.

            Parameters:
                stream (:class:`~plexapi.media.AudioStream`): AudioStream to set as default
        """
        if isinstance(stream, AudioStream):
            key = "/library/parts/%d?audioStreamID=%d&allParts=1" % (self.id, stream.id)
        else:
            key = "/library/parts/%d?audioStreamID=%d&allParts=1" % (self.id, stream)
        self._server.query(key, method=self._server._session.put)

    def setDefaultSubtitleStream(self, stream):
        """ Set the default :class:`~plexapi.media.SubtitleStream` for this MediaPart.
            
            Parameters:
                stream (:class:`~plexapi.media.SubtitleStream`): SubtitleStream to set as default.
        """
        if isinstance(stream, SubtitleStream):
            key = "/library/parts/%d?subtitleStreamID=%d&allParts=1" % (self.id, stream.id)
        else:
            key = "/library/parts/%d?subtitleStreamID=%d&allParts=1" % (self.id, stream)
        self._server.query(key, method=self._server._session.put)

    def resetDefaultSubtitleStream(self):
        """ Set default subtitle of this MediaPart to 'none'. """
        key = "/library/parts/%d?subtitleStreamID=0&allParts=1" % (self.id)
        self._server.query(key, method=self._server._session.put)


class MediaPartStream(PlexObject):
    """ Base class for media streams. These consist of video, audio and subtitles.

        Attributes:
            server (:class:`~plexapi.server.PlexServer`): PlexServer object this is from.
            initpath (str): Relative path requested when retrieving specified data.
            part (:class:`~plexapi.media.MediaPart`): Media part this stream belongs to.
            codec (str): Codec of this stream (ex: srt, ac3, mpeg4).
            codecID (str): Codec ID (ex: XVID).
            id (int): Unique stream ID on this server.
            index (int): Unknown
            language (str): Stream language (ex: English, ไทย).
            languageCode (str): Ascii code for language (ex: eng, tha).
            selected (bool): True if this stream is selected.
            streamType (int): Stream type (1=:class:`~plexapi.media.VideoStream`,
                2=:class:`~plexapi.media.AudioStream`, 3=:class:`~plexapi.media.SubtitleStream`).
            type (int): Alias for streamType.
    """

    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        self._data = data
        self.codec = data.attrib.get('codec')
        self.codecID = data.attrib.get('codecID')
        self.id = cast(int, data.attrib.get('id'))
        self.index = cast(int, data.attrib.get('index', '-1'))
        self.language = data.attrib.get('language')
        self.languageCode = data.attrib.get('languageCode')
        self.selected = cast(bool, data.attrib.get('selected', '0'))
        self.streamType = cast(int, data.attrib.get('streamType'))
        self.type = cast(int, data.attrib.get('streamType'))

    @staticmethod
    def parse(server, data, initpath):  # pragma: no cover seems to be dead code.
        """ Factory method returns a new MediaPartStream from xml data. """
        STREAMCLS = {1: VideoStream, 2: AudioStream, 3: SubtitleStream}
        stype = cast(int, data.attrib.get('streamType'))
        cls = STREAMCLS.get(stype, MediaPartStream)
        return cls(server, data, initpath)


@utils.registerPlexObject
class VideoStream(MediaPartStream):
    """ Respresents a video stream within a :class:`~plexapi.media.MediaPart`.

        Attributes:
            TAG (str): 'Stream'
            STREAMTYPE (int): 1
            bitDepth (int): Bit depth (ex: 8).
            bitrate (int): Bitrate (ex: 1169)
            cabac (int): Unknown
            chromaSubsampling (str): Chroma Subsampling (ex: 4:2:0).
            colorSpace (str): Unknown
            duration (int): Duration of video stream in milliseconds.
            frameRate (float): Frame rate (ex: 23.976)
            frameRateMode (str): Unknown
            hasScallingMatrix (bool): True if video stream has a scaling matrix.
            height (int): Height of video stream.
            level (int): Videl stream level (?).
            profile (str): Video stream profile (ex: asp).
            refFrames (int): Unknown
            scanType (str): Video stream scan type (ex: progressive).
            title (str): Title of this video stream.
            width (int): Width of video stream.
    """
    TAG = 'Stream'
    STREAMTYPE = 1

    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        super(VideoStream, self)._loadData(data)
        self.bitDepth = cast(int, data.attrib.get('bitDepth'))
        self.bitrate = cast(int, data.attrib.get('bitrate'))
        self.cabac = cast(int, data.attrib.get('cabac'))
        self.chromaSubsampling = data.attrib.get('chromaSubsampling')
        self.colorSpace = data.attrib.get('colorSpace')
        self.duration = cast(int, data.attrib.get('duration'))
        self.frameRate = cast(float, data.attrib.get('frameRate'))
        self.frameRateMode = data.attrib.get('frameRateMode')
        self.hasScallingMatrix = cast(bool, data.attrib.get('hasScallingMatrix'))
        self.height = cast(int, data.attrib.get('height'))
        self.level = cast(int, data.attrib.get('level'))
        self.profile = data.attrib.get('profile')
        self.refFrames = cast(int, data.attrib.get('refFrames'))
        self.scanType = data.attrib.get('scanType')
        self.title = data.attrib.get('title')
        self.width = cast(int, data.attrib.get('width'))


@utils.registerPlexObject
class AudioStream(MediaPartStream):
    """ Respresents a audio stream within a :class:`~plexapi.media.MediaPart`.

        Attributes:
            TAG (str): 'Stream'
            STREAMTYPE (int): 2
            audioChannelLayout (str): Audio channel layout (ex: 5.1(side)).
            bitDepth (int): Bit depth (ex: 16).
            bitrate (int): Audio bitrate (ex: 448).
            bitrateMode (str): Bitrate mode (ex: cbr).
            channels (int): number of channels in this stream (ex: 6).
            dialogNorm (int): Unknown (ex: -27).
            duration (int): Duration of audio stream in milliseconds.
            samplingRate (int): Sampling rate (ex: xxx)
            title (str): Title of this audio stream.
    """
    TAG = 'Stream'
    STREAMTYPE = 2

    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        super(AudioStream, self)._loadData(data)
        self.audioChannelLayout = data.attrib.get('audioChannelLayout')
        self.bitDepth = cast(int, data.attrib.get('bitDepth'))
        self.bitrate = cast(int, data.attrib.get('bitrate'))
        self.bitrateMode = data.attrib.get('bitrateMode')
        self.channels = cast(int, data.attrib.get('channels'))
        self.dialogNorm = cast(int, data.attrib.get('dialogNorm'))
        self.duration = cast(int, data.attrib.get('duration'))
        self.samplingRate = cast(int, data.attrib.get('samplingRate'))
        self.title = data.attrib.get('title')


@utils.registerPlexObject
class SubtitleStream(MediaPartStream):
    """ Respresents a audio stream within a :class:`~plexapi.media.MediaPart`.

        Attributes:
            TAG (str): 'Stream'
            STREAMTYPE (int): 3
            forced (bool): True if this is a forced subtitle
            format (str): Subtitle format (ex: srt).
            key (str): Key of this subtitle stream (ex: /library/streams/212284).
            title (str): Title of this subtitle stream.
    """
    TAG = 'Stream'
    STREAMTYPE = 3

    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        super(SubtitleStream, self)._loadData(data)
        self.forced = cast(bool, data.attrib.get('forced', '0'))
        self.format = data.attrib.get('format')
        self.key = data.attrib.get('key')
        self.title = data.attrib.get('title')


@utils.registerPlexObject
class Session(PlexObject):
    """ Represents a current session. """
    TAG = 'Session'

    def _loadData(self, data):
        self.id = data.attrib.get('id')
        self.bandwidth = utils.cast(int, data.attrib.get('bandwidth'))
        self.location = data.attrib.get('location')


@utils.registerPlexObject
class TranscodeSession(PlexObject):
    """ Represents a current transcode session.

        Attributes:
            TAG (str): 'TranscodeSession'
            TODO: Document this.
    """
    TAG = 'TranscodeSession'

    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        self._data = data
        self.audioChannels = cast(int, data.attrib.get('audioChannels'))
        self.audioCodec = data.attrib.get('audioCodec')
        self.audioDecision = data.attrib.get('audioDecision')
        self.container = data.attrib.get('container')
        self.context = data.attrib.get('context')
        self.duration = cast(int, data.attrib.get('duration'))
        self.height = cast(int, data.attrib.get('height'))
        self.key = data.attrib.get('key')
        self.progress = cast(float, data.attrib.get('progress'))
        self.protocol = data.attrib.get('protocol')
        self.remaining = cast(int, data.attrib.get('remaining'))
        self.speed = cast(int, data.attrib.get('speed'))
        self.throttled = cast(int, data.attrib.get('throttled'))
        self.sourceVideoCodec = data.attrib.get('sourceVideoCodec')
        self.videoCodec = data.attrib.get('videoCodec')
        self.videoDecision = data.attrib.get('videoDecision')
        self.width = cast(int, data.attrib.get('width'))


class MediaTag(PlexObject):
    """ Base class for media tags used for filtering and searching your library
        items or navigating the metadata of media items in your library. Tags are
        the construct used for things such as Country, Director, Genre, etc.

        Attributes:
            server (:class:`~plexapi.server.PlexServer`): Server this client is connected to.
            id (id): Tag ID (This seems meaningless except to use it as a unique id).
            role (str): Unknown
            tag (str): Name of the tag. This will be Animation, SciFi etc for Genres. The name of
                person for Directors and Roles (ex: Animation, Stephen Graham, etc).
            <Hub_Search_Attributes>: Attributes only applicable in search results from
                PlexServer :func:`~plexapi.server.PlexServer.search()`. They provide details of which
                library section the tag was found as well as the url to dig deeper into the results.

                * key (str): API URL to dig deeper into this tag (ex: /library/sections/1/all?actor=9081).
                * librarySectionID (int): Section ID this tag was generated from.
                * librarySectionTitle (str): Library section title this tag was found.
                * librarySectionType (str): Media type of the library section this tag was found.
                * tagType (int): Tag type ID.
                * thumb (str): URL to thumbnail image.
    """

    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        self._data = data
        self.id = cast(int, data.attrib.get('id'))
        self.role = data.attrib.get('role')
        self.tag = data.attrib.get('tag')
        # additional attributes only from hub search
        self.key = data.attrib.get('key')
        self.librarySectionID = cast(int, data.attrib.get('librarySectionID'))
        self.librarySectionTitle = data.attrib.get('librarySectionTitle')
        self.librarySectionType = data.attrib.get('librarySectionType')
        self.tagType = cast(int, data.attrib.get('tagType'))
        self.thumb = data.attrib.get('thumb')

    def items(self, *args, **kwargs):
        """ Return the list of items within this tag. This function is only applicable
            in search results from PlexServer :func:`~plexapi.server.PlexServer.search()`.
        """
        if not self.key:
            raise BadRequest('Key is not defined for this tag: %s' % self.tag)
        return self.fetchItems(self.key)


@utils.registerPlexObject
class Collection(MediaTag):
    """ Represents a single Collection media tag.

        Attributes:
            TAG (str): 'Collection'
            FILTER (str): 'collection'
    """
    TAG = 'Collection'
    FILTER = 'collection'


@utils.registerPlexObject
class Label(MediaTag):
    """ Represents a single label media tag.

        Attributes:
            TAG (str): 'label'
            FILTER (str): 'label'
    """
    TAG = 'Label'
    FILTER = 'label'


@utils.registerPlexObject
class Country(MediaTag):
    """ Represents a single Country media tag.

        Attributes:
            TAG (str): 'Country'
            FILTER (str): 'country'
    """
    TAG = 'Country'
    FILTER = 'country'


@utils.registerPlexObject
class Director(MediaTag):
    """ Represents a single Director media tag.

        Attributes:
            TAG (str): 'Director'
            FILTER (str): 'director'
    """
    TAG = 'Director'
    FILTER = 'director'


@utils.registerPlexObject
class Genre(MediaTag):
    """ Represents a single Genre media tag.

        Attributes:
            TAG (str): 'Genre'
            FILTER (str): 'genre'
    """
    TAG = 'Genre'
    FILTER = 'genre'


@utils.registerPlexObject
class Mood(MediaTag):
    """ Represents a single Mood media tag.

        Attributes:
            TAG (str): 'Mood'
            FILTER (str): 'mood'
    """
    TAG = 'Mood'
    FILTER = 'mood'


@utils.registerPlexObject
class Poster(PlexObject):
    """ Represents a Poster.

        Attributes:
            TAG (str): 'Photo'
    """
    TAG = 'Photo'

    def _loadData(self, data):
        self._data = data
        self.key = data.attrib.get('key')
        self.ratingKey = data.attrib.get('ratingKey')
        self.selected = data.attrib.get('selected')
        self.thumb = data.attrib.get('thumb')


@utils.registerPlexObject
class Producer(MediaTag):
    """ Represents a single Producer media tag.

        Attributes:
            TAG (str): 'Producer'
            FILTER (str): 'producer'
    """
    TAG = 'Producer'
    FILTER = 'producer'


@utils.registerPlexObject
class Role(MediaTag):
    """ Represents a single Role (actor/actress) media tag.

        Attributes:
            TAG (str): 'Role'
            FILTER (str): 'role'
    """
    TAG = 'Role'
    FILTER = 'role'


@utils.registerPlexObject
class Similar(MediaTag):
    """ Represents a single Similar media tag.

        Attributes:
            TAG (str): 'Similar'
            FILTER (str): 'similar'
    """
    TAG = 'Similar'
    FILTER = 'similar'


@utils.registerPlexObject
class Writer(MediaTag):
    """ Represents a single Writer media tag.

        Attributes:
            TAG (str): 'Writer'
            FILTER (str): 'writer'
    """
    TAG = 'Writer'
    FILTER = 'writer'


@utils.registerPlexObject
class Chapter(PlexObject):
    """ Represents a single Writer media tag.

        Attributes:
            TAG (str): 'Chapter'
    """
    TAG = 'Chapter'

    def _loadData(self, data):
        self._data = data
        self.id = cast(int, data.attrib.get('id', 0))
        self.filter = data.attrib.get('filter')  # I couldn't filter on it anyways
        self.tag = data.attrib.get('tag')
        self.title = self.tag
        self.index = cast(int, data.attrib.get('index'))
        self.start = cast(int, data.attrib.get('startTimeOffset'))
        self.end = cast(int, data.attrib.get('endTimeOffset'))


@utils.registerPlexObject
class Field(PlexObject):
    """ Represents a single Field.

        Attributes:
            TAG (str): 'Field'
    """
    TAG = 'Field'

    def _loadData(self, data):
        self._data = data
        self.name = data.attrib.get('name')
        self.locked = cast(bool, data.attrib.get('locked'))
