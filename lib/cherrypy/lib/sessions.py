"""Session implementation for CherryPy.

You need to edit your config file to use sessions. Here's an example::

    [/]
    tools.sessions.on = True
    tools.sessions.storage_class = cherrypy.lib.sessions.FileSession
    tools.sessions.storage_path = "/home/site/sessions"
    tools.sessions.timeout = 60

This sets the session to be stored in files in the directory
/home/site/sessions, and the session timeout to 60 minutes. If you omit
``storage_class``, the sessions will be saved in RAM.
``tools.sessions.on`` is the only required line for working sessions,
the rest are optional.

By default, the session ID is passed in a cookie, so the client's browser must
have cookies enabled for your site.

To set data for the current session, use
``cherrypy.session['fieldname'] = 'fieldvalue'``;
to get data use ``cherrypy.session.get('fieldname')``.

================
Locking sessions
================

By default, the ``'locking'`` mode of sessions is ``'implicit'``, which means
the session is locked early and unlocked late. Be mindful of this default mode
for any requests that take a long time to process (streaming responses,
expensive calculations, database lookups, API calls, etc), as other concurrent
requests that also utilize sessions will hang until the session is unlocked.

If you want to control when the session data is locked and unlocked,
set ``tools.sessions.locking = 'explicit'``. Then call
``cherrypy.session.acquire_lock()`` and ``cherrypy.session.release_lock()``.
Regardless of which mode you use, the session is guaranteed to be unlocked when
the request is complete.

=================
Expiring Sessions
=================

You can force a session to expire with :func:`cherrypy.lib.sessions.expire`.
Simply call that function at the point you want the session to expire, and it
will cause the session cookie to expire client-side.

===========================
Session Fixation Protection
===========================

If CherryPy receives, via a request cookie, a session id that it does not
recognize, it will reject that id and create a new one to return in the
response cookie. This `helps prevent session fixation attacks
<http://en.wikipedia.org/wiki/Session_fixation#Regenerate_SID_on_each_request>`_.
However, CherryPy "recognizes" a session id by looking up the saved session
data for that id. Therefore, if you never save any session data,
**you will get a new session id for every request**.

A side effect of CherryPy overwriting unrecognised session ids is that if you
have multiple, separate CherryPy applications running on a single domain (e.g.
on different ports), each app will overwrite the other's session id because by
default they use the same cookie name (``"session_id"``) but do not recognise
each others sessions. It is therefore a good idea to use a different name for
each, for example::

    [/]
    ...
    tools.sessions.name = "my_app_session_id"

================
Sharing Sessions
================

If you run multiple instances of CherryPy (for example via mod_python behind
Apache prefork), you most likely cannot use the RAM session backend, since each
instance of CherryPy will have its own memory space. Use a different backend
instead, and verify that all instances are pointing at the same file or db
location. Alternately, you might try a load balancer which makes sessions
"sticky". Google is your friend, there.

================
Expiration Dates
================

The response cookie will possess an expiration date to inform the client at
which point to stop sending the cookie back in requests. If the server time
and client time differ, expect sessions to be unreliable. **Make sure the
system time of your server is accurate**.

CherryPy defaults to a 60-minute session timeout, which also applies to the
cookie which is sent to the client. Unfortunately, some versions of Safari
("4 public beta" on Windows XP at least) appear to have a bug in their parsing
of the GMT expiration date--they appear to interpret the date as one hour in
the past. Sixty minutes minus one hour is pretty close to zero, so you may
experience this bug as a new session id for every request, unless the requests
are less than one second apart. To fix, try increasing the session.timeout.

On the other extreme, some users report Firefox sending cookies after their
expiration date, although this was on a system with an inaccurate system time.
Maybe FF doesn't trust system time.
"""
import sys
import datetime
import os
import time
import threading
import binascii
import pickle

import zc.lockfile

import cherrypy
from cherrypy.lib import httputil
from cherrypy.lib import locking
from cherrypy.lib import is_iterator


missing = object()


