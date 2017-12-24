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

import os
from Queue import Queue
import sqlite3
import sys
import subprocess
import threading
import datetime
import uuid
# Some cut down versions of Python may not include this module and it's not critical for us
try:
    import webbrowser
    no_browser = False
except ImportError:
    no_browser = True

import cherrypy
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

import activity_handler
import activity_pinger
import config
import database
import libraries
import logger
import mobile_app
import notification_handler
import notifiers
import plextv
import pmsconnect
import users
import versioncheck
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
NOFORK = False

SCHED = BackgroundScheduler()
SCHED_LOCK = threading.Lock()

NOTIFY_QUEUE = Queue()

INIT_LOCK = threading.Lock()
_INITIALIZED = False
_STARTED = False

DATA_DIR = None

CONFIG = None
CONFIG_FILE = None

DB_FILE = None

INSTALL_TYPE = None
CURRENT_VERSION = None
LATEST_VERSION = None
COMMITS_BEHIND = None

UMASK = None

HTTP_ROOT = None

DEV = False

WS_CONNECTED = False
PLEX_SERVER_UP = True


def initialize(config_file):
    with INIT_LOCK:

        global CONFIG
        global CONFIG_FILE
        global _INITIALIZED
        global CURRENT_VERSION
        global LATEST_VERSION
        global UMASK
        CONFIG = plexpy.config.Config(config_file)
        CONFIG_FILE = config_file

        assert CONFIG is not None

        if _INITIALIZED:
            return False

        if CONFIG.HTTP_PORT < 21 or CONFIG.HTTP_PORT > 65535:
            plexpy.logger.warn(
                u"HTTP_PORT out of bounds: 21 < %s < 65535", CONFIG.HTTP_PORT)
            CONFIG.HTTP_PORT = 8181

        if not CONFIG.HTTPS_CERT:
            CONFIG.HTTPS_CERT = os.path.join(DATA_DIR, 'server.crt')
        if not CONFIG.HTTPS_KEY:
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

        if not CONFIG.BACKUP_DIR:
            CONFIG.BACKUP_DIR = os.path.join(DATA_DIR, 'backups')
        if not os.path.exists(CONFIG.BACKUP_DIR):
            try:
                os.makedirs(CONFIG.BACKUP_DIR)
            except OSError as e:
                logger.error(u"Could not create backup dir '%s': %s" % (CONFIG.BACKUP_DIR, e))

        if not CONFIG.CACHE_DIR:
            CONFIG.CACHE_DIR = os.path.join(DATA_DIR, 'cache')
        if not os.path.exists(CONFIG.CACHE_DIR):
            try:
                os.makedirs(CONFIG.CACHE_DIR)
            except OSError as e:
                logger.error(u"Could not create cache dir '%s': %s" % (CONFIG.CACHE_DIR, e))

        # Initialize the database
        logger.info(u"Checking if the database upgrades are required...")
        try:
            dbcheck()
        except Exception as e:
            logger.error(u"Can't connect to the database: %s" % e)

        # Perform upgrades
        logger.info(u"Checking if configuration upgrades are required...")
        try:
            upgrade()
        except Exception as e:
            logger.error(u"Could not perform upgrades: %s" % e)

        # Add notifier configs to logger blacklist
        notifiers.blacklist_logger()
        mobile_app.blacklist_logger()

        # Check if Tautulli has a uuid
        if CONFIG.PMS_UUID == '' or not CONFIG.PMS_UUID:
            logger.debug(u"Generating UUID...")
            my_uuid = generate_uuid()
            CONFIG.__setattr__('PMS_UUID', my_uuid)
            CONFIG.write()
        
        # Check if Tautulli has an API key
        if CONFIG.API_KEY == '':
            logger.debug(u"Generating API key...")
            api_key = generate_uuid()
            CONFIG.__setattr__('API_KEY', api_key)
            CONFIG.write()
        
        # Get the currently installed version. Returns None, 'win32' or the git
        # hash.
        CURRENT_VERSION, CONFIG.GIT_REMOTE, CONFIG.GIT_BRANCH = versioncheck.getVersion()

        # Write current version to a file, so we know which version did work.
        # This allowes one to restore to that version. The idea is that if we
        # arrive here, most parts of Tautulli seem to work.
        if CURRENT_VERSION:
            version_lock_file = os.path.join(DATA_DIR, "version.lock")

            try:
                with open(version_lock_file, "w") as fp:
                    fp.write(CURRENT_VERSION)
            except IOError as e:
                logger.error(u"Unable to write current version to file '%s': %s" %
                             (version_lock_file, e))

        # Check for new versions
        if CONFIG.CHECK_GITHUB_ON_STARTUP and CONFIG.CHECK_GITHUB:
            try:
                LATEST_VERSION = versioncheck.checkGithub()
            except:
                logger.exception(u"Unhandled exception")
                LATEST_VERSION = CURRENT_VERSION
        else:
            LATEST_VERSION = CURRENT_VERSION

        # Get the real PMS urls for SSL and remote access
        if CONFIG.PMS_TOKEN and CONFIG.PMS_IP and CONFIG.PMS_PORT:
            plextv.get_server_resources()

        # Refresh the users list on startup
        if CONFIG.PMS_TOKEN and CONFIG.REFRESH_USERS_ON_STARTUP:
            users.refresh_users()

        # Refresh the libraries list on startup
        if CONFIG.PMS_IP and CONFIG.PMS_TOKEN and CONFIG.REFRESH_LIBRARIES_ON_STARTUP:
            libraries.refresh_libraries()

        # Store the original umask
        UMASK = os.umask(0)
        os.umask(UMASK)

        _INITIALIZED = True
        return True

