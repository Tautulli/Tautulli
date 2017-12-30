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

import os
import platform
import re
import subprocess
import tarfile

import plexpy
import logger
import request
import version


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
            output = output.strip()

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

    return (output, err)


def getVersion():

    if version.PLEXPY_BRANCH.startswith('win32build'):
        plexpy.INSTALL_TYPE = 'win'

        # Don't have a way to update exe yet, but don't want to set VERSION to None
        return 'Windows Install', 'origin', 'master'

    elif os.path.isdir(os.path.join(plexpy.PROG_DIR, '.git')):

        plexpy.INSTALL_TYPE = 'git'
        output, err = runGit('rev-parse HEAD')

        if not output:
            logger.error('Could not find latest installed version.')
            cur_commit_hash = None

        cur_commit_hash = str(output)

        if not re.match('^[a-z0-9]+$', cur_commit_hash):
            logger.error('Output does not look like a hash, not using it.')
            cur_commit_hash = None

        if plexpy.CONFIG.DO_NOT_OVERRIDE_GIT_BRANCH and plexpy.CONFIG.GIT_BRANCH:
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

        plexpy.INSTALL_TYPE = 'source'

        version_file = os.path.join(plexpy.PROG_DIR, 'version.txt')

        if not os.path.isfile(version_file):
            return None, 'origin', 'master'

        with open(version_file, 'r') as f:
            current_version = f.read().strip(' \n\r')

        if current_version:
            return current_version, plexpy.CONFIG.GIT_REMOTE, plexpy.CONFIG.GIT_BRANCH
        else:
            return None, 'origin', 'master'


def checkGithub(auto_update=False):
    plexpy.COMMITS_BEHIND = 0

    # Get the latest version available from github
    logger.info('Retrieving latest version information from GitHub')
    url = 'https://api.github.com/repos/%s/plexpy/commits/%s' % (plexpy.CONFIG.GIT_USER, plexpy.CONFIG.GIT_BRANCH)
    if plexpy.CONFIG.GIT_TOKEN: url = url + '?access_token=%s' % plexpy.CONFIG.GIT_TOKEN
    version = request.request_json(url, timeout=20, validator=lambda x: type(x) == dict)

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

    logger.info('Comparing currently installed version with latest GitHub version')
    url = 'https://api.github.com/repos/%s/plexpy/compare/%s...%s' % (plexpy.CONFIG.GIT_USER, plexpy.LATEST_VERSION, plexpy.CURRENT_VERSION)
    if plexpy.CONFIG.GIT_TOKEN: url = url + '?access_token=%s' % plexpy.CONFIG.GIT_TOKEN
    commits = request.request_json(url, timeout=20, whitelist_status_code=404, validator=lambda x: type(x) == dict)

    if commits is None:
        logger.warn('Could not get commits behind from GitHub.')
        return plexpy.LATEST_VERSION

    try:
        plexpy.COMMITS_BEHIND = int(commits['behind_by'])
        logger.debug("In total, %d commits behind", plexpy.COMMITS_BEHIND)
    except KeyError:
        logger.info('Cannot compare versions. Are you running a local development version?')
        plexpy.COMMITS_BEHIND = 0

    if plexpy.COMMITS_BEHIND > 0:
        logger.info('New version is available. You are %s commits behind' % plexpy.COMMITS_BEHIND)

        url = 'https://api.github.com/repos/%s/plexpy/releases' % plexpy.CONFIG.GIT_USER
        releases = request.request_json(url, timeout=20, whitelist_status_code=404, validator=lambda x: type(x) == list)

        if plexpy.CONFIG.GIT_BRANCH == 'master':
            release = next((r for r in releases if not r['prerelease']), releases[0])
        elif plexpy.CONFIG.GIT_BRANCH == 'beta':
            release = next((r for r in releases if r['prerelease'] and '-beta' in r['tag_name']), releases[0])
        elif plexpy.CONFIG.GIT_BRANCH == 'nightly':
            release = next((r for r in releases if r['prerelease'] and '-nightly' in r['tag_name']), releases[0])
        else:
            release = releases[0]

        plexpy.NOTIFY_QUEUE.put({'notify_action': 'on_plexpyupdate', 'plexpy_download_info': release,
                                 'plexpy_update_commit': plexpy.LATEST_VERSION, 'plexpy_update_behind': plexpy.COMMITS_BEHIND})

        if auto_update:
            logger.info('Running automatic update.')
            plexpy.shutdown(restart=True, update=True)

    elif plexpy.COMMITS_BEHIND == 0:
        logger.info('Tautulli is up to date')

    return plexpy.LATEST_VERSION