class Session(object):

    """A CherryPy dict-like Session object (one per request)."""

    _id = None

    id_observers = None
    "A list of callbacks to which to pass new id's."

    @property
    def id(self):
        """Return the current session id."""
        return self._id

    @id.setter
    def id(self, value):
        self._id = value
        for o in self.id_observers:
            o(value)

    timeout = 60
    'Number of minutes after which to delete session data.'

    locked = False
    """
    If True, this session instance has exclusive read/write access
    to session data."""

    loaded = False
    """
    If True, data has been retrieved from storage. This should happen
    automatically on the first attempt to access session data."""

    clean_thread = None
    'Class-level Monitor which calls self.clean_up.'

    clean_freq = 5
    'The poll rate for expired session cleanup in minutes.'

    originalid = None
    'The session id passed by the client. May be missing or unsafe.'

    missing = False
    'True if the session requested by the client did not exist.'

    regenerated = False
    """
    True if the application called session.regenerate(). This is not set by
    internal calls to regenerate the session id."""

    debug = False
    'If True, log debug information.'

    # --------------------- Session management methods --------------------- #

    def __init__(self, id=None, **kwargs):
        self.id_observers = []
        self._data = {}

        for k, v in kwargs.items():
            setattr(self, k, v)

        self.originalid = id
        self.missing = False
        if id is None:
            if self.debug:
                cherrypy.log('No id given; making a new one', 'TOOLS.SESSIONS')
            self._regenerate()
        else:
            self.id = id
            if self._exists():
                if self.debug:
                    cherrypy.log('Set id to %s.' % id, 'TOOLS.SESSIONS')
            else:
                if self.debug:
                    cherrypy.log('Expired or malicious session %r; '
                                 'making a new one' % id, 'TOOLS.SESSIONS')
                # Expired or malicious session. Make a new one.
                # See https://github.com/cherrypy/cherrypy/issues/709.
                self.id = None
                self.missing = True
                self._regenerate()

    def now(self):
        """Generate the session specific concept of 'now'.

        Other session providers can override this to use alternative,
        possibly timezone aware, versions of 'now'.
        """
        return datetime.datetime.now()

    def regenerate(self):
        """Replace the current session (with a new id)."""
        self.regenerated = True
        self._regenerate()

    def _regenerate(self):
        if self.id is not None:
            if self.debug:
                cherrypy.log(
                    'Deleting the existing session %r before '
                    'regeneration.' % self.id,
                    'TOOLS.SESSIONS')
            self.delete()

        old_session_was_locked = self.locked
        if old_session_was_locked:
            self.release_lock()
            if self.debug:
                cherrypy.log('Old lock released.', 'TOOLS.SESSIONS')

        self.id = None
        while self.id is None:
            self.id = self.generate_id()
            # Assert that the generated id is not already stored.
            if self._exists():
                self.id = None
        if self.debug:
            cherrypy.log('Set id to generated %s.' % self.id,
                         'TOOLS.SESSIONS')

        if old_session_was_locked:
            self.acquire_lock()
            if self.debug:
                cherrypy.log('Regenerated lock acquired.', 'TOOLS.SESSIONS')

    def clean_up(self):
        """Clean up expired sessions."""
        pass

    def generate_id(self):
        """Return a new session id."""
        return binascii.hexlify(os.urandom(20)).decode('ascii')

    def save(self):
        """Save session data."""
        try:
            # If session data has never been loaded then it's never been
            #   accessed: no need to save it
            if self.loaded:
                t = datetime.timedelta(seconds=self.timeout * 60)
                expiration_time = self.now() + t
                if self.debug:
                    cherrypy.log('Saving session %r with expiry %s' %
                                 (self.id, expiration_time),
                                 'TOOLS.SESSIONS')
                self._save(expiration_time)
            else:
                if self.debug:
                    cherrypy.log(
                        'Skipping save of session %r (no session loaded).' %
                        self.id, 'TOOLS.SESSIONS')
        finally:
            if self.locked:
                # Always release the lock if the user didn't release it
                self.release_lock()
                if self.debug:
                    cherrypy.log('Lock released after save.', 'TOOLS.SESSIONS')

    def load(self):
        """Copy stored session data into this session instance."""
        data = self._load()
        # data is either None or a tuple (session_data, expiration_time)
        if data is None or data[1] < self.now():
            if self.debug:
                cherrypy.log('Expired session %r, flushing data.' % self.id,
                             'TOOLS.SESSIONS')
            self._data = {}
        else:
            if self.debug:
                cherrypy.log('Data loaded for session %r.' % self.id,
                             'TOOLS.SESSIONS')
            self._data = data[0]
        self.loaded = True

        # Stick the clean_thread in the class, not the instance.
        # The instances are created and destroyed per-request.
        cls = self.__class__
        if self.clean_freq and not cls.clean_thread:
            # clean_up is an instancemethod and not a classmethod,
            # so that tool config can be accessed inside the method.
            t = cherrypy.process.plugins.Monitor(
                cherrypy.engine, self.clean_up, self.clean_freq * 60,
                name='Session cleanup')
            t.subscribe()
            cls.clean_thread = t
            t.start()
            if self.debug:
                cherrypy.log('Started cleanup thread.', 'TOOLS.SESSIONS')

    def delete(self):
        """Delete stored session data."""
        self._delete()
        if self.debug:
            cherrypy.log('Deleted session %s.' % self.id,
                         'TOOLS.SESSIONS')

    # -------------------- Application accessor methods -------------------- #

    def __getitem__(self, key):
        if not self.loaded:
            self.load()
        return self._data[key]

    def __setitem__(self, key, value):
        if not self.loaded:
            self.load()
        self._data[key] = value

    def __delitem__(self, key):
        if not self.loaded:
            self.load()
        del self._data[key]

    def pop(self, key, default=missing):
        """Remove the specified key and return the corresponding value.
        If key is not found, default is returned if given,
        otherwise KeyError is raised.
        """
        if not self.loaded:
            self.load()
        if default is missing:
            return self._data.pop(key)
        else:
            return self._data.pop(key, default)

    def __contains__(self, key):
        if not self.loaded:
            self.load()
        return key in self._data

    def get(self, key, default=None):
        """D.get(k[,d]) -> D[k] if k in D, else d.  d defaults to None."""
        if not self.loaded:
            self.load()
        return self._data.get(key, default)

    def update(self, d):
        """D.update(E) -> None.  Update D from E: for k in E: D[k] = E[k]."""
        if not self.loaded:
            self.load()
        self._data.update(d)

    def setdefault(self, key, default=None):
        """D.setdefault(k[,d]) -> D.get(k,d), also set D[k]=d if k not in D."""
        if not self.loaded:
            self.load()
        return self._data.setdefault(key, default)

    def clear(self):
        """D.clear() -> None.  Remove all items from D."""
        if not self.loaded:
            self.load()
        self._data.clear()

    def keys(self):
        """D.keys() -> list of D's keys."""
        if not self.loaded:
            self.load()
        return self._data.keys()

    def items(self):
        """D.items() -> list of D's (key, value) pairs, as 2-tuples."""
        if not self.loaded:
            self.load()
        return self._data.items()

    def values(self):
        """D.values() -> list of D's values."""
        if not self.loaded:
            self.load()
        return self._data.values()


