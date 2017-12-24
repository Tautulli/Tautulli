#  This file is part of Tautulli.
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

import platform
from collections import OrderedDict

import version

# Identify Our Application
USER_AGENT = 'Tautulli/-' + version.PLEXPY_BRANCH + ' v' + version.PLEXPY_RELEASE_VERSION + ' (' + platform.system() + \
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
                           'Mystery 5': 'Xbox 360',
                           'WebMAF': 'Playstation 4'
                           }

PMS_PLATFORM_NAME_OVERRIDES = {'MacOSX': 'Mac'
                               }

PLATFORM_NAMES = {'android': 'android',
                  'apple tv': 'atv',
                  'chrome': 'chrome',
                  'chromecast': 'chromecast',
                  'dlna': 'dlna',
                  'firefox': 'firefox',
                  'internet explorer': 'ie',
                  'ios': 'ios',
                  'ipad': 'ios',
                  'iphone': 'ios',
                  'kodi': 'kodi',
                  'linux': 'linux',
                  'nexus': 'android',
                  'macos': 'macos',
                  'microsoft edge': 'msedge',
                  'opera': 'opera',
                  'osx': 'macos',
                  'playstation': 'playstation',
                  'plex home theater': 'plex',
                  'plex media player': 'plex',
                  'plexamp': 'plexamp',
                  'plextogether': 'synclounge',
                  'roku': 'roku',
                  'safari': 'safari',
                  'samsung': 'samsung',
                  'synclounge': 'synclounge',
                  'tivo': 'tivo',
                  'tvos': 'atv',
                  'vizio': 'opera',
                  'wiiu': 'wiiu',
                  'windows': 'windows',
                  'windows phone': 'wp',
                  'xbmc': 'xbmc',
                  'xbox': 'xbox'
                  }
PLATFORM_NAMES = OrderedDict(sorted(PLATFORM_NAMES.items(), key=lambda k: k[0], reverse=True))

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
                              '540': '540p',
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

VIDEO_QUALITY_PROFILES = {20000: '20 Mbps 1080p',
                          12000: '12 Mbps 1080p',
                          10000: '10 Mbps 1080p',
                          8000: '8 Mbps 1080p',
                          4000: '4 Mbps 720p',
                          3000: '3 Mbps 720p',
                          2000: '2 Mbps 720p',
                          1500: '1.5 Mbps 480p',
                          720: '0.7 Mbps 328p',
                          320: '0.3 Mbps 240p',
                          208: '0.2 Mbps 160p',
                          96: '0.096 Mbps',
                          64: '0.064 Mbps'
                          }
VIDEO_QUALITY_PROFILES = OrderedDict(sorted(VIDEO_QUALITY_PROFILES.items(), key=lambda k: k[0], reverse=True))

AUDIO_QUALITY_PROFILES = {512: '512 kbps',
                          320: '320 kbps',
                          256: '256 kbps',
                          192: '192 kbps',
                          128: '128 kbps',
                          96: '96 kbps'
                          }
AUDIO_QUALITY_PROFILES = OrderedDict(sorted(AUDIO_QUALITY_PROFILES.items(), key=lambda k: k[0], reverse=True))

