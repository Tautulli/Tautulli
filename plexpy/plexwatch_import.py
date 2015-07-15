# This file is part of PlexPy.
#
#  PlexPy is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  PlexPy is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with PlexPy.  If not, see <http://www.gnu.org/licenses/>.

import sqlite3

from plexpy import logger, helpers, monitor, datafactory, plextv
from xml.dom import minidom

import plexpy

def extract_plexwatch_xml(xml=None):
    output = {}
    clean_xml = helpers.latinToAscii(xml)
    try:
        xml_parse = minidom.parseString(clean_xml)
    except:
        logger.warn("Error parsing XML for Plexwatch database.")
        return None

    xml_head = xml_parse.getElementsByTagName('opt')
    if not xml_head:
        logger.warn("Error parsing XML for Plexwatch database.")
        return None

    for a in xml_head:
        added_at = helpers.get_xml_attr(a, 'addedAt')
        art = helpers.get_xml_attr(a, 'art')
        duration = helpers.get_xml_attr(a, 'duration')
        grandparent_thumb = helpers.get_xml_attr(a, 'grandparentThumb')
        grandparent_title = helpers.get_xml_attr(a, 'grandparentTitle')
        guid = helpers.get_xml_attr(a, 'guid')
        media_index = helpers.get_xml_attr(a, 'index')
        originally_available_at = helpers.get_xml_attr(a, 'originallyAvailableAt')
        last_viewed_at = helpers.get_xml_attr(a, 'lastViewedAt')
        parent_media_index = helpers.get_xml_attr(a, 'parentIndex')
        parent_thumb = helpers.get_xml_attr(a, 'parentThumb')
        rating = helpers.get_xml_attr(a, 'rating')
        thumb = helpers.get_xml_attr(a, 'thumb')
        media_type = helpers.get_xml_attr(a, 'type')
        updated_at = helpers.get_xml_attr(a, 'updatedAt')
        view_offset = helpers.get_xml_attr(a, 'viewOffset')
        year = helpers.get_xml_attr(a, 'year')
        parent_title = helpers.get_xml_attr(a, 'parentTitle')
        studio = helpers.get_xml_attr(a, 'studio')
        title = helpers.get_xml_attr(a, 'title')

        directors = []
        if a.getElementsByTagName('Director'):
            director_elem = a.getElementsByTagName('Director')
            for b in director_elem:
                directors.append(helpers.get_xml_attr(b, 'tag'))

        aspect_ratio = ''
        audio_channels = None
        audio_codec = ''
        bitrate = None
        container = ''
        height = None
        video_codec = ''
        video_framerate = ''
        video_resolution = ''
        width = None

        if a.getElementsByTagName('Media'):
            media_elem = a.getElementsByTagName('Media')
            for c in media_elem:
                aspect_ratio = helpers.get_xml_attr(c, 'aspectRatio')
                audio_channels = helpers.get_xml_attr(c, 'audioChannels')
                audio_codec = helpers.get_xml_attr(c, 'audioCodec')
                bitrate = helpers.get_xml_attr(c, 'bitrate')
                container = helpers.get_xml_attr(c, 'container')
                height = helpers.get_xml_attr(c, 'height')
                video_codec = helpers.get_xml_attr(c, 'videoCodec')
                video_framerate = helpers.get_xml_attr(c, 'videoFrameRate')
                video_resolution = helpers.get_xml_attr(c, 'videoResolution')
                width = helpers.get_xml_attr(c, 'width')

        machine_id = ''
        platform = ''
        player = ''

        if a.getElementsByTagName('Player'):
            player_elem = a.getElementsByTagName('Player')
            for d in player_elem:
                machine_id = helpers.get_xml_attr(d, 'machineIdentifier')
                platform = helpers.get_xml_attr(d, 'platform')
                player = helpers.get_xml_attr(d, 'title')

        transcode_audio_channels = None
        transcode_audio_codec = ''
        audio_decision = 'direct play'
        transcode_container = ''
        transcode_height = None
        transcode_protocol = ''
        transcode_video_codec = ''
        video_decision = 'direct play'
        transcode_width = None

        if a.getElementsByTagName('TranscodeSession'):
            transcode_elem = a.getElementsByTagName('TranscodeSession')
            for e in transcode_elem:
                transcode_audio_channels = helpers.get_xml_attr(e, 'audioChannels')
                transcode_audio_codec = helpers.get_xml_attr(e, 'audioCodec')
                audio_decision = helpers.get_xml_attr(e, 'audioDecision')
                transcode_container = helpers.get_xml_attr(e, 'container')
                transcode_height = helpers.get_xml_attr(e, 'height')
                transcode_protocol = helpers.get_xml_attr(e, 'protocol')
                transcode_video_codec = helpers.get_xml_attr(e, 'videoCodec')
                video_decision = helpers.get_xml_attr(e, 'videoDecision')
                transcode_width = helpers.get_xml_attr(e, 'width')

        user_id = None

        if a.getElementsByTagName('User'):
            user_elem = a.getElementsByTagName('User')
            for f in user_elem:
                user_id = helpers.get_xml_attr(f, 'id')

        writers = []
        if a.getElementsByTagName('Writer'):
            writer_elem = a.getElementsByTagName('Writer')
            for g in writer_elem:
                writers.append(helpers.get_xml_attr(g, 'tag'))

        actors = []
        if a.getElementsByTagName('Role'):
            actor_elem = a.getElementsByTagName('Role')
            for h in actor_elem:
                actors.append(helpers.get_xml_attr(h, 'tag'))

        genres = []
        if a.getElementsByTagName('Genre'):
            genre_elem = a.getElementsByTagName('Genre')
            for i in genre_elem:
                genres.append(helpers.get_xml_attr(i, 'tag'))

        output = {'added_at': added_at,
                  'art': art,
                  'duration': duration,
                  'grandparent_thumb': grandparent_thumb,
                  'grandparent_title': grandparent_title,
                  'parent_title': parent_title,
                  'title': title,
                  'guid': guid,
                  'media_index': media_index,
                  'originally_available_at': originally_available_at,
                  'last_viewed_at': last_viewed_at,
                  'parent_media_index': parent_media_index,
                  'parent_thumb': parent_thumb,
                  'rating': rating,
                  'thumb': thumb,
                  'media_type': media_type,
                  'updated_at': updated_at,
                  'view_offset': view_offset,
                  'year': year,
                  'directors': directors,
                  'aspect_ratio': aspect_ratio,
                  'audio_channels': audio_channels,
                  'audio_codec': audio_codec,
                  'bitrate': bitrate,
                  'container': container,
                  'height': height,
                  'video_codec': video_codec,
                  'video_framerate': video_framerate,
                  'video_resolution': video_resolution,
                  'width': width,
                  'machine_id': machine_id,
                  'platform': platform,
                  'player': player,
                  'transcode_audio_channels': transcode_audio_channels,
                  'transcode_audio_codec': transcode_audio_codec,
                  'audio_decision': audio_decision,
                  'transcode_container': transcode_container,
                  'transcode_height': transcode_height,
                  'transcode_protocol': transcode_protocol,
                  'transcode_video_codec': transcode_video_codec,
                  'video_decision': video_decision,
                  'transcode_width': transcode_width,
                  'user_id': user_id,
                  'writers': writers,
                  'actors': actors,
                  'genres': genres,
                  'studio': studio
                  }

    return output

