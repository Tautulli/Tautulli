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

from __future__ import division
from __future__ import unicode_literals
from future.builtins import next
from future.builtins import str

import json
import os
import platform
import re
import subprocess
import tarfile

import plexpy
if plexpy.PYTHON2:
    import common
    import helpers
    import logger
    import request
else:
    from plexpy import common
    from plexpy import helpers
    from plexpy import logger
    from plexpy import request


def runGit(args):

    if plexpy.CONFIG.GIT_PATH:
        git_locations = ['"' + plexpy.CONFIG.GIT_PATH + '"']
    else:
        git_locations = ['git']

    if platform.system().lower() == 'darwin':
        git_locations.append('/usr/local/git/bin/git')

    output = err = None

    for cur_git in git_locations:
        cmd = cur_git + ' ' + args

        try:
            logger.debug('Trying to execute: "' + cmd + '" with shell in ' + plexpy.PROG_DIR)
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True, cwd=plexpy.PROG_DIR)
            output, err = p.communicate()
            output = output.strip().decode()

            logger.debug('Git output: ' + output)
        except OSError:
            logger.debug('Command failed: %s', cmd)
            continue

        if 'not found' in output or "not recognized as an internal or external command" in output:
            logger.debug('Unable to find git with command ' + cmd)
            output = None
        elif 'fatal:' in output or err:
            logger.error('Git returned bad info. Are you sure this is a git installation?')
            output = None
        elif output:
            break

    return output, err


def get_version():

    if plexpy.FROZEN and common.PLATFORM == 'Windows':
        plexpy.INSTALL_TYPE = 'windows'
        current_version, current_branch = get_version_from_file()
        return current_version, 'origin', current_branch

    elif plexpy.FROZEN and common.PLATFORM == 'Darwin':
        plexpy.INSTALL_TYPE = 'macos'
        current_version, current_branch = get_version_from_file()
        return current_version, 'origin', current_branch

    elif os.path.isdir(os.path.join(plexpy.PROG_DIR, '.git')):
        plexpy.INSTALL_TYPE = 'git'
        output, err = runGit('rev-parse HEAD')

        if not output:
            logger.error('Could not find latest installed version.')
            cur_commit_hash = None
        else:
            cur_commit_hash = str(output)

        if not re.match('^[a-z0-9]+$', cur_commit_hash):
            logger.error('Output does not look like a hash, not using it.')
            cur_commit_hash = None

        if plexpy.CONFIG.DO_NOT_OVERRIDE_GIT_BRANCH and plexpy.CONFIG.GIT_BRANCH:
            remote_name = None
            branch_name = plexpy.CONFIG.GIT_BRANCH

        else:
            remote_branch, err = runGit('rev-parse --abbrev-ref --symbolic-full-name @{u}')
            remote_branch = remote_branch.rsplit('/', 1) if remote_branch else []
            if len(remote_branch) == 2:
                remote_name, branch_name = remote_branch
            else:
                remote_name = branch_name = None

            if not remote_name and plexpy.CONFIG.GIT_REMOTE:
                logger.error('Could not retrieve remote name from git. Falling back to %s.' % plexpy.CONFIG.GIT_REMOTE)
                remote_name = plexpy.CONFIG.GIT_REMOTE
            if not remote_name:
                logger.error('Could not retrieve remote name from git. Defaulting to origin.')
                branch_name = 'origin'

            if not branch_name and plexpy.CONFIG.GIT_BRANCH:
                logger.error('Could not retrieve branch name from git. Falling back to %s.' % plexpy.CONFIG.GIT_BRANCH)
                branch_name = plexpy.CONFIG.GIT_BRANCH
            if not branch_name:
                logger.error('Could not retrieve branch name from git. Defaulting to master.')
                branch_name = 'master'

        return cur_commit_hash, remote_name, branch_name

    else:
        if plexpy.DOCKER:
            plexpy.INSTALL_TYPE = 'docker'
        elif plexpy.SNAP:
            plexpy.INSTALL_TYPE = 'snap'
        else:
            plexpy.INSTALL_TYPE = 'source'

        current_version, current_branch = get_version_from_file()
        return current_version, 'origin', current_branch


