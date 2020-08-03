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
from future.builtins import object
from future.builtins import str

from plexapi.server import PlexServer

import plexpy
if plexpy.PYTHON2:
    import logger
else:
    from plexpy import logger


class Plex(object):
    def __init__(self, url, token):
        self.plex = PlexServer(url, token)

    def get_library(self, section_id):
        return self.plex.library.sectionByID(str(section_id))

    def get_library_items(self, section_id):
        return self.get_library(str(section_id)).all()

    def get_item(self, rating_key):
        return self.plex.fetchItem(rating_key)
