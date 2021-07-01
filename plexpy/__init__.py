# This file is part of Tautulli.
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

from __future__ import unicode_literals
from future.builtins import range

import datetime
import os
import future.moves.queue as queue
import sqlite3
import sys
import subprocess
import threading
import uuid

# Some cut down versions of Python may not include this module and it's not critical for us
try:
    import webbrowser
    no_browser = False
except ImportError:
    no_browser = True

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from UniversalAnalytics import Tracker
import pytz

PYTHON2 = sys.version_info[0] == 2

if PYTHON2:
    import activity_handler
    import activity_pinger
    import common
    import database
    import datafactory
    import exporter
    import helpers
    import libraries
    import logger
    import mobile_app
    import newsletters
    import newsletter_handler
    import notification_handler
    import notifiers
    import plex
    import plextv
    import users
    import versioncheck
    import web_socket
    import webstart
    import config
else:
    from plexpy import activity_handler
    from plexpy import activity_pinger
    from plexpy import common
    from plexpy import database
    from plexpy import datafactory
    from plexpy import exporter
    from plexpy import helpers
    from plexpy import libraries
    from plexpy import logger
    from plexpy import mobile_app
    from plexpy import newsletters
    from plexpy import newsletter_handler
    from plexpy import notification_handler
    from plexpy import notifiers
    from plexpy import plex
    from plexpy import plextv
    from plexpy import users
    from plexpy import versioncheck
    from plexpy import web_socket
    from plexpy import webstart
    from plexpy import config


PROG_DIR = None
FULL_PATH = None

ARGS = None
SIGNAL = None

SYS_PLATFORM = None
SYS_LANGUAGE = None
SYS_ENCODING = None

QUIET = False
VERBOSE = False
DAEMON = False
CREATEPID = False
PIDFILE = None
NOFORK = False
DOCKER = False
SNAP = False
SNAP_MIGRATE = False
FROZEN = False

SCHED = None
SCHED_LOCK = threading.Lock()

NOTIFY_QUEUE = queue.Queue()

INIT_LOCK = threading.Lock()
_INITIALIZED = False
_STARTED = False
_UPDATE = False

DATA_DIR = None

CONFIG = None
CONFIG_FILE = None

DB_FILE = None

INSTALL_TYPE = None
CURRENT_VERSION = None
LATEST_VERSION = None
COMMITS_BEHIND = None
PREV_RELEASE = None
LATEST_RELEASE = None
UPDATE_AVAILABLE = False

UMASK = None

HTTP_PORT = None
HTTP_ROOT = None
AUTH_ENABLED = None

DEV = False

WEBSOCKET = None
WS_CONNECTED = False
PLEX_SERVER_UP = None
PLEX_REMOTE_ACCESS_UP = None

TRACKER = None

WIN_SYS_TRAY_ICON = None
MAC_SYS_TRAY_ICON = None

SYS_TIMEZONE = None
SYS_UTC_OFFSET = None


def initialize(config_file):
    with INIT_LOCK:

        global CONFIG
        global CONFIG_FILE
        global VERBOSE
        global _INITIALIZED
        global CURRENT_VERSION
        global LATEST_VERSION
        global PREV_RELEASE
        global UMASK
        global _UPDATE

        try:
            CONFIG = config.Config(config_file)
        except:
            raise SystemExit("Unable to initialize Tautulli due to a corrupted config file. Exiting...")

        CONFIG_FILE = config_file

        assert CONFIG is not None

        if _INITIALIZED:
            return False

        if SNAP_MIGRATE:
            snap_common = os.environ['SNAP_COMMON']
            old_data_dir = os.path.join(snap_common, 'Tautulli')
            CONFIG.HTTPS_CERT = CONFIG.HTTPS_CERT.replace(old_data_dir, DATA_DIR)
            CONFIG.HTTPS_CERT_CHAIN = CONFIG.HTTPS_CERT_CHAIN.replace(old_data_dir, DATA_DIR)
            CONFIG.HTTPS_KEY = CONFIG.HTTPS_KEY.replace(old_data_dir, DATA_DIR)
            CONFIG.LOG_DIR = CONFIG.LOG_DIR.replace(old_data_dir, DATA_DIR)
            CONFIG.BACKUP_DIR = CONFIG.BACKUP_DIR.replace(old_data_dir, DATA_DIR)
            CONFIG.CACHE_DIR = CONFIG.CACHE_DIR.replace(old_data_dir, DATA_DIR)
            CONFIG.EXPORT_DIR = CONFIG.EXPORT_DIR.replace(old_data_dir, DATA_DIR)
            CONFIG.NEWSLETTER_DIR = CONFIG.NEWSLETTER_DIR.replace(old_data_dir, DATA_DIR)

        if CONFIG.HTTP_PORT < 21 or CONFIG.HTTP_PORT > 65535:
            logger.warn("HTTP_PORT out of bounds: 21 < %s < 65535", CONFIG.HTTP_PORT)
            CONFIG.HTTP_PORT = 8181

        if not CONFIG.HTTPS_CERT:
            CONFIG.HTTPS_CERT = os.path.join(DATA_DIR, 'server.crt')
        if not CONFIG.HTTPS_KEY:
            CONFIG.HTTPS_KEY = os.path.join(DATA_DIR, 'server.key')

        CONFIG.LOG_DIR, log_writable = check_folder_writable(
            CONFIG.LOG_DIR, os.path.join(DATA_DIR, 'logs'), 'logs')
        if not log_writable and not QUIET:
            sys.stderr.write("Unable to create the log directory. Logging to screen only.\n")

        VERBOSE = VERBOSE or bool(CONFIG.VERBOSE_LOGS)

        # Start the logger, disable console if needed
        logger.initLogger(console=not QUIET, log_dir=CONFIG.LOG_DIR if log_writable else None,
                          verbose=VERBOSE)

        if not PYTHON2:
            os.environ['PLEXAPI_CONFIG_PATH'] = os.path.join(DATA_DIR, 'plexapi.config.ini')
            os.environ['PLEXAPI_LOG_PATH'] = os.path.join(CONFIG.LOG_DIR, 'plexapi.log')
            plex.initialize_plexapi()

        if DOCKER:
            build = '[Docker] '
        elif SNAP:
            build = '[Snap] '
        elif FROZEN:
            build = '[Bundle] '
        else:
            build = ''

        logger.info("Starting Tautulli {}".format(
            common.RELEASE
        ))
        logger.info("{}{} {} ({}{})".format(
            build, common.PLATFORM, common.PLATFORM_RELEASE, common.PLATFORM_VERSION,
            ' - {}'.format(common.PLATFORM_LINUX_DISTRO) if common.PLATFORM_LINUX_DISTRO else ''
        ))
        logger.info("{} (UTC{})".format(
            SYS_TIMEZONE.zone, SYS_UTC_OFFSET
        ))
        logger.info("Python {}".format(
            sys.version.replace('\n', '')
        ))
        logger.info("Program Dir: {}".format(
            PROG_DIR
        ))
        logger.info("Config File: {}".format(
            CONFIG_FILE
        ))
        logger.info("Database File: {}".format(
            DB_FILE
        ))

        CONFIG.BACKUP_DIR, _ = check_folder_writable(
            CONFIG.BACKUP_DIR, os.path.join(DATA_DIR, 'backups'), 'backups')
        CONFIG.CACHE_DIR, _ = check_folder_writable(
            CONFIG.CACHE_DIR, os.path.join(DATA_DIR, 'cache'), 'cache')
        CONFIG.EXPORT_DIR, _ = check_folder_writable(
            CONFIG.EXPORT_DIR, os.path.join(DATA_DIR, 'exports'), 'exports')
        CONFIG.NEWSLETTER_DIR, _ = check_folder_writable(
            CONFIG.NEWSLETTER_DIR, os.path.join(DATA_DIR, 'newsletters'), 'newsletters')

        # Initialize the database
        logger.info("Checking if the database upgrades are required...")
        try:
            dbcheck()
        except Exception as e:
            logger.error("Can't connect to the database: %s" % e)

        # Perform upgrades
        logger.info("Checking if configuration upgrades are required...")
        try:
            upgrade()
        except Exception as e:
            logger.error("Could not perform upgrades: %s" % e)

        # Add notifier configs to logger blacklist
        newsletters.blacklist_logger()
        notifiers.blacklist_logger()
        mobile_app.blacklist_logger()

        # Check if Tautulli has a uuid
        if CONFIG.PMS_UUID == '' or not CONFIG.PMS_UUID:
            logger.debug("Generating UUID...")
            CONFIG.PMS_UUID = generate_uuid()
            CONFIG.write()

        # Check if Tautulli has an API key
        if CONFIG.API_KEY == '':
            logger.debug("Generating API key...")
            CONFIG.API_KEY = generate_uuid()
            CONFIG.write()

        # Check if Tautulli has a jwt_secret
        if CONFIG.JWT_SECRET == '' or not CONFIG.JWT_SECRET or CONFIG.JWT_UPDATE_SECRET:
            logger.debug("Generating JWT secret...")
            CONFIG.JWT_SECRET = generate_uuid()
            CONFIG.JWT_UPDATE_SECRET = False
            CONFIG.write()

        # Get the previous version from the file
        version_lock_file = os.path.join(DATA_DIR, "version.lock")
        prev_version = None
        if os.path.isfile(version_lock_file):
            try:
                with open(version_lock_file, "r") as fp:
                    prev_version = fp.read()
            except IOError as e:
                logger.error("Unable to read previous version from file '%s': %s" %
                             (version_lock_file, e))

        # Get the currently installed version. Returns None, 'win32' or the git
        # hash.
        CURRENT_VERSION, CONFIG.GIT_REMOTE, CONFIG.GIT_BRANCH = versioncheck.get_version()

        # Write current version to a file, so we know which version did work.
        # This allows one to restore to that version. The idea is that if we
        # arrive here, most parts of Tautulli seem to work.
        if CURRENT_VERSION:
            try:
                with open(version_lock_file, "w") as fp:
                    fp.write(CURRENT_VERSION)
            except IOError as e:
                logger.error("Unable to write current version to file '%s': %s" %
                             (version_lock_file, e))

        # Check for new versions
        if CONFIG.CHECK_GITHUB_ON_STARTUP and CONFIG.CHECK_GITHUB:
            try:
                versioncheck.check_update(use_cache=True)
            except:
                logger.exception("Unhandled exception")
                LATEST_VERSION = CURRENT_VERSION
        else:
            LATEST_VERSION = CURRENT_VERSION

        # Get the previous release from the file
        release_file = os.path.join(DATA_DIR, "release.lock")
        PREV_RELEASE = common.RELEASE
        if os.path.isfile(release_file):
            try:
                with open(release_file, "r") as fp:
                    PREV_RELEASE = fp.read()
            except IOError as e:
                logger.error("Unable to read previous release from file '%s': %s" %
                             (release_file, e))

        # Check if the release was updated
        if common.RELEASE != PREV_RELEASE:
            CONFIG.UPDATE_SHOW_CHANGELOG = 1
            CONFIG.write()
            _UPDATE = True

        # Write current release version to file for update checking
        try:
            with open(release_file, "w") as fp:
                fp.write(common.RELEASE)
        except IOError as e:
            logger.error("Unable to write current release to file '%s': %s" %
                         (release_file, e))

        # Store the original umask
        UMASK = os.umask(0)
        os.umask(UMASK)

        _INITIALIZED = True
        return True


def daemonize():
    if threading.activeCount() != 1:
        logger.warn(
            "There are %r active threads. Daemonizing may cause"
            " strange behavior.",
            threading.enumerate())

    sys.stdout.flush()
    sys.stderr.flush()

    # Do first fork
    try:
        pid = os.fork()  # @UndefinedVariable - only available in UNIX
        if pid != 0:
            sys.exit(0)
    except OSError as e:
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
    except OSError as e:
        raise RuntimeError("2nd fork failed: %s [%d]", e.strerror, e.errno)

    dev_null = open('/dev/null', 'r')
    os.dup2(dev_null.fileno(), sys.stdin.fileno())

    si = open('/dev/null', "r")
    so = open('/dev/null', "a+")
    se = open('/dev/null', "a+")

    os.dup2(si.fileno(), sys.stdin.fileno())
    os.dup2(so.fileno(), sys.stdout.fileno())
    os.dup2(se.fileno(), sys.stderr.fileno())

    pid = os.getpid()
    logger.info("Daemonized to PID: %d", pid)

    if CREATEPID:
        logger.info("Writing PID %d to %s", pid, PIDFILE)
        with open(PIDFILE, 'w') as fp:
            fp.write("%s\n" % pid)


def launch_browser(host, port, root):
    if not no_browser:
        if host == '0.0.0.0':
            host = 'localhost'

        if CONFIG.ENABLE_HTTPS:
            protocol = 'https'
        else:
            protocol = 'http'

        try:
            webbrowser.open('%s://%s:%i%s' % (protocol, host, port, root))
        except Exception as e:
            logger.error("Could not launch browser: %s" % e)


