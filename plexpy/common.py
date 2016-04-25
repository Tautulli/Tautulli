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

from plexpy import version

# Identify Our Application
USER_AGENT = 'PlexPy/-' + version.PLEXPY_VERSION + ' v' + version.PLEXPY_RELEASE_VERSION + ' (' + platform.system() + \
             ' ' + platform.release() + ')'

PLATFORM = platform.system()
PLATFORM_VERSION = platform.release()
BRANCH = version.PLEXPY_VERSION
VERSION_NUMBER = version.PLEXPY_RELEASE_VERSION

# Notification Types
NOTIFY_STARTED = 1
NOTIFY_STOPPED = 2

notify_strings = {}
notify_strings[NOTIFY_STARTED] = "Playback started"
notify_strings[NOTIFY_STOPPED] = "Playback stopped"

DEFAULT_USER_THUMB = "interfaces/default/images/gravatar-default-80x80.png"
DEFAULT_POSTER_THUMB = "interfaces/default/images/poster.png"
DEFAULT_COVER_THUMB = "interfaces/default/images/cover.png"
DEFAULT_ART = "interfaces/default/images/art.png"

PLATFORM_NAME_OVERRIDES = {'Konvergo': 'Plex Media Player',
                           'Mystery 3': 'Playstation 3',
                           'Mystery 4': 'Playstation 4',
                           'Mystery 5': 'Xbox 360'}

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

SCHEDULER_LIST = ['Check GitHub for updates',
                  'Check for active sessions',
                  'Check for recently added items',
                  'Check for Plex updates',
                  'Check for Plex remote access',
                  'Refresh users list',
                  'Refresh libraries list',
                  'Refresh Plex server URLs',
                  'Refresh Plex server name',
                  'Backup PlexPy database'
                  ]