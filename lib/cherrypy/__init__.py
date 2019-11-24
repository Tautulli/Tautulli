"""CherryPy is a pythonic, object-oriented HTTP framework.

CherryPy consists of not one, but four separate API layers.

The APPLICATION LAYER is the simplest. CherryPy applications are written as
a tree of classes and methods, where each branch in the tree corresponds to
a branch in the URL path. Each method is a 'page handler', which receives
GET and POST params as keyword arguments, and returns or yields the (HTML)
body of the response. The special method name 'index' is used for paths
that end in a slash, and the special method name 'default' is used to
handle multiple paths via a single handler. This layer also includes:

 * the 'exposed' attribute (and cherrypy.expose)
 * cherrypy.quickstart()
 * _cp_config attributes
 * cherrypy.tools (including cherrypy.session)
 * cherrypy.url()

The ENVIRONMENT LAYER is used by developers at all levels. It provides
information about the current request and response, plus the application
and server environment, via a (default) set of top-level objects:

 * cherrypy.request
 * cherrypy.response
 * cherrypy.engine
 * cherrypy.server
 * cherrypy.tree
 * cherrypy.config
 * cherrypy.thread_data
 * cherrypy.log
 * cherrypy.HTTPError, NotFound, and HTTPRedirect
 * cherrypy.lib

The EXTENSION LAYER allows advanced users to construct and share their own
plugins. It consists of:

 * Hook API
 * Tool API
 * Toolbox API
 * Dispatch API
 * Config Namespace API

Finally, there is the CORE LAYER, which uses the core API's to construct
the default components which are available at higher layers. You can think
of the default components as the 'reference implementation' for CherryPy.
Megaframeworks (and advanced users) may replace the default components
with customized or extended components. The core API's are:

 * Application API
 * Engine API
 * Request API
 * Server API
 * WSGI API

These API's are described in the `CherryPy specification
<https://github.com/cherrypy/cherrypy/wiki/CherryPySpec>`_.
"""

try:
    import pkg_resources
except ImportError:
    pass

from threading import local as _local

from ._cperror import (
    HTTPError, HTTPRedirect, InternalRedirect,
    NotFound, CherryPyException,
)

from . import _cpdispatch as dispatch

from ._cptools import default_toolbox as tools, Tool
from ._helper import expose, popargs, url

from . import _cprequest, _cpserver, _cptree, _cplogging, _cpconfig

import cherrypy.lib.httputil as _httputil

from ._cptree import Application
from . import _cpwsgi as wsgi

from . import process
try:
    from .process import win32
    engine = win32.Win32Bus()
    engine.console_control_handler = win32.ConsoleCtrlHandler(engine)
    del win32
except ImportError:
    engine = process.bus

from . import _cpchecker

__all__ = (
    'HTTPError', 'HTTPRedirect', 'InternalRedirect',
    'NotFound', 'CherryPyException',
    'dispatch', 'tools', 'Tool', 'Application',
    'wsgi', 'process', 'tree', 'engine',
    'quickstart', 'serving', 'request', 'response', 'thread_data',
    'log', 'expose', 'popargs', 'url', 'config',
)


__import__('cherrypy._cptools')
__import__('cherrypy._cprequest')


tree = _cptree.Tree()


try:
    __version__ = pkg_resources.require('cherrypy')[0].version
except Exception:
    __version__ = 'unknown'


engine.listeners['before_request'] = set()
engine.listeners['after_request'] = set()


engine.autoreload = process.plugins.Autoreloader(engine)
engine.autoreload.subscribe()

engine.thread_manager = process.plugins.ThreadManager(engine)
engine.thread_manager.subscribe()

engine.signal_handler = process.plugins.SignalHandler(engine)


class _HandleSignalsPlugin(object):
    """Handle signals from other processes.

    Based on the configured platform handlers above.
    """

    def __init__(self, bus):
        self.bus = bus

    def subscribe(self):
        """Add the handlers based on the platform."""
        if hasattr(self.bus, 'signal_handler'):
            self.bus.signal_handler.subscribe()
        if hasattr(self.bus, 'console_control_handler'):
            self.bus.console_control_handler.subscribe()


engine.signals = _HandleSignalsPlugin(engine)


server = _cpserver.Server()
server.subscribe()


def quickstart(root=None, script_name='', config=None):
    """Mount the given root, start the builtin server (and engine), then block.

    root: an instance of a "controller class" (a collection of page handler
        methods) which represents the root of the application.
    script_name: a string containing the "mount point" of the application.
        This should start with a slash, and be the path portion of the URL
        at which to mount the given root. For example, if root.index() will
        handle requests to "http://www.example.com:8080/dept/app1/", then
        the script_name argument would be "/dept/app1".

        It MUST NOT end in a slash. If the script_name refers to the root
        of the URI, it MUST be an empty string (not "/").
    config: a file or dict containing application config. If this contains
        a [global] section, those entries will be used in the global
        (site-wide) config.
    """
    if config:
        _global_conf_alias.update(config)

    tree.mount(root, script_name, config)

    engine.signals.subscribe()
    engine.start()
    engine.block()