def initialize_scheduler():
    """
    Start the scheduled background tasks. Re-schedule if interval settings changed.
    """

    with SCHED_LOCK:

        # Check if scheduler should be started
        start_jobs = not len(SCHED.get_jobs())

        # Update check
        github_hours = CONFIG.CHECK_GITHUB_INTERVAL if CONFIG.CHECK_GITHUB_INTERVAL and CONFIG.CHECK_GITHUB else 0
        pms_update_check_hours = CONFIG.PMS_UPDATE_CHECK_INTERVAL if 1 <= CONFIG.PMS_UPDATE_CHECK_INTERVAL else 24

        schedule_job(versioncheck.check_update, 'Check GitHub for updates',
                     hours=github_hours, minutes=0, seconds=0, args=(True, True))

        backup_hours = CONFIG.BACKUP_INTERVAL if 1 <= CONFIG.BACKUP_INTERVAL <= 24 else 6

        schedule_job(database.optimize_db, 'Optimize Tautulli database',
                     hours=24, minutes=0, seconds=0)
        schedule_job(database.make_backup, 'Backup Tautulli database',
                     hours=backup_hours, minutes=0, seconds=0, args=(True, True))
        schedule_job(config.make_backup, 'Backup Tautulli config',
                     hours=backup_hours, minutes=0, seconds=0, args=(True, True))

        if WS_CONNECTED and CONFIG.PMS_IP and CONFIG.PMS_TOKEN:
            schedule_job(plextv.get_server_resources, 'Refresh Plex server URLs',
                         hours=12 * (not bool(CONFIG.PMS_URL_MANUAL)), minutes=0, seconds=0)

            schedule_job(activity_pinger.check_server_updates, 'Check for Plex updates',
                         hours=pms_update_check_hours * bool(CONFIG.MONITOR_PMS_UPDATES), minutes=0, seconds=0)

            # Refresh the users list and libraries list
            user_hours = CONFIG.REFRESH_USERS_INTERVAL if 1 <= CONFIG.REFRESH_USERS_INTERVAL <= 24 else 12
            library_hours = CONFIG.REFRESH_LIBRARIES_INTERVAL if 1 <= CONFIG.REFRESH_LIBRARIES_INTERVAL <= 24 else 12

            schedule_job(users.refresh_users, 'Refresh users list',
                         hours=user_hours, minutes=0, seconds=0)
            schedule_job(libraries.refresh_libraries, 'Refresh libraries list',
                         hours=library_hours, minutes=0, seconds=0)

            schedule_job(activity_pinger.connect_server, 'Check for server response',
                         hours=0, minutes=0, seconds=0)
            schedule_job(web_socket.send_ping, 'Websocket ping',
                         hours=0, minutes=0, seconds=10 * bool(CONFIG.WEBSOCKET_MONITOR_PING_PONG))

        else:
            # Cancel all jobs
            schedule_job(plextv.get_server_resources, 'Refresh Plex server URLs',
                         hours=0, minutes=0, seconds=0)

            schedule_job(activity_pinger.check_server_updates, 'Check for Plex updates',
                         hours=0, minutes=0, seconds=0)

            schedule_job(users.refresh_users, 'Refresh users list',
                         hours=0, minutes=0, seconds=0)
            schedule_job(libraries.refresh_libraries, 'Refresh libraries list',
                         hours=0, minutes=0, seconds=0)

            # Schedule job to reconnect server
            schedule_job(activity_pinger.connect_server, 'Check for server response',
                         hours=0, minutes=0, seconds=30, args=(False,))
            schedule_job(web_socket.send_ping, 'Websocket ping',
                         hours=0, minutes=0, seconds=0)

        # Start scheduler
        if start_jobs and len(SCHED.get_jobs()):
            try:
                SCHED.start()
            except Exception as e:
                logger.error(e)


def schedule_job(func, name, hours=0, minutes=0, seconds=0, args=None):
    """
    Start scheduled job if starting or restarting plexpy.
    Reschedule job if Interval Settings have changed.
    Remove job if if Interval Settings changed to 0

    """

    job = SCHED.get_job(name)
    if job:
        if hours == 0 and minutes == 0 and seconds == 0:
            SCHED.remove_job(name)
            logger.info("Removed background task: %s", name)
        elif job.trigger.interval != datetime.timedelta(hours=hours, minutes=minutes):
            SCHED.reschedule_job(
                name, trigger=IntervalTrigger(
                    hours=hours, minutes=minutes, seconds=seconds, timezone=pytz.UTC),
                args=args)
            logger.info("Re-scheduled background task: %s", name)
    elif hours > 0 or minutes > 0 or seconds > 0:
        SCHED.add_job(
            func, id=name, trigger=IntervalTrigger(
                hours=hours, minutes=minutes, seconds=seconds, timezone=pytz.UTC),
            args=args, misfire_grace_time=None)
        logger.info("Scheduled background task: %s", name)


def start():
    global _STARTED

    if _INITIALIZED:
        # Start refreshes on a separate thread
        threading.Thread(target=startup_refresh).start()

        global SCHED
        SCHED = BackgroundScheduler(timezone=pytz.UTC)
        activity_handler.ACTIVITY_SCHED = BackgroundScheduler(timezone=pytz.UTC)
        newsletter_handler.NEWSLETTER_SCHED = BackgroundScheduler(timezone=pytz.UTC)

        # Start the scheduler for stale stream callbacks
        activity_handler.ACTIVITY_SCHED.start()

        # Start background notification thread
        notification_handler.start_threads(num_threads=CONFIG.NOTIFICATION_THREADS)
        notifiers.check_browser_enabled()

        # Schedule newsletters
        newsletter_handler.NEWSLETTER_SCHED.start()
        newsletter_handler.schedule_newsletters()

        # Cancel processing exports
        exporter.cancel_exports()

        if CONFIG.SYSTEM_ANALYTICS:
            global TRACKER
            TRACKER = initialize_tracker()

            # Send system analytics events
            if not CONFIG.FIRST_RUN_COMPLETE:
                analytics_event(category='system', action='install')

            elif _UPDATE:
                analytics_event(category='system', action='update')

            analytics_event(category='system', action='start')

        _STARTED = True


def startup_refresh():
    # Get the real PMS urls for SSL and remote access
    if CONFIG.PMS_TOKEN and CONFIG.PMS_IP and CONFIG.PMS_PORT:
        plextv.get_server_resources()

    # Connect server after server resource is refreshed
    if CONFIG.FIRST_RUN_COMPLETE:
        activity_pinger.connect_server(log=True, startup=True)

    # Refresh the users list on startup
    if CONFIG.PMS_TOKEN and CONFIG.REFRESH_USERS_ON_STARTUP:
        users.refresh_users()

    # Refresh the libraries list on startup
    if CONFIG.PMS_IP and CONFIG.PMS_TOKEN and CONFIG.REFRESH_LIBRARIES_ON_STARTUP:
        libraries.refresh_libraries()


def sig_handler(signum=None, frame=None):
    if signum is not None:
        logger.info("Signal %i caught, saving and exiting...", signum)
        shutdown()


