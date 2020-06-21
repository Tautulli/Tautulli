#!/usr/bin/env bash

if [[ "$TAUTULLI_DOCKER" = "True" ]]; then
    PUID=${PUID:-911}
    PGID=${PGID:-911}
    getent group "$PGID" 2>&1 > /dev/null || groupadd -g "$PGID" tautulli
    getent passwd "$PUID" 2>&1 > /dev/null || useradd -r -u "$PUID" -g "$PGID" tautulli
    chown -f -R "$PUID":"$PGID" /config
    python Tautulli.py --datadir /config
else
    python Tautulli.py &> /dev/null &
fi
