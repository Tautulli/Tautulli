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
import psutil
import requests
import shutil
import subprocess
import sys
import tempfile


SCRIPT_PATH = os.path.dirname(os.path.abspath(__file__))
CREATE_NO_WINDOW = 0x08000000
REPO_URL = 'https://api.github.com/repos/Tautulli/Tautulli'

LOGFILE = 'updater.log'
LOGPATH = os.path.join(SCRIPT_PATH, LOGFILE)
MAX_SIZE = 1000000  # 1MB
MAX_FILES = 1


def init_logger():
    log = logging.getLogger('updater')
    log.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)-7s :: %(threadName)s : Tautulli Updater :: %(message)s',
        '%Y-%m-%d %H:%M:%S')
    file_handler = handlers.RotatingFileHandler(
        LOGPATH, maxBytes=MAX_SIZE, backupCount=MAX_FILES, encoding='utf-8')
    file_handler.setFormatter(file_formatter)
    log.addHandler(file_handler)
    return log


def read_file(file_path):
    try:
        with open(file_path, 'r') as f:
            return f.read().strip(' \n\r')
    except Exception as e:
        logger.error('Read file error: %s', e)
        raise Exception(1)


def request_json(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error('Request error: %s', e)
        raise Exception(2)


def kill_and_get_processes(process_name):
    processes = []
    for process in psutil.process_iter():
        if process.name() == process_name:
            processes.append(process.cmdline())
            logger.info('Sending SIGTERM to %s (PID=%d)', process.name(), process.pid)
            process.terminate()
    return processes


def update_tautulli():
    logger.info('Starting Tautulli update check')

    branch = read_file(os.path.join(SCRIPT_PATH, 'branch.txt'))
    logger.info('Branch: %s', branch)

    current_version = read_file(os.path.join(SCRIPT_PATH, 'version.txt'))
    logger.info('Current version: %s', current_version)

    logger.info('Retrieving latest version from GitHub')
    commits = request_json('{}/commits/{}'.format(REPO_URL, branch))
    latest_version = commits['sha']
    logger.info('Latest version: %s', latest_version)

    if current_version == latest_version:
        logger.info('Tautulli is already up to date')
        return 0

    logger.info('Comparing version on GitHub')
    compare = request_json('{}/compare/{}...{}'.format(REPO_URL, latest_version, current_version))
    commits_behind = compare['behind_by']
    logger.info('Commits behind: %s', commits_behind)

    if commits_behind <= 0:
        logger.info('Tautulli is already up to date')
        return 0

    logger.info('Retrieving releases on GitHub')
    releases = request_json('{}/releases'.format(REPO_URL))

    if branch == 'master':
        release = next((r for r in releases if not r['prerelease']), releases[0])
    else:
        release = next((r for r in releases), releases[0])

    version = release['tag_name']
    logger.info('Release: %s', version)

    win_exe = 'application/vnd.microsoft.portable-executable'
    asset = next((a for a in release['assets'] if a['content_type'] == win_exe), None)
    download_url = asset['browser_download_url']
    download_file = asset['name']

    file_path = os.path.join(tempfile.gettempdir(), download_file)
    logger.info('Downloading installer to temporary directory: %s', file_path)
    try:
        with requests.get(download_url, stream=True) as r:
            with open(file_path, 'wb') as f:
                shutil.copyfileobj(r.raw, f)
    except Exception as e:
        logger.error('Failed to download %s: %s', download_file, e)
        return 2

    logger.info('Stopping Tautulli processes')
    try:
        processes = kill_and_get_processes('Tautulli.exe')
    except Exception as e:
        logger.error('Failed to stop Tautulli: %s', e)
        return 1

    logger.info('Running %s', download_file)
    try:
        subprocess.call([file_path, '/S', '/NORUN'], creationflags=CREATE_NO_WINDOW)
        status = 0
    except Exception as e:
        logger.exception('Failed to install Tautulli: %s', e)
        status = -1

    if status == 0:
        logger.info('Tautulli updated to %s', version)

    logger.info('Restarting Tautulli processes')
    for process in processes:
        logger.info('Starting process: %s', process)
        subprocess.Popen(process, creationflags=CREATE_NO_WINDOW)

    return status


if __name__ == '__main__':
    logger = init_logger()

    try:
        status_code = update_tautulli()
    except Exception as exc:
        status_code = exc
    logger.debug('Update function returned status code %s', status_code)

    sys.exit(status_code)
