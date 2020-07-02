#!/usr/bin/env bash

if [[ "$TAUTULLI_DOCKER" = "True" ]]; then
    if [[ -v PUID && -v PGID ]]; then
        getent group "$PGID" 2>&1 > /dev/null || groupadd -g "$PGID" tautulli
        getent passwd "$PUID" 2>&1 > /dev/null || useradd -r -u "$PUID" -g "$PGID" tautulli

        user=$(getent passwd "$PUID" | cut -d: -f1)
        group=$(getent group "$PGID" | cut -d: -f1)
        usermod -a -G root "$user"

        chown -R "$user":"$group" /config

        echo "Running Tautulli using user $user (uid=$PUID) and group $group (gid=$PGID)"
        su "$user" -g "$group" -c "python /app/Tautulli.py --datadir /config"
    else
        python Tautulli.py --datadir /config
    fi
else
    if command -v python3 >/dev/null; then
        python3 Tautulli.py &> /dev/null &
    elif command -v python3.8 >/dev/null; then
        python3.8 Tautulli.py &> /dev/null &
    elif command -v python3.7 >/dev/null; then
        python3.7 Tautulli.py &> /dev/null &
    elif command -v python3.6 >/dev/null; then
        python3.6 Tautulli.py &> /dev/null &
    elif command -v python >/dev/null; then
        python Tautulli.py &> /dev/null &
    elif command -v python2 >/dev/null; then
        python2 Tautulli.py &> /dev/null &
    elif command -v python2.7 >/dev/null; then
        python2.7 Tautulli.py &> /dev/null &
    else
        echo "Cannot start Tautulli: python not found."
    fi
fi
