FROM tautulli/tautulli-baseimage:latest

LABEL maintainer="Tautulli"

ARG VERSION
ARG BRANCH

ENV TAUTULLI_DOCKER=True
ENV TZ=UTC

WORKDIR /app

RUN \
  echo ${VERSION} > /app/version.txt && \
  echo ${BRANCH} > /app/branch.txt

COPY . /app

CMD [ "python", "Tautulli.py", "--datadir", "/config" ]

VOLUME /config /plex_logs
EXPOSE 8181
HEALTHCHECK  --start-period=90s CMD curl -ILfSs http://localhost:8181/status > /dev/null || curl -ILfkSs https://localhost:8181/status > /dev/null || exit 1
