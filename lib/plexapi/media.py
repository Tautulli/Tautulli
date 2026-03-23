from pathlib import Path
from urllib.parse import quote_plus
from xml.etree import ElementTree

from plexapi import log, settings, utils
from plexapi.base import PlexObject, cached_data_property
from plexapi.exceptions import BadRequest


@utils.registerPlexObject
class Media(PlexObject):
    """ Container object for all MediaPart objects. Provides useful data about the
        video or audio this media belong to such as video framerate, resolution, etc.

        Attributes:
            TAG (str): 'Media'
            aspectRatio (float): The aspect ratio of the media (ex: 2.35).
            audioChannels (int): The number of audio channels of the media (ex: 6).
            audioCodec (str): The audio codec of the media (ex: ac3).
            audioProfile (str): The audio profile of the media (ex: dts).
            bitrate (int): The bitrate of the media (ex: 1624).
            container (str): The container of the media (ex: avi).
            duration (int): The duration of the media in milliseconds (ex: 6990483).
            height (int): The height of the media in pixels (ex: 256).
            id (int): The unique ID for this media on the server.
            has64bitOffsets (bool): True if video has 64 bit offsets.
            hasVoiceActivity (bool): True if video has voice activity analyzed.
            optimizedForStreaming (bool): True if video is optimized for streaming.
            parts (List<:class:`~plexapi.media.MediaPart`>): List of media part objects.
            proxyType (int): Equals 42 for optimized versions.
            target (str): The media version target name.
            title (str): The title of the media.
            videoCodec (str): The video codec of the media (ex: ac3).
            videoFrameRate (str): The video frame rate of the media (ex: 24p).
            videoProfile (str): The video profile of the media (ex: high).
            videoResolution (str): The video resolution of the media (ex: sd).
            width (int): The width of the video in pixels (ex: 608).

            Photo_only_attributes: The following attributes are only available for photos.

                * aperture (str): The aperture used to take the photo.
                * exposure (str): The exposure used to take the photo.
                * iso (int): The iso used to take the photo.
                * lens (str): The lens used to take the photo.
                * make (str): The make of the camera used to take the photo.
                * model (str): The model of the camera used to take the photo.
    """
    TAG = 'Media'

    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        self.aspectRatio = utils.cast(float, data.attrib.get('aspectRatio'))
        self.audioChannels = utils.cast(int, data.attrib.get('audioChannels'))
        self.audioCodec = data.attrib.get('audioCodec')
        self.audioProfile = data.attrib.get('audioProfile')
        self.bitrate = utils.cast(int, data.attrib.get('bitrate'))
        self.container = data.attrib.get('container')
        self.duration = utils.cast(int, data.attrib.get('duration'))
        self.height = utils.cast(int, data.attrib.get('height'))
        self.id = utils.cast(int, data.attrib.get('id'))
        self.has64bitOffsets = utils.cast(bool, data.attrib.get('has64bitOffsets'))
        self.hasVoiceActivity = utils.cast(bool, data.attrib.get('hasVoiceActivity', '0'))
        self.optimizedForStreaming = utils.cast(bool, data.attrib.get('optimizedForStreaming'))
        self.proxyType = utils.cast(int, data.attrib.get('proxyType'))
        self.selected = utils.cast(bool, data.attrib.get('selected'))
        self.target = data.attrib.get('target')
        self.title = data.attrib.get('title')
        self.videoCodec = data.attrib.get('videoCodec')
        self.videoFrameRate = data.attrib.get('videoFrameRate')
        self.videoProfile = data.attrib.get('videoProfile')
        self.videoResolution = data.attrib.get('videoResolution')
        self.width = utils.cast(int, data.attrib.get('width'))
        self.uuid = data.attrib.get('uuid')

        # Photo only attributes
        self.aperture = data.attrib.get('aperture')
        self.exposure = data.attrib.get('exposure')
        self.iso = utils.cast(int, data.attrib.get('iso'))
        self.lens = data.attrib.get('lens')
        self.make = data.attrib.get('make')
        self.model = data.attrib.get('model')

        parent = self._parent()
        self._parentKey = parent.key

    @cached_data_property
    def parts(self):
        return self.findItems(self._data, MediaPart)

    @property
    def isOptimizedVersion(self):
        """ Returns True if the media is a Plex optimized version. """
        return self.proxyType == utils.SEARCHTYPES['optimizedVersion']

    def delete(self):
        part = f'{self._parentKey}/media/{self.id}'
        try:
            return self._server.query(part, method=self._server._session.delete)
        except BadRequest:
            log.error("Failed to delete %s. This could be because you haven't allowed items to be deleted", part)
            raise