class RamSession(Session):

    # Class-level objects. Don't rebind these!
    cache = {}
    locks = {}

    def clean_up(self):
        """Clean up expired sessions."""

        now = self.now()
        for _id, (data, expiration_time) in self.cache.copy().items():
            if expiration_time <= now:
                try:
                    del self.cache[_id]
                except KeyError:
                    pass
                try:
                    if self.locks[_id].acquire(blocking=False):
                        lock = self.locks.pop(_id)
                        lock.release()
                except KeyError:
                    pass

        # added to remove obsolete lock objects
        for _id in list(self.locks):
            locked = (
                _id not in self.cache
                and self.locks[_id].acquire(blocking=False)
            )
            if locked:
                lock = self.locks.pop(_id)
                lock.release()

    def _exists(self):
        return self.id in self.cache

    def _load(self):
        return self.cache.get(self.id)

    def _save(self, expiration_time):
        self.cache[self.id] = (self._data, expiration_time)

    def _delete(self):
        self.cache.pop(self.id, None)

    def acquire_lock(self):
        """Acquire an exclusive lock on the currently-loaded session data."""
        self.locked = True
        self.locks.setdefault(self.id, threading.RLock()).acquire()

    def release_lock(self):
        """Release the lock on the currently-loaded session data."""
        self.locks[self.id].release()
        self.locked = False

    def __len__(self):
        """Return the number of active sessions."""
        return len(self.cache)


