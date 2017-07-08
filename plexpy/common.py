#  This file is part of PlexPy.
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

'''
Created on Aug 1, 2011

@author: Michael
'''
import platform

import version

# Identify Our Application
USER_AGENT = 'PlexPy/-' + version.PLEXPY_BRANCH + ' v' + version.PLEXPY_RELEASE_VERSION + ' (' + platform.system() + \
             ' ' + platform.release() + ')'

PLATFORM = platform.system()
PLATFORM_VERSION = platform.release()
BRANCH = version.PLEXPY_BRANCH
VERSION_NUMBER = version.PLEXPY_RELEASE_VERSION

DEFAULT_USER_THUMB = "interfaces/default/images/gravatar-default-80x80.png"
DEFAULT_POSTER_THUMB = "interfaces/default/images/poster.png"
DEFAULT_COVER_THUMB = "interfaces/default/images/cover.png"
DEFAULT_ART = "interfaces/default/images/art.png"

PLATFORM_NAME_OVERRIDES = {'Konvergo': 'Plex Media Player',
                           'Mystery 3': 'Playstation 3',
                           'Mystery 4': 'Playstation 4',
                           'Mystery 5': 'Xbox 360'
                           }

PMS_PLATFORM_NAME_OVERRIDES = {'MacOSX': 'Mac'
                               }

MEDIA_FLAGS_AUDIO = {'ac.?3': 'dolby_digital',
                     'truehd': 'dolby_truehd',
                     '(dca|dta)': 'dts',
                     'dts(hd_|-hd|-)?ma': 'dca-ma',
                     'vorbis': 'ogg'
                     }
MEDIA_FLAGS_VIDEO = {'avc1': 'h264',
                     'wmv(1|2)': 'wmv',
                     'wmv3': 'wmvhd'
                     }

AUDIO_CODEC_OVERRIDES = {'truehd': 'TrueHD'}

VIDEO_RESOLUTION_OVERRIDES = {'sd': 'SD',
                              '480': '480p',
                              '576': '576p',
                              '720': '720p',
                              '1080': '1080p',
                              '4k': '4k'
                              }

AUDIO_CHANNELS = {'1': 'Mono',
                  '2': 'Stereo',
                  '3': '2.1',
                  '4': '3.1',
                  '6': '5.1',
                  '7': '6.1',
                  '8': '7.1'
                  }

QUALITY_PROFILES = {20000: '20 Mbps 1080p',
                    12000: '12 Mbps 1080p',
                    10000: '10 Mbps 1080p',
                    8000: '8 Mbps 1080p',
                    4000: '4 Mbps 720p',
                    3000: '3 Mbps 720p',
                    2000: '2 Mbps 720p',
                    1500: '1.5 Mbps 480p',
                    720: '720 kbps',
                    320: '320 kbps',
                    208: '208 kbps',
                    96: '96 kbps',
                    64: '64 kbps'
                    }

SCHEDULER_LIST = ['Check GitHub for updates',
                  'Check for active sessions',
                  'Check for recently added items',
                  'Check for Plex updates',
                  'Check for Plex remote access',
                  'Refresh users list',
                  'Refresh libraries list',
                  'Refresh Plex server URLs',
                  'Refresh Plex server name',
                  'Backup PlexPy database',
                  'Backup PlexPy config'
                  ]

