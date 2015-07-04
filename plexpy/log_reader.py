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

from plexpy import helpers, logger
import re
import os
import plexpy

def get_log_tail(window=20):

    if plexpy.CONFIG.PMS_LOGS_FOLDER:
        log_file = os.path.join(plexpy.CONFIG.PMS_LOGS_FOLDER, 'Plex Media Server.log')
    else:
        return []

    try:
        logfile = open(log_file, "r")
    except IOError, e:
        logger.error('Unable to open Plex Log file. %s' % e)
        return []

    log_lines = tail(logfile, window)

    line_error = False
    clean_lines = []
    for i in log_lines:
        try:
            log_time = i.split(' [')[0]
            log_level = i.split('] ', 1)[1].split(' - ',1)[0]
            log_msg = i.split('] ', 1)[1].split(' - ',1)[1]
            full_line = [log_time, log_level, log_msg]
            clean_lines.append(full_line)
        except:
            line_error = True
            full_line = ['', '', 'Unable to parse log line.']
            clean_lines.append(full_line)

    if line_error:
        logger.error('PlexPy was unable to parse some lines of the Plex Media Server log.')

    return clean_lines

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