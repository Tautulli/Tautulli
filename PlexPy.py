#!/usr/bin/env python
# coding=utf-8

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


import argparse
import locale
import os
import signal
import sys
import time

import plexpy
from plexpy import config
from plexpy import database
from plexpy import logger
from plexpy import web_socket
from plexpy import webstart

# Register signals, such as CTRL + C
signal.signal(signal.SIGINT, plexpy.sig_handler)
signal.signal(signal.SIGTERM, plexpy.sig_handler)


def main():
    """
    PlexPy application entry point. Parses arguments, setups encoding and
    initializes the application.
    """

    # Fixed paths to PlexPy
    if hasattr(sys, 'frozen'):
        plexpy.FULL_PATH = os.path.abspath(sys.executable)
    else:
        plexpy.FULL_PATH = os.path.abspath(__file__)

    plexpy.PROG_DIR = os.path.dirname(plexpy.FULL_PATH)
    plexpy.ARGS = sys.argv[1:]

    # From sickbeard
    plexpy.SYS_PLATFORM = sys.platform
    plexpy.SYS_ENCODING = None

    try:
        locale.setlocale(locale.LC_ALL, "")
        plexpy.SYS_ENCODING = locale.getpreferredencoding()
    except (locale.Error, IOError):
        pass

    # for OSes that are poorly configured I'll just force UTF-8
    if not plexpy.SYS_ENCODING or plexpy.SYS_ENCODING in ('ANSI_X3.4-1968', 'US-ASCII', 'ASCII'):
        plexpy.SYS_ENCODING = 'UTF-8'

    # Set up and gather command line arguments
    parser = argparse.ArgumentParser(
        description='A Python based monitoring and tracking tool for Plex Media Server.')

    parser.add_argument(
        '-v', '--verbose', action='store_true', help='Increase console logging verbosity')
    parser.add_argument(
        '-q', '--quiet', action='store_true', help='Turn off console logging')
    parser.add_argument(
        '-d', '--daemon', action='store_true', help='Run as a daemon')
    parser.add_argument(
        '-p', '--port', type=int, help='Force PlexPy to run on a specified port')
    parser.add_argument(
        '--dev', action='store_true', help='Start PlexPy in the development environment')
    parser.add_argument(
        '--datadir', help='Specify a directory where to store your data files')
    parser.add_argument(
        '--config', help='Specify a config file to use')
    parser.add_argument(
        '--nolaunch', action='store_true', help='Prevent browser from launching on startup')
    parser.add_argument(
        '--pidfile', help='Create a pid file (only relevant when running as a daemon)')

    args = parser.parse_args()

    if args.verbose:
        plexpy.VERBOSE = True
    if args.quiet:
        plexpy.QUIET = True

    # Do an intial setup of the logger.
    logger.initLogger(console=not plexpy.QUIET, log_dir=False,
                      verbose=plexpy.VERBOSE)

    if args.dev:
        plexpy.DEV = True
        logger.debug(u"PlexPy is running in the dev environment.")

    if args.daemon:
        if sys.platform == 'win32':
            sys.stderr.write(
                "Daemonizing not supported under Windows, starting normally\n")
        else:
            plexpy.DAEMON = True
            plexpy.QUIET = True

    if args.pidfile:
        plexpy.PIDFILE = str(args.pidfile)

        # If the pidfile already exists, plexpy may still be running, so
        # exit
        if os.path.exists(plexpy.PIDFILE):
            try:
                with open(plexpy.PIDFILE, 'r') as fp:
                    pid = int(fp.read())
                os.kill(pid, 0)
            except IOError as e:
                raise SystemExit("Unable to read PID file: %s", e)
            except OSError:
                logger.warn("PID file '%s' already exists, but PID %d is "
                            "not running. Ignoring PID file." %
                            (plexpy.PIDFILE, pid))
            else:
                # The pidfile exists and points to a live PID. plexpy may
                # still be running, so exit.
                raise SystemExit("PID file '%s' already exists. Exiting." %
                                 plexpy.PIDFILE)

        # The pidfile is only useful in daemon mode, make sure we can write the
        # file properly
        if plexpy.DAEMON:
            plexpy.CREATEPID = True

            try:
                with open(plexpy.PIDFILE, 'w') as fp:
                    fp.write("pid\n")
            except IOError as e:
                raise SystemExit("Unable to write PID file: %s", e)
        else:
            logger.warn("Not running in daemon mode. PID file creation "
                        "disabled.")

    # Determine which data directory and config file to use
    if args.datadir:
        plexpy.DATA_DIR = args.datadir
    else:
        plexpy.DATA_DIR = plexpy.PROG_DIR

    if args.config:
        config_file = args.config
    else:
        config_file = os.path.join(plexpy.DATA_DIR, config.FILENAME)

    # Try to create the DATA_DIR if it doesn't exist
    if not os.path.exists(plexpy.DATA_DIR):
        try:
            os.makedirs(plexpy.DATA_DIR)
        except OSError:
            raise SystemExit(
                'Could not create data directory: ' + plexpy.DATA_DIR + '. Exiting....')

    # Make sure the DATA_DIR is writeable
    if not os.access(plexpy.DATA_DIR, os.W_OK):
        raise SystemExit(
            'Cannot write to the data directory: ' + plexpy.DATA_DIR + '. Exiting...')

    # Put the database in the DATA_DIR
    plexpy.DB_FILE = os.path.join(plexpy.DATA_DIR, database.FILENAME)

    if plexpy.DAEMON:
        plexpy.daemonize()

    # Read config and start logging
    plexpy.initialize(config_file)

    # Start the background threads
    plexpy.start()

    # Open connection for websocket
    try:
        web_socket.start_thread()
    except:
        logger.warn(u"Websocket :: Unable to open connection.")

    # Force the http port if neccessary
    if args.port:
        http_port = args.port
        logger.info('Using forced web server port: %i', http_port)
    else:
        http_port = int(plexpy.CONFIG.HTTP_PORT)

    # Check if pyOpenSSL is installed. It is required for certificate generation
    # and for CherryPy.
    if plexpy.CONFIG.ENABLE_HTTPS:
        try:
            import OpenSSL
        except ImportError:
            logger.warn("The pyOpenSSL module is missing. Install this "
                        "module to enable HTTPS. HTTPS will be disabled.")
            plexpy.CONFIG.ENABLE_HTTPS = False

    # Try to start the server. Will exit here is address is already in use.
    web_config = {
        'http_port': http_port,
        'http_host': plexpy.CONFIG.HTTP_HOST,
        'http_root': plexpy.CONFIG.HTTP_ROOT,
        'http_environment': plexpy.CONFIG.HTTP_ENVIRONMENT,
        'http_proxy': plexpy.CONFIG.HTTP_PROXY,
        'enable_https': plexpy.CONFIG.ENABLE_HTTPS,
        'https_cert': plexpy.CONFIG.HTTPS_CERT,
        'https_key': plexpy.CONFIG.HTTPS_KEY,
        'http_username': plexpy.CONFIG.HTTP_USERNAME,
        'http_password': plexpy.CONFIG.HTTP_PASSWORD,
        'http_basic_auth': plexpy.CONFIG.HTTP_BASIC_AUTH
    }
    webstart.initialize(web_config)

    # Open webbrowser
    if plexpy.CONFIG.LAUNCH_BROWSER and not args.nolaunch and not plexpy.DEV:
        plexpy.launch_browser(plexpy.CONFIG.HTTP_HOST, http_port,
                              plexpy.CONFIG.HTTP_ROOT)

    # Wait endlessy for a signal to happen
    while True:
        if not plexpy.SIGNAL:
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                plexpy.SIGNAL = 'shutdown'
        else:
            logger.info('Received signal: %s', plexpy.SIGNAL)

            if plexpy.SIGNAL == 'shutdown':
                plexpy.shutdown()
            elif plexpy.SIGNAL == 'restart':
                plexpy.shutdown(restart=True)
            elif plexpy.SIGNAL == 'checkout':
                plexpy.shutdown(restart=True, checkout=True)
            else:
                plexpy.shutdown(restart=True, update=True)

            plexpy.SIGNAL = None

# Call main()
if __name__ == "__main__":
    main()