DATE_TIME_FORMATS = [
    {
        'category': 'Year',
        'parameters': [
            {'value': 'MMMM', 'description': 'Textual, full', 'example': 'January-December'},
            {'value': 'MMM', 'description': 'Textual, three letters', 'example': 'Jan-Dec'},
            {'value': 'MM', 'description': 'Numeric, with leading zeros', 'example': '42747'},
            {'value': 'M', 'description': 'Numeric, without leading zeros', 'example': '42747'},
        ]
     },
    {
        'category': 'Day of the Year',
        'parameters': [
            {'value': 'DDDD', 'description': 'Numeric, with leading zeros', 'example': '001-365'},
            {'value': 'DDD', 'description': 'Numeric, without leading zeros', 'example': '1-365'},
        ]
     },
    {
        'category': 'Day of the Month',
        'parameters': [
            {'value': 'DD', 'description': 'Numeric, with leading zeros', 'example': '42766'},
            {'value': 'D', 'description': 'Numeric, without leading zeros', 'example': '42766'},
            {'value': 'Do', 'description': 'Numeric, with suffix', 'example': 'E.g. 1st, 2nd ... 31st.'},
        ]
     },
    {
        'category': 'Day of the Week',
        'parameters': [
            {'value': 'dddd', 'description': 'Textual, full', 'example': 'Sunday-Saturday'},
            {'value': 'ddd', 'description': 'Textual, three letters', 'example': 'Sun-Sat'},
            {'value': 'd', 'description': 'Numeric', 'example': '0-6'},
        ]
     },
    {
        'category': 'Hour',
        'parameters': [
            {'value': 'HH', 'description': '24-hour, with leading zeros', 'example': '00-23'},
            {'value': 'H', 'description': '24-hour, without leading zeros', 'example': '0-23'},
            {'value': 'hh', 'description': '12-hour, with leading zeros', 'example': '42747'},
            {'value': 'h', 'description': '12-hour, without leading zeros', 'example': '42747'},
        ]
     },
    {
        'category': 'Minute',
        'parameters': [
            {'value': 'mm', 'description': 'Numeric, with leading zeros', 'example': '00-59'},
            {'value': 'm', 'description': 'Numeric, without leading zeros', 'example': '0-59'},
        ]
     },
    {
        'category': 'Second',
        'parameters': [
            {'value': 'ss', 'description': 'Numeric, with leading zeros', 'example': '00-59'},
            {'value': 's', 'description': 'Numeric, without leading zeros', 'example': '0-59'},
        ]
     },
    {
        'category': 'AM / PM',
        'parameters': [
            {'value': 'A', 'description': 'AM/PM uppercase', 'example': 'AM, PM'},
            {'value': 'a', 'description': 'am/pm lowercase', 'example': 'am, pm'},
        ]
     },
    {
        'category': 'Timezone',
        'parameters': [
            {'value': 'ZZ', 'description': 'UTC offset', 'example': 'E.g. +0100, -0700'},
            {'value': 'Z', 'description': 'UTC offset', 'example': 'E.g. +01:00, -07:00'},
        ]
     },
    {
        'category': 'Timestamp',
        'parameters': [
            {'value': 'X', 'description': 'Unix timestamp', 'example': 'E.g. 1456887825'},
        ]
     },
    ]

