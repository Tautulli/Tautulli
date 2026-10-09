#!/bin/sh
# A manifest command cannot expand variables, so this wrapper sets the data directory.
# The runtime has no display socket here, so the Python webbrowser module needs BROWSER to find xdg-open.
export BROWSER=xdg-open
export PYTHONDONTWRITEBYTECODE=1
exec python3 /app/share/tautulli/Tautulli.py --datadir "$XDG_DATA_HOME" "$@"
