#!/usr/bin/env bash

if [[ "$TAUTULLI_DOCKER" = "True" ]]; then
    PUID=${PUID:-1000}
    PGID=${PGID:-1000}
    getent group tautulli 2>&1 > /dev/null || groupadd -g "$PGID" tautulli
    getent passwd tautulli 2>&1 > /dev/null || useradd -r -u "$PUID" -g tautulli tautulli
    chown -f -R tautulli:tautulli /config
    python Tautulli.py --datadir /config
else
    python Tautulli.py &> /dev/null &
fi