def dbcheck():
    conn_db = sqlite3.connect(DB_FILE)
    c_db = conn_db.cursor()

    # schema table :: This is a table which keeps track of the database version
    c_db.execute(
        'CREATE TABLE IF NOT EXISTS version_info (key TEXT UNIQUE, value TEXT)'
    )

    # sessions table :: This is a temp table that logs currently active sessions
    c_db.execute(
        'CREATE TABLE IF NOT EXISTS sessions (id INTEGER PRIMARY KEY AUTOINCREMENT, session_key INTEGER, session_id TEXT, '
        'transcode_key TEXT, rating_key INTEGER, section_id INTEGER, media_type TEXT, started INTEGER, stopped INTEGER, '
        'paused_counter INTEGER DEFAULT 0, state TEXT, user_id INTEGER, user TEXT, friendly_name TEXT, '
        'ip_address TEXT, machine_id TEXT, bandwidth INTEGER, location TEXT, player TEXT, product TEXT, platform TEXT, '
        'title TEXT, parent_title TEXT, grandparent_title TEXT, original_title TEXT, full_title TEXT, '
        'media_index INTEGER, parent_media_index INTEGER, '
        'thumb TEXT, parent_thumb TEXT, grandparent_thumb TEXT, year INTEGER, '
        'parent_rating_key INTEGER, grandparent_rating_key INTEGER, '
        'originally_available_at TEXT, added_at INTEGER, guid TEXT, '
        'view_offset INTEGER DEFAULT 0, duration INTEGER, video_decision TEXT, audio_decision TEXT, '
        'transcode_decision TEXT, container TEXT, bitrate INTEGER, width INTEGER, height INTEGER, '
        'video_codec TEXT, video_bitrate INTEGER, video_resolution TEXT, video_width INTEGER, video_height INTEGER, '
        'video_framerate TEXT, video_scan_type TEXT, video_full_resolution TEXT, '
        'video_dynamic_range TEXT, aspect_ratio TEXT, '
        'audio_codec TEXT, audio_bitrate INTEGER, audio_channels INTEGER, audio_language TEXT, audio_language_code TEXT, '
        'subtitle_codec TEXT, stream_bitrate INTEGER, stream_video_resolution TEXT, quality_profile TEXT, '
        'stream_container_decision TEXT, stream_container TEXT, '
        'stream_video_decision TEXT, stream_video_codec TEXT, stream_video_bitrate INTEGER, stream_video_width INTEGER, '
        'stream_video_height INTEGER, stream_video_framerate TEXT, stream_video_scan_type TEXT, stream_video_full_resolution TEXT, '
        'stream_video_dynamic_range TEXT, '
        'stream_audio_decision TEXT, stream_audio_codec TEXT, stream_audio_bitrate INTEGER, stream_audio_channels INTEGER, '
        'stream_audio_language TEXT, stream_audio_language_code TEXT, '
        'subtitles INTEGER, stream_subtitle_decision TEXT, stream_subtitle_codec TEXT, '
        'transcode_protocol TEXT, transcode_container TEXT, '
        'transcode_video_codec TEXT, transcode_audio_codec TEXT, transcode_audio_channels INTEGER,'
        'transcode_width INTEGER, transcode_height INTEGER, '
        'transcode_hw_decoding INTEGER, transcode_hw_encoding INTEGER, '
        'optimized_version INTEGER, optimized_version_profile TEXT, optimized_version_title TEXT, '
        'synced_version INTEGER, synced_version_profile TEXT, '
        'live INTEGER, live_uuid TEXT, channel_call_sign TEXT, channel_identifier TEXT, channel_thumb TEXT, '
        'secure INTEGER, relayed INTEGER, '
        'buffer_count INTEGER DEFAULT 0, buffer_last_triggered INTEGER, last_paused INTEGER, watched INTEGER DEFAULT 0, '
        'initial_stream INTEGER DEFAULT 1, write_attempts INTEGER DEFAULT 0, raw_stream_info TEXT)'
    )

    # sessions_continued table :: This is a temp table that keeps track of continued streaming sessions
    c_db.execute(
        'CREATE TABLE IF NOT EXISTS sessions_continued (id INTEGER PRIMARY KEY AUTOINCREMENT, '
        'user_id INTEGER, machine_id TEXT, media_type TEXT, stopped INTEGER)'
    )

    # session_history table :: This is a history table which logs essential stream details
    c_db.execute(
        'CREATE TABLE IF NOT EXISTS session_history (id INTEGER PRIMARY KEY AUTOINCREMENT, reference_id INTEGER, '
        'started INTEGER, stopped INTEGER, rating_key INTEGER, user_id INTEGER, user TEXT, '
        'ip_address TEXT, paused_counter INTEGER DEFAULT 0, player TEXT, product TEXT, product_version TEXT, '
        'platform TEXT, platform_version TEXT, profile TEXT, machine_id TEXT, '
        'bandwidth INTEGER, location TEXT, quality_profile TEXT, secure INTEGER, relayed INTEGER, '
        'parent_rating_key INTEGER, grandparent_rating_key INTEGER, media_type TEXT, section_id INTEGER, '
        'view_offset INTEGER DEFAULT 0)'
    )

    # session_history_media_info table :: This is a table which logs each session's media info
    c_db.execute(
        'CREATE TABLE IF NOT EXISTS session_history_media_info (id INTEGER PRIMARY KEY, rating_key INTEGER, '
        'video_decision TEXT, audio_decision TEXT, transcode_decision TEXT, duration INTEGER DEFAULT 0, '
        'container TEXT, bitrate INTEGER, width INTEGER, height INTEGER, video_bitrate INTEGER, video_bit_depth INTEGER, '
        'video_codec TEXT, video_codec_level TEXT, video_width INTEGER, video_height INTEGER, video_resolution TEXT, '
        'video_framerate TEXT, video_scan_type TEXT, video_full_resolution TEXT, video_dynamic_range TEXT, aspect_ratio TEXT, '
        'audio_bitrate INTEGER, audio_codec TEXT, audio_channels INTEGER, audio_language TEXT, audio_language_code TEXT, '
        'transcode_protocol TEXT, transcode_container TEXT, transcode_video_codec TEXT, transcode_audio_codec TEXT, '
        'transcode_audio_channels INTEGER, transcode_width INTEGER, transcode_height INTEGER, '
        'transcode_hw_requested INTEGER, transcode_hw_full_pipeline INTEGER, '
        'transcode_hw_decode TEXT, transcode_hw_decode_title TEXT, transcode_hw_decoding INTEGER, '
        'transcode_hw_encode TEXT, transcode_hw_encode_title TEXT, transcode_hw_encoding INTEGER, '
        'stream_container TEXT, stream_container_decision TEXT, stream_bitrate INTEGER, '
        'stream_video_decision TEXT, stream_video_bitrate INTEGER, stream_video_codec TEXT, stream_video_codec_level TEXT, '
        'stream_video_bit_depth INTEGER, stream_video_height INTEGER, stream_video_width INTEGER, stream_video_resolution TEXT, '
        'stream_video_framerate TEXT, stream_video_scan_type TEXT, stream_video_full_resolution TEXT, stream_video_dynamic_range TEXT, '
        'stream_audio_decision TEXT, stream_audio_codec TEXT, stream_audio_bitrate INTEGER, stream_audio_channels INTEGER, '
        'stream_audio_language TEXT, stream_audio_language_code TEXT, '
        'stream_subtitle_decision TEXT, stream_subtitle_codec TEXT, stream_subtitle_container TEXT, stream_subtitle_forced INTEGER, '
        'subtitles INTEGER, subtitle_codec TEXT, synced_version INTEGER, synced_version_profile TEXT, '
        'optimized_version INTEGER, optimized_version_profile TEXT, optimized_version_title TEXT)'
    )

    # session_history_metadata table :: This is a table which logs each session's media metadata
    c_db.execute(
        'CREATE TABLE IF NOT EXISTS session_history_metadata (id INTEGER PRIMARY KEY, '
        'rating_key INTEGER, parent_rating_key INTEGER, grandparent_rating_key INTEGER, '
        'title TEXT, parent_title TEXT, grandparent_title TEXT, original_title TEXT, full_title TEXT, '
        'media_index INTEGER, parent_media_index INTEGER, '
        'thumb TEXT, parent_thumb TEXT, grandparent_thumb TEXT, '
        'art TEXT, media_type TEXT, year INTEGER, originally_available_at TEXT, added_at INTEGER, updated_at INTEGER, '
        'last_viewed_at INTEGER, content_rating TEXT, summary TEXT, tagline TEXT, rating TEXT, '
        'duration INTEGER DEFAULT 0, guid TEXT, directors TEXT, writers TEXT, actors TEXT, genres TEXT, studio TEXT, '
        'labels TEXT, live INTEGER DEFAULT 0, channel_call_sign TEXT, channel_identifier TEXT, channel_thumb TEXT)'
    )

    # users table :: This table keeps record of the friends list
    c_db.execute(
        'CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, '
        'user_id INTEGER DEFAULT NULL UNIQUE, username TEXT NOT NULL, friendly_name TEXT, '
        'thumb TEXT, custom_avatar_url TEXT, email TEXT, is_active INTEGER DEFAULT 1, is_admin INTEGER DEFAULT 0, '
        'is_home_user INTEGER DEFAULT NULL, is_allow_sync INTEGER DEFAULT NULL, is_restricted INTEGER DEFAULT NULL, '
        'do_notify INTEGER DEFAULT 1, keep_history INTEGER DEFAULT 1, deleted_user INTEGER DEFAULT 0, '
        'allow_guest INTEGER DEFAULT 0, user_token TEXT, server_token TEXT, shared_libraries TEXT, '
        'filter_all TEXT, filter_movies TEXT, filter_tv TEXT, filter_music TEXT, filter_photos TEXT)'
    )

    # library_sections table :: This table keeps record of the servers library sections
    c_db.execute(
        'CREATE TABLE IF NOT EXISTS library_sections (id INTEGER PRIMARY KEY AUTOINCREMENT, '
        'server_id TEXT, section_id INTEGER, section_name TEXT, section_type TEXT, agent TEXT, '
        'thumb TEXT, custom_thumb_url TEXT, art TEXT, custom_art_url TEXT, '
        'count INTEGER, parent_count INTEGER, child_count INTEGER, is_active INTEGER DEFAULT 1, '
        'do_notify INTEGER DEFAULT 1, do_notify_created INTEGER DEFAULT 1, keep_history INTEGER DEFAULT 1, '
        'deleted_section INTEGER DEFAULT 0, UNIQUE(server_id, section_id))'
    )

    # user_login table :: This table keeps record of the Tautulli guest logins
    c_db.execute(
        'CREATE TABLE IF NOT EXISTS user_login (id INTEGER PRIMARY KEY AUTOINCREMENT, '
        'timestamp INTEGER, user_id INTEGER, user TEXT, user_group TEXT, '
        'ip_address TEXT, host TEXT, user_agent TEXT, success INTEGER DEFAULT 1,'
        'expiry TEXT, jwt_token TEXT)'
    )

    # notifiers table :: This table keeps record of the notification agent settings
    c_db.execute(
        'CREATE TABLE IF NOT EXISTS notifiers (id INTEGER PRIMARY KEY AUTOINCREMENT, '
        'agent_id INTEGER, agent_name TEXT, agent_label TEXT, friendly_name TEXT, notifier_config TEXT, '
        'on_play INTEGER DEFAULT 0, on_stop INTEGER DEFAULT 0, on_pause INTEGER DEFAULT 0, '
        'on_resume INTEGER DEFAULT 0, on_change INTEGER DEFAULT 0, on_buffer INTEGER DEFAULT 0, '
        'on_error INTEGER DEFAULT 0, on_watched INTEGER DEFAULT 0, on_created INTEGER DEFAULT 0, '
        'on_extdown INTEGER DEFAULT 0, on_intdown INTEGER DEFAULT 0, '
        'on_extup INTEGER DEFAULT 0, on_intup INTEGER DEFAULT 0, on_pmsupdate INTEGER DEFAULT 0, '
        'on_concurrent INTEGER DEFAULT 0, on_newdevice INTEGER DEFAULT 0, on_plexpyupdate INTEGER DEFAULT 0, '
        'on_plexpydbcorrupt INTEGER DEFAULT 0, '
        'on_play_subject TEXT, on_stop_subject TEXT, on_pause_subject TEXT, '
        'on_resume_subject TEXT, on_change_subject TEXT, on_buffer_subject TEXT, on_error_subject TEXT, '
        'on_watched_subject TEXT, on_created_subject TEXT, on_extdown_subject TEXT, on_intdown_subject TEXT, '
        'on_extup_subject TEXT, on_intup_subject TEXT, on_pmsupdate_subject TEXT, '
        'on_concurrent_subject TEXT, on_newdevice_subject TEXT, on_plexpyupdate_subject TEXT, '
        'on_plexpydbcorrupt_subject TEXT, '
        'on_play_body TEXT, on_stop_body TEXT, on_pause_body TEXT, '
        'on_resume_body TEXT, on_change_body TEXT, on_buffer_body TEXT, on_error_body TEXT, '
        'on_watched_body TEXT, on_created_body TEXT, on_extdown_body TEXT, on_intdown_body TEXT, '
        'on_extup_body TEXT, on_intup_body TEXT, on_pmsupdate_body TEXT, '
        'on_concurrent_body TEXT, on_newdevice_body TEXT, on_plexpyupdate_body TEXT, '
        'on_plexpydbcorrupt_body TEXT, '
        'custom_conditions TEXT, custom_conditions_logic TEXT)'
    )

    # notify_log table :: This is a table which logs notifications sent
    c_db.execute(
        'CREATE TABLE IF NOT EXISTS notify_log (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp INTEGER, '
        'session_key INTEGER, rating_key INTEGER, parent_rating_key INTEGER, grandparent_rating_key INTEGER, '
        'user_id INTEGER, user TEXT, notifier_id INTEGER, agent_id INTEGER, agent_name TEXT, notify_action TEXT, '
        'subject_text TEXT, body_text TEXT, script_args TEXT, success INTEGER DEFAULT 0, tag TEXT)'
    )

    # newsletters table :: This table keeps record of the newsletter settings
    c_db.execute(
        'CREATE TABLE IF NOT EXISTS newsletters (id INTEGER PRIMARY KEY AUTOINCREMENT, '
        'agent_id INTEGER, agent_name TEXT, agent_label TEXT, id_name TEXT NOT NULL, '
        'friendly_name TEXT, newsletter_config TEXT, email_config TEXT, '
        'subject TEXT, body TEXT, message TEXT, '
        'cron TEXT NOT NULL DEFAULT \'0 0 * * 0\', active INTEGER DEFAULT 0)'
    )

    # newsletter_log table :: This is a table which logs newsletters sent
    c_db.execute(
        'CREATE TABLE IF NOT EXISTS newsletter_log (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp INTEGER, '
        'newsletter_id INTEGER, agent_id INTEGER, agent_name TEXT, notify_action TEXT, '
        'subject_text TEXT, body_text TEXT, message_text TEXT, start_date TEXT, end_date TEXT, '
        'start_time INTEGER, end_time INTEGER, uuid TEXT UNIQUE, filename TEXT, email_msg_id TEXT, '
        'success INTEGER DEFAULT 0)'
    )

    # recently_added table :: This table keeps record of recently added items
    c_db.execute(
        'CREATE TABLE IF NOT EXISTS recently_added (id INTEGER PRIMARY KEY AUTOINCREMENT, '
        'added_at INTEGER, pms_identifier TEXT, section_id INTEGER, '
        'rating_key INTEGER, parent_rating_key INTEGER, grandparent_rating_key INTEGER, media_type TEXT, '
        'media_info TEXT)'
    )

    # mobile_devices table :: This table keeps record of devices linked with the mobile app
    c_db.execute(
        'CREATE TABLE IF NOT EXISTS mobile_devices (id INTEGER PRIMARY KEY AUTOINCREMENT, '
        'device_id TEXT NOT NULL UNIQUE, device_token TEXT, device_name TEXT, '
        'platform TEXT, version TEXT, friendly_name TEXT, '
        'onesignal_id TEXT, last_seen INTEGER, official INTEGER DEFAULT 0)'
    )

    # tvmaze_lookup table :: This table keeps record of the TVmaze lookups
    c_db.execute(
        'CREATE TABLE IF NOT EXISTS tvmaze_lookup (id INTEGER PRIMARY KEY AUTOINCREMENT, '
        'rating_key INTEGER, thetvdb_id INTEGER, imdb_id TEXT, '
        'tvmaze_id INTEGER, tvmaze_url TEXT, tvmaze_json TEXT)'
    )

    # themoviedb_lookup table :: This table keeps record of the TheMovieDB lookups
    c_db.execute(
        'CREATE TABLE IF NOT EXISTS themoviedb_lookup (id INTEGER PRIMARY KEY AUTOINCREMENT, '
        'rating_key INTEGER, thetvdb_id INTEGER, imdb_id TEXT, '
        'themoviedb_id INTEGER, themoviedb_url TEXT, themoviedb_json TEXT)'
    )

    # musicbrainz_lookup table :: This table keeps record of the MusicBrainz lookups
    c_db.execute(
        'CREATE TABLE IF NOT EXISTS musicbrainz_lookup (id INTEGER PRIMARY KEY AUTOINCREMENT, '
        'rating_key INTEGER, musicbrainz_id INTEGER, musicbrainz_url TEXT, musicbrainz_type TEXT, '
        'musicbrainz_json TEXT)'
    )

    # image_hash_lookup table :: This table keeps record of the image hash lookups
    c_db.execute(
        'CREATE TABLE IF NOT EXISTS image_hash_lookup (id INTEGER PRIMARY KEY AUTOINCREMENT, '
        'img_hash TEXT UNIQUE, img TEXT, rating_key INTEGER, width INTEGER, height INTEGER, '
        'opacity INTEGER, background TEXT, blur INTEGER, fallback TEXT)'
    )

    # imgur_lookup table :: This table keeps record of the Imgur uploads
    c_db.execute(
        'CREATE TABLE IF NOT EXISTS imgur_lookup (id INTEGER PRIMARY KEY AUTOINCREMENT, '
        'img_hash TEXT, imgur_title TEXT, imgur_url TEXT, delete_hash TEXT)'
    )

    # cloudinary_lookup table :: This table keeps record of the Cloudinary uploads
    c_db.execute(
        'CREATE TABLE IF NOT EXISTS cloudinary_lookup (id INTEGER PRIMARY KEY AUTOINCREMENT, '
        'img_hash TEXT, cloudinary_title TEXT, cloudinary_url TEXT)'
    )

    # exports table :: This table keeps record of the exported files
    c_db.execute(
        'CREATE TABLE IF NOT EXISTS exports (id INTEGER PRIMARY KEY AUTOINCREMENT, '
        'timestamp INTEGER, section_id INTEGER, user_id INTEGER, rating_key INTEGER, media_type TEXT, '
        'title TEXT, file_format TEXT, '
        'metadata_level INTEGER, media_info_level INTEGER, '
        'thumb_level INTEGER DEFAULT 0, art_level INTEGER DEFAULT 0, '
        'custom_fields TEXT, individual_files INTEGER DEFAULT 0, '
        'file_size INTEGER DEFAULT 0, complete INTEGER DEFAULT 0, '
        'exported_items INTEGER DEFAULT 0, total_items INTEGER DEFAULT 0)'
    )

    # Upgrade sessions table from earlier versions
    try:
        c_db.execute('SELECT started FROM sessions')
    except sqlite3.OperationalError:
        logger.debug("Altering database. Updating database table sessions.")
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN started INTEGER'
        )
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN paused_counter INTEGER DEFAULT 0'
        )
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN state TEXT'
        )
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN user TEXT'
        )
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN machine_id TEXT'
        )

    # Upgrade sessions table from earlier versions
    try:
        c_db.execute('SELECT title FROM sessions')
    except sqlite3.OperationalError:
        logger.debug("Altering database. Updating database table sessions.")
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN title TEXT'
        )
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN parent_title TEXT'
        )
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN grandparent_title TEXT'
        )
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN friendly_name TEXT'
        )
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN player TEXT'
        )
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN user_id INTEGER'
        )

    # Upgrade sessions table from earlier versions
    try:
        c_db.execute('SELECT ip_address FROM sessions')
    except sqlite3.OperationalError:
        logger.debug("Altering database. Updating database table sessions.")
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN ip_address TEXT'
        )
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN platform TEXT'
        )
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN parent_rating_key INTEGER'
        )
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN grandparent_rating_key INTEGER'
        )
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN view_offset INTEGER DEFAULT 0'
        )
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN duration INTEGER'
        )
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN video_decision TEXT'
        )
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN audio_decision TEXT'
        )
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN width INTEGER'
        )
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN height INTEGER'
        )
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN container TEXT'
        )
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN video_codec TEXT'
        )
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN audio_codec TEXT'
        )
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN bitrate INTEGER'
        )
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN video_resolution TEXT'
        )
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN video_framerate TEXT'
        )
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN aspect_ratio TEXT'
        )
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN audio_channels INTEGER'
        )
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN transcode_protocol TEXT'
        )
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN transcode_container TEXT'
        )
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN transcode_video_codec TEXT'
        )
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN transcode_audio_codec TEXT'
        )
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN transcode_audio_channels INTEGER'
        )
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN transcode_width INTEGER'
        )
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN transcode_height INTEGER'
        )

    # Upgrade sessions table from earlier versions
    try:
        c_db.execute('SELECT buffer_count FROM sessions')
    except sqlite3.OperationalError:
        logger.debug("Altering database. Updating database table sessions.")
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN buffer_count INTEGER DEFAULT 0'
        )
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN buffer_last_triggered INTEGER'
        )

    # Upgrade sessions table from earlier versions
    try:
        c_db.execute('SELECT last_paused FROM sessions')
    except sqlite3.OperationalError:
        logger.debug("Altering database. Updating database table sessions.")
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN last_paused INTEGER'
        )

    # Upgrade sessions table from earlier versions
    try:
        c_db.execute('SELECT section_id FROM sessions')
    except sqlite3.OperationalError:
        logger.debug("Altering database. Updating database table sessions.")
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN section_id INTEGER'
        )

    # Upgrade sessions table from earlier versions
    try:
        c_db.execute('SELECT stopped FROM sessions')
    except sqlite3.OperationalError:
        logger.debug("Altering database. Updating database table sessions.")
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN stopped INTEGER'
        )

    # Upgrade sessions table from earlier versions
    try:
        c_db.execute('SELECT transcode_key FROM sessions')
    except sqlite3.OperationalError:
        logger.debug("Altering database. Updating database table sessions.")
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN transcode_key TEXT'
        )

    # Upgrade sessions table from earlier versions
    try:
        c_db.execute('SELECT write_attempts FROM sessions')
    except sqlite3.OperationalError:
        logger.debug("Altering database. Updating database table sessions.")
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN write_attempts INTEGER DEFAULT 0'
        )

    # Upgrade sessions table from earlier versions
    try:
        c_db.execute('SELECT transcode_decision FROM sessions')
    except sqlite3.OperationalError:
        logger.debug("Altering database. Updating database table sessions.")
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN transcode_decision TEXT'
        )
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN full_title TEXT'
        )
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN media_index INTEGER'
        )
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN parent_media_index INTEGER'
        )
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN thumb TEXT'
        )
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN parent_thumb TEXT'
        )
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN grandparent_thumb TEXT'
        )
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN year INTEGER'
        )

    # Upgrade sessions table from earlier versions
    try:
        c_db.execute('SELECT raw_stream_info FROM sessions')
    except sqlite3.OperationalError:
        logger.debug("Altering database. Updating database table sessions.")
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN product TEXT'
        )
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN optimized_version INTEGER'
        )
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN optimized_version_profile TEXT'
        )
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN synced_version INTEGER'
        )
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN video_bitrate INTEGER'
        )
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN video_width INTEGER'
        )
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN video_height INTEGER'
        )
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN audio_bitrate INTEGER'
        )
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN subtitle_codec TEXT'
        )
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN stream_bitrate INTEGER'
        )
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN stream_video_resolution TEXT'
        )
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN quality_profile TEXT'
        )
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN stream_container_decision TEXT'
        )
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN stream_container TEXT'
        )
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN stream_video_decision TEXT'
        )
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN stream_video_codec TEXT'
        )
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN stream_video_bitrate INTEGER'
        )
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN stream_video_width INTEGER'
        )
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN stream_video_height INTEGER'
        )
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN stream_video_framerate TEXT'
        )
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN stream_audio_decision TEXT'
        )
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN stream_audio_codec TEXT'
        )
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN stream_audio_bitrate INTEGER'
        )
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN stream_audio_channels INTEGER'
        )
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN subtitles INTEGER'
        )
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN stream_subtitle_decision TEXT'
        )
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN stream_subtitle_codec TEXT'
        )
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN raw_stream_info TEXT'
        )

    # Upgrade sessions table from earlier versions
    try:
        c_db.execute('SELECT video_height FROM sessions')
    except sqlite3.OperationalError:
        logger.debug("Altering database. Updating database table sessions.")
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN video_height INTEGER'
        )

    # Upgrade sessions table from earlier versions
    try:
        c_db.execute('SELECT subtitles FROM sessions')
    except sqlite3.OperationalError:
        logger.debug("Altering database. Updating database table sessions.")
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN subtitles INTEGER'
        )

    # Upgrade sessions table from earlier versions
    try:
        c_db.execute('SELECT synced_version_profile FROM sessions')
    except sqlite3.OperationalError:
        logger.debug("Altering database. Updating database table sessions.")
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN synced_version_profile TEXT'
        )
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN optimized_version_title TEXT'
        )

    # Upgrade sessions table from earlier versions
    try:
        c_db.execute('SELECT transcode_hw_decoding FROM sessions')
    except sqlite3.OperationalError:
        logger.debug("Altering database. Updating database table sessions.")
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN transcode_hw_decoding INTEGER'
        )
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN transcode_hw_encoding INTEGER'
        )

    # Upgrade sessions table from earlier versions
    try:
        c_db.execute('SELECT watched FROM sessions')
    except sqlite3.OperationalError:
        logger.debug("Altering database. Updating database table sessions.")
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN watched INTEGER DEFAULT 0'
        )

    # Upgrade sessions table from earlier versions
    try:
        c_db.execute('SELECT live FROM sessions')
    except sqlite3.OperationalError:
        logger.debug("Altering database. Updating database table sessions.")
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN live INTEGER'
        )
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN live_uuid TEXT'
        )

    # Upgrade sessions table from earlier versions
    try:
        c_db.execute('SELECT session_id FROM sessions')
    except sqlite3.OperationalError:
        logger.debug("Altering database. Updating database table sessions.")
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN session_id TEXT'
        )

    # Upgrade sessions table from earlier versions
    try:
        c_db.execute('SELECT original_title FROM sessions')
    except sqlite3.OperationalError:
        logger.debug("Altering database. Updating database table sessions.")
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN original_title TEXT'
        )

    # Upgrade sessions table from earlier versions
    try:
        c_db.execute('SELECT secure FROM sessions')
    except sqlite3.OperationalError:
        logger.debug("Altering database. Updating database table sessions.")
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN secure INTEGER'
        )
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN relayed INTEGER'
        )

    # Upgrade sessions table from earlier versions
    try:
        c_db.execute('SELECT rating_key_websocket FROM sessions')
    except sqlite3.OperationalError:
        logger.debug("Altering database. Updating database table sessions.")
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN rating_key_websocket TEXT'
        )

    # Upgrade sessions table from earlier versions
    try:
        c_db.execute('SELECT video_scan_type FROM sessions')
    except sqlite3.OperationalError:
        logger.debug("Altering database. Updating database table sessions.")
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN video_scan_type TEXT'
        )
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN video_full_resolution TEXT'
        )
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN stream_video_scan_type TEXT'
        )
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN stream_video_full_resolution TEXT'
        )

    # Upgrade sessions table from earlier versions
    try:
        c_db.execute('SELECT video_dynamic_range FROM sessions')
    except sqlite3.OperationalError:
        logger.debug("Altering database. Updating database table sessions.")
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN video_dynamic_range TEXT'
        )
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN stream_video_dynamic_range TEXT'
        )

    # Upgrade sessions table from earlier versions
    try:
        c_db.execute('SELECT channel_identifier FROM sessions')
    except sqlite3.OperationalError:
        logger.debug("Altering database. Updating database table sessions.")
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN channel_call_sign TEXT'
        )
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN channel_identifier TEXT'
        )
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN channel_thumb TEXT'
        )

    # Upgrade sessions table from earlier versions
    try:
        c_db.execute('SELECT originally_available_at FROM sessions')
    except sqlite3.OperationalError:
        logger.debug("Altering database. Updating database table sessions.")
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN originally_available_at TEXT'
        )
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN added_at INTEGER'
        )

    # Upgrade sessions table from earlier versions
    try:
        c_db.execute('SELECT guid FROM sessions')
    except sqlite3.OperationalError:
        logger.debug("Altering database. Updating database table sessions.")
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN guid TEXT'
        )

    # Upgrade sessions table from earlier versions
    try:
        c_db.execute('SELECT bandwidth FROM sessions')
    except sqlite3.OperationalError:
        logger.debug(u"Altering database. Updating database table sessions.")
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN bandwidth INTEGER'
        )
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN location TEXT'
        )

    # Upgrade sessions table from earlier versions
    try:
        c_db.execute('SELECT initial_stream FROM sessions')
    except sqlite3.OperationalError:
        logger.debug(u"Altering database. Updating database table sessions.")
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN initial_stream INTEGER DEFAULT 1'
        )

    # Upgrade sessions table from earlier versions
    try:
        c_db.execute('SELECT audio_language FROM sessions')
    except sqlite3.OperationalError:
        logger.debug(u"Altering database. Updating database table sessions.")
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN audio_language TEXT'
        )
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN audio_language_code TEXT'
        )
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN stream_audio_language TEXT'
        )
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN stream_audio_language_code TEXT'
        )

    # Upgrade session_history table from earlier versions
    try:
        c_db.execute('SELECT reference_id FROM session_history')
    except sqlite3.OperationalError:
        logger.debug("Altering database. Updating database table session_history.")
        c_db.execute(
            'ALTER TABLE session_history ADD COLUMN reference_id INTEGER DEFAULT 0'
        )
        # Set reference_id to the first row where (user_id = previous row, rating_key != previous row) and user_id = user_id
        c_db.execute(
            'UPDATE session_history ' \
            'SET reference_id = (SELECT (CASE \
             WHEN (SELECT MIN(id) FROM session_history WHERE id > ( \
                 SELECT MAX(id) FROM session_history \
                 WHERE (user_id = t1.user_id AND rating_key <> t1.rating_key AND id < t1.id)) AND user_id = t1.user_id) IS NULL \
             THEN (SELECT MIN(id) FROM session_history WHERE (user_id = t1.user_id)) \
             ELSE (SELECT MIN(id) FROM session_history WHERE id > ( \
                 SELECT MAX(id) FROM session_history \
                 WHERE (user_id = t1.user_id AND rating_key <> t1.rating_key AND id < t1.id)) AND user_id = t1.user_id) END) ' \
            'FROM session_history AS t1 ' \
            'WHERE t1.id = session_history.id) '
        )

    # Upgrade session_history table from earlier versions
    try:
        c_db.execute('SELECT bandwidth FROM session_history')
    except sqlite3.OperationalError:
        logger.debug("Altering database. Updating database table session_history.")
        c_db.execute(
            'ALTER TABLE session_history ADD COLUMN platform_version TEXT'
        )
        c_db.execute(
            'ALTER TABLE session_history ADD COLUMN product TEXT'
        )
        c_db.execute(
            'ALTER TABLE session_history ADD COLUMN product_version TEXT'
        )
        c_db.execute(
            'ALTER TABLE session_history ADD COLUMN profile TEXT'
        )
        c_db.execute(
            'ALTER TABLE session_history ADD COLUMN bandwidth INTEGER'
        )
        c_db.execute(
            'ALTER TABLE session_history ADD COLUMN location TEXT'
        )
        c_db.execute(
            'ALTER TABLE session_history ADD COLUMN quality_profile TEXT'
        )

    # Upgrade session_history table from earlier versions
    try:
        c_db.execute('SELECT secure FROM session_history')
    except sqlite3.OperationalError:
        logger.debug("Altering database. Updating database table session_history.")
        c_db.execute(
            'ALTER TABLE session_history ADD COLUMN secure INTEGER'
        )
        c_db.execute(
            'ALTER TABLE session_history ADD COLUMN relayed INTEGER'
        )

    # Upgrade session_history table from earlier versions
    try:
        result = c_db.execute('SELECT platform FROM session_history '
                              'WHERE platform = "windows"').fetchall()
        if len(result) > 0:
            logger.debug("Altering database. Capitalizing Windows platform values in session_history table.")
            c_db.execute(
                'UPDATE session_history SET platform = "Windows" WHERE platform = "windows" '
            )
    except sqlite3.OperationalError:
        logger.warn("Unable to capitalize Windows platform values in session_history table.")

    # Upgrade session_history table from earlier versions
    try:
        c_db.execute('SELECT section_id FROM session_history')
    except sqlite3.OperationalError:
        logger.debug("Altering database. Updating database table session_history.")
        c_db.execute(
            'ALTER TABLE session_history ADD COLUMN section_id INTEGER'
        )
        c_db.execute(
            'UPDATE session_history SET section_id = ('
            'SELECT section_id FROM session_history_metadata '
            'WHERE session_history_metadata.id = session_history.id)'
        )
        c_db.execute(
            'CREATE TABLE IF NOT EXISTS session_history_metadata_temp (id INTEGER PRIMARY KEY, '
            'rating_key INTEGER, parent_rating_key INTEGER, grandparent_rating_key INTEGER, '
            'title TEXT, parent_title TEXT, grandparent_title TEXT, original_title TEXT, full_title TEXT, '
            'media_index INTEGER, parent_media_index INTEGER, '
            'thumb TEXT, parent_thumb TEXT, grandparent_thumb TEXT, '
            'art TEXT, media_type TEXT, year INTEGER, originally_available_at TEXT, added_at INTEGER, updated_at INTEGER, '
            'last_viewed_at INTEGER, content_rating TEXT, summary TEXT, tagline TEXT, rating TEXT, '
            'duration INTEGER DEFAULT 0, guid TEXT, directors TEXT, writers TEXT, actors TEXT, genres TEXT, studio TEXT, '
            'labels TEXT, live INTEGER DEFAULT 0, channel_call_sign TEXT, channel_identifier TEXT, channel_thumb TEXT)'
        )
        c_db.execute(
            'INSERT INTO session_history_metadata_temp (id, rating_key, parent_rating_key, grandparent_rating_key, '
            'title, parent_title, grandparent_title, original_title, full_title, '
            'media_index, parent_media_index, '
            'thumb, parent_thumb, grandparent_thumb, '
            'art, media_type, year, originally_available_at, added_at, updated_at, '
            'last_viewed_at, content_rating, summary, tagline, rating, '
            'duration, guid, directors, writers, actors, genres, studio, '
            'labels, live, channel_call_sign, channel_identifier, channel_thumb) '
            'SELECT id, rating_key, parent_rating_key, grandparent_rating_key, '
            'title, parent_title, grandparent_title, original_title, full_title, '
            'media_index, parent_media_index, '
            'thumb, parent_thumb, grandparent_thumb, '
            'art, media_type, year, originally_available_at, added_at, updated_at, '
            'last_viewed_at, content_rating, summary, tagline, rating, '
            'duration, guid, directors, writers, actors, genres, studio, '
            'labels, live, channel_call_sign, channel_identifier, channel_thumb '
            'FROM session_history_metadata'
        )
        c_db.execute(
            'DROP TABLE session_history_metadata'
        )
        c_db.execute(
            'ALTER TABLE session_history_metadata_temp RENAME TO session_history_metadata'
        )

    # Upgrade session_history_metadata table from earlier versions
    try:
        c_db.execute('SELECT full_title FROM session_history_metadata')
    except sqlite3.OperationalError:
        logger.debug("Altering database. Updating database table session_history_metadata.")
        c_db.execute(
            'ALTER TABLE session_history_metadata ADD COLUMN full_title TEXT'
        )

    # Upgrade session_history_metadata table from earlier versions
    try:
        c_db.execute('SELECT tagline FROM session_history_metadata')
    except sqlite3.OperationalError:
        logger.debug("Altering database. Updating database table session_history_metadata.")
        c_db.execute(
            'ALTER TABLE session_history_metadata ADD COLUMN tagline TEXT'
        )

    # Upgrade session_history_metadata table from earlier versions
    try:
        c_db.execute('SELECT labels FROM session_history_metadata')
    except sqlite3.OperationalError:
        logger.debug("Altering database. Updating database table session_history_metadata.")
        c_db.execute(
            'ALTER TABLE session_history_metadata ADD COLUMN labels TEXT'
        )

    # Upgrade session_history_metadata table from earlier versions
    try:
        c_db.execute('SELECT original_title FROM session_history_metadata')
    except sqlite3.OperationalError:
        logger.debug("Altering database. Updating database table session_history_metadata.")
        c_db.execute(
            'ALTER TABLE session_history_metadata ADD COLUMN original_title TEXT'
        )

    # Upgrade session_history_metadata table from earlier versions
    try:
        c_db.execute('SELECT live FROM session_history_metadata')
    except sqlite3.OperationalError:
        logger.debug("Altering database. Updating database table session_history_metadata.")
        c_db.execute(
            'ALTER TABLE session_history_metadata ADD COLUMN live INTEGER DEFAULT 0'
        )
        c_db.execute(
            'ALTER TABLE session_history_metadata ADD COLUMN channel_call_sign TEXT'
        )
        c_db.execute(
            'ALTER TABLE session_history_metadata ADD COLUMN channel_identifier TEXT'
        )
        c_db.execute(
            'ALTER TABLE session_history_metadata ADD COLUMN channel_thumb TEXT'
        )

    # Upgrade session_history_media_info table from earlier versions
    try:
        c_db.execute('SELECT transcode_decision FROM session_history_media_info')
    except sqlite3.OperationalError:
        logger.debug("Altering database. Updating database table session_history_media_info.")
        c_db.execute(
            'ALTER TABLE session_history_media_info ADD COLUMN transcode_decision TEXT'
        )
        c_db.execute(
            'UPDATE session_history_media_info SET transcode_decision = (CASE '
            'WHEN video_decision = "transcode" OR audio_decision = "transcode" THEN "transcode" '
            'WHEN video_decision = "copy" OR audio_decision = "copy" THEN "copy" '
            'WHEN video_decision = "direct play" OR audio_decision = "direct play" THEN "direct play" END)'
        )

    # Upgrade session_history_media_info table from earlier versions
    try:
        c_db.execute('SELECT subtitles FROM session_history_media_info')
    except sqlite3.OperationalError:
        logger.debug("Altering database. Updating database table session_history_media_info.")
        c_db.execute(
            'ALTER TABLE session_history_media_info ADD COLUMN video_bit_depth INTEGER'
        )
        c_db.execute(
            'ALTER TABLE session_history_media_info ADD COLUMN video_bitrate INTEGER'
        )
        c_db.execute(
            'ALTER TABLE session_history_media_info ADD COLUMN video_codec_level TEXT'
        )
        c_db.execute(
            'ALTER TABLE session_history_media_info ADD COLUMN video_width INTEGER'
        )
        c_db.execute(
            'ALTER TABLE session_history_media_info ADD COLUMN video_height INTEGER'
        )
        c_db.execute(
            'ALTER TABLE session_history_media_info ADD COLUMN audio_bitrate INTEGER'
        )
        c_db.execute(
            'ALTER TABLE session_history_media_info ADD COLUMN transcode_hw_requested INTEGER'
        )
        c_db.execute(
            'ALTER TABLE session_history_media_info ADD COLUMN transcode_hw_full_pipeline INTEGER'
        )
        c_db.execute(
            'ALTER TABLE session_history_media_info ADD COLUMN transcode_hw_decode TEXT'
        )
        c_db.execute(
            'ALTER TABLE session_history_media_info ADD COLUMN transcode_hw_encode TEXT'
        )
        c_db.execute(
            'ALTER TABLE session_history_media_info ADD COLUMN transcode_hw_decode_title TEXT'
        )
        c_db.execute(
            'ALTER TABLE session_history_media_info ADD COLUMN transcode_hw_encode_title TEXT'
        )
        c_db.execute(
            'ALTER TABLE session_history_media_info ADD COLUMN stream_container TEXT'
        )
        c_db.execute(
            'ALTER TABLE session_history_media_info ADD COLUMN stream_container_decision TEXT'
        )
        c_db.execute(
            'ALTER TABLE session_history_media_info ADD COLUMN stream_bitrate INTEGER'
        )
        c_db.execute(
            'ALTER TABLE session_history_media_info ADD COLUMN stream_video_decision TEXT'
        )
        c_db.execute(
            'ALTER TABLE session_history_media_info ADD COLUMN stream_video_bitrate INTEGER'
        )
        c_db.execute(
            'ALTER TABLE session_history_media_info ADD COLUMN stream_video_codec TEXT'
        )
        c_db.execute(
            'ALTER TABLE session_history_media_info ADD COLUMN stream_video_codec_level TEXT'
        )
        c_db.execute(
            'ALTER TABLE session_history_media_info ADD COLUMN stream_video_bit_depth INTEGER'
        )
        c_db.execute(
            'ALTER TABLE session_history_media_info ADD COLUMN stream_video_height INTEGER'
        )
        c_db.execute(
            'ALTER TABLE session_history_media_info ADD COLUMN stream_video_width INTEGER'
        )
        c_db.execute(
            'ALTER TABLE session_history_media_info ADD COLUMN stream_video_resolution TEXT'
        )
        c_db.execute(
            'ALTER TABLE session_history_media_info ADD COLUMN stream_video_framerate TEXT'
        )
        c_db.execute(
            'ALTER TABLE session_history_media_info ADD COLUMN stream_audio_decision TEXT'
        )
        c_db.execute(
            'ALTER TABLE session_history_media_info ADD COLUMN stream_audio_codec TEXT'
        )
        c_db.execute(
            'ALTER TABLE session_history_media_info ADD COLUMN stream_audio_bitrate INTEGER'
        )
        c_db.execute(
            'ALTER TABLE session_history_media_info ADD COLUMN stream_audio_channels INTEGER'
        )
        c_db.execute(
            'ALTER TABLE session_history_media_info ADD COLUMN stream_subtitle_decision TEXT'
        )
        c_db.execute(
            'ALTER TABLE session_history_media_info ADD COLUMN stream_subtitle_codec TEXT'
        )
        c_db.execute(
            'ALTER TABLE session_history_media_info ADD COLUMN stream_subtitle_container TEXT'
        )
        c_db.execute(
            'ALTER TABLE session_history_media_info ADD COLUMN stream_subtitle_forced INTEGER'
        )
        c_db.execute(
            'ALTER TABLE session_history_media_info ADD COLUMN subtitles INTEGER'
        )
        c_db.execute(
            'ALTER TABLE session_history_media_info ADD COLUMN synced_version INTEGER'
        )
        c_db.execute(
            'ALTER TABLE session_history_media_info ADD COLUMN optimized_version INTEGER'
        )
        c_db.execute(
            'ALTER TABLE session_history_media_info ADD COLUMN optimized_version_profile TEXT'
        )
        c_db.execute(
            'UPDATE session_history_media_info SET video_resolution=REPLACE(video_resolution, "p", "")'
        )
        c_db.execute(
            'UPDATE session_history_media_info SET video_resolution=REPLACE(video_resolution, "SD", "sd")'
        )

    # Upgrade session_history_media_info table from earlier versions
    try:
        c_db.execute('SELECT subtitle_codec FROM session_history_media_info')
    except sqlite3.OperationalError:
        logger.debug("Altering database. Updating database table session_history_media_info.")
        c_db.execute(
            'ALTER TABLE session_history_media_info ADD COLUMN subtitle_codec TEXT'
        )

    # Upgrade session_history_media_info table from earlier versions
    try:
        c_db.execute('SELECT synced_version_profile FROM session_history_media_info')
    except sqlite3.OperationalError:
        logger.debug("Altering database. Updating database table session_history_media_info.")
        c_db.execute(
            'ALTER TABLE session_history_media_info ADD COLUMN synced_version_profile TEXT'
        )
        c_db.execute(
            'ALTER TABLE session_history_media_info ADD COLUMN optimized_version_title TEXT'
        )

    # Upgrade session_history_media_info table from earlier versions
    try:
        c_db.execute('SELECT transcode_hw_decoding FROM session_history_media_info')
    except sqlite3.OperationalError:
        logger.debug("Altering database. Updating database table session_history_media_info.")
        c_db.execute(
            'ALTER TABLE session_history_media_info ADD COLUMN transcode_hw_decoding INTEGER'
        )
        c_db.execute(
            'ALTER TABLE session_history_media_info ADD COLUMN transcode_hw_encoding INTEGER'
        )
        c_db.execute(
            'UPDATE session_history_media_info SET subtitle_codec = "" WHERE subtitle_codec IS NULL'
        )

    # Upgrade session_history_media_info table from earlier versions
    try:
        result = c_db.execute('SELECT stream_container FROM session_history_media_info '
                              'WHERE stream_container IS NULL').fetchall()
        if len(result) > 0:
            logger.debug("Altering database. Removing NULL values from session_history_media_info table.")
            c_db.execute(
                'UPDATE session_history_media_info SET stream_container = "" WHERE stream_container IS NULL'
            )
            c_db.execute(
                'UPDATE session_history_media_info SET stream_video_codec = "" WHERE stream_video_codec IS NULL'
            )
            c_db.execute(
                'UPDATE session_history_media_info SET stream_audio_codec = "" WHERE stream_audio_codec IS NULL'
            )
            c_db.execute(
                'UPDATE session_history_media_info SET stream_subtitle_codec = "" WHERE stream_subtitle_codec IS NULL'
            )
    except sqlite3.OperationalError:
        logger.warn("Unable to remove NULL values from session_history_media_info table.")

    # Upgrade session_history_media_info table from earlier versions
    try:
        c_db.execute('SELECT video_scan_type FROM session_history_media_info')
    except sqlite3.OperationalError:
        logger.debug("Altering database. Updating database table session_history_media_info.")
        c_db.execute(
            'ALTER TABLE session_history_media_info ADD COLUMN video_scan_type TEXT'
        )
        c_db.execute(
            'ALTER TABLE session_history_media_info ADD COLUMN video_full_resolution TEXT'
        )
        c_db.execute(
            'ALTER TABLE session_history_media_info ADD COLUMN stream_video_scan_type TEXT'
        )
        c_db.execute(
            'ALTER TABLE session_history_media_info ADD COLUMN stream_video_full_resolution TEXT'
        )
        c_db.execute(
            'UPDATE session_history_media_info SET video_scan_type = "progressive" '
            'WHERE video_resolution != ""'
        )
        c_db.execute(
            'UPDATE session_history_media_info SET stream_video_scan_type = "progressive" '
            'WHERE stream_video_resolution != "" AND stream_video_resolution IS NOT NULL'
        )
        c_db.execute(
            'UPDATE session_history_media_info SET video_full_resolution = (CASE '
            'WHEN video_resolution = "" OR video_resolution = "SD" OR video_resolution = "4k" THEN video_resolution '
            'WHEN video_resolution = "sd" THEN "SD" '
            'ELSE video_resolution || "p" END)'
        )
        c_db.execute(
            'UPDATE session_history_media_info SET stream_video_full_resolution = ( '
            'CASE WHEN stream_video_resolution = "" OR stream_video_resolution = "SD" OR stream_video_resolution = "4k" '
            'THEN stream_video_resolution '
            'WHEN stream_video_resolution = "sd" THEN "SD" '
            'ELSE stream_video_resolution || "p" END)'
        )

    # Upgrade session_history_media_info table from earlier versions
    try:
        c_db.execute('SELECT video_dynamic_range FROM session_history_media_info')
    except sqlite3.OperationalError:
        logger.debug("Altering database. Updating database table session_history_media_info.")
        c_db.execute(
            'ALTER TABLE session_history_media_info ADD COLUMN video_dynamic_range TEXT'
        )
        c_db.execute(
            'ALTER TABLE session_history_media_info ADD COLUMN stream_video_dynamic_range TEXT'
        )

    result = c_db.execute('SELECT * FROM session_history_media_info '
                          'WHERE video_dynamic_range = "SDR" AND stream_video_dynamic_range = "HDR"').fetchone()
    if result:
        c_db.execute(
            'UPDATE session_history_media_info SET stream_video_dynamic_range = "SDR" '
            'WHERE video_dynamic_range = "SDR" AND stream_video_dynamic_range = "HDR"'
        )
    
    # Upgrade session_history_media_info table from earlier versions
    try:
        c_db.execute('SELECT audio_language FROM session_history_media_info')
    except sqlite3.OperationalError:
        logger.debug("Altering database. Updating database table session_history_media_info.")
        c_db.execute(
            'ALTER TABLE session_history_media_info ADD COLUMN audio_language TEXT'
        )
        c_db.execute(
            'ALTER TABLE session_history_media_info ADD COLUMN audio_language_code TEXT'
        )
        c_db.execute(
            'ALTER TABLE session_history_media_info ADD COLUMN stream_audio_language TEXT'
        )
        c_db.execute(
            'ALTER TABLE session_history_media_info ADD COLUMN stream_audio_language_code TEXT'
        ) 
    
    # Upgrade users table from earlier versions
    try:
        c_db.execute('SELECT do_notify FROM users')
    except sqlite3.OperationalError:
        logger.debug("Altering database. Updating database table users.")
        c_db.execute(
            'ALTER TABLE users ADD COLUMN do_notify INTEGER DEFAULT 1'
        )

    # Upgrade users table from earlier versions
    try:
        c_db.execute('SELECT keep_history FROM users')
    except sqlite3.OperationalError:
        logger.debug("Altering database. Updating database table users.")
        c_db.execute(
            'ALTER TABLE users ADD COLUMN keep_history INTEGER DEFAULT 1'
        )

    # Upgrade users table from earlier versions
    try:
        c_db.execute('SELECT custom_avatar_url FROM users')
    except sqlite3.OperationalError:
        logger.debug("Altering database. Updating database table users.")
        c_db.execute(
            'ALTER TABLE users ADD COLUMN custom_avatar_url TEXT'
        )

    # Upgrade users table from earlier versions
    try:
        c_db.execute('SELECT deleted_user FROM users')
    except sqlite3.OperationalError:
        logger.debug("Altering database. Updating database table users.")
        c_db.execute(
            'ALTER TABLE users ADD COLUMN deleted_user INTEGER DEFAULT 0'
        )

    # Upgrade users table from earlier versions
    try:
        c_db.execute('SELECT allow_guest FROM users')
    except sqlite3.OperationalError:
        logger.debug("Altering database. Updating database table users.")
        c_db.execute(
            'ALTER TABLE users ADD COLUMN allow_guest INTEGER DEFAULT 0'
        )
        c_db.execute(
            'ALTER TABLE users ADD COLUMN user_token TEXT'
        )
        c_db.execute(
            'ALTER TABLE users ADD COLUMN server_token TEXT'
        )

    # Upgrade users table from earlier versions
    try:
        c_db.execute('SELECT shared_libraries FROM users')
    except sqlite3.OperationalError:
        logger.debug("Altering database. Updating database table users.")
        c_db.execute(
            'ALTER TABLE users ADD COLUMN shared_libraries TEXT'
        )
        c_db.execute(
            'ALTER TABLE users ADD COLUMN filter_all TEXT'
        )
        c_db.execute(
            'ALTER TABLE users ADD COLUMN filter_movies TEXT'
        )
        c_db.execute(
            'ALTER TABLE users ADD COLUMN filter_tv TEXT'
        )
        c_db.execute(
            'ALTER TABLE users ADD COLUMN filter_music TEXT'
        )
        c_db.execute(
            'ALTER TABLE users ADD COLUMN filter_photos TEXT'
        )

    # Upgrade users table from earlier versions
    try:
        c_db.execute('SELECT is_admin FROM users')
    except sqlite3.OperationalError:
        logger.debug("Altering database. Updating database table users.")
        c_db.execute(
            'ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0'
        )

    # Upgrade users table from earlier versions
    try:
        c_db.execute('SELECT is_active FROM users')
    except sqlite3.OperationalError:
        logger.debug("Altering database. Updating database table users.")
        c_db.execute(
            'ALTER TABLE users ADD COLUMN is_active INTEGER DEFAULT 1'
        )

    # Upgrade notify_log table from earlier versions
    try:
        c_db.execute('SELECT poster_url FROM notify_log')
    except sqlite3.OperationalError:
        logger.debug("Altering database. Updating database table notify_log.")
        c_db.execute(
            'ALTER TABLE notify_log ADD COLUMN poster_url TEXT'
        )

    # Upgrade notify_log table from earlier versions (populate table with data from notify_log)
    try:
        c_db.execute('SELECT timestamp FROM notify_log')
    except sqlite3.OperationalError:
        logger.debug("Altering database. Updating database table notify_log.")
        c_db.execute(
            'CREATE TABLE IF NOT EXISTS notify_log_temp (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp INTEGER, '
            'session_key INTEGER, rating_key INTEGER, parent_rating_key INTEGER, grandparent_rating_key INTEGER, '
            'user_id INTEGER, user TEXT, agent_id INTEGER, agent_name TEXT, notify_action TEXT, '
            'subject_text TEXT, body_text TEXT, script_args TEXT, poster_url TEXT)'
        )
        c_db.execute(
            'INSERT INTO notify_log_temp (session_key, rating_key, user_id, user, agent_id, agent_name, '
            'poster_url, timestamp, notify_action) '
            'SELECT session_key, rating_key, user_id, user, agent_id, agent_name, poster_url, timestamp, '
            'notify_action FROM notify_log_temp '
            'UNION ALL SELECT session_key, rating_key, user_id, user, agent_id, agent_name, poster_url, '
            'on_play, "play" FROM notify_log WHERE on_play '
            'UNION ALL SELECT session_key, rating_key, user_id, user, agent_id, agent_name, poster_url, '
            'on_stop, "stop" FROM notify_log WHERE on_stop '
            'UNION ALL SELECT session_key, rating_key, user_id, user, agent_id, agent_name, poster_url, '
            'on_watched, "watched" FROM notify_log WHERE on_watched '
            'UNION ALL SELECT session_key, rating_key, user_id, user, agent_id, agent_name, poster_url, '
            'on_pause, "pause" FROM notify_log WHERE on_pause '
            'UNION ALL SELECT session_key, rating_key, user_id, user, agent_id, agent_name, poster_url, '
            'on_resume, "resume" FROM notify_log WHERE on_resume '
            'UNION ALL SELECT session_key, rating_key, user_id, user, agent_id, agent_name, poster_url, '
            'on_buffer, "buffer" FROM notify_log WHERE on_buffer '
            'UNION ALL SELECT session_key, rating_key, user_id, user, agent_id, agent_name, poster_url, '
            'on_created, "created" FROM notify_log WHERE on_created '
            'ORDER BY timestamp ')
        c_db.execute(
            'DROP TABLE notify_log'
        )
        c_db.execute(
            'ALTER TABLE notify_log_temp RENAME TO notify_log'
        )

    # Upgrade notify_log table from earlier versions
    try:
        c_db.execute('SELECT notifier_id FROM notify_log')
    except sqlite3.OperationalError:
        logger.debug("Altering database. Updating database table notify_log.")
        c_db.execute(
            'ALTER TABLE notify_log ADD COLUMN notifier_id INTEGER'
        )

    # Upgrade notify_log table from earlier versions
    try:
        c_db.execute('SELECT success FROM notify_log')
    except sqlite3.OperationalError:
        logger.debug("Altering database. Updating database table notify_log.")
        c_db.execute(
            'ALTER TABLE notify_log ADD COLUMN success INTEGER DEFAULT 0'
        )
        c_db.execute(
            'UPDATE notify_log SET success = 1'
        )

    # Upgrade notify_log table from earlier versions
    try:
        c_db.execute('SELECT tag FROM notify_log')
    except sqlite3.OperationalError:
        logger.debug("Altering database. Updating database table notify_log.")
        c_db.execute(
            'ALTER TABLE notify_log ADD COLUMN tag TEXT'
        )

    # Upgrade newsletter_log table from earlier versions
    try:
        c_db.execute('SELECT start_time FROM newsletter_log')
    except sqlite3.OperationalError:
        logger.debug("Altering database. Updating database table newsletter_log.")
        c_db.execute(
            'ALTER TABLE newsletter_log ADD COLUMN start_time INTEGER'
        )
        c_db.execute(
            'ALTER TABLE newsletter_log ADD COLUMN end_time INTEGER'
        )

    # Upgrade newsletter_log table from earlier versions
    try:
        c_db.execute('SELECT filename FROM newsletter_log')
    except sqlite3.OperationalError:
        logger.debug("Altering database. Updating database table newsletter_log.")
        c_db.execute(
            'ALTER TABLE newsletter_log ADD COLUMN filename TEXT'
        )

    # Upgrade newsletter_log table from earlier versions
    try:
        c_db.execute('SELECT email_msg_id FROM newsletter_log')
    except sqlite3.OperationalError:
        logger.debug("Altering database. Updating database table newsletter_log.")
        c_db.execute(
            'ALTER TABLE newsletter_log ADD COLUMN email_msg_id TEXT'
        )

    # Upgrade newsletters table from earlier versions
    try:
        c_db.execute('SELECT id_name FROM newsletters')
    except sqlite3.OperationalError:
        logger.debug("Altering database. Updating database table newsletters.")
        c_db.execute(
            'ALTER TABLE newsletters ADD COLUMN id_name TEXT NOT NULL'
        )

    # Upgrade newsletters table from earlier versions
    try:
        result = c_db.execute('SELECT SQL FROM sqlite_master WHERE type="table" AND name="newsletters"').fetchone()
        if '"cron"\tTEXT NOT NULL DEFAULT "0 0 * * 0"' in result[0]:
            logger.debug("Altering database. Updating default cron value in newsletters table.")
            c_db.execute(
                'CREATE TABLE newsletters_temp (id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'agent_id INTEGER, agent_name TEXT, agent_label TEXT, id_name TEXT NOT NULL, '
                'friendly_name TEXT, newsletter_config TEXT, email_config TEXT, '
                'subject TEXT, body TEXT, message TEXT, '
                'cron TEXT NOT NULL DEFAULT \'0 0 * * 0\', active INTEGER DEFAULT 0)'
            )
            c_db.execute(
                'INSERT INTO newsletters_temp (id, agent_id, agent_name, agent_label, id_name, '
                'friendly_name, newsletter_config, email_config, subject, body, message, cron, active) '
                'SELECT id, agent_id, agent_name, agent_label, id_name, '
                'friendly_name, newsletter_config, email_config, subject, body, message, cron, active '
                'FROM newsletters'
            )
            c_db.execute(
                'DROP TABLE newsletters'
            )
            c_db.execute(
                'ALTER TABLE newsletters_temp RENAME TO newsletters'
            )
    except sqlite3.OperationalError:
        logger.warn("Unable to update default cron value in newsletters table.")
        try:
            c_db.execute(
                'DROP TABLE newsletters_temp'
            )
        except:
            pass

    # Upgrade library_sections table from earlier versions (remove UNIQUE constraint on section_id)
    try:
        result = c_db.execute('SELECT SQL FROM sqlite_master WHERE type="table" AND name="library_sections"').fetchone()
        if 'section_id INTEGER UNIQUE' in result[0]:
            logger.debug("Altering database. Removing unique constraint on section_id from library_sections table.")
            c_db.execute(
                'CREATE TABLE library_sections_temp (id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'server_id TEXT, section_id INTEGER, section_name TEXT, section_type TEXT, '
                'thumb TEXT, custom_thumb_url TEXT, art TEXT, count INTEGER, parent_count INTEGER, child_count INTEGER, '
                'do_notify INTEGER DEFAULT 1, do_notify_created INTEGER DEFAULT 1, keep_history INTEGER DEFAULT 1, '
                'deleted_section INTEGER DEFAULT 0, UNIQUE(server_id, section_id))'
            )
            c_db.execute(
                'INSERT INTO library_sections_temp (id, server_id, section_id, section_name, section_type, '
                'thumb, custom_thumb_url, art, count, parent_count, child_count, do_notify, do_notify_created, '
                'keep_history, deleted_section) '
                'SELECT id, server_id, section_id, section_name, section_type, '
                'thumb, custom_thumb_url, art, count, parent_count, child_count, do_notify, do_notify_created, '
                'keep_history, deleted_section '
                'FROM library_sections'
            )
            c_db.execute(
                'DROP TABLE library_sections'
            )
            c_db.execute(
                'ALTER TABLE library_sections_temp RENAME TO library_sections'
            )
    except sqlite3.OperationalError:
        logger.warn("Unable to remove section_id unique constraint from library_sections.")
        try:
            c_db.execute(
                'DROP TABLE library_sections_temp'
            )
        except:
            pass

    # Upgrade library_sections table from earlier versions (remove duplicated libraries)
    try:
        result = c_db.execute('SELECT * FROM library_sections WHERE server_id = ""').fetchall()
        if len(result) > 0:
            logger.debug("Altering database. Removing duplicate libraries from library_sections table.")
            c_db.execute(
                'DELETE FROM library_sections WHERE server_id = ""'
            )
    except sqlite3.OperationalError:
        logger.warn("Unable to remove duplicate libraries from library_sections table.")

    # Upgrade library_sections table from earlier versions
    try:
        c_db.execute('SELECT agent FROM library_sections')
    except sqlite3.OperationalError:
        logger.debug("Altering database. Updating database table library_sections.")
        c_db.execute(
            'ALTER TABLE library_sections ADD COLUMN agent TEXT'
        )

    # Upgrade library_sections table from earlier versions
    try:
        c_db.execute('SELECT custom_art_url FROM library_sections')
    except sqlite3.OperationalError:
        logger.debug("Altering database. Updating database table library_sections.")
        c_db.execute(
            'ALTER TABLE library_sections ADD COLUMN custom_art_url TEXT'
        )

    # Upgrade library_sections table from earlier versions
    try:
        c_db.execute('SELECT is_active FROM library_sections')
    except sqlite3.OperationalError:
        logger.debug("Altering database. Updating database table library_sections.")
        c_db.execute(
            'ALTER TABLE library_sections ADD COLUMN is_active INTEGER DEFAULT 1'
        )

    # Upgrade library_sections table from earlier versions
    try:
        result = c_db.execute('SELECT thumb, art FROM library_sections WHERE section_id = ?',
                              [common.LIVE_TV_SECTION_ID]).fetchone()
        if result and (not result[0] or not result[1]):
            logger.debug("Altering database. Updating database table library_sections.")
            c_db.execute('UPDATE library_sections SET thumb = ?, art =? WHERE section_id = ?',
                         [common.DEFAULT_LIVE_TV_THUMB,
                          common.DEFAULT_LIVE_TV_ART_FULL,
                          common.LIVE_TV_SECTION_ID])
    except sqlite3.OperationalError:
        pass

    # Upgrade users table from earlier versions (remove UNIQUE constraint on username)
    try:
        result = c_db.execute('SELECT SQL FROM sqlite_master WHERE type="table" AND name="users"').fetchone()
        if 'username TEXT NOT NULL UNIQUE' in result[0]:
            logger.debug("Altering database. Removing unique constraint on username from users table.")
            c_db.execute(
                'CREATE TABLE users_temp (id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'user_id INTEGER DEFAULT NULL UNIQUE, username TEXT NOT NULL, friendly_name TEXT, '
                'thumb TEXT, custom_avatar_url TEXT, email TEXT, is_home_user INTEGER DEFAULT NULL, '
                'is_allow_sync INTEGER DEFAULT NULL, is_restricted INTEGER DEFAULT NULL, do_notify INTEGER DEFAULT 1, '
                'keep_history INTEGER DEFAULT 1, deleted_user INTEGER DEFAULT 0)'
            )
            c_db.execute(
                'INSERT INTO users_temp (id, user_id, username, friendly_name, thumb, custom_avatar_url, '
                'email, is_home_user, is_allow_sync, is_restricted, do_notify, keep_history, deleted_user) '
                'SELECT id, user_id, username, friendly_name, thumb, custom_avatar_url, '
                'email, is_home_user, is_allow_sync, is_restricted, do_notify, keep_history, deleted_user '
                'FROM users'
            )
            c_db.execute(
                'DROP TABLE users'
            )
            c_db.execute(
                'ALTER TABLE users_temp RENAME TO users'
            )
    except sqlite3.OperationalError:
        logger.warn("Unable to remove username unique constraint from users.")
        try:
            c_db.execute(
                'DROP TABLE users_temp'
            )
        except:
            pass

    # Upgrade mobile_devices table from earlier versions
    try:
        result = c_db.execute('SELECT SQL FROM sqlite_master WHERE type="table" AND name="mobile_devices"').fetchone()
        if 'device_token TEXT NOT NULL UNIQUE' in result[0]:
            logger.debug("Altering database. Dropping and recreating mobile_devices table.")
            c_db.execute(
                'DROP TABLE mobile_devices'
            )
            c_db.execute(
                'CREATE TABLE IF NOT EXISTS mobile_devices (id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'device_id TEXT NOT NULL UNIQUE, device_token TEXT, device_name TEXT, friendly_name TEXT)'
            )
    except sqlite3.OperationalError:
        logger.warn("Failed to recreate mobile_devices table.")
        pass

    # Upgrade mobile_devices table from earlier versions
    try:
        c_db.execute('SELECT last_seen FROM mobile_devices')
    except sqlite3.OperationalError:
        logger.debug("Altering database. Updating database table mobile_devices.")
        c_db.execute(
            'ALTER TABLE mobile_devices ADD COLUMN last_seen INTEGER'
        )

    # Upgrade mobile_devices table from earlier versions
    try:
        c_db.execute('SELECT official FROM mobile_devices')
    except sqlite3.OperationalError:
        logger.debug("Altering database. Updating database table mobile_devices.")
        c_db.execute(
            'ALTER TABLE mobile_devices ADD COLUMN official INTEGER DEFAULT 0'
        )
        # Update official mobile device flag
        for device_id, in c_db.execute('SELECT device_id FROM mobile_devices').fetchall():
            c_db.execute('UPDATE mobile_devices SET official = ? WHERE device_id = ?',
                         [mobile_app.validate_onesignal_id(device_id), device_id])

    # Upgrade mobile_devices table from earlier versions
    try:
        c_db.execute('SELECT onesignal_id FROM mobile_devices')
    except sqlite3.OperationalError:
        logger.debug("Altering database. Updating database table mobile_devices.")
        c_db.execute(
            'ALTER TABLE mobile_devices ADD COLUMN onesignal_id TEXT'
        )

    # Upgrade mobile_devices table from earlier versions
    try:
        c_db.execute('SELECT platform FROM mobile_devices')
    except sqlite3.OperationalError:
        logger.debug("Altering database. Updating database table mobile_devices.")
        c_db.execute(
            'ALTER TABLE mobile_devices ADD COLUMN platform TEXT'
        )
        c_db.execute(
            'ALTER TABLE mobile_devices ADD COLUMN version TEXT'
        )
        # Update mobile device platforms
        for device_id, in c_db.execute(
                'SELECT device_id FROM mobile_devices WHERE official > 0').fetchall():
            c_db.execute('UPDATE mobile_devices SET platform = ? WHERE device_id = ?',
                         ['android', device_id])

    # Upgrade notifiers table from earlier versions
    try:
        c_db.execute('SELECT custom_conditions FROM notifiers')
    except sqlite3.OperationalError:
        logger.debug("Altering database. Updating database table notifiers.")
        c_db.execute(
            'ALTER TABLE notifiers ADD COLUMN custom_conditions TEXT'
        )
        c_db.execute(
            'ALTER TABLE notifiers ADD COLUMN custom_conditions_logic TEXT'
        )

    # Upgrade notifiers table from earlier versions
    try:
        c_db.execute('SELECT on_change FROM notifiers')
    except sqlite3.OperationalError:
        logger.debug("Altering database. Updating database table notifiers.")
        c_db.execute(
            'ALTER TABLE notifiers ADD COLUMN on_change INTEGER DEFAULT 0'
        )
        c_db.execute(
            'ALTER TABLE notifiers ADD COLUMN on_change_subject TEXT'
        )
        c_db.execute(
            'ALTER TABLE notifiers ADD COLUMN on_change_body TEXT'
        )

    # Upgrade notifiers table from earlier versions
    try:
        c_db.execute('SELECT on_plexpydbcorrupt FROM notifiers')
    except sqlite3.OperationalError:
        logger.debug("Altering database. Updating database table notifiers.")
        c_db.execute(
            'ALTER TABLE notifiers ADD COLUMN on_plexpydbcorrupt INTEGER DEFAULT 0'
        )
        c_db.execute(
            'ALTER TABLE notifiers ADD COLUMN on_plexpydbcorrupt_subject TEXT'
        )
        c_db.execute(
            'ALTER TABLE notifiers ADD COLUMN on_plexpydbcorrupt_body TEXT'
        )

    # Upgrade notifiers table from earlier versions
    try:
        c_db.execute('SELECT on_error FROM notifiers')
    except sqlite3.OperationalError:
        logger.debug("Altering database. Updating database table notifiers.")
        c_db.execute(
            'ALTER TABLE notifiers ADD COLUMN on_error INTEGER DEFAULT 0'
        )
        c_db.execute(
            'ALTER TABLE notifiers ADD COLUMN on_error_subject TEXT'
        )
        c_db.execute(
            'ALTER TABLE notifiers ADD COLUMN on_error_body TEXT'
        )

    # Upgrade tvmaze_lookup table from earlier versions
    try:
        c_db.execute('SELECT rating_key FROM tvmaze_lookup')
    except sqlite3.OperationalError:
        logger.debug("Altering database. Updating database table tvmaze_lookup.")
        c_db.execute(
            'ALTER TABLE tvmaze_lookup ADD COLUMN rating_key INTEGER'
        )
        c_db.execute(
            'DROP INDEX IF EXISTS idx_tvmaze_lookup_thetvdb_id'
        )
        c_db.execute(
            'DROP INDEX IF EXISTS idx_tvmaze_lookup_imdb_id'
        )

    # Upgrade themoviedb_lookup table from earlier versions
    try:
        c_db.execute('SELECT rating_key FROM themoviedb_lookup')
    except sqlite3.OperationalError:
        logger.debug("Altering database. Updating database table themoviedb_lookup.")
        c_db.execute(
            'ALTER TABLE themoviedb_lookup ADD COLUMN rating_key INTEGER'
        )
        c_db.execute(
            'DROP INDEX IF EXISTS idx_themoviedb_lookup_thetvdb_id'
        )
        c_db.execute(
            'DROP INDEX IF EXISTS idx_themoviedb_lookup_imdb_id'
        )

    # Upgrade user_login table from earlier versions
    try:
        c_db.execute('SELECT success FROM user_login')
    except sqlite3.OperationalError:
        logger.debug("Altering database. Updating database table user_login.")
        c_db.execute(
            'ALTER TABLE user_login ADD COLUMN success INTEGER DEFAULT 1'
        )

    # Upgrade user_login table from earlier versions
    try:
        c_db.execute('SELECT expiry FROM user_login')
    except sqlite3.OperationalError:
        logger.debug("Altering database. Updating database table user_login.")
        c_db.execute(
            'ALTER TABLE user_login ADD COLUMN expiry TEXT'
        )
        c_db.execute(
            'ALTER TABLE user_login ADD COLUMN jwt_token TEXT'
        )

    # Rename notifiers in the database
    result = c_db.execute('SELECT agent_label FROM notifiers '
                          'WHERE agent_label = "XBMC" '
                          'OR agent_label = "OSX Notify" '
                          'OR agent_name = "androidapp"').fetchone()
    if result:
        logger.debug("Altering database. Renaming notifiers.")
        c_db.execute(
            'UPDATE notifiers SET agent_label = "Kodi" WHERE agent_label = "XBMC"'
        )
        c_db.execute(
            'UPDATE notifiers SET agent_label = "macOS Notification Center" WHERE agent_label = "OSX Notify"'
        )
        c_db.execute(
            'UPDATE notifiers SET agent_name = "remoteapp", agent_label = "Tautulli Remote App" '
            'WHERE agent_name = "androidapp"'
        )

    # Upgrade exports table from earlier versions
    try:
        c_db.execute('SELECT thumb_level FROM exports')
    except sqlite3.OperationalError:
        logger.debug("Altering database. Updating database table exports.")
        c_db.execute(
            'ALTER TABLE exports ADD COLUMN thumb_level INTEGER DEFAULT 0'
        )
        c_db.execute(
            'UPDATE exports SET thumb_level = 9 WHERE include_thumb = 1'
        )
        c_db.execute(
            'ALTER TABLE exports ADD COLUMN art_level INTEGER DEFAULT 0'
        )
        c_db.execute(
            'UPDATE exports SET art_level = 9 WHERE include_art = 1'
        )

    # Upgrade exports table from earlier versions
    try:
        c_db.execute('SELECT title FROM exports')
    except sqlite3.OperationalError:
        logger.debug("Altering database. Updating database table exports.")
        c_db.execute(
            'ALTER TABLE exports ADD COLUMN title TEXT'
        )
        c_db.execute(
            'ALTER TABLE exports ADD COLUMN individual_files INTEGER DEFAULT 0'
        )

    # Upgrade exports table from earlier versions
    try:
        c_db.execute('SELECT total_items FROM exports')
    except sqlite3.OperationalError:
        logger.debug("Altering database. Updating database table exports.")
        c_db.execute(
            'ALTER TABLE exports ADD COLUMN exported_items INTEGER DEFAULT 0'
        )
        c_db.execute(
            'ALTER TABLE exports ADD COLUMN total_items INTEGER DEFAULT 0'
        )

    # Upgrade image_hash_lookup table from earlier versions
    try:
        c_db.execute('DELETE FROM image_hash_lookup '
                     'WHERE id NOT IN (SELECT MIN(id) FROM image_hash_lookup GROUP BY img_hash)')
    except sqlite3.OperationalError:
        pass

    # Upgrade imgur_lookup table from earlier versions
    try:
        c_db.execute('DELETE FROM imgur_lookup '
                     'WHERE id NOT IN (SELECT MIN(id) FROM imgur_lookup GROUP BY img_hash)')
    except sqlite3.OperationalError:
        pass

    # Upgrade cloudinary_lookup table from earlier versions
    try:
        c_db.execute('DELETE FROM cloudinary_lookup '
                     'WHERE id NOT IN (SELECT MIN(id) FROM cloudinary_lookup GROUP BY img_hash)')
    except sqlite3.OperationalError:
        pass

    # Add "Local" user to database as default unauthenticated user.
    result = c_db.execute('SELECT id FROM users WHERE username = "Local"')
    if not result.fetchone():
        logger.debug("User 'Local' does not exist. Adding user.")
        c_db.execute('INSERT INTO users (user_id, username) VALUES (0, "Local")')

    # Create session_history table indices
    c_db.execute(
        'CREATE INDEX IF NOT EXISTS "idx_session_history_media_type" '
        'ON "session_history" ("media_type")'
    )
    c_db.execute(
        'CREATE INDEX IF NOT EXISTS "idx_session_history_media_type_stopped" '
        'ON "session_history" ("media_type", "stopped" ASC)'
    )
    c_db.execute(
        'CREATE INDEX IF NOT EXISTS "idx_session_history_rating_key" '
        'ON "session_history" ("rating_key")'
    )
    c_db.execute(
        'CREATE INDEX IF NOT EXISTS "idx_session_history_parent_rating_key" '
        'ON "session_history" ("parent_rating_key")'
    )
    c_db.execute(
        'CREATE INDEX IF NOT EXISTS "idx_session_history_grandparent_rating_key" '
        'ON "session_history" ("grandparent_rating_key")'
    )
    c_db.execute(
        'CREATE INDEX IF NOT EXISTS "idx_session_history_user" '
        'ON "session_history" ("user")'
    )
    c_db.execute(
        'CREATE INDEX IF NOT EXISTS "idx_session_history_user_id" '
        'ON "session_history" ("user_id")'
    )
    c_db.execute(
        'CREATE INDEX IF NOT EXISTS "idx_session_history_user_id_stopped" '
        'ON "session_history" ("user_id", "stopped" ASC)'
    )
    c_db.execute(
        'CREATE INDEX IF NOT EXISTS "idx_session_history_section_id" '
        'ON "session_history" ("section_id")'
    )
    c_db.execute(
        'CREATE INDEX IF NOT EXISTS "idx_session_history_section_id_stopped" '
        'ON "session_history" ("section_id", "stopped" ASC)'
    )
    c_db.execute(
        'CREATE INDEX IF NOT EXISTS "idx_session_history_reference_id" '
        'ON "session_history" ("reference_id" ASC)'
    )

    # Create session_history_metadata table indices
    c_db.execute(
        'CREATE INDEX IF NOT EXISTS "idx_session_history_metadata_rating_key" '
        'ON "session_history_metadata" ("rating_key")'
    )
    c_db.execute(
        'CREATE INDEX IF NOT EXISTS "idx_session_history_metadata_guid" '
        'ON "session_history_metadata" ("guid")'
    )
    c_db.execute(
        'CREATE INDEX IF NOT EXISTS "idx_session_history_metadata_live" '
        'ON "session_history_metadata" ("live")'
    )

    # Create session_history_media_info table indices
    c_db.execute(
        'CREATE INDEX IF NOT EXISTS "idx_session_history_media_info_transcode_decision" '
        'ON "session_history_media_info" ("transcode_decision")'
    )

    # Create lookup table indices
    c_db.execute(
        'CREATE UNIQUE INDEX IF NOT EXISTS "idx_tvmaze_lookup" '
        'ON "tvmaze_lookup" ("rating_key")'
    )
    c_db.execute(
        'CREATE UNIQUE INDEX IF NOT EXISTS "idx_themoviedb_lookup" '
        'ON "themoviedb_lookup" ("rating_key")'
    )
    c_db.execute(
        'CREATE UNIQUE INDEX IF NOT EXISTS "idx_musicbrainz_lookup" '
        'ON "musicbrainz_lookup" ("rating_key")'
    )
    c_db.execute(
        'CREATE UNIQUE INDEX IF NOT EXISTS "idx_image_hash_lookup" '
        'ON "image_hash_lookup" ("img_hash")'
    )
    c_db.execute(
        'CREATE UNIQUE INDEX IF NOT EXISTS "idx_cloudinary_lookup" '
        'ON "cloudinary_lookup" ("img_hash")'
    )
    c_db.execute(
        'CREATE UNIQUE INDEX IF NOT EXISTS "idx_imgur_lookup" '
        'ON "imgur_lookup" ("img_hash")'
    )
    c_db.execute(
        'CREATE UNIQUE INDEX IF NOT EXISTS "idx_sessions_continued" '
        'ON "sessions_continued" ("user_id", "machine_id", "media_type")'
    )

    # Set database version
    result = c_db.execute('SELECT value FROM version_info WHERE key = "version"').fetchone()
    if not result:
        c_db.execute(
            'INSERT OR REPLACE INTO version_info (key, value) VALUES ("version", ?)',
            [common.RELEASE]
        )
    elif helpers.version_to_tuple(result[0]) < helpers.version_to_tuple(common.RELEASE):
        c_db.execute(
            'UPDATE version_info SET value = ? WHERE key = "version"',
            [common.RELEASE]
        )

    conn_db.commit()
    c_db.close()

    # Migrate poster_urls to imgur_lookup table
    try:
        db = database.MonitorDatabase()
        result = db.select('SELECT SQL FROM sqlite_master WHERE type="table" AND name="poster_urls"')
        if result:
            result = db.select('SELECT * FROM poster_urls')
            logger.debug("Altering database. Updating database table imgur_lookup.")

            data_factory = datafactory.DataFactory()

            for row in result:
                img_hash = notification_handler.set_hash_image_info(
                    rating_key=row['rating_key'], width=1000, height=1500, fallback='poster')
                data_factory.set_img_info(img_hash=img_hash, img_title=row['poster_title'],
                                          img_url=row['poster_url'], delete_hash=row['delete_hash'],
                                          service='imgur')

            db.action('DROP TABLE poster_urls')
    except sqlite3.OperationalError:
        pass