SCHEDULER_LIST = ['Check GitHub for updates',
                  'Check for active sessions',
                  'Check for recently added items',
                  'Check for Plex updates',
                  'Check for Plex remote access',
                  'Check server response',
                  'Refresh users list',
                  'Refresh libraries list',
                  'Refresh Plex server URLs',
                  'Backup Tautulli database',
                  'Backup Tautulli config'
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
             {'name': 'Tautulli Version', 'type': 'str', 'value': 'plexpy_version', 'description': 'The current version of Tautulli.'},
             {'name': 'Tautulli Branch', 'type': 'str', 'value': 'plexpy_branch', 'description': 'The current git branch of Tautulli.'},
             {'name': 'Tautulli Commit', 'type': 'str', 'value': 'plexpy_commit', 'description': 'The current git commit hash of Tautulli.'},
             {'name': 'Server Name', 'type': 'str', 'value': 'server_name', 'description': 'The name of your Plex Server.'},
             {'name': 'Server Uptime', 'type': 'str', 'value': 'server_uptime', 'description': 'The uptime (in days, hours, mins, secs) of your Plex Server.'},
             {'name': 'Server Version', 'type': 'str', 'value': 'server_version', 'description': 'The current version of your Plex Server.'},
             {'name': 'Action', 'type': 'str', 'value': 'action', 'description': 'The action that triggered the notification.'},
             {'name': 'Datestamp', 'type': 'int', 'value': 'datestamp', 'description': 'The date (in date format) the notification was triggered.'},
             {'name': 'Timestamp', 'type': 'int', 'value': 'timestamp', 'description': 'The time (in time format) the notification was triggered.'},
         ]
     },
    {
        'category': 'Stream Details',
        'parameters': [
             {'name': 'Streams', 'type': 'int', 'value': 'streams', 'description': 'The number of concurrent streams.'},
             {'name': 'User Streams', 'type': 'int', 'value': 'user_streams', 'description': 'The number of concurrent streams by the person streaming.'},
             {'name': 'User', 'type': 'str', 'value': 'user', 'description': 'The friendly name of the person streaming.'},
             {'name': 'Username', 'type': 'str', 'value': 'username', 'description': 'The username of the person streaming.'},
             {'name': 'Device', 'type': 'str', 'value': 'device', 'description': 'The type of client device being used for playback.'},
             {'name': 'Platform', 'type': 'str', 'value': 'platform', 'description': 'The type of client platform being used for playback.'},
             {'name': 'Product', 'type': 'str', 'value': 'product', 'description': 'The type of client product being used for playback.'},
             {'name': 'Player', 'type': 'str', 'value': 'player', 'description': 'The name of the player being used for playback.'},
             {'name': 'IP Address', 'type': 'str', 'value': 'ip_address', 'description': 'The IP address of the device being used for playback.'},
             {'name': 'Stream Duration', 'type': 'int', 'value': 'stream_duration', 'description': 'The duration (in minutes) for the stream.'},
             {'name': 'Stream Time', 'type': 'str', 'value': 'stream_time', 'description': 'The duration (in time format) of the stream.'},
             {'name': 'Remaining Duration', 'type': 'int', 'value': 'remaining_duration', 'description': 'The remaining duration (in minutes) of the stream.'},
             {'name': 'Remaining Time', 'type': 'str', 'value': 'remaining_time', 'description': 'The remaining duration (in time format) of the stream.'},
             {'name': 'Progress Duration', 'type': 'int', 'value': 'progress_duration', 'description': 'The last reported offset (in minutes) of the stream.'},
             {'name': 'Progress Time', 'type': 'str', 'value': 'progress_time', 'description': 'The last reported offset (in time format) of the stream.'},
             {'name': 'Progress Percent', 'type': 'int', 'value': 'progress_percent', 'description': 'The last reported progress percent of the stream.'},
             {'name': 'Transcode Decision', 'type': 'str', 'value': 'transcode_decision', 'description': 'The transcode decisions of the stream.'},
             {'name': 'Video Decision', 'type': 'str', 'value': 'video_decision', 'description': 'The video transcode decisions of the stream.'},
             {'name': 'Audio Decision', 'type': 'str', 'value': 'audio_decision', 'description': 'The audio transcode decisions of the stream.'},
             {'name': 'Subtitle Decision', 'type': 'str', 'value': 'subtitle_decision', 'description': 'The subtitle transcode decisions of the stream.'},
             {'name': 'Quality Profile', 'type': 'str', 'value': 'quality_profile', 'description': 'The Plex quality profile of the stream.', 'example': 'e.g. Original, 4 Mbps 720p, etc.'},
             {'name': 'Optimized Version', 'type': 'int', 'value': 'optimized_version', 'description': 'If the stream is an optimized version.', 'example': '0 or 1'},
             {'name': 'Optimized Version Profile', 'type': 'str', 'value': 'optimized_version_profile', 'description': 'The optimized version profile of the stream.'},
             {'name': 'Synced Version', 'type': 'int', 'value': 'synced_version', 'description': 'If the stream is an synced version.', 'example': '0 or 1'},
             {'name': 'Stream Local', 'type': 'int', 'value': 'stream_local', 'description': 'If the stream is local.', 'example': '0 or 1'},
             {'name': 'Stream Location', 'type': 'str', 'value': 'stream_location', 'description': 'The network location of the stream.', 'example': 'lan or wan'},
             {'name': 'Stream Bandwidth', 'type': 'int', 'value': 'stream_bandwidth', 'description': 'The required bandwidth (in kbps) of the stream.', 'help_text': 'not the used bandwidth'},
             {'name': 'Stream Container', 'type': 'str', 'value': 'stream_container', 'description': 'The media container of the stream.'},
             {'name': 'Stream Bitrate', 'type': 'int', 'value': 'stream_bitrate', 'description': 'The bitrate (in kbps) of the stream.'},
             {'name': 'Stream Aspect Ratio', 'type': 'float', 'value': 'stream_aspect_ratio', 'description': 'The aspect ratio of the stream.'},
             {'name': 'Stream Video Codec', 'type': 'str', 'value': 'stream_video_codec', 'description': 'The video codec of the stream.'},
             {'name': 'Stream Video Codec Level', 'type': 'int', 'value': 'stream_video_codec_level', 'description': 'The video codec level of the stream.'},
             {'name': 'Stream Video Bitrate', 'type': 'int', 'value': 'stream_video_bitrate', 'description': 'The video bitrate (in kbps) of the stream.'},
             {'name': 'Stream Video Bit Depth', 'type': 'int', 'value': 'stream_video_bit_depth', 'description': 'The video bit depth of the stream.'},
             {'name': 'Stream Video Framerate', 'type': 'str', 'value': 'stream_video_framerate', 'description': 'The video framerate of the stream.'},
             {'name': 'Stream Video Ref Frames', 'type': 'int', 'value': 'stream_video_ref_frames', 'description': 'The video reference frames of the stream.'},
             {'name': 'Stream Video Resolution', 'type': 'str', 'value': 'stream_video_resolution', 'description': 'The video resolution of the stream.'},
             {'name': 'Stream Video Height', 'type': 'int', 'value': 'stream_video_height', 'description': 'The video height of the stream.'},
             {'name': 'Stream Video Width', 'type': 'int', 'value': 'stream_video_width', 'description': 'The video width of the stream.'},
             {'name': 'Stream Video Language', 'type': 'str', 'value': 'stream_video_language', 'description': 'The video language of the stream.'},
             {'name': 'Stream Video Language Code', 'type': 'str', 'value': 'stream_video_language_code', 'description': 'The video language code of the stream.'},
             {'name': 'Stream Audio Bitrate', 'type': 'int', 'value': 'stream_audio_bitrate', 'description': 'The audio bitrate of the stream.'},
             {'name': 'Stream Audio Bitrate Mode', 'type': 'str', 'value': 'stream_audio_bitrate_mode', 'description': 'The audio bitrate mode of the stream.', 'example': 'cbr or vbr'},
             {'name': 'Stream Audio Codec', 'type': 'str', 'value': 'stream_audio_codec', 'description': 'The audio codec of the stream.'},
             {'name': 'Stream Audio Channels', 'type': 'float', 'value': 'stream_audio_channels', 'description': 'The audio channels of the stream.'},
             {'name': 'Stream Audio Channel Layout', 'type': 'str', 'value': 'stream_audio_channel_layout', 'description': 'The audio channel layout of the stream.'},
             {'name': 'Stream Audio Sample Rate', 'type': 'int', 'value': 'stream_audio_sample_rate', 'description': 'The audio sample rate (in Hz) of the stream.'},
             {'name': 'Stream Audio Language', 'type': 'str', 'value': 'stream_audio_language', 'description': 'The audio language of the stream.'},
             {'name': 'Stream Audio Language Code', 'type': 'str', 'value': 'stream_audio_language_code', 'description': 'The audio language code of the stream.'},
             {'name': 'Stream Subtitle Codec', 'type': 'str', 'value': 'stream_subtitle_codec', 'description': 'The subtitle codec of the stream.'},
             {'name': 'Stream Subtitle Container', 'type': 'str', 'value': 'stream_subtitle_container', 'description': 'The subtitle container of the stream.'},
             {'name': 'Stream Subtitle Format', 'type': 'str', 'value': 'stream_subtitle_format', 'description': 'The subtitle format of the stream.'},
             {'name': 'Stream Subtitle Forced', 'type': 'int', 'value': 'stream_subtitle_forced', 'description': 'If the subtitles are forced.', 'example': '0 or 1'},
             {'name': 'Stream Subtitle Language', 'type': 'str', 'value': 'stream_subtitle_language', 'description': 'The subtitle language of the stream.'},
             {'name': 'Stream Subtitle Language Code', 'type': 'str', 'value': 'stream_subtitle_language_code', 'description': 'The subtitle language code of the stream.'},
             {'name': 'Stream Subtitle Location', 'type': 'str', 'value': 'stream_subtitle_location', 'description': 'The subtitle location of the stream.'},
             {'name': 'Transcode Container', 'type': 'str', 'value': 'transcode_container', 'description': 'The media container of the transcoded stream.'},
             {'name': 'Transcode Video Codec', 'type': 'str', 'value': 'transcode_video_codec', 'description': 'The video codec of the transcoded stream.'},
             {'name': 'Transcode Video Width', 'type': 'int', 'value': 'transcode_video_width', 'description': 'The video width of the transcoded stream.'},
             {'name': 'Transcode Video Height', 'type': 'int', 'value': 'transcode_video_height', 'description': 'The video height of the transcoded stream.'},
             {'name': 'Transcode Audio Codec', 'type': 'str', 'value': 'transcode_audio_codec', 'description': 'The audio codec of the transcoded stream.'},
             {'name': 'Transcode Audio Channels', 'type': 'float', 'value': 'transcode_audio_channels', 'description': 'The audio channels of the transcoded stream.'},
             {'name': 'Transcode Hardware', 'type': 'int', 'value': 'transcode_hardware', 'description': 'If hardware transcoding is used.', 'example': '0 or 1'},
             {'name': 'Session Key', 'type': 'str', 'value': 'session_key', 'description': 'The unique identifier for the session.'},
             {'name': 'Transcode Key', 'type': 'str', 'value': 'transcode_key', 'description': 'The unique identifier for the transcode session.'},
             {'name': 'Session ID', 'type': 'str', 'value': 'session_id', 'description': 'The unique identifier for the stream.'},
             {'name': 'User ID', 'type': 'int', 'value': 'user_id', 'description': 'The unique identifier for the user.'},
             {'name': 'Machine ID', 'type': 'str', 'value': 'machine_id', 'description': 'The unique identifier for the player.'},
         ]
     },
    {
        'category': 'Source Metadata Details',
        'parameters': [
             {'name': 'Media Type', 'type': 'str', 'value': 'media_type', 'description': 'The type of media.', 'example': 'movie, show, season, episode, artist, album, track'},
             {'name': 'Title', 'type': 'str', 'value': 'title', 'description': 'The full title of the item.'},
             {'name': 'Library Name', 'type': 'str', 'value': 'library_name', 'description': 'The library name of the item.'},
             {'name': 'Show Name', 'type': 'str', 'value': 'show_name', 'description': 'The title of the TV series.'},
             {'name': 'Episode Name', 'type': 'str', 'value': 'episode_name', 'description': 'The title of the episode.'},
             {'name': 'Artist Name', 'type': 'str', 'value': 'artist_name', 'description': 'The name of the artist.'},
             {'name': 'Album Name', 'type': 'str', 'value': 'album_name', 'description': 'The title of the album.'},
             {'name': 'Track Name', 'type': 'str', 'value': 'track_name', 'description': 'The title of the track.'},
             {'name': 'Season Number', 'type': 'int', 'value': 'season_num', 'description': 'The season number.', 'example': 'e.g. 1, or 1-3'},
             {'name': 'Season Number 00', 'type': 'int', 'value': 'season_num00', 'description': 'The two digit season number.', 'example': 'e.g. 01, or 01-03'},
             {'name': 'Episode Number', 'type': 'int', 'value': 'episode_num', 'description': 'The episode number.', 'example': 'e.g. 6, or 6-10'},
             {'name': 'Episode Number 00', 'type': 'int', 'value': 'episode_num00', 'description': 'The two digit episode number.', 'example': 'e.g. 06, or 06-10'},
             {'name': 'Track Number', 'type': 'int', 'value': 'track_num', 'description': 'The track number.', 'example': 'e.g. 4, or 4-10'},
             {'name': 'Track Number 00', 'type': 'int', 'value': 'track_num00', 'description': 'The two digit track number.', 'example': 'e.g. 04, or 04-10'},
             {'name': 'Year', 'type': 'int', 'value': 'year', 'description': 'The release year for the item.'},
             {'name': 'Release Date', 'type': 'int', 'value': 'release_date', 'description': 'The release date (in date format) for the item.'},
             {'name': 'Air Date', 'type': 'int', 'value': 'air_date', 'description': 'The air date (in date format) for the item.'},
             {'name': 'Added Date', 'type': 'int', 'value': 'added_date', 'description': 'The date (in date format) the item was added to Plex.'},
             {'name': 'Updated Date', 'type': 'int', 'value': 'updated_date', 'description': 'The date (in date format) the item was updated on Plex.'},
             {'name': 'Last Viewed Date', 'type': 'int', 'value': 'last_viewed_date', 'description': 'The date (in date format) the item was last viewed on Plex.'},
             {'name': 'Studio', 'type': 'str', 'value': 'studio', 'description': 'The studio for the item.'},
             {'name': 'Content Rating', 'type': 'int', 'value': 'content_rating', 'description': 'The content rating for the item.', 'example': 'e.g. TV-MA, TV-PG, etc.'},
             {'name': 'Director', 'type': 'str', 'value': 'directors', 'description': 'A list of directors for the item.'},
             {'name': 'Writer', 'type': 'str', 'value': 'writers', 'description': 'A list of writers for the item.'},
             {'name': 'Actor', 'type': 'str', 'value': 'actors', 'description': 'A list of actors for the item.'},
             {'name': 'Genre', 'type': 'str', 'value': 'genres', 'description': 'A list of genres for the item.'},
             {'name': 'Summary', 'type': 'str', 'value': 'summary', 'description': 'A short plot summary for the item.'},
             {'name': 'Tagline', 'type': 'str', 'value': 'tagline', 'description': 'A tagline for the media item.'},
             {'name': 'Rating', 'type': 'int', 'value': 'rating', 'description': 'The rating (out of 10) for the item.'},
             {'name': 'Audience Rating', 'type': 'int', 'value': 'audience_rating', 'description': 'The audience rating (%) for the item.', 'help_text': 'Ratings source must be Rotten Tomatoes for the Plex Movie agent'},
             {'name': 'Duration', 'type': 'int', 'value': 'duration', 'description': 'The duration (in minutes) for the item.'},
             {'name': 'Poster URL', 'type': 'str', 'value': 'poster_url', 'description': 'A URL for the movie, TV show, or album poster.'},
             {'name': 'Plex URL', 'type': 'str', 'value': 'plex_url', 'description': 'The Plex URL to your server for the item.'},
             {'name': 'IMDB ID', 'type': 'str', 'value': 'imdb_id', 'description': 'The IMDB ID for the movie.', 'example': 'e.g. tt2488496'},
             {'name': 'IMDB URL', 'type': 'str', 'value': 'imdb_url', 'description': 'The IMDB URL for the movie.'},
             {'name': 'TVDB ID', 'type': 'int', 'value': 'thetvdb_id', 'description': 'The TVDB ID for the TV show.', 'example': 'e.g. 121361'},
             {'name': 'TVDB URL', 'type': 'str', 'value': 'thetvdb_url', 'description': 'The TVDB URL for the TV show.'},
             {'name': 'TMDB ID', 'type': 'int', 'value': 'themoviedb_id', 'description': 'The TMDb ID for the movie or TV show.', 'example': 'e.g. 15260'},
             {'name': 'TMDB URL', 'type': 'str', 'value': 'themoviedb_url', 'description': 'The TMDb URL for the movie or TV show.'},
             {'name': 'TVmaze ID', 'type': 'int', 'value': 'tvmaze_id', 'description': 'The TVmaze ID for the TV show.', 'example': 'e.g. 290'},
             {'name': 'TVmaze URL', 'type': 'str', 'value': 'tvmaze_url', 'description': 'The TVmaze URL for the TV show.'},
             {'name': 'Last.fm URL', 'type': 'str', 'value': 'lastfm_url', 'description': 'The Last.fm URL for the album.'},
             {'name': 'Trakt.tv URL', 'type': 'str', 'value': 'trakt_url', 'description': 'The trakt.tv URL for the movie or TV show.'},
             {'name': 'Container', 'type': 'str', 'value': 'container', 'description': 'The media container of the original media.'},
             {'name': 'Bitrate', 'type': 'int', 'value': 'bitrate', 'description': 'The bitrate of the original media.'},
             {'name': 'Aspect Ratio', 'type': 'float', 'value': 'aspect_ratio', 'description': 'The aspect ratio of the original media.'},
             {'name': 'Video Codec', 'type': 'str', 'value': 'video_codec', 'description': 'The video codec of the original media.'},
             {'name': 'Video Codec Level', 'type': 'int', 'value': 'video_codec_level', 'description': 'The video codec level of the original media.'},
             {'name': 'Video Bitrate', 'type': 'int', 'value': 'video_bitrate', 'description': 'The video bitrate of the original media.'},
             {'name': 'Video Bit Depth', 'type': 'int', 'value': 'video_bit_depth', 'description': 'The video bit depth of the original media.'},
             {'name': 'Video Framerate', 'type': 'str', 'value': 'video_framerate', 'description': 'The video framerate of the original media.'},
             {'name': 'Video Ref Frames', 'type': 'int', 'value': 'video_ref_frames', 'description': 'The video reference frames of the original media.'},
             {'name': 'Video Resolution', 'type': 'str', 'value': 'video_resolution', 'description': 'The video resolution of the original media.'},
             {'name': 'Video Height', 'type': 'int', 'value': 'video_height', 'description': 'The video height of the original media.'},
             {'name': 'Video Width', 'type': 'int', 'value': 'video_width', 'description': 'The video width of the original media.'},
             {'name': 'Video Language', 'type': 'str', 'value': 'video_language', 'description': 'The video language of the original media.'},
             {'name': 'Video Language Code', 'type': 'str', 'value': 'video_language_code', 'description': 'The video language code of the original media.'},
             {'name': 'Audio Bitrate', 'type': 'int', 'value': 'audio_bitrate', 'description': 'The audio bitrate of the original media.'},
             {'name': 'Audio Bitrate Mode', 'type': 'str', 'value': 'audio_bitrate_mode', 'description': 'The audio bitrate mode of the original media.', 'example': 'cbr or vbr'},
             {'name': 'Audio Codec', 'type': 'str', 'value': 'audio_codec', 'description': 'The audio codec of the original media.'},
             {'name': 'Audio Channels', 'type': 'float', 'value': 'audio_channels', 'description': 'The audio channels of the original media.'},
             {'name': 'Audio Channel Layout', 'type': 'str', 'value': 'audio_channel_layout', 'description': 'The audio channel layout of the original media.'},
             {'name': 'Audio Sample Rate', 'type': 'int', 'value': 'audio_sample_rate', 'description': 'The audio sample rate (in Hz) of the original media.'},
             {'name': 'Audio Language', 'type': 'str', 'value': 'audio_language', 'description': 'The audio language of the original media.'},
             {'name': 'Audio Language Code', 'type': 'str', 'value': 'audio_language_code', 'description': 'The audio language code of the original media.'},
             {'name': 'Subtitle Codec', 'type': 'str', 'value': 'subtitle_codec', 'description': 'The subtitle codec of the original media.'},
             {'name': 'Subtitle Container', 'type': 'str', 'value': 'subtitle_container', 'description': 'The subtitle container of the original media.'},
             {'name': 'Subtitle Format', 'type': 'str', 'value': 'subtitle_format', 'description': 'The subtitle format of the original media.'},
             {'name': 'Subtitle Forced', 'type': 'int', 'value': 'subtitle_forced', 'description': 'If the subtitles are forced.', 'example': '0 or 1'},
             {'name': 'Subtitle Location', 'type': 'str', 'value': 'subtitle_location', 'description': 'The subtitle location of the original media.'},
             {'name': 'Subtitle Language', 'type': 'str', 'value': 'subtitle_language', 'description': 'The subtitle language of the original media.'},
             {'name': 'Subtitle Language Code', 'type': 'str', 'value': 'subtitle_language_code', 'description': 'The subtitle language code of the original media.'},
             {'name': 'File', 'type': 'str', 'value': 'file', 'description': 'The file path to the item.'},
             {'name': 'File Size', 'type': 'int', 'value': 'file_size', 'description': 'The file size of the item.'},
             {'name': 'Section ID', 'type': 'int', 'value': 'section_id', 'description': 'The unique identifier for the library.'},
             {'name': 'Rating Key', 'type': 'int', 'value': 'rating_key', 'description': 'The unique identifier for the movie, episode, or track.'},
             {'name': 'Parent Rating Key', 'type': 'int', 'value': 'parent_rating_key', 'description': 'The unique identifier for the season or album.'},
             {'name': 'Grandparent Rating Key', 'type': 'int', 'value': 'grandparent_rating_key', 'description': 'The unique identifier for the TV show or artist.'},
             {'name': 'Thumb', 'type': 'str', 'value': 'thumb', 'description': 'The Plex thumbnail for the movie or episode.'},
             {'name': 'Parent Thumb', 'type': 'str', 'value': 'parent_thumb', 'description': 'The Plex thumbnail for the season or album.'},
             {'name': 'Grandparent Thumb', 'type': 'str', 'value': 'grandparent_thumb', 'description': 'The Plex thumbnail for the TV show or artist.'},
             {'name': 'Poster Thumb', 'type': 'str', 'value': 'poster_thumb', 'description': 'The Plex thumbnail for the poster image.'},
             {'name': 'Poster Title', 'type': 'str', 'value': 'poster_title', 'description': 'The title for the poster image.'},
             {'name': 'Indexes', 'type': 'int', 'value': 'indexes', 'description': 'If the media has video preview thumbnails.', 'example': '0 or 1'},
         ]
     },
    {
        'category': 'Plex Update Available',
        'parameters': [
             {'name': 'Update Version', 'type': 'int', 'value': 'update_version', 'description': 'The available update version for your Plex Server.'},
             {'name': 'Update Url', 'type': 'int', 'value': 'update_url', 'description': 'The download URL for the available update.'},
             {'name': 'Update Release Date', 'type': 'int', 'value': 'update_release_date', 'description': 'The release date of the available update.'},
             {'name': 'Update Channel', 'type': 'int', 'value': 'update_channel', 'description': 'The update channel.', 'example': 'Public or Plex Pass'},
             {'name': 'Update Platform', 'type': 'int', 'value': 'update_platform', 'description': 'The platform of your Plex Server.'},
             {'name': 'Update Distro', 'type': 'int', 'value': 'update_distro', 'description': 'The distro of your Plex Server.'},
             {'name': 'Update Distro Build', 'type': 'int', 'value': 'update_distro_build', 'description': 'The distro build of your Plex Server.'},
             {'name': 'Update Requirements', 'type': 'int', 'value': 'update_requirements', 'description': 'The requirements for the available update.'},
             {'name': 'Update Extra Info', 'type': 'int', 'value': 'update_extra_info', 'description': 'Any extra info for the available update.'},
             {'name': 'Update Changelog Added', 'type': 'int', 'value': 'update_changelog_added', 'description': 'The added changelog for the available update.'},
             {'name': 'Update Changelog Fixed', 'type': 'int', 'value': 'update_changelog_fixed', 'description': 'The fixed changelog for the available update.'},
         ]
     },
    {
        'category': 'Tautulli Update Available',
        'parameters': [
             {'name': 'Plexpy Update Version', 'type': 'int', 'value': 'plexpy_update_version', 'description': 'The available update version for Tautulli.'},
             {'name': 'Plexpy Update Tar', 'type': 'int', 'value': 'plexpy_update_tar', 'description': 'The tar download URL for the available update.'},
             {'name': 'Plexpy Update Zip', 'type': 'int', 'value': 'plexpy_update_zip', 'description': 'The zip download URL for the available update.'},
             {'name': 'Plexpy Update Commit', 'type': 'int', 'value': 'plexpy_update_commit', 'description': 'The commit hash for the available update.'},
             {'name': 'Plexpy Update Behind', 'type': 'int', 'value': 'plexpy_update_behind', 'description': 'The number of commits behind for the available update.'},
             {'name': 'Plexpy Update Changelog', 'type': 'int', 'value': 'plexpy_update_changelog', 'description': 'The changelog for the available update.'},
        ]
     },
    ]