def update():
    if plexpy.INSTALL_TYPE == 'win':
        logger.info('Windows .exe updating not supported yet.')

    elif plexpy.INSTALL_TYPE == 'git':
        output, err = runGit('pull ' + plexpy.CONFIG.GIT_REMOTE + ' ' + plexpy.CONFIG.GIT_BRANCH)

        if not output:
            logger.error('Unable to download latest version')
            return

        for line in output.split('\n'):

            if 'Already up-to-date.' in line:
                logger.info('No update available, not updating')
                logger.info('Output: ' + str(output))
            elif line.endswith(('Aborting', 'Aborting.')):
                logger.error('Unable to update from git: ' + line)
                logger.info('Output: ' + str(output))

    else:
        tar_download_url = 'https://github.com/{}/{}/tarball/{}'.format(plexpy.CONFIG.GIT_USER, plexpy.CONFIG.GIT_REPO, plexpy.CONFIG.GIT_BRANCH)
        update_dir = os.path.join(plexpy.PROG_DIR, 'update')
        version_path = os.path.join(plexpy.PROG_DIR, 'version.txt')

        logger.info('Downloading update from: ' + tar_download_url)
        data = request.request_content(tar_download_url)

        if not data:
            logger.error("Unable to retrieve new version from '%s', can't update", tar_download_url)
            return

        download_name = plexpy.CONFIG.GIT_BRANCH + '-github'
        tar_download_path = os.path.join(plexpy.PROG_DIR, download_name)

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


def checkout_git_branch():
    if plexpy.INSTALL_TYPE == 'git':
        output, err = runGit('fetch ' + plexpy.CONFIG.GIT_REMOTE)
        output, err = runGit('checkout ' + plexpy.CONFIG.GIT_BRANCH)

        if not output:
            logger.error('Unable to change git branch.')
            return

        for line in output.split('\n'):
            if line.endswith(('Aborting', 'Aborting.')):
                logger.error('Unable to checkout from git: ' + line)
                logger.info('Output: ' + str(output))


def read_changelog(latest_only=False):
    changelog_file = os.path.join(plexpy.PROG_DIR, 'CHANGELOG.md')

    if not os.path.isfile(changelog_file):
        return '<h4>Missing changelog file</h4>'

    try:
        output = ''
        prev_level = 0

        latest_version_found = False

        header_pattern = re.compile(r'(^#+)\s(.+)')
        list_pattern = re.compile(r'(^[ \t]*\*\s)(.+)')

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

                    output += '<h' + header_level + '>' + header_text + '</h' + header_level + '>'

                elif line_list_match:
                    line_level = len(line_list_match.group(1)) / 2
                    line_text = line_list_match.group(2)

                    if line_level > prev_level:
                        output += '<ul>' * (line_level - prev_level) + '<li>' + line_text + '</li>'
                    elif line_level < prev_level:
                        output += '</ul>' * (prev_level - line_level) + '<li>' + line_text + '</li>'
                    else:
                        output += '<li>' + line_text + '</li>'

                    prev_level = line_level

                elif line.strip() == '' and prev_level:
                    output += '</ul>' * (prev_level)
                    prev_level = 0

        return output

    except IOError as e:
        logger.error('Tautulli Version Checker :: Unable to open changelog file. %s' % e)
        return '<h4>Unable to open changelog file</h4>'