NOTIFICATION_PARAMETERS = [
    {
        'category': 'Global',
        'parameters': [
             {'name': 'PlexPy Version', 'type': 'str', 'value': 'plexpy_version', 'description': 'The current version of PlexPy.', 'example': '', 'help_text': ''},
             {'name': 'PlexPy Branch', 'type': 'str', 'value': 'plexpy_branch', 'description': 'The current git branch of PlexPy.', 'example': '', 'help_text': ''},
             {'name': 'PlexPy Commit', 'type': 'str', 'value': 'plexpy_commit', 'description': 'The current git commit hash of PlexPy.', 'example': '', 'help_text': ''},
             {'name': 'Server Name', 'type': 'str', 'value': 'server_name', 'description': 'The name of your Plex Server.', 'example': '', 'help_text': ''},
             {'name': 'Server Uptime', 'type': 'str', 'value': 'server_uptime', 'description': 'The uptime (in days, hours, mins, secs) of your Plex Server.', 'example': '', 'help_text': ''},
             {'name': 'Server Version', 'type': 'str', 'value': 'server_version', 'description': 'The current version of your Plex Server.', 'example': '', 'help_text': ''},
             {'name': 'Action', 'type': 'str', 'value': 'action', 'description': 'The action that triggered the notification.', 'example': '', 'help_text': ''},
             {'name': 'Datestamp', 'type': 'int', 'value': 'datestamp', 'description': 'The date (in date format) the notification was triggered.', 'example': '', 'help_text': ''},
             {'name': 'Timestamp', 'type': 'int', 'value': 'timestamp', 'description': 'The time (in time format) the notification was triggered.', 'example': '', 'help_text': ''},
         ]
     },
    {
        'category': 'Stream Details',
        'parameters': [
             {'name': 'Streams', 'type': 'int', 'value': 'streams', 'description': 'The number of concurrent streams.', 'example': '', 'help_text': ''},
             {'name': 'User Streams', 'type': 'int', 'value': 'user_streams', 'description': 'The number of concurrent streams by the person streaming.', 'example': '', 'help_text': ''},
             {'name': 'User', 'type': 'str', 'value': 'user', 'description': 'The friendly name of the person streaming.', 'example': '', 'help_text': ''},
             {'name': 'Username', 'type': 'str', 'value': 'username', 'description': 'The username of the person streaming.', 'example': '', 'help_text': ''},
             {'name': 'Device', 'type': 'str', 'value': 'device', 'description': 'The type of client device being used for playback.', 'example': '', 'help_text': ''},
             {'name': 'Platform', 'type': 'str', 'value': 'platform', 'description': 'The type of client platform being used for playback.', 'example': '', 'help_text': ''},
             {'name': 'Product', 'type': 'str', 'value': 'product', 'description': 'The type of client product being used for playback.', 'example': '', 'help_text': ''},
             {'name': 'Player', 'type': 'str', 'value': 'player', 'description': 'The name of the player being used for playback.', 'example': '', 'help_text': ''},
             {'name': 'IP Address', 'type': 'str', 'value': 'ip_address', 'description': 'The IP address of the device being used for playback.', 'example': '', 'help_text': ''},
             {'name': 'Stream Duration', 'type': 'int', 'value': 'stream_duration', 'description': 'The duration (in minutes) for the stream.', 'example': '', 'help_text': ''},
             {'name': 'Stream Time', 'type': 'str', 'value': 'stream_time', 'description': 'The duration (in time format) of the stream.', 'example': '', 'help_text': ''},
             {'name': 'Remaining Duration', 'type': 'int', 'value': 'remaining_duration', 'description': 'The remaining duration (in minutes) of the stream.', 'example': '', 'help_text': ''},
             {'name': 'Remaining Time', 'type': 'str', 'value': 'remaining_time', 'description': 'The remaining duration (in time format) of the stream.', 'example': '', 'help_text': ''},
             {'name': 'Progress Duration', 'type': 'int', 'value': 'progress_duration', 'description': 'The last reported offset (in minutes) of the stream.', 'example': '', 'help_text': ''},
             {'name': 'Progress Time', 'type': 'str', 'value': 'progress_time', 'description': 'The last reported offset (in time format) of the stream.', 'example': '', 'help_text': ''},
             {'name': 'Progress Percent', 'type': 'int', 'value': 'progress_percent', 'description': 'The last reported progress percent of the stream.', 'example': '', 'help_text': ''},
             {'name': 'Transcode Decision', 'type': 'str', 'value': 'transcode_decision', 'description': 'The transcode decisions of the stream.', 'example': '', 'help_text': ''},
             {'name': 'Video Decision', 'type': 'str', 'value': 'video_decision', 'description': 'The video transcode decisions of the stream.', 'example': '', 'help_text': ''},
             {'name': 'Audio Decision', 'type': 'str', 'value': 'audio_decision', 'description': 'The audio transcode decisions of the stream.', 'example': '', 'help_text': ''},
             {'name': 'Subtitle Decision', 'type': 'str', 'value': 'subtitle_decision', 'description': 'The subtitle transcode decisions of the stream.', 'example': '', 'help_text': ''},
             {'name': 'Quality Profile', 'type': 'str', 'value': 'quality_profile', 'description': 'The Plex quality profile of the stream.', 'example': 'e.g. Original, 4 Mbps 720p, etc.', 'help_text': ''},
             {'name': 'Optimized Version', 'type': 'int', 'value': 'optimized_version', 'description': 'If the stream is an optimized version.', 'example': '0 or 1', 'help_text': ''},
             {'name': 'Optimized Version Profile', 'type': 'str', 'value': 'optimized_version_profile', 'description': 'The optimized version profile of the stream.', 'example': '', 'help_text': ''},
             {'name': 'Stream Local', 'type': 'int', 'value': 'stream_local', 'description': 'If the stream is local.', 'example': '0 or 1', 'help_text': ''},
             {'name': 'Stream Location', 'type': 'str', 'value': 'stream_location', 'description': 'The network location of the stream.', 'example': 'lan or wan', 'help_text': ''},
             {'name': 'Stream Bandwidth', 'type': 'int', 'value': 'stream_bandwidth', 'description': 'The required bandwidth (in kbps) of the stream.', 'example': '', 'help_text': 'not the used bandwidth'},
             {'name': 'Stream Container', 'type': 'str', 'value': 'stream_container', 'description': 'The media container of the stream.', 'example': '', 'help_text': ''},
             {'name': 'Stream Bitrate', 'type': 'int', 'value': 'stream_bitrate', 'description': 'The bitrate (in kbps) of the stream.', 'example': '', 'help_text': ''},
             {'name': 'Stream Aspect Ratio', 'type': 'float', 'value': 'stream_aspect_ratio', 'description': 'The aspect ratio of the stream.', 'example': '', 'help_text': ''},
             {'name': 'Stream Video Codec', 'type': 'str', 'value': 'stream_video_codec', 'description': 'The video codec of the stream.', 'example': '', 'help_text': ''},
             {'name': 'Stream Video Codec Level', 'type': 'int', 'value': 'stream_video_codec_level', 'description': 'The video codec level of the stream.', 'example': '', 'help_text': ''},
             {'name': 'Stream Video Bitrate', 'type': 'int', 'value': 'stream_video_bitrate', 'description': 'The video bitrate (in kbps) of the stream.', 'example': '', 'help_text': ''},
             {'name': 'Stream Video Bit Depth', 'type': 'int', 'value': 'stream_video_bit_depth', 'description': 'The video bit depth of the stream.', 'example': '', 'help_text': ''},
             {'name': 'Stream Video Framerate', 'type': 'str', 'value': 'stream_video_framerate', 'description': 'The video framerate of the stream.', 'example': '', 'help_text': ''},
             {'name': 'Stream Video Ref Frames', 'type': 'int', 'value': 'stream_video_ref_frames', 'description': 'The video reference frames of the stream.', 'example': '', 'help_text': ''},
             {'name': 'Stream Video Resolution', 'type': 'str', 'value': 'stream_video_resolution', 'description': 'The video resolution of the stream.', 'example': '', 'help_text': ''},
             {'name': 'Stream Video Height', 'type': 'int', 'value': 'stream_video_height', 'description': 'The video height of the stream.', 'example': '', 'help_text': ''},
             {'name': 'Stream Video Width', 'type': 'int', 'value': 'stream_video_width', 'description': 'The video width of the stream.', 'example': '', 'help_text': ''},
             {'name': 'Stream Video Language', 'type': 'str', 'value': 'stream_video_language', 'description': 'The video language of the stream.', 'example': '', 'help_text': ''},
             {'name': 'Stream Video Language Code', 'type': 'str', 'value': 'stream_video_language_code', 'description': 'The video language code of the stream.', 'example': '', 'help_text': ''},
             {'name': 'Stream Audio Bitrate', 'type': 'int', 'value': 'stream_audio_bitrate', 'description': 'The audio bitrate of the stream.', 'example': '', 'help_text': ''},
             {'name': 'Stream Audio Bitrate Mode', 'type': 'str', 'value': 'stream_audio_bitrate_mode', 'description': 'The audio bitrate mode of the stream.', 'example': 'cbr or vbr', 'help_text': ''},
             {'name': 'Stream Audio Codec', 'type': 'str', 'value': 'stream_audio_codec', 'description': 'The audio codec of the stream.', 'example': '', 'help_text': ''},
             {'name': 'Stream Audio Channels', 'type': 'float', 'value': 'stream_audio_channels', 'description': 'The audio channels of the stream.', 'example': '', 'help_text': ''},
             {'name': 'Stream Audio Channel Layout', 'type': 'str', 'value': 'stream_audio_channel_layout', 'description': 'The audio channel layout of the stream.', 'example': '', 'help_text': ''},
             {'name': 'Stream Audio Sample Rate', 'type': 'int', 'value': 'stream_audio_sample_rate', 'description': 'The audio sample rate (in Hz) of the stream.', 'example': '', 'help_text': ''},
             {'name': 'Stream Audio Language', 'type': 'str', 'value': 'stream_audio_language', 'description': 'The audio language of the stream.', 'example': '', 'help_text': ''},
             {'name': 'Stream Audio Language Code', 'type': 'str', 'value': 'stream_audio_language_code', 'description': 'The audio language code of the stream.', 'example': '', 'help_text': ''},
             {'name': 'Stream Subtitle Codec', 'type': 'str', 'value': 'stream_subtitle_codec', 'description': 'The subtitle codec of the stream.', 'example': '', 'help_text': ''},
             {'name': 'Stream Subtitle Container', 'type': 'str', 'value': 'stream_subtitle_container', 'description': 'The subtitle container of the stream.', 'example': '', 'help_text': ''},
             {'name': 'Stream Subtitle Format', 'type': 'str', 'value': 'stream_subtitle_format', 'description': 'The subtitle format of the stream.', 'example': '', 'help_text': ''},
             {'name': 'Stream Subtitle Forced', 'type': 'int', 'value': 'stream_subtitle_forced', 'description': 'If the subtitles are forced.', 'example': '0 or 1', 'help_text': ''},
             {'name': 'Stream Subtitle Language', 'type': 'str', 'value': 'stream_subtitle_language', 'description': 'The subtitle language of the stream.', 'example': '', 'help_text': ''},
             {'name': 'Stream Subtitle Language Code', 'type': 'str', 'value': 'stream_subtitle_language_code', 'description': 'The subtitle language code of the stream.', 'example': '', 'help_text': ''},
             {'name': 'Stream Subtitle Location', 'type': 'str', 'value': 'stream_subtitle_location', 'description': 'The subtitle location of the stream.', 'example': '', 'help_text': ''},
             {'name': 'Transcode Container', 'type': 'str', 'value': 'transcode_container', 'description': 'The media container of the transcoded stream.', 'example': '', 'help_text': ''},
             {'name': 'Transcode Video Codec', 'type': 'str', 'value': 'transcode_video_codec', 'description': 'The video codec of the transcoded stream.', 'example': '', 'help_text': ''},
             {'name': 'Transcode Video Width', 'type': 'int', 'value': 'transcode_video_width', 'description': 'The video width of the transcoded stream.', 'example': '', 'help_text': ''},
             {'name': 'Transcode Video Height', 'type': 'int', 'value': 'transcode_video_height', 'description': 'The video height of the transcoded stream.', 'example': '', 'help_text': ''},
             {'name': 'Transcode Audio Codec', 'type': 'str', 'value': 'transcode_audio_codec', 'description': 'The audio codec of the transcoded stream.', 'example': '', 'help_text': ''},
             {'name': 'Transcode Audio Channels', 'type': 'float', 'value': 'transcode_audio_channels', 'description': 'The audio channels of the transcoded stream.', 'example': '', 'help_text': ''},
             {'name': 'Transcode Hardware', 'type': 'int', 'value': 'transcode_hardware', 'description': 'If hardware transcoding is used.', 'example': '0 or 1', 'help_text': ''},
             {'name': 'Session Key', 'type': 'str', 'value': 'session_key', 'description': 'The unique identifier for the session.', 'example': '', 'help_text': ''},
             {'name': 'Transcode Key', 'type': 'str', 'value': 'transcode_key', 'description': 'The unique identifier for the transcode session.', 'example': '', 'help_text': ''},
             {'name': 'Session ID', 'type': 'str', 'value': 'session_id', 'description': 'The unique identifier for the stream.', 'example': '', 'help_text': ''},
             {'name': 'User ID', 'type': 'int', 'value': 'user_id', 'description': 'The unique identifier for the user.', 'example': '', 'help_text': ''},
             {'name': 'Machine ID', 'type': 'str', 'value': 'machine_id', 'description': 'The unique identifier for the player.', 'example': '', 'help_text': ''},
         ]
     },
    {
        'category': 'Source Metadata Details',
        'parameters': [
             {'name': 'Media Type', 'type': 'str', 'value': 'media_type', 'description': 'The type of media.', 'example': 'movie, show, season, episode, artist, album, track', 'help_text': ''},
             {'name': 'Title', 'type': 'str', 'value': 'title', 'description': 'The full title of the item.', 'example': '', 'help_text': ''},
             {'name': 'Library Name', 'type': 'str', 'value': 'library_name', 'description': 'The library name of the item.', 'example': '', 'help_text': ''},
             {'name': 'Show Name', 'type': 'str', 'value': 'show_name', 'description': 'The title of the TV series.', 'example': '', 'help_text': ''},
             {'name': 'Episode Name', 'type': 'str', 'value': 'episode_name', 'description': 'The title of the episode.', 'example': '', 'help_text': ''},
             {'name': 'Artist Name', 'type': 'str', 'value': 'artist_name', 'description': 'The name of the artist.', 'example': '', 'help_text': ''},
             {'name': 'Album Name', 'type': 'str', 'value': 'album_name', 'description': 'The title of the album.', 'example': '', 'help_text': ''},
             {'name': 'Track Name', 'type': 'str', 'value': 'track_name', 'description': 'The title of the track.', 'example': '', 'help_text': ''},
             {'name': 'Season Number', 'type': 'int', 'value': 'season_num', 'description': 'The season number.', 'example': 'e.g. 1, or 1-3', 'help_text': ''},
             {'name': 'Season Number 00', 'type': 'int', 'value': 'season_num00', 'description': 'The two digit season number.', 'example': 'e.g. 01, or 01-03', 'help_text': ''},
             {'name': 'Episode Number', 'type': 'int', 'value': 'episode_num', 'description': 'The episode number.', 'example': 'e.g. 6, or 6-10', 'help_text': ''},
             {'name': 'Episode Number 00', 'type': 'int', 'value': 'episode_num00', 'description': 'The two digit episode number.', 'example': 'e.g. 06, or 06-10', 'help_text': ''},
             {'name': 'Track Number', 'type': 'int', 'value': 'track_num', 'description': 'The track number.', 'example': 'e.g. 4, or 4-10', 'help_text': ''},
             {'name': 'Track Number 00', 'type': 'int', 'value': 'track_num00', 'description': 'The two digit track number.', 'example': 'e.g. 04, or 04-10', 'help_text': ''},
             {'name': 'Year', 'type': 'int', 'value': 'year', 'description': 'The release year for the item.', 'example': '', 'help_text': ''},
             {'name': 'Release Date', 'type': 'int', 'value': 'release_date', 'description': 'The release date (in date format) for the item.', 'example': '', 'help_text': ''},
             {'name': 'Air Date', 'type': 'int', 'value': 'air_date', 'description': 'The air date (in date format) for the item.', 'example': '', 'help_text': ''},
             {'name': 'Added Date', 'type': 'int', 'value': 'added_date', 'description': 'The date (in date format) the item was added to Plex.', 'example': '', 'help_text': ''},
             {'name': 'Updated Date', 'type': 'int', 'value': 'updated_date', 'description': 'The date (in date format) the item was updated on Plex.', 'example': '', 'help_text': ''},
             {'name': 'Last Viewed Date', 'type': 'int', 'value': 'last_viewed_date', 'description': 'The date (in date format) the item was last viewed on Plex.', 'example': '', 'help_text': ''},
             {'name': 'Studio', 'type': 'str', 'value': 'studio', 'description': 'The studio for the item.', 'example': '', 'help_text': ''},
             {'name': 'Content Rating', 'type': 'int', 'value': 'content_rating', 'description': 'The content rating for the item.', 'example': 'e.g. TV-MA, TV-PG, etc.', 'help_text': ''},
             {'name': 'Director', 'type': 'str', 'value': 'directors', 'description': 'A list of directors for the item.', 'example': '', 'help_text': ''},
             {'name': 'Writer', 'type': 'str', 'value': 'writers', 'description': 'A list of writers for the item.', 'example': '', 'help_text': ''},
             {'name': 'Actor', 'type': 'str', 'value': 'actors', 'description': 'A list of actors for the item.', 'example': '', 'help_text': ''},
             {'name': 'Genre', 'type': 'str', 'value': 'genres', 'description': 'A list of genres for the item.', 'example': '', 'help_text': ''},
             {'name': 'Summary', 'type': 'str', 'value': 'summary', 'description': 'A short plot summary for the item.', 'example': '', 'help_text': ''},
             {'name': 'Tagline', 'type': 'str', 'value': 'tagline', 'description': 'A tagline for the media item.', 'example': '', 'help_text': ''},
             {'name': 'Rating', 'type': 'int', 'value': 'rating', 'description': 'The rating (out of 10) for the item.', 'example': '', 'help_text': ''},
             {'name': 'Audience Rating', 'type': 'int', 'value': 'audience_rating', 'description': 'The audience rating (%) for the item.', 'example': '', 'help_text': 'Ratings source must be Rotten Tomatoes for the Plex Movie agent'},
             {'name': 'Duration', 'type': 'int', 'value': 'duration', 'description': 'The duration (in minutes) for the item.', 'example': '', 'help_text': ''},
             {'name': 'Poster URL', 'type': 'str', 'value': 'poster_url', 'description': 'A URL for the movie, TV show, or album poster.', 'example': '', 'help_text': ''},
             {'name': 'Plex URL', 'type': 'str', 'value': 'plex_url', 'description': 'The Plex URL to your server for the item.', 'example': '', 'help_text': ''},
             {'name': 'IMDB ID', 'type': 'str', 'value': 'imdb_id', 'description': 'The IMDB ID for the movie.', 'example': 'e.g. tt2488496', 'help_text': 'PMS agent must be Plex Movie'},
             {'name': 'IMDB URL', 'type': 'str', 'value': 'imdb_url', 'description': 'The IMDB URL for the movie.', 'example': '', 'help_text': 'PMS agent must be Plex Movie'},
             {'name': 'TVDB ID', 'type': 'int', 'value': 'thetvdb_id', 'description': 'The TVDB ID for the TV show.', 'example': 'e.g. 121361', 'help_text': 'PMS agent must be TheTVDB'},
             {'name': 'TVDB URL', 'type': 'str', 'value': 'thetvdb_url', 'description': 'The TVDB URL for the TV show.', 'example': '', 'help_text': 'PMS agent must be TheTVDB'},
             {'name': 'TMDB ID', 'type': 'int', 'value': 'themoviedb_id', 'description': 'The TMDb ID for the movie or TV show.', 'example': 'e.g. 15260', 'help_text': 'PMS agent must be The Movie Database'},
             {'name': 'TMDB URL', 'type': 'str', 'value': 'themoviedb_url', 'description': 'The TMDb URL for the movie or TV show.', 'example': '', 'help_text': 'PMS agent must be The Movie Database'},
             {'name': 'Last.fm URL', 'type': 'str', 'value': 'lastfm_url', 'description': 'The Last.fm URL for the album.', 'example': '', 'help_text': 'PMS agent must be Last.fm'},
             {'name': 'Trakt.tv URL', 'type': 'str', 'value': 'trakt_url', 'description': 'The trakt.tv URL for the movie or TV show.', 'example': '', 'help_text': ''},
             {'name': 'Container', 'type': 'str', 'value': 'container', 'description': 'The media container of the original media.', 'example': '', 'help_text': ''},
             {'name': 'Bitrate', 'type': 'int', 'value': 'bitrate', 'description': 'The bitrate of the original media.', 'example': '', 'help_text': ''},
             {'name': 'Aspect Ratio', 'type': 'float', 'value': 'aspect_ratio', 'description': 'The aspect ratio of the original media.', 'example': '', 'help_text': ''},
             {'name': 'Video Codec', 'type': 'str', 'value': 'video_codec', 'description': 'The video codec of the original media.', 'example': '', 'help_text': ''},
             {'name': 'Video Codec Level', 'type': 'int', 'value': 'video_codec_level', 'description': 'The video codec level of the original media.', 'example': '', 'help_text': ''},
             {'name': 'Video Bitrate', 'type': 'int', 'value': 'video_bitrate', 'description': 'The video bitrate of the original media.', 'example': '', 'help_text': ''},
             {'name': 'Video Bit Depth', 'type': 'int', 'value': 'video_bit_depth', 'description': 'The video bit depth of the original media.', 'example': '', 'help_text': ''},
             {'name': 'Video Framerate', 'type': 'str', 'value': 'video_framerate', 'description': 'The video framerate of the original media.', 'example': '', 'help_text': ''},
             {'name': 'Video Ref Frames', 'type': 'int', 'value': 'video_ref_frames', 'description': 'The video reference frames of the original media.', 'example': '', 'help_text': ''},
             {'name': 'Video Resolution', 'type': 'str', 'value': 'video_resolution', 'description': 'The video resolution of the original media.', 'example': '', 'help_text': ''},
             {'name': 'Video Height', 'type': 'int', 'value': 'video_height', 'description': 'The video height of the original media.', 'example': '', 'help_text': ''},
             {'name': 'Video Width', 'type': 'int', 'value': 'video_width', 'description': 'The video width of the original media.', 'example': '', 'help_text': ''},
             {'name': 'Video Language', 'type': 'str', 'value': 'video_language', 'description': 'The video language of the original media.', 'example': '', 'help_text': ''},
             {'name': 'Video Language Code', 'type': 'str', 'value': 'video_language_code', 'description': 'The video language code of the original media.', 'example': '', 'help_text': ''},
             {'name': 'Audio Bitrate', 'type': 'int', 'value': 'audio_bitrate', 'description': 'The audio bitrate of the original media.', 'example': '', 'help_text': ''},
             {'name': 'Audio Bitrate Mode', 'type': 'str', 'value': 'audio_bitrate_mode', 'description': 'The audio bitrate mode of the original media.', 'example': 'cbr or vbr', 'help_text': ''},
             {'name': 'Audio Codec', 'type': 'str', 'value': 'audio_codec', 'description': 'The audio codec of the original media.', 'example': '', 'help_text': ''},
             {'name': 'Audio Channels', 'type': 'float', 'value': 'audio_channels', 'description': 'The audio channels of the original media.', 'example': '', 'help_text': ''},
             {'name': 'Audio Channel Layout', 'type': 'str', 'value': 'audio_channel_layout', 'description': 'The audio channel layout of the original media.', 'example': '', 'help_text': ''},
             {'name': 'Audio Sample Rate', 'type': 'int', 'value': 'audio_sample_rate', 'description': 'The audio sample rate (in Hz) of the original media.', 'example': '', 'help_text': ''},
             {'name': 'Audio Language', 'type': 'str', 'value': 'audio_language', 'description': 'The audio language of the original media.', 'example': '', 'help_text': ''},
             {'name': 'Audio Language Code', 'type': 'str', 'value': 'audio_language_code', 'description': 'The audio language code of the original media.', 'example': '', 'help_text': ''},
             {'name': 'Subtitle Codec', 'type': 'str', 'value': 'subtitle_codec', 'description': 'The subtitle codec of the original media.', 'example': '', 'help_text': ''},
             {'name': 'Subtitle Container', 'type': 'str', 'value': 'subtitle_container', 'description': 'The subtitle container of the original media.', 'example': '', 'help_text': ''},
             {'name': 'Subtitle Format', 'type': 'str', 'value': 'subtitle_format', 'description': 'The subtitle format of the original media.', 'example': '', 'help_text': ''},
             {'name': 'Subtitle Forced', 'type': 'int', 'value': 'subtitle_forced', 'description': 'If the subtitles are forced.', 'example': '0 or 1', 'help_text': ''},
             {'name': 'Subtitle Location', 'type': 'str', 'value': 'subtitle_location', 'description': 'The subtitle location of the original media.', 'example': '', 'help_text': ''},
             {'name': 'Subtitle Language', 'type': 'str', 'value': 'subtitle_language', 'description': 'The subtitle language of the original media.', 'example': '', 'help_text': ''},
             {'name': 'Subtitle Language Code', 'type': 'str', 'value': 'subtitle_language_code', 'description': 'The subtitle language code of the original media.', 'example': '', 'help_text': ''},
             {'name': 'File', 'type': 'str', 'value': 'file', 'description': 'The file path to the item.', 'example': '', 'help_text': ''},
             {'name': 'File Size', 'type': 'int', 'value': 'file_size', 'description': 'The file size of the item.', 'example': '', 'help_text': ''},
             {'name': 'Section ID', 'type': 'int', 'value': 'section_id', 'description': 'The unique identifier for the library.', 'example': '', 'help_text': ''},
             {'name': 'Rating Key', 'type': 'int', 'value': 'rating_key', 'description': 'The unique identifier for the movie, episode, or track.', 'example': '', 'help_text': ''},
             {'name': 'Parent Rating Key', 'type': 'int', 'value': 'parent_rating_key', 'description': 'The unique identifier for the season or album.', 'example': '', 'help_text': ''},
             {'name': 'Grandparent Rating Key', 'type': 'int', 'value': 'grandparent_rating_key', 'description': 'The unique identifier for the TV show or artist.', 'example': '', 'help_text': ''},
             {'name': 'Thumb', 'type': 'str', 'value': 'thumb', 'description': 'The Plex thumbnail for the movie or episode.', 'example': '', 'help_text': ''},
             {'name': 'Parent Thumb', 'type': 'str', 'value': 'parent_thumb', 'description': 'The Plex thumbnail for the season or album.', 'example': '', 'help_text': ''},
             {'name': 'Grandparent Thumb', 'type': 'str', 'value': 'grandparent_thumb', 'description': 'The Plex thumbnail for the TV show or artist.', 'example': '', 'help_text': ''},
             {'name': 'Poster Thumb', 'type': 'str', 'value': 'poster_thumb', 'description': 'The Plex thumbnail for the poster image.', 'example': '', 'help_text': ''},
             {'name': 'Poster Title', 'type': 'str', 'value': 'poster_title', 'description': 'The title for the poster image.', 'example': '', 'help_text': ''},
             {'name': 'Indexes', 'type': 'int', 'value': 'indexes', 'description': 'If the media has video preview thumbnails.', 'example': '0 or 1', 'help_text': ''},
         ]
     },
    {
        'category': 'Plex Update Available',
        'parameters': [
             {'name': 'Update Version', 'type': 'int', 'value': 'update_version', 'description': 'The available update version for your Plex Server.', 'example': '', 'help_text': ''},
             {'name': 'Update Url', 'type': 'int', 'value': 'update_url', 'description': 'The download URL for the available update.', 'example': '', 'help_text': ''},
             {'name': 'Update Release Date', 'type': 'int', 'value': 'update_release_date', 'description': 'The release date of the available update.', 'example': '', 'help_text': ''},
             {'name': 'Update Channel', 'type': 'int', 'value': 'update_channel', 'description': 'The update channel.', 'example': 'Public or Plex Pass', 'help_text': ''},
             {'name': 'Update Platform', 'type': 'int', 'value': 'update_platform', 'description': 'The platform of your Plex Server.', 'example': '', 'help_text': ''},
             {'name': 'Update Distro', 'type': 'int', 'value': 'update_distro', 'description': 'The distro of your Plex Server.', 'example': '', 'help_text': ''},
             {'name': 'Update Distro Build', 'type': 'int', 'value': 'update_distro_build', 'description': 'The distro build of your Plex Server.', 'example': '', 'help_text': ''},
             {'name': 'Update Requirements', 'type': 'int', 'value': 'update_requirements', 'description': 'The requirements for the available update.', 'example': '', 'help_text': ''},
             {'name': 'Update Extra Info', 'type': 'int', 'value': 'update_extra_info', 'description': 'Any extra info for the available update.', 'example': '', 'help_text': ''},
             {'name': 'Update Changelog Added', 'type': 'int', 'value': 'update_changelog_added', 'description': 'The added changelog for the available update.', 'example': '', 'help_text': ''},
             {'name': 'Update Changelog Fixed', 'type': 'int', 'value': 'update_changelog_fixed', 'description': 'The fixed changelog for the available update.', 'example': '', 'help_text': ''},
         ]
     },
    {
        'category': 'PlexPy Update Available',
        'parameters': [
             {'name': 'Plexpy Update Version', 'type': 'int', 'value': 'plexpy_update_version', 'description': 'The available update version for PlexPy.', 'example': '', 'help_text': ''},
             {'name': 'Plexpy Update Tar', 'type': 'int', 'value': 'plexpy_update_tar', 'description': 'The tar download URL for the available update.', 'example': '', 'help_text': ''},
             {'name': 'Plexpy Update Zip', 'type': 'int', 'value': 'plexpy_update_zip', 'description': 'The zip download URL for the available update.', 'example': '', 'help_text': ''},
             {'name': 'Plexpy Update Commit', 'type': 'int', 'value': 'plexpy_update_commit', 'description': 'The commit hash for the available update.', 'example': '', 'help_text': ''},
             {'name': 'Plexpy Update Behind', 'type': 'int', 'value': 'plexpy_update_behind', 'description': 'The number of commits behind for the available update.', 'example': '', 'help_text': ''},
             {'name': 'Plexpy Update Changelog', 'type': 'int', 'value': 'plexpy_update_changelog', 'description': 'The changelog for the available update.', 'example': '', 'help_text': ''},
        ]
     },
    ]
