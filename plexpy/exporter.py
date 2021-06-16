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
        'season': (True, True),
        'episode': (False, False),
        'artist': (True, True),
        'album': (True, True),
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
        'collection': ['item'],
        'playlist': ['item']
    }
    TREE_MEDIA_TYPES = [
        ('episode', 'season', 'show'),
        ('track', 'album', 'artist'),
        ('photo', 'photoalbum'),
        ('clip', 'photoalbum'),
        ('item', 'collection'),
        ('item', 'playlist')
    ]
    METADATA_LEVELS = (0, 1, 2, 3, 9)
    MEDIA_INFO_LEVELS = (0, 1, 2, 3, 9)
    IMAGE_LEVELS = (0, 1, 2, 9)
    FILE_FORMATS = ('csv', 'json', 'xml', 'm3u8')
    EXPORT_TYPES = ('all', 'collection', 'playlist')

    def __init__(self, section_id=None, user_id=None, rating_key=None, file_format='csv',
                 metadata_level=1, media_info_level=1,
                 thumb_level=0, art_level=0,
                 custom_fields='', export_type='all', individual_files=False):
        self.section_id = helpers.cast_to_int(section_id) or None
        self.user_id = helpers.cast_to_int(user_id) or None
        self.rating_key = helpers.cast_to_int(rating_key) or None
        self.file_format = str(file_format).lower()
        self.metadata_level = helpers.cast_to_int(metadata_level)
        self.media_info_level = helpers.cast_to_int(media_info_level)
        self.thumb_level = helpers.cast_to_int(thumb_level)
        self.art_level = helpers.cast_to_int(art_level)
        self.custom_fields = custom_fields.replace(' ', '')
        self._custom_fields = {}
        self.export_type = str(export_type).lower() or 'all'
        self.individual_files = individual_files

        self.timestamp = helpers.timestamp()

        self.media_type = None
        self.obj = None
        self.obj_title = None

        self.directory = None
        self.filename = None
        self.title = None
        self.export_id = None
        self.file_size = 0
        self.exported_thumb = False
        self.exported_art = False
        self._reload_check_files = False

        self.total_items = 0
        self.exported_items = 0
        self.success = False

        # Reset export options for m3u8
        if self.file_format == 'm3u8':
            self.metadata_level = 1
            self.media_info_level = 1
            self.thumb_level = 0
            self.art_level = 0
            self.custom_fields = ''

    def return_attrs(self, media_type, flatten=False):
        # o: current object
        # e: element in object attribute value list

        def movie_attrs():
            _movie_attrs = {
                'addedAt': helpers.datetime_to_iso,
                'art': None,
                'artBlurHash': None,
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
                'durationHuman': lambda o: helpers.human_duration(getattr(o, 'duration', 0)),
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
                'hasPreviewThumbnails': None,
                'key': None,
                'labels': {
                    'id': None,
                    'tag': None
                },
                'languageOverride': None,
                'lastRatedAt': helpers.datetime_to_iso,
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
                    'isOptimizedVersion': None,
                    'has64bitOffsets': None,
                    'optimizedForStreaming': None,
                    'proxyType': None,
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
                        'hasPreviewThumbnails': None,
                        'hasThumbnail': None,
                        'id': None,
                        'indexes': None,
                        'key': None,
                        'optimizedForStreaming': None,
                        'packetLength': None,
                        'requiredBandwidths': None,
                        'size': None,
                        'sizeHuman': lambda o: helpers.human_file_size(getattr(o, 'size', 0)),
                        'syncItemId': None,
                        'syncState': None,
                        'videoProfile': None,
                        'videoStreams': {
                            'bitrate': None,
                            'codec': None,
                            'default': None,
                            'displayTitle': None,
                            'extendedDisplayTitle': None,
                            'id': None,
                            'index': None,
                            'key': None,
                            'language': None,
                            'languageCode': None,
                            'requiredBandwidths': None,
                            'selected': None,
                            'streamType': None,
                            'title': None,
                            'type': None,
                            'anamorphic': None,
                            'bitDepth': None,
                            'cabac': None,
                            'chromaLocation': None,
                            'chromaSubsampling': None,
                            'codecID': None,
                            'codedHeight': None,
                            'codedWidth': None,
                            'colorPrimaries': None,
                            'colorRange': None,
                            'colorSpace': None,
                            'colorTrc': None,
                            'DOVIBLCompatID': None,
                            'DOVIBLPresent': None,
                            'DOVIELPresent': None,
                            'DOVILevel': None,
                            'DOVIPresent': None,
                            'DOVIProfile': None,
                            'DOVIRPUPresent': None,
                            'DOVIVersion': None,
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
                            'scanType': None,
                            'streamIdentifier': None,
                            'width': None
                        },
                        'audioStreams': {
                            'bitrate': None,
                            'codec': None,
                            'default': None,
                            'displayTitle': None,
                            'extendedDisplayTitle': None,
                            'id': None,
                            'index': None,
                            'key': None,
                            'language': None,
                            'languageCode': None,
                            'requiredBandwidths': None,
                            'selected': None,
                            'streamType': None,
                            'title': None,
                            'type': None,
                            'audioChannelLayout': None,
                            'bitDepth': None,
                            'bitrateMode': None,
                            'channels': None,
                            'duration': None,
                            'profile': None,
                            'samplingRate': None,
                            'streamIdentifier': None
                        },
                        'subtitleStreams': {
                            'codec': None,
                            'default': None,
                            'displayTitle': None,
                            'extendedDisplayTitle': None,
                            'id': None,
                            'index': None,
                            'key': None,
                            'language': None,
                            'languageCode': None,
                            'requiredBandwidths': None,
                            'selected': None,
                            'streamType': None,
                            'title': None,
                            'type': None,
                            'container': None,
                            'forced': None,
                            'format': None,
                            'headerCompression': None,
                            'transient': None
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
                'thumbBlurHash': None,
                'thumbFile': lambda o: self.get_image(o, 'thumb'),
                'title': None,
                'titleSort': None,
                'type': None,
                'updatedAt': helpers.datetime_to_iso,
                'useOriginalTitle': None,
                'userRating': None,
                'viewCount': None,
                'viewOffset': None,
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
                'artBlurHash': None,
                'artFile': lambda o: self.get_image(o, 'art'),
                'audienceRating': None,
                'audienceRatingImage': None,
                'autoDeletionItemPolicyUnwatchedLibrary': None,
                'autoDeletionItemPolicyWatchedLibrary': None,
                'banner': None,
                'bannerFile': lambda o: self.get_image(o, 'banner'),
                'childCount': None,
                'collections': {
                    'id': None,
                    'tag': None
                },
                'contentRating': None,
                'duration': None,
                'durationHuman': lambda o: helpers.human_duration(getattr(o, 'duration', 0)),
                'episodeSort': None,
                'fields': {
                    'name': None,
                    'locked': None
                },
                'flattenSeasons': None,
                'genres': {
                    'id': None,
                    'tag': None
                },
                'guid': None,
                'guids': {
                    'id': None
                },
                'index': None,
                'key': None,
                'labels': {
                    'id': None,
                    'tag': None
                },
                'languageOverride': None,
                'lastRatedAt': helpers.datetime_to_iso,
                'lastViewedAt': helpers.datetime_to_iso,
                'leafCount': None,
                'librarySectionID': None,
                'librarySectionKey': None,
                'librarySectionTitle': None,
                'locations': None,
                'network': None,
                'originallyAvailableAt': partial(helpers.datetime_to_iso, to_date=True),
                'originalTitle': None,
                'rating': None,
                'ratingKey': None,
                'roles': {
                    'id': None,
                    'tag': None,
                    'role': None,
                    'thumb': None
                },
                'showOrdering': None,
                'studio': None,
                'summary': None,
                'tagline': None,
                'theme': None,
                'thumb': None,
                'thumbBlurHash': None,
                'thumbFile': lambda o: self.get_image(o, 'thumb'),
                'title': None,
                'titleSort': None,
                'type': None,
                'updatedAt': helpers.datetime_to_iso,
                'useOriginalTitle': None,
                'userRating': None,
                'viewCount': None,
                'viewedLeafCount': None,
                'year': None,
                'seasons': lambda e: self.export_obj(e)
            }
            return _show_attrs

        def season_attrs():
            _season_attrs = {
                'addedAt': helpers.datetime_to_iso,
                'art': None,
                'artBlurHash': None,
                'artFile': lambda o: self.get_image(o, 'art'),
                'collections': {
                    'id': None,
                    'tag': None
                },
                'fields': {
                    'name': None,
                    'locked': None
                },
                'guid': None,
                'guids': {
                    'id': None
                },
                'index': None,
                'key': None,
                'lastRatedAt': helpers.datetime_to_iso,
                'lastViewedAt': helpers.datetime_to_iso,
                'leafCount': None,
                'librarySectionID': None,
                'librarySectionKey': None,
                'librarySectionTitle': None,
                'parentGuid': None,
                'parentIndex': None,
                'parentKey': None,
                'parentRatingKey': None,
                'parentStudio': None,
                'parentTheme': None,
                'parentThumb': None,
                'parentTitle': None,
                'ratingKey': None,
                'seasonNumber': None,
                'summary': None,
                'thumb': None,
                'thumbBlurHash': None,
                'thumbFile': lambda o: self.get_image(o, 'thumb'),
                'title': None,
                'titleSort': None,
                'type': None,
                'updatedAt': helpers.datetime_to_iso,
                'userRating': None,
                'viewCount': None,
                'viewedLeafCount': None,
                'year': None,
                'episodes': lambda e: self.export_obj(e)
            }
            return _season_attrs

        def episode_attrs():
            _episode_attrs = {
                'addedAt': helpers.datetime_to_iso,
                'art': None,
                'artBlurHash': None,
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
                'directors': {
                    'id': None,
                    'tag': None
                },
                'duration': None,
                'durationHuman': lambda o: helpers.human_duration(getattr(o, 'duration', 0)),
                'episodeNumber': None,
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
                'guids': {
                    'id': None
                },
                'hasIntroMarker': None,
                'hasPreviewThumbnails': None,
                'index': None,
                'key': None,
                'lastRatedAt': helpers.datetime_to_iso,
                'lastViewedAt': helpers.datetime_to_iso,
                'librarySectionID': None,
                'librarySectionKey': None,
                'librarySectionTitle': None,
                'locations': None,
                'markers': {
                    'end': None,
                    'start': None,
                    'type': None
                },
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
                    'isOptimizedVersion': None,
                    'has64bitOffsets': None,
                    'optimizedForStreaming': None,
                    'proxyType': None,
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
                        'hasPreviewThumbnails': None,
                        'hasThumbnail': None,
                        'id': None,
                        'indexes': None,
                        'key': None,
                        'optimizedForStreaming': None,
                        'packetLength': None,
                        'requiredBandwidths': None,
                        'size': None,
                        'sizeHuman': lambda o: helpers.human_file_size(getattr(o, 'size', 0)),
                        'syncItemId': None,
                        'syncState': None,
                        'videoProfile': None,
                        'videoStreams': {
                            'bitrate': None,
                            'codec': None,
                            'default': None,
                            'displayTitle': None,
                            'extendedDisplayTitle': None,
                            'id': None,
                            'index': None,
                            'key': None,
                            'language': None,
                            'languageCode': None,
                            'requiredBandwidths': None,
                            'selected': None,
                            'streamType': None,
                            'title': None,
                            'type': None,
                            'anamorphic': None,
                            'bitDepth': None,
                            'cabac': None,
                            'chromaLocation': None,
                            'chromaSubsampling': None,
                            'codecID': None,
                            'codedHeight': None,
                            'codedWidth': None,
                            'colorPrimaries': None,
                            'colorRange': None,
                            'colorSpace': None,
                            'colorTrc': None,
                            'DOVIBLCompatID': None,
                            'DOVIBLPresent': None,
                            'DOVIELPresent': None,
                            'DOVILevel': None,
                            'DOVIPresent': None,
                            'DOVIProfile': None,
                            'DOVIRPUPresent': None,
                            'DOVIVersion': None,
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
                            'scanType': None,
                            'streamIdentifier': None,
                            'width': None
                        },
                        'audioStreams': {
                            'bitrate': None,
                            'codec': None,
                            'default': None,
                            'displayTitle': None,
                            'extendedDisplayTitle': None,
                            'id': None,
                            'index': None,
                            'key': None,
                            'language': None,
                            'languageCode': None,
                            'requiredBandwidths': None,
                            'selected': None,
                            'streamType': None,
                            'title': None,
                            'type': None,
                            'audioChannelLayout': None,
                            'bitDepth': None,
                            'bitrateMode': None,
                            'channels': None,
                            'duration': None,
                            'profile': None,
                            'samplingRate': None,
                            'streamIdentifier': None
                        },
                        'subtitleStreams': {
                            'codec': None,
                            'default': None,
                            'displayTitle': None,
                            'extendedDisplayTitle': None,
                            'id': None,
                            'index': None,
                            'key': None,
                            'language': None,
                            'languageCode': None,
                            'requiredBandwidths': None,
                            'selected': None,
                            'streamType': None,
                            'title': None,
                            'type': None,
                            'container': None,
                            'forced': None,
                            'format': None,
                            'headerCompression': None,
                            'transient': None
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
                'parentYear': None,
                'rating': None,
                'ratingKey': None,
                'seasonEpisode': None,
                'seasonNumber': None,
                'summary': None,
                'thumb': None,
                'thumbBlurHash': None,
                'thumbFile': lambda o: self.get_image(o, 'thumb'),
                'title': None,
                'titleSort': None,
                'type': None,
                'updatedAt': helpers.datetime_to_iso,
                'userRating': None,
                'viewCount': None,
                'viewOffset': None,
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
                'albumSort': None,
                'art': None,
                'artBlurHash': None,
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
                'lastRatedAt': helpers.datetime_to_iso,
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
                'similar': {
                    'id': None,
                    'tag': None
                },
                'styles': {
                    'id': None,
                    'tag': None
                },
                'summary': None,
                'thumb': None,
                'thumbBlurHash': None,
                'thumbFile': lambda o: self.get_image(o, 'thumb'),
                'title': None,
                'titleSort': None,
                'type': None,
                'updatedAt': helpers.datetime_to_iso,
                'userRating': None,
                'viewCount': None,
                'albums': lambda e: self.export_obj(e)
            }
            return _artist_attrs

        def album_attrs():
            _album_attrs = {
                'addedAt': helpers.datetime_to_iso,
                'art': None,
                'artBlurHash': None,
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
                'lastRatedAt': helpers.datetime_to_iso,
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
                'studio': None,
                'styles': {
                    'id': None,
                    'tag': None
                },
                'summary': None,
                'thumb': None,
                'thumbBlurHash': None,
                'thumbFile': lambda o: self.get_image(o, 'thumb'),
                'title': None,
                'titleSort': None,
                'type': None,
                'updatedAt': helpers.datetime_to_iso,
                'userRating': None,
                'viewCount': None,
                'viewedLeafCount': None,
                'year': None,
                'tracks': lambda e: self.export_obj(e)
            }
            return _album_attrs

        def track_attrs():
            _track_attrs = {
                'addedAt': helpers.datetime_to_iso,
                'art': None,
                'artBlurHash': None,
                'chapterSource': None,
                'collections': {
                    'id': None,
                    'tag': None
                },
                'duration': None,
                'durationHuman': lambda o: helpers.human_duration(getattr(o, 'duration', 0)),
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
                'lastRatedAt': helpers.datetime_to_iso,
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
                        'requiredBandwidths': None,
                        'size': None,
                        'sizeHuman': lambda o: helpers.human_file_size(getattr(o, 'size', 0)),
                        'syncItemId': None,
                        'syncState': None,
                        'audioStreams': {
                            'bitrate': None,
                            'codec': None,
                            'default': None,
                            'displayTitle': None,
                            'extendedDisplayTitle': None,
                            'id': None,
                            'index': None,
                            'key': None,
                            'language': None,
                            'languageCode': None,
                            'requiredBandwidths': None,
                            'selected': None,
                            'streamType': None,
                            'title': None,
                            'type': None,
                            'albumGain': None,
                            'albumPeak': None,
                            'albumRange': None,
                            'audioChannelLayout': None,
                            'bitDepth': None,
                            'bitrateMode': None,
                            'channels': None,
                            'duration': None,
                            'endRamp': None,
                            'gain': None,
                            'loudness': None,
                            'lra': None,
                            'peak': None,
                            'profile': None,
                            'samplingRate': None,
                            'startRamp': None
                        },
                        'lyricStreams': {
                            'codec': None,
                            'default': None,
                            'displayTitle': None,
                            'extendedDisplayTitle': None,
                            'id': None,
                            'index': None,
                            'key': None,
                            'language': None,
                            'languageCode': None,
                            'requiredBandwidths': None,
                            'selected': None,
                            'streamType': None,
                            'title': None,
                            'type': None,
                            'format': None,
                            'minLines': None,
                            'provider': None,
                            'timed': None
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
                'thumbBlurHash': None,
                'title': None,
                'titleSort': None,
                'trackNumber': None,
                'type': None,
                'updatedAt': helpers.datetime_to_iso,
                'userRating': None,
                'viewCount': None,
                'viewOffset': None,
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
                'lastRatedAt': helpers.datetime_to_iso,
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
                'userRating': None,
                'photoalbums': lambda o: [self.export_obj(e) for e in getattr(o, 'albums')()],
                'photos': lambda e: self.export_obj(e),
                'clips': lambda e: self.export_obj(e)
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
                'lastRatedAt': helpers.datetime_to_iso,
                'librarySectionID': None,
                'librarySectionKey': None,
                'librarySectionTitle': None,
                'locations': None,
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
                'userRating': None,
                'year': None,
                'media': {
                    'aperture': None,
                    'aspectRatio': None,
                    'container': None,
                    'exposure': None,
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
                'artBlurHash': None,
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
                'lastRatedAt': helpers.datetime_to_iso,
                'librarySectionID': None,
                'librarySectionKey': None,
                'librarySectionTitle': None,
                'maxYear': None,
                'minYear': None,
                'ratingKey': None,
                'subtype': None,
                'summary': None,
                'thumb': None,
                'thumbBlurHash': None,
                'thumbFile': lambda o: self.get_image(o, 'thumb'),
                'title': None,
                'titleSort': None,
                'type': None,
                'updatedAt': helpers.datetime_to_iso,
                'userRating': None,
                'items': lambda e: self.export_obj(e)
            }
            return _collection_attrs

        def playlist_attrs():
            _playlist_attrs = {
                'addedAt': helpers.datetime_to_iso,
                'composite': None,
                'content': None,
                'duration': None,
                'durationHuman': lambda o: helpers.human_duration(getattr(o, 'duration', 0)),
                'guid': None,
                'icon': None,
                'key': None,
                'leafCount': None,
                'playlistType': None,
                'ratingKey': None,
                'smart': None,
                'summary': None,
                'title': None,
                'type': None,
                'updatedAt': helpers.datetime_to_iso,
                'items': lambda e: self.export_obj(e)
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
                    'updatedAt', 'lastViewedAt', 'viewCount', 'lastRatedAt', 'hasPreviewThumbnails'
                ],
                9: self._get_all_metadata_attrs(_media_type)
            }
            _media_info_levels = {
                1: [
                    'locations', 'media.aspectRatio', 'media.audioChannels', 'media.audioCodec', 'media.audioProfile',
                    'media.bitrate', 'media.container', 'media.duration', 'media.height', 'media.width',
                    'media.videoCodec', 'media.videoFrameRate', 'media.videoProfile', 'media.videoResolution',
                    'media.isOptimizedVersion', 'media.hdr'
                ],
                2: [
                    'media.parts.file', 'media.parts.duration',
                    'media.parts.container', 'media.parts.indexes', 'media.parts.size', 'media.parts.sizeHuman',
                    'media.parts.audioProfile', 'media.parts.videoProfile',
                    'media.parts.optimizedForStreaming', 'media.parts.deepAnalysisVersion',
                    'media.parts.hasPreviewThumbnails'
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
                    'media.parts.subtitleStreams.default', 'media.parts.subtitleStreams.container'
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
                    'ratingKey', 'title', 'titleSort', 'originallyAvailableAt', 'originalTitle', 'year', 'addedAt',
                    'rating', 'audienceRating', 'audienceRatingImage', 'userRating', 'contentRating', 'network',
                    'studio', 'tagline', 'summary', 'guid', 'duration', 'durationHuman', 'type', 'childCount',
                    'seasons'
                ],
                2: [
                    'roles.tag', 'roles.role',
                    'genres.tag', 'collections.tag', 'labels.tag',
                    'fields.name', 'fields.locked', 'guids.id'
                ],
                3: [
                    'art', 'thumb', 'banner', 'theme', 'key',
                    'updatedAt', 'lastViewedAt', 'viewCount', 'lastRatedAt'
                ],
                9: self._get_all_metadata_attrs(_media_type)
            }
            _media_info_levels = {}
            return _metadata_levels, _media_info_levels

        def season_levels():
            _media_type = 'season'
            _metadata_levels = {
                1: [
                    'ratingKey', 'title', 'titleSort', 'addedAt', 'year',
                    'userRating',
                    'summary', 'guid', 'type', 'seasonNumber',
                    'parentTitle', 'parentRatingKey', 'parentGuid',
                    'episodes'
                ],
                2: [
                    'collections.tag',
                    'fields.name', 'fields.locked', 'guids.id'
                ],
                3: [
                    'art', 'thumb', 'key',
                    'updatedAt', 'lastViewedAt', 'viewCount', 'lastRatedAt',
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
                    'rating', 'audienceRating', 'audienceRatingImage', 'userRating', 'contentRating',
                    'summary', 'guid', 'duration', 'durationHuman', 'type', 'episodeNumber', 'seasonEpisode',
                    'parentTitle', 'parentRatingKey', 'parentGuid', 'parentYear', 'seasonNumber',
                    'grandparentTitle', 'grandparentRatingKey', 'grandparentGuid', 'hasIntroMarker'
                ],
                2: [
                    'collections.tag', 'directors.tag', 'writers.tag',
                    'fields.name', 'fields.locked', 'guids.id',
                    'markers.type', 'markers.start', 'markers.end'
                ],
                3: [
                    'art', 'thumb', 'key', 'chapterSource',
                    'chapters.tag', 'chapters.index', 'chapters.start', 'chapters.end', 'chapters.thumb',
                    'updatedAt', 'lastViewedAt', 'viewCount', 'lastRatedAt', 'hasPreviewThumbnails',
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
                    'media.isOptimizedVersion', 'media.hdr'
                ],
                2: [
                    'media.parts.file', 'media.parts.duration',
                    'media.parts.container', 'media.parts.indexes', 'media.parts.size', 'media.parts.sizeHuman',
                    'media.parts.audioProfile', 'media.parts.videoProfile',
                    'media.parts.optimizedForStreaming', 'media.parts.deepAnalysisVersion',
                    'media.parts.hasPreviewThumbnails'
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
                    'media.parts.subtitleStreams.default', 'media.parts.subtitleStreams.container'
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
                    'collections.tag', 'genres.tag', 'countries.tag', 'moods.tag', 'similar.tag', 'styles.tag',
                    'fields.name', 'fields.locked'
                ],
                3: [
                    'art', 'thumb', 'key',
                    'updatedAt', 'lastViewedAt', 'viewCount', 'lastRatedAt'
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
                    'rating', 'userRating', 'studio', 'year',
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
                    'updatedAt', 'lastViewedAt', 'viewCount', 'lastRatedAt',
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
                    'summary', 'guid', 'duration', 'durationHuman', 'type', 'trackNumber',
                    'parentTitle', 'parentRatingKey', 'parentGuid', 'parentIndex',
                    'grandparentTitle', 'grandparentRatingKey', 'grandparentGuid'
                ],
                2: [
                    'collections.tag', 'moods.tag',
                    'fields.name', 'fields.locked'
                ],
                3: [
                    'art', 'thumb', 'key',
                    'updatedAt', 'lastViewedAt', 'viewCount', 'lastRatedAt',
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
                    'media.parts.file', 'media.parts.duration',
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
                    'summary', 'guid', 'type', 'index', 'userRating',
                    'photoalbums', 'photos', 'clips'
                ],
                2: [
                    'fields.name', 'fields.locked'
                ],
                3: [
                    'art', 'thumb', 'key',
                    'updatedAt', 'lastRatedAt'
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
                    'summary', 'guid', 'type', 'index', 'userRating',
                    'parentTitle', 'parentRatingKey', 'parentGuid', 'parentIndex',
                    'createdAtAccuracy', 'createdAtTZOffset'
                ],
                2: [
                    'tag.tag', 'tag.title'
                ],
                3: [
                    'thumb', 'key',
                    'updatedAt', 'lastRatedAt',
                    'parentThumb', 'parentKey'
                ],
                9: self._get_all_metadata_attrs(_media_type)
            }
            _media_info_levels = {
                1: [
                    'locations', 'media.aspectRatio', 'media.aperture', 'media.exposure',
                    'media.container', 'media.height', 'media.width',
                    'media.iso', 'media.lens', 'media.make', 'media.model'
                ],
                2: [
                    'media.parts.file',
                    'media.parts.container', 'media.parts.size', 'media.parts.sizeHuman'
                ],
                3: [
                ],
                9: [
                    'locations', 'media'
                ]
            }
            return _metadata_levels, _media_info_levels

        def collection_levels():
            _media_type = 'collection'
            _metadata_levels = {
                1: [
                    'ratingKey', 'title', 'titleSort', 'minYear', 'maxYear', 'addedAt',
                    'contentRating', 'userRating',
                    'summary', 'guid', 'type', 'subtype', 'childCount',
                    'collectionMode', 'collectionSort',
                    'items'
                ],
                2: [
                    'labels.tag',
                    'fields.name', 'fields.locked'
                ],
                3: [
                    'art', 'thumb', 'key',
                    'updatedAt', 'lastRatedAt'
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
        elif self.thumb_level not in self.IMAGE_LEVELS:
            msg = "Export called with invalid thumb_level '{}'.".format(self.thumb_level)
        elif self.art_level not in self.IMAGE_LEVELS:
            msg = "Export called with invalid art_level '{}'.".format(self.art_level)
        elif self.file_format not in self.FILE_FORMATS:
            msg = "Export called with invalid file_format '{}'.".format(self.file_format)
        elif self.export_type not in self.EXPORT_TYPES:
            msg = "Export called with invalid export_type '{}'.".format(self.export_type)
        elif self.user_id and self.export_type != 'playlist':
            msg = "Export called with invalid export_type '{}'. " \
                  "Only export_type 'playlist' is allowed for user export."
        elif self.individual_files and self.rating_key:
            msg = "Individual file export is only allowed for library or user export."

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

        plex = Plex(token=plex_token)

        if self.rating_key:
            logger.debug(
                "Tautulli Exporter :: Export called with rating_key %s, "
                "metadata_level %d, media_info_level %d, thumb_level %s, art_level %s, "
                "file_format %s",
                self.rating_key, self.metadata_level, self.media_info_level,
                self.thumb_level, self.art_level, self.file_format)

            self.obj = plex.get_item(self.rating_key)
            self.media_type = self._media_type(self.obj)

            if self.media_type != 'playlist':
                self.section_id = self.obj.librarySectionID

            if self.media_type in ('season', 'episode', 'album', 'track'):
                self.obj_title = self.obj._defaultSyncTitle()
            else:
                self.obj_title = self.obj.title

        elif self.user_id:
            logger.debug(
                "Tautulli Exporter :: Export called with user_id %s, "
                "metadata_level %d, media_info_level %d, thumb_level %s, art_level %s, "
                "export_type %s, file_format %s",
                self.user_id, self.metadata_level, self.media_info_level,
                self.thumb_level, self.art_level, self.export_type, self.file_format)

            self.obj = plex.PlexServer
            self.media_type = self.export_type

            self.obj_title = user_info['username']

        elif self.section_id:
            logger.debug(
                "Tautulli Exporter :: Export called with section_id %s, "
                "metadata_level %d, media_info_level %d, thumb_level %s, art_level %s, "
                "export_type %s, file_format %s",
                self.section_id, self.metadata_level, self.media_info_level,
                self.thumb_level, self.art_level, self.export_type, self.file_format)

            self.obj = plex.get_library(self.section_id)
            if self.export_type == 'all':
                self.media_type = self.obj.type
            else:
                self.media_type = self.export_type

            self.obj_title = self.obj.title

        else:
            msg = "Export called but no section_id, user_id, or rating_key provided."
            logger.error("Tautulli Exporter :: %s", msg)
            return msg

        if self.media_type not in self.MEDIA_TYPES:
            msg = "Cannot export media type '{}'.".format(self.media_type)
            logger.error("Tautulli Exporter :: %s", msg)
            return msg

        if not self.MEDIA_TYPES[self.media_type][0]:
            self.thumb_level = 0
        if not self.MEDIA_TYPES[self.media_type][1]:
            self.art_level = 0

        self._process_custom_fields()

        self.directory = self._filename(directory=True)
        self.filename = self._filename()
        self.title = self._filename(extension=False)

        self.export_id = self.add_export()
        if not self.export_id:
            msg = "Failed to export '{}'.".format(self.directory)
            logger.error("Tautulli Exporter :: %s", msg)
            return msg

        threading.Thread(target=self._real_export).start()

        return True

    def add_export(self):
        keys = {
            'timestamp': self.timestamp,
            'section_id': self.section_id,
            'user_id': self.user_id,
            'rating_key': self.rating_key,
            'media_type': self.media_type
        }

        values = {
            'title': self.title,
            'file_format': self.file_format,
            'metadata_level': self.metadata_level,
            'media_info_level': self.media_info_level,
            'thumb_level': self.thumb_level,
            'art_level': self.art_level,
            'custom_fields': self.custom_fields,
            'individual_files': self.individual_files
        }

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

        keys = {
            'id': self.export_id
        }
        values = {
            'thumb_level': self.thumb_level,
            'art_level': self.art_level,
            'complete': complete,
            'file_size': self.file_size
        }

        db = database.MonitorDatabase()
        db.upsert(table_name='exports', key_dict=keys, value_dict=values)

    def set_export_progress(self):
        keys = {
            'id': self.export_id
        }
        values = {
            'total_items': self.total_items,
            'exported_items': self.exported_items
        }

        db = database.MonitorDatabase()
        db.upsert(table_name='exports', key_dict=keys, value_dict=values)

    def _real_export(self):
        logger.info("Tautulli Exporter :: Starting export for '%s'...", self.title)

        if self.rating_key:
            items = [self.obj]
        elif self.user_id:
            # Only playlists export allowed for users
            items = self.obj.playlists()
        else:
            method = getattr(self.obj, self.export_type)
            items = method()

        self.total_items = len(items)
        logger.info("Tautulli Exporter :: Exporting %d item(s).", self.total_items)

        pool = ThreadPool(processes=plexpy.CONFIG.EXPORT_THREADS)
        items = [ExportObject(self, item) for item in items]

        try:
            result = pool.map(self._do_export, items)

            if self.individual_files:
                for item, item_result in zip(items, result):
                    self._save_file([item_result], obj=item)
                    self._exported_images(item.title)

            else:
                self._save_file(result, obj=self)
                self._exported_images(self.title)

            self.thumb_level = self.thumb_level or 10 if self.exported_thumb else 0
            self.art_level = self.art_level or 10 if self.exported_art else 0

            self.file_size += sum(item.file_size for item in items)

            self.success = True

            dirpath = get_export_dirpath(self.directory)
            logger.info("Tautulli Exporter :: Successfully exported to '%s'", dirpath)

        except Exception as e:
            logger.exception("Tautulli Exporter :: Failed to export '%s': %s", self.title, e)

        finally:
            pool.close()
            pool.join()
            self.set_export_state()

    def _do_export(self, item):
        result = item._export_obj()
        self.exported_items += 1
        self.set_export_progress()
        return result

    def _save_file(self, result, obj=None):
        filename = obj.filename
        dirpath = get_export_dirpath(self.directory)
        filepath = os.path.join(dirpath, filename)

        if not os.path.exists(dirpath):
            os.makedirs(dirpath)

        if self.file_format == 'csv':
            csv_data = helpers.flatten_dict(result)
            csv_headers = sorted(set().union(*csv_data), key=helpers.sort_attrs)
            # Move ratingKey, title, and titleSort to front of headers
            for key in ('titleSort', 'title', 'ratingKey'):
                csv_headers = helpers.move_to_front(csv_headers, key)
            with open(filepath, 'w', encoding='utf-8', newline='') as outfile:
                writer = csv.DictWriter(outfile, csv_headers)
                writer.writeheader()
                writer.writerows(csv_data)

        elif self.file_format == 'json':
            json_data = json.dumps(helpers.sort_obj(result), indent=4, ensure_ascii=False)
            with open(filepath, 'w', encoding='utf-8') as outfile:
                outfile.write(json_data)

        elif self.file_format == 'xml':
            xml_data = self.data_to_xml(result, obj)
            with open(filepath, 'w', encoding='utf-8') as outfile:
                outfile.write(xml_data)

        elif self.file_format == 'm3u8':
            m3u8_data = self.data_to_m3u8(result, obj)
            with open(filepath, 'w', encoding='utf-8') as outfile:
                outfile.write(m3u8_data)

        self.file_size += os.path.getsize(filepath)

    def _exported_images(self, title):
        images_dirpath = get_export_dirpath(self.directory, images_directory=title)

        if os.path.exists(images_dirpath):
            for f in os.listdir(images_dirpath):
                if f.endswith('.thumb.jpg'):
                    self.exported_thumb = True
                elif f.endswith('.art.jpg'):
                    self.exported_art = True

    def _media_type(self, obj):
        return 'photoalbum' if self.is_photoalbum(obj) else obj.type

    def _filename(self, obj=None, directory=False, extension=True):
        if obj:
            media_type = self._media_type(obj)
            if media_type in ('season', 'episode', 'album', 'track'):
                title = obj._defaultSyncTitle()
            else:
                title = obj.title
            filename = '{} - {} [{}]'.format(
                media_type.capitalize(), title, obj.ratingKey)

        elif self.rating_key:
            filename = '{} - {} [{}]'.format(
                self.media_type.capitalize(), self.obj_title, self.rating_key)

        elif self.user_id:
            filename = 'User - {} - {} [{}]'.format(
                self.obj_title, self.export_type.capitalize(), self.user_id)

        elif self.section_id:
            filename = 'Library - {} - {} [{}]'.format(
                self.obj_title, self.export_type.capitalize(), self.section_id)

        else:
            filename = 'Export - Unknown'

        filename = helpers.clean_filename(filename)
        if directory:
            return format_export_directory(filename, self.timestamp)
        elif extension:
            return format_export_filename(filename, self.file_format)
        return filename

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

        for tree in self.TREE_MEDIA_TYPES:
            for child_media_type, parent_media_type in zip(tree[:-1], tree[1:]):
                if child_media_type in self._custom_fields:
                    plural_child_media_type = self.PLURAL_MEDIA_TYPES[child_media_type]
                    if parent_media_type in self._custom_fields:
                        self._custom_fields[parent_media_type].add(plural_child_media_type)
                    else:
                        self._custom_fields[parent_media_type] = {plural_child_media_type}

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

        if self.thumb_level:
            if 'thumbFile' in media_attrs and self.MEDIA_TYPES[media_type][0]:
                export_attrs_set.add('thumbFile')
        if self.art_level:
            if 'artFile' in media_attrs and self.MEDIA_TYPES[media_type][1]:
                export_attrs_set.add('artFile')

        if media_type in self._custom_fields:
            export_attrs_set.update(self._custom_fields[media_type])

        for child_media_type in self.CHILD_MEDIA_TYPES.get(media_type):
            if child_media_type in self._custom_fields:
                export_attrs_set.add(self.PLURAL_MEDIA_TYPES[child_media_type])

        if media_type != self.media_type:
            if self.media_type == 'collection' and 'item' in self._custom_fields:
                export_attrs_set.update(self._custom_fields['item'])
            elif self.media_type == 'playlist' and 'item' in self._custom_fields:
                export_attrs_set.update(self._custom_fields['item'])

        if 'media.parts.accessible' in export_attrs_set or 'media.parts.exists' in export_attrs_set or \
                self.media_info_level == 9:
            self._reload_check_files = True

        for attr in export_attrs_set:
            try:
                value = helpers.get_dict_value_by_path(media_attrs, attr)
            except (KeyError, TypeError):
                logger.warn("Tautulli Exporter :: Unknown export attribute '%s', skipping...", attr)
                continue

            export_attrs_list.append(value)

        return reduce(helpers.dict_merge, export_attrs_list, {})

    @staticmethod
    def is_media_info_attr(attr):
        return attr.startswith('media.') or attr == 'locations'

    @staticmethod
    def is_photoalbum(obj):
        return obj.type == 'photo' and obj.TAG == 'Directory'

    def data_to_xml(self, data, obj):
        xml_metadata = {obj.media_type: helpers.sort_obj(data), 'title': obj.title, 'type': obj.media_type}
        if obj.rating_key:
            xml_metadata['ratingKey'] = obj.rating_key
        if obj.user_id:
            xml_metadata['userID'] = obj.user_id
        if obj.section_id:
            xml_metadata['sectionID'] = obj.section_id

        return helpers.dict_to_xml(xml_metadata, root_node='export', indent=4)

    def data_to_m3u8(self, data, obj):
        items = self._get_m3u8_items(data)

        m3u8_metadata = {'title': obj.title, 'type': obj.media_type}
        if obj.rating_key:
            m3u8_metadata['ratingKey'] = obj.rating_key
        if obj.user_id:
            m3u8_metadata['userID'] = obj.user_id
        if obj.section_id:
            m3u8_metadata['sectionID'] = obj.section_id

        m3u8 = '#EXTM3U\n'
        m3u8 += '# Playlist: {title}\n# {metadata}\n\n'.format(title=obj.title, metadata=json.dumps(m3u8_metadata))
        m3u8_item_template = '# {metadata}\n#EXTINF:{duration},{title}\n{location}\n'
        m3u8_items = []

        for item in items:
            m3u8_values = {
                'duration': item.pop('duration'),
                'title': item.pop('title'),
                'location': item.pop('location'),
                'metadata': json.dumps(item)
            }
            m3u8_items.append(m3u8_item_template.format(**m3u8_values))

        m3u8 = m3u8 + '\n'.join(m3u8_items)

        return m3u8

    def _get_m3u8_items(self, data):
        items = []

        for d in data:
            if d.get('locations', []):
                if 'grandparentTitle' in d:
                    full_title = '{} - {}'.format(d.get('originalTitle') or d['grandparentTitle'], d['title'])
                else:
                    full_title = d['title']
                metadata = {
                    'type': d['type'],
                    'ratingKey': d['ratingKey'],
                    'duration': d.get('duration', 5),
                    'title': full_title,
                    'location': '\n'.join(d['locations'])  # Add all locations
                }
                items.append(metadata)

            for child_media_type in self.CHILD_MEDIA_TYPES[d['type']]:
                child_locations = self._get_m3u8_items(d[self.PLURAL_MEDIA_TYPES[child_media_type]])
                items.extend(child_locations)

        return items

    def _export_obj(self):
        pass

    def export_obj(self, obj):
        media_type = self._media_type(obj)
        export_attrs = self._get_export_attrs(media_type)

        # Reload ~plexapi.base.PlexPartialObject
        if hasattr(obj, 'isPartialObject') and obj.isPartialObject():
            obj = obj.reload(checkFiles=self._reload_check_files)

        return helpers.get_attrs_to_dict(obj, attrs=export_attrs)

    def get_any_hdr(self, item, media_type):
        root = self.return_attrs(media_type)['media']
        attrs = helpers.get_dict_value_by_path(root, 'parts.videoStreams.hdr')
        media = helpers.get_attrs_to_dict(item, attrs)
        return any(vs.get('hdr') for p in media.get('parts', []) for vs in p.get('videoStreams', []))

    def get_image(self, item, image):
        media_type = item.type
        rating_key = item.ratingKey

        export_image = True
        if self.thumb_level == 1 or self.art_level == 1:
            posters = item.arts() if image == 'art' else item.posters()
            export_image = any(poster.selected and poster.ratingKey.startswith('upload://')
                               for poster in posters)
        elif self.thumb_level == 2 or self.art_level == 2:
            export_image = any(field.locked and field.name == image
                               for field in item.fields)
        elif self.thumb_level == 9 or self.art_level == 9:
            export_image = True

        if not export_image and image + 'File' in self._custom_fields.get(media_type, set()):
            export_image = True

        if not export_image:
            return

        image_url = None
        if image == 'thumb':
            image_url = item.thumbUrl
        elif image == 'art':
            image_url = item.artUrl
        elif image == 'banner':
            image_url = item.bannerUrl

        if not image_url:
            return

        r = requests.get(image_url, stream=True)
        if r.status_code != 200:
            return

        if media_type in ('season', 'episode', 'album', 'track'):
            item_title = item._defaultSyncTitle()
        else:
            item_title = item.title

        dirpath = get_export_dirpath(self.directory, images_directory=self.title)
        filename = helpers.clean_filename('{} [{}].{}.jpg'.format(item_title, rating_key, image))
        filepath = os.path.join(dirpath, filename)

        if not os.path.exists(dirpath):
            os.makedirs(dirpath)

        with open(filepath, 'wb') as outfile:
            for chunk in r:
                outfile.write(chunk)

        self.file_size += os.path.getsize(filepath)

        return os.path.join(os.path.basename(dirpath), filename)


class ExportObject(Export):
    def __init__(self, export, obj):
        super(ExportObject, self).__init__()
        self.__dict__.update(export.__dict__)

        self.obj = obj
        self.rating_key = self.obj.ratingKey
        self.filename = self._filename(obj=self.obj)
        self.title = self._filename(obj=self.obj, extension=False)

    def _export_obj(self):
        result = self.export_obj(self.obj)
        self.obj = None  # Clear the object to prevent memory leak
        return result


def get_export(export_id):
    db = database.MonitorDatabase()
    result = db.select_single('SELECT timestamp, title, file_format, thumb_level, art_level, '
                              'individual_files, complete '
                              'FROM exports WHERE id = ?',
                              [export_id])

    if result:
        if result['individual_files']:
            result['filename'] = None
            result['exists'] = check_export_exists(result['title'], result['timestamp'])
        else:
            result['filename'] = '{}.{}'.format(result['title'], result['file_format'])
            result['exists'] = check_export_exists(result['title'], result['timestamp'], result['filename'])

    return result


def delete_export(export_id):
    if str(export_id).isdigit():
        deleted = True

        result = get_export(export_id=export_id)
        if result and check_export_exists(result['title'], result['timestamp']):  # Only check if folder exists
            dirpath = get_export_dirpath(result['title'], result['timestamp'])
            logger.info("Tautulli Exporter :: Deleting export '%s'.", dirpath)
            try:
                shutil.rmtree(dirpath, ignore_errors=True)
            except OSError as e:
                logger.error("Tautulli Exporter :: Failed to delete export '%s': %s", dirpath, e)
                deleted = False

        if deleted:
            logger.info("Tautulli Exporter :: Deleting export_id %s from the database.", export_id)
            db = database.MonitorDatabase()
            result = db.action('DELETE FROM exports WHERE id = ?', args=[export_id])

        return deleted
    else:
        return False


def delete_all_exports():
    logger.info("Tautulli Exporter :: Deleting all exports from the export directory.")

    export_dir = plexpy.CONFIG.EXPORT_DIR
    try:
        shutil.rmtree(export_dir, ignore_errors=True)
    except OSError as e:
        logger.error("Tautulli Exporter :: Failed to delete export directory '%s': %s", export_dir, e)

    if not os.path.exists(export_dir):
        os.makedirs(export_dir)

    database.delete_exports()
    return True


def cancel_exports():
    db = database.MonitorDatabase()
    db.action('UPDATE exports SET complete = -1 WHERE complete = 0')


def get_export_datatable(section_id=None, user_id=None, rating_key=None, kwargs=None):
    default_return = {'recordsFiltered': 0,
                      'recordsTotal': 0,
                      'draw': 0,
                      'data': []}

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
               'CASE WHEN exports.media_type = "photoalbum" THEN "Photo Album" ELSE '
               'UPPER(SUBSTR(exports.media_type, 1, 1)) || SUBSTR(exports.media_type, 2) END '
               'AS media_type_title',
               'exports.title',
               'exports.file_format',
               'exports.metadata_level',
               'exports.media_info_level',
               'exports.thumb_level',
               'exports.art_level',
               'exports.custom_fields',
               'exports.individual_files',
               'exports.file_size',
               'exports.complete',
               'exports.total_items',
               'exports.exported_items'
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
        if item['individual_files']:
            filename = None
            exists = check_export_exists(item['title'], item['timestamp'])
        else:
            filename = format_export_filename(item['title'], item['file_format'])
            exists = check_export_exists(item['title'], item['timestamp'], filename)

        row = {'export_id': item['export_id'],
               'timestamp': item['timestamp'],
               'section_id': item['section_id'],
               'user_id': item['user_id'],
               'rating_key': item['rating_key'],
               'media_type': item['media_type'],
               'media_type_title': item['media_type_title'],
               'title': item['title'],
               'filename': filename,
               'file_format': item['file_format'],
               'metadata_level': item['metadata_level'],
               'media_info_level': item['media_info_level'],
               'thumb_level': item['thumb_level'],
               'art_level': item['art_level'],
               'custom_fields': item['custom_fields'],
               'individual_files': item['individual_files'],
               'file_size': item['file_size'],
               'complete': item['complete'],
               'exported_items': item['exported_items'],
               'total_items': item['total_items'],
               'exists': exists
               }

        rows.append(row)

    result = {'recordsFiltered': query['filteredCount'],
              'recordsTotal': query['totalCount'],
              'data': rows,
              'draw': query['draw']
              }

    return result


def format_export_directory(title, timestamp):
    return '{}.{}'.format(title, helpers.timestamp_to_YMDHMS(timestamp))


def format_export_filename(title, file_format):
    return '{}.{}'.format(title, file_format)


def get_export_dirpath(title, timestamp=None, images_directory=None):
    if timestamp:
        title = format_export_directory(title, timestamp)
    dirpath = os.path.join(plexpy.CONFIG.EXPORT_DIR, title)
    if images_directory:
        dirpath = os.path.join(dirpath, '{}.images'.format(images_directory))
    return dirpath


def get_export_filepath(title, timestamp, filename):
    dirpath = get_export_dirpath(title, timestamp)
    return os.path.join(dirpath, filename)


def check_export_exists(title, timestamp, filename=None):
    if filename:
        return os.path.isfile(get_export_filepath(title, timestamp, filename))
    return os.path.isdir(get_export_dirpath(title, timestamp))


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
                if child_media_type == 'item':
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


def build_export_docs():
    export = Export()

    section_head = '### <a id="{anchor}">{section}</a>\n\n'
    section_details = '<details>\n' \
                      '<summary><strong>{field_type} Fields</strong></summary><br>\n\n' \
                      '{table}\n' \
                      '</details>'

    table_head = '| {field_type} Field | Level 0 | Level 1 | Level 2 | Level 3 | Level 9 |\n' \
                 '| :--- | :---: | :---: | :---: | :---: | :---: |\n'
    table_row = '| `{attr}` | {level0} | {level1} | {level2} | {level3} | {level9} |'

    def _child_rows(_media_type):
        child_table_rows = []
        for child_media_type in export.CHILD_MEDIA_TYPES[_media_type]:
            child_plural_media_type = export.PLURAL_MEDIA_TYPES[child_media_type]
            if child_media_type == 'photoalbum':
                child_section_title = 'Photo Albums'
            else:
                child_section_title = child_plural_media_type.capitalize()
            child_text = u'\u2713<br>Includes [{}](#{}-{}) Level {{}}'.format(
                child_section_title, media_type, child_media_type)
            child_row = {
                'attr': child_plural_media_type,
                'level0': '',
                'level1': child_text.format(1),
                'level2': child_text.format(2),
                'level3': child_text.format(3),
                'level9': child_text.format(9),
            }
            child_table_rows.append(table_row.format(**child_row))
        return child_table_rows

    contents = []
    sections = []

    for media_type, (thumb, art) in export.MEDIA_TYPES.items():
        if media_type == 'photoalbum':
            section_title = 'Photo Albums'
        else:
            section_title = export.PLURAL_MEDIA_TYPES[media_type].capitalize()

        details = []
        table_child_rows = _child_rows(media_type)

        metadata_levels_map, media_info_levels_map = export.return_attrs_level_map(media_type)

        # Metadata Fields table
        table_rows = []
        for attr, level in sorted(metadata_levels_map.items(), key=helpers.sort_attrs):
            if thumb and attr == 'thumbFile' or art and attr == 'artFile':
                text = 'Refer to [Image Exports](#image-export)'
                row = {
                    'attr': attr,
                    'level0': text,
                    'level1': '',
                    'level2': '',
                    'level3': '',
                    'level9': ''
                }
            else:
                row = {
                    'attr': attr,
                    'level0': u'\u2713' if level <= 0 else '',
                    'level1': u'\u2713' if level <= 1 else '',
                    'level2': u'\u2713' if level <= 2 else '',
                    'level3': u'\u2713' if level <= 3 else '',
                    'level9': u'\u2713' if level <= 9 else ''
                }
            table_rows.append(table_row.format(**row))
        table_rows += table_child_rows
        metadata_table = table_head.format(field_type='Metadata') + '\n'.join(table_rows)
        details.append(section_details.format(field_type='Metadata', table=metadata_table))

        # Media Info Fields table
        table_rows = []
        for attr, level in sorted(media_info_levels_map.items(), key=helpers.sort_attrs):
            row = {
                'attr': attr,
                'level0': u'\u2713' if level <= 0 else '',
                'level1': u'\u2713' if level <= 1 else '',
                'level2': u'\u2713' if level <= 2 else '',
                'level3': u'\u2713' if level <= 3 else '',
                'level9': u'\u2713' if level <= 9 else ''
            }
            table_rows.append(table_row.format(**row))
        table_rows += table_child_rows
        media_info_table = table_head.format(field_type='Media Info') + '\n'.join(table_rows)
        details.append(section_details.format(field_type='Media Info', table=media_info_table))

        section = section_head.format(anchor=media_type, section=section_title) + '\n\n'.join(details)

        if media_type == 'collection':
            section += '\n\n* <a id="collection-item">**Note:**</a> Collection `items` can be [Movies](#movie) or [Shows](#show) ' \
                       'depending on the collection.'
        elif media_type == 'playlist':
            section += '\n\n* <a id="playlist-item">**Note:**</a> Playlist `items` can be [Movies](#movie), [Episodes](#episode), ' \
                       '[Tracks](#track), or [Photos](#photo) depending on the playlist.'

        sections.append(section)

    docs = '\n\n\n'.join(sections)
    return helpers.sanitize(docs)
