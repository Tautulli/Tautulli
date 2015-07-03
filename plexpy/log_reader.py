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
    clean_lines = []
    for i in log_lines:
        log_time = i.split(' [')[0]
        log_level = i.split('] ', 1)[1].split(' - ',1)[0]
        log_msg = i.split('] ', 1)[1].split(' - ',1)[1]
        full_line = [log_time, log_level, log_msg]
        clean_lines.append(full_line)

    return clean_lines

# https://stackoverflow.com/questions/136168/get-last-n-lines-of-a-file-with-python-similar-to-tail
def tail(f, window=20):
    """
    Returns the last `window` lines of file `f` as a list.
    """
    if window == 0:
        return []
    BUFSIZ = 1024
    f.seek(0, 2)
    bytes = f.tell()
    size = window + 1
    block = -1
    data = []
    while size > 0 and bytes > 0:
        if bytes - BUFSIZ > 0:
            # Seek back one whole BUFSIZ
            f.seek(block * BUFSIZ, 2)
            # read BUFFER
            data.insert(0, f.read(BUFSIZ))
        else:
            # file too small, start from begining
            f.seek(0,0)
            # only read what was not read
            data.insert(0, f.read(bytes))
        linesFound = data[0].count('\n')
        size -= linesFound
        bytes -= BUFSIZ
        block -= 1
    return ''.join(data).splitlines()[-window:]

