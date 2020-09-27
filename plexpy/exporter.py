# -*- coding: utf-8 -*-

# This file is part of Tautulli.
#
#  Tautulli is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  Tautulli is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with Tautulli.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals
from future.builtins import str
from backports import csv

import json
import os
import requests
import shutil
import threading

from functools import partial, reduce
from io import open
from multiprocessing.dummy import Pool as ThreadPool

import plexpy
if plexpy.PYTHON2:
    import database
    import datatables
    import helpers
    import logger
    from plex import Plex
else:
    from plexpy import database
    from plexpy import datatables
    from plexpy import helpers
    from plexpy import logger
    from plexpy.plex import Plex


class Export(object):
    MEDIA_TYPES = (
        'movie',
        'show', 'season', 'episode',
        'artist', 'album', 'track',
        'photo album', 'photo',
        'collection',
        'playlist'
    )
    CHILDREN = {
        'show': 'season',
        'season': 'episode',
        'artist': 'album',
        'album': 'track',
        'photo album': 'photo'
    }
    LEVELS = (1, 2, 3, 9)

    def __init__(self, section_id=None, rating_key=None, file_format='json',
                 metadata_level=1, media_info_level=1, include_images=False):
        self.section_id = helpers.cast_to_int(section_id)
        self.rating_key = helpers.cast_to_int(rating_key)
        self.file_format = file_format
        self.metadata_level = helpers.cast_to_int(metadata_level)
        self.media_info_level = helpers.cast_to_int(media_info_level)
        self.include_images = include_images

        self.timestamp = helpers.timestamp()

        self.media_type = None
        self.items = []

        self.filename = None
        self.export_id = None
        self.file_size = None
        self.success = False

    def _get_all_metadata_attr(self, media_type):
        exclude_attrs = ('media', 'artFile', 'thumbFile')
        all_attrs = self.return_attrs(media_type)
        return [attr for attr in all_attrs if attr not in exclude_attrs]

    def return_attrs(self, media_type):
        def movie_attrs():
            _movie_attrs = {
                'addedAt': helpers.datetime_to_iso,
                'art': None,
                'artFile': lambda i: get_image(i, 'art', self.filename),
                'audienceRating': None,
                'audienceRatingImage': None,
                'chapters': {
                    'id': None,
                    'tag': None,
                    'index': None,
                    'start': None,
                    'end': None,
                    'thumb': None
                },
                'chapterSource': None,
                'collections': {
                    'id': None,
                    'tag': None
                },
                'contentRating': None,
                'countries': {
                    'id': None,
                    'tag': None
                },
                'directors': {
                    'id': None,
                    'tag': None
                },
                'duration': None,
                'durationHuman': lambda i: helpers.human_duration(getattr(i, 'duration', 0), sig='dhm'),
                'fields': {
                    'name': None,
                    'locked': None
                },
                'genres': {
                    'id': None,
                    'tag': None
                },
                'guid': None,
                'key': None,
                'labels': {
                    'id': None,
                    'tag': None
                },
                'lastViewedAt': helpers.datetime_to_iso,
                'librarySectionID': None,
                'librarySectionKey': None,
                'librarySectionTitle': None,
                'locations': None,
                'media': {
                    'aspectRatio': None,
                    'audioChannels': None,
                    'audioCodec': None,
                    'audioProfile': None,
                    'bitrate': None,
                    'container': None,
                    'duration': None,
                    'height': None,
                    'id': None,
                    'has64bitOffsets': None,
                    'optimizedForStreaming': None,
                    'optimizedVersion': None,
                    'target': None,
                    'title': None,
                    'videoCodec': None,
                    'videoFrameRate': None,
                    'videoProfile': None,
                    'videoResolution': None,
                    'width': None,
                    'hdr': lambda i: get_any_hdr(i, self.return_attrs('movie')['media']),
                    'parts': {
                        'accessible': None,
                        'audioProfile': None,
                        'container': None,
                        'deepAnalysisVersion': None,
                        'duration': None,
                        'exists': None,
                        'file': None,
                        'has64bitOffsets': None,
                        'id': None,
                        'indexes': None,
                        'key': None,
                        'size': None,
                        'sizeHuman': lambda i: helpers.human_file_size(getattr(i, 'size', 0)),
                        'optimizedForStreaming': None,
                        'requiredBandwidths': lambda e: [int(b) for b in e.split(',')] if e else None,
                        'syncItemId': None,
                        'syncState': None,
                        'videoProfile': None,
                        'videoStreams': {
                            'codec': None,
                            'codecID': None,
                            'default': None,
                            'displayTitle': None,
                            'extendedDisplayTitle': None,
                            'id': None,
                            'index': None,
                            'language': None,
                            'languageCode': None,
                            'selected': None,
                            'streamType': None,
                            'title': None,
                            'type': None,
                            'bitDepth': None,
                            'bitrate': None,
                            'cabac': None,
                            'chromaLocation': None,
                            'chromaSubsampling': None,
                            'colorPrimaries': None,
                            'colorRange': None,
                            'colorSpace': None,
                            'colorTrc': None,
                            'duration': None,
                            'frameRate': None,
                            'frameRateMode': None,
                            'hasScalingMatrix': None,
                            'hdr': lambda i: helpers.is_hdr(getattr(i, 'bitDepth', 0), getattr(i, 'colorSpace', '')),
                            'height': None,
                            'level': None,
                            'pixelAspectRatio': None,
                            'pixelFormat': None,
                            'profile': None,
                            'refFrames': None,
                            'requiredBandwidths': lambda e: [int(b) for b in e.split(',')] if e else None,
                            'scanType': None,
                            'streamIdentifier': None,
                            'width': None
                        },
                        'audioStreams': {
                            'codec': None,
                            'codecID': None,
                            'default': None,
                            'displayTitle': None,
                            'extendedDisplayTitle': None,
                            'id': None,
                            'index': None,
                            'language': None,
                            'languageCode': None,
                            'selected': None,
                            'streamType': None,
                            'title': None,
                            'type': None,
                            'audioChannelLayout': None,
                            'bitDepth': None,
                            'bitrate': None,
                            'bitrateMode': None,
                            'channels': None,
                            'dialogNorm': None,
                            'duration': None,
                            'profile': None,
                            'requiredBandwidths': lambda e: [int(b) for b in e.split(',')] if e else None,
                            'samplingRate': None
                        },
                        'subtitleStreams': {
                            'codec': None,
                            'codecID': None,
                            'default': None,
                            'displayTitle': None,
                            'extendedDisplayTitle': None,
                            'id': None,
                            'index': None,
                            'language': None,
                            'languageCode': None,
                            'requiredBandwidths': lambda e: [int(b) for b in e.split(',')] if e else None,
                            'selected': None,
                            'streamType': None,
                            'title': None,
                            'type': None,
                            'forced': None,
                            'format': None,
                            'headerCompression': None,
                            'key': None
                        }
                    }
                },
                'originallyAvailableAt': partial(helpers.datetime_to_iso, to_date=True),
                'originalTitle': None,
                'producers': {
                    'id': None,
                    'tag': None
                },
                'rating': None,
                'ratingImage': None,
                'ratingKey': None,
                'roles': {
                    'id': None,
                    'tag': None,
                    'role': None,
                    'thumb': None
                },
                'studio': None,
                'summary': None,
                'tagline': None,
                'thumb': None,
                'thumbFile': lambda i: get_image(i, 'thumb', self.filename),
                'title': None,
                'titleSort': None,
                'type': None,
                'updatedAt': helpers.datetime_to_iso,
                'userRating': None,
                'viewCount': None,
                'writers': {
                    'id': None,
                    'tag': None
                },
                'year': None
            }
            return _movie_attrs

        def show_attrs():
            _show_attrs = {
                'addedAt': helpers.datetime_to_iso,
                'art': None,
                'artFile': lambda i: get_image(i, 'art', self.filename),
                'banner': None,
                'childCount': None,
                'collections': {
                    'id': None,
                    'tag': None
                },
                'contentRating': None,
                'duration': None,
                'durationHuman': lambda i: helpers.human_duration(getattr(i, 'duration', 0), sig='dhm'),
                'fields': {
                    'name': None,
                    'locked': None
                },
                'genres': {
                    'id': None,
                    'tag': None
                },
                'guid': None,
                'index': None,
                'key': None,
                'labels': {
                    'id': None,
                    'tag': None
                },
                'lastViewedAt': helpers.datetime_to_iso,
                'leafCount': None,
                'librarySectionID': None,
                'librarySectionKey': None,
                'librarySectionTitle': None,
                'locations': None,
                'originallyAvailableAt': partial(helpers.datetime_to_iso, to_date=True),
                'rating': None,
                'ratingKey': None,
                'roles': {
                    'id': None,
                    'tag': None,
                    'role': None,
                    'thumb': None
                },
                'studio': None,
                'summary': None,
                'theme': None,
                'thumb': None,
                'thumbFile': lambda i: get_image(i, 'thumb', self.filename),
                'title': None,
                'titleSort': None,
                'type': None,
                'updatedAt': helpers.datetime_to_iso,
                'userRating': None,
                'viewCount': None,
                'viewedLeafCount': None,
                'year': None,
                'seasons': lambda e: helpers.get_attrs_to_dict(e.reload() if e.isPartialObject() else e,
                                                               self.return_attrs(e.type)[0])
            }
            return _show_attrs

        def season_attrs():
            _season_attrs = {
                'addedAt': helpers.datetime_to_iso,
                'art': None,
                'fields': {
                    'name': None,
                    'locked': None
                },
                'guid': None,
                'index': None,
                'key': None,
                'lastViewedAt': helpers.datetime_to_iso,
                'leafCount': None,
                'librarySectionID': None,
                'librarySectionKey': None,
                'librarySectionTitle': None,
                'parentGuid': None,
                'parentIndex': None,
                'parentKey': None,
                'parentRatingKey': None,
                'parentTheme': None,
                'parentThumb': None,
                'parentTitle': None,
                'ratingKey': None,
                'summary': None,
                'thumb': None,
                'thumbFile': lambda i: get_image(i, 'thumb', self.filename),
                'title': None,
                'titleSort': None,
                'type': None,
                'updatedAt': helpers.datetime_to_iso,
                'userRating': None,
                'viewCount': None,
                'viewedLeafCount': None,
                'episodes': lambda e: helpers.get_attrs_to_dict(e.reload() if e.isPartialObject() else e,
                                                                self.return_attrs(e.type)[0])
            }
            return _season_attrs

        def episode_attrs():
            _episode_attrs = {
                'addedAt': helpers.datetime_to_iso,
                'art': None,
                'chapterSource': None,
                'contentRating': None,
                'directors': {
                    'id': None,
                    'tag': None
                },
                'duration': None,
                'durationHuman': lambda i: helpers.human_duration(getattr(i, 'duration', 0), sig='dhm'),
                'fields': {
                    'name': None,
                    'locked': None
                },
                'grandparentArt': None,
                'grandparentGuid': None,
                'grandparentKey': None,
                'grandparentRatingKey': None,
                'grandparentTheme': None,
                'grandparentThumb': None,
                'grandparentTitle': None,
                'guid': None,
                'index': None,
                'key': None,
                'lastViewedAt': helpers.datetime_to_iso,
                'librarySectionID': None,
                'librarySectionKey': None,
                'librarySectionTitle': None,
                'locations': None,
                'media': {
                    'aspectRatio': None,
                    'audioChannels': None,
                    'audioCodec': None,
                    'audioProfile': None,
                    'bitrate': None,
                    'container': None,
                    'duration': None,
                    'height': None,
                    'id': None,
                    'has64bitOffsets': None,
                    'optimizedForStreaming': None,
                    'optimizedVersion': None,
                    'target': None,
                    'title': None,
                    'videoCodec': None,
                    'videoFrameRate': None,
                    'videoProfile': None,
                    'videoResolution': None,
                    'width': None,
                    'hdr': lambda i: get_any_hdr(i, self.return_attrs('episode')['media']),
                    'parts': {
                        'accessible': None,
                        'audioProfile': None,
                        'container': None,
                        'deepAnalysisVersion': None,
                        'duration': None,
                        'exists': None,
                        'file': None,
                        'has64bitOffsets': None,
                        'id': None,
                        'indexes': None,
                        'key': None,
                        'size': None,
                        'sizeHuman': lambda i: helpers.human_file_size(getattr(i, 'size', 0)),
                        'optimizedForStreaming': None,
                        'requiredBandwidths': lambda e: [int(b) for b in e.split(',')] if e else None,
                        'syncItemId': None,
                        'syncState': None,
                        'videoProfile': None,
                        'videoStreams': {
                            'codec': None,
                            'codecID': None,
                            'default': None,
                            'displayTitle': None,
                            'extendedDisplayTitle': None,
                            'id': None,
                            'index': None,
                            'language': None,
                            'languageCode': None,
                            'selected': None,
                            'streamType': None,
                            'title': None,
                            'type': None,
                            'bitDepth': None,
                            'bitrate': None,
                            'cabac': None,
                            'chromaLocation': None,
                            'chromaSubsampling': None,
                            'colorPrimaries': None,
                            'colorRange': None,
                            'colorSpace': None,
                            'colorTrc': None,
                            'duration': None,
                            'frameRate': None,
                            'frameRateMode': None,
                            'hasScalingMatrix': None,
                            'hdr': lambda i: helpers.is_hdr(getattr(i, 'bitDepth', 0), getattr(i, 'colorSpace', '')),
                            'height': None,
                            'level': None,
                            'pixelAspectRatio': None,
                            'pixelFormat': None,
                            'profile': None,
                            'refFrames': None,
                            'requiredBandwidths': lambda e: [int(b) for b in e.split(',')] if e else None,
                            'scanType': None,
                            'streamIdentifier': None,
                            'width': None
                        },
                        'audioStreams': {
                            'codec': None,
                            'codecID': None,
                            'default': None,
                            'displayTitle': None,
                            'extendedDisplayTitle': None,
                            'id': None,
                            'index': None,
                            'language': None,
                            'languageCode': None,
                            'selected': None,
                            'streamType': None,
                            'title': None,
                            'type': None,
                            'audioChannelLayout': None,
                            'bitDepth': None,
                            'bitrate': None,
                            'bitrateMode': None,
                            'channels': None,
                            'dialogNorm': None,
                            'duration': None,
                            'profile': None,
                            'requiredBandwidths': lambda e: [int(b) for b in e.split(',')] if e else None,
                            'samplingRate': None
                        },
                        'subtitleStreams': {
                            'codec': None,
                            'codecID': None,
                            'default': None,
                            'displayTitle': None,
                            'extendedDisplayTitle': None,
                            'id': None,
                            'index': None,
                            'language': None,
                            'languageCode': None,
                            'requiredBandwidths': lambda e: [int(b) for b in e.split(',')] if e else None,
                            'selected': None,
                            'streamType': None,
                            'title': None,
                            'type': None,
                            'forced': None,
                            'format': None,
                            'headerCompression': None,
                            'key': None
                        }
                    }
                },
                'originallyAvailableAt': partial(helpers.datetime_to_iso, to_date=True),
                'parentGuid': None,
                'parentIndex': None,
                'parentKey': None,
                'parentRatingKey': None,
                'parentThumb': None,
                'parentTitle': None,
                'rating': None,
                'ratingKey': None,
                'summary': None,
                'thumb': None,
                'title': None,
                'titleSort': None,
                'type': None,
                'updatedAt': helpers.datetime_to_iso,
                'userRating': None,
                'viewCount': None,
                'writers': {
                    'id': None,
                    'tag': None
                },
                'year': None
            }
            return _episode_attrs

        def artist_attrs():
            _artist_attrs = {
                'addedAt': helpers.datetime_to_iso,
                'art': None,
                'artFile': lambda i: get_image(i, 'art', self.filename),
                'collections': {
                    'id': None,
                    'tag': None
                },
                'countries': {
                    'id': None,
                    'tag': None
                },
                'fields': {
                    'name': None,
                    'locked': None
                },
                'genres': {
                    'id': None,
                    'tag': None
                },
                'guid': None,
                'index': None,
                'key': None,
                'lastViewedAt': helpers.datetime_to_iso,
                'librarySectionID': None,
                'librarySectionKey': None,
                'librarySectionTitle': None,
                'locations': None,
                'moods': {
                    'id': None,
                    'tag': None
                },
                'rating': None,
                'ratingKey': None,
                'styles': {
                    'id': None,
                    'tag': None
                },
                'summary': None,
                'thumb': None,
                'thumbFile': lambda i: get_image(i, 'thumb', self.filename),
                'title': None,
                'titleSort': None,
                'type': None,
                'updatedAt': helpers.datetime_to_iso,
                'userRating': None,
                'viewCount': None,
                'albums': lambda e: helpers.get_attrs_to_dict(e.reload() if e.isPartialObject() else e,
                                                              self.return_attrs(e.type))
            }
            return _artist_attrs

        def album_attrs():
            _album_attrs = {
                'addedAt': helpers.datetime_to_iso,
                'art': None,
                'artFile': lambda i: get_image(i, 'art', self.filename),
                'collections': {
                    'id': None,
                    'tag': None
                },
                'fields': {
                    'name': None,
                    'locked': None
                },
                'genres': {
                    'id': None,
                    'tag': None
                },
                'guid': None,
                'index': None,
                'key': None,
                'labels': {
                    'id': None,
                    'tag': None
                },
                'lastViewedAt': helpers.datetime_to_iso,
                'leafCount': None,
                'librarySectionID': None,
                'librarySectionKey': None,
                'librarySectionTitle': None,
                'loudnessAnalysisVersion': None,
                'moods': {
                    'id': None,
                    'tag': None
                },
                'originallyAvailableAt': partial(helpers.datetime_to_iso, to_date=True),
                'parentGuid': None,
                'parentKey': None,
                'parentRatingKey': None,
                'parentThumb': None,
                'parentTitle': None,
                'rating': None,
                'ratingKey': None,
                'styles': {
                    'id': None,
                    'tag': None
                },
                'summary': None,
                'thumb': None,
                'thumbFile': lambda i: get_image(i, 'thumb', self.filename),
                'title': None,
                'titleSort': None,
                'type': None,
                'updatedAt': helpers.datetime_to_iso,
                'userRating': None,
                'viewCount': None,
                'viewedLeafCount': None,
                'tracks': lambda e: helpers.get_attrs_to_dict(e.reload() if e.isPartialObject() else e,
                                                              self.return_attrs(e.type))
            }
            return _album_attrs

        def track_attrs():
            _track_attrs = {
                'addedAt': helpers.datetime_to_iso,
                'art': None,
                'duration': None,
                'durationHuman': lambda i: helpers.human_duration(getattr(i, 'duration', 0), sig='dhm'),
                'fields': {
                    'name': None,
                    'locked': None
                },
                'grandparentArt': None,
                'grandparentGuid': None,
                'grandparentKey': None,
                'grandparentRatingKey': None,
                'grandparentThumb': None,
                'grandparentTitle': None,
                'guid': None,
                'index': None,
                'key': None,
                'lastViewedAt': helpers.datetime_to_iso,
                'librarySectionID': None,
                'librarySectionKey': None,
                'librarySectionTitle': None,
                'locations': None,
                'media': {
                    'audioChannels': None,
                    'audioCodec': None,
                    'audioProfile': None,
                    'bitrate': None,
                    'container': None,
                    'duration': None,
                    'id': None,
                    'title': None,
                    'parts': {
                        'accessible': None,
                        'audioProfile': None,
                        'container': None,
                        'deepAnalysisVersion': None,
                        'duration': None,
                        'exists': None,
                        'file': None,
                        'hasThumbnail': None,
                        'id': None,
                        'key': None,
                        'size': None,
                        'sizeHuman': lambda i: helpers.human_file_size(getattr(i, 'size', 0)),
                        'requiredBandwidths': lambda e: [int(b) for b in e.split(',')] if e else None,
                        'syncItemId': None,
                        'syncState': None,
                        'audioStreams': {
                            'codec': None,
                            'codecID': None,
                            'default': None,
                            'displayTitle': None,
                            'extendedDisplayTitle': None,
                            'id': None,
                            'index': None,
                            'selected': None,
                            'streamType': None,
                            'title': None,
                            'type': None,
                            'albumGain': None,
                            'albumPeak': None,
                            'albumRange': None,
                            'audioChannelLayout': None,
                            'bitrate': None,
                            'channels': None,
                            'duration': None,
                            'endRamp': None,
                            'gain': None,
                            'loudness': None,
                            'lra': None,
                            'peak': None,
                            'requiredBandwidths': lambda e: [int(b) for b in e.split(',')] if e else None,
                            'samplingRate': None,
                            'startRamp': None,
                        },
                        'lyricStreams': {
                            'codec': None,
                            'codecID': None,
                            'default': None,
                            'displayTitle': None,
                            'extendedDisplayTitle': None,
                            'id': None,
                            'index': None,
                            'minLines': None,
                            'provider': None,
                            'streamType': None,
                            'timed': None,
                            'title': None,
                            'type': None,
                            'format': None,
                            'key': None
                        }
                    }
                },
                'moods': {
                    'id': None,
                    'tag': None
                },
                'originalTitle': None,
                'parentGuid': None,
                'parentIndex': None,
                'parentKey': None,
                'parentRatingKey': None,
                'parentThumb': None,
                'parentTitle': None,
                'ratingCount': None,
                'ratingKey': None,
                'summary': None,
                'thumb': None,
                'title': None,
                'titleSort': None,
                'type': None,
                'updatedAt': helpers.datetime_to_iso,
                'userRating': None,
                'viewCount': None,
                'year': None,
            }
            return _track_attrs

        def photo_album_attrs():
            _photo_album_attrs = {
                # For some reason photos needs to be first,
                # otherwise the photo album ratingKey gets
                # clobbered by the first photo's ratingKey
                'photos': lambda e: helpers.get_attrs_to_dict(e.reload() if e.isPartialObject() else e,
                                                              self.return_attrs(e.type)),
                'addedAt': helpers.datetime_to_iso,
                'art': None,
                'composite': None,
                'fields': {
                    'name': None,
                    'locked': None
                },
                'guid': None,
                'index': None,
                'key': None,
                'librarySectionID': None,
                'librarySectionKey': None,
                'librarySectionTitle': None,
                'ratingKey': None,
                'summary': None,
                'thumb': None,
                'title': None,
                'titleSort': None,
                'type': None,
                'updatedAt': helpers.datetime_to_iso
            }
            return _photo_album_attrs

        def photo_attrs():
            _photo_attrs = {
                'addedAt': helpers.datetime_to_iso,
                'createdAtAccuracy': None,
                'createdAtTZOffset': None,
                'fields': {
                    'name': None,
                    'locked': None
                },
                'guid': None,
                'index': None,
                'key': None,
                'librarySectionID': None,
                'librarySectionKey': None,
                'librarySectionTitle': None,
                'originallyAvailableAt': partial(helpers.datetime_to_iso, to_date=True),
                'parentGuid': None,
                'parentIndex': None,
                'parentKey': None,
                'parentRatingKey': None,
                'parentThumb': None,
                'parentTitle': None,
                'ratingKey': None,
                'summary': None,
                'thumb': None,
                'title': None,
                'titleSort': None,
                'type': None,
                'updatedAt': helpers.datetime_to_iso,
                'year': None,
                'media': {
                    'aperture': None,
                    'aspectRatio': None,
                    'container': None,
                    'height': None,
                    'id': None,
                    'iso': None,
                    'lens': None,
                    'make': None,
                    'model': None,
                    'width': None,
                    'parts': {
                        'accessible': None,
                        'container': None,
                        'exists': None,
                        'file': None,
                        'id': None,
                        'key': None,
                        'size': None,
                        'sizeHuman': lambda i: helpers.human_file_size(getattr(i, 'size', 0)),
                    }
                },
                'tag': {
                    'id': None,
                    'tag': None,
                    'title': None
                }
            }
            return _photo_attrs

        def collection_attrs():
            _collection_attrs = {
                'addedAt': helpers.datetime_to_iso,
                'art': None,
                'artFile': lambda i: get_image(i, 'art', self.filename),
                'childCount': None,
                'collectionMode': None,
                'collectionSort': None,
                'contentRating': None,
                'fields': {
                    'name': None,
                    'locked': None
                },
                'guid': None,
                'index': None,
                'key': None,
                'librarySectionID': None,
                'librarySectionKey': None,
                'librarySectionTitle': None,
                'maxYear': None,
                'minYear': None,
                'ratingKey': None,
                'subtype': None,
                'summary': None,
                'thumb': None,
                'thumbFile': lambda i: get_image(i, 'thumb', self.filename),
                'title': None,
                'type': None,
                'updatedAt': helpers.datetime_to_iso,
                'children': lambda e: helpers.get_attrs_to_dict(e.reload() if e.isPartialObject() else e,
                                                                self.return_attrs(e.type))
            }
            return _collection_attrs

        def playlist_attrs():
            _playlist_attrs = {
                'addedAt': helpers.datetime_to_iso,
                'composite': None,
                'duration': None,
                'durationHuman': lambda i: helpers.human_duration(getattr(i, 'duration', 0), sig='dhm'),
                'guid': None,
                'key': None,
                'leafCount': None,
                'playlistType': None,
                'ratingKey': None,
                'smart': None,
                'summary': None,
                'title': None,
                'type': None,
                'updatedAt': helpers.datetime_to_iso,
                'items': lambda e: helpers.get_attrs_to_dict(e.reload() if e.isPartialObject() else e,
                                                             self.return_attrs(e.type))
            }
            return _playlist_attrs

        _media_types = {
            'movie': movie_attrs,
            'show': show_attrs,
            'season': season_attrs,
            'episode': episode_attrs,
            'artist': artist_attrs,
            'album': album_attrs,
            'track': track_attrs,
            'photo album': photo_album_attrs,
            'photo': photo_attrs,
            'collection': collection_attrs,
            'playlist': playlist_attrs,
        }

        return _media_types[media_type]()

    def return_levels(self, media_type):

        def movie_levels():
            _media_type = 'movie'

            _movie_levels = [
                {
                    1: [
                        'ratingKey', 'title', 'titleSort', 'originalTitle', 'originallyAvailableAt', 'year', 'addedAt',
                        'rating', 'ratingImage', 'audienceRating', 'audienceRatingImage', 'userRating', 'contentRating',
                        'studio', 'tagline', 'summary', 'guid', 'duration', 'durationHuman', 'type'
                    ],
                    2: [
                        'directors.tag', 'writers.tag', 'producers.tag', 'roles.tag', 'roles.role',
                        'countries.tag', 'genres.tag', 'collections.tag', 'labels.tag',
                        'fields.name', 'fields.locked'
                    ],
                    3: [
                        'art', 'thumb', 'key', 'chapterSource',
                        'chapters.tag', 'chapters.index', 'chapters.start', 'chapters.end', 'chapters.thumb',
                        'updatedAt', 'lastViewedAt', 'viewCount'
                    ],
                    9: self._get_all_metadata_attr(_media_type)
                },
                {
                    1: [
                        'locations', 'media.aspectRatio', 'media.audioChannels', 'media.audioCodec', 'media.audioProfile',
                        'media.bitrate', 'media.container', 'media.duration', 'media.height', 'media.width',
                        'media.videoCodec', 'media.videoFrameRate', 'media.videoProfile', 'media.videoResolution',
                        'media.optimizedVersion', 'media.hdr'
                    ],
                    2: [
                        'media.parts.accessible', 'media.parts.exists', 'media.parts.file', 'media.parts.duration',
                        'media.parts.container', 'media.parts.indexes', 'media.parts.size', 'media.parts.sizeHuman',
                        'media.parts.audioProfile', 'media.parts.videoProfile',
                        'media.parts.optimizedForStreaming', 'media.parts.deepAnalysisVersion'
                    ],
                    3: [
                        'media.parts.videoStreams.codec', 'media.parts.videoStreams.bitrate',
                        'media.parts.videoStreams.language', 'media.parts.videoStreams.languageCode',
                        'media.parts.videoStreams.title', 'media.parts.videoStreams.displayTitle',
                        'media.parts.videoStreams.extendedDisplayTitle', 'media.parts.videoStreams.hdr',
                        'media.parts.videoStreams.bitDepth', 'media.parts.videoStreams.colorSpace',
                        'media.parts.videoStreams.frameRate', 'media.parts.videoStreams.level',
                        'media.parts.videoStreams.profile', 'media.parts.videoStreams.refFrames',
                        'media.parts.videoStreams.scanType', 'media.parts.videoStreams.default',
                        'media.parts.videoStreams.height', 'media.parts.videoStreams.width',
                        'media.parts.audioStreams.codec', 'media.parts.audioStreams.bitrate',
                        'media.parts.audioStreams.language', 'media.parts.audioStreams.languageCode',
                        'media.parts.audioStreams.title', 'media.parts.audioStreams.displayTitle',
                        'media.parts.audioStreams.extendedDisplayTitle', 'media.parts.audioStreams.bitDepth',
                        'media.parts.audioStreams.channels', 'media.parts.audioStreams.audioChannelLayout',
                        'media.parts.audioStreams.profile', 'media.parts.audioStreams.samplingRate',
                        'media.parts.audioStreams.default',
                        'media.parts.subtitleStreams.codec', 'media.parts.subtitleStreams.format',
                        'media.parts.subtitleStreams.language', 'media.parts.subtitleStreams.languageCode',
                        'media.parts.subtitleStreams.title', 'media.parts.subtitleStreams.displayTitle',
                        'media.parts.subtitleStreams.extendedDisplayTitle', 'media.parts.subtitleStreams.forced',
                        'media.parts.subtitleStreams.default'
                    ],
                    9: [
                        'locations', 'media'
                    ]
                }
            ]
            return _movie_levels

        def show_levels():
            _media_type = 'show'
            _child_type = self.CHILDREN[_media_type]
            _child_attr = _child_type + 's.'
            _child_levels = self.return_levels(_child_type)

            _show_levels = [
                {
                    1: [
                           'ratingKey', 'title', 'titleSort', 'originallyAvailableAt', 'year', 'addedAt',
                           'rating', 'userRating', 'contentRating',
                           'studio', 'summary', 'guid', 'duration', 'durationHuman', 'type', 'childCount'
                       ] + [_child_attr + attr for attr in _child_levels[0][1]],
                    2: [
                           'roles.tag', 'roles.role',
                           'genres.tag', 'collections.tag', 'labels.tag',
                           'fields.name', 'fields.locked'
                       ] + [_child_attr + attr for attr in _child_levels[0][2]],
                    3: [
                           'art', 'thumb', 'banner', 'theme', 'key',
                           'updatedAt', 'lastViewedAt', 'viewCount'
                       ] + [_child_attr + attr for attr in _child_levels[0][3]],
                    9: self._get_all_metadata_attr(_media_type)
                },
                {
                    l: [_child_attr + attr for attr in _child_levels[1][l]] for l in self.LEVELS
                }
            ]
            return _show_levels

        def season_levels():
            _media_type = 'season'
            _child_type = self.CHILDREN[_media_type]
            _child_attr = _child_type + 's.'
            _child_levels = self.return_levels(_child_type)

            _season_levels = [
                {
                    1: [
                           'ratingKey', 'title', 'titleSort', 'addedAt',
                           'userRating',
                           'summary', 'guid', 'type', 'index',
                           'parentTitle', 'parentRatingKey', 'parentGuid'
                       ] + [_child_attr + attr for attr in _child_levels[0][1]],
                    2: [
                           'fields.name', 'fields.locked'
                       ] + [_child_attr + attr for attr in _child_levels[0][2]],
                    3: [
                           'art', 'thumb', 'key',
                           'updatedAt', 'lastViewedAt', 'viewCount',
                           'parentKey', 'parentTheme', 'parentThumb'
                       ] + [_child_attr + attr for attr in _child_levels[0][3]],
                    9: self._get_all_metadata_attr(_media_type)
                },
                {
                    l: [_child_attr + attr for attr in _child_levels[1][l]] for l in self.LEVELS
                }
            ]
            return _season_levels

        def episode_levels():
            _media_type = 'episode'

            _episode_levels = [
                {
                    1: [
                        'ratingKey', 'title', 'titleSort', 'originallyAvailableAt', 'year', 'addedAt',
                        'rating', 'userRating', 'contentRating',
                        'summary', 'guid', 'duration', 'durationHuman', 'type', 'index',
                        'parentTitle', 'parentRatingKey', 'parentGuid', 'parentIndex',
                        'grandparentTitle', 'grandparentRatingKey', 'grandparentGuid'
                    ],
                    2: [
                        'directors.tag', 'writers.tag',
                        'fields.name', 'fields.locked'
                    ],
                    3: [
                        'art', 'thumb', 'key', 'chapterSource',
                        'updatedAt', 'lastViewedAt', 'viewCount',
                        'parentThumb', 'parentKey',
                        'grandparentArt', 'grandparentThumb', 'grandparentTheme', 'grandparentKey'
                    ],
                    9: self._get_all_metadata_attr(_media_type)
                },
                {
                    1: [
                        'locations', 'media.aspectRatio', 'media.audioChannels', 'media.audioCodec', 'media.audioProfile',
                        'media.bitrate', 'media.container', 'media.duration', 'media.height', 'media.width',
                        'media.videoCodec', 'media.videoFrameRate', 'media.videoProfile', 'media.videoResolution',
                        'media.optimizedVersion', 'media.hdr'
                    ],
                    2: [
                        'media.parts.accessible', 'media.parts.exists', 'media.parts.file', 'media.parts.duration',
                        'media.parts.container', 'media.parts.indexes', 'media.parts.size', 'media.parts.sizeHuman',
                        'media.parts.audioProfile', 'media.parts.videoProfile',
                        'media.parts.optimizedForStreaming', 'media.parts.deepAnalysisVersion'
                    ],
                    3: [
                        'media.parts.videoStreams.codec', 'media.parts.videoStreams.bitrate',
                        'media.parts.videoStreams.language', 'media.parts.videoStreams.languageCode',
                        'media.parts.videoStreams.title', 'media.parts.videoStreams.displayTitle',
                        'media.parts.videoStreams.extendedDisplayTitle', 'media.parts.videoStreams.hdr',
                        'media.parts.videoStreams.bitDepth', 'media.parts.videoStreams.colorSpace',
                        'media.parts.videoStreams.frameRate', 'media.parts.videoStreams.level',
                        'media.parts.videoStreams.profile', 'media.parts.videoStreams.refFrames',
                        'media.parts.videoStreams.scanType', 'media.parts.videoStreams.default',
                        'media.parts.videoStreams.height', 'media.parts.videoStreams.width',
                        'media.parts.audioStreams.codec', 'media.parts.audioStreams.bitrate',
                        'media.parts.audioStreams.language', 'media.parts.audioStreams.languageCode',
                        'media.parts.audioStreams.title', 'media.parts.audioStreams.displayTitle',
                        'media.parts.audioStreams.extendedDisplayTitle', 'media.parts.audioStreams.bitDepth',
                        'media.parts.audioStreams.channels', 'media.parts.audioStreams.audioChannelLayout',
                        'media.parts.audioStreams.profile', 'media.parts.audioStreams.samplingRate',
                        'media.parts.audioStreams.default',
                        'media.parts.subtitleStreams.codec', 'media.parts.subtitleStreams.format',
                        'media.parts.subtitleStreams.language', 'media.parts.subtitleStreams.languageCode',
                        'media.parts.subtitleStreams.title', 'media.parts.subtitleStreams.displayTitle',
                        'media.parts.subtitleStreams.extendedDisplayTitle', 'media.parts.subtitleStreams.forced',
                        'media.parts.subtitleStreams.default'
                    ],
                    9: [
                        'locations', 'media'
                    ]
                }
            ]
            return _episode_levels

        def artist_levels():
            _media_type = 'artist'
            _child_type = self.CHILDREN[_media_type]
            _child_attr = _child_type + 's.'
            _child_levels = self.return_levels(_child_type)

            _artist_levels = [
                {
                    1: [
                           'ratingKey', 'title', 'titleSort', 'addedAt',
                           'rating', 'userRating',
                           'summary', 'guid', 'type',
                       ] + [_child_attr + attr for attr in _child_levels[0][1]],
                    2: [
                           'collections.tag', 'genres.tag', 'countries.tag', 'moods.tag', 'styles.tag',
                           'fields.name', 'fields.locked'
                       ] + [_child_attr + attr for attr in _child_levels[0][2]],
                    3: [
                           'art', 'thumb', 'key',
                           'updatedAt', 'lastViewedAt', 'viewCount'
                       ] + [_child_attr + attr for attr in _child_levels[0][3]],
                    9: self._get_all_metadata_attr(_media_type)
                },
                {
                    l: [_child_attr + attr for attr in _child_levels[1][l]] for l in self.LEVELS
                }
            ]
            return _artist_levels

        def album_levels():
            _media_type = 'album'
            _child_type = self.CHILDREN[_media_type]
            _child_attr = _child_type + 's.'
            _child_levels = self.return_levels(_child_type)

            _album_levels = [
                {
                    1: [
                           'ratingKey', 'title', 'titleSort', 'originallyAvailableAt', 'addedAt',
                           'rating', 'userRating',
                           'summary', 'guid', 'type', 'index',
                           'parentTitle', 'parentRatingKey', 'parentGuid'
                       ] + [_child_attr + attr for attr in _child_levels[0][1]],
                    2: [
                           'collections.tag', 'genres.tag', 'labels.tag', 'moods.tag', 'styles.tag',
                           'fields.name', 'fields.locked'
                       ] + [_child_attr + attr for attr in _child_levels[0][2]],
                    3: [
                           'art', 'thumb', 'key',
                           'updatedAt', 'lastViewedAt', 'viewCount',
                           'parentKey', 'parentThumb'
                       ] + [_child_attr + attr for attr in _child_levels[0][3]],
                    9: self._get_all_metadata_attr(_media_type)
                },
                {
                    l: [_child_attr + attr for attr in _child_levels[1][l]] for l in self.LEVELS
                }
            ]
            return _album_levels

        def track_levels():
            _media_type = 'track'

            _track_levels = [
                {
                    1: [
                        'ratingKey', 'title', 'titleSort', 'originalTitle', 'year', 'addedAt',
                        'userRating', 'ratingCount',
                        'summary', 'guid', 'duration', 'durationHuman', 'type', 'index',
                        'parentTitle', 'parentRatingKey', 'parentGuid', 'parentIndex',
                        'grandparentTitle', 'grandparentRatingKey', 'grandparentGuid'
                    ],
                    2: [
                        'moods.tag', 'writers.tag',
                        'fields.name', 'fields.locked'
                    ],
                    3: [
                        'art', 'thumb', 'key',
                        'updatedAt', 'lastViewedAt', 'viewCount',
                        'parentThumb', 'parentKey',
                        'grandparentArt', 'grandparentThumb', 'grandparentKey'
                    ],
                    9: self._get_all_metadata_attr(_media_type)
                },
                {
                    1: [
                        'locations', 'media.audioChannels', 'media.audioCodec',
                        'media.audioProfile',
                        'media.bitrate', 'media.container', 'media.duration'
                    ],
                    2: [
                        'media.parts.accessible', 'media.parts.exists', 'media.parts.file', 'media.parts.duration',
                        'media.parts.container', 'media.parts.size', 'media.parts.sizeHuman',
                        'media.parts.audioProfile',
                        'media.parts.deepAnalysisVersion', 'media.parts.hasThumbnail'
                    ],
                    3: [
                        'media.parts.audioStreams.codec', 'media.parts.audioStreams.bitrate',
                        'media.parts.audioStreams.title', 'media.parts.audioStreams.displayTitle',
                        'media.parts.audioStreams.extendedDisplayTitle',
                        'media.parts.audioStreams.channels', 'media.parts.audioStreams.audioChannelLayout',
                        'media.parts.audioStreams.samplingRate',
                        'media.parts.audioStreams.default',
                        'media.parts.audioStreams.albumGain', 'media.parts.audioStreams.albumPeak',
                        'media.parts.audioStreams.albumRange',
                        'media.parts.audioStreams.loudness', 'media.parts.audioStreams.gain',
                        'media.parts.audioStreams.lra', 'media.parts.audioStreams.peak',
                        'media.parts.audioStreams.startRamp', 'media.parts.audioStreams.endRamp',
                        'media.parts.lyricStreams.codec', 'media.parts.lyricStreams.format',
                        'media.parts.lyricStreams.title', 'media.parts.lyricStreams.displayTitle',
                        'media.parts.lyricStreams.extendedDisplayTitle',
                        'media.parts.lyricStreams.default', 'media.parts.lyricStreams.minLines',
                        'media.parts.lyricStreams.provider', 'media.parts.lyricStreams.timed',
                    ],
                    9: [
                        'locations', 'media'
                    ]
                }
            ]
            return _track_levels

        def photo_album_levels():
            _media_type = 'photo album'
            _child_type = self.CHILDREN[_media_type]
            _child_attr = _child_type + 's.'
            _child_levels = self.return_levels(_child_type)

            _photo_album_levels = [
                {
                    1: [
                           'ratingKey', 'title', 'titleSort', 'addedAt',
                           'summary', 'guid', 'type', 'index',
                       ] + [_child_attr + attr for attr in _child_levels[0][1]],
                    2: [
                           'fields.name', 'fields.locked'
                       ] + [_child_attr + attr for attr in _child_levels[0][2]],
                    3: [
                           'art', 'thumb', 'key',
                           'updatedAt'
                       ] + [_child_attr + attr for attr in _child_levels[0][3]],
                    9: self._get_all_metadata_attr(_media_type)
                },
                {
                    l: [_child_attr + attr for attr in _child_levels[1][l]] for l in self.LEVELS
                }
            ]
            return _photo_album_levels

        def photo_levels():
            _media_type = 'photo'

            _photo_levels = [
                {
                    1: [
                        'ratingKey', 'title', 'titleSort', 'year', 'originallyAvailableAt', 'addedAt',
                        'summary', 'guid', 'type', 'index',
                        'parentTitle', 'parentRatingKey', 'parentGuid', 'parentIndex',
                        'createdAtAccuracy', 'createdAtTZOffset'
                    ],
                    2: [
                        'tag.tag', 'tag.title'
                    ],
                    3: [
                        'thumb', 'key',
                        'updatedAt',
                        'parentThumb', 'parentKey'
                    ],
                    9: self._get_all_metadata_attr(_media_type)
                },
                {
                    1: [
                        'media.aspectRatio', 'media.aperture',
                        'media.container', 'media.height', 'media.width',
                        'media.iso', 'media.lens', 'media.make', 'media.model'
                    ],
                    2: [
                        'media.parts.accessible', 'media.parts.exists', 'media.parts.file',
                        'media.parts.container', 'media.parts.size', 'media.parts.sizeHuman'
                    ],
                    3: [
                    ],
                    9: [
                        'media'
                    ]
                }
            ]
            return _photo_levels

        def collection_levels():
            _collection_levels = []
            return _collection_levels

        def playlist_levels():
            _playlist_levels = []
            return _playlist_levels

        _media_types = {
            'movie': movie_levels,
            'show': show_levels,
            'season': season_levels,
            'episode': episode_levels,
            'artist': artist_levels,
            'album': album_levels,
            'track': track_levels,
            'photo album': photo_album_levels,
            'photo': photo_levels,
            'collection': collection_levels,
            'playlist': playlist_levels
        }

        return _media_types[media_type]()

    def export(self):
        if not self.section_id and not self.rating_key:
            logger.error("Tautulli Exporter :: Export called but no section_id or rating_key provided.")
            return
        elif self.rating_key and not str(self.rating_key).isdigit():
            logger.error("Tautulli Exporter :: Export called with invalid rating_key '%s'.", self.rating_key)
            return
        elif self.section_id and not str(self.section_id).isdigit():
            logger.error("Tautulli Exporter :: Export called with invalid section_id '%s'.", self.section_id)
            return
        elif not self.metadata_level:
            logger.error("Tautulli Exporter :: Export called with invalid metadata_level '%s'.", self.metadata_level)
            return
        elif not self.media_info_level:
            logger.error("Tautulli Exporter :: Export called with invalid media_info_level '%s'.", self.media_info_level)
            return
        elif self.file_format not in ('json', 'csv'):
            logger.error("Tautulli Exporter :: Export called but invalid file_format '%s' provided.", self.file_format)
            return

        plex = Plex(plexpy.CONFIG.PMS_URL, plexpy.CONFIG.PMS_TOKEN)

        if self.rating_key:
            logger.debug(
                "Tautulli Exporter :: Export called with rating_key %s, "
                "metadata_level %d, media_info_level %d, include_images %s",
                self.rating_key, self.metadata_level, self.media_info_level, self.include_images)

            item = plex.get_item(self.rating_key)
            self.media_type = item.type

            if self.media_type != 'playlist':
                self.section_id = item.librarySectionID

            if self.media_type in ('season', 'episode', 'album', 'track'):
                item_title = item._defaultSyncTitle()
            else:
                item_title = item.title

            if self.media_type == 'photo' and item.TAG == 'Directory':
                self.media_type = 'photo album'

            filename = '{} - {} [{}].{}'.format(
                self.media_type.title(), item_title, self.rating_key,
                helpers.timestamp_to_YMDHMS(self.timestamp))

            self.items = [item]

        elif self.section_id:
            logger.debug(
                "Tautulli Exporter :: Export called with section_id %s, metadata_level %d, media_info_level %d",
                self.section_id, self.metadata_level, self.media_info_level)

            library = plex.get_library(str(self.section_id))
            self.media_type = library.type
            library_title = library.title

            filename = 'Library - {} [{}].{}'.format(
                library_title, self.section_id,
                helpers.timestamp_to_YMDHMS(self.timestamp))

            self.items = library.all()

        else:
            return

        if self.media_type not in self.MEDIA_TYPES:
            logger.error("Tautulli Exporter :: Cannot export media type '%s'", self.media_type)
            return

        media_attrs = self.return_attrs(self.media_type)
        metadata_level_attrs, media_info_level_attrs = self.return_levels(self.media_type)

        if self.metadata_level not in metadata_level_attrs:
            logger.error("Tautulli Exporter :: Export called with invalid metadata_level '%s'.", self.metadata_level)
            return
        elif self.media_info_level not in media_info_level_attrs:
            logger.error("Tautulli Exporter :: Export called with invalid media_info_level '%s'.", self.media_info_level)
            return

        export_attrs_list = []
        export_attrs_set = set()

        for level, attrs in metadata_level_attrs.items():
            if level <= self.metadata_level:
                export_attrs_set.update(attrs)

        for level, attrs in media_info_level_attrs.items():
            if level <= self.media_info_level:
                export_attrs_set.update(attrs)

        if self.include_images:
            for image_attr in ('artFile', 'thumbFile'):
                if image_attr in media_attrs:
                    export_attrs_set.add(image_attr)
            if self.media_type in ('show', 'artist'):
                child_media_type = self.CHILDREN[self.media_type]
                child_media_attrs = self.return_attrs(child_media_type)
                for image_attr in ('artFile', 'thumbFile'):
                    if image_attr in child_media_attrs:
                        export_attrs_set.add(child_media_type + 's.' + image_attr)

        for attr in export_attrs_set:
            value = self._get_attr_value(media_attrs, attr)
            if not value:
                continue
            export_attrs_list.append(value)

        export_attrs = reduce(helpers.dict_merge, export_attrs_list)

        self.filename = '{}.{}'.format(helpers.clean_filename(filename), self.file_format)

        self.export_id = self.add_export()

        if not self.export_id:
            logger.error("Tautulli Exporter :: Failed to export '%s'", self.filename)
            return

        threading.Thread(target=self._real_export,
                         kwargs={'attrs': export_attrs}).start()

        return True

    def _real_export(self, attrs):
        logger.info("Tautulli Exporter :: Starting export for '%s'...", self.filename)

        filepath = get_export_filepath(self.filename)

        part = partial(helpers.get_attrs_to_dict, attrs=attrs)
        pool = ThreadPool(processes=4)

        try:
            result = pool.map(part, self.items)

            if self.file_format == 'json':
                json_data = json.dumps(result, indent=4, ensure_ascii=False, sort_keys=True)
                with open(filepath, 'w', encoding='utf-8') as outfile:
                    outfile.write(json_data)

            elif self.file_format == 'csv':
                flatten_result = helpers.flatten_dict(result)
                flatten_attrs = set().union(*flatten_result)
                with open(filepath, 'w', encoding='utf-8', newline='') as outfile:
                    writer = csv.DictWriter(outfile, sorted(flatten_attrs))
                    writer.writeheader()
                    writer.writerows(flatten_result)

            self.file_size = os.path.getsize(filepath)

            if self.include_images:
                images_folder = get_export_filepath(self.filename, images=True)
                if os.path.exists(images_folder):
                    for f in os.listdir(images_folder):
                        image_path = os.path.join(images_folder, f)
                        if os.path.isfile(image_path):
                            self.file_size += os.path.getsize(image_path)

            self.success = True
            logger.info("Tautulli Exporter :: Successfully exported to '%s'", filepath)

        except Exception as e:
            logger.error("Tautulli Exporter :: Failed to export '%s': %s", self.filename, e)
            import traceback
            traceback.print_exc()

        finally:
            pool.close()
            pool.join()
            self.set_export_state()

    def add_export(self):
        keys = {'timestamp': self.timestamp,
                'section_id': self.section_id,
                'rating_key': self.rating_key,
                'media_type': self.media_type}

        values = {'file_format': self.file_format,
                  'filename': self.filename,
                  'include_images': self.include_images}

        db = database.MonitorDatabase()
        try:
            db.upsert(table_name='exports', key_dict=keys, value_dict=values)
            return db.last_insert_id()
        except Exception as e:
            logger.error("Tautulli Exporter :: Unable to save export to database: %s", e)
            return False

    def set_export_state(self):
        if self.success:
            complete = 1
        else:
            complete = -1

        keys = {'id': self.export_id}
        values = {'complete': complete,
                  'file_size': self.file_size}

        db = database.MonitorDatabase()
        db.upsert(table_name='exports', key_dict=keys, value_dict=values)

    def _get_attr_value(self, media_attrs, attr):
        try:
            return helpers.get_dict_value_by_path(media_attrs, attr)
        except KeyError:
            pass
        except TypeError:
            if '.' in attr:
                sub_media_type, sub_attr = attr.split('.', maxsplit=1)
                if sub_media_type[:-1] in self.MEDIA_TYPES:
                    sub_media_attrs = self.return_attrs(sub_media_type[:-1])
                    return {sub_media_type: self._get_attr_value(sub_media_attrs, sub_attr)}

        logger.warn("Tautulli Exporter :: Unknown export attribute '%s', skipping...", attr)