def daemonize():
    if threading.activeCount() != 1:
        logger.warn(
            u"There are %r active threads. Daemonizing may cause"
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

    dev_null = file('/dev/null', 'r')
    os.dup2(dev_null.fileno(), sys.stdin.fileno())

    si = open('/dev/null', "r")
    so = open('/dev/null', "a+")
    se = open('/dev/null', "a+")

    os.dup2(si.fileno(), sys.stdin.fileno())
    os.dup2(so.fileno(), sys.stdout.fileno())
    os.dup2(se.fileno(), sys.stderr.fileno())

    pid = os.getpid()
    logger.info(u"Daemonized to PID: %d", pid)

    if CREATEPID:
        logger.info(u"Writing PID %d to %s", pid, PIDFILE)
        with file(PIDFILE, 'w') as fp:
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
            logger.error(u"Could not launch browser: %s" % e)


def initialize_scheduler():
    """
    Start the scheduled background tasks. Re-schedule if interval settings changed.
    """

    with SCHED_LOCK:

        # Check if scheduler should be started
        start_jobs = not len(SCHED.get_jobs())

        # Update check
        github_minutes = CONFIG.CHECK_GITHUB_INTERVAL if CONFIG.CHECK_GITHUB_INTERVAL and CONFIG.CHECK_GITHUB else 0

        schedule_job(versioncheck.checkGithub, 'Check GitHub for updates',
                     hours=0, minutes=github_minutes, seconds=0, args=(bool(CONFIG.PLEXPY_AUTO_UPDATE),))

        backup_hours = CONFIG.BACKUP_INTERVAL if 1 <= CONFIG.BACKUP_INTERVAL <= 24 else 6

        schedule_job(database.make_backup, 'Backup Tautulli database',
                     hours=backup_hours, minutes=0, seconds=0, args=(True, True))
        schedule_job(config.make_backup, 'Backup Tautulli config',
                     hours=backup_hours, minutes=0, seconds=0, args=(True, True))

        if WS_CONNECTED and CONFIG.PMS_IP and CONFIG.PMS_TOKEN:
            schedule_job(plextv.get_server_resources, 'Refresh Plex server URLs',
                         hours=12 * (not bool(CONFIG.PMS_URL_MANUAL)), minutes=0, seconds=0)

            schedule_job(activity_pinger.check_server_access, 'Check for Plex remote access',
                         hours=0, minutes=0, seconds=60 * bool(CONFIG.MONITOR_REMOTE_ACCESS))
            schedule_job(activity_pinger.check_server_updates, 'Check for Plex updates',
                         hours=12 * bool(CONFIG.MONITOR_PMS_UPDATES), minutes=0, seconds=0)

            # Refresh the users list and libraries list
            user_hours = CONFIG.REFRESH_USERS_INTERVAL if 1 <= CONFIG.REFRESH_USERS_INTERVAL <= 24 else 12
            library_hours = CONFIG.REFRESH_LIBRARIES_INTERVAL if 1 <= CONFIG.REFRESH_LIBRARIES_INTERVAL <= 24 else 12

            schedule_job(users.refresh_users, 'Refresh users list',
                         hours=user_hours, minutes=0, seconds=0)
            schedule_job(libraries.refresh_libraries, 'Refresh libraries list',
                         hours=library_hours, minutes=0, seconds=0)

            schedule_job(activity_pinger.check_server_response, 'Check server response',
                         hours=0, minutes=0, seconds=0)

        else:
            # Cancel all jobs
            schedule_job(plextv.get_server_resources, 'Refresh Plex server URLs',
                         hours=0, minutes=0, seconds=0)

            schedule_job(activity_pinger.check_server_access, 'Check for Plex remote access',
                         hours=0, minutes=0, seconds=0)
            schedule_job(activity_pinger.check_server_updates, 'Check for Plex updates',
                         hours=0, minutes=0, seconds=0)

            schedule_job(users.refresh_users, 'Refresh users list',
                         hours=0, minutes=0, seconds=0)
            schedule_job(libraries.refresh_libraries, 'Refresh libraries list',
                         hours=0, minutes=0, seconds=0)

            # Schedule job to reconnect websocket
            response_seconds = CONFIG.WEBSOCKET_CONNECTION_ATTEMPTS * CONFIG.WEBSOCKET_CONNECTION_TIMEOUT
            response_seconds = 60 if response_seconds < 60 else response_seconds

            schedule_job(activity_pinger.check_server_response, 'Check server response',
                         hours=0, minutes=0, seconds=response_seconds)

        # Start scheduler
        if start_jobs and len(SCHED.get_jobs()):
            try:
                SCHED.start()
            except Exception as e:
                logger.error(e)


def schedule_job(function, name, hours=0, minutes=0, seconds=0, args=None):
    """
    Start scheduled job if starting or restarting plexpy.
    Reschedule job if Interval Settings have changed.
    Remove job if if Interval Settings changed to 0

    """

    job = SCHED.get_job(name)
    if job:
        if hours == 0 and minutes == 0 and seconds == 0:
            SCHED.remove_job(name)
            logger.info(u"Removed background task: %s", name)
        elif job.trigger.interval != datetime.timedelta(hours=hours, minutes=minutes):
            SCHED.reschedule_job(name, trigger=IntervalTrigger(
                hours=hours, minutes=minutes, seconds=seconds), args=args)
            logger.info(u"Re-scheduled background task: %s", name)
    elif hours > 0 or minutes > 0 or seconds > 0:
        SCHED.add_job(function, id=name, trigger=IntervalTrigger(
            hours=hours, minutes=minutes, seconds=seconds), args=args)
        logger.info(u"Scheduled background task: %s", name)


def start():
    global _STARTED

    if _INITIALIZED:
        # Start the scheduler for stale stream callbacks
        activity_handler.ACTIVITY_SCHED.start()

        # Start background notification thread
        notification_handler.start_threads(num_threads=CONFIG.NOTIFICATION_THREADS)

        _STARTED = True


def sig_handler(signum=None, frame=None):
    if signum is not None:
        logger.info(u"Signal %i caught, saving and exiting...", signum)
        shutdown()


def dbcheck():
    conn_db = sqlite3.connect(DB_FILE)
    c_db = conn_db.cursor()

    # sessions table :: This is a temp table that logs currently active sessions
    c_db.execute(
        'CREATE TABLE IF NOT EXISTS sessions (id INTEGER PRIMARY KEY AUTOINCREMENT, session_key INTEGER, '
        'transcode_key TEXT, rating_key INTEGER, section_id INTEGER, media_type TEXT, started INTEGER, stopped INTEGER, '
        'paused_counter INTEGER DEFAULT 0, state TEXT, user_id INTEGER, user TEXT, friendly_name TEXT, '
        'ip_address TEXT, machine_id TEXT, player TEXT, product TEXT, platform TEXT, title TEXT, parent_title TEXT, '
        'grandparent_title TEXT, full_title TEXT, media_index INTEGER, parent_media_index INTEGER, '
        'thumb TEXT, parent_thumb TEXT, grandparent_thumb TEXT, year INTEGER, '
        'parent_rating_key INTEGER, grandparent_rating_key INTEGER, '
        'view_offset INTEGER DEFAULT 0, duration INTEGER, video_decision TEXT, audio_decision TEXT, '
        'transcode_decision TEXT, container TEXT, bitrate INTEGER, width INTEGER, height INTEGER, '
        'video_codec TEXT, video_bitrate INTEGER, video_resolution TEXT, video_width INTEGER, video_height INTEGER, '
        'video_framerate TEXT, aspect_ratio TEXT, '
        'audio_codec TEXT, audio_bitrate INTEGER, audio_channels INTEGER, subtitle_codec TEXT, '
        'stream_bitrate INTEGER, stream_video_resolution TEXT, quality_profile TEXT, '
        'stream_container_decision TEXT, stream_container TEXT, '
        'stream_video_decision TEXT, stream_video_codec TEXT, stream_video_bitrate INTEGER, stream_video_width INTEGER, '
        'stream_video_height INTEGER, stream_video_framerate TEXT, '
        'stream_audio_decision TEXT, stream_audio_codec TEXT, stream_audio_bitrate INTEGER, stream_audio_channels INTEGER, '
        'subtitles INTEGER, stream_subtitle_decision TEXT, stream_subtitle_codec TEXT, '
        'transcode_protocol TEXT, transcode_container TEXT, '
        'transcode_video_codec TEXT, transcode_audio_codec TEXT, transcode_audio_channels INTEGER,'
        'transcode_width INTEGER, transcode_height INTEGER, '
        'optimized_version INTEGER, optimized_version_profile TEXT, optimized_version_title TEXT, '
        'synced_version INTEGER, synced_version_profile TEXT, '
        'buffer_count INTEGER DEFAULT 0, buffer_last_triggered INTEGER, last_paused INTEGER, write_attempts INTEGER DEFAULT 0, '
        'raw_stream_info TEXT)'
    )

    # session_history table :: This is a history table which logs essential stream details
    c_db.execute(
        'CREATE TABLE IF NOT EXISTS session_history (id INTEGER PRIMARY KEY AUTOINCREMENT, reference_id INTEGER, '
        'started INTEGER, stopped INTEGER, rating_key INTEGER, user_id INTEGER, user TEXT, '
        'ip_address TEXT, paused_counter INTEGER DEFAULT 0, player TEXT, product TEXT, product_version TEXT, platform TEXT, platform_version TEXT, profile TEXT, machine_id TEXT, '
        'bandwidth INTEGER, location TEXT, quality_profile TEXT, '
        'parent_rating_key INTEGER, grandparent_rating_key INTEGER, media_type TEXT, view_offset INTEGER DEFAULT 0)'
    )

    # session_history_media_info table :: This is a table which logs each session's media info
    c_db.execute(
        'CREATE TABLE IF NOT EXISTS session_history_media_info (id INTEGER PRIMARY KEY, rating_key INTEGER, '
        'video_decision TEXT, audio_decision TEXT, transcode_decision TEXT, duration INTEGER DEFAULT 0, '
        'container TEXT, bitrate INTEGER, width INTEGER, height INTEGER, video_bitrate INTEGER, video_bit_depth INTEGER, '
        'video_codec TEXT, video_codec_level TEXT, video_width INTEGER, video_height INTEGER, video_resolution TEXT, '
        'video_framerate TEXT, aspect_ratio TEXT, '
        'audio_bitrate INTEGER, audio_codec TEXT, audio_channels INTEGER, transcode_protocol TEXT, '
        'transcode_container TEXT, transcode_video_codec TEXT, transcode_audio_codec TEXT, '
        'transcode_audio_channels INTEGER, transcode_width INTEGER, transcode_height INTEGER, '
        'transcode_hw_requested INTEGER, transcode_hw_full_pipeline INTEGER, transcode_hw_decode TEXT, '
        'transcode_hw_decode_title TEXT, transcode_hw_encode TEXT, transcode_hw_encode_title TEXT, '
        'stream_container TEXT, stream_container_decision TEXT, stream_bitrate INTEGER, '
        'stream_video_decision TEXT, stream_video_bitrate INTEGER, stream_video_codec TEXT, stream_video_codec_level TEXT, '
        'stream_video_bit_depth INTEGER, stream_video_height INTEGER, stream_video_width INTEGER, stream_video_resolution TEXT, '
        'stream_video_framerate TEXT, '
        'stream_audio_decision TEXT, stream_audio_codec TEXT, stream_audio_bitrate INTEGER, stream_audio_channels INTEGER, '
        'stream_subtitle_decision TEXT, stream_subtitle_codec TEXT, stream_subtitle_container TEXT, stream_subtitle_forced INTEGER, '
        'subtitles INTEGER, subtitle_codec TEXT, synced_version INTEGER, synced_version_profile TEXT, '
        'optimized_version INTEGER, optimized_version_profile TEXT, optimized_version_title TEXT)'
    )

    # session_history_metadata table :: This is a table which logs each session's media metadata
    c_db.execute(
        'CREATE TABLE IF NOT EXISTS session_history_metadata (id INTEGER PRIMARY KEY, '
        'rating_key INTEGER, parent_rating_key INTEGER, grandparent_rating_key INTEGER, '
        'title TEXT, parent_title TEXT, grandparent_title TEXT, full_title TEXT, media_index INTEGER, '
        'parent_media_index INTEGER, section_id INTEGER, thumb TEXT, parent_thumb TEXT, grandparent_thumb TEXT, '
        'art TEXT, media_type TEXT, year INTEGER, originally_available_at TEXT, added_at INTEGER, updated_at INTEGER, '
        'last_viewed_at INTEGER, content_rating TEXT, summary TEXT, tagline TEXT, rating TEXT, '
        'duration INTEGER DEFAULT 0, guid TEXT, directors TEXT, writers TEXT, actors TEXT, genres TEXT, studio TEXT, '
        'labels TEXT)'
    )

    # users table :: This table keeps record of the friends list
    c_db.execute(
        'CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, '
        'user_id INTEGER DEFAULT NULL UNIQUE, username TEXT NOT NULL, friendly_name TEXT, '
        'thumb TEXT, custom_avatar_url TEXT, email TEXT, is_home_user INTEGER DEFAULT NULL, '
        'is_allow_sync INTEGER DEFAULT NULL, is_restricted INTEGER DEFAULT NULL, do_notify INTEGER DEFAULT 1, '
        'keep_history INTEGER DEFAULT 1, deleted_user INTEGER DEFAULT 0, allow_guest INTEGER DEFAULT 0, '
        'user_token TEXT, server_token TEXT, shared_libraries TEXT, filter_all TEXT, filter_movies TEXT, filter_tv TEXT, '
        'filter_music TEXT, filter_photos TEXT)'
    )

    # notify_log table :: This is a table which logs notifications sent
    c_db.execute(
        'CREATE TABLE IF NOT EXISTS notify_log (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp INTEGER, '
        'session_key INTEGER, rating_key INTEGER, parent_rating_key INTEGER, grandparent_rating_key INTEGER, '
        'user_id INTEGER, user TEXT, notifier_id INTEGER, agent_id INTEGER, agent_name TEXT, notify_action TEXT, '
        'subject_text TEXT, body_text TEXT, script_args TEXT, success INTEGER DEFAULT 0)'
    )

    # library_sections table :: This table keeps record of the servers library sections
    c_db.execute(
        'CREATE TABLE IF NOT EXISTS library_sections (id INTEGER PRIMARY KEY AUTOINCREMENT, '
        'server_id TEXT, section_id INTEGER, section_name TEXT, section_type TEXT, '
        'thumb TEXT, custom_thumb_url TEXT, art TEXT, count INTEGER, parent_count INTEGER, child_count INTEGER, '
        'do_notify INTEGER DEFAULT 1, do_notify_created INTEGER DEFAULT 1, keep_history INTEGER DEFAULT 1, '
        'deleted_section INTEGER DEFAULT 0, UNIQUE(server_id, section_id))'
    )

    # user_login table :: This table keeps record of the Tautulli guest logins
    c_db.execute(
        'CREATE TABLE IF NOT EXISTS user_login (id INTEGER PRIMARY KEY AUTOINCREMENT, '
        'timestamp INTEGER, user_id INTEGER, user TEXT, user_group TEXT, '
        'ip_address TEXT, host TEXT, user_agent TEXT, success INTEGER DEFAULT 1)'
    )

    # notifiers table :: This table keeps record of the notification agent settings
    c_db.execute(
        'CREATE TABLE IF NOT EXISTS notifiers (id INTEGER PRIMARY KEY AUTOINCREMENT, '
        'agent_id INTEGER, agent_name TEXT, agent_label TEXT, friendly_name TEXT, notifier_config TEXT, '
        'on_play INTEGER DEFAULT 0, on_stop INTEGER DEFAULT 0, on_pause INTEGER DEFAULT 0, '
        'on_resume INTEGER DEFAULT 0, on_buffer INTEGER DEFAULT 0, on_watched INTEGER DEFAULT 0, '
        'on_created INTEGER DEFAULT 0, on_extdown INTEGER DEFAULT 0, on_intdown INTEGER DEFAULT 0, '
        'on_extup INTEGER DEFAULT 0, on_intup INTEGER DEFAULT 0, on_pmsupdate INTEGER DEFAULT 0, '
        'on_concurrent INTEGER DEFAULT 0, on_newdevice INTEGER DEFAULT 0, on_plexpyupdate INTEGER DEFAULT 0, '
        'on_play_subject TEXT, on_stop_subject TEXT, on_pause_subject TEXT, '
        'on_resume_subject TEXT, on_buffer_subject TEXT, on_watched_subject TEXT, '
        'on_created_subject TEXT, on_extdown_subject TEXT, on_intdown_subject TEXT, '
        'on_extup_subject TEXT, on_intup_subject TEXT, on_pmsupdate_subject TEXT, '
        'on_concurrent_subject TEXT, on_newdevice_subject TEXT, on_plexpyupdate_subject TEXT, '
        'on_play_body TEXT, on_stop_body TEXT, on_pause_body TEXT, '
        'on_resume_body TEXT, on_buffer_body TEXT, on_watched_body TEXT, '
        'on_created_body TEXT, on_extdown_body TEXT, on_intdown_body TEXT, '
        'on_extup_body TEXT, on_intup_body TEXT, on_pmsupdate_body TEXT, '
        'on_concurrent_body TEXT, on_newdevice_body TEXT, on_plexpyupdate_body TEXT, '
        'custom_conditions TEXT, custom_conditions_logic TEXT)'
    )

    # poster_urls table :: This table keeps record of the notification poster urls
    c_db.execute(
        'CREATE TABLE IF NOT EXISTS poster_urls (id INTEGER PRIMARY KEY AUTOINCREMENT, '
        'rating_key INTEGER, poster_title TEXT, poster_url TEXT)'
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
        'device_id TEXT NOT NULL UNIQUE, device_token TEXT, device_name TEXT, friendly_name TEXT, '
        'last_seen INTEGER)'
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

    # Upgrade sessions table from earlier versions
    try:
        c_db.execute('SELECT started FROM sessions')
    except sqlite3.OperationalError:
        logger.debug(u"Altering database. Updating database table sessions.")
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
        logger.debug(u"Altering database. Updating database table sessions.")
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
        logger.debug(u"Altering database. Updating database table sessions.")
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
        logger.debug(u"Altering database. Updating database table sessions.")
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
        logger.debug(u"Altering database. Updating database table sessions.")
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN last_paused INTEGER'
        )

    # Upgrade sessions table from earlier versions
    try:
        c_db.execute('SELECT section_id FROM sessions')
    except sqlite3.OperationalError:
        logger.debug(u"Altering database. Updating database table sessions.")
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN section_id INTEGER'
        )

    # Upgrade sessions table from earlier versions
    try:
        c_db.execute('SELECT stopped FROM sessions')
    except sqlite3.OperationalError:
        logger.debug(u"Altering database. Updating database table sessions.")
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN stopped INTEGER'
        )

    # Upgrade sessions table from earlier versions
    try:
        c_db.execute('SELECT transcode_key FROM sessions')
    except sqlite3.OperationalError:
        logger.debug(u"Altering database. Updating database table sessions.")
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN transcode_key TEXT'
        )

    # Upgrade sessions table from earlier versions
    try:
        c_db.execute('SELECT write_attempts FROM sessions')
    except sqlite3.OperationalError:
        logger.debug(u"Altering database. Updating database table sessions.")
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN write_attempts INTEGER DEFAULT 0'
        )

    # Upgrade sessions table from earlier versions
    try:
        c_db.execute('SELECT transcode_decision FROM sessions')
    except sqlite3.OperationalError:
        logger.debug(u"Altering database. Updating database table sessions.")
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
        logger.debug(u"Altering database. Updating database table sessions.")
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN product INTEGER'
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
        logger.debug(u"Altering database. Updating database table sessions.")
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN video_height INTEGER'
        )

    # Upgrade sessions table from earlier versions
    try:
        c_db.execute('SELECT subtitles FROM sessions')
    except sqlite3.OperationalError:
        logger.debug(u"Altering database. Updating database table sessions.")
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN subtitles INTEGER'
        )

    # Upgrade sessions table from earlier versions
    try:
        c_db.execute('SELECT synced_version_profile FROM sessions')
    except sqlite3.OperationalError:
        logger.debug(u"Altering database. Updating database table sessions.")
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN synced_version_profile TEXT'
        )
        c_db.execute(
            'ALTER TABLE sessions ADD COLUMN optimized_version_title TEXT'
        )

    # Upgrade session_history table from earlier versions
    try:
        c_db.execute('SELECT reference_id FROM session_history')
    except sqlite3.OperationalError:
        logger.debug(u"Altering database. Updating database table session_history.")
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
        logger.debug(u"Altering database. Updating database table session_history.")
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

    # Upgrade session_history_metadata table from earlier versions
    try:
        c_db.execute('SELECT full_title FROM session_history_metadata')
    except sqlite3.OperationalError:
        logger.debug(u"Altering database. Updating database table session_history_metadata.")
        c_db.execute(
            'ALTER TABLE session_history_metadata ADD COLUMN full_title TEXT'
        )

    # Upgrade session_history_metadata table from earlier versions
    try:
        c_db.execute('SELECT tagline FROM session_history_metadata')
    except sqlite3.OperationalError:
        logger.debug(u"Altering database. Updating database table session_history_metadata.")
        c_db.execute(
            'ALTER TABLE session_history_metadata ADD COLUMN tagline TEXT'
        )

    # Upgrade session_history_metadata table from earlier versions
    try:
        c_db.execute('SELECT section_id FROM session_history_metadata')
    except sqlite3.OperationalError:
        logger.debug(u"Altering database. Updating database table session_history_metadata.")
        c_db.execute(
            'ALTER TABLE session_history_metadata ADD COLUMN section_id INTEGER'
        )

    # Upgrade session_history_metadata table from earlier versions
    try:
        c_db.execute('SELECT labels FROM session_history_metadata')
    except sqlite3.OperationalError:
        logger.debug(u"Altering database. Updating database table session_history_metadata.")
        c_db.execute(
            'ALTER TABLE session_history_metadata ADD COLUMN labels TEXT'
        )

    # Upgrade session_history_media_info table from earlier versions
    try:
        c_db.execute('SELECT transcode_decision FROM session_history_media_info')
    except sqlite3.OperationalError:
        logger.debug(u"Altering database. Updating database table session_history_media_info.")
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
        logger.debug(u"Altering database. Updating database table session_history_media_info.")
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
        logger.debug(u"Altering database. Updating database table session_history_media_info.")
        c_db.execute(
            'ALTER TABLE session_history_media_info ADD COLUMN subtitle_codec TEXT '
        )

    # Upgrade session_history_media_info table from earlier versions
    try:
        c_db.execute('SELECT synced_version_profile FROM session_history_media_info')
    except sqlite3.OperationalError:
        logger.debug(u"Altering database. Updating database table session_history_media_info.")
        c_db.execute(
            'ALTER TABLE session_history_media_info ADD COLUMN synced_version_profile TEXT '
        )
        c_db.execute(
            'ALTER TABLE session_history_media_info ADD COLUMN optimized_version_title TEXT '
        )

    # Upgrade users table from earlier versions
    try:
        c_db.execute('SELECT do_notify FROM users')
    except sqlite3.OperationalError:
        logger.debug(u"Altering database. Updating database table users.")
        c_db.execute(
            'ALTER TABLE users ADD COLUMN do_notify INTEGER DEFAULT 1'
        )

    # Upgrade users table from earlier versions
    try:
        c_db.execute('SELECT keep_history FROM users')
    except sqlite3.OperationalError:
        logger.debug(u"Altering database. Updating database table users.")
        c_db.execute(
            'ALTER TABLE users ADD COLUMN keep_history INTEGER DEFAULT 1'
        )

    # Upgrade users table from earlier versions
    try:
        c_db.execute('SELECT custom_avatar_url FROM users')
    except sqlite3.OperationalError:
        logger.debug(u"Altering database. Updating database table users.")
        c_db.execute(
            'ALTER TABLE users ADD COLUMN custom_avatar_url TEXT'
        )

    # Upgrade users table from earlier versions
    try:
        c_db.execute('SELECT deleted_user FROM users')
    except sqlite3.OperationalError:
        logger.debug(u"Altering database. Updating database table users.")
        c_db.execute(
            'ALTER TABLE users ADD COLUMN deleted_user INTEGER DEFAULT 0'
        )

    # Upgrade users table from earlier versions
    try:
        c_db.execute('SELECT allow_guest FROM users')
    except sqlite3.OperationalError:
        logger.debug(u"Altering database. Updating database table users.")
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
        logger.debug(u"Altering database. Updating database table users.")
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

    # Upgrade notify_log table from earlier versions
    try:
        c_db.execute('SELECT poster_url FROM notify_log')
    except sqlite3.OperationalError:
        logger.debug(u"Altering database. Updating database table notify_log.")
        c_db.execute(
            'ALTER TABLE notify_log ADD COLUMN poster_url TEXT'
        )

    # Upgrade notify_log table from earlier versions (populate table with data from notify_log)
    try:
        c_db.execute('SELECT timestamp FROM notify_log')
    except sqlite3.OperationalError:
        logger.debug(u"Altering database. Updating database table notify_log.")
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
        logger.debug(u"Altering database. Updating database table notify_log.")
        c_db.execute(
            'ALTER TABLE notify_log ADD COLUMN notifier_id INTEGER'
        )

    # Upgrade notify_log table from earlier versions
    try:
        c_db.execute('SELECT success FROM notify_log')
    except sqlite3.OperationalError:
        logger.debug(u"Altering database. Updating database table notify_log.")
        c_db.execute(
            'ALTER TABLE notify_log ADD COLUMN success INTEGER DEFAULT 0'
        )
        c_db.execute(
            'UPDATE notify_log SET success = 1'
        )

    # Upgrade library_sections table from earlier versions (remove UNIQUE constraint on section_id)
    try:
        result = c_db.execute('SELECT SQL FROM sqlite_master WHERE type="table" AND name="library_sections"').fetchone()
        if 'section_id INTEGER UNIQUE' in result[0]:
            logger.debug(u"Altering database. Removing unique constraint on section_id from library_sections table.")
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
        logger.warn(u"Unable to remove section_id unique constraint from library_sections.")
        try:
            c_db.execute(
                'DROP TABLE library_sections_temp'
            )
        except:
            pass

    # Upgrade library_sections table from earlier versions (remove duplicated libraries)
    try:
        result = c_db.execute('SELECT * FROM library_sections WHERE server_id = ""')
        if result.rowcount > 0:
            logger.debug(u"Altering database. Removing duplicate libraries from library_sections table.")
            c_db.execute(
                'DELETE FROM library_sections WHERE server_id = ""'
            )
    except sqlite3.OperationalError:
        logger.warn(u"Unable to remove duplicate libraries from library_sections table.")

    # Upgrade users table from earlier versions (remove UNIQUE constraint on username)
    try:
        result = c_db.execute('SELECT SQL FROM sqlite_master WHERE type="table" AND name="users"').fetchone()
        if 'username TEXT NOT NULL UNIQUE' in result[0]:
            logger.debug(u"Altering database. Removing unique constraint on username from users table.")
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
        logger.warn(u"Unable to remove username unique constraint from users.")
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
            logger.debug(u"Altering database. Dropping and recreating mobile_devices table.")
            c_db.execute(
                'DROP TABLE mobile_devices'
            )
            c_db.execute(
                'CREATE TABLE IF NOT EXISTS mobile_devices (id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'device_id TEXT NOT NULL UNIQUE, device_token TEXT, device_name TEXT, friendly_name TEXT)'
            )
    except sqlite3.OperationalError:
        logger.warn(u"Failed to recreate mobile_devices table.")
        pass

    # Upgrade mobile_devices table from earlier versions
    try:
        c_db.execute('SELECT last_seen FROM mobile_devices')
    except sqlite3.OperationalError:
        logger.debug(u"Altering database. Updating database table mobile_devices.")
        c_db.execute(
            'ALTER TABLE mobile_devices ADD COLUMN last_seen INTEGER'
        )

    # Upgrade notifiers table from earlier versions
    try:
        c_db.execute('SELECT custom_conditions FROM notifiers')
    except sqlite3.OperationalError:
        logger.debug(u"Altering database. Updating database table notifiers.")
        c_db.execute(
            'ALTER TABLE notifiers ADD COLUMN custom_conditions TEXT'
        )
        c_db.execute(
            'ALTER TABLE notifiers ADD COLUMN custom_conditions_logic TEXT'
        )

    # Upgrade tvmaze_lookup table from earlier versions
    try:
        c_db.execute('SELECT rating_key FROM tvmaze_lookup')
    except sqlite3.OperationalError:
        logger.debug(u"Altering database. Updating database table tvmaze_lookup.")
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
        logger.debug(u"Altering database. Updating database table themoviedb_lookup.")
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
        logger.debug(u"Altering database. Updating database table user_login.")
        c_db.execute(
            'ALTER TABLE user_login ADD COLUMN success INTEGER DEFAULT 1'
        )

    # Add "Local" user to database as default unauthenticated user.
    result = c_db.execute('SELECT id FROM users WHERE username = "Local"')
    if not result.fetchone():
        logger.debug(u"User 'Local' does not exist. Adding user.")
        c_db.execute('INSERT INTO users (user_id, username) VALUES (0, "Local")')
    
    # Create table indices
    c_db.execute(
        'CREATE UNIQUE INDEX IF NOT EXISTS idx_tvmaze_lookup ON tvmaze_lookup (rating_key)'
    )
    c_db.execute(
        'CREATE UNIQUE INDEX IF NOT EXISTS idx_themoviedb_lookup ON themoviedb_lookup (rating_key)'
    )   

    conn_db.commit()
    c_db.close()

