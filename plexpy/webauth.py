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

import cherrypy
from cgi import escape
from hashing_passwords import check_hash

import plexpy
from plexpy import logger


SESSION_KEY = '_cp_username'

def check_credentials(username, password):
    """Verifies credentials for username and password.
    Returns None on success or a string describing the error on failure"""
    if plexpy.CONFIG.HTTP_HASHED_PASSWORD and \
        username == plexpy.CONFIG.HTTP_USERNAME and check_hash(password, plexpy.CONFIG.HTTP_PASSWORD):
        return None
    elif username == plexpy.CONFIG.HTTP_USERNAME and password == plexpy.CONFIG.HTTP_PASSWORD:
        return None
    else:
        return u"Incorrect username or password."
    
    # An example implementation which uses an ORM could be:
    # u = User.get(username)
    # if u is None:
    #     return u"Username %s is unknown to me." % username
    # if u.password != md5.new(password).hexdigest():
    #     return u"Incorrect password"

def check_auth(*args, **kwargs):
    """A tool that looks in config for 'auth.require'. If found and it
    is not None, a login is required and the entry is evaluated as a list of
    conditions that the user must fulfill"""
    conditions = cherrypy.request.config.get('auth.require', None)
    if conditions is not None:
        username = cherrypy.session.get(SESSION_KEY)
        if username:
            cherrypy.request.login = username
            for condition in conditions:
                # A condition is just a callable that returns true or false
                if not condition():
                    raise cherrypy.HTTPRedirect("auth/login")
        else:
            raise cherrypy.HTTPRedirect("auth/login")
    
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

        username = escape(username, True)

        return serve_template(templatename="login.html", title="Login", username=username, msg=msg)
    
    @cherrypy.expose
    def index(self):
        raise cherrypy.HTTPRedirect("login")

    @cherrypy.expose
    def login(self, username=None, password=None, remember_me=0):
        if not plexpy.CONFIG.HTTP_PASSWORD:
            raise cherrypy.HTTPRedirect(plexpy.HTTP_ROOT)

        if username is None or password is None:
            return self.get_loginform()
        
        error_msg = check_credentials(username, password)

        if error_msg:
            logger.debug(u"Invalid login attempt from '%s'." % username)
            return self.get_loginform(username, error_msg)
        else:
            cherrypy.session.regenerate()
            cherrypy.session[SESSION_KEY] = cherrypy.request.login = username
            self.on_login(username)
            raise cherrypy.HTTPRedirect(plexpy.HTTP_ROOT)
    
    @cherrypy.expose
    def logout(self):
        if not plexpy.CONFIG.HTTP_PASSWORD:
            raise cherrypy.HTTPRedirect(plexpy.HTTP_ROOT)

        sess = cherrypy.session
        username = sess.get(SESSION_KEY, None)
        sess[SESSION_KEY] = None

        if username:
            cherrypy.request.login = None
            self.on_logout(username)
        raise cherrypy.HTTPRedirect("login")