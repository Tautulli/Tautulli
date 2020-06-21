FROM tautulli/tautulli-baseimage:python3

LABEL maintainer="Tautulli"

ARG BRANCH
ARG COMMIT

ENV TAUTULLI_DOCKER=True
ENV TZ=UTC

WORKDIR /app

RUN \
  echo ${BRANCH} > /app/branch.txt && \
  echo ${COMMIT} > /app/version.txt

COPY . /app

ENTRYPOINT [ "./start.sh" ]

VOLUME /config
EXPOSE 8181
HEALTHCHECK  --start-period=90s CMD curl -ILfSs http://localhost:8181/status > /dev/null || curl -ILfkSs https://localhost:8181/status > /dev/null || exit 1
