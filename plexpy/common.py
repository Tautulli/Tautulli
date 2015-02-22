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

#Identify Our Application
USER_AGENT = 'PlexPy/-' + version.PLEXPY_VERSION + ' (' + platform.system() + ' ' + platform.release() + ')'

### Notification Types
NOTIFY_SNATCH = 1
NOTIFY_DOWNLOAD = 2

notifyStrings = {}
notifyStrings[NOTIFY_SNATCH] = "Started Download"
notifyStrings[NOTIFY_DOWNLOAD] = "Download Finished"

### Release statuses
UNKNOWN = -1 # should never happen
UNAIRED = 1 # releases that haven't dropped yet
SNATCHED = 2 # qualified with quality
WANTED = 3 # releases we don't have but want to get
DOWNLOADED = 4 # qualified with quality
SKIPPED = 5 # releases we don't want
ARCHIVED = 6 # releases that you don't have locally (counts toward download completion stats)
IGNORED = 7 # releases that you don't want included in your download stats
SNATCHED_PROPER = 9 # qualified with quality