def get_any_hdr(obj, root):
    attrs = helpers.get_dict_value_by_path(root, 'parts.videoStreams.hdr')
    media = helpers.get_attrs_to_dict(obj, attrs)
    return any(vs.get('hdr') for p in media.get('parts', []) for vs in p.get('videoStreams', []))


def get_image(item, image, export_filename):
    media_type = item.type
    rating_key = item.ratingKey

    if media_type in ('season', 'episode', 'album', 'track'):
        item_title = item._defaultSyncTitle()
    else:
        item_title = item.title

    folder = get_export_filepath(export_filename, images=True)
    filename = helpers.clean_filename('{} [{}].{}.jpg'.format(item_title, rating_key, image))
    filepath = os.path.join(folder, filename)

    if not os.path.exists(folder):
        os.makedirs(folder)

    image_url = None
    if image == 'art':
        image_url = item.artUrl
    elif image == 'thumb':
        image_url = item.thumbUrl

    if not image_url:
        return

    r = requests.get(image_url, stream=True)
    if r.status_code == 200:
        with open(filepath, 'wb') as outfile:
            for chunk in r:
                outfile.write(chunk)

        return filepath


def get_export(export_id):
    db = database.MonitorDatabase()
    result = db.select_single('SELECT filename, file_format, include_images, complete '
                              'FROM exports WHERE id = ?',
                              [export_id])

    if result:
        result['exists'] = check_export_exists(result['filename'])

    return result