@utils.registerPlexObject
class MediaPart(PlexObject):
    """ Represents a single media part (often a single file) for the media this belongs to.

        Attributes:
            TAG (str): 'Part'
            accessible (bool): True if the file is accessible.
                Requires reloading the media with ``checkFiles=True``.
                Refer to :func:`~plexapi.base.PlexObject.reload`.
            audioProfile (str): The audio profile of the file.
            container (str): The container type of the file (ex: avi).
            decision (str): Unknown.
            deepAnalysisVersion (int): The Plex deep analysis version for the file.
            duration (int): The duration of the file in milliseconds.
            exists (bool): True if the file exists.
                Requires reloading the media with ``checkFiles=True``.
                Refer to :func:`~plexapi.base.PlexObject.reload`.
            file (str): The path to this file on disk (ex: /media/Movies/Cars (2006)/Cars (2006).mkv)
            has64bitOffsets (bool): True if the file has 64 bit offsets.
            hasThumbnail (bool): True if the file (track) has an embedded thumbnail.
            id (int): The unique ID for this media part on the server.
            indexes (str, None): sd if the file has generated preview (BIF) thumbnails.
            key (str): API URL (ex: /library/parts/46618/1389985872/file.mkv).
            optimizedForStreaming (bool): True if the file is optimized for streaming.
            packetLength (int): The packet length of the file.
            requiredBandwidths (str): The required bandwidths to stream the file.
            selected (bool): True if this media part is selected.
            size (int): The size of the file in bytes (ex: 733884416).
            streams (List<:class:`~plexapi.media.MediaPartStream`>): List of stream objects.
            syncItemId (int): The unique ID for this media part if it is synced.
            syncState (str): The sync state for this media part.
            videoProfile (str): The video profile of the file.
    """
    TAG = 'Part'

    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        self.accessible = utils.cast(bool, data.attrib.get('accessible'))
        self.audioProfile = data.attrib.get('audioProfile')
        self.container = data.attrib.get('container')
        self.decision = data.attrib.get('decision')
        self.deepAnalysisVersion = utils.cast(int, data.attrib.get('deepAnalysisVersion'))
        self.duration = utils.cast(int, data.attrib.get('duration'))
        self.exists = utils.cast(bool, data.attrib.get('exists'))
        self.file = data.attrib.get('file')
        self.has64bitOffsets = utils.cast(bool, data.attrib.get('has64bitOffsets'))
        self.hasThumbnail = utils.cast(bool, data.attrib.get('hasThumbnail'))
        self.id = utils.cast(int, data.attrib.get('id'))
        self.indexes = data.attrib.get('indexes')
        self.key = data.attrib.get('key')
        self.optimizedForStreaming = utils.cast(bool, data.attrib.get('optimizedForStreaming'))
        self.packetLength = utils.cast(int, data.attrib.get('packetLength'))
        self.protocol = data.attrib.get('protocol')
        self.requiredBandwidths = data.attrib.get('requiredBandwidths')
        self.selected = utils.cast(bool, data.attrib.get('selected'))
        self.size = utils.cast(int, data.attrib.get('size'))
        self.streams = self._buildStreams(data)
        self.syncItemId = utils.cast(int, data.attrib.get('syncItemId'))
        self.syncState = data.attrib.get('syncState')
        self.videoProfile = data.attrib.get('videoProfile')

    def _buildStreams(self, data):
        """ Returns a list of :class:`~plexapi.media.MediaPartStream` objects in this MediaPart. """
        return self.findItems(data)

    @property
    def hasPreviewThumbnails(self):
        """ Returns True if the media part has generated preview (BIF) thumbnails. """
        return self.indexes == 'sd'

    def videoStreams(self):
        """ Returns a list of :class:`~plexapi.media.VideoStream` objects in this MediaPart. """
        return [stream for stream in self.streams if isinstance(stream, VideoStream)]

    def audioStreams(self):
        """ Returns a list of :class:`~plexapi.media.AudioStream` objects in this MediaPart. """
        return [stream for stream in self.streams if isinstance(stream, AudioStream)]

    def subtitleStreams(self):
        """ Returns a list of :class:`~plexapi.media.SubtitleStream` objects in this MediaPart. """
        return [stream for stream in self.streams if isinstance(stream, SubtitleStream)]

    def lyricStreams(self):
        """ Returns a list of :class:`~plexapi.media.LyricStream` objects in this MediaPart. """
        return [stream for stream in self.streams if isinstance(stream, LyricStream)]

    def setSelectedAudioStream(self, stream):
        """ Set the selected :class:`~plexapi.media.AudioStream` for this MediaPart.

            Parameters:
                stream (:class:`~plexapi.media.AudioStream`): Audio stream to set as selected
        """
        key = f'/library/parts/{self.id}'
        params = {'allParts': 1}

        if isinstance(stream, AudioStream):
            params['audioStreamID'] = stream.id
        else:
            params['audioStreamID'] = stream

        self._server.query(key, method=self._server._session.put, params=params)
        return self

    def setSelectedSubtitleStream(self, stream):
        """ Set the selected :class:`~plexapi.media.SubtitleStream` for this MediaPart.

            Parameters:
                stream (:class:`~plexapi.media.SubtitleStream`): Subtitle stream to set as selected.
        """
        key = f'/library/parts/{self.id}'
        params = {'allParts': 1}

        if isinstance(stream, SubtitleStream):
            params['subtitleStreamID'] = stream.id
        else:
            params['subtitleStreamID'] = stream

        self._server.query(key, method=self._server._session.put, params=params)
        return self

    def resetSelectedSubtitleStream(self):
        """ Set the selected subtitle of this MediaPart to 'None'. """
        key = f'/library/parts/{self.id}'
        params = {'subtitleStreamID': 0, 'allParts': 1}

        self._server.query(key, method=self._server._session.put, params=params)
        return self


class MediaPartStream(PlexObject):
    """ Base class for media streams. These consist of video, audio, subtitles, and lyrics.

        Attributes:
            bitrate (int): The bitrate of the stream.
            codec (str): The codec of the stream (ex: srt, ac3, mpeg4).
            default (bool): True if this is the default stream.
            displayTitle (str): The display title of the stream.
            extendedDisplayTitle (str): The extended display title of the stream.
            key (str): API URL (/library/streams/<id>)
            id (int): The unique ID for this stream on the server.
            index (int): The index of the stream.
            language (str): The language of the stream (ex: English, ไทย).
            languageCode (str): The ASCII language code of the stream (ex: eng, tha).
            languageTag (str): The two letter language tag of the stream (ex: en, fr).
            requiredBandwidths (str): The required bandwidths to stream the file.
            selected (bool): True if this stream is selected.
            streamType (int): The stream type (1= :class:`~plexapi.media.VideoStream`,
                2= :class:`~plexapi.media.AudioStream`, 3= :class:`~plexapi.media.SubtitleStream`).
            title (str): The title of the stream.
            type (int): Alias for streamType.
    """

    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        self.bitrate = utils.cast(int, data.attrib.get('bitrate'))
        self.codec = data.attrib.get('codec')
        self.decision = data.attrib.get('decision')
        self.default = utils.cast(bool, data.attrib.get('default'))
        self.displayTitle = data.attrib.get('displayTitle')
        self.extendedDisplayTitle = data.attrib.get('extendedDisplayTitle')
        self.id = utils.cast(int, data.attrib.get('id'))
        self.index = utils.cast(int, data.attrib.get('index', '-1'))
        self.key = data.attrib.get('key')
        self.language = data.attrib.get('language')
        self.languageCode = data.attrib.get('languageCode')
        self.languageTag = data.attrib.get('languageTag')
        self.location = data.attrib.get('location')
        self.requiredBandwidths = data.attrib.get('requiredBandwidths')
        self.selected = utils.cast(bool, data.attrib.get('selected', '0'))
        self.streamType = utils.cast(int, data.attrib.get('streamType'))
        self.title = data.attrib.get('title')
        self.type = utils.cast(int, data.attrib.get('streamType'))


