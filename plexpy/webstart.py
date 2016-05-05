#  This file is part of PlexPy.
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

import os
import sys

import cherrypy
from plexpy import logger, webauth
import plexpy
from plexpy.helpers import create_https_certificates
from plexpy.webserve import WebInterface



def initialize(options):

    # HTTPS stuff stolen from sickbeard
    enable_https = options['enable_https']
    https_cert = options['https_cert']
    https_key = options['https_key']

    if enable_https:
        # If either the HTTPS certificate or key do not exist, try to make self-signed ones.
        if plexpy.CONFIG.HTTPS_CREATE_CERT and \
            (not (https_cert and os.path.exists(https_cert)) or not (https_key and os.path.exists(https_key))):
            if not create_https_certificates(https_cert, https_key):
                logger.warn("Unable to create certificate and key. Disabling HTTPS")
                enable_https = False

        if not (os.path.exists(https_cert) and os.path.exists(https_key)):
            logger.warn("Disabled HTTPS because of missing certificate and key.")
            enable_https = False

    options_dict = {
        'server.socket_port': options['http_port'],
        'server.socket_host': options['http_host'],
        'environment': options['http_environment'],
        'server.thread_pool': 10,
        'tools.encode.on': True,
        'tools.encode.encoding': 'utf-8',
        'tools.decode.on': True
    }

    if plexpy.DEV:
        options_dict['environment'] = "test_suite"
        options_dict['engine.autoreload.on'] = True

    if enable_https:
        options_dict['server.ssl_certificate'] = https_cert
        options_dict['server.ssl_private_key'] = https_key
        protocol = "https"
    else:
        protocol = "http"

    if options['http_password']:
        logger.info("Web server authentication is enabled, username is '%s'", options['http_username'])
        options_dict['tools.sessions.on'] = auth_enabled = session_enabled = True
        cherrypy.tools.auth = cherrypy.Tool('before_handler', webauth.check_auth)
    else:
        auth_enabled = session_enabled = False

    if not options['http_root'] or options['http_root'] == '/':
        plexpy.HTTP_ROOT = options['http_root'] = '/'
    else:
        plexpy.HTTP_ROOT = options['http_root'] = '/' + options['http_root'].strip('/') + '/'

    cherrypy.config.update(options_dict)

    conf = {
        '/': {
            'tools.staticdir.root': os.path.join(plexpy.PROG_DIR, 'data'),
            'tools.proxy.on': options['http_proxy'],  # pay attention to X-Forwarded-Proto header
            'tools.gzip.on': True,
            'tools.gzip.mime_types': ['text/html', 'text/plain', 'text/css',
                                      'text/javascript', 'application/json',
                                      'application/javascript'],
            'tools.auth.on': auth_enabled,
            'tools.sessions.on': session_enabled,
            'tools.sessions.timeout': 30 * 24 * 60  # 30 days
        },
        '/interfaces': {
            'tools.staticdir.on': True,
            'tools.staticdir.dir': "interfaces",
            'tools.caching.on': True,
            'tools.caching.force': True,
            'tools.caching.delay': 0,
            'tools.expires.on': True,
            'tools.expires.secs': 60 * 60 * 24 * 30,  # 30 days
            'tools.auth.on': False,
            'tools.sessions.on': False
        },
        '/images': {
            'tools.staticdir.on': True,
            'tools.staticdir.dir': "interfaces/default/images",
            'tools.caching.on': True,
            'tools.caching.force': True,
            'tools.caching.delay': 0,
            'tools.expires.on': True,
            'tools.expires.secs': 60 * 60 * 24 * 30,  # 30 days
            'tools.auth.on': False,
            'tools.sessions.on': False
        },
        '/css': {
            'tools.staticdir.on': True,
            'tools.staticdir.dir': "interfaces/default/css",
            'tools.caching.on': True,
            'tools.caching.force': True,
            'tools.caching.delay': 0,
            'tools.expires.on': True,
            'tools.expires.secs': 60 * 60 * 24 * 30,  # 30 days
            'tools.auth.on': False,
            'tools.sessions.on': False
        },
        '/fonts': {
            'tools.staticdir.on': True,
            'tools.staticdir.dir': "interfaces/default/fonts",
            'tools.caching.on': True,
            'tools.caching.force': True,
            'tools.caching.delay': 0,
            'tools.expires.on': True,
            'tools.expires.secs': 60 * 60 * 24 * 30,  # 30 days
            'tools.auth.on': False,
            'tools.sessions.on': False
        },
        '/js': {
            'tools.staticdir.on': True,
            'tools.staticdir.dir': "interfaces/default/js",
            'tools.caching.on': True,
            'tools.caching.force': True,
            'tools.caching.delay': 0,
            'tools.expires.on': True,
            'tools.expires.secs': 60 * 60 * 24 * 30,  # 30 days
            'tools.auth.on': False,
            'tools.sessions.on': False
        },
        '/json': {
            'tools.staticdir.on': True,
            'tools.staticdir.dir': "interfaces/default/json",
            'tools.caching.on': True,
            'tools.caching.force': True,
            'tools.caching.delay': 0,
            'tools.expires.on': True,
            'tools.expires.secs': 60 * 60 * 24 * 30,  # 30 days
            'tools.auth.on': False,
            'tools.sessions.on': False
        },
        '/xml': {
            'tools.staticdir.on': True,
            'tools.staticdir.dir': "interfaces/default/xml",
            'tools.caching.on': True,
            'tools.caching.force': True,
            'tools.caching.delay': 0,
            'tools.expires.on': True,
            'tools.expires.secs': 60 * 60 * 24 * 30,  # 30 days
            'tools.auth.on': False,
            'tools.sessions.on': False
        },
        '/cache': {
            'tools.staticdir.on': True,
            'tools.staticdir.dir': plexpy.CONFIG.CACHE_DIR,
            'tools.caching.on': True,
            'tools.caching.force': True,
            'tools.caching.delay': 0,
            'tools.expires.on': True,
            'tools.expires.secs': 60 * 60 * 24 * 30,  # 30 days
            'tools.auth.on': False,
            'tools.sessions.on': False
        },
        '/pms_image_proxy': {
            'tools.staticdir.on': True,
            'tools.staticdir.dir': os.path.join(plexpy.CONFIG.CACHE_DIR, 'images'),
            'tools.caching.on': True,
            'tools.caching.force': True,
            'tools.caching.delay': 0,
            'tools.expires.on': True,
            'tools.expires.secs': 60 * 60 * 24 * 30,  # 30 days
            'tools.auth.on': False,
            'tools.sessions.on': False
        },
        '/favicon.ico': {
            'tools.staticfile.on': True,
            'tools.staticfile.filename': os.path.abspath(os.path.join(plexpy.PROG_DIR, 'data/interfaces/default/images/favicon.ico')),
            'tools.caching.on': True,
            'tools.caching.force': True,
            'tools.caching.delay': 0,
            'tools.expires.on': True,
            'tools.expires.secs': 60 * 60 * 24 * 30,  # 30 days
            'tools.auth.on': False,
            'tools.sessions.on': False
        },
    }

    # Prevent time-outs
    cherrypy.engine.timeout_monitor.unsubscribe()
    cherrypy.tree.mount(WebInterface(), options['http_root'], config=conf)

    try:
        logger.info("Starting PlexPy web server on %s://%s:%d%s", protocol,
                    options['http_host'], options['http_port'], options['http_root'])
        cherrypy.process.servers.check_port(str(options['http_host']), options['http_port'])
        if not plexpy.DEV:
            cherrypy.server.start()
        else:
            cherrypy.engine.signals.subscribe()
            cherrypy.engine.start()
            cherrypy.engine.block()
    except IOError:
        sys.stderr.write('Failed to start on port: %i. Is something else running?\n' % (options['http_port']))
        sys.exit(1)

    cherrypy.server.wait()
