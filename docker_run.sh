#!/bin/bash
docker rm -f plexpy
docker pull lngarrett/plexpy:latest
docker run \
  --name="plexpy" \
  --publish=8181:8181 \
  --restart="always" \
  --detach=true \
  lngarrett/plexpy
