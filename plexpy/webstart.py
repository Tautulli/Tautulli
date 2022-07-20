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
import sys

import cherrypy
import portend

import plexpy
from plexpy import logger
from plexpy import webauth
from plexpy.helpers import create_https_certificates
from plexpy.webserve import WebInterface


def initialize(options):

    # HTTPS stuff stolen from sickbeard
    enable_https = options['enable_https']
    https_cert = options['https_cert']
    https_cert_chain = options['https_cert_chain']
    https_key = options['https_key']

    if enable_https:
        # If either the HTTPS certificate or key do not exist, try to make self-signed ones.
        if plexpy.CONFIG.HTTPS_CREATE_CERT and \
                (not (https_cert and os.path.exists(https_cert)) or
                 not (https_key and os.path.exists(https_key))):
            if not create_https_certificates(https_cert, https_key):
                logger.warn(u"Tautulli WebStart :: Unable to create certificate and key. Disabling HTTPS")
                enable_https = False

        if not (os.path.exists(https_cert) and os.path.exists(https_key)):
            logger.warn(u"Tautulli WebStart :: Disabled HTTPS because of missing certificate and key.")
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
        options_dict['server.ssl_certificate_chain'] = https_cert_chain
        options_dict['server.ssl_private_key'] = https_key
        protocol = "https"
    else:
        protocol = "http"

    if options['http_proxy']:
        # Overwrite cherrypy.tools.proxy with our own proxy handler
        cherrypy.tools.proxy = cherrypy.Tool('before_handler', proxy, priority=1)

    if options['http_password']:
        login_allowed = ["Tautulli admin (username is '%s')" % options['http_username']]
        if plexpy.CONFIG.HTTP_PLEX_ADMIN:
            login_allowed.append("Plex admin")

        logger.info(u"Tautulli WebStart :: Web server authentication is enabled: %s.", ' and '.join(login_allowed))

        if options['http_basic_auth']:
            auth_enabled = False
            basic_auth_enabled = True
        else:
            auth_enabled = True
            basic_auth_enabled = False
            cherrypy.tools.auth = cherrypy.Tool('before_handler', webauth.check_auth, priority=2)
    else:
        auth_enabled = basic_auth_enabled = False

    if options['http_root'].strip('/'):
        plexpy.HTTP_ROOT = options['http_root'] = '/' + options['http_root'].strip('/') + '/'
    else:
        plexpy.HTTP_ROOT = options['http_root'] = '/'

    cherrypy.config.update(options_dict)

    conf = {
        '/': {
            'tools.staticdir.root': os.path.join(plexpy.PROG_DIR, 'data'),
            'tools.proxy.on': bool(options['http_proxy']),
            'tools.gzip.on': True,
            'tools.gzip.mime_types': ['text/html', 'text/plain', 'text/css',
                                      'text/javascript', 'application/json',
                                      'application/javascript'],
            'tools.auth.on': auth_enabled,
            'tools.auth_basic.on': basic_auth_enabled,
            'tools.auth_basic.realm': 'Tautulli web server',
            'tools.auth_basic.checkpassword': cherrypy.lib.auth_basic.checkpassword_dict({
                options['http_username']: options['http_password']})
        },
        '/api': {
            'tools.auth_basic.on': False
        },
        '/interfaces': {
            'tools.staticdir.on': True,
            'tools.staticdir.dir': "interfaces",
            'tools.caching.on': True,
            'tools.caching.force': True,
            'tools.caching.delay': 0,
            'tools.expires.on': True,
            'tools.expires.secs': 60 * 60 * 24 * 30,  # 30 days
            'tools.sessions.on': False,
            'tools.auth.on': False
        },
        '/images': {
            'tools.staticdir.on': True,
            'tools.staticdir.dir': "interfaces/default/images",
            'tools.staticdir.content_types': {'svg': 'image/svg+xml'},
            'tools.caching.on': True,
            'tools.caching.force': True,
            'tools.caching.delay': 0,
            'tools.expires.on': True,
            'tools.expires.secs': 60 * 60 * 24 * 30,  # 30 days
            'tools.sessions.on': False,
            'tools.auth.on': False
        },
        '/css': {
            'tools.staticdir.on': True,
            'tools.staticdir.dir': "interfaces/default/css",
            'tools.caching.on': True,
            'tools.caching.force': True,
            'tools.caching.delay': 0,
            'tools.expires.on': True,
            'tools.expires.secs': 60 * 60 * 24 * 30,  # 30 days
            'tools.sessions.on': False,
            'tools.auth.on': False
        },
        '/fonts': {
            'tools.staticdir.on': True,
            'tools.staticdir.dir': "interfaces/default/fonts",
            'tools.caching.on': True,
            'tools.caching.force': True,
            'tools.caching.delay': 0,
            'tools.expires.on': True,
            'tools.expires.secs': 60 * 60 * 24 * 30,  # 30 days
            'tools.sessions.on': False,
            'tools.auth.on': False
        },
        '/js': {
            'tools.staticdir.on': True,
            'tools.staticdir.dir': "interfaces/default/js",
            'tools.caching.on': True,
            'tools.caching.force': True,
            'tools.caching.delay': 0,
            'tools.expires.on': True,
            'tools.expires.secs': 60 * 60 * 24 * 30,  # 30 days
            'tools.sessions.on': False,
            'tools.auth.on': False
        },
        '/cache': {
            'tools.staticdir.on': True,
            'tools.staticdir.dir': plexpy.CONFIG.CACHE_DIR,
            'tools.caching.on': True,
            'tools.caching.force': True,
            'tools.caching.delay': 0,
            'tools.expires.on': True,
            'tools.expires.secs': 60 * 60 * 24 * 30,  # 30 days
            'tools.sessions.on': False,
            'tools.auth.on': False
        },
        #'/pms_image_proxy': {
        #    'tools.staticdir.on': True,
        #    'tools.staticdir.dir': os.path.join(plexpy.CONFIG.CACHE_DIR, 'images'),
        #    'tools.caching.on': True,
        #    'tools.caching.force': True,
        #    'tools.caching.delay': 0,
        #    'tools.expires.on': True,
        #    'tools.expires.secs': 60 * 60 * 24 * 30,  # 30 days
        #    'tools.auth.on': False,
        #    'tools.sessions.on': False
        #},
        '/favicon.ico': {
            'tools.staticfile.on': True,
            'tools.staticfile.filename': os.path.abspath(os.path.join(plexpy.PROG_DIR, 'data/interfaces/default/images/favicon/favicon.ico')),
            'tools.caching.on': True,
            'tools.caching.force': True,
            'tools.caching.delay': 0,
            'tools.expires.on': True,
            'tools.expires.secs': 60 * 60 * 24 * 30,  # 30 days
            'tools.sessions.on': False,
            'tools.auth.on': False
        }
    }

    # Prevent time-outs
    #cherrypy.engine.timeout_monitor.unsubscribe()
    cherrypy.tree.mount(WebInterface(), options['http_root'], config=conf)
    if plexpy.HTTP_ROOT != '/':
        cherrypy.tree.mount(BaseRedirect(), '/')

    try:
        logger.info(u"Tautulli WebStart :: Starting Tautulli web server on %s://%s:%d%s", protocol,
                    options['http_host'], options['http_port'], options['http_root'])
        portend.free(str(options['http_host']), options['http_port'])
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