def delete_export(export_id):
    db = database.MonitorDatabase()
    if str(export_id).isdigit():
        export_data = get_export(export_id=export_id)

        logger.info("Tautulli Exporter :: Deleting export_id %s from the database.", export_id)
        result = db.action('DELETE FROM exports WHERE id = ?', args=[export_id])

        if export_data and export_data['exists']:
            filepath = get_export_filepath(export_data['filename'])
            logger.info("Tautulli Exporter :: Deleting exported file from '%s'.", filepath)
            try:
                os.remove(filepath)
                if export_data['include_images']:
                    images_folder = get_export_filepath(export_data['filename'], images=True)
                    if os.path.exists(images_folder):
                        shutil.rmtree(images_folder)
            except OSError as e:
                logger.error("Tautulli Exporter :: Failed to delete exported file '%s': %s", filepath, e)
        return True
    else:
        return False


def delete_all_exports():
    db = database.MonitorDatabase()
    result = db.select('SELECT filename, include_images FROM exports')

    logger.info("Tautulli Exporter :: Deleting all exports from the database.")

    deleted_files = True
    for row in result:
        if check_export_exists(row['filename']):
            filepath = get_export_filepath(row['filename'])
            try:
                os.remove(filepath)
                if row['include_images']:
                    images_folder = get_export_filepath(row['filename'], images=True)
                    if os.path.exists(images_folder):
                        shutil.rmtree(images_folder)
            except OSError as e:
                logger.error("Tautulli Exporter :: Failed to delete exported file '%s': %s", filepath, e)
                deleted_files = False
                break

    if deleted_files:
        database.delete_exports()
        return True


