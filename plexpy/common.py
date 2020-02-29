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
PRODUCT = 'Tautulli'
PLATFORM = platform.system()
PLATFORM_RELEASE = platform.release()
PLATFORM_VERSION = platform.version()
PLATFORM_LINUX_DISTRO = ' '.join(x for x in platform.linux_distribution() if x)
PLATFORM_DEVICE_NAME = platform.node()
BRANCH = version.PLEXPY_BRANCH
RELEASE = version.PLEXPY_RELEASE_VERSION

USER_AGENT = '{}/{} ({} {})'.format(PRODUCT, RELEASE, PLATFORM, PLATFORM_RELEASE)

DEFAULT_USER_THUMB = "interfaces/default/images/gravatar-default-80x80.png"
DEFAULT_POSTER_THUMB = "interfaces/default/images/poster.png"
DEFAULT_COVER_THUMB = "interfaces/default/images/cover.png"
DEFAULT_ART = "interfaces/default/images/art.png"

ONLINE_POSTER_THUMB = "https://tautulli.com/images/poster.png"
ONLINE_COVER_THUMB = "https://tautulli.com/images/cover.png"
ONLINE_ART = "https://tautulli.com/images/art.png"

MEDIA_TYPE_HEADERS = {
    'movie': 'Movies',
    'show': 'TV Shows',
    'season': 'Seasons',
    'episode': 'Episodes',
    'artist': 'Artists',
    'album': 'Albums',
    'track': 'Tracks',
}

PLATFORM_NAME_OVERRIDES = {
    'Konvergo': 'Plex Media Player',
    'Mystery 3': 'Playstation 3',
    'Mystery 4': 'Playstation 4',
    'Mystery 5': 'Xbox 360',
    'WebMAF': 'Playstation 4',
    'windows': 'Windows',
    'osx': 'macOS'
}

PMS_PLATFORM_NAME_OVERRIDES = {
    'MacOSX': 'Mac'
}

PLATFORM_NAMES = {
    'android': 'android',
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
    'tizen': 'samsung',
    'tvos': 'atv',
    'vizio': 'opera',
    'wiiu': 'wiiu',
    'windows': 'windows',
    'windows phone': 'wp',
    'xbmc': 'xbmc',
    'xbox': 'xbox'
}
PLATFORM_NAMES = OrderedDict(sorted(PLATFORM_NAMES.items(), key=lambda k: k[0], reverse=True))

MEDIA_FLAGS_AUDIO = {
    'ac.?3': 'dolby_digital',
    'truehd': 'dolby_truehd',
    '(dca|dta)': 'dts',
    'dts(hd_|-hd|-)?ma': 'dca-ma',
    'vorbis': 'ogg'
}
MEDIA_FLAGS_VIDEO = {
    'avc1': 'h264',
    'wmv(1|2)': 'wmv',
    'wmv3': 'wmvhd'
}

AUDIO_CODEC_OVERRIDES = {
    'truehd': 'TrueHD'
}

VIDEO_RESOLUTION_OVERRIDES = {
    'sd': 'SD',
    '4k': '4k'
}

AUDIO_CHANNELS = {
    '1': 'Mono',
    '2': 'Stereo',
    '3': '2.1',
    '4': '3.1',
    '6': '5.1',
    '7': '6.1',
    '8': '7.1'
}

