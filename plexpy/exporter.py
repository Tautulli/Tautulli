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

import csv
import json
import os

from functools import partial
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


MOVIE_ATTRS = {
    'addedAt': helpers.datetime_to_iso,
    'art': None,
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
            'optimizedForStreaming': None,
            'requiredBandwidths': lambda e: [int(b) for b in e.split(',')] if e else None,
            'syncItemId': None,
            'syncState': None,
            'videoProfile': None,
            'videoStreams': {
                'codec': None,
                'codecID': None,
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
                'height': None,
                'level': None,
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

SHOW_ATTRS = {
    'addedAt': helpers.datetime_to_iso,
    'art': None,
    'banner': None,
    'childCount': None,
    'collections': {
        'id': None,
        'tag': None
    },
    'contentRating': None,
    'duration': None,
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
    'title': None,
    'titleSort': None,
    'type': None,
    'updatedAt': helpers.datetime_to_iso,
    'userRating': None,
    'viewCount': None,
    'viewedLeafCount': None,
    'year': None,
    'seasons': lambda e: helpers.get_attrs_to_dict(e, MEDIA_TYPES[e.type])
}

SEASON_ATTRS = {
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
    'title': None,
    'titleSort': None,
    'type': None,
    'updatedAt': helpers.datetime_to_iso,
    'userRating': None,
    'viewCount': None,
    'viewedLeafCount': None,
    'episodes': lambda e: helpers.get_attrs_to_dict(e, MEDIA_TYPES[e.type])
}

EPISODE_ATTRS = {
    'addedAt': helpers.datetime_to_iso,
    'art': None,
    'chapterSource': None,
    'contentRating': None,
    'directors': {
        'id': None,
        'tag': None
    },
    'duration': None,
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
            'optimizedForStreaming': None,
            'requiredBandwidths': lambda e: [int(b) for b in e.split(',')] if e else None,
            'syncItemId': None,
            'syncState': None,
            'videoProfile': None,
            'videoStreams': {
                'codec': None,
                'codecID': None,
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
                'height': None,
                'level': None,
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

ARTIST_ATTRS = {
    'addedAt': helpers.datetime_to_iso,
    'art': None,
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
    'moods':  {
        'id': None,
        'tag': None
    },
    'rating': None,
    'ratingKey': None,
    'styles':  {
        'id': None,
        'tag': None
    },
    'summary': None,
    'thumb': None,
    'title': None,
    'titleSort': None,
    'type': None,
    'updatedAt': helpers.datetime_to_iso,
    'userRating': None,
    'viewCount': None,
    'albums': lambda e: helpers.get_attrs_to_dict(e, MEDIA_TYPES[e.type])
}

ALBUM_ATTRS = {
    'addedAt': helpers.datetime_to_iso,
    'art': None,
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
    'moods':  {
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
    'styles':  {
        'id': None,
        'tag': None
    },
    'summary': None,
    'thumb': None,
    'title': None,
    'titleSort': None,
    'type': None,
    'updatedAt': helpers.datetime_to_iso,
    'userRating': None,
    'viewCount': None,
    'viewedLeafCount': None,
    'tracks': lambda e: helpers.get_attrs_to_dict(e, MEDIA_TYPES[e.type])
}

TRACK_ATTRS = {
    'addedAt': helpers.datetime_to_iso,
    'art': None,
    'duration': None,
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
            'requiredBandwidths': lambda e: [int(b) for b in e.split(',')] if e else None,
            'syncItemId': None,
            'syncState': None,
            'audioStreams': {
                'codec': None,
                'codecID': None,
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
    'moods':  {
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

PHOTO_ALBUM_ATTRS = {
    # For some reason photos needs to be first,
    # otherwise the photo album ratingKey gets
    # clobbered by the first photo's ratingKey
    'photos': lambda e: helpers.get_attrs_to_dict(e, MEDIA_TYPES[e.type]),
    'addedAt': helpers.datetime_to_iso,
    'art': None,
    'composite': None,
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
    'type': None,
    'updatedAt': helpers.datetime_to_iso
}

PHOTO_ATTRS = {
    'addedAt': helpers.datetime_to_iso,
    'createdAtAccuracy': None,
    'createdAtTZOffset': None,
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
            'size': None
        }
    },
    'tag': {
        'id': None,
        'tag': None,
        'title': None
    }
}

COLLECTION_ATTRS = {
    'addedAt': helpers.datetime_to_iso,
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
    'title': None,
    'type': None,
    'updatedAt': helpers.datetime_to_iso,
    'children': lambda e: helpers.get_attrs_to_dict(e, MEDIA_TYPES[e.type])
}

PLAYLIST_ATTRS = {
    'addedAt': helpers.datetime_to_iso,
    'composite': None,
    'duration': None,
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
    'items': lambda e: helpers.get_attrs_to_dict(e, MEDIA_TYPES[e.type])
}

MEDIA_TYPES = {
    'movie': MOVIE_ATTRS,
    'show': SHOW_ATTRS,
    'season': SEASON_ATTRS,
    'episode': EPISODE_ATTRS,
    'artist': ARTIST_ATTRS,
    'album': ALBUM_ATTRS,
    'track': TRACK_ATTRS,
    'photo album': PHOTO_ALBUM_ATTRS,
    'photo': PHOTO_ATTRS,
    'collection': COLLECTION_ATTRS,
    'playlist': PLAYLIST_ATTRS
}


def export(section_id=None, rating_key=None, file_format='json'):
    timestamp = helpers.timestamp()

    if not section_id and not rating_key:
        logger.error("Tautulli Exporter :: Export called but no section_id or rating_key provided.")
        return
    elif section_id and not str(section_id).isdigit():
        logger.error("Tautulli Exporter :: Export called with invalid section_id '%s'.", section_id)
        return
    elif rating_key and not str(rating_key).isdigit():
        logger.error("Tautulli Exporter :: Export called with invalid rating_key '%s'.", rating_key)
        return
    elif file_format not in ('json', 'csv'):
        logger.error("Tautulli Exporter :: Export called but invalid file_format '%s' provided.", file_format)
        return

    plex = Plex(plexpy.CONFIG.PMS_URL, plexpy.CONFIG.PMS_TOKEN)

    if section_id:
        logger.debug("Tautulli Exporter :: Exporting called with section_id %s", section_id)

        library = plex.get_library(section_id)
        media_type = library.type
        library_title = library.title
        filename = 'Library - {} [{}].{}.{}'.format(
            library_title, section_id, helpers.timestamp_to_YMDHMS(timestamp), file_format)
        items = library.all()

    elif rating_key:
        logger.debug("Tautulli Exporter :: Exporting called with rating_key %s", rating_key)

        item = plex.get_item(helpers.cast_to_int(rating_key))
        media_type = item.type
        section_id = item.librarySectionID

        if media_type in ('season', 'episode', 'album', 'track'):
            item_title = item._defaultSyncTitle()
        else:
            item_title = item.title

        if media_type == 'photo' and item.TAG == 'Directory':
            media_type = 'photo album'

        filename = '{} - {} [{}].{}.{}'.format(
            media_type.title(), item_title, rating_key, helpers.timestamp_to_YMDHMS(timestamp), file_format)

        items = [item]

    else:
        return

    filename = helpers.clean_filename(filename)
    filepath = os.path.join(plexpy.CONFIG.EXPORT_DIR, filename)
    logger.info("Tautulli Exporter :: Starting export for '%s'...", filename)

    export_id = set_export_state(timestamp=timestamp,
                                 section_id=section_id,
                                 rating_key=rating_key,
                                 media_type=media_type,
                                 file_format=file_format,
                                 filename=filename)
    if not export_id:
        logger.error("Tautulli Exporter :: Failed to export '%s'", filename)
        return

    attrs = MEDIA_TYPES[media_type]
    part = partial(helpers.get_attrs_to_dict, attrs=attrs)

    with ThreadPool(processes=4) as pool:
        result = pool.map(part, items)

    if file_format == 'json':
        with open(filepath, 'w', encoding='utf-8') as outfile:
            json.dump(result, outfile, indent=4, ensure_ascii=False, sort_keys=True)

    elif file_format == 'csv':
        flatten_result = helpers.flatten_dict(result)
        flatten_attrs = helpers.flatten_dict(attrs)
        with open(filepath, 'w', encoding='utf-8', newline='') as outfile:
            writer = csv.DictWriter(outfile, sorted(flatten_attrs[0].keys()))
            writer.writeheader()
            writer.writerows(flatten_result)

    set_export_complete(export_id=export_id)
    logger.info("Tautulli Exporter :: Successfully exported to '%s'", filepath)


def set_export_state(timestamp, section_id, rating_key, media_type, file_format, filename):
    keys = {'timestamp': timestamp,
            'section_id': section_id,
            'rating_key': rating_key,
            'media_type': media_type}

    values = {'file_format': file_format,
              'filename': filename}

    db = database.MonitorDatabase()
    try:
        db.upsert(table_name='exports', key_dict=keys, value_dict=values)
        return db.last_insert_id()
    except Exception as e:
        logger.error("Tautulli Exporter :: Unable to save export to database: %s", e)
        return False


def set_export_complete(export_id):
    keys = {'id': export_id}
    values = {'complete': 1}

    db = database.MonitorDatabase()
    db.upsert(table_name='exports', key_dict=keys, value_dict=values)


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

    columns = ['exports.id AS row_id',
               'exports.timestamp',
               'exports.section_id',
               'exports.rating_key',
               'exports.media_type',
               'exports.file_format',
               'exports.filename',
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
        logger.warn("Tautulli Exporter :: Unable to execute database query for get_export_datatable: %s." % e)
        return default_return

    result = query['result']

    rows = []
    for item in result:
        media_type_title = item['media_type'].title()
        filepath = os.path.join(plexpy.CONFIG.EXPORT_DIR, item['filename'])
        exists = helpers.cast_to_int(os.path.isfile(filepath))

        row = {'row_id': item['row_id'],
               'timestamp': item['timestamp'],
               'section_id': item['section_id'],
               'rating_key': item['rating_key'],
               'media_type': item['media_type'],
               'media_type_title': media_type_title,
               'file_format': item['file_format'],
               'filename': item['filename'],
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