class BaseRedirect(object):
    @cherrypy.expose
    def index(self):
        raise cherrypy.HTTPRedirect(plexpy.HTTP_ROOT)


def proxy():
    # logger.debug(u"REQUEST URI: %s, HEADER [X-Forwarded-Host]: %s, [X-Host]: %s, [Origin]: %s, [Host]: %s",
    #              cherrypy.request.wsgi_environ['REQUEST_URI'],
    #              cherrypy.request.headers.get('X-Forwarded-Host'),
    #              cherrypy.request.headers.get('X-Host'),
    #              cherrypy.request.headers.get('Origin'),
    #              cherrypy.request.headers.get('Host'))

    # Change cherrpy.tools.proxy.local header if X-Forwarded-Host header is not present
    local = 'X-Forwarded-Host'
    if not cherrypy.request.headers.get('X-Forwarded-Host'):
        if cherrypy.request.headers.get('X-Host'):  # lighttpd
            local = 'X-Host'
        elif cherrypy.request.headers.get('Origin'):  # Squid
            local = 'Origin'
        elif cherrypy.request.headers.get('Host'):  # nginx
            local = 'Host'
        # logger.debug(u"cherrypy.tools.proxy.local set to [%s]", local)

    # Call original cherrypy proxy tool with the new local
    cherrypy.lib.cptools.proxy(local=local)
