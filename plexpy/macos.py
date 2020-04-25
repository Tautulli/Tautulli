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

import os
import sys
import plistlib

import plexpy
if plexpy.PYTHON2:
    import common
    import logger
else:
    from plexpy import common
    from plexpy import logger


def set_startup():
    launch_agents = os.path.join(os.path.expanduser('~'), 'Library/LaunchAgents')
    plist_file = 'com.Tautulli.Tautulli.plist'
    plist_file_path = os.path.join(launch_agents, plist_file)

    exe = sys.executable
    if plexpy.FROZEN:
        args = [exe]
    else:
        args = [exe, plexpy.FULL_PATH]

    args += ['--nolaunch']

    plist_dict = {
        'Label': common.PRODUCT,
        'ProgramArguments': args,
        'RunAtLoad': True,
        'KeepAlive': True
    }

    if plexpy.CONFIG.LAUNCH_STARTUP:
        if not os.path.exists(launch_agents):
            try:
                os.makedirs(launch_agents)
            except OSError:
                return False

            with open(plist_file_path, 'wb') as f:
                try:
                    plistlib.dump(plist_dict, f)
                except AttributeError:
                    plistlib.writePlist(plist_dict, f)
                except OSError as e:
                    logger.error("Failed to create MacOS system startup plist file: %s", e)
                    return False

            return True

    else:
        try:
            if os.path.isfile(plist_file_path):
                os.remove(plist_file_path)
            return True
        except OSError as e:
            logger.error("Failed to delete MacOS system startup plist file: %s", e)
            return False
