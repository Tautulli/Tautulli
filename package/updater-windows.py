# -*- coding: utf-8 -*-

#  This file is part of Tautulli.
#
#  Tautulli is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  Tautulli is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with Tautulli.  If not, see <http://www.gnu.org/licenses/>.

from logging import handlers
import logging
import os
import requests
import shutil
import subprocess
import tempfile


SCRIPT_PATH = os.path.dirname(os.path.abspath(__file__))
CREATE_NO_WINDOW = 0x08000000
REPO_URL = 'https://api.github.com/repos/Tautulli/Tautulli'

LOGFILE = 'updater.log'
LOGPATH = os.path.join(SCRIPT_PATH, LOGFILE)
MAX_SIZE = 5000000
MAX_FILES = 1

logger = logging.getLogger('updater')
logger.setLevel(logging.DEBUG)
file_formatter = logging.Formatter(
    '%(asctime)s - %(levelname)-7s :: %(threadName)s : Tautulli Updater :: %(message)s',
    '%Y-%m-%d %H:%M:%S')
file_handler = handlers.RotatingFileHandler(
    LOGPATH, maxBytes=MAX_SIZE, backupCount=MAX_FILES, encoding='utf-8')
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)


def kill_if_exists(process_name):
    output = subprocess.check_output(
        ['TASKLIST', '/FI', 'IMAGENAME eq {}'.format(process_name)],
        creationflags=CREATE_NO_WINDOW).decode()
    output = output.strip().split('\n')[-1]
    if output.lower().startswith(process_name.lower()):
        return subprocess.check_call(
            ['TASKKILL', '/IM', process_name],
            creationflags=CREATE_NO_WINDOW)
    return 0


def update_tautulli():
    logger.info('Starting Tautulli update check')

    with open(os.path.join(SCRIPT_PATH, 'branch.txt'), 'r') as f:
        branch = f.read()
    logger.info('Branch: %s', branch)

    with open(os.path.join(SCRIPT_PATH, 'version.txt'), 'r') as f:
        current_version = f.read()
    logger.info('Current version: %s', current_version)

    logger.info('Retrieving latest version from GitHub')
    try:
        response = requests.get('{}/commits/{}'.format(REPO_URL, branch))
        response.raise_for_status()
    except Exception as e:
        logger.error('Request error: %s', e)
        return 2

    try:
        commits = response.json()
        latest_version = commits['sha']
    except Exception as e:
        logger.error('Failed to retrieve latest version: %s', e)
        return 1
    logger.info('Latest version: %s', latest_version)

    if current_version == latest_version:
        logger.info('Tautulli is already up to date')
        return 0

    logger.info('Comparing version on GitHub')
    try:
        response = requests.get('{}/compare/{}...{}'.format(REPO_URL, latest_version, current_version))
        response.raise_for_status()
    except Exception as e:
        logger.error('Request error: %s', e)
        return 2

    try:
        compare = response.json()
        commits_behind = compare['behind_by']
    except Exception as e:
        logger.error('Failed to compare commits: %s', e)
        return 1
    logger.info('Commits behind: %s', commits_behind)

    if commits_behind > 0:
        logger.info('Retrieving releases on GitHub')
        try:
            response = requests.get('{}/releases'.format(REPO_URL))
            response.raise_for_status()
        except Exception as e:
            logger.error('Request error: %s', e)
            return 2

        try:
            releases = response.json()

            if branch == 'master':
                release = next((r for r in releases if not r['prerelease']), releases[0])
            else:
                release = next((r for r in releases), releases[0])

            version = release['tag_name']
            asset = next((a for a in release['assets'] if a['content_type'] == 'application/vnd.microsoft.portable-executable'), None)
            download_url = asset['browser_download_url']
            download_file = asset['name']
        except Exception as e:
            logger.error('Failed to retrieve releases: %s', e)
            return 1
        logger.info('Release: %s', version)

        file_path = os.path.join(tempfile.gettempdir(), download_file)
        logger.info('Downloading installer to temporary directory: %s', file_path)
        with requests.get(download_url, stream=True) as r:
            with open(file_path, 'wb') as f:
                shutil.copyfileobj(r.raw, f)

        logger.info('Stopping Tautulli')
        try:
            killed = kill_if_exists('Tautulli.exe')
        except Exception as e:
            logger.error('Failed to stop Tautulli: %s', e)
            return 1

        if killed != 0:
            logger.error('Failed to stop Tautulli')
            return 1

        logger.info('Running %s', download_file)
        try:
            subprocess.call(
                [file_path, '/S'],
                creationflags=CREATE_NO_WINDOW)
        except Exception as e:
            logger.exception('Failed to install Tautulli: %s', e)
            return -1

        logger.info('Tautulli updated to %s', version)

    return 0


if __name__ == '__main__':
    status = update_tautulli()
    logger.debug('Update function returned %s', status)