@utils.registerPlexObject
class VideoStream(MediaPartStream):
    """ Represents a video stream within a :class:`~plexapi.media.MediaPart`.

        Attributes:
            TAG (str): 'Stream'
            STREAMTYPE (int): 1
            anamorphic (str): If the video is anamorphic.
            bitDepth (int): The bit depth of the video stream (ex: 8).
            cabac (int): The context-adaptive binary arithmetic coding.
            chromaLocation (str): The chroma location of the video stream.
            chromaSubsampling (str): The chroma subsampling of the video stream (ex: 4:2:0).
            codecID (str): The codec ID (ex: XVID).
            codedHeight (int): The coded height of the video stream in pixels.
            codedWidth (int): The coded width of the video stream in pixels.
            colorPrimaries (str): The color primaries of the video stream.
            colorRange (str): The color range of the video stream.
            colorSpace (str): The color space of the video stream (ex: bt2020).
            colorTrc (str): The color trc of the video stream.
            DOVIBLCompatID (int): Dolby Vision base layer compatibility ID.
            DOVIBLPresent (bool): True if Dolby Vision base layer is present.
            DOVIELPresent (bool): True if Dolby Vision enhancement layer is present.
            DOVILevel (int): Dolby Vision level.
            DOVIPresent (bool): True if Dolby Vision is present.
            DOVIProfile (int): Dolby Vision profile.
            DOVIRPUPresent (bool): True if Dolby Vision reference processing unit is present.
            DOVIVersion (float): The Dolby Vision version.
            duration (int): The duration of video stream in milliseconds.
            frameRate (float): The frame rate of the video stream (ex: 23.976).
            frameRateMode (str): The frame rate mode of the video stream.
            hasScalingMatrix (bool): True if video stream has a scaling matrix.
            height (int): The height of the video stream in pixels (ex: 1080).
            level (int): The codec encoding level of the video stream (ex: 41).
            profile (str): The profile of the video stream (ex: asp).
            pixelAspectRatio (str): The pixel aspect ratio of the video stream.
            pixelFormat (str): The pixel format of the video stream.
            refFrames (int): The number of reference frames of the video stream.
            scanType (str): The scan type of the video stream (ex: progressive).
            streamIdentifier(int): The stream identifier of the video stream.
            width (int): The width of the video stream in pixels (ex: 1920).
    """
    TAG = 'Stream'
    STREAMTYPE = 1

    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        super(VideoStream, self)._loadData(data)
        self.anamorphic = data.attrib.get('anamorphic')
        self.bitDepth = utils.cast(int, data.attrib.get('bitDepth'))
        self.cabac = utils.cast(int, data.attrib.get('cabac'))
        self.chromaLocation = data.attrib.get('chromaLocation')
        self.chromaSubsampling = data.attrib.get('chromaSubsampling')
        self.codecID = data.attrib.get('codecID')
        self.codedHeight = utils.cast(int, data.attrib.get('codedHeight'))
        self.codedWidth = utils.cast(int, data.attrib.get('codedWidth'))
        self.colorPrimaries = data.attrib.get('colorPrimaries')
        self.colorRange = data.attrib.get('colorRange')
        self.colorSpace = data.attrib.get('colorSpace')
        self.colorTrc = data.attrib.get('colorTrc')
        self.DOVIBLCompatID = utils.cast(int, data.attrib.get('DOVIBLCompatID'))
        self.DOVIBLPresent = utils.cast(bool, data.attrib.get('DOVIBLPresent'))
        self.DOVIELPresent = utils.cast(bool, data.attrib.get('DOVIELPresent'))
        self.DOVILevel = utils.cast(int, data.attrib.get('DOVILevel'))
        self.DOVIPresent = utils.cast(bool, data.attrib.get('DOVIPresent'))
        self.DOVIProfile = utils.cast(int, data.attrib.get('DOVIProfile'))
        self.DOVIRPUPresent = utils.cast(bool, data.attrib.get('DOVIRPUPresent'))
        self.DOVIVersion = utils.cast(float, data.attrib.get('DOVIVersion'))
        self.duration = utils.cast(int, data.attrib.get('duration'))
        self.frameRate = utils.cast(float, data.attrib.get('frameRate'))
        self.frameRateMode = data.attrib.get('frameRateMode')
        self.hasScalingMatrix = utils.cast(bool, data.attrib.get('hasScalingMatrix'))
        self.height = utils.cast(int, data.attrib.get('height'))
        self.level = utils.cast(int, data.attrib.get('level'))
        self.profile = data.attrib.get('profile')
        self.pixelAspectRatio = data.attrib.get('pixelAspectRatio')
        self.pixelFormat = data.attrib.get('pixelFormat')
        self.refFrames = utils.cast(int, data.attrib.get('refFrames'))
        self.scanType = data.attrib.get('scanType')
        self.streamIdentifier = utils.cast(int, data.attrib.get('streamIdentifier'))
        self.width = utils.cast(int, data.attrib.get('width'))


@utils.registerPlexObject
class AudioStream(MediaPartStream):
    """ Represents a audio stream within a :class:`~plexapi.media.MediaPart`.

        Attributes:
            TAG (str): 'Stream'
            STREAMTYPE (int): 2
            audioChannelLayout (str): The audio channel layout of the audio stream (ex: 5.1(side)).
            bitDepth (int): The bit depth of the audio stream (ex: 16).
            bitrateMode (str): The bitrate mode of the audio stream (ex: cbr).
            channels (int): The number of audio channels of the audio stream (ex: 6).
            duration (int): The duration of audio stream in milliseconds.
            profile (str): The profile of the audio stream.
            samplingRate (int): The sampling rate of the audio stream (ex: xxx)
            streamIdentifier (int): The stream identifier of the audio stream.
            visualImpaired (bool): True if this is a visually impaired (AD) audio stream.

            Track_only_attributes: The following attributes are only available for tracks.

                * albumGain (float): The gain for the album.
                * albumPeak (float): The peak for the album.
                * albumRange (float): The range for the album.
                * endRamp (str): The end ramp for the track.
                * gain (float): The gain for the track.
                * loudness (float): The loudness for the track.
                * lra (float): The lra for the track.
                * peak (float): The peak for the track.
                * startRamp (str): The start ramp for the track.
    """
    TAG = 'Stream'
    STREAMTYPE = 2

    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        super(AudioStream, self)._loadData(data)
        self.audioChannelLayout = data.attrib.get('audioChannelLayout')
        self.bitDepth = utils.cast(int, data.attrib.get('bitDepth'))
        self.bitrateMode = data.attrib.get('bitrateMode')
        self.channels = utils.cast(int, data.attrib.get('channels'))
        self.duration = utils.cast(int, data.attrib.get('duration'))
        self.profile = data.attrib.get('profile')
        self.samplingRate = utils.cast(int, data.attrib.get('samplingRate'))
        self.streamIdentifier = utils.cast(int, data.attrib.get('streamIdentifier'))
        self.visualImpaired = utils.cast(bool, data.attrib.get('visualImpaired', '0'))

        # Track only attributes
        self.albumGain = utils.cast(float, data.attrib.get('albumGain'))
        self.albumPeak = utils.cast(float, data.attrib.get('albumPeak'))
        self.albumRange = utils.cast(float, data.attrib.get('albumRange'))
        self.endRamp = data.attrib.get('endRamp')
        self.gain = utils.cast(float, data.attrib.get('gain'))
        self.loudness = utils.cast(float, data.attrib.get('loudness'))
        self.lra = utils.cast(float, data.attrib.get('lra'))
        self.peak = utils.cast(float, data.attrib.get('peak'))
        self.startRamp = data.attrib.get('startRamp')

    def setSelected(self):
        """ Sets this audio stream as the selected audio stream.
            Alias for :func:`~plexapi.media.MediaPart.setSelectedAudioStream`.
        """
        return self._parent().setSelectedAudioStream(self)

    def levels(self, subSample=128):
        """ Returns a list of :class:`~plexapi.media.Level` objects for this AudioStream.
            Only available for Tracks which have been analyzed for loudness.

            Attributes:
                subSample (int): The number of loudness samples to return. Default 128.
        """
        key = f'/library/streams/{self.id}/levels'
        params = {'subsample': subSample}
        return self.fetchItems(key, params=params)