def get_version_from_file():
    version_file = os.path.join(plexpy.PROG_DIR, 'version.txt')
    branch_file = os.path.join(plexpy.PROG_DIR, 'branch.txt')

    if os.path.isfile(version_file):
        with open(version_file, 'r') as f:
            current_version = f.read().strip(' \n\r')
    else:
        current_version = None

    if os.path.isfile(branch_file):
        with open(branch_file, 'r') as f:
            current_branch = f.read().strip(' \n\r')
    else:
        current_branch = common.BRANCH

    return current_version, current_branch


def check_update(scheduler=False, notify=False, use_cache=False):
    check_github(scheduler=scheduler, notify=notify, use_cache=use_cache)

    if not plexpy.CURRENT_VERSION:
        plexpy.UPDATE_AVAILABLE = None
    elif plexpy.COMMITS_BEHIND > 0 and \
            (plexpy.common.BRANCH in ('master', 'beta') or plexpy.SNAP or plexpy.FROZEN) and \
            plexpy.common.RELEASE != plexpy.LATEST_RELEASE:
        plexpy.UPDATE_AVAILABLE = 'release'
    elif plexpy.COMMITS_BEHIND > 0 and \
            not plexpy.SNAP and not plexpy.FROZEN and \
            plexpy.CURRENT_VERSION != plexpy.LATEST_VERSION:
        plexpy.UPDATE_AVAILABLE = 'commit'
    else:
        plexpy.UPDATE_AVAILABLE = False

    if plexpy.WIN_SYS_TRAY_ICON:
        plexpy.WIN_SYS_TRAY_ICON.change_tray_update_icon()
    elif plexpy.MAC_SYS_TRAY_ICON:
        plexpy.MAC_SYS_TRAY_ICON.change_tray_update_icon()