class FileSession(Session):

    """Implementation of the File backend for sessions

    storage_path
        The folder where session data will be saved. Each session
        will be saved as pickle.dump(data, expiration_time) in its own file;
        the filename will be self.SESSION_PREFIX + self.id.

    lock_timeout
        A timedelta or numeric seconds indicating how long
        to block acquiring a lock. If None (default), acquiring a lock
        will block indefinitely.
    """

    SESSION_PREFIX = 'session-'
    LOCK_SUFFIX = '.lock'
    pickle_protocol = pickle.HIGHEST_PROTOCOL

    def __init__(self, id=None, **kwargs):
        # The 'storage_path' arg is required for file-based sessions.
        kwargs['storage_path'] = os.path.abspath(kwargs['storage_path'])
        kwargs.setdefault('lock_timeout', None)

        Session.__init__(self, id=id, **kwargs)

        # validate self.lock_timeout
        if isinstance(self.lock_timeout, (int, float)):
            self.lock_timeout = datetime.timedelta(seconds=self.lock_timeout)
        if not isinstance(self.lock_timeout, (datetime.timedelta, type(None))):
            raise ValueError(
                'Lock timeout must be numeric seconds or a timedelta instance.'
            )

    @classmethod
    def setup(cls, **kwargs):
        """Set up the storage system for file-based sessions.

        This should only be called once per process; this will be done
        automatically when using sessions.init (as the built-in Tool does).
        """
        # The 'storage_path' arg is required for file-based sessions.
        kwargs['storage_path'] = os.path.abspath(kwargs['storage_path'])

        for k, v in kwargs.items():
            setattr(cls, k, v)

    def _get_file_path(self):
        f = os.path.join(self.storage_path, self.SESSION_PREFIX + self.id)
        if not os.path.abspath(f).startswith(self.storage_path):
            raise cherrypy.HTTPError(400, 'Invalid session id in cookie.')
        return f

    def _exists(self):
        path = self._get_file_path()
        return os.path.exists(path)

    def _load(self, path=None):
        assert self.locked, ('The session load without being locked.  '
                             "Check your tools' priority levels.")
        if path is None:
            path = self._get_file_path()
        try:
            with open(path, 'rb') as f:
                return pickle.load(f)
        except (IOError, EOFError):
            e = sys.exc_info()[1]
            if self.debug:
                cherrypy.log('Error loading the session pickle: %s' %
                             e, 'TOOLS.SESSIONS')
            return None

    def _save(self, expiration_time):
        assert self.locked, ('The session was saved without being locked.  '
                             "Check your tools' priority levels.")
        with open(self._get_file_path(), 'wb') as f:
            pickle.dump((self._data, expiration_time), f, self.pickle_protocol)

    def _delete(self):
        assert self.locked, ('The session deletion without being locked.  '
                             "Check your tools' priority levels.")
        try:
            os.unlink(self._get_file_path())
        except OSError:
            pass

    def acquire_lock(self, path=None):
        """Acquire an exclusive lock on the currently-loaded session data."""
        if path is None:
            path = self._get_file_path()
        path += self.LOCK_SUFFIX
        checker = locking.LockChecker(self.id, self.lock_timeout)
        while not checker.expired():
            try:
                self.lock = zc.lockfile.LockFile(path)
            except zc.lockfile.LockError:
                time.sleep(0.1)
            else:
                break
        self.locked = True
        if self.debug:
            cherrypy.log('Lock acquired.', 'TOOLS.SESSIONS')

    def release_lock(self, path=None):
        """Release the lock on the currently-loaded session data."""
        self.lock.close()
        self.locked = False

    def clean_up(self):
        """Clean up expired sessions."""
        now = self.now()
        # Iterate over all session files in self.storage_path
        for fname in os.listdir(self.storage_path):
            have_session = (
                fname.startswith(self.SESSION_PREFIX)
                and not fname.endswith(self.LOCK_SUFFIX)
            )
            if have_session:
                # We have a session file: lock and load it and check
                #   if it's expired. If it fails, nevermind.
                path = os.path.join(self.storage_path, fname)
                self.acquire_lock(path)
                if self.debug:
                    # This is a bit of a hack, since we're calling clean_up
                    # on the first instance rather than the entire class,
                    # so depending on whether you have "debug" set on the
                    # path of the first session called, this may not run.
                    cherrypy.log('Cleanup lock acquired.', 'TOOLS.SESSIONS')

                try:
                    contents = self._load(path)
                    # _load returns None on IOError
                    if contents is not None:
                        data, expiration_time = contents
                        if expiration_time < now:
                            # Session expired: deleting it
                            os.unlink(path)
                finally:
                    self.release_lock(path)

    def __len__(self):
        """Return the number of active sessions."""
        return len([fname for fname in os.listdir(self.storage_path)
                    if (fname.startswith(self.SESSION_PREFIX) and
                        not fname.endswith(self.LOCK_SUFFIX))])