@utils.registerPlexObject
class SubtitleStream(MediaPartStream):
    """ Represents a audio stream within a :class:`~plexapi.media.MediaPart`.

        Attributes:
            TAG (str): 'Stream'
            STREAMTYPE (int): 3
            canAutoSync (bool): True if the subtitle stream can be auto synced.
            container (str): The container of the subtitle stream.
            forced (bool): True if this is a forced subtitle.
            format (str): The format of the subtitle stream (ex: srt).
            headerCompression (str): The header compression of the subtitle stream.
            hearingImpaired (bool): True if this is a hearing impaired (SDH) subtitle.
            perfectMatch (bool): True if the on-demand subtitle is a perfect match.
            providerTitle (str): The provider title where the on-demand subtitle is downloaded from.
            score (int): The match score (download count) of the on-demand subtitle.
            sourceKey (str): The source key of the on-demand subtitle.
            transient (str): Unknown.
            userID (int): The user id of the user that downloaded the on-demand subtitle.
    """
    TAG = 'Stream'
    STREAMTYPE = 3

    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        super(SubtitleStream, self)._loadData(data)
        self.canAutoSync = utils.cast(bool, data.attrib.get('canAutoSync'))
        self.container = data.attrib.get('container')
        self.forced = utils.cast(bool, data.attrib.get('forced', '0'))
        self.format = data.attrib.get('format')
        self.headerCompression = data.attrib.get('headerCompression')
        self.hearingImpaired = utils.cast(bool, data.attrib.get('hearingImpaired', '0'))
        self.perfectMatch = utils.cast(bool, data.attrib.get('perfectMatch'))
        self.providerTitle = data.attrib.get('providerTitle')
        self.score = utils.cast(int, data.attrib.get('score'))
        self.sourceKey = data.attrib.get('sourceKey')
        self.transient = data.attrib.get('transient')
        self.userID = utils.cast(int, data.attrib.get('userID'))

    def setSelected(self):
        """ Sets this subtitle stream as the selected subtitle stream.
            Alias for :func:`~plexapi.media.MediaPart.setSelectedSubtitleStream`.
        """
        return self._parent().setSelectedSubtitleStream(self)


@utils.registerPlexObject
class LyricStream(MediaPartStream):
    """ Represents a lyric stream within a :class:`~plexapi.media.MediaPart`.

        Attributes:
            TAG (str): 'Stream'
            STREAMTYPE (int): 4
            format (str): The format of the lyric stream (ex: lrc).
            minLines (int): The minimum number of lines in the (timed) lyric stream.
            provider (str): The provider of the lyric stream (ex: com.plexapp.agents.lyricfind).
            timed (bool): True if the lyrics are timed to the track.
    """
    TAG = 'Stream'
    STREAMTYPE = 4

    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        super(LyricStream, self)._loadData(data)
        self.format = data.attrib.get('format')
        self.minLines = utils.cast(int, data.attrib.get('minLines'))
        self.provider = data.attrib.get('provider')
        self.timed = utils.cast(bool, data.attrib.get('timed', '0'))


@utils.registerPlexObject
class Session(PlexObject):
    """ Represents a current session.

        Attributes:
            TAG (str): 'Session'
            id (str): The unique identifier for the session.
            bandwidth (int): The Plex streaming brain reserved bandwidth for the session.
            location (str): The location of the session (lan, wan, or cellular)
    """
    TAG = 'Session'

    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        self.id = data.attrib.get('id')
        self.bandwidth = utils.cast(int, data.attrib.get('bandwidth'))
        self.location = data.attrib.get('location')


@utils.registerPlexObject
class TranscodeSession(PlexObject):
    """ Represents a current transcode session.

        Attributes:
            TAG (str): 'TranscodeSession'
            audioChannels (int): The number of audio channels of the transcoded media.
            audioCodec (str): The audio codec of the transcoded media.
            audioDecision (str): The transcode decision for the audio stream.
            complete (bool): True if the transcode is complete.
            container (str): The container of the transcoded media.
            context (str): The context for the transcode session.
            duration (int): The duration of the transcoded media in milliseconds.
            height (int): The height of the transcoded media in pixels.
            key (str): API URL (ex: /transcode/sessions/<id>).
            maxOffsetAvailable (float): Unknown.
            minOffsetAvailable (float): Unknown.
            progress (float): The progress percentage of the transcode.
            protocol (str): The protocol of the transcode.
            remaining (int): Unknown.
            size (int): The size of the transcoded media in bytes.
            sourceAudioCodec (str): The audio codec of the source media.
            sourceVideoCodec (str): The video codec of the source media.
            speed (float): The speed of the transcode.
            subtitleDecision (str): The transcode decision for the subtitle stream
            throttled (bool): True if the transcode is throttled.
            timestamp (int): The epoch timestamp when the transcode started.
            transcodeHwDecoding (str): The hardware transcoding decoder engine.
            transcodeHwDecodingTitle (str): The title of the hardware transcoding decoder engine.
            transcodeHwEncoding (str): The hardware transcoding encoder engine.
            transcodeHwEncodingTitle (str): The title of the hardware transcoding encoder engine.
            transcodeHwFullPipeline (str): True if hardware decoding and encoding is being used for the transcode.
            transcodeHwRequested (str): True if hardware transcoding was requested for the transcode.
            videoCodec (str): The video codec of the transcoded media.
            videoDecision (str): The transcode decision for the video stream.
            width (str): The width of the transcoded media in pixels.
    """
    TAG = 'TranscodeSession'

    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        self.audioChannels = utils.cast(int, data.attrib.get('audioChannels'))
        self.audioCodec = data.attrib.get('audioCodec')
        self.audioDecision = data.attrib.get('audioDecision')
        self.complete = utils.cast(bool, data.attrib.get('complete', '0'))
        self.container = data.attrib.get('container')
        self.context = data.attrib.get('context')
        self.duration = utils.cast(int, data.attrib.get('duration'))
        self.height = utils.cast(int, data.attrib.get('height'))
        self.key = data.attrib.get('key')
        self.maxOffsetAvailable = utils.cast(float, data.attrib.get('maxOffsetAvailable'))
        self.minOffsetAvailable = utils.cast(float, data.attrib.get('minOffsetAvailable'))
        self.progress = utils.cast(float, data.attrib.get('progress'))
        self.protocol = data.attrib.get('protocol')
        self.remaining = utils.cast(int, data.attrib.get('remaining'))
        self.size = utils.cast(int, data.attrib.get('size'))
        self.sourceAudioCodec = data.attrib.get('sourceAudioCodec')
        self.sourceVideoCodec = data.attrib.get('sourceVideoCodec')
        self.speed = utils.cast(float, data.attrib.get('speed'))
        self.subtitleDecision = data.attrib.get('subtitleDecision')
        self.throttled = utils.cast(bool, data.attrib.get('throttled', '0'))
        self.timestamp = utils.cast(float, data.attrib.get('timeStamp'))
        self.transcodeHwDecoding = data.attrib.get('transcodeHwDecoding')
        self.transcodeHwDecodingTitle = data.attrib.get('transcodeHwDecodingTitle')
        self.transcodeHwEncoding = data.attrib.get('transcodeHwEncoding')
        self.transcodeHwEncodingTitle = data.attrib.get('transcodeHwEncodingTitle')
        self.transcodeHwFullPipeline = utils.cast(bool, data.attrib.get('transcodeHwFullPipeline', '0'))
        self.transcodeHwRequested = utils.cast(bool, data.attrib.get('transcodeHwRequested', '0'))
        self.videoCodec = data.attrib.get('videoCodec')
        self.videoDecision = data.attrib.get('videoDecision')
        self.width = utils.cast(int, data.attrib.get('width'))