def check_github(scheduler=False, notify=False, use_cache=False):
    plexpy.COMMITS_BEHIND = 0

    if plexpy.CONFIG.GIT_TOKEN:
        headers = {'Authorization': 'token {}'.format(plexpy.CONFIG.GIT_TOKEN)}
    else:
        headers = {}

    version = github_cache('version', use_cache=use_cache)
    if not version:
        # Get the latest version available from github
        logger.info('Retrieving latest version information from GitHub')
        url = 'https://api.github.com/repos/%s/%s/commits/%s' % (plexpy.CONFIG.GIT_USER,
                                                                 plexpy.CONFIG.GIT_REPO,
                                                                 plexpy.CONFIG.GIT_BRANCH)
        version = request.request_json(url, headers=headers, timeout=20,
                                       validator=lambda x: type(x) == dict)
        github_cache('version', github_data=version)

    if version is None:
        logger.warn('Could not get the latest version from GitHub. Are you running a local development version?')
        return plexpy.CURRENT_VERSION

    plexpy.LATEST_VERSION = version['sha']
    logger.debug("Latest version is %s", plexpy.LATEST_VERSION)

    # See how many commits behind we are
    if not plexpy.CURRENT_VERSION:
        logger.info('You are running an unknown version of Tautulli. Run the updater to identify your version')
        return plexpy.LATEST_VERSION

    if plexpy.LATEST_VERSION == plexpy.CURRENT_VERSION:
        logger.info('Tautulli is up to date')
        return plexpy.LATEST_VERSION

    commits = github_cache('commits', use_cache=use_cache)
    if not commits:
        logger.info('Comparing currently installed version with latest GitHub version')
        # Need to compare CURRENT << LATEST to get a list of commits
        url = 'https://api.github.com/repos/%s/%s/compare/%s...%s' % (plexpy.CONFIG.GIT_USER,
                                                                      plexpy.CONFIG.GIT_REPO,
                                                                      plexpy.CURRENT_VERSION,
                                                                      plexpy.LATEST_VERSION)
        commits = request.request_json(url, headers=headers, timeout=20, whitelist_status_code=404,
                                       validator=lambda x: type(x) == dict)
        github_cache('commits', github_data=commits)

    if commits is None:
        logger.warn('Could not get commits behind from GitHub.')
        return plexpy.LATEST_VERSION

    try:
        ahead_by = int(commits['ahead_by'])
        logger.debug("In total, %d commits behind", ahead_by)

        # Do not count [skip ci] commits for Docker or Snap on the nightly branch
        if (plexpy.DOCKER or plexpy.SNAP) and plexpy.CONFIG.GIT_BRANCH == 'nightly':
            for commit in reversed(commits['commits']):
                if '[skip ci]' not in commit['commit']['message']:
                    plexpy.LATEST_VERSION = commit['sha']
                    break
                ahead_by -= 1
            install = 'Docker container' if plexpy.DOCKER else 'Snap package'
            logger.debug("%s %d commits behind", install, ahead_by)

        plexpy.COMMITS_BEHIND = ahead_by
    except KeyError:
        logger.info('Cannot compare versions. Are you running a local development version?')
        plexpy.COMMITS_BEHIND = 0

    if plexpy.COMMITS_BEHIND > 0:
        logger.info('New version is available. You are %s commits behind' % plexpy.COMMITS_BEHIND)

        releases = github_cache('releases', use_cache=use_cache)
        if not releases:
            url = 'https://api.github.com/repos/%s/%s/releases' % (plexpy.CONFIG.GIT_USER,
                                                                   plexpy.CONFIG.GIT_REPO)
            releases = request.request_json(url, timeout=20, whitelist_status_code=404,
                                            validator=lambda x: type(x) == list)
            github_cache('releases', github_data=releases)

        if releases is None:
            logger.warn('Could not get releases from GitHub.')
            return plexpy.LATEST_VERSION

        if plexpy.CONFIG.GIT_BRANCH == 'master':
            release = next((r for r in releases if not r['prerelease']), releases[0])
        elif plexpy.CONFIG.GIT_BRANCH == 'beta':
            release = next((r for r in releases if not r['tag_name'].endswith('-nightly')), releases[0])
        elif plexpy.CONFIG.GIT_BRANCH == 'nightly':
            release = next((r for r in releases), releases[0])
        else:
            release = releases[0]

        plexpy.LATEST_RELEASE = release['tag_name']

        if plexpy.CONFIG.GIT_BRANCH in ('master', 'beta') and release['target_commitish'] == plexpy.CURRENT_VERSION:
            logger.info('Tautulli is up to date')
            return plexpy.CURRENT_VERSION

        if notify:
            plexpy.NOTIFY_QUEUE.put({'notify_action': 'on_plexpyupdate',
                                     'plexpy_download_info': release,
                                     'plexpy_update_commit': plexpy.LATEST_VERSION,
                                     'plexpy_update_behind': plexpy.COMMITS_BEHIND})

        if plexpy.PYTHON2:
            logger.warn('Tautulli is running using Python 2. Unable to run automatic update.')

        elif scheduler and plexpy.CONFIG.PLEXPY_AUTO_UPDATE and \
                not plexpy.DOCKER and not plexpy.SNAP and not plexpy.FROZEN:
            logger.info('Running automatic update.')
            plexpy.shutdown(restart=True, update=True)

    elif plexpy.COMMITS_BEHIND == 0:
        logger.info('Tautulli is up to date')

    return plexpy.LATEST_VERSION