VIDEO_QUALITY_PROFILES = {
    20000: '20 Mbps 1080p',
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

AUDIO_QUALITY_PROFILES = {
    512: '512 kbps',
    320: '320 kbps',
    256: '256 kbps',
    192: '192 kbps',
    128: '128 kbps',
    96: '96 kbps'
}
AUDIO_QUALITY_PROFILES = OrderedDict(sorted(AUDIO_QUALITY_PROFILES.items(), key=lambda k: k[0], reverse=True))

HW_DECODERS = [
    'dxva2',
    'videotoolbox',
    'mediacodecndk',
    'vaapi',
    'nvdec'
]
HW_ENCODERS = [
    'qsv',
    'mf',
    'videotoolbox',
    'mediacodecndk',
    'vaapi',
    'nvenc',
    'x264'
]

EXTRA_TYPES = {
    '1': 'Trailer',
    '2': 'Deleted Scene',
    '3': 'Interview',
    '5': 'Behind the Scenes',
    '6': 'Scene',
    '10': 'Featurette',
    '11': 'Short'
}

SCHEDULER_LIST = [
    'Check GitHub for updates',
    'Check for server response',
    'Check for active sessions',
    'Check for recently added items',
    'Check for Plex updates',
    'Check for Plex remote access',
    'Refresh users list',
    'Refresh libraries list',
    'Refresh Plex server URLs',
    'Backup Tautulli database',
    'Backup Tautulli config',
    'Update GeoLite2 database'
]

DATE_TIME_FORMATS = [
    {
        'category': 'Year',
        'parameters': [
            {'value': 'YYYY', 'description': 'Numeric, four digits', 'example': '1999, 2003'},
            {'value': 'YY', 'description': 'Numeric, two digits', 'example': '99, 03'}
        ]
     },
    {
        'category': 'Month',
        'parameters': [
            {'value': 'MMMM', 'description': 'Textual, full', 'example': 'January-December'},
            {'value': 'MMM', 'description': 'Textual, three letters', 'example': 'Jan-Dec'},
            {'value': 'MM', 'description': 'Numeric, with leading zeros', 'example': '01-12'},
            {'value': 'M', 'description': 'Numeric, without leading zeros', 'example': '1-12'},
            {'value': 'Mo', 'description': 'Numeric, with suffix', 'example': '1st, 2nd ... 12th'},
        ]
     },
    {
        'category': 'Day of the Year',
        'parameters': [
            {'value': 'DDDD', 'description': 'Numeric, with leading zeros', 'example': '001-365'},
            {'value': 'DDD', 'description': 'Numeric, without leading zeros', 'example': '1-365'},
            {'value': 'DDDo', 'description': 'Numeric, with suffix', 'example': '1st, 2nd, ... 365th'},
        ]
     },
    {
        'category': 'Day of the Month',
        'parameters': [
            {'value': 'DD', 'description': 'Numeric, with leading zeros', 'example': '01-31'},
            {'value': 'D', 'description': 'Numeric, without leading zeros', 'example': '1-31'},
            {'value': 'Do', 'description': 'Numeric, with suffix', 'example': '1st, 2nd ... 31st'},
        ]
     },
    {
        'category': 'Day of the Week',
        'parameters': [
            {'value': 'dddd', 'description': 'Textual, full', 'example': 'Sunday-Saturday'},
            {'value': 'ddd', 'description': 'Textual, three letters', 'example': 'Sun-Sat'},
            {'value': 'dd', 'description': 'Textual, two letters', 'example': 'Su-Sa'},
            {'value': 'd', 'description': 'Numeric', 'example': '0-6'},
            {'value': 'do', 'description': 'Numeric, with suffix', 'example': '0th, 1st ... 6th'},
        ]
     },
    {
        'category': 'Hour',
        'parameters': [
            {'value': 'HH', 'description': '24-hour, with leading zeros', 'example': '00-23'},
            {'value': 'H', 'description': '24-hour, without leading zeros', 'example': '0-23'},
            {'value': 'hh', 'description': '12-hour, with leading zeros', 'example': '01-12'},
            {'value': 'h', 'description': '12-hour, without leading zeros', 'example': '1-12'},
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
            {'value': 'ZZ', 'description': 'UTC offset', 'example': '+0100, -0700'},
            {'value': 'Z', 'description': 'UTC offset', 'example': '+01:00, -07:00'},
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
             {'name': 'Tautulli Version', 'type': 'str', 'value': 'tautulli_version', 'description': 'The current version of Tautulli.'},
             {'name': 'Tautulli Remote', 'type': 'str', 'value': 'tautulli_remote', 'description': 'The current git remote of Tautulli.'},
             {'name': 'Tautulli Branch', 'type': 'str', 'value': 'tautulli_branch', 'description': 'The current git branch of Tautulli.'},
             {'name': 'Tautulli Commit', 'type': 'str', 'value': 'tautulli_commit', 'description': 'The current git commit hash of Tautulli.'},
             {'name': 'Server Name', 'type': 'str', 'value': 'server_name', 'description': 'The name of your Plex Server.'},
             {'name': 'Server IP', 'type': 'str', 'value': 'server_ip', 'description': 'The connection IP address for your Plex Server.'},
             {'name': 'Server Port', 'type': 'int', 'value': 'server_port', 'description': 'The connection port for your Plex Server.'},
             {'name': 'Server URL', 'type': 'str', 'value': 'server_url', 'description': 'The connection URL for your Plex Server.'},
             {'name': 'Server Platform', 'type': 'str', 'value': 'server_platform', 'description': 'The platform of your Plex Server.'},
             {'name': 'Server Version', 'type': 'str', 'value': 'server_version', 'description': 'The current version of your Plex Server.'},
             {'name': 'Server ID', 'type': 'str', 'value': 'server_machine_id', 'description': 'The unique identifier for your Plex Server.'},
             {'name': 'Action', 'type': 'str', 'value': 'action', 'description': 'The action that triggered the notification.'},
             {'name': 'Current Year', 'type': 'int', 'value': 'current_year', 'description': 'The year when the notification is triggered.'},
             {'name': 'Current Month', 'type': 'int', 'value': 'current_month', 'description': 'The month when the notification is triggered.', 'example': '1 to 12'},
             {'name': 'Current Day', 'type': 'int', 'value': 'current_day', 'description': 'The day when the notification is triggered.', 'example': '1 to 31'},
             {'name': 'Current Hour', 'type': 'int', 'value': 'current_hour', 'description': 'The hour when the notification is triggered.', 'example': '0 to 23'},
             {'name': 'Current Minute', 'type': 'int', 'value': 'current_minute', 'description': 'The minute when the notification is triggered.', 'example': '0 to 59'},
             {'name': 'Current Second', 'type': 'int', 'value': 'current_second', 'description': 'The second when the notification is triggered.', 'example': '0 to 59'},
             {'name': 'Current Weekday', 'type': 'int', 'value': 'current_weekday', 'description': 'The ISO weekday when the notification is triggered.', 'example': '1 (Mon) to 7 (Sun)'},
             {'name': 'Current Week', 'type': 'int', 'value': 'current_week', 'description': 'The ISO week number when the notification is triggered.', 'example': '1 to 52'},
             {'name': 'Datestamp', 'type': 'str', 'value': 'datestamp', 'description': 'The date (in date format) when the notification is triggered.'},
             {'name': 'Timestamp', 'type': 'str', 'value': 'timestamp', 'description': 'The time (in time format) when the notification is triggered.'},
             {'name': 'Unix Time', 'type': 'int', 'value': 'unixtime', 'description': 'The unix timestamp when the notification is triggered.'},
             {'name': 'UTC Time', 'type': 'int', 'value': 'utctime', 'description': 'The UTC timestamp in ISO format when the notification is triggered.'},
        ]
     },
    {
        'category': 'Stream Details',
        'parameters': [
             {'name': 'Streams', 'type': 'int', 'value': 'streams', 'description': 'The number of concurrent streams.'},
             {'name': 'User Streams', 'type': 'int', 'value': 'user_streams', 'description': 'The number of concurrent streams by the person streaming.'},
             {'name': 'User', 'type': 'str', 'value': 'user', 'description': 'The friendly name of the person streaming.'},
             {'name': 'Username', 'type': 'str', 'value': 'username', 'description': 'The username of the person streaming.'},
             {'name': 'User Email', 'type': 'str', 'value': 'user_email', 'description': 'The email address of the person streaming.'},
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
             {'name': 'Live', 'type': 'int', 'value': 'live', 'description': 'If the stream is live TV.', 'example': '0 or 1'},
             {'name': 'Secure', 'type': 'int', 'value': 'secure', 'description': 'If the stream is using a secure connection.', 'example': '0 or 1'},
             {'name': 'Relayed', 'type': 'int', 'value': 'relayed', 'description': 'If the stream is using Plex Relay.', 'example': '0 or 1'},
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
             {'name': 'Stream Video Chroma Subsampling', 'type': 'str', 'value': 'stream_video_chroma_subsampling', 'description': 'The video chroma subsampling of the stream.'},
             {'name': 'Stream Video Color Primaries', 'type': 'str', 'value': 'stream_video_color_primaries', 'description': 'The video color primaries of the stream.'},
             {'name': 'Stream Video Color Range', 'type': 'str', 'value': 'stream_video_color_range', 'description': 'The video color range of the stream.'},
             {'name': 'Stream Video Color Space', 'type': 'str', 'value': 'stream_video_color_space', 'description': 'The video color space of the stream.'},
             {'name': 'Stream Video Color Transfer Function', 'type': 'str', 'value': 'stream_video_color_trc', 'description': 'The video transfer function of the stream.'},
             {'name': 'Stream Video Dynamic Range', 'type': 'str', 'value': 'stream_video_dynamic_range', 'description': 'The video dynamic range of the stream.', 'example': 'HDR or SDR'},
             {'name': 'Stream Video Framerate', 'type': 'str', 'value': 'stream_video_framerate', 'description': 'The video framerate of the stream.'},
             {'name': 'Stream Video Full Resolution', 'type': 'str', 'value': 'stream_video_full_resolution', 'description': 'The video resolution of the stream with scan type.'},
             {'name': 'Stream Video Ref Frames', 'type': 'int', 'value': 'stream_video_ref_frames', 'description': 'The video reference frames of the stream.'},
             {'name': 'Stream Video Resolution', 'type': 'str', 'value': 'stream_video_resolution', 'description': 'The video resolution of the stream.'},
             {'name': 'Stream Video Scan Type', 'type': 'str', 'value': 'stream_video_scan_type', 'description': 'The video scan type of the stream.'},
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
             {'name': 'Transcode HW Requested', 'type': 'int', 'value': 'transcode_hw_requested', 'description': 'If hardware decoding/encoding was requested.', 'example': '0 or 1'},
             {'name': 'Transcode HW Decoding', 'type': 'int', 'value': 'transcode_hw_decoding', 'description': 'If hardware decoding is used.', 'example': '0 or 1'},
             {'name': 'Transcode HW Decoding Codec', 'type': 'str', 'value': 'transcode_hw_decode', 'description': 'The hardware decoding codec.'},
             {'name': 'Transcode HW Decoding Title', 'type': 'str', 'value': 'transcode_hw_decode_title', 'description': 'The hardware decoding codec title.'},
             {'name': 'Transcode HW Encoding', 'type': 'int', 'value': 'transcode_hw_encoding', 'description': 'If hardware encoding is used.', 'example': '0 or 1'},
             {'name': 'Transcode HW Encoding Codec', 'type': 'str', 'value': 'transcode_hw_encode', 'description': 'The hardware encoding codec.'},
             {'name': 'Transcode HW Encoding Title', 'type': 'str', 'value': 'transcode_hw_encode_title', 'description': 'The hardware encoding codec title.'},
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
             {'name': 'Media Type', 'type': 'str', 'value': 'media_type', 'description': 'The type of media.', 'example': 'movie, show, season, episode, artist, album, track, clip'},
             {'name': 'Title', 'type': 'str', 'value': 'title', 'description': 'The full title of the item.'},
             {'name': 'Library Name', 'type': 'str', 'value': 'library_name', 'description': 'The library name of the item.'},
             {'name': 'Show Name', 'type': 'str', 'value': 'show_name', 'description': 'The title of the TV series.'},
             {'name': 'Episode Name', 'type': 'str', 'value': 'episode_name', 'description': 'The title of the episode.'},
             {'name': 'Artist Name', 'type': 'str', 'value': 'artist_name', 'description': 'The name of the artist.'},
             {'name': 'Album Name', 'type': 'str', 'value': 'album_name', 'description': 'The title of the album.'},
             {'name': 'Track Name', 'type': 'str', 'value': 'track_name', 'description': 'The title of the track.'},
             {'name': 'Track Artist', 'type': 'str', 'value': 'track_artist', 'description': 'The name of the artist of the track.'},
             {'name': 'Season Number', 'type': 'int', 'value': 'season_num', 'description': 'The season number.', 'example': 'e.g. 1, or 1-3'},
             {'name': 'Season Number 00', 'type': 'int', 'value': 'season_num00', 'description': 'The two digit season number.', 'example': 'e.g. 01, or 01-03'},
             {'name': 'Episode Number', 'type': 'int', 'value': 'episode_num', 'description': 'The episode number.', 'example': 'e.g. 6, or 6-10'},
             {'name': 'Episode Number 00', 'type': 'int', 'value': 'episode_num00', 'description': 'The two digit episode number.', 'example': 'e.g. 06, or 06-10'},
             {'name': 'Track Number', 'type': 'int', 'value': 'track_num', 'description': 'The track number.', 'example': 'e.g. 4, or 4-10'},
             {'name': 'Track Number 00', 'type': 'int', 'value': 'track_num00', 'description': 'The two digit track number.', 'example': 'e.g. 04, or 04-10'},
             {'name': 'Season Count', 'type': 'int', 'value': 'season_count', 'description': 'The number of seasons.'},
             {'name': 'Episode Count', 'type': 'int', 'value': 'episode_count', 'description': 'The number of episodes.'},
             {'name': 'Album Count', 'type': 'int', 'value': 'album_count', 'description': 'The number of albums.'},
             {'name': 'Track Count', 'type': 'int', 'value': 'track_count', 'description': 'The number of tracks.'},
             {'name': 'Year', 'type': 'int', 'value': 'year', 'description': 'The release year for the item.'},
             {'name': 'Release Date', 'type': 'str', 'value': 'release_date', 'description': 'The release date (in date format) for the item.'},
             {'name': 'Air Date', 'type': 'str', 'value': 'air_date', 'description': 'The air date (in date format) for the item.'},
             {'name': 'Added Date', 'type': 'str', 'value': 'added_date', 'description': 'The date (in date format) the item was added to Plex.'},
             {'name': 'Updated Date', 'type': 'str', 'value': 'updated_date', 'description': 'The date (in date format) the item was updated on Plex.'},
             {'name': 'Last Viewed Date', 'type': 'str', 'value': 'last_viewed_date', 'description': 'The date (in date format) the item was last viewed on Plex.'},
             {'name': 'Studio', 'type': 'str', 'value': 'studio', 'description': 'The studio for the item.'},
             {'name': 'Content Rating', 'type': 'str', 'value': 'content_rating', 'description': 'The content rating for the item.', 'example': 'e.g. TV-MA, TV-PG, etc.'},
             {'name': 'Directors', 'type': 'str', 'value': 'directors', 'description': 'A list of directors for the item.'},
             {'name': 'Writers', 'type': 'str', 'value': 'writers', 'description': 'A list of writers for the item.'},
             {'name': 'Actors', 'type': 'str', 'value': 'actors', 'description': 'A list of actors for the item.'},
             {'name': 'Genres', 'type': 'str', 'value': 'genres', 'description': 'A list of genres for the item.'},
             {'name': 'Labels', 'type': 'str', 'value': 'labels', 'description': 'A list of labels for the item.'},
             {'name': 'Collections', 'type': 'str', 'value': 'collections', 'description': 'A list of collections for the item.'},
             {'name': 'Summary', 'type': 'str', 'value': 'summary', 'description': 'A short plot summary for the item.'},
             {'name': 'Tagline', 'type': 'str', 'value': 'tagline', 'description': 'A tagline for the media item.'},
             {'name': 'Rating', 'type': 'float', 'value': 'rating', 'description': 'The rating (out of 10) for the item.'},
             {'name': 'Critic Rating', 'type': 'int', 'value': 'critic_rating', 'description': 'The critic rating (%) for the item.', 'help_text': 'Ratings source must be Rotten Tomatoes for the Plex Movie agent'},
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
             {'name': 'MusicBrainz ID', 'type': 'str', 'value': 'musicbrainz_id', 'description': 'The MusicBrainz ID for the artist, album, or track.', 'example': 'e.g. b670dfcf-9824-4309-a57e-03595aaba286'},
             {'name': 'MusicBrainz URL', 'type': 'str', 'value': 'musicbrainz_url', 'description': 'The MusicBrainz URL for the artist, album, or track.'},
             {'name': 'Last.fm URL', 'type': 'str', 'value': 'lastfm_url', 'description': 'The Last.fm URL for the album.', 'help_text': 'Music library agent must be Last.fm'},
             {'name': 'Trakt.tv URL', 'type': 'str', 'value': 'trakt_url', 'description': 'The trakt.tv URL for the movie or TV show.'},
             {'name': 'Container', 'type': 'str', 'value': 'container', 'description': 'The media container of the original media.'},
             {'name': 'Bitrate', 'type': 'int', 'value': 'bitrate', 'description': 'The bitrate of the original media.'},
             {'name': 'Aspect Ratio', 'type': 'float', 'value': 'aspect_ratio', 'description': 'The aspect ratio of the original media.'},
             {'name': 'Video Codec', 'type': 'str', 'value': 'video_codec', 'description': 'The video codec of the original media.'},
             {'name': 'Video Codec Level', 'type': 'int', 'value': 'video_codec_level', 'description': 'The video codec level of the original media.'},
             {'name': 'Video Bitrate', 'type': 'int', 'value': 'video_bitrate', 'description': 'The video bitrate of the original media.'},
             {'name': 'Video Bit Depth', 'type': 'int', 'value': 'video_bit_depth', 'description': 'The video bit depth of the original media.'},
             {'name': 'Video Chroma Subsampling', 'type': 'str', 'value': 'video_chroma_subsampling', 'description': 'The video chroma subsampling of the original media.'},
             {'name': 'Video Color Primaries', 'type': 'str', 'value': 'video_color_primaries', 'description': 'The video color primaries of the original media.'},
             {'name': 'Video Color Range', 'type': 'str', 'value': 'video_color_range', 'description': 'The video color range of the original media.'},
             {'name': 'Video Color Space', 'type': 'str', 'value': 'video_color_space', 'description': 'The video color space of the original media.'},
             {'name': 'Video Color Transfer Function', 'type': 'str', 'value': 'video_color_trc', 'description': 'The video transfer function of the original media.'},
             {'name': 'Video Dynamic Range', 'type': 'str', 'value': 'video_dynamic_range', 'description': 'The video dynamic range of the original media.', 'example': 'HDR or SDR'},
             {'name': 'Video Framerate', 'type': 'str', 'value': 'video_framerate', 'description': 'The video framerate of the original media.'},
             {'name': 'Video Full Resolution', 'type': 'str', 'value': 'video_full_resolution', 'description': 'The video resolution of the original media with scan type.'},
             {'name': 'Video Ref Frames', 'type': 'int', 'value': 'video_ref_frames', 'description': 'The video reference frames of the original media.'},
             {'name': 'Video Resolution', 'type': 'str', 'value': 'video_resolution', 'description': 'The video resolution of the original media.'},
             {'name': 'Video Scan Tpye', 'type': 'str', 'value': 'video_scan_type', 'description': 'The video scan type of the original media.'},
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
             {'name': 'Filename', 'type': 'str', 'value': 'filename', 'description': 'The file name of the item.'},
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
             {'name': 'Update Version', 'type': 'str', 'value': 'update_version', 'description': 'The available update version for your Plex Server.'},
             {'name': 'Update Url', 'type': 'str', 'value': 'update_url', 'description': 'The download URL for the available update.'},
             {'name': 'Update Release Date', 'type': 'str', 'value': 'update_release_date', 'description': 'The release date of the available update.'},
             {'name': 'Update Channel', 'type': 'str', 'value': 'update_channel', 'description': 'The update channel.', 'example': 'Public or Plex Pass'},
             {'name': 'Update Platform', 'type': 'str', 'value': 'update_platform', 'description': 'The platform of your Plex Server.'},
             {'name': 'Update Distro', 'type': 'str', 'value': 'update_distro', 'description': 'The distro of your Plex Server.'},
             {'name': 'Update Distro Build', 'type': 'str', 'value': 'update_distro_build', 'description': 'The distro build of your Plex Server.'},
             {'name': 'Update Requirements', 'type': 'str', 'value': 'update_requirements', 'description': 'The requirements for the available update.'},
             {'name': 'Update Extra Info', 'type': 'str', 'value': 'update_extra_info', 'description': 'Any extra info for the available update.'},
             {'name': 'Update Changelog Added', 'type': 'str', 'value': 'update_changelog_added', 'description': 'The added changelog for the available update.'},
             {'name': 'Update Changelog Fixed', 'type': 'str', 'value': 'update_changelog_fixed', 'description': 'The fixed changelog for the available update.'},
         ]
     },
    {
        'category': 'Tautulli Update Available',
        'parameters': [
             {'name': 'Tautulli Update Version', 'type': 'str', 'value': 'tautulli_update_version', 'description': 'The available update version for Tautulli.'},
             {'name': 'Tautulli Update Release URL', 'type': 'str', 'value': 'tautulli_update_release_url', 'description': 'The release page URL on GitHub.'},
             {'name': 'Tautulli Update Tar', 'type': 'str', 'value': 'tautulli_update_tar', 'description': 'The tar download URL for the available update.'},
             {'name': 'Tautulli Update Zip', 'type': 'str', 'value': 'tautulli_update_zip', 'description': 'The zip download URL for the available update.'},
             {'name': 'Tautulli Update Commit', 'type': 'str', 'value': 'tautulli_update_commit', 'description': 'The commit hash for the available update.'},
             {'name': 'Tautulli Update Behind', 'type': 'int', 'value': 'tautulli_update_behind', 'description': 'The number of commits behind for the available update.'},
             {'name': 'Tautulli Update Changelog', 'type': 'str', 'value': 'tautulli_update_changelog', 'description': 'The changelog for the available update.'},
        ]
     },
]

NEWSLETTER_PARAMETERS = [
    {
        'category': 'Global',
        'parameters': [
            {'name': 'Server Name', 'type': 'str', 'value': 'server_name', 'description': 'The name of your Plex Server.'},
            {'name': 'Start Date', 'type': 'str', 'value': 'start_date', 'description': 'The start date of the newsletter.'},
            {'name': 'End Date', 'type': 'str', 'value': 'end_date', 'description': 'The end date of the newsletter.'},
            {'name': 'Current Year', 'type': 'int', 'value': 'current_year', 'description': 'The year of the start date of the newsletter.'},
            {'name': 'Current Month', 'type': 'int', 'value': 'current_month', 'description': 'The month of the start date of the newsletter.', 'example': '1 to 12'},
            {'name': 'Current Day', 'type': 'int', 'value': 'current_day', 'description': 'The day of the start date of the newsletter.', 'example': '1 to 31'},
            {'name': 'Current Hour', 'type': 'int', 'value': 'current_hour', 'description': 'The hour of the start date of the newsletter.', 'example': '0 to 23'},
            {'name': 'Current Minute', 'type': 'int', 'value': 'current_minute', 'description': 'The minute of the start date of the newsletter.', 'example': '0 to 59'},
            {'name': 'Current Second', 'type': 'int', 'value': 'current_second', 'description': 'The second of the start date of the newsletter.', 'example': '0 to 59'},
            {'name': 'Current Weekday', 'type': 'int', 'value': 'current_weekday', 'description': 'The ISO weekday of the start date of the newsletter.', 'example': '1 (Mon) to 7 (Sun)'},
            {'name': 'Current Week', 'type': 'int', 'value': 'current_week', 'description': 'The ISO week number of the start date of the newsletter.', 'example': '1 to 52'},
            {'name': 'Newsletter Time Frame', 'type': 'int', 'value': 'newsletter_time_frame', 'description': 'The time frame included in the newsletter.'},
            {'name': 'Newsletter Time Frame Units', 'type': 'str', 'value': 'newsletter_time_frame_units', 'description': 'The time frame units included in the newsletter.'},
            {'name': 'Newsletter URL', 'type': 'str', 'value': 'newsletter_url', 'description': 'The self-hosted URL to the newsletter.'},
            {'name': 'Newsletter Static URL', 'type': 'str', 'value': 'newsletter_static_url', 'description': 'The static self-hosted URL to the latest scheduled newsletter for the agent.'},
            {'name': 'Newsletter UUID', 'type': 'str', 'value': 'newsletter_uuid', 'description': 'The unique identifier for the newsletter.'},
            {'name': 'Newsletter ID', 'type': 'int', 'value': 'newsletter_id', 'description': 'The unique ID number for the newsletter agent.'},
            {'name': 'Newsletter ID Name', 'type': 'int', 'value': 'newsletter_id_name', 'description': 'The unique ID name for the newsletter agent.'},
            {'name': 'Newsletter Password', 'type': 'str', 'value': 'newsletter_password', 'description': 'The password required to view the newsletter if enabled.'},
        ]
     },
    {
        'category': 'Recently Added',
        'parameters': [
            {'name': 'Included Libraries', 'type': 'str', 'value': 'newsletter_libraries', 'description': 'The list of libraries included in the newsletter.'},
        ]
    }
]
