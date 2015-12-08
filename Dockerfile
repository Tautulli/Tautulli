FROM python:2

## Maintainer info
MAINTAINER Logan Garrett <https://github.com/lngarrett>

COPY . .
CMD [ "python", "PlexPy.py"]

