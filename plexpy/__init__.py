# This file is part of PlexPy.
#
#  PlexPy is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  PlexPy is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with PlexPy.  If not, see <http://www.gnu.org/licenses/>.

# NZBGet support added by CurlyMo <curlymoo1@gmail.com> as a part of
# XBian - XBMC on the Raspberry Pi

import os
import sys
import subprocess
import threading
import webbrowser
import sqlite3
import cherrypy
import datetime
import uuid

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from plexpy import versioncheck, logger
import plexpy.config

PROG_DIR = None
FULL_PATH = None

ARGS = None
SIGNAL = None

SYS_PLATFORM = None
SYS_ENCODING = None

QUIET = False
VERBOSE = True
DAEMON = False
CREATEPID = False
PIDFILE = None

SCHED = BackgroundScheduler()
SCHED_LOCK = threading.Lock()

INIT_LOCK = threading.Lock()
_INITIALIZED = False
started = False

DATA_DIR = None

CONFIG = None

DB_FILE = None

LOG_LIST = []

INSTALL_TYPE = None
CURRENT_VERSION = None
LATEST_VERSION = None
COMMITS_BEHIND = None

UMASK = None


def initialize(config_file):
    with INIT_LOCK:

        global CONFIG
        global _INITIALIZED
        global CURRENT_VERSION
        global LATEST_VERSION
        global UMASK

        CONFIG = plexpy.config.Config(config_file)

        assert CONFIG is not None

        if _INITIALIZED:
            return False

        if CONFIG.HTTP_PORT < 21 or CONFIG.HTTP_PORT > 65535:
            plexpy.logger.warn(
                'HTTP_PORT out of bounds: 21 < %s < 65535', CONFIG.HTTP_PORT)
            CONFIG.HTTP_PORT = 8181

        if CONFIG.HTTPS_CERT == '':
            CONFIG.HTTPS_CERT = os.path.join(DATA_DIR, 'server.crt')
        if CONFIG.HTTPS_KEY == '':
            CONFIG.HTTPS_KEY = os.path.join(DATA_DIR, 'server.key')

        if not CONFIG.LOG_DIR:
            CONFIG.LOG_DIR = os.path.join(DATA_DIR, 'logs')

        if not os.path.exists(CONFIG.LOG_DIR):
            try:
                os.makedirs(CONFIG.LOG_DIR)
            except OSError:
                CONFIG.LOG_DIR = None

                if not QUIET:
                    sys.stderr.write("Unable to create the log directory. " \
                                     "Logging to screen only.\n")

        # Start the logger, disable console if needed
        logger.initLogger(console=not QUIET, log_dir=CONFIG.LOG_DIR,
                          verbose=VERBOSE)

        if not CONFIG.CACHE_DIR:
            # Put the cache dir in the data dir for now
            CONFIG.CACHE_DIR = os.path.join(DATA_DIR, 'cache')
        if not os.path.exists(CONFIG.CACHE_DIR):
            try:
                os.makedirs(CONFIG.CACHE_DIR)
            except OSError as e:
                logger.error("Could not create cache dir '%s': %s", DATA_DIR, e)

        # Initialize the database
        logger.info('Checking to see if the database has all tables....')
        try:
            dbcheck()
        except Exception as e:
            logger.error("Can't connect to the database: %s", e)

        # Check if PlexPy has a uuid
        if CONFIG.PMS_UUID == '' or not CONFIG.PMS_UUID:
            my_uuid = generate_uuid()
            CONFIG.__setattr__('PMS_UUID', my_uuid)
            CONFIG.write()

        # Get the currently installed version. Returns None, 'win32' or the git
        # hash.
        CURRENT_VERSION, CONFIG.GIT_BRANCH = versioncheck.getVersion()

        # Write current version to a file, so we know which version did work.
        # This allowes one to restore to that version. The idea is that if we
        # arrive here, most parts of PlexPy seem to work.
        if CURRENT_VERSION:
            version_lock_file = os.path.join(DATA_DIR, "version.lock")

            try:
                with open(version_lock_file, "w") as fp:
                    fp.write(CURRENT_VERSION)
            except IOError as e:
                logger.error("Unable to write current version to file '%s': %s",
                             version_lock_file, e)

        # Check for new versions
        if CONFIG.CHECK_GITHUB_ON_STARTUP:
            try:
                LATEST_VERSION = versioncheck.checkGithub()
            except:
                logger.exception("Unhandled exception")
                LATEST_VERSION = CURRENT_VERSION
        else:
            LATEST_VERSION = CURRENT_VERSION

        # Store the original umask
        UMASK = os.umask(0)
        os.umask(UMASK)

        _INITIALIZED = True
        return True


