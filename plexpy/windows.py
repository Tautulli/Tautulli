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
from systray import SysTrayIcon

try:
    from shlex import quote as cmd_quote
except ImportError:
    from pipes import quote as cmd_quote

try:
    import winreg
except ImportError:
    import _winreg as winreg

import plexpy
if plexpy.PYTHON2:
    import common
    import logger
    import versioncheck
else:
    from plexpy import common
    from plexpy import logger
    from plexpy import versioncheck


class WindowsSystemTray(object):
    def __init__(self):
        self.image_dir = os.path.join(plexpy.PROG_DIR, 'data/interfaces/', plexpy.CONFIG.INTERFACE, 'images')

        if plexpy.UPDATE_AVAILABLE:
            self.icon = os.path.join(self.image_dir, 'logo-circle-update.ico')
            self.hover_text = common.PRODUCT + ' - Update Available!'
        else:
            self.icon = os.path.join(self.image_dir, 'logo-circle.ico')
            self.hover_text = common.PRODUCT

        if plexpy.CONFIG.LAUNCH_STARTUP:
            start_icon = os.path.join(self.image_dir, 'check-solid.ico')
        else:
            start_icon = None

        self.menu = [
            ['Open Tautulli', None, self.tray_open, 'default'],
            ['', None, 'separator', None],
            ['Start Tautulli at Login', start_icon, self.tray_startup, None],
            ['', None, 'separator', None],
            ['Check for Updates', None, self.tray_check_update, None],
            ['Restart', None, self.tray_restart, None]
        ]
        if not plexpy.FROZEN:
            self.menu.insert(5, ['Update', None, self.tray_update, None])

        self.tray_icon = SysTrayIcon(self.icon, self.hover_text, self.menu, on_quit=self.tray_quit)

    def start(self):
        logger.info("Launching Windows system tray icon.")
        try:
            self.tray_icon.start()
        except Exception as e:
            logger.error("Unable to launch system tray icon: %s." % e)

    def shutdown(self):
        self.tray_icon.shutdown()

    def update(self, **kwargs):
        self.tray_icon.update(**kwargs)

    def tray_open(self, tray_icon):
        plexpy.launch_browser(plexpy.CONFIG.HTTP_HOST, plexpy.HTTP_PORT, plexpy.HTTP_ROOT)

    def tray_startup(self, tray_icon):
        plexpy.CONFIG.LAUNCH_STARTUP = not plexpy.CONFIG.LAUNCH_STARTUP
        set_startup()

    def tray_check_update(self, tray_icon):
        versioncheck.check_update()

    def tray_update(self, tray_icon):
        if plexpy.UPDATE_AVAILABLE:
            plexpy.SIGNAL = 'update'
        else:
            hover_text = common.PRODUCT + ' - No Update Available'
            self.update(hover_text=hover_text)

    def tray_restart(self, tray_icon):
        plexpy.SIGNAL = 'restart'

    def tray_quit(self, tray_icon):
        plexpy.SIGNAL = 'shutdown'

    def change_tray_update_icon(self):
        if plexpy.UPDATE_AVAILABLE:
            self.icon = os.path.join(self.image_dir, 'logo-circle-update.ico')
            self.hover_text = common.PRODUCT + ' - Update Available!'
        else:
            self.icon = os.path.join(self.image_dir, 'logo-circle.ico')
            self.hover_text = common.PRODUCT + ' - No Update Available'
        self.update(icon=self.icon, hover_text=self.hover_text)

    def change_tray_startup_icon(self):
        if plexpy.CONFIG.LAUNCH_STARTUP:
            start_icon = os.path.join(self.image_dir, 'check-solid.ico')
        else:
            start_icon = None
        self.menu[2][1] = start_icon
        self.update(menu_options=self.menu)


def set_startup():
    if plexpy.WIN_SYS_TRAY_ICON:
        plexpy.WIN_SYS_TRAY_ICON.change_tray_startup_icon()

    startup_reg_path = "Software\\Microsoft\\Windows\\CurrentVersion\\Run"

    exe = sys.executable
    if plexpy.FROZEN:
        args = [exe]
    else:
        args = [exe, plexpy.FULL_PATH]

    cmd = ' '.join(cmd_quote(arg) for arg in args).replace('python.exe', 'pythonw.exe').replace("'", '"')

    if plexpy.CONFIG.LAUNCH_STARTUP:
        try:
            winreg.CreateKey(winreg.HKEY_CURRENT_USER, startup_reg_path)
            registry_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, startup_reg_path, 0, winreg.KEY_WRITE)
            winreg.SetValueEx(registry_key, common.PRODUCT, 0, winreg.REG_SZ, cmd)
            winreg.CloseKey(registry_key)
            logger.info("Added Tautulli to Windows system startup registry key.")
            return True
        except WindowsError as e:
            logger.error("Failed to create Windows system startup registry key: %s", e)
            return False

    else:
        # Check if registry value exists
        try:
            registry_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, startup_reg_path, 0, winreg.KEY_ALL_ACCESS)
            winreg.QueryValueEx(registry_key, common.PRODUCT)
            reg_value_exists = True
        except WindowsError:
            reg_value_exists = False

        if reg_value_exists:
            try:
                winreg.DeleteValue(registry_key, common.PRODUCT)
                winreg.CloseKey(registry_key)
                logger.info("Removed Tautulli from Windows system startup registry key.")
                return True
            except WindowsError as e:
                logger.error("Failed to delete Windows system startup registry key: %s", e)
                return False
