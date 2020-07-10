#!/usr/bin/env bash

if [[ "$TAUTULLI_DOCKER" == "True" ]]; then
    if [[ -n $PUID && -n $PGID ]]; then
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
    python_versions=("python3" "python3.8" "python3.7" "python3.6" "python" "python2" "python2.7")
    for cmd in "${python_versions[@]}"; do
        if command -v "$cmd" >/dev/null; then
            echo "Starting Tautulli with $cmd."
            if [[ "$(uname -s)" == "Darwin" ]]; then
                $cmd Tautulli.py &> /dev/null &
            else
                $cmd Tautulli.py --quiet --daemon
            fi
            exit
        fi
    done
    echo "Unable to start Tautulli. No Python interpreter was found in the following options:" "${python_versions[@]}"
fi
