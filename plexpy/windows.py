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
import shlex
import sys
import winreg

import plexpy
if plexpy.PYTHON2:
    import common
    import logger
    import versioncheck
else:
    from plexpy import common
    from plexpy import logger
    from plexpy import versioncheck


def win_system_tray():
    from systray import SysTrayIcon

    def tray_open(sysTrayIcon):
        plexpy.launch_browser(plexpy.CONFIG.HTTP_HOST, plexpy.HTTP_PORT, plexpy.HTTP_ROOT)

    def tray_startup(sysTrayIcon):
        plexpy.CONFIG.LAUNCH_STARTUP = not plexpy.CONFIG.LAUNCH_STARTUP
        if plexpy.CONFIG.LAUNCH_STARTUP:
            start_icon = os.path.join(image_dir, 'check-solid.ico')
        else:
            start_icon = None
        menu_options[2][1] = start_icon
        plexpy.WIN_SYS_TRAY_ICON.update(menu_options=menu_options)

    def tray_check_update(sysTrayIcon):
        versioncheck.check_update()

    def tray_update(sysTrayIcon):
        if plexpy.UPDATE_AVAILABLE:
            plexpy.SIGNAL = 'update'
        else:
            hover_text = common.PRODUCT + ' - No Update Available'
            plexpy.WIN_SYS_TRAY_ICON.update(hover_text=hover_text)

    def tray_restart(sysTrayIcon):
        plexpy.SIGNAL = 'restart'

    def tray_quit(sysTrayIcon):
        plexpy.SIGNAL = 'shutdown'

    image_dir = os.path.join(plexpy.PROG_DIR, 'data/interfaces/', plexpy.CONFIG.INTERFACE, 'images')

    if plexpy.UPDATE_AVAILABLE:
        icon = os.path.join(image_dir, 'logo-circle-update.ico')
        hover_text = common.PRODUCT + ' - Update Available!'
    else:
        icon = os.path.join(image_dir, 'logo-circle.ico')
        hover_text = common.PRODUCT

    if plexpy.CONFIG.LAUNCH_STARTUP:
        start_icon = os.path.join(image_dir, 'check-solid.ico')
    else:
        start_icon = None

    menu_options = [
        ['Open Tautulli', None, tray_open, 'default'],
        ['', None, 'separator', None],
        ['Start Tautulli at Login', start_icon, tray_startup, None],
        ['', None, 'separator', None],
        ['Check for Updates', None, tray_check_update, None],
        ['Update', None, tray_update, None],
        ['Restart', None, tray_restart, None]
    ]

    logger.info("Launching system tray icon.")

    try:
        plexpy.WIN_SYS_TRAY_ICON = SysTrayIcon(icon, hover_text, menu_options, on_quit=tray_quit)
        plexpy.WIN_SYS_TRAY_ICON.start()
    except Exception as e:
        logger.error("Unable to launch system tray icon: %s." % e)
        plexpy.WIN_SYS_TRAY_ICON = None


def set_startup():
    startup_reg_path = "Software\\Microsoft\\Windows\\CurrentVersion\\Run"

    exe = sys.executable
    if plexpy.FROZEN:
        args = [exe]
    else:
        args = [exe, plexpy.FULL_PATH]

    args += ['--nolaunch']

    cmd = ' '.join(shlex.quote(arg) for arg in args).replace('python.exe', 'pythonw.exe').replace("'", '"')

    if plexpy.CONFIG.LAUNCH_STARTUP:
        try:
            winreg.CreateKey(winreg.HKEY_CURRENT_USER, startup_reg_path)
            registry_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, startup_reg_path, 0, winreg.KEY_WRITE)
            winreg.SetValueEx(registry_key, common.PRODUCT, 0, winreg.REG_SZ, cmd)
            winreg.CloseKey(registry_key)
            return True
        except WindowsError:
            return False

    else:
        try:
            registry_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, startup_reg_path, 0, winreg.KEY_ALL_ACCESS)
            winreg.DeleteValue(registry_key, common.PRODUCT)
            winreg.CloseKey(registry_key)
            return True
        except WindowsError:
            return False