class MemcachedSession(Session):

    # The most popular memcached client for Python isn't thread-safe.
    # Wrap all .get and .set operations in a single lock.
    mc_lock = threading.RLock()

    # This is a separate set of locks per session id.
    locks = {}

    servers = ['localhost:11211']

    @classmethod
    def setup(cls, **kwargs):
        """Set up the storage system for memcached-based sessions.

        This should only be called once per process; this will be done
        automatically when using sessions.init (as the built-in Tool does).
        """
        for k, v in kwargs.items():
            setattr(cls, k, v)

        import memcache
        cls.cache = memcache.Client(cls.servers)

    def _exists(self):
        self.mc_lock.acquire()
        try:
            return bool(self.cache.get(self.id))
        finally:
            self.mc_lock.release()

    def _load(self):
        self.mc_lock.acquire()
        try:
            return self.cache.get(self.id)
        finally:
            self.mc_lock.release()

    def _save(self, expiration_time):
        # Send the expiration time as "Unix time" (seconds since 1/1/1970)
        td = int(time.mktime(expiration_time.timetuple()))
        self.mc_lock.acquire()
        try:
            if not self.cache.set(self.id, (self._data, expiration_time), td):
                raise AssertionError(
                    'Session data for id %r not set.' % self.id)
        finally:
            self.mc_lock.release()

    def _delete(self):
        self.cache.delete(self.id)

    def acquire_lock(self):
        """Acquire an exclusive lock on the currently-loaded session data."""
        self.locked = True
        self.locks.setdefault(self.id, threading.RLock()).acquire()
        if self.debug:
            cherrypy.log('Lock acquired.', 'TOOLS.SESSIONS')

    def release_lock(self):
        """Release the lock on the currently-loaded session data."""
        self.locks[self.id].release()
        self.locked = False

    def __len__(self):
        """Return the number of active sessions."""
        raise NotImplementedError


# Hook functions (for CherryPy tools)

def save():
    """Save any changed session data."""

    if not hasattr(cherrypy.serving, 'session'):
        return
    request = cherrypy.serving.request
    response = cherrypy.serving.response

    # Guard against running twice
    if hasattr(request, '_sessionsaved'):
        return
    request._sessionsaved = True

    if response.stream:
        # If the body is being streamed, we have to save the data
        #   *after* the response has been written out
        request.hooks.attach('on_end_request', cherrypy.session.save)
    else:
        # If the body is not being streamed, we save the data now
        # (so we can release the lock).
        if is_iterator(response.body):
            response.collapse_body()
        cherrypy.session.save()


save.failsafe = True


def close():
    """Close the session object for this request."""
    sess = getattr(cherrypy.serving, 'session', None)
    if getattr(sess, 'locked', False):
        # If the session is still locked we release the lock
        sess.release_lock()
        if sess.debug:
            cherrypy.log('Lock released on close.', 'TOOLS.SESSIONS')


close.failsafe = True
close.priority = 90