def validate_database(database=None, table_name=None):
    try:
        connection = sqlite3.connect(database, timeout=20)
    except sqlite3.OperationalError:
        logger.error('PlexPy Importer :: Invalid database specified.')
        return 'Invalid database specified.'
    except ValueError:
        logger.error('PlexPy Importer :: Invalid database specified.')
        return 'Invalid database specified.'

    try:
        connection.execute('SELECT ratingKey from %s' % table_name)
        connection.close()
    except sqlite3.OperationalError:
        logger.error('PlexPy Importer :: Invalid database specified.')
        return 'Invalid database specified.'

    return 'success'

def import_from_plexwatch(database=None, table_name=None, import_ignore_interval=0):

    try:
        connection = sqlite3.connect(database, timeout=20)
    except sqlite3.OperationalError:
        logger.error('PlexPy Importer :: Invalid filename.')
        return None
    except ValueError:
        logger.error('PlexPy Importer :: Invalid filename.')
        return None

    try:
        connection.execute('SELECT ratingKey from %s' % table_name)
    except sqlite3.OperationalError:
        logger.error('PlexPy Importer :: Database specified does not contain the required fields.')
        return None

    logger.debug(u"PlexPy Importer :: PlexWatch data import in progress...")

    logger.debug(u"PlexPy Importer :: Disabling monitoring while import in progress.")
    plexpy.schedule_job(monitor.check_active_sessions, 'Check for active sessions', hours=0, minutes=0, seconds=0)

    monitor_processing = monitor.MonitorProcessing()
    data_factory = datafactory.DataFactory()

    # Get the latest friends list so we can pull user id's
    try:
        plextv.refresh_users()
    except:
        logger.debug(u"PlexPy Importer :: Unable to refresh the users list. Aborting import.")
        return None

    query = 'SELECT time AS started, ' \
            'stopped, ' \
            'ratingKey AS rating_key, ' \
            'null AS user_id, ' \
            'user, ' \
            'ip_address, ' \
            'paused_counter, ' \
            'platform AS player, ' \
            'null AS platform, ' \
            'null as machine_id, ' \
            'parentRatingKey as parent_rating_key, ' \
            'grandparentRatingKey as grandparent_rating_key, ' \
            'null AS media_type, ' \
            'null AS view_offset, ' \
            'xml, ' \
            'rating as content_rating,' \
            'summary,' \
            'title AS full_title,' \
            'orig_title AS title, ' \
            'orig_title_ep AS grandparent_title ' \
            'FROM ' + table_name + ' ORDER BY id'

    result = connection.execute(query)

    for row in result:
        # Extract the xml from the Plexwatch db xml field.
        extracted_xml = extract_plexwatch_xml(row[14])

        # If the user_id no longer exists in the friends list, pull it from the xml.
        if data_factory.get_user_id(user=row[4]):
            user_id = data_factory.get_user_id(user=row[4])
        else:
            user_id = extracted_xml['user_id']

        session_history = {'started': row[0],
                           'stopped': row[1],
                           'rating_key': row[2],
                           'title': extracted_xml['title'],
                           'parent_title': extracted_xml['parent_title'],
                           'grandparent_title': extracted_xml['grandparent_title'],
                           'user_id': user_id,
                           'user': row[4],
                           'ip_address': row[5],
                           'paused_counter': row[6],
                           'player': row[7],
                           'platform': extracted_xml['platform'],
                           'machine_id': extracted_xml['machine_id'],
                           'parent_rating_key': row[10],
                           'grandparent_rating_key': row[11],
                           'media_type': extracted_xml['media_type'],
                           'view_offset': extracted_xml['view_offset'],
                           'video_decision': extracted_xml['video_decision'],
                           'audio_decision': extracted_xml['audio_decision'],
                           'duration': extracted_xml['duration'],
                           'width': extracted_xml['width'],
                           'height': extracted_xml['height'],
                           'container': extracted_xml['container'],
                           'video_codec': extracted_xml['video_codec'],
                           'audio_codec': extracted_xml['audio_codec'],
                           'bitrate': extracted_xml['bitrate'],
                           'video_resolution': extracted_xml['video_resolution'],
                           'video_framerate': extracted_xml['video_framerate'],
                           'aspect_ratio': extracted_xml['aspect_ratio'],
                           'audio_channels': extracted_xml['audio_channels'],
                           'transcode_protocol': extracted_xml['transcode_protocol'],
                           'transcode_container': extracted_xml['transcode_container'],
                           'transcode_video_codec': extracted_xml['transcode_video_codec'],
                           'transcode_audio_codec': extracted_xml['transcode_audio_codec'],
                           'transcode_audio_channels': extracted_xml['transcode_audio_channels'],
                           'transcode_width': extracted_xml['transcode_width'],
                           'transcode_height': extracted_xml['transcode_height']
                           }

        session_history_metadata = {'rating_key': row[2],
                                    'parent_rating_key': row[10],
                                    'grandparent_rating_key': row[11],
                                    'title': extracted_xml['title'],
                                    'parent_title': extracted_xml['parent_title'],
                                    'grandparent_title': extracted_xml['grandparent_title'],
                                    'index': extracted_xml['media_index'],
                                    'parent_index': extracted_xml['parent_media_index'],
                                    'thumb': extracted_xml['thumb'],
                                    'parent_thumb': extracted_xml['parent_thumb'],
                                    'grandparent_thumb': extracted_xml['grandparent_thumb'],
                                    'art': extracted_xml['art'],
                                    'media_type': extracted_xml['media_type'],
                                    'year': extracted_xml['year'],
                                    'originally_available_at': extracted_xml['originally_available_at'],
                                    'added_at': extracted_xml['added_at'],
                                    'updated_at': extracted_xml['updated_at'],
                                    'last_viewed_at': extracted_xml['last_viewed_at'],
                                    'content_rating': row[15],
                                    'summary': row[16],
                                    'rating': extracted_xml['rating'],
                                    'duration': extracted_xml['duration'],
                                    'guid': extracted_xml['guid'],
                                    'directors': extracted_xml['directors'],
                                    'writers': extracted_xml['writers'],
                                    'actors': extracted_xml['actors'],
                                    'genres': extracted_xml['genres'],
                                    'studio': extracted_xml['studio'],
                                    'full_title': row[17]
                                    }

        # On older versions of PMS, "clip" items were still classified as "movie" and had bad ratingKey values
        # Just make sure that the ratingKey is indeed an integer
        if str(row[2]).isdigit():
            monitor_processing.write_session_history(session=session_history,
                                                     import_metadata=session_history_metadata,
                                                     is_import=True,
                                                     import_ignore_interval=import_ignore_interval)
        else:
            logger.debug(u"PlexPy Importer :: Item has bad rating_key: %s" % str(row[2]))

    logger.debug(u"PlexPy Importer :: PlexWatch data import complete.")

    logger.debug(u"PlexPy Importer :: Re-enabling monitoring.")
    plexpy.initialize_scheduler()
