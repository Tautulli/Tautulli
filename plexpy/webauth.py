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


# http://tools.cherrypy.org/wiki/AuthenticationAndAccessRestrictions
# Form based authentication for CherryPy. Requires the
# Session tool to be loaded.

from datetime import datetime, timedelta
import re

import cherrypy
from hashing_passwords import check_hash
import jwt

import plexpy
import logger
from plexpy.database import MonitorDatabase
from plexpy.users import Users, refresh_users
from plexpy.plextv import PlexTV


JWT_ALGORITHM = 'HS256'
JWT_COOKIE_NAME = 'tautulli_token_'


def user_login(username=None, password=None):
    if not username or not password:
        return None

    # Try to login to Plex.tv to check if the user has a vaild account
    plex_tv = PlexTV(username=username, password=password)
    plex_user = plex_tv.get_token()
    if plex_user:
        user_token = plex_user['auth_token']
        user_id = plex_user['user_id']

        # Try to retrieve the user from the database.
        # Also make sure guest access is enabled for the user and the user is not deleted.
        user_data = Users()
        user_details = user_data.get_details(user_id=user_id)
        if user_id != str(user_details['user_id']):
            # The user is not in the database.
            return None
        elif plexpy.CONFIG.HTTP_PLEX_ADMIN and user_details['is_admin']:
            # Plex admin login
            return 'admin'
        elif not user_details['allow_guest'] or user_details['deleted_user']:
            # Guest access is disabled or the user is deleted.
            return None

        # Stop here if guest access is not enabled
        if not plexpy.CONFIG.ALLOW_GUEST_ACCESS:
            return None

        # The user is in the database, and guest access is enabled, so try to retrieve a server token.
        # If a server token is returned, then the user is a valid friend of the server.
        plex_tv = PlexTV(token=user_token)
        server_token = plex_tv.get_server_token()
        if server_token:

            # Register the new user / update the access tokens.
            monitor_db = MonitorDatabase()
            try:
                logger.debug(u"Tautulli WebAuth :: Regestering tokens for user '%s' in the database." % username)
                result = monitor_db.action('UPDATE users SET user_token = ?, server_token = ? WHERE user_id = ?',
                                            [user_token, server_token, user_id])

                if result:
                    # Refresh the users list to make sure we have all the correct permissions.
                    refresh_users()
                    # Successful login
                    return 'guest'
                else:
                    logger.warn(u"Tautulli WebAuth :: Unable to register user '%s' in database." % username)
                    return None
            except Exception as e:
                logger.warn(u"Tautulli WebAuth :: Unable to register user '%s' in database: %s." % (username, e))
                return None
        else:
            logger.warn(u"Tautulli WebAuth :: Unable to retrieve Plex.tv server token for user '%s'." % username)
            return None
    else:
        logger.warn(u"Tautulli WebAuth :: Unable to retrieve Plex.tv user token for user '%s'." % username)
        return None

    return None


def check_credentials(username, password, admin_login='0'):
    """Verifies credentials for username and password.
    Returns True and the user group on success or False and no user group"""

    if plexpy.CONFIG.HTTP_PASSWORD:
        if plexpy.CONFIG.HTTP_HASHED_PASSWORD and \
                username == plexpy.CONFIG.HTTP_USERNAME and check_hash(password, plexpy.CONFIG.HTTP_PASSWORD):
            return True, 'admin'
        elif not plexpy.CONFIG.HTTP_HASHED_PASSWORD and \
                username == plexpy.CONFIG.HTTP_USERNAME and password == plexpy.CONFIG.HTTP_PASSWORD:
            return True, 'admin'

    if plexpy.CONFIG.HTTP_PLEX_ADMIN or (not admin_login == '1' and plexpy.CONFIG.ALLOW_GUEST_ACCESS):
        plex_login = user_login(username, password)
        if plex_login is not None:
            return True, plex_login

    return False, None


def check_jwt_token():
    jwt_cookie = JWT_COOKIE_NAME + plexpy.CONFIG.PMS_UUID
    jwt_token = cherrypy.request.cookie.get(jwt_cookie)

    if jwt_token:
        try:
            payload = jwt.decode(
                jwt_token.value, plexpy.CONFIG.JWT_SECRET, leeway=timedelta(seconds=10), algorithms=[JWT_ALGORITHM]
            )
        except (jwt.DecodeError, jwt.ExpiredSignatureError):
            return None

        return payload


def check_auth(*args, **kwargs):
    """A tool that looks in config for 'auth.require'. If found and it
    is not None, a login is required and the entry is evaluated as a list of
    conditions that the user must fulfill"""
    conditions = cherrypy.request.config.get('auth.require', None)
    if conditions is not None:
        payload = check_jwt_token()

        if payload:
            cherrypy.request.login = payload

            for condition in conditions:
                # A condition is just a callable that returns true or false
                if not condition():
                    raise cherrypy.HTTPRedirect(plexpy.HTTP_ROOT)

        else:
            raise cherrypy.HTTPRedirect(plexpy.HTTP_ROOT + "auth/logout")


def requireAuth(*conditions):
    """A decorator that appends conditions to the auth.require config
    variable."""
    def decorate(f):
        if not hasattr(f, '_cp_config'):
            f._cp_config = dict()
        if 'auth.require' not in f._cp_config:
            f._cp_config['auth.require'] = []
        f._cp_config['auth.require'].extend(conditions)
        return f
    return decorate