def init(storage_type=None, path=None, path_header=None, name='session_id',
         timeout=60, domain=None, secure=False, clean_freq=5,
         persistent=True, httponly=False, debug=False,
         # Py27 compat
         # *, storage_class=RamSession,
         **kwargs):
    """Initialize session object (using cookies).

    storage_class
        The Session subclass to use. Defaults to RamSession.

    storage_type
        (deprecated)
        One of 'ram', 'file', memcached'. This will be
        used to look up the corresponding class in cherrypy.lib.sessions
        globals. For example, 'file' will use the FileSession class.

    path
        The 'path' value to stick in the response cookie metadata.

    path_header
        If 'path' is None (the default), then the response
        cookie 'path' will be pulled from request.headers[path_header].

    name
        The name of the cookie.

    timeout
        The expiration timeout (in minutes) for the stored session data.
        If 'persistent' is True (the default), this is also the timeout
        for the cookie.

    domain
        The cookie domain.

    secure
        If False (the default) the cookie 'secure' value will not
        be set. If True, the cookie 'secure' value will be set (to 1).

    clean_freq (minutes)
        The poll rate for expired session cleanup.

    persistent
        If True (the default), the 'timeout' argument will be used
        to expire the cookie. If False, the cookie will not have an expiry,
        and the cookie will be a "session cookie" which expires when the
        browser is closed.

    httponly
        If False (the default) the cookie 'httponly' value will not be set.
        If True, the cookie 'httponly' value will be set (to 1).

    Any additional kwargs will be bound to the new Session instance,
    and may be specific to the storage type. See the subclass of Session
    you're using for more information.
    """

    # Py27 compat
    storage_class = kwargs.pop('storage_class', RamSession)

    request = cherrypy.serving.request

    # Guard against running twice
    if hasattr(request, '_session_init_flag'):
        return
    request._session_init_flag = True

    # Check if request came with a session ID
    id = None
    if name in request.cookie:
        id = request.cookie[name].value
        if debug:
            cherrypy.log('ID obtained from request.cookie: %r' % id,
                         'TOOLS.SESSIONS')

    first_time = not hasattr(cherrypy, 'session')

    if storage_type:
        if first_time:
            msg = 'storage_type is deprecated. Supply storage_class instead'
            cherrypy.log(msg)
        storage_class = storage_type.title() + 'Session'
        storage_class = globals()[storage_class]

    # call setup first time only
    if first_time:
        if hasattr(storage_class, 'setup'):
            storage_class.setup(**kwargs)

    # Create and attach a new Session instance to cherrypy.serving.
    # It will possess a reference to (and lock, and lazily load)
    # the requested session data.
    kwargs['timeout'] = timeout
    kwargs['clean_freq'] = clean_freq
    cherrypy.serving.session = sess = storage_class(id, **kwargs)
    sess.debug = debug

    def update_cookie(id):
        """Update the cookie every time the session id changes."""
        cherrypy.serving.response.cookie[name] = id
    sess.id_observers.append(update_cookie)

    # Create cherrypy.session which will proxy to cherrypy.serving.session
    if not hasattr(cherrypy, 'session'):
        cherrypy.session = cherrypy._ThreadLocalProxy('session')

    if persistent:
        cookie_timeout = timeout
    else:
        # See http://support.microsoft.com/kb/223799/EN-US/
        # and http://support.mozilla.com/en-US/kb/Cookies
        cookie_timeout = None
    set_response_cookie(path=path, path_header=path_header, name=name,
                        timeout=cookie_timeout, domain=domain, secure=secure,
                        httponly=httponly)


def set_response_cookie(path=None, path_header=None, name='session_id',
                        timeout=60, domain=None, secure=False, httponly=False):
    """Set a response cookie for the client.

    path
        the 'path' value to stick in the response cookie metadata.

    path_header
        if 'path' is None (the default), then the response
        cookie 'path' will be pulled from request.headers[path_header].

    name
        the name of the cookie.

    timeout
        the expiration timeout for the cookie. If 0 or other boolean
        False, no 'expires' param will be set, and the cookie will be a
        "session cookie" which expires when the browser is closed.

    domain
        the cookie domain.

    secure
        if False (the default) the cookie 'secure' value will not
        be set. If True, the cookie 'secure' value will be set (to 1).

    httponly
        If False (the default) the cookie 'httponly' value will not be set.
        If True, the cookie 'httponly' value will be set (to 1).

    """
    # Set response cookie
    cookie = cherrypy.serving.response.cookie
    cookie[name] = cherrypy.serving.session.id
    cookie[name]['path'] = (
        path or
        cherrypy.serving.request.headers.get(path_header) or
        '/'
    )

    if timeout:
        cookie[name]['max-age'] = timeout * 60
        _add_MSIE_max_age_workaround(cookie[name], timeout)
    if domain is not None:
        cookie[name]['domain'] = domain
    if secure:
        cookie[name]['secure'] = 1
    if httponly:
        if not cookie[name].isReservedKey('httponly'):
            raise ValueError('The httponly cookie token is not supported.')
        cookie[name]['httponly'] = 1


def _add_MSIE_max_age_workaround(cookie, timeout):
    """
    We'd like to use the "max-age" param as indicated in
    http://www.faqs.org/rfcs/rfc2109.html but IE doesn't
    save it to disk and the session is lost if people close
    the browser. So we have to use the old "expires" ... sigh ...
    """
    expires = time.time() + timeout * 60
    cookie['expires'] = httputil.HTTPDate(expires)


def expire():
    """Expire the current session cookie."""
    name = cherrypy.serving.request.config.get(
        'tools.sessions.name', 'session_id')
    one_year = 60 * 60 * 24 * 365
    e = time.time() - one_year
    cherrypy.serving.response.cookie[name]['expires'] = httputil.HTTPDate(e)
    cherrypy.serving.response.cookie[name].pop('max-age', None)