def upgrade():
    if CONFIG.UPGRADE_FLAG == 0:
        mobile_app.revalidate_onesignal_ids()
        CONFIG.UPGRADE_FLAG = 1
        CONFIG.write()

    return


def shutdown(restart=False, update=False, checkout=False, reset=False):
    webstart.stop()

    # Shutdown the websocket connection
    if WEBSOCKET:
        web_socket.shutdown()

    if SCHED.running:
        SCHED.shutdown(wait=False)
    if activity_handler.ACTIVITY_SCHED.running:
        activity_handler.ACTIVITY_SCHED.shutdown(wait=False)

    # Stop the notification threads
    for i in range(CONFIG.NOTIFICATION_THREADS):
        NOTIFY_QUEUE.put(None)

    CONFIG.write()

    if update:
        logger.info("Tautulli is updating...")
        try:
            versioncheck.update()
        except Exception as e:
            logger.warn("Tautulli failed to update: %s. Restarting." % e)

    if checkout:
        logger.info("Tautulli is switching the git branch...")
        try:
            versioncheck.checkout_git_branch()
        except Exception as e:
            logger.warn("Tautulli failed to switch git branch: %s. Restarting." % e)

    if reset:
        logger.info("Tautulli is resetting the git install...")
        try:
            versioncheck.reset_git_install()
        except Exception as e:
            logger.warn("Tautulli failed to reset git install: %s. Restarting." % e)

    if CREATEPID:
        logger.info("Removing pidfile %s", PIDFILE)
        os.remove(PIDFILE)

    if restart:
        logger.info("Tautulli is restarting...")

        exe = sys.executable
        if FROZEN:
            args = [exe]
        else:
            args = [exe, FULL_PATH]
        args += ARGS
        if '--nolaunch' not in args:
            args += ['--nolaunch']

        # Separate out logger so we can shutdown logger after
        if NOFORK:
            logger.info("Running as service, not forking. Exiting...")
        else:
            logger.info("Restarting Tautulli with %s", args)

        # os.execv fails with spaced names on Windows
        # https://bugs.python.org/issue19066
        if NOFORK:
            pass
        elif common.PLATFORM in ('Windows', 'Darwin'):
            subprocess.Popen(args, cwd=os.getcwd())
        else:
            os.execv(exe, args)

    else:
        logger.info("Tautulli is shutting down...")

    logger.shutdown()

    if WIN_SYS_TRAY_ICON:
        WIN_SYS_TRAY_ICON.shutdown()
    elif MAC_SYS_TRAY_ICON:
        MAC_SYS_TRAY_ICON.shutdown()

    os._exit(0)


