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
    import users
    from plex import Plex
else:
    from plexpy import database
    from plexpy import datatables
    from plexpy import helpers
    from plexpy import logger
    from plexpy import users
    from plexpy.plex import Plex


class Export(object):
    # True/False for allowed (thumb, art) image export
    MEDIA_TYPES = {
        'movie': (True, True),
        'show': (True, True),
        'season': (True, False),
        'episode': (False, False),
        'artist': (True, True),
        'album': (True, False),
        'track': (False, False),
        'photoalbum': (False, False),
        'photo': (False, False),
        'clip': (False, False),
        'collection': (True, True),
        'playlist': (True, True)
    }
    PLURAL_MEDIA_TYPES = {
        'movie': 'movies',
        'show': 'shows',
        'season': 'seasons',
        'episode': 'episodes',
        'artist': 'artists',
        'album': 'albums',
        'track': 'tracks',
        'photoalbum': 'photoalbums',
        'photo': 'photos',
        'clip': 'clips',
        'collection': 'collections',
        'children': 'children',
        'playlist': 'playlists',
        'item': 'items'
    }
    CHILD_MEDIA_TYPES = {
        'movie': [],
        'show': ['season'],
        'season': ['episode'],
        'episode': [],
        'artist': ['album'],
        'album': ['track'],
        'track': [],
        'photoalbum': ['photoalbum', 'photo', 'clip'],
        'photo': [],
        'clip': [],
        'collection': ['children'],
        'playlist': ['item']
    }
    METADATA_LEVELS = (0, 1, 2, 3, 9)
    MEDIA_INFO_LEVELS = (0, 1, 2, 3, 9)
    FILE_FORMATS = ('csv', 'json', 'xml', 'm3u8')
    EXPORT_TYPES = ('all', 'collection', 'playlist')

    def __init__(self, section_id=None, user_id=None, rating_key=None, file_format='csv',
                 metadata_level=1, media_info_level=1,
                 include_thumb=False, include_art=False,
                 custom_fields='', export_type=None):
        self.section_id = helpers.cast_to_int(section_id) or None
        self.user_id = helpers.cast_to_int(user_id) or None
        self.rating_key = helpers.cast_to_int(rating_key) or None
        self.file_format = str(file_format).lower()
        self.metadata_level = helpers.cast_to_int(metadata_level)
        self.media_info_level = helpers.cast_to_int(media_info_level)
        self.include_thumb = include_thumb
        self.include_art = include_art
        self.custom_fields = custom_fields.replace(' ', '')
        self._custom_fields = {}
        self.export_type = export_type or 'all'

        self.timestamp = helpers.timestamp()

        self.media_type = None
        self.obj = None

        self.filename = None
        self.export_id = None
        self.file_size = None
        self.success = False

        # Reset export options for m3u8
        if self.file_format == 'm3u8':
            self.metadata_level = 1
            self.media_info_level = 1
            self.include_thumb = False
            self.include_art = False
            self.custom_fields = ''

    def return_attrs(self, media_type, flatten=False):
        # o: current object
        # e: element in object attribute value list

        def movie_attrs():
            _movie_attrs = {
                'addedAt': helpers.datetime_to_iso,
                'art': None,
                'artFile': lambda o: self.get_image(o, 'art'),
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
                'durationHuman': lambda o: helpers.human_duration(getattr(o, 'duration', 0), sig='dhm'),
                'fields': {
                    'name': None,
                    'locked': None
                },
                'genres': {
                    'id': None,
                    'tag': None
                },
                'guid': None,
                'guids': {
                    'id': None
                },
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
                    'hdr': lambda o: self.get_any_hdr(o, 'movie'),
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
                        'sizeHuman': lambda o: helpers.human_file_size(getattr(o, 'size', 0)),
                        'optimizedForStreaming': None,
                        'requiredBandwidths': None,
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
                            'hdr': lambda o: helpers.is_hdr(getattr(o, 'bitDepth', 0), getattr(o, 'colorSpace', '')),
                            'height': None,
                            'level': None,
                            'pixelAspectRatio': None,
                            'pixelFormat': None,
                            'profile': None,
                            'refFrames': None,
                            'requiredBandwidths': None,
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
                            'requiredBandwidths': None,
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
                            'requiredBandwidths': None,
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
                'thumbFile': lambda o: self.get_image(o, 'thumb'),
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
                'artFile': lambda o: self.get_image(o, 'art'),
                'banner': None,
                'childCount': None,
                'collections': {
                    'id': None,
                    'tag': None
                },
                'contentRating': None,
                'duration': None,
                'durationHuman': lambda o: helpers.human_duration(getattr(o, 'duration', 0), sig='dhm'),
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
                'thumbFile': lambda o: self.get_image(o, 'thumb'),
                'title': None,
                'titleSort': None,
                'type': None,
                'updatedAt': helpers.datetime_to_iso,
                'userRating': None,
                'viewCount': None,
                'viewedLeafCount': None,
                'year': None,
                'seasons': lambda e: self._export_obj(e)
            }
            return _show_attrs

        def season_attrs():
            _season_attrs = {
                'addedAt': helpers.datetime_to_iso,
                'art': None,
                'artFile': lambda o: self.get_image(o, 'art'),
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
                'thumbFile': lambda o: self.get_image(o, 'thumb'),
                'title': None,
                'titleSort': None,
                'type': None,
                'updatedAt': helpers.datetime_to_iso,
                'userRating': None,
                'viewCount': None,
                'viewedLeafCount': None,
                'episodes': lambda e: self._export_obj(e)
            }
            return _season_attrs

        def episode_attrs():
            _episode_attrs = {
                'addedAt': helpers.datetime_to_iso,
                'art': None,
                'artFile': lambda o: self.get_image(o, 'art'),
                'chapterSource': None,
                'contentRating': None,
                'directors': {
                    'id': None,
                    'tag': None
                },
                'duration': None,
                'durationHuman': lambda o: helpers.human_duration(getattr(o, 'duration', 0), sig='dhm'),
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
                    'hdr': lambda o: self.get_any_hdr(o, 'episode'),
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
                        'sizeHuman': lambda o: helpers.human_file_size(getattr(o, 'size', 0)),
                        'optimizedForStreaming': None,
                        'requiredBandwidths': None,
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
                            'hdr': lambda o: helpers.is_hdr(getattr(o, 'bitDepth', 0), getattr(o, 'colorSpace', '')),
                            'height': None,
                            'level': None,
                            'pixelAspectRatio': None,
                            'pixelFormat': None,
                            'profile': None,
                            'refFrames': None,
                            'requiredBandwidths': None,
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
                            'requiredBandwidths': None,
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
                            'requiredBandwidths': None,
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
                'thumbFile': lambda o: self.get_image(o, 'thumb'),
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
                'artFile': lambda o: self.get_image(o, 'art'),
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
                'thumbFile': lambda o: self.get_image(o, 'thumb'),
                'title': None,
                'titleSort': None,
                'type': None,
                'updatedAt': helpers.datetime_to_iso,
                'userRating': None,
                'viewCount': None,
                'albums': lambda e: self._export_obj(e)
            }
            return _artist_attrs

        def album_attrs():
            _album_attrs = {
                'addedAt': helpers.datetime_to_iso,
                'art': None,
                'artFile': lambda o: self.get_image(o, 'art'),
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
                'thumbFile': lambda o: self.get_image(o, 'thumb'),
                'title': None,
                'titleSort': None,
                'type': None,
                'updatedAt': helpers.datetime_to_iso,
                'userRating': None,
                'viewCount': None,
                'viewedLeafCount': None,
                'tracks': lambda e: self._export_obj(e)
            }
            return _album_attrs

        def track_attrs():
            _track_attrs = {
                'addedAt': helpers.datetime_to_iso,
                'art': None,
                'duration': None,
                'durationHuman': lambda o: helpers.human_duration(getattr(o, 'duration', 0), sig='dhm'),
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
                        'sizeHuman': lambda o: helpers.human_file_size(getattr(o, 'size', 0)),
                        'requiredBandwidths': None,
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
                            'requiredBandwidths': None,
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
                'type': lambda e: 'photoalbum' if e == 'photo' else e,
                'updatedAt': helpers.datetime_to_iso,
                'photoalbums': lambda o: [self._export_obj(e) for e in getattr(o, 'albums')()],
                'photos': lambda e: self._export_obj(e),
                'clips': lambda e: self._export_obj(e)
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
                        'sizeHuman': lambda o: helpers.human_file_size(getattr(o, 'size', 0)),
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
                'artFile': lambda o: self.get_image(o, 'art'),
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
                'labels': {
                    'id': None,
                    'tag': None
                },
                'librarySectionID': None,
                'librarySectionKey': None,
                'librarySectionTitle': None,
                'maxYear': None,
                'minYear': None,
                'ratingKey': None,
                'subtype': None,
                'summary': None,
                'thumb': None,
                'thumbFile': lambda o: self.get_image(o, 'thumb'),
                'title': None,
                'titleSort': None,
                'type': None,
                'updatedAt': helpers.datetime_to_iso,
                'children': lambda e: self._export_obj(e)
            }
            return _collection_attrs

        def playlist_attrs():
            _playlist_attrs = {
                'addedAt': helpers.datetime_to_iso,
                'composite': None,
                'duration': None,
                'durationHuman': lambda o: helpers.human_duration(getattr(o, 'duration', 0), sig='dhm'),
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
                'items': lambda e: self._export_obj(e)
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
            'photoalbum': photo_album_attrs,
            'photo': photo_attrs,
            'clip': episode_attrs,  # Assume clip is the same as an episode
            'collection': collection_attrs,
            'playlist': playlist_attrs,
        }

        media_attrs = _media_types[media_type]()

        if flatten:
            media_attrs = helpers.flatten_dict(media_attrs)[0]

        return media_attrs

    def return_levels(self, media_type, reverse_map=False):
        def movie_levels():
            _media_type = 'movie'
            _metadata_levels = {
                1: [
                    'ratingKey', 'title', 'titleSort', 'originalTitle', 'originallyAvailableAt', 'year', 'addedAt',
                    'rating', 'ratingImage', 'audienceRating', 'audienceRatingImage', 'userRating', 'contentRating',
                    'studio', 'tagline', 'summary', 'guid', 'duration', 'durationHuman', 'type'
                ],
                2: [
                    'directors.tag', 'writers.tag', 'producers.tag', 'roles.tag', 'roles.role',
                    'countries.tag', 'genres.tag', 'collections.tag', 'labels.tag',
                    'fields.name', 'fields.locked', 'guids.id'
                ],
                3: [
                    'art', 'thumb', 'key', 'chapterSource',
                    'chapters.tag', 'chapters.index', 'chapters.start', 'chapters.end', 'chapters.thumb',
                    'updatedAt', 'lastViewedAt', 'viewCount'
                ],
                9: self._get_all_metadata_attrs(_media_type)
            }
            _media_info_levels = {
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
            return _metadata_levels, _media_info_levels

        def show_levels():
            _media_type = 'show'
            _metadata_levels = {
                1: [
                    'ratingKey', 'title', 'titleSort', 'originallyAvailableAt', 'year', 'addedAt',
                    'rating', 'userRating', 'contentRating',
                    'studio', 'summary', 'guid', 'duration', 'durationHuman', 'type', 'childCount',
                    'seasons'
                ],
                2: [
                    'roles.tag', 'roles.role',
                    'genres.tag', 'collections.tag', 'labels.tag',
                    'fields.name', 'fields.locked'
                ],
                3: [
                    'art', 'thumb', 'banner', 'theme', 'key',
                    'updatedAt', 'lastViewedAt', 'viewCount'
                ],
                9: self._get_all_metadata_attrs(_media_type)
            }
            _media_info_levels = {}
            return _metadata_levels, _media_info_levels

        def season_levels():
            _media_type = 'season'
            _metadata_levels = {
                1: [
                    'ratingKey', 'title', 'titleSort', 'addedAt',
                    'userRating',
                    'summary', 'guid', 'type', 'index',
                    'parentTitle', 'parentRatingKey', 'parentGuid',
                    'episodes'
                ],
                2: [
                    'fields.name', 'fields.locked'
                ],
                3: [
                    'art', 'thumb', 'key',
                    'updatedAt', 'lastViewedAt', 'viewCount',
                    'parentKey', 'parentTheme', 'parentThumb'
                ],
                9: self._get_all_metadata_attrs(_media_type)
            }
            _media_info_levels = {}
            return _metadata_levels, _media_info_levels

        def episode_levels():
            _media_type = 'episode'
            _metadata_levels = {
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
                9: self._get_all_metadata_attrs(_media_type)
            }
            _media_info_levels = {
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
            return _metadata_levels, _media_info_levels

        def artist_levels():
            _media_type = 'artist'
            _metadata_levels = {
                1: [
                    'ratingKey', 'title', 'titleSort', 'addedAt',
                    'rating', 'userRating',
                    'summary', 'guid', 'type',
                    'albums'
                ],
                2: [
                    'collections.tag', 'genres.tag', 'countries.tag', 'moods.tag', 'styles.tag',
                    'fields.name', 'fields.locked'
                ],
                3: [
                    'art', 'thumb', 'key',
                    'updatedAt', 'lastViewedAt', 'viewCount'
                ],
                9: self._get_all_metadata_attrs(_media_type)
            }
            _media_info_levels = {}
            return _metadata_levels, _media_info_levels

        def album_levels():
            _media_type = 'album'
            _metadata_levels = {
                1: [
                    'ratingKey', 'title', 'titleSort', 'originallyAvailableAt', 'addedAt',
                    'rating', 'userRating',
                    'summary', 'guid', 'type', 'index',
                    'parentTitle', 'parentRatingKey', 'parentGuid',
                    'tracks'
                ],
                2: [
                    'collections.tag', 'genres.tag', 'labels.tag', 'moods.tag', 'styles.tag',
                    'fields.name', 'fields.locked'
                ],
                3: [
                    'art', 'thumb', 'key',
                    'updatedAt', 'lastViewedAt', 'viewCount',
                    'parentKey', 'parentThumb'
                ],
                9: self._get_all_metadata_attrs(_media_type)
            }
            _media_info_levels = {}
            return _metadata_levels, _media_info_levels

        def track_levels():
            _media_type = 'track'
            _metadata_levels = {
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
                9: self._get_all_metadata_attrs(_media_type)
            }
            _media_info_levels = {
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
            return _metadata_levels, _media_info_levels

        def photo_album_levels():
            _media_type = 'photoalbum'
            _metadata_levels = {
                1: [
                    'ratingKey', 'title', 'titleSort', 'addedAt',
                    'summary', 'guid', 'type', 'index',
                    'photoalbums', 'photos', 'clips'
                ],
                2: [
                    'fields.name', 'fields.locked'
                ],
                3: [
                    'art', 'thumb', 'key',
                    'updatedAt'
                ],
                9: self._get_all_metadata_attrs(_media_type)
            }
            _media_info_levels = {}
            return _metadata_levels, _media_info_levels

        def photo_levels():
            _media_type = 'photo'
            _metadata_levels = {
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
                9: self._get_all_metadata_attrs(_media_type)
            }
            _media_info_levels = {
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
            return _metadata_levels, _media_info_levels

        def collection_levels():
            _media_type = 'collection'
            _metadata_levels = {
                1: [
                    'ratingKey', 'title', 'titleSort', 'minYear', 'maxYear', 'addedAt',
                    'contentRating',
                    'summary', 'guid', 'type', 'subtype', 'childCount',
                    'collectionMode', 'collectionSort',
                    'children'
                ],
                2: [
                    'labels.tag',
                    'fields.name', 'fields.locked'
                ],
                3: [
                    'art', 'thumb', 'key',
                    'updatedAt'
                ],
                9: self._get_all_metadata_attrs(_media_type)
            }
            _media_info_levels = {}
            return _metadata_levels, _media_info_levels

        def playlist_levels():
            _media_type = 'playlist'
            _metadata_levels = {
                1: [
                    'ratingKey', 'title', 'addedAt',
                    'summary', 'guid', 'type', 'duration', 'durationHuman',
                    'playlistType', 'smart',
                    'items'
                ],
                2: [
                ],
                3: [
                    'composite', 'key',
                    'updatedAt'
                ],
                9: self._get_all_metadata_attrs(_media_type)
            }
            _media_info_levels = {}
            return _metadata_levels, _media_info_levels

        _media_types = {
            'movie': movie_levels,
            'show': show_levels,
            'season': season_levels,
            'episode': episode_levels,
            'artist': artist_levels,
            'album': album_levels,
            'track': track_levels,
            'photoalbum': photo_album_levels,
            'photo': photo_levels,
            'clip': episode_levels,  # Assume clip is the same as an episode
            'collection': collection_levels,
            'playlist': playlist_levels
        }

        metadata_levels, media_info_levels = _media_types[media_type]()

        if reverse_map:
            metadata_levels = {attr: level for level, attrs in reversed(sorted(metadata_levels.items()))
                               for attr in attrs}
            media_info_levels = {attr: level for level, attrs in reversed(sorted(media_info_levels.items()))
                                 for attr in attrs}

        return metadata_levels, media_info_levels

    def return_attrs_level_map(self, media_type, prefix=''):
        media_attrs = self.return_attrs(media_type, flatten=True)
        metadata_levels, media_info_levels = self.return_levels(media_type, reverse_map=True)

        child_media_types = [self.PLURAL_MEDIA_TYPES[m] for m in self.CHILD_MEDIA_TYPES[media_type]]

        metadata_levels_map = {}
        media_info_levels_map = {}

        for attr in media_attrs:
            # Skip the main child attribute
            if attr in child_media_types:
                continue

            metadata_level = metadata_levels.get(
                attr, max(self.METADATA_LEVELS) if not self.is_media_info_attr(attr) else None)
            media_info_level = media_info_levels.get(
                attr, max(self.MEDIA_INFO_LEVELS) if self.is_media_info_attr(attr) else None)

            if metadata_level is not None:
                metadata_levels_map[prefix + attr] = metadata_level
            elif media_info_level is not None:
                media_info_levels_map[prefix + attr] = media_info_level

        return metadata_levels_map, media_info_levels_map

    def export(self):
        msg = ''
        if not self.section_id and not self.user_id and not self.rating_key:
            msg = "Export called but no section_id, user_id, or rating_key provided."
        elif self.metadata_level not in self.METADATA_LEVELS:
            msg = "Export called with invalid metadata_level '{}'.".format(self.metadata_level)
        elif self.media_info_level not in self.MEDIA_INFO_LEVELS:
            msg = "Export called with invalid media_info_level '{}'.".format(self.media_info_level)
        elif self.file_format not in self.FILE_FORMATS:
            msg = "Export called with invalid file_format '{}'.".format(self.file_format)
        elif self.export_type not in self.EXPORT_TYPES:
            msg = "Export called with invalid export_type '{}'.".format(self.export_type)
        elif self.user_id and self.export_type != 'playlist':
            msg = "Export called with invalid export_type '{}'. " \
                  "Only export_type 'playlist' is allowed for user export."

        if msg:
            logger.error("Tautulli Exporter :: %s", msg)
            return msg

        if self.user_id:
            user_data = users.Users()
            user_info = user_data.get_details(user_id=self.user_id)
            user_tokens = user_data.get_tokens(user_id=self.user_id)
            plex_token = user_tokens['server_token']
        else:
            plex_token = plexpy.CONFIG.PMS_TOKEN

        plex = Plex(plexpy.CONFIG.PMS_URL, plex_token)

        if self.rating_key:
            logger.debug(
                "Tautulli Exporter :: Export called with rating_key %s, "
                "metadata_level %d, media_info_level %d, include_thumb %s, include_art %s",
                self.rating_key, self.metadata_level, self.media_info_level,
                self.include_thumb, self.include_art)

            self.obj = plex.get_item(self.rating_key)
            self.media_type = 'photoalbum' if self.is_photoalbum(self.obj) else self.obj.type

            if self.media_type != 'playlist':
                self.section_id = self.obj.librarySectionID

            if self.media_type in ('season', 'episode', 'album', 'track'):
                item_title = self.obj._defaultSyncTitle()
            else:
                item_title = self.obj.title

            filename = '{} - {} [{}].{}'.format(
                self.media_type.capitalize(), item_title, self.rating_key,
                helpers.timestamp_to_YMDHMS(self.timestamp))

        elif self.user_id:
            logger.debug(
                "Tautulli Exporter :: Export called with user_id %s, "
                "metadata_level %d, media_info_level %d, include_thumb %s, include_art %s, "
                "export_type %s",
                self.user_id, self.metadata_level, self.media_info_level,
                self.include_thumb, self.include_art, self.export_type)

            self.obj = plex.plex
            self.media_type = self.export_type

            username = user_info['username']

            filename = 'User - {} - {} [{}].{}'.format(
                username, self.export_type.capitalize(), self.user_id,
                helpers.timestamp_to_YMDHMS(self.timestamp))

        elif self.section_id:
            logger.debug(
                "Tautulli Exporter :: Export called with section_id %s, "
                "metadata_level %d, media_info_level %d, include_thumb %s, include_art %s, "
                "export_type %s",
                self.section_id, self.metadata_level, self.media_info_level,
                self.include_thumb, self.include_art, self.export_type)

            self.obj = plex.get_library(str(self.section_id))
            if self.export_type == 'all':
                self.media_type = self.obj.type
            else:
                self.media_type = self.export_type

            library_title = self.obj.title

            filename = 'Library - {} - {} [{}].{}'.format(
                library_title, self.export_type.capitalize(), self.section_id,
                helpers.timestamp_to_YMDHMS(self.timestamp))

        else:
            msg = "Export called but no section_id, user_id, or rating_key provided."
            logger.error("Tautulli Exporter :: %s", msg)
            return msg

        if self.media_type not in self.MEDIA_TYPES:
            msg = "Cannot export media type '{}'.".format(self.media_type)
            logger.error("Tautulli Exporter :: %s", msg)
            return msg

        self.include_thumb = self.include_thumb and self.MEDIA_TYPES[self.media_type][0]
        self.include_art = self.include_art and self.MEDIA_TYPES[self.media_type][1]
        self._process_custom_fields()

        self.filename = '{}.{}'.format(helpers.clean_filename(filename), self.file_format)
        self.export_id = self.add_export()
        if not self.export_id:
            msg = "Failed to export '{}'.".format(self.filename)
            logger.error("Tautulli Exporter :: %s", msg)
            return msg

        threading.Thread(target=self._real_export).start()

        return True

    def add_export(self):
        keys = {'timestamp': self.timestamp,
                'section_id': self.section_id,
                'user_id': self.user_id,
                'rating_key': self.rating_key,
                'media_type': self.media_type}

        values = {'file_format': self.file_format,
                  'filename': self.filename,
                  'metadata_level': self.metadata_level,
                  'media_info_level': self.media_info_level,
                  'include_thumb': self.include_thumb,
                  'include_art': self.include_art,
                  'custom_fields': self.custom_fields}

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
                  'file_size': self.file_size,
                  'include_thumb': self.include_thumb,
                  'include_art': self.include_art}

        db = database.MonitorDatabase()
        db.upsert(table_name='exports', key_dict=keys, value_dict=values)

    def _real_export(self):
        logger.info("Tautulli Exporter :: Starting export for '%s'...", self.filename)

        filepath = get_export_filepath(self.filename)
        images_folder = get_export_filepath(self.filename, images=True)

        if self.rating_key:
            items = [self.obj]
        elif self.user_id:
            # Only playlists export allowed for users
            items = self.obj.playlists()
        else:
            method = getattr(self.obj, self.export_type)
            items = method()

        pool = ThreadPool(processes=4)

        try:
            result = pool.map(self._export_obj, items)

            if self.file_format == 'csv':
                csv_data = helpers.flatten_dict(result)
                csv_headers = set().union(*csv_data)
                with open(filepath, 'w', encoding='utf-8', newline='') as outfile:
                    writer = csv.DictWriter(outfile, sorted(csv_headers))
                    writer.writeheader()
                    writer.writerows(csv_data)

            elif self.file_format == 'json':
                json_data = json.dumps(result, indent=4, ensure_ascii=False, sort_keys=True)
                with open(filepath, 'w', encoding='utf-8') as outfile:
                    outfile.write(json_data)

            elif self.file_format == 'xml':
                xml_data = helpers.dict_to_xml({self.media_type: result}, root_node='export', indent=4)
                with open(filepath, 'w', encoding='utf-8') as outfile:
                    outfile.write(xml_data)

            elif self.file_format == 'm3u8':
                m3u8_data = self.dict_to_m3u8(result)
                with open(filepath, 'w', encoding='utf-8') as outfile:
                    outfile.write(m3u8_data)

            self.file_size = os.path.getsize(filepath)

            if os.path.exists(images_folder):
                for f in os.listdir(images_folder):
                    if self.include_thumb is False and f.endswith('.thumb.jpg'):
                        self.include_thumb = True
                    if self.include_art is False and f.endswith('.art.jpg'):
                        self.include_art = True

                    image_path = os.path.join(images_folder, f)
                    if os.path.isfile(image_path):
                        self.file_size += os.path.getsize(image_path)

            self.success = True
            logger.info("Tautulli Exporter :: Successfully exported to '%s'", filepath)

        except Exception as e:
            logger.exception("Tautulli Exporter :: Failed to export '%s': %s", self.filename, e)

        finally:
            pool.close()
            pool.join()
            self.set_export_state()

    def _export_obj(self, obj):
        # Reload ~plexapi.base.PlexPartialObject
        if hasattr(obj, 'isPartialObject') and obj.isPartialObject():
            obj = obj.reload()

        media_type = 'photoalbum' if self.is_photoalbum(obj) else obj.type
        export_attrs = self._get_export_attrs(media_type)
        return helpers.get_attrs_to_dict(obj, attrs=export_attrs)

    def _process_custom_fields(self):
        if self.custom_fields:
            logger.debug("Tautulli Exporter :: Processing custom fields: %s", self.custom_fields)

        for field in self.custom_fields.split(','):
            field = field.strip()
            if not field:
                continue

            media_type, field = self._parse_custom_field(self.media_type, field)

            if media_type in self._custom_fields:
                self._custom_fields[media_type].add(field)
            else:
                self._custom_fields[media_type] = {field}

    def _parse_custom_field(self, media_type, field):
        for child_media_type in self.CHILD_MEDIA_TYPES.get(media_type, []):
            plural_key = self.PLURAL_MEDIA_TYPES[child_media_type]
            if field.startswith(plural_key + '.'):
                media_type, field = field.split('.', maxsplit=1)
                media_type, field = self._parse_custom_field(child_media_type, field)

        return media_type, field

    def _get_all_metadata_attrs(self, media_type):
        exclude_attrs = ('locations', 'media', 'artFile', 'thumbFile')
        all_attrs = self.return_attrs(media_type)
        return [attr for attr in all_attrs if attr not in exclude_attrs]

    def _get_export_attrs(self, media_type):
        media_attrs = self.return_attrs(media_type)
        metadata_level_attrs, media_info_level_attrs = self.return_levels(media_type)

        export_attrs_list = []
        export_attrs_set = set()

        for level, attrs in metadata_level_attrs.items():
            if level <= self.metadata_level:
                export_attrs_set.update(attrs)

        for level, attrs in media_info_level_attrs.items():
            if level <= self.media_info_level:
                export_attrs_set.update(attrs)

        if self.include_thumb:
            if 'thumbFile' in media_attrs and self.MEDIA_TYPES[media_type][0]:
                export_attrs_set.add('thumbFile')
        if self.include_art:
            if 'artFile' in media_attrs and self.MEDIA_TYPES[media_type][1]:
                export_attrs_set.add('artFile')

        if media_type in self._custom_fields:
            export_attrs_set.update(self._custom_fields[media_type])

        for child_media_type in self.CHILD_MEDIA_TYPES.get(media_type):
            if child_media_type in self._custom_fields:
                export_attrs_set.add(self.PLURAL_MEDIA_TYPES[child_media_type])

        if media_type != self.media_type:
            if self.media_type == 'collection' and 'children' in self._custom_fields:
                export_attrs_set.update(self._custom_fields['children'])
            elif self.media_type == 'playlist' and 'item' in self._custom_fields:
                export_attrs_set.update(self._custom_fields['item'])

        for attr in export_attrs_set:
            try:
                value = helpers.get_dict_value_by_path(media_attrs, attr)
            except (KeyError, TypeError):
                logger.warn("Tautulli Exporter :: Unknown export attribute '%s', skipping...", attr)
                continue

            export_attrs_list.append(value)

        return reduce(helpers.dict_merge, export_attrs_list, {})

    def get_any_hdr(self, item, media_type):
        root = self.return_attrs(media_type)['media']
        attrs = helpers.get_dict_value_by_path(root, 'parts.videoStreams.hdr')
        media = helpers.get_attrs_to_dict(item, attrs)
        return any(vs.get('hdr') for p in media.get('parts', []) for vs in p.get('videoStreams', []))
    
    def get_image(self, item, image):
        media_type = item.type
        rating_key = item.ratingKey
    
        if media_type in ('season', 'episode', 'album', 'track'):
            item_title = item._defaultSyncTitle()
        else:
            item_title = item.title
    
        folder = get_export_filepath(self.filename, images=True)
        filename = helpers.clean_filename('{} [{}].{}.jpg'.format(item_title, rating_key, image))
        filepath = os.path.join(folder, filename)
    
        os.makedirs(folder, exist_ok=True)
    
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
    
            return os.path.join(os.path.basename(folder), filename)

    @staticmethod
    def is_media_info_attr(attr):
        return attr.startswith('media.') or attr == 'locations'

    @staticmethod
    def is_photoalbum(obj):
        return obj.type == 'photo' and obj.TAG == 'Directory'

    def dict_to_m3u8(self, data):
        items = self._get_m3u8_items(data)

        m3u8 = '#EXTM3U\n'
        m3u8 += '# Playlist: {}\n\n'.format(self.filename)
        m3u8_item_template = '# ratingKey: {ratingKey}\n#EXTINF:{duration},{title}\n{location}\n'
        m3u8_items = []

        for item in items:
            m3u8_items.append(m3u8_item_template.format(**item))

        m3u8 = m3u8 + '\n'.join(m3u8_items)

        return m3u8

    def _get_m3u8_items(self, data):
        items = []

        for d in data:
            if d.get('locations', []):
                location = {
                    'ratingKey': d['ratingKey'],
                    'duration': d['duration'],
                    'title': d['title'],
                    'location': d['locations'][0]
                }
                items.append(location)

            for child_media_type in self.CHILD_MEDIA_TYPES[d['type']]:
                child_locations = self._get_m3u8_items(d[self.PLURAL_MEDIA_TYPES[child_media_type]])
                items.extend(child_locations)

        return items


def get_export(export_id):
    db = database.MonitorDatabase()
    result = db.select_single('SELECT filename, file_format, include_thumb, include_art, complete '
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
                images_folder = get_export_filepath(export_data['filename'], images=True)
                shutil.rmtree(images_folder, ignore_errors=True)
            except OSError as e:
                logger.error("Tautulli Exporter :: Failed to delete exported file '%s': %s", filepath, e)
        return True
    else:
        return False


def delete_all_exports():
    db = database.MonitorDatabase()
    result = db.select('SELECT filename, include_thumb, include_art FROM exports')

    logger.info("Tautulli Exporter :: Deleting all exports from the database.")

    deleted_files = True
    for row in result:
        if check_export_exists(row['filename']):
            filepath = get_export_filepath(row['filename'])
            try:
                os.remove(filepath)
                images_folder = get_export_filepath(row['filename'], images=True)
                shutil.rmtree(images_folder, ignore_errors=True)
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


def get_export_datatable(section_id=None, user_id=None, rating_key=None, kwargs=None):
    default_return = {'recordsFiltered': 0,
                      'recordsTotal': 0,
                      'draw': 0,
                      'data': 'null',
                      'error': 'Unable to execute database query.'}

    data_tables = datatables.DataTables()

    custom_where = []
    if section_id:
        custom_where.append(['exports.section_id', section_id])
    if user_id:
        custom_where.append(['exports.user_id', user_id])
    if rating_key:
        custom_where.append(['exports.rating_key', rating_key])

    columns = ['exports.id AS export_id',
               'exports.timestamp',
               'exports.section_id',
               'exports.user_id',
               'exports.rating_key',
               'exports.media_type',
               'exports.filename',
               'exports.file_format',
               'exports.metadata_level',
               'exports.media_info_level',
               'exports.include_thumb',
               'exports.include_art',
               'exports.custom_fields',
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
               'user_id': item['user_id'],
               'rating_key': item['rating_key'],
               'media_type': item['media_type'],
               'media_type_title': media_type_title,
               'filename': item['filename'],
               'file_format': item['file_format'],
               'metadata_level': item['metadata_level'],
               'media_info_level': item['media_info_level'],
               'include_thumb': item['include_thumb'],
               'include_art': item['include_art'],
               'custom_fields': item['custom_fields'],
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


def get_custom_fields(media_type, sub_media_type=None):
    custom_fields = {
        'metadata_fields': [],
        'media_info_fields': []
    }

    collection_sub_media_types = {'movie', 'show', 'artist', 'album', 'photoalbum'}
    playlist_sub_media_types = {'video', 'audio', 'photo'}
    sub_media_type = {s.strip().lower() for s in sub_media_type.split(',')}

    export = Export()

    if media_type not in export.MEDIA_TYPES:
        return custom_fields
    elif media_type == 'collection' and not sub_media_type.issubset(collection_sub_media_types):
        return custom_fields
    elif media_type == 'playlist' and not sub_media_type.issubset(playlist_sub_media_types):
        return custom_fields

    sub_media_types = list(sub_media_type.difference(playlist_sub_media_types))
    if media_type == 'playlist' and 'video' in sub_media_type:
        sub_media_types += ['movie', 'episode']
    elif media_type == 'playlist' and 'audio' in sub_media_type:
        sub_media_types += ['track']
    elif media_type == 'playlist' and 'photo' in sub_media_type:
        sub_media_types += ['photo']

    metadata_levels_map, media_info_levels_map = export.return_attrs_level_map(media_type)

    for sub_media_type in sub_media_types:
        for child_media_type in export.CHILD_MEDIA_TYPES[media_type]:
            prefix = ''

            while child_media_type:
                if child_media_type in ('children', 'item'):
                    fields_child_media_type = sub_media_type
                else:
                    fields_child_media_type = child_media_type

                prefix = prefix + export.PLURAL_MEDIA_TYPES[child_media_type] + '.'

                child_metadata_levels_map, child_media_info_levels_map = export.return_attrs_level_map(
                    fields_child_media_type, prefix=prefix)

                metadata_levels_map.update(child_metadata_levels_map)
                media_info_levels_map.update(child_media_info_levels_map)

                if child_media_type == 'photoalbum':
                    # Don't recurse photoalbum again
                    break

                child_media_type = export.CHILD_MEDIA_TYPES.get(fields_child_media_type)
                if child_media_type:
                    child_media_type = child_media_type[0]

    custom_fields['metadata_fields'] = [{'field': attr, 'level': level}
                                        for attr, level in sorted(metadata_levels_map.items()) if level]
    custom_fields['media_info_fields'] = [{'field': attr, 'level': level}
                                          for attr, level in sorted(media_info_levels_map.items()) if level]

    return custom_fields