def upgrade():
    if CONFIG.UPDATE_NOTIFIERS_DB:
        notifiers.upgrade_config_to_db()
    if CONFIG.UPDATE_LIBRARIES_DB_NOTIFY:
        libraries.update_libraries_db_notify()

def shutdown(restart=False, update=False, checkout=False):
    cherrypy.engine.exit()
    SCHED.shutdown(wait=False)

    # Stop the notification threads
    for i in range(CONFIG.NOTIFICATION_THREADS):
        NOTIFY_QUEUE.put(None)

    CONFIG.write()

    if not restart and not update and not checkout:
        logger.info(u"Tautulli is shutting down...")

    if update:
        logger.info(u"Tautulli is updating...")
        try:
            versioncheck.update()
        except Exception as e:
            logger.warn(u"Tautulli failed to update: %s. Restarting." % e)

    if checkout:
        logger.info(u"Tautulli is switching the git branch...")
        try:
            versioncheck.checkout_git_branch()
        except Exception as e:
            logger.warn(u"Tautulli failed to switch git branch: %s. Restarting." % e)

    if CREATEPID:
        logger.info(u"Removing pidfile %s", PIDFILE)
        os.remove(PIDFILE)

    if restart:
        logger.info(u"Tautulli is restarting...")
        exe = sys.executable
        args = [exe, FULL_PATH]
        args += ARGS
        if '--nolaunch' not in args:
            args += ['--nolaunch']

        # os.execv fails with spaced names on Windows
        # https://bugs.python.org/issue19066
        if NOFORK:
            logger.info('Running as service, not forking. Exiting...')
        elif os.name == 'nt':
            logger.info('Restarting Tautulli with %s', args)
            subprocess.Popen(args, cwd=os.getcwd())
        else:
            logger.info('Restarting Tautulli with %s', args)
            os.execv(exe, args)

    os._exit(0)


def generate_uuid():
    return uuid.uuid4().hex