@utils.registerPlexObject
class TranscodeJob(PlexObject):
    """ Represents an Optimizing job.
        TrancodeJobs are the process for optimizing conversions.
        Active or paused optimization items. Usually one item as a time."""
    TAG = 'TranscodeJob'

    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        self.generatorID = data.attrib.get('generatorID')
        self.key = data.attrib.get('key')
        self.progress = data.attrib.get('progress')
        self.ratingKey = data.attrib.get('ratingKey')
        self.size = data.attrib.get('size')
        self.targetTagID = data.attrib.get('targetTagID')
        self.thumb = data.attrib.get('thumb')
        self.title = data.attrib.get('title')
        self.type = data.attrib.get('type')


@utils.registerPlexObject
class Optimized(PlexObject):
    """ Represents a Optimized item.
        Optimized items are optimized and queued conversions items."""
    TAG = 'Item'

    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        self.id = data.attrib.get('id')
        self.composite = data.attrib.get('composite')
        self.title = data.attrib.get('title')
        self.type = data.attrib.get('type')
        self.target = data.attrib.get('target')
        self.targetTagID = data.attrib.get('targetTagID')

    def items(self):
        """ Returns a list of all :class:`~plexapi.media.Video` objects
            in this optimized item.
        """
        key = f'{self._initpath}/{self.id}/items'
        return self.fetchItems(key)

    def remove(self):
        """ Remove an Optimized item"""
        key = f'{self._initpath}/{self.id}'
        self._server.query(key, method=self._server._session.delete)

    def rename(self, title):
        """ Rename an Optimized item"""
        key = f'{self._initpath}/{self.id}?Item[title]={title}'
        self._server.query(key, method=self._server._session.put)

    def reprocess(self, ratingKey):
        """ Reprocess a removed Conversion item that is still a listed Optimize item"""
        key = f'{self._initpath}/{self.id}/{ratingKey}/enable'
        self._server.query(key, method=self._server._session.put)


@utils.registerPlexObject
class Conversion(PlexObject):
    """ Represents a Conversion item.
        Conversions are items queued for optimization or being actively optimized."""
    TAG = 'Video'

    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        self.addedAt = data.attrib.get('addedAt')
        self.art = data.attrib.get('art')
        self.chapterSource = data.attrib.get('chapterSource')
        self.contentRating = data.attrib.get('contentRating')
        self.duration = data.attrib.get('duration')
        self.generatorID = data.attrib.get('generatorID')
        self.generatorType = data.attrib.get('generatorType')
        self.guid = data.attrib.get('guid')
        self.key = data.attrib.get('key')
        self.lastViewedAt = data.attrib.get('lastViewedAt')
        self.librarySectionID = data.attrib.get('librarySectionID')
        self.librarySectionKey = data.attrib.get('librarySectionKey')
        self.librarySectionTitle = data.attrib.get('librarySectionTitle')
        self.originallyAvailableAt = data.attrib.get('originallyAvailableAt')
        self.playQueueItemID = data.attrib.get('playQueueItemID')
        self.playlistID = data.attrib.get('playlistID')
        self.primaryExtraKey = data.attrib.get('primaryExtraKey')
        self.rating = data.attrib.get('rating')
        self.ratingKey = data.attrib.get('ratingKey')
        self.studio = data.attrib.get('studio')
        self.summary = data.attrib.get('summary')
        self.tagline = data.attrib.get('tagline')
        self.target = data.attrib.get('target')
        self.thumb = data.attrib.get('thumb')
        self.title = data.attrib.get('title')
        self.type = data.attrib.get('type')
        self.updatedAt = data.attrib.get('updatedAt')
        self.userID = data.attrib.get('userID')
        self.username = data.attrib.get('username')
        self.viewOffset = data.attrib.get('viewOffset')
        self.year = data.attrib.get('year')

    def remove(self):
        """ Remove Conversion from queue """
        key = f'/playlists/{self.playlistID}/items/{self.generatorID}/{self.ratingKey}/disable'
        self._server.query(key, method=self._server._session.put)

    def move(self, after):
        """ Move Conversion items position in queue
            after (int): Place item after specified playQueueItemID. '-1' is the active conversion.

                Example:
                    Move 5th conversion Item to active conversion
                        conversions[4].move('-1')

                    Move 4th conversion Item to 3rd in conversion queue
                        conversions[3].move(conversions[1].playQueueItemID)
        """

        key = f'{self._initpath}/items/{self.playQueueItemID}/move?after={after}'
        self._server.query(key, method=self._server._session.put)


