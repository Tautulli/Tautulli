#!/usr/bin/env bash

if [[ "$TAUTULLI_DOCKER" == "True" ]]; then
    PUID=${PUID:-1000}
    PGID=${PGID:-1000}

    groupmod -o -g "$PGID" tautulli
    usermod -o -u "$PUID" tautulli

    find /config \! \( -uid $(id -u tautulli) -gid $(id -g tautulli) \) -print0 | xargs -0r chown tautulli:tautulli

    echo "Running Tautulli using user tautulli (uid=$(id -u tautulli)) and group tautulli (gid=$(id -g tautulli))"
    exec gosu tautulli "$@"
else
    python_versions=("python3.11" "python3.10" "python3.9" "python3.8" "python3" "python")
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
