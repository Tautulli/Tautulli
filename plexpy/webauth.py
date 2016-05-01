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


# http://tools.cherrypy.org/wiki/AuthenticationAndAccessRestrictions
# Form based authentication for CherryPy. Requires the
# Session tool to be loaded.

from cgi import escape
import cherrypy
from datetime import datetime, timedelta
from hashing_passwords import check_hash
import re

import plexpy
from plexpy import logger
from plexpy.database import MonitorDatabase
from plexpy.users import Users
from plexpy.plextv import PlexTV
from plexpy.pmsconnect import PmsConnect


SESSION_KEY = '_cp_username'

def user_login(username=None, password=None):
    if not username and not password:
        return None

    user_data = Users()
    
    # Try to login to Plex.tv to check if the user has a vaild account
    plex_tv = PlexTV(username=username, password=password)
    plex_user = plex_tv.get_token()
    if plex_user:
        user_token = plex_user['auth_token']
        user_id = plex_user['user_id']

        # Retrieve user token from the database and check against the Plex.tv token.
        # Also Make sure 'allow_guest' access is enabled for the user.
        # The user tokens should match if it is the same PlexPy install.
        tokens = user_data.get_tokens(user_id=user_id)
        if not tokens:
            # The user is not in the database
            return None
        elif not tokens['allow_guest'] or not user_token == tokens['user_token']:
            # Guest access is disabled, or user tokens don't match
            return None

        # Otherwise it is a new user or token is no longer valid.
        # Check if the user is in the database, not deleted, and 'allow_guest' access.
        user_details = user_data.get_details(user_id=user_id)
        if user_id == str(user_details['user_id']) and \
            not user_details['deleted_user'] and user_details['allow_guest']:

            # The user is in the database, so try to retrieve a new server token.
            # If a server token is returned, then the user is a valid friend
            plex_tv = PlexTV(token=user_token)
            server_token = plex_tv.get_server_token()
            if server_token:

                # Register the new user / update the access tokens.
                monitor_db = MonitorDatabase()
                try:
                    logger.debug(u"PlexPy Users :: Regestering tokens for user '%s' in the database." % username)
                    result = monitor_db.action('UPDATE users SET user_token = ?, server_token = ? WHERE user_id = ?',
                                               [user_token, server_token, user_id])

                    if result:
                        # Successful login
                        return True
                    else:
                        logger.warn(u"PlexPy Users :: Unable to register user '%s' in database." % username)
                        return None
                except Exception as e:
                    logger.warn(u"PlexPy Users :: Unable to register user '%s' in database: %s." % (username, e))
                    return None
            else:
                logger.warn(u"PlexPy Users :: Unable to retrieve Plex.tv server token for user '%s'." % username)
                return None
        else:
            logger.warn(u"PlexPy Users :: Unable to register user '%s'. User not in the database." % username)
            return None
    else:
        logger.warn(u"PlexPy Users :: Unable to retrieve Plex.tv user token for user '%s'." % username)
        return None

    return None

def check_credentials(username, password, admin_login='0'):
    """Verifies credentials for username and password.
    Returns True and the user group on success or False and no user group"""

    if plexpy.CONFIG.HTTP_HASHED_PASSWORD and \
        username == plexpy.CONFIG.HTTP_USERNAME and check_hash(password, plexpy.CONFIG.HTTP_PASSWORD):
        return True, u'admin'
    elif username == plexpy.CONFIG.HTTP_USERNAME and password == plexpy.CONFIG.HTTP_PASSWORD:
        return True, u'admin'
    elif not admin_login == '1' and plexpy.CONFIG.ALLOW_GUEST_ACCESS and user_login(username, password):
        return True, u'guest'
    else:
        return False, None
    
def check_auth(*args, **kwargs):
    """A tool that looks in config for 'auth.require'. If found and it
    is not None, a login is required and the entry is evaluated as a list of
    conditions that the user must fulfill"""
    conditions = cherrypy.request.config.get('auth.require', None)
    if conditions is not None:
        _session = cherrypy.session.get(SESSION_KEY)

        if _session and (_session['user'] and _session['expiry']) and _session['expiry'] > datetime.now():
            cherrypy.request.login = _session['user']
            for condition in conditions:
                # A condition is just a callable that returns true or false
                if not condition():
                    raise cherrypy.HTTPRedirect(plexpy.HTTP_ROOT)
        else:
            raise cherrypy.HTTPRedirect("auth/logout")
    
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

def member_of(groupname):
    def check():
        # replace with actual check if <username> is in <groupname>
        return cherrypy.request.login == plexpy.CONFIG.HTTP_USERNAME and groupname == 'admin'
    return check

def name_is(reqd_username):
    return lambda: reqd_username == cherrypy.request.login

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
    
    def on_login(self, username):
        """Called on successful login"""
        logger.debug(u"User '%s' logged into PlexPy." % username)
    
    def on_logout(self, username):
        """Called on logout"""
        logger.debug(u"User '%s' logged out of PlexPy." % username)
    
    def get_loginform(self, username="", msg=""):
        from plexpy.webserve import serve_template
        return serve_template(templatename="login.html", title="Login", username=escape(username, True), msg=msg)
    
    @cherrypy.expose
    def index(self):
        raise cherrypy.HTTPRedirect("login")

    @cherrypy.expose
    def login(self, username=None, password=None, remember_me='0', admin_login='0'):
        if not cherrypy.config.get('tools.sessions.on'):
            raise cherrypy.HTTPRedirect(plexpy.HTTP_ROOT)

        if username is None or password is None:
            return self.get_loginform()
        
        (vaild_login, user_group) = check_credentials(username, password, admin_login)

        if vaild_login:
            if user_group == 'guest':
                if re.match(r"[^@]+@[^@]+\.[^@]+", username):
                    user_details = Users().get_details(email=username)
                else:
                    user_details = Users().get_details(user=username)

                user_id = user_details['user_id']
            else:
                user_id = None

            expiry = datetime.now() + (timedelta(days=30) if remember_me == '1' else timedelta(minutes=60))

            cherrypy.session.regenerate()
            cherrypy.request.login = username
            cherrypy.session[SESSION_KEY] = {'user_id': user_id,
                                             'user': username,
                                             'user_group': user_group,
                                             'expiry': expiry}

            self.on_login(username)
            raise cherrypy.HTTPRedirect(plexpy.HTTP_ROOT)

        elif admin_login == '1':
            logger.debug(u"Invalid admin login attempt from '%s'." % username)
            raise cherrypy.HTTPRedirect(plexpy.HTTP_ROOT)
        else:
            logger.debug(u"Invalid login attempt from '%s'." % username)
            return self.get_loginform(username, u"Incorrect username/email or password.")
    
    @cherrypy.expose
    def logout(self):
        if not cherrypy.config.get('tools.sessions.on'):
            raise cherrypy.HTTPRedirect(plexpy.HTTP_ROOT)

        _session = cherrypy.session.get(SESSION_KEY)
        cherrypy.session[SESSION_KEY] = None

        if _session and _session['user']:
            cherrypy.request.login = None
            self.on_logout(_session['user'])
        raise cherrypy.HTTPRedirect("login")