class MediaTag(PlexObject):
    """ Base class for media tags used for filtering and searching your library
        items or navigating the metadata of media items in your library. Tags are
        the construct used for things such as Country, Director, Genre, etc.

        Attributes:
            filter (str): The library filter for the tag.
            id (int): Tag ID (This seems meaningless except to use it as a unique id).
            key (str): API URL (/library/section/<librarySectionID>/all?<filter>).
            role (str): The name of the character role for :class:`~plexapi.media.Role` only.
            tag (str): Name of the tag. This will be Animation, SciFi etc for Genres. The name of
                person for Directors and Roles (ex: Animation, Stephen Graham, etc).
            tagKey (str): Plex GUID for the actor/actress for :class:`~plexapi.media.Role` only.
            thumb (str): URL to thumbnail image for :class:`~plexapi.media.Role` only.
    """

    def __str__(self):
        """ Returns the tag name. """
        return self.tag

    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        self.filter = data.attrib.get('filter')
        self.id = utils.cast(int, data.attrib.get('id'))
        self.key = data.attrib.get('key')
        self.role = data.attrib.get('role')
        self.tag = data.attrib.get('tag')
        self.tagKey = data.attrib.get('tagKey')
        self.thumb = data.attrib.get('thumb')

        parent = self._parent()
        self._librarySectionID = utils.cast(int, parent._data.attrib.get('librarySectionID'))
        self._librarySectionKey = parent._data.attrib.get('librarySectionKey')
        self._librarySectionTitle = parent._data.attrib.get('librarySectionTitle')
        self._parentType = parent.TYPE

        if self._librarySectionKey and self.filter:
            self.key = f'{self._librarySectionKey}/all?{self.filter}&type={utils.searchType(self._parentType)}'

    def items(self):
        """ Return the list of items within this tag. """
        if not self.key:
            raise BadRequest(f'Key is not defined for this tag: {self.tag}. Reload the parent object.')
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

    def collection(self):
        """ Return the :class:`~plexapi.collection.Collection` object for this collection tag.
        """
        key = f'{self._librarySectionKey}/collections'
        return self.fetchItem(key, etag='Directory', index=self.id)


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
class Format(MediaTag):
    """ Represents a single Format media tag.

        Attributes:
            TAG (str): 'Format'
            FILTER (str): 'format'
    """
    TAG = 'Format'
    FILTER = 'format'


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
class Label(MediaTag):
    """ Represents a single Label media tag.

        Attributes:
            TAG (str): 'Label'
            FILTER (str): 'label'
    """
    TAG = 'Label'
    FILTER = 'label'


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
class Style(MediaTag):
    """ Represents a single Style media tag.

        Attributes:
            TAG (str): 'Style'
            FILTER (str): 'style'
    """
    TAG = 'Style'
    FILTER = 'style'


@utils.registerPlexObject
class Subformat(MediaTag):
    """ Represents a single Subformat media tag.

        Attributes:
            TAG (str): 'Subformat'
            FILTER (str): 'subformat'
    """
    TAG = 'Subformat'
    FILTER = 'subformat'


@utils.registerPlexObject
class Tag(MediaTag):
    """ Represents a single Tag media tag.

        Attributes:
            TAG (str): 'Tag'
            FILTER (str): 'tag'
    """
    TAG = 'Tag'
    FILTER = 'tag'


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
class Guid(PlexObject):
    """ Represents a single Guid media tag.

        Attributes:
            TAG (str): 'Guid'
            id (id): The guid for external metadata sources (e.g. IMDB, TMDB, TVDB, MBID).
    """
    TAG = 'Guid'

    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        self.id = data.attrib.get('id')


@utils.registerPlexObject
class Image(PlexObject):
    """ Represents a single Image media tag.

        Attributes:
            TAG (str): 'Image'
            alt (str): The alt text for the image.
            type (str): The type of image (e.g. coverPoster, background, snapshot).
            url (str): The API URL (/library/metadata/<ratingKey>/thumb/<thumbid>).
    """
    TAG = 'Image'

    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        self.alt = data.attrib.get('alt')
        self.type = data.attrib.get('type')
        self.url = data.attrib.get('url')


@utils.registerPlexObject
class Rating(PlexObject):
    """ Represents a single Rating media tag.

        Attributes:
            TAG (str): 'Rating'
            image (str): The uri for the rating image
                (e.g. ``imdb://image.rating``, ``rottentomatoes://image.rating.ripe``,
                ``rottentomatoes://image.rating.upright``, ``themoviedb://image.rating``).
            type (str): The type of rating (e.g. audience or critic).
            value (float): The rating value.
    """
    TAG = 'Rating'

    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        self.image = data.attrib.get('image')
        self.type = data.attrib.get('type')
        self.value = utils.cast(float, data.attrib.get('value'))


@utils.registerPlexObject
class Review(PlexObject):
    """ Represents a single Review for a Movie.

        Attributes:
            TAG (str): 'Review'
            filter (str): The library filter for the review.
            id (int): The ID of the review.
            image (str): The image uri for the review.
            link (str): The url to the online review.
            source (str): The source of the review.
            tag (str): The name of the reviewer.
            text (str): The text of the review.
    """
    TAG = 'Review'

    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        self.filter = data.attrib.get('filter')
        self.id = utils.cast(int, data.attrib.get('id', 0))
        self.image = data.attrib.get('image')
        self.link = data.attrib.get('link')
        self.source = data.attrib.get('source')
        self.tag = data.attrib.get('tag')
        self.text = data.attrib.get('text')


@utils.registerPlexObject
class UltraBlurColors(PlexObject):
    """ Represents a single UltraBlurColors media tag.

        Attributes:
            TAG (str): 'UltraBlurColors'
            bottomLeft (str): The bottom left hex color.
            bottomRight (str): The bottom right hex color.
            topLeft (str): The top left hex color.
            topRight (str): The top right hex color.
    """
    TAG = 'UltraBlurColors'

    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        self.bottomLeft = data.attrib.get('bottomLeft')
        self.bottomRight = data.attrib.get('bottomRight')
        self.topLeft = data.attrib.get('topLeft')
        self.topRight = data.attrib.get('topRight')


class BaseResource(PlexObject):
    """ Base class for all Art, Poster, and Theme objects.

        Attributes:
            TAG (str): 'Photo' or 'Track'
            key (str): API URL (/library/metadata/<ratingkey>).
            provider (str): The source of the resource. 'local' for local files (e.g. theme.mp3),
                None if uploaded or agent-/plugin-supplied.
            ratingKey (str): Unique key identifying the resource.
            selected (bool): True if the resource is currently selected.
            thumb (str): The URL to retrieve the resource thumbnail.
    """

    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        self.key = data.attrib.get('key')
        self.provider = data.attrib.get('provider')
        self.ratingKey = data.attrib.get('ratingKey')
        self.selected = utils.cast(bool, data.attrib.get('selected'))
        self.thumb = data.attrib.get('thumb')

    def select(self):
        key = self._initpath[:-1]
        data = f'{key}?url={quote_plus(self.ratingKey)}'
        try:
            self._server.query(data, method=self._server._session.put)
        except ElementTree.ParseError:
            pass

    @property
    def resourceFilepath(self):
        """ Returns the file path to the resource in the Plex Media Server data directory.
            Note: Returns the URL if the resource is not stored locally.
        """
        if self.ratingKey.startswith('media://'):
            return str(Path('Media') / 'localhost' / self.ratingKey.split('://')[-1])
        elif self.ratingKey.startswith('metadata://'):
            return str(Path(self._parent().metadataDirectory) / 'Contents' / '_combined' / self.ratingKey.split('://')[-1])
        elif self.ratingKey.startswith('upload://'):
            return str(Path(self._parent().metadataDirectory) / 'Uploads' / self.ratingKey.split('://')[-1])
        else:
            return self.ratingKey


