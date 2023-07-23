# -*- coding: utf-8 -*-

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

from __future__ import unicode_literals
from io import open

import os

import plexpy
if plexpy.PYTHON2:
    import helpers
    import logger
else:
    from plexpy import helpers
    from plexpy import logger


def list_plex_logs():
    logs_dir = plexpy.CONFIG.PMS_LOGS_FOLDER

    if not logs_dir or logs_dir and not os.path.exists(logs_dir):
        return []

    log_files = []
    for file in os.listdir(logs_dir):
        if file.startswith('Plex Transcoder Statistics'):
            # Plex Transcoder Statistics is an XML file
            continue
        if os.path.isfile(os.path.join(logs_dir, file)):
            name, ext = os.path.splitext(file)
            if ext == '.log' and not name[-1].isdigit():
                log_files.append(name)

    return log_files


def get_log_tail(window=20, parsed=True, log_file=''):
    if not plexpy.CONFIG.PMS_LOGS_FOLDER:
        return []

    log_file = (log_file or 'Plex Media Server') + '.log'
    log_file = os.path.join(plexpy.CONFIG.PMS_LOGS_FOLDER, log_file)

    try:
        logfile = open(log_file, 'r', encoding='utf-8')
    except IOError as e:
        logger.error('Unable to open Plex Log file. %s' % e)
        return []

    log_lines = tail(logfile, window)

    if parsed:
        line_error = False
        clean_lines = []
        for i in log_lines:
            if not i.strip():
                continue
            try:
                log_time = i.split(' [')[0]
                log_level = i.split('] ', 1)[1].split(' - ', 1)[0]
                log_msg = i.split('] ', 1)[1].split(' - ', 1)[1]
                full_line = [log_time, log_level, log_msg]
                clean_lines.append(full_line)
            except:
                line_error = True
                full_line = ['', '', 'Unable to parse log line.']
                clean_lines.append(full_line)

        if line_error:
            logger.error('Tautulli was unable to parse some lines of the Plex Media Server log.')

        return clean_lines
    else:
        raw_lines = []
        for i in log_lines:
            raw_lines.append(helpers.latinToAscii(i))

        return raw_lines


# http://stackoverflow.com/a/13790289/2405162
def tail(f, lines=1, _buffer=4098):
    """Tail a file and get X lines from the end"""
    # place holder for the lines found
    lines_found = []

    # block counter will be multiplied by buffer
    # to get the block size from the end
    block_counter = -1

    # loop until we find X lines
    while len(lines_found) < lines:
        try:
            f.seek(block_counter * _buffer, os.SEEK_END)
        except IOError:  # either file is too small, or too many lines requested
            f.seek(0)
            lines_found = f.readlines()
            break

        lines_found = f.readlines()

        # we found enough lines, get out
        if len(lines_found) > lines:
            break

        # decrement the block counter to get the
        # next X bytes
        block_counter -= 1

    return lines_found[-lines:]