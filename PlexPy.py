#!/bin/sh
''''which python    >/dev/null 2>&1 && exec python    "$0" "$@" # '''
''''which python2   >/dev/null 2>&1 && exec python2   "$0" "$@" # '''
''''which python2.7 >/dev/null 2>&1 && exec python2.7 "$0" "$@" # '''
''''exec echo "Error: Python not found!" # '''

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

from Tautulli import main

# Call main() from Tautulli.py
if __name__ == "__main__":
    main()
