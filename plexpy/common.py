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
import operator
import os
import re

from plexpy import version

# Identify Our Application
USER_AGENT = 'PlexPy/-' + version.PLEXPY_VERSION + ' (' + platform.system() + ' ' + platform.release() + ')'

# Notification Types
NOTIFY_STARTED = 1
NOTIFY_STOPPED = 2

notify_strings = {}
notify_strings[NOTIFY_STARTED] = "Playback started"
notify_strings[NOTIFY_STOPPED] = "Playback stopped"

DEFAULT_USER_THUMB = "interfaces/default/images/gravatar-default-80x80.png"
DEFAULT_POSTER_THUMB = "interfaces/default/images/poster.png"
DEFAULT_COVER_THUMB = "interfaces/default/images/cover.png"