def generate_uuid():
    return uuid.uuid4().hex


def initialize_tracker():
    data = {
        'dataSource': 'server',
        'appName': common.PRODUCT,
        'appVersion': common.RELEASE,
        'appId': INSTALL_TYPE,
        'appInstallerId': CONFIG.GIT_BRANCH,
        'dimension1': '{} {}'.format(common.PLATFORM, common.PLATFORM_RELEASE),  # App Platform
        'dimension2': common.PLATFORM_LINUX_DISTRO,  # Linux Distro
        'dimension3': common.PYTHON_VERSION,
        'userLanguage': SYS_LANGUAGE,
        'documentEncoding': SYS_ENCODING,
        'noninteractive': True
        }

    tracker = Tracker.create('UA-111522699-2', client_id=CONFIG.PMS_UUID, hash_client_id=True,
                             user_agent=common.USER_AGENT)
    tracker.set(data)

    return tracker


def analytics_event(category, action, label=None, value=None, **kwargs):
    data = {'category': category, 'action': action}

    if label is not None:
        data['label'] = label

    if value is not None:
        data['value'] = value

    if kwargs:
        data.update(kwargs)

    if TRACKER:
        try:
            TRACKER.send('event', data)
        except Exception as e:
            logger.warn("Failed to send analytics event for category '%s', action '%s': %s" % (category, action, e))