class Art(BaseResource):
    """ Represents a single Art object. """
    TAG = 'Photo'


class Logo(BaseResource):
    """ Represents a single Logo object. """
    TAG = 'Photo'


class Poster(BaseResource):
    """ Represents a single Poster object. """
    TAG = 'Photo'


class SquareArt(BaseResource):
    """ Represents a single Square Art object. """
    TAG = 'Photo'


class Theme(BaseResource):
    """ Represents a single Theme object. """
    TAG = 'Track'


@utils.registerPlexObject
class Chapter(PlexObject):
    """ Represents a single Chapter media tag.

        Attributes:
            TAG (str): 'Chapter'
            end (int): The end time of the chapter in milliseconds.
            filter (str): The library filter for the chapter.
            id (int): The ID of the chapter.
            index (int): The index of the chapter.
            tag (str): The name of the chapter.
            title (str): The title of the chapter.
            thumb (str): The URL to retrieve the chapter thumbnail.
            start (int): The start time of the chapter in milliseconds.
    """
    TAG = 'Chapter'

    def __repr__(self):
        name = self._clean(self.firstAttr('tag'))
        start = utils.millisecondToHumanstr(self._clean(self.firstAttr('start')))
        end = utils.millisecondToHumanstr(self._clean(self.firstAttr('end')))
        offsets = f'{start}-{end}'
        return f"<{':'.join([self.__class__.__name__, name, offsets])}>"

    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        self.end = utils.cast(int, data.attrib.get('endTimeOffset'))
        self.filter = data.attrib.get('filter')
        self.id = utils.cast(int, data.attrib.get('id', 0))
        self.index = utils.cast(int, data.attrib.get('index'))
        self.tag = data.attrib.get('tag')
        self.title = self.tag
        self.thumb = data.attrib.get('thumb')
        self.start = utils.cast(int, data.attrib.get('startTimeOffset'))


@utils.registerPlexObject
class Marker(PlexObject):
    """ Represents a single Marker media tag.

        Attributes:
            TAG (str): 'Marker'
            end (int): The end time of the marker in milliseconds.
            final (bool): True if the marker is the final credits marker.
            id (int): The ID of the marker.
            type (str): The type of marker.
            start (int): The start time of the marker in milliseconds.
            version (int): The Plex marker version.
    """
    TAG = 'Marker'

    def __repr__(self):
        name = self._clean(self.firstAttr('type'))
        start = utils.millisecondToHumanstr(self._clean(self.firstAttr('start')))
        end = utils.millisecondToHumanstr(self._clean(self.firstAttr('end')))
        offsets = f'{start}-{end}'
        return f"<{':'.join([self.__class__.__name__, name, offsets])}>"

    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        self.end = utils.cast(int, data.attrib.get('endTimeOffset'))
        self.final = utils.cast(bool, data.attrib.get('final'))
        self.id = utils.cast(int, data.attrib.get('id'))
        self.type = data.attrib.get('type')
        self.start = utils.cast(int, data.attrib.get('startTimeOffset'))

        attributes = data.find('Attributes')
        self.version = attributes.attrib.get('version')

    @property
    def first(self):
        """ Returns True if the marker in the first credits marker. """
        if self.type != 'credits':
            return None
        first = min(
            (marker for marker in self._parent().markers if marker.type == 'credits'),
            key=lambda m: m.start
        )
        return first == self


@utils.registerPlexObject
class Field(PlexObject):
    """ Represents a single Field.

        Attributes:
            TAG (str): 'Field'
            locked (bool): True if the field is locked.
            name (str): The name of the field.
    """
    TAG = 'Field'

    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        self.locked = utils.cast(bool, data.attrib.get('locked'))
        self.name = data.attrib.get('name')


@utils.registerPlexObject
class SearchResult(PlexObject):
    """ Represents a single SearchResult.

        Attributes:
            TAG (str): 'SearchResult'
    """
    TAG = 'SearchResult'

    def __repr__(self):
        name = self._clean(self.firstAttr('name'))
        score = self._clean(self.firstAttr('score'))
        return f"<{':'.join([p for p in [self.__class__.__name__, name, score] if p])}>"

    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        self.guid = data.attrib.get('guid')
        self.lifespanEnded = data.attrib.get('lifespanEnded')
        self.name = data.attrib.get('name')
        self.score = utils.cast(int, data.attrib.get('score'))
        self.year = data.attrib.get('year')


@utils.registerPlexObject
class Agent(PlexObject):
    """ Represents a single Agent.

        Attributes:
            TAG (str): 'Agent'
    """
    TAG = 'Agent'

    def __repr__(self):
        uid = self._clean(self.firstAttr('shortIdentifier'))
        return f"<{':'.join([p for p in [self.__class__.__name__, uid] if p])}>"

    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        self.hasAttribution = data.attrib.get('hasAttribution')
        self.hasPrefs = data.attrib.get('hasPrefs')
        self.identifier = data.attrib.get('identifier')
        self.name = data.attrib.get('name')
        self.primary = data.attrib.get('primary')
        self.shortIdentifier = self.identifier.rsplit('.', 1)[1]

    @cached_data_property
    def languageCodes(self):
        if 'mediaType' in self._initpath:
            return self.listAttrs(self._data, 'code', etag='Language')
        return []

    @cached_data_property
    def mediaTypes(self):
        if 'mediaType' not in self._initpath:
            return self.findItems(self._data, cls=AgentMediaType)
        return []

    def settings(self):
        key = f'/:/plugins/{self.identifier}/prefs'
        data = self._server.query(key)
        return self.findItems(data, cls=settings.Setting)


class AgentMediaType(Agent):
    """ Represents a single Agent MediaType.

        Attributes:
            TAG (str): 'MediaType'
    """
    TAG = 'MediaType'

    def __repr__(self):
        uid = self._clean(self.firstAttr('name'))
        return f"<{':'.join([p for p in [self.__class__.__name__, uid] if p])}>"

    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        self.mediaType = utils.cast(int, data.attrib.get('mediaType'))
        self.name = data.attrib.get('name')

    @cached_data_property
    def languageCodes(self):
        return self.listAttrs(self._data, 'code', etag='Language')