def update():
    if plexpy.PYTHON2:
        logger.warn('Tautulli is running using Python 2. Unable to update.')
        return

    if not plexpy.UPDATE_AVAILABLE:
        return

    if plexpy.INSTALL_TYPE in ('docker', 'snap', 'windows', 'macos'):
        return

    elif plexpy.INSTALL_TYPE == 'git':
        output, err = runGit('pull --ff-only {} {}'.format(plexpy.CONFIG.GIT_REMOTE,
                                                           plexpy.CONFIG.GIT_BRANCH))

        if not output:
            logger.error('Unable to download latest version')
            return

        for line in output.split('\n'):
            if 'Already up-to-date.' in line or 'Already up to date.' in line:
                logger.info('No update available, not updating')
            elif line.endswith(('Aborting', 'Aborting.')):
                logger.error('Unable to update from git: ' + line)

    elif plexpy.INSTALL_TYPE == 'source':
        tar_download_url = 'https://github.com/{}/{}/tarball/{}'.format(plexpy.CONFIG.GIT_USER,
                                                                        plexpy.CONFIG.GIT_REPO,
                                                                        plexpy.CONFIG.GIT_BRANCH)
        update_dir = os.path.join(plexpy.DATA_DIR, 'update')
        version_path = os.path.join(plexpy.PROG_DIR, 'version.txt')

        logger.info('Downloading update from: ' + tar_download_url)
        data = request.request_content(tar_download_url)

        if not data:
            logger.error("Unable to retrieve new version from '%s', can't update", tar_download_url)
            return

        download_name = plexpy.CONFIG.GIT_BRANCH + '-github'
        tar_download_path = os.path.join(plexpy.DATA_DIR, download_name)

        # Save tar to disk
        with open(tar_download_path, 'wb') as f:
            f.write(data)

        # Extract the tar to update folder
        logger.info('Extracting file: ' + tar_download_path)
        tar = tarfile.open(tar_download_path)
        tar.extractall(update_dir)
        tar.close()

        # Delete the tar.gz
        logger.info('Deleting file: ' + tar_download_path)
        os.remove(tar_download_path)

        # Find update dir name
        update_dir_contents = [x for x in os.listdir(update_dir) if os.path.isdir(os.path.join(update_dir, x))]
        if len(update_dir_contents) != 1:
            logger.error("Invalid update data, update failed: " + str(update_dir_contents))
            return
        content_dir = os.path.join(update_dir, update_dir_contents[0])

        # walk temp folder and move files to main folder
        for dirname, dirnames, filenames in os.walk(content_dir):
            dirname = dirname[len(content_dir) + 1:]
            for curfile in filenames:
                old_path = os.path.join(content_dir, dirname, curfile)
                new_path = os.path.join(plexpy.PROG_DIR, dirname, curfile)

                if os.path.isfile(new_path):
                    os.remove(new_path)
                os.renames(old_path, new_path)

        # Update version.txt
        try:
            with open(version_path, 'w') as f:
                f.write(str(plexpy.LATEST_VERSION))
        except IOError as e:
            logger.error(
                "Unable to write current version to version.txt, update not complete: %s",
                e
            )
            return


def reset_git_install():
    if plexpy.INSTALL_TYPE == 'git':
        logger.info('Attempting to reset git install to "{}/{}/{}"'.format(plexpy.CONFIG.GIT_REMOTE,
                                                                           plexpy.CONFIG.GIT_BRANCH,
                                                                           common.RELEASE))

        output, err = runGit('remote set-url {} https://github.com/{}/{}.git'.format(plexpy.CONFIG.GIT_REMOTE,
                                                                                     plexpy.CONFIG.GIT_USER,
                                                                                     plexpy.CONFIG.GIT_REPO))
        output, err = runGit('fetch {}'.format(plexpy.CONFIG.GIT_REMOTE))
        output, err = runGit('checkout {}'.format(plexpy.CONFIG.GIT_BRANCH))
        output, err = runGit('branch -u {}/{}'.format(plexpy.CONFIG.GIT_REMOTE,
                                                      plexpy.CONFIG.GIT_BRANCH))
        output, err = runGit('reset --hard {}'.format(common.RELEASE))

        if not output:
            logger.error('Unable to reset Tautulli installation.')
            return False

        for line in output.split('\n'):
            if 'Already up-to-date.' in line or 'Already up to date.' in line:
                logger.info('Tautulli installation reset successfully.')
                return True
            elif line.endswith(('Aborting', 'Aborting.')):
                logger.error('Unable to reset Tautulli installation: ' + line)
                return False


