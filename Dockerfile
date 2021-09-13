FROM ghcr.io/tautulli/tautulli-baseimage:python3

LABEL maintainer="Tautulli"

ARG BRANCH
ARG COMMIT

ENV TAUTULLI_DOCKER=True
ENV TZ=UTC

WORKDIR /app

RUN \
  groupadd -g 1000 tautulli && \
  useradd -u 1000 -g 1000 tautulli && \
  echo ${BRANCH} > /app/branch.txt && \
  echo ${COMMIT} > /app/version.txt

COPY . /app

VOLUME /config
RUN touch /config/DOCKER

CMD [ "python", "Tautulli.py", "--datadir", "/config" ]
ENTRYPOINT [ "./start.sh" ]

EXPOSE 8181
HEALTHCHECK --start-period=90s CMD curl -ILfSs http://localhost:8181/status > /dev/null || curl -ILfkSs https://localhost:8181/status > /dev/null || exit 1