@utils.registerPlexObject
class Availability(PlexObject):
    """ Represents a single online streaming service Availability.

        Attributes:
            TAG (str): 'Availability'
            country (str): The streaming service country.
            offerType (str): Subscription, buy, or rent from the streaming service.
            platform (str): The platform slug for the streaming service.
            platformColorThumb (str): Thumbnail icon for the streaming service.
            platformInfo (str): The streaming service platform info.
            platformUrl (str): The URL to the media on the streaming service.
            price (float): The price to buy or rent from the streaming service.
            priceDescription (str): The display price to buy or rent from the streaming service.
            quality (str): The video quality on the streaming service.
            title (str): The title of the streaming service.
            url (str): The Plex availability URL.
    """
    TAG = 'Availability'

    def __repr__(self):
        return f'<{self.__class__.__name__}:{self.platform}:{self.offerType}>'

    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        self.country = data.attrib.get('country')
        self.offerType = data.attrib.get('offerType')
        self.platform = data.attrib.get('platform')
        self.platformColorThumb = data.attrib.get('platformColorThumb')
        self.platformInfo = data.attrib.get('platformInfo')
        self.platformUrl = data.attrib.get('platformUrl')
        self.price = utils.cast(float, data.attrib.get('price'))
        self.priceDescription = data.attrib.get('priceDescription')
        self.quality = data.attrib.get('quality')
        self.title = data.attrib.get('title')
        self.url = data.attrib.get('url')


@utils.registerPlexObject
class Level(PlexObject):
    """ Represents a single loudness Level sample for an AudioStream.

        Attributes:
            loudness (float): Loudness level value
    """
    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        self.loudness = utils.cast(float, data.attrib.get('v'))


@utils.registerPlexObject
class CommonSenseMedia(PlexObject):
    """ Represents a single CommonSenseMedia media tag.
        Note: This object is only loaded with partial data from a Plex Media Server.
        Call `reload()` to load the full data from Plex Discover (Plex Pass required).

        Attributes:
            TAG (str): 'CommonSenseMedia'
            ageRatings (List<:class:`~plexapi.media.AgeRating`>): List of AgeRating objects.
            anyGood (str): A brief description of the media's quality.
            id (int): The ID of the CommonSenseMedia tag.
            key (str): The unique key for the CommonSenseMedia tag.
            oneLiner (str): A brief description of the CommonSenseMedia tag.
            parentalAdvisoryTopics (List<:class:`~plexapi.media.ParentalAdvisoryTopic`>):
                List of ParentalAdvisoryTopic objects.
            parentsNeedToKnow (str): A brief description of what parents need to know about the media.
            talkingPoints (List<:class:`~plexapi.media.TalkingPoint`>): List of TalkingPoint objects.

        Example:

            .. code-block:: python

                from plexapi.server import PlexServer
                plex = PlexServer('http://localhost:32400', token='xxxxxxxxxxxxxxxxxxxx')

                # Retrieve the Common Sense Media info for a movie
                movie = plex.library.section('Movies').get('Cars')
                commonSenseMedia = movie.commonSenseMedia
                ageRating = commonSenseMedia.ageRatings[0].age

                # Load the Common Sense Media info from Plex Discover (Plex Pass required)
                commonSenseMedia.reload()
                parentalAdvisoryTopics = commonSenseMedia.parentalAdvisoryTopics
                talkingPoints = commonSenseMedia.talkingPoints

    """
    TAG = 'CommonSenseMedia'

    def _loadData(self, data):
        self.ageRatings = self.findItems(data, AgeRating)
        self.anyGood = data.attrib.get('anyGood')
        self.id = utils.cast(int, data.attrib.get('id'))
        self.key = data.attrib.get('key')
        self.oneLiner = data.attrib.get('oneLiner')
        self.parentalAdvisoryTopics = self.findItems(data, ParentalAdvisoryTopic)
        self.parentsNeedToKnow = data.attrib.get('parentsNeedToKnow')
        self.talkingPoints = self.findItems(data, TalkingPoint)

    def _reload(self, **kwargs):
        """ Reload the data for the Common Sense Media object. """
        guid = self._parent().guid
        if not guid.startswith('plex://'):
            return self

        ratingKey = guid.rsplit('/', 1)[-1]
        account = self._server.myPlexAccount()
        key = f'{account.METADATA}/library/metadata/{ratingKey}/commonsensemedia'
        data = account.query(key)
        self._findAndLoadElem(data)
        return self


@utils.registerPlexObject
class AgeRating(PlexObject):
    """ Represents a single AgeRating for a Common Sense Media tag.

        Attributes:
            TAG (str): 'AgeRating'
            age (float): The age rating (e.g. 13, 17).
            ageGroup (str): The age group for the rating (e.g. Little Kids, Teens, etc.).
            rating (float): The star rating (out of 5).
            ratingCount (int): The number of ratings contributing to the star rating.
            type (str): The type of rating (official, adult, child).
    """
    TAG = 'AgeRating'

    def _loadData(self, data):
        self.age = utils.cast(float, data.attrib.get('age'))
        self.ageGroup = data.attrib.get('ageGroup')
        self.rating = utils.cast(float, data.attrib.get('rating'))
        self.ratingCount = utils.cast(int, data.attrib.get('ratingCount'))
        self.type = data.attrib.get('type')


@utils.registerPlexObject
class TalkingPoint(PlexObject):
    """ Represents a single TalkingPoint for a Common Sense Media tag.

        Attributes:
            TAG (str): 'TalkingPoint'
            tag (str): The description of the talking point.
    """
    TAG = 'TalkingPoint'

    def _loadData(self, data):
        self.tag = data.attrib.get('tag')


@utils.registerPlexObject
class ParentalAdvisoryTopic(PlexObject):
    """ Represents a single ParentalAdvisoryTopic for a Common Sense Media tag.

        Attributes:
            TAG (str): 'ParentalAdvisoryTopic'
            id (str): The ID of the topic (e.g. violence, language, etc.).
            label (str): The label for the topic (e.g. Violence & Scariness, Language, etc.).
            positive (bool): Whether the topic is considered positive.
            rating (float): The rating of the topic (out of 5).
            tag (str): The description of the parental advisory topic.
    """
    TAG = 'ParentalAdvisoryTopic'

    def _loadData(self, data):
        self.id = data.attrib.get('id')
        self.label = data.attrib.get('label')
        self.positive = utils.cast(bool, data.attrib.get('positive'))
        self.rating = utils.cast(float, data.attrib.get('rating'))
        self.tag = data.attrib.get('tag')