def checkout_git_branch():
    if plexpy.INSTALL_TYPE == 'git':
        logger.info('Attempting to checkout git branch "{}/{}"'.format(plexpy.CONFIG.GIT_REMOTE,
                                                                       plexpy.CONFIG.GIT_BRANCH))

        output, err = runGit('fetch {}'.format(plexpy.CONFIG.GIT_REMOTE))
        output, err = runGit('checkout {}'.format(plexpy.CONFIG.GIT_BRANCH))

        if not output:
            logger.error('Unable to change git branch.')
            return

        for line in output.split('\n'):
            if line.endswith(('Aborting', 'Aborting.')):
                logger.error('Unable to checkout from git: ' + line)
                return

        output, err = runGit('pull {} {}'.format(plexpy.CONFIG.GIT_REMOTE,
                                                 plexpy.CONFIG.GIT_BRANCH))


def github_cache(cache, github_data=None, use_cache=True):
    timestamp = helpers.timestamp()
    cache_filepath = os.path.join(plexpy.CONFIG.CACHE_DIR, 'github_{}.json'.format(cache))

    if github_data:
        cache_data = {'github_data': github_data,
                      '_cache_time': timestamp,
                      '_release_version': common.RELEASE}
        try:
            with open(cache_filepath, 'w', encoding='utf-8') as cache_file:
                json.dump(cache_data, cache_file)
        except:
            pass
    else:
        if not use_cache:
            return
        try:
            with open(cache_filepath, 'r', encoding='utf-8') as cache_file:
                cache_data = json.load(cache_file)
            if (
                timestamp - cache_data['_cache_time'] < plexpy.CONFIG.CHECK_GITHUB_CACHE_SECONDS and
                cache_data['_release_version'] == common.RELEASE
            ):
                logger.debug('Using cached GitHub %s data', cache)
                return cache_data['github_data']
        except:
            pass


def read_changelog(latest_only=False, since_prev_release=False):
    changelog_file = os.path.join(plexpy.PROG_DIR, 'CHANGELOG.md')

    if not os.path.isfile(changelog_file):
        return '<h4>Missing changelog file</h4>'

    try:
        output = ['']
        prev_level = 0

        latest_version_found = False

        header_pattern = re.compile(r'(^#+)\s(.+)')
        list_pattern = re.compile(r'(^[ \t]*\*\s)(.+)')

        beta_release = False
        prev_release = str(plexpy.PREV_RELEASE)

        with open(changelog_file, "r") as logfile:
            for line in logfile:
                line_header_match = re.search(header_pattern, line)
                line_list_match = re.search(list_pattern, line)

                if line_header_match:
                    header_level = str(len(line_header_match.group(1)))
                    header_text = line_header_match.group(2)

                    if header_text.lower() == 'changelog':
                        continue

                    if latest_version_found:
                        break
                    elif latest_only:
                        latest_version_found = True
                    # Add a space to the end of the release to match tags
                    elif since_prev_release:
                        if prev_release.endswith('-beta') and not beta_release:
                            if prev_release + ' ' in header_text:
                                break
                            elif prev_release.replace('-beta', '') + ' ' in header_text:
                                beta_release = True
                        elif prev_release.endswith('-beta') and beta_release:
                            break
                        elif prev_release + ' ' in header_text:
                            break

                    output[-1] += '<h' + header_level + '>' + header_text + '</h' + header_level + '>'

                elif line_list_match:
                    line_level = len(line_list_match.group(1)) // 2
                    line_text = line_list_match.group(2)

                    if line_level > prev_level:
                        output[-1] += '<ul>' * (line_level - prev_level) + '<li>' + line_text + '</li>'
                    elif line_level < prev_level:
                        output[-1] += '</ul>' * (prev_level - line_level) + '<li>' + line_text + '</li>'
                    else:
                        output[-1] += '<li>' + line_text + '</li>'

                    prev_level = line_level

                elif line.strip() == '' and prev_level:
                    output[-1] += '</ul>' * (prev_level)
                    output.append('')
                    prev_level = 0

        if since_prev_release:
            output.reverse()

        return ''.join(output)

    except IOError as e:
        logger.error('Tautulli Version Checker :: Unable to open changelog file. %s' % e)
        return '<h4>Unable to open changelog file</h4>'
