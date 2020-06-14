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
import subprocess
import sys
import plistlib

try:
    import rumps
    has_rumps = True
except ImportError:
    has_rumps = False

import plexpy
if plexpy.PYTHON2:
    import common
    import logger
    import versioncheck
else:
    from plexpy import common
    from plexpy import logger
    from plexpy import versioncheck


class MacOSSystemTray(object):
    def __init__(self):
        self.image_dir = os.path.join(plexpy.PROG_DIR, 'data/interfaces/', plexpy.CONFIG.INTERFACE, 'images')

        if plexpy.UPDATE_AVAILABLE:
            self.icon = os.path.join(self.image_dir, 'logo-circle-update.ico')
        else:
            self.icon = os.path.join(self.image_dir, 'logo-circle.ico')

        self.menu = [
            rumps.MenuItem('Open Tautulli', callback=self.tray_open),
            None,
            rumps.MenuItem('Start Tautulli at Login', callback=self.tray_startup),
            rumps.MenuItem('Open Browser when Tautulli Starts', callback=self.tray_browser),
            None,
            rumps.MenuItem('Check for Updates', callback=self.tray_check_update),
            rumps.MenuItem('Restart', callback=self.tray_restart),
            rumps.MenuItem('Quit', callback=self.tray_quit)
        ]
        if not plexpy.FROZEN:
            self.menu.insert(6, rumps.MenuItem('Update', callback=self.tray_update))
        self.menu[2].state = plexpy.CONFIG.LAUNCH_STARTUP
        self.menu[3].state = plexpy.CONFIG.LAUNCH_BROWSER

        self.tray_icon = rumps.App(common.PRODUCT, icon=self.icon, menu=self.menu, quit_button=None)

    def start(self):
        logger.info("Launching MacOS system tray icon.")
        try:
            self.tray_icon.run()
        except Exception as e:
            logger.error("Unable to launch system tray icon: %s." % e)

    def shutdown(self):
        rumps.quit_application()

    def update(self, **kwargs):
        if 'icon' in kwargs:
            self.tray_icon.icon = kwargs['icon']

    def tray_open(self, tray_icon):
        plexpy.launch_browser(plexpy.CONFIG.HTTP_HOST, plexpy.HTTP_PORT, plexpy.HTTP_ROOT)

    def tray_startup(self, tray_icon):
        plexpy.CONFIG.LAUNCH_STARTUP = not plexpy.CONFIG.LAUNCH_STARTUP
        set_startup()

    def tray_browser(self, tray_icon):
        plexpy.CONFIG.LAUNCH_BROWSER = not plexpy.CONFIG.LAUNCH_BROWSER
        set_startup()

    def tray_check_update(self, tray_icon):
        versioncheck.check_update()

    def tray_update(self, tray_icon):
        if plexpy.UPDATE_AVAILABLE:
            plexpy.SIGNAL = 'update'

    def tray_restart(self, tray_icon):
        plexpy.SIGNAL = 'restart'

    def tray_quit(self, tray_icon):
        plexpy.SIGNAL = 'shutdown'

    def change_tray_update_icon(self):
        if plexpy.UPDATE_AVAILABLE:
            self.icon = os.path.join(self.image_dir, 'logo-circle-update.ico')
        else:
            self.icon = os.path.join(self.image_dir, 'logo-circle.ico')
        self.update(icon=self.icon)

    def change_tray_icons(self):
        self.tray_icon.menu['Start Tautulli at Login'].state = plexpy.CONFIG.LAUNCH_STARTUP
        self.tray_icon.menu['Open Browser when Tautulli Starts'].state = plexpy.CONFIG.LAUNCH_BROWSER


def set_startup():
    if plexpy.MAC_SYS_TRAY_ICON:
        plexpy.MAC_SYS_TRAY_ICON.change_tray_icons()

    if plexpy.INSTALL_TYPE == 'macos':
        if plexpy.CONFIG.LAUNCH_STARTUP:
            try:
                subprocess.Popen(['osascript',
                                  '-e', 'tell application "System Events"',
                                  '-e', 'get the name of every login item',
                                  '-e', 'if not exists login item "Tautulli" then '
                                        'make login item at end with properties '
                                        '{path:"/Applications/Tautulli.app", hidden:false}',
                                  '-e', 'end tell'])
                logger.info("Added Tautulli to MacOS login items.")
                return True
            except OSError as e:
                logger.error("Failed to add Tautulli to MacOS login items: %s", e)
                return False

        else:
            try:
                subprocess.Popen(['osascript',
                                  '-e', 'tell application "System Events"',
                                  '-e', 'get the name of every login item',
                                  '-e', 'if exists login item "Tautulli" then '
                                        'delete login item "Tautulli"',
                                  '-e', 'end tell'])
                logger.info("Removed Tautulli from MacOS login items.")
                return True
            except OSError as e:
                logger.error("Failed to remove Tautulli from MacOS login items: %s", e)
                return False

    else:
        launch_agents = os.path.join(os.path.expanduser('~'), 'Library/LaunchAgents')
        plist_file = 'com.Tautulli.Tautulli.plist'
        plist_file_path = os.path.join(launch_agents, plist_file)

        exe = sys.executable
        if plexpy.FROZEN:
            args = [exe]
        else:
            args = [exe, plexpy.FULL_PATH]

        plist_dict = {
            'Label': common.PRODUCT,
            'ProgramArguments': args,
            'RunAtLoad': True
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

            logger.info("Added Tautulli to MacOS system startup launch agents.")
            return True

        else:
            try:
                if os.path.isfile(plist_file_path):
                    os.remove(plist_file_path)
                    logger.info("Removed Tautulli from MacOS system startup launch agents.")
                return True
            except OSError as e:
                logger.error("Failed to delete MacOS system startup plist file: %s", e)
                return False