# Conditions are callables that return True
# if the user fulfills the conditions they define, False otherwise
#
# They can access the current username as cherrypy.request.login
#
# Define those at will however suits the application.

def member_of(user_group):
    return lambda: cherrypy.request.login and cherrypy.request.login['user_group'] == user_group


def name_is(user_name):
    return lambda: cherrypy.request.login and cherrypy.request.login['user'] == user_name


# These might be handy

def any_of(*conditions):
    """Returns True if any of the conditions match"""
    def check():
        for c in conditions:
            if c():
                return True
        return False
    return check


# By default all conditions are required, but this might still be
# needed if you want to use it inside of an any_of(...) condition
def all_of(*conditions):
    """Returns True if all of the conditions match"""
    def check():
        for c in conditions:
            if not c():
                return False
        return True
    return check


# Controller to provide login and logout actions

class AuthController(object):

    def check_auth_enabled(self):
        if not plexpy.CONFIG.HTTP_BASIC_AUTH and plexpy.CONFIG.HTTP_PASSWORD:
            return
        raise cherrypy.HTTPRedirect(plexpy.HTTP_ROOT)

    def on_login(self, user_id, username, user_group):
        """Called on successful login"""

        # Save login to the database
        ip_address = cherrypy.request.headers.get('X-Forwarded-For', cherrypy.request.headers.get('Remote-Addr'))
        host = cherrypy.request.headers.get('Origin')
        user_agent = cherrypy.request.headers.get('User-Agent')

        Users().set_user_login(user_id=user_id,
                               user=username,
                               user_group=user_group,
                               ip_address=ip_address,
                               host=host,
                               user_agent=user_agent,
                               success=1)

        logger.debug(u"Tautulli WebAuth :: %s user '%s' logged into Tautulli." % (user_group.capitalize(), username))
    
    def on_logout(self, username, user_group):
        """Called on logout"""
        logger.debug(u"Tautulli WebAuth :: %s user '%s' logged out of Tautulli." % (user_group.capitalize(), username))
    
    def on_login_failed(self, username):
        """Called on failed login"""

        # Save login attempt to the database
        ip_address = cherrypy.request.headers.get('X-Forwarded-For', cherrypy.request.headers.get('Remote-Addr'))
        host = cherrypy.request.headers.get('Origin')
        user_agent = cherrypy.request.headers.get('User-Agent')

        Users().set_user_login(user=username,
                               ip_address=ip_address,
                               host=host,
                               user_agent=user_agent,
                               success=0)

    def get_loginform(self):
        from plexpy.webserve import serve_template
        return serve_template(templatename="login.html", title="Login")
    
    @cherrypy.expose
    def index(self):
        raise cherrypy.HTTPRedirect(plexpy.HTTP_ROOT + "auth/login")

    @cherrypy.expose
    def login(self):
        self.check_auth_enabled()

        return self.get_loginform()

    @cherrypy.expose
    def logout(self):
        self.check_auth_enabled()

        payload = check_jwt_token()
        if payload:
            self.on_logout(payload['user'], payload['user_group'])

        jwt_cookie = JWT_COOKIE_NAME + plexpy.CONFIG.PMS_UUID
        cherrypy.response.cookie[jwt_cookie] = 'expire'
        cherrypy.response.cookie[jwt_cookie]['expires'] = 0
        cherrypy.response.cookie[jwt_cookie]['path'] = '/'

        cherrypy.request.login = None
        raise cherrypy.HTTPRedirect(plexpy.HTTP_ROOT + "auth/login")

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def signin(self, username=None, password=None, remember_me='0', admin_login='0'):
        if cherrypy.request.method != 'POST':
            cherrypy.response.status = 405
            return {'status': 'error', 'message': 'Sign in using POST.'}

        error_message = {'status': 'error', 'message': 'Incorrect username or password.'}

        valid_login, user_group = check_credentials(username, password, admin_login)

        if valid_login:
            if user_group == 'guest':
                if re.match(r"[^@]+@[^@]+\.[^@]+", username):
                    user_details = Users().get_details(email=username)
                else:
                    user_details = Users().get_details(user=username)

                user_id = user_details['user_id']
            else:
                user_id = None

            time_delta = timedelta(days=30) if remember_me == '1' else timedelta(minutes=60)
            expiry = datetime.utcnow() + time_delta

            payload = {
                'user_id': user_id,
                'user': username,
                'user_group': user_group,
                'exp': expiry
            }

            jwt_token = jwt.encode(payload, plexpy.CONFIG.JWT_SECRET, algorithm=JWT_ALGORITHM)

            self.on_login(user_id, username, user_group)

            jwt_cookie = JWT_COOKIE_NAME + plexpy.CONFIG.PMS_UUID
            cherrypy.response.cookie[jwt_cookie] = jwt_token
            cherrypy.response.cookie[jwt_cookie]['expires'] = int(time_delta.total_seconds())
            cherrypy.response.cookie[jwt_cookie]['path'] = '/'

            cherrypy.request.login = payload
            cherrypy.response.status = 200
            return {'status': 'success', 'token': jwt_token.decode('utf-8'), 'uuid': plexpy.CONFIG.PMS_UUID}

        elif admin_login == '1':
            self.on_login_failed(username)
            logger.debug(u"Tautulli WebAuth :: Invalid admin login attempt from '%s'." % username)
            cherrypy.response.status = 401
            return error_message

        else:
            self.on_login_failed(username)
            logger.debug(u"Tautulli WebAuth :: Invalid login attempt from '%s'." % username)
            cherrypy.response.status = 401
            return error_message