def cancel_exports():
    db = database.MonitorDatabase()
    db.action('UPDATE exports SET complete = -1 WHERE complete = 0')


def get_export_datatable(section_id=None, rating_key=None, kwargs=None):
    default_return = {'recordsFiltered': 0,
                      'recordsTotal': 0,
                      'draw': 0,
                      'data': 'null',
                      'error': 'Unable to execute database query.'}

    data_tables = datatables.DataTables()

    custom_where = []
    if section_id:
        custom_where.append(['exports.section_id', section_id])
    if rating_key:
        custom_where.append(['exports.rating_key', rating_key])

    columns = ['exports.id AS export_id',
               'exports.timestamp',
               'exports.section_id',
               'exports.rating_key',
               'exports.media_type',
               'exports.filename',
               'exports.file_format',
               'exports.include_images',
               'exports.file_size',
               'exports.complete'
               ]
    try:
        query = data_tables.ssp_query(table_name='exports',
                                      columns=columns,
                                      custom_where=custom_where,
                                      group_by=[],
                                      join_types=[],
                                      join_tables=[],
                                      join_evals=[],
                                      kwargs=kwargs)
    except Exception as e:
        logger.warn("Tautulli Exporter :: Unable to execute database query for get_export_datatable: %s.", e)
        return default_return

    result = query['result']

    rows = []
    for item in result:
        media_type_title = item['media_type'].title()
        exists = helpers.cast_to_int(check_export_exists(item['filename']))

        row = {'export_id': item['export_id'],
               'timestamp': item['timestamp'],
               'section_id': item['section_id'],
               'rating_key': item['rating_key'],
               'media_type': item['media_type'],
               'media_type_title': media_type_title,
               'filename': item['filename'],
               'file_format': item['file_format'],
               'include_images': item['include_images'],
               'file_size': item['file_size'],
               'complete': item['complete'],
               'exists': exists
               }

        rows.append(row)

    result = {'recordsFiltered': query['filteredCount'],
              'recordsTotal': query['totalCount'],
              'data': rows,
              'draw': query['draw']
              }

    return result


def get_export_filepath(filename, images=False):
    if images:
        images_folder = '{}.images'.format(os.path.splitext(filename)[0])
        return os.path.join(plexpy.CONFIG.EXPORT_DIR, images_folder)
    return os.path.join(plexpy.CONFIG.EXPORT_DIR, filename)


def check_export_exists(filename):
    return os.path.isfile(get_export_filepath(filename))
