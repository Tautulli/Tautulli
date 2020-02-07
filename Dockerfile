FROM python:2.7.17-slim

LABEL maintainer="TheMeanCanEHdian"

ARG VERSION

ENV TAUTULLI_DOCKER=True
ENV TZ=UTC

WORKDIR /app

RUN \
apt-get -q -y update --no-install-recommends && \
apt-get install -q -y --no-install-recommends \
  curl && \
rm -rf /var/lib/apt/lists/* && \
pip install --no-cache-dir --upgrade pip && \
pip install --no-cache-dir --upgrade \
  plexapi \
  pycryptodomex \
  pyopenssl && \
echo ${VERSION} > /app/version.txt

COPY . /app

CMD [ "python", "Tautulli.py", "--datadir", "/config" ]

VOLUME /config /plex_logs
EXPOSE 8181
HEALTHCHECK  --start-period=90s CMD curl -ILfSs http://localhost:8181/status > /dev/null || curl -ILfkSs https://localhost:8181/status > /dev/null || exit 1