class _Serving(_local):
    """An interface for registering request and response objects.

    Rather than have a separate "thread local" object for the request and
    the response, this class works as a single threadlocal container for
    both objects (and any others which developers wish to define). In this
    way, we can easily dump those objects when we stop/start a new HTTP
    conversation, yet still refer to them as module-level globals in a
    thread-safe way.
    """

    request = _cprequest.Request(_httputil.Host('127.0.0.1', 80),
                                 _httputil.Host('127.0.0.1', 1111))
    """
    The request object for the current thread. In the main thread,
    and any threads which are not receiving HTTP requests, this is None."""

    response = _cprequest.Response()
    """
    The response object for the current thread. In the main thread,
    and any threads which are not receiving HTTP requests, this is None."""

    def load(self, request, response):
        self.request = request
        self.response = response

    def clear(self):
        """Remove all attributes of self."""
        self.__dict__.clear()


serving = _Serving()


class _ThreadLocalProxy(object):

    __slots__ = ['__attrname__', '__dict__']

    def __init__(self, attrname):
        self.__attrname__ = attrname

    def __getattr__(self, name):
        child = getattr(serving, self.__attrname__)
        return getattr(child, name)

    def __setattr__(self, name, value):
        if name in ('__attrname__', ):
            object.__setattr__(self, name, value)
        else:
            child = getattr(serving, self.__attrname__)
            setattr(child, name, value)

    def __delattr__(self, name):
        child = getattr(serving, self.__attrname__)
        delattr(child, name)

    @property
    def __dict__(self):
        child = getattr(serving, self.__attrname__)
        d = child.__class__.__dict__.copy()
        d.update(child.__dict__)
        return d

    def __getitem__(self, key):
        child = getattr(serving, self.__attrname__)
        return child[key]

    def __setitem__(self, key, value):
        child = getattr(serving, self.__attrname__)
        child[key] = value

    def __delitem__(self, key):
        child = getattr(serving, self.__attrname__)
        del child[key]

    def __contains__(self, key):
        child = getattr(serving, self.__attrname__)
        return key in child

    def __len__(self):
        child = getattr(serving, self.__attrname__)
        return len(child)

    def __nonzero__(self):
        child = getattr(serving, self.__attrname__)
        return bool(child)
    # Python 3
    __bool__ = __nonzero__


# Create request and response object (the same objects will be used
#   throughout the entire life of the webserver, but will redirect
#   to the "serving" object)
request = _ThreadLocalProxy('request')
response = _ThreadLocalProxy('response')

# Create thread_data object as a thread-specific all-purpose storage


class _ThreadData(_local):
    """A container for thread-specific data."""


thread_data = _ThreadData()


# Monkeypatch pydoc to allow help() to go through the threadlocal proxy.
# Jan 2007: no Googleable examples of anyone else replacing pydoc.resolve.
# The only other way would be to change what is returned from type(request)
# and that's not possible in pure Python (you'd have to fake ob_type).
def _cherrypy_pydoc_resolve(thing, forceload=0):
    """Given an object or a path to an object, get the object and its name."""
    if isinstance(thing, _ThreadLocalProxy):
        thing = getattr(serving, thing.__attrname__)
    return _pydoc._builtin_resolve(thing, forceload)


try:
    import pydoc as _pydoc
    _pydoc._builtin_resolve = _pydoc.resolve
    _pydoc.resolve = _cherrypy_pydoc_resolve
except ImportError:
    pass


class _GlobalLogManager(_cplogging.LogManager):
    """A site-wide LogManager; routes to app.log or global log as appropriate.

    This :class:`LogManager<cherrypy._cplogging.LogManager>` implements
    cherrypy.log() and cherrypy.log.access(). If either
    function is called during a request, the message will be sent to the
    logger for the current Application. If they are called outside of a
    request, the message will be sent to the site-wide logger.
    """

    def __call__(self, *args, **kwargs):
        """Log the given message to the app.log or global log.

        Log the given message to the app.log or global
        log as appropriate.
        """
        # Do NOT use try/except here. See
        # https://github.com/cherrypy/cherrypy/issues/945
        if hasattr(request, 'app') and hasattr(request.app, 'log'):
            log = request.app.log
        else:
            log = self
        return log.error(*args, **kwargs)

    def access(self):
        """Log an access message to the app.log or global log.

        Log the given message to the app.log or global
        log as appropriate.
        """
        try:
            return request.app.log.access()
        except AttributeError:
            return _cplogging.LogManager.access(self)


log = _GlobalLogManager()
# Set a default screen handler on the global log.
log.screen = True
log.error_file = ''
# Using an access file makes CP about 10% slower. Leave off by default.
log.access_file = ''


@engine.subscribe('log')
def _buslog(msg, level):
    log.error(msg, 'ENGINE', severity=level)


# Use _global_conf_alias so quickstart can use 'config' as an arg
# without shadowing cherrypy.config.
config = _global_conf_alias = _cpconfig.Config()
config.defaults = {
    'tools.log_tracebacks.on': True,
    'tools.log_headers.on': True,
    'tools.trailing_slash.on': True,
    'tools.encode.on': True
}
config.namespaces['log'] = lambda k, v: setattr(log, k, v)
config.namespaces['checker'] = lambda k, v: setattr(checker, k, v)
# Must reset to get our defaults applied.
config.reset()

checker = _cpchecker.Checker()
engine.subscribe('start', checker)