def check_folder_writable(folder, fallback, name):
    if not folder:
        folder = fallback

    if not os.path.exists(folder):
        try:
            os.makedirs(folder)
        except OSError as e:
            logger.error("Could not create %s dir '%s': %s" % (name, folder, e))
            if fallback and folder != fallback:
                logger.warn("Falling back to %s dir '%s'" % (name, fallback))
                return check_folder_writable(None, fallback, name)
            else:
                return folder, None

    if not os.access(folder, os.W_OK):
        logger.error("Cannot write to %s dir '%s'" % (name, folder))
        if fallback and folder != fallback:
            logger.warn("Falling back to %s dir '%s'" % (name, fallback))
            return check_folder_writable(None, fallback, name)
        else:
            return folder, False

    return folder, True


def get_tautulli_info():
    tautulli = {
        'tautulli_install_type': INSTALL_TYPE,
        'tautulli_version': common.RELEASE,
        'tautulli_branch': CONFIG.GIT_BRANCH,
        'tautulli_commit': CURRENT_VERSION,
        'tautulli_platform':common.PLATFORM,
        'tautulli_platform_release': common.PLATFORM_RELEASE,
        'tautulli_platform_version': common.PLATFORM_VERSION,
        'tautulli_platform_linux_distro': common.PLATFORM_LINUX_DISTRO,
        'tautulli_platform_device_name': common.PLATFORM_DEVICE_NAME,
        'tautulli_python_version': common.PYTHON_VERSION,
    }
    return tautulli