def daemonize():
    if threading.activeCount() != 1:
        logger.warn(
            'There are %r active threads. Daemonizing may cause'
            ' strange behavior.',
            threading.enumerate())

    sys.stdout.flush()
    sys.stderr.flush()

    # Do first fork
    try:
        pid = os.fork()  # @UndefinedVariable - only available in UNIX
        if pid != 0:
            sys.exit(0)
    except OSError, e:
        raise RuntimeError("1st fork failed: %s [%d]", e.strerror, e.errno)

    os.setsid()

    # Make sure I can read my own files and shut out others
    prev = os.umask(0)  # @UndefinedVariable - only available in UNIX
    os.umask(prev and int('077', 8))

    # Make the child a session-leader by detaching from the terminal
    try:
        pid = os.fork()  # @UndefinedVariable - only available in UNIX
        if pid != 0:
            sys.exit(0)
    except OSError, e:
        raise RuntimeError("2nd fork failed: %s [%d]", e.strerror, e.errno)

    dev_null = file('/dev/null', 'r')
    os.dup2(dev_null.fileno(), sys.stdin.fileno())

    si = open('/dev/null', "r")
    so = open('/dev/null', "a+")
    se = open('/dev/null', "a+")

    os.dup2(si.fileno(), sys.stdin.fileno())
    os.dup2(so.fileno(), sys.stdout.fileno())
    os.dup2(se.fileno(), sys.stderr.fileno())

    pid = os.getpid()
    logger.info('Daemonized to PID: %d', pid)

    if CREATEPID:
        logger.info("Writing PID %d to %s", pid, PIDFILE)
        with file(PIDFILE, 'w') as fp:
            fp.write("%s\n" % pid)


def launch_browser(host, port, root):
    if host == '0.0.0.0':
        host = 'localhost'

    if CONFIG.ENABLE_HTTPS:
        protocol = 'https'
    else:
        protocol = 'http'

    try:
        webbrowser.open('%s://%s:%i%s' % (protocol, host, port, root))
    except Exception as e:
        logger.error('Could not launch browser: %s', e)


def initialize_scheduler():
    """
    Start the scheduled background tasks. Re-schedule if interval settings changed.
    """



    with SCHED_LOCK:

        # Check if scheduler should be started
        start_jobs = not len(SCHED.get_jobs())

        #Update check
        if CONFIG.CHECK_GITHUB_INTERVAL:
            minutes = CONFIG.CHECK_GITHUB_INTERVAL
        else:
            minutes = 0
        schedule_job(versioncheck.checkGithub, 'Check GitHub for updates', hours=0, minutes=minutes)

        # Start scheduler
        if start_jobs and len(SCHED.get_jobs()):
            try:
                SCHED.start()
            except Exception as e:
                logger.info(e)

                # Debug
                #SCHED.print_jobs()


def schedule_job(function, name, hours=0, minutes=0):
    """
    Start scheduled job if starting or restarting plexpy.
    Reschedule job if Interval Settings have changed.
    Remove job if if Interval Settings changed to 0

    """

    job = SCHED.get_job(name)
    if job:
        if hours == 0 and minutes == 0:
            SCHED.remove_job(name)
            logger.info("Removed background task: %s", name)
        elif job.trigger.interval != datetime.timedelta(hours=hours, minutes=minutes):
            SCHED.reschedule_job(name, trigger=IntervalTrigger(
                hours=hours, minutes=minutes))
            logger.info("Re-scheduled background task: %s", name)
    elif hours > 0 or minutes > 0:
        SCHED.add_job(function, id=name, trigger=IntervalTrigger(
            hours=hours, minutes=minutes))
        logger.info("Scheduled background task: %s", name)


def start():
    global started

    if _INITIALIZED:
        initialize_scheduler()
        started = True


def sig_handler(signum=None, frame=None):
    if signum is not None:
        logger.info("Signal %i caught, saving and exiting...", signum)
        shutdown()


def dbcheck():
    conn = sqlite3.connect(plexpy.CONFIG.PLEXWATCH_DATABASE)
    c = conn.cursor()
    conn.commit()
    c.close()


def shutdown(restart=False, update=False):
    cherrypy.engine.exit()
    SCHED.shutdown(wait=False)

    CONFIG.write()

    if not restart and not update:
        logger.info('PlexPy is shutting down...')

    if update:
        logger.info('PlexPy is updating...')
        try:
            versioncheck.update()
        except Exception as e:
            logger.warn('PlexPy failed to update: %s. Restarting.', e)

    if CREATEPID:
        logger.info('Removing pidfile %s', PIDFILE)
        os.remove(PIDFILE)

    if restart:
        logger.info('PlexPy is restarting...')
        popen_list = [sys.executable, FULL_PATH]
        popen_list += ARGS
        if '--nolaunch' not in popen_list:
            popen_list += ['--nolaunch']
        logger.info('Restarting PlexPy with %s', popen_list)
        subprocess.Popen(popen_list, cwd=os.getcwd())

    os._exit(0)

def generate_uuid():
    logger.debug(u"Generating UUID...")
    return uuid.uuid4().hex