"""
Configuration system for CherryPy.

Configuration in CherryPy is implemented via dictionaries. Keys are strings
which name the mapped value, which may be of any type.


Architecture
------------

CherryPy Requests are part of an Application, which runs in a global context,
and configuration data may apply to any of those three scopes:

Global
    Configuration entries which apply everywhere are stored in
    cherrypy.config.

Application
    Entries which apply to each mounted application are stored
    on the Application object itself, as 'app.config'. This is a two-level
    dict where each key is a path, or "relative URL" (for example, "/" or
    "/path/to/my/page"), and each value is a config dict. Usually, this
    data is provided in the call to tree.mount(root(), config=conf),
    although you may also use app.merge(conf).

Request
    Each Request object possesses a single 'Request.config' dict.
    Early in the request process, this dict is populated by merging global
    config entries, Application entries (whose path equals or is a parent
    of Request.path_info), and any config acquired while looking up the
    page handler (see next).


Declaration
-----------

Configuration data may be supplied as a Python dictionary, as a filename,
or as an open file object. When you supply a filename or file, CherryPy
uses Python's builtin ConfigParser; you declare Application config by
writing each path as a section header::

    [/path/to/my/page]
    request.stream = True

To declare global configuration entries, place them in a [global] section.

You may also declare config entries directly on the classes and methods
(page handlers) that make up your CherryPy application via the ``_cp_config``
attribute, set with the ``cherrypy.config`` decorator. For example::

    @cherrypy.config(**{'tools.gzip.on': True})
    class Demo:

        @cherrypy.expose
        @cherrypy.config(**{'request.show_tracebacks': False})
        def index(self):
            return "Hello world"

.. note::

    This behavior is only guaranteed for the default dispatcher.
    Other dispatchers may have different restrictions on where
    you can attach config attributes.


Namespaces
----------

Configuration keys are separated into namespaces by the first "." in the key.
Current namespaces:

engine
    Controls the 'application engine', including autoreload.
    These can only be declared in the global config.

tree
    Grafts cherrypy.Application objects onto cherrypy.tree.
    These can only be declared in the global config.

hooks
    Declares additional request-processing functions.

log
    Configures the logging for each application.
    These can only be declared in the global or / config.

request
    Adds attributes to each Request.

response
    Adds attributes to each Response.

server
    Controls the default HTTP server via cherrypy.server.
    These can only be declared in the global config.

tools
    Runs and configures additional request-processing packages.

wsgi
    Adds WSGI middleware to an Application's "pipeline".
    These can only be declared in the app's root config ("/").

checker
    Controls the 'checker', which looks for common errors in
    app state (including config) when the engine starts.
    Global config only.

The only key that does not exist in a namespace is the "environment" entry.
This special entry 'imports' other config entries from a template stored in
cherrypy._cpconfig.environments[environment]. It only applies to the global
config, and only when you use cherrypy.config.update.

You can define your own namespaces to be called at the Global, Application,
or Request level, by adding a named handler to cherrypy.config.namespaces,
app.namespaces, or app.request_class.namespaces. The name can
be any string, and the handler must be either a callable or a (Python 2.5
style) context manager.
"""

import cherrypy
from cherrypy._cpcompat import text_or_bytes
from cherrypy.lib import reprconf


def _if_filename_register_autoreload(ob):
    """Register for autoreload if ob is a string (presumed filename)."""
    is_filename = isinstance(ob, text_or_bytes)
    is_filename and cherrypy.engine.autoreload.files.add(ob)


def merge(base, other):
    """Merge one app config (from a dict, file, or filename) into another.

    If the given config is a filename, it will be appended to
    the list of files to monitor for "autoreload" changes.
    """
    _if_filename_register_autoreload(other)

    # Load other into base
    for section, value_map in reprconf.Parser.load(other).items():
        if not isinstance(value_map, dict):
            raise ValueError(
                'Application config must include section headers, but the '
                "config you tried to merge doesn't have any sections. "
                'Wrap your config in another dict with paths as section '
                "headers, for example: {'/': config}.")
        base.setdefault(section, {}).update(value_map)


class Config(reprconf.Config):
    """The 'global' configuration data for the entire CherryPy process."""

    def update(self, config):
        """Update self from a dict, file or filename."""
        _if_filename_register_autoreload(config)
        super(Config, self).update(config)

    def _apply(self, config):
        """Update self from a dict."""
        if isinstance(config.get('global'), dict):
            if len(config) > 1:
                cherrypy.checker.global_config_contained_paths = True
            config = config['global']
        if 'tools.staticdir.dir' in config:
            config['tools.staticdir.section'] = 'global'
        super(Config, self)._apply(config)

    @staticmethod
    def __call__(**kwargs):
        """Decorate for page handlers to set _cp_config."""
        def tool_decorator(f):
            _Vars(f).setdefault('_cp_config', {}).update(kwargs)
            return f
        return tool_decorator


class _Vars(object):
    """Adapter allowing setting a default attribute on a function or class."""

    def __init__(self, target):
        self.target = target

    def setdefault(self, key, default):
        if not hasattr(self.target, key):
            setattr(self.target, key, default)
        return getattr(self.target, key)


# Sphinx begin config.environments
Config.environments = environments = {
    'staging': {
        'engine.autoreload.on': False,
        'checker.on': False,
        'tools.log_headers.on': False,
        'request.show_tracebacks': False,
        'request.show_mismatched_params': False,
    },
    'production': {
        'engine.autoreload.on': False,
        'checker.on': False,
        'tools.log_headers.on': False,
        'request.show_tracebacks': False,
        'request.show_mismatched_params': False,
        'log.screen': False,
    },
    'embedded': {
        # For use with CherryPy embedded in another deployment stack.
        'engine.autoreload.on': False,
        'checker.on': False,
        'tools.log_headers.on': False,
        'request.show_tracebacks': False,
        'request.show_mismatched_params': False,
        'log.screen': False,
        'engine.SIGHUP': None,
        'engine.SIGTERM': None,
    },
    'test_suite': {
        'engine.autoreload.on': False,
        'checker.on': False,
        'tools.log_headers.on': False,
        'request.show_tracebacks': True,
        'request.show_mismatched_params': True,
        'log.screen': False,
    },
}
# Sphinx end config.environments


def _server_namespace_handler(k, v):
    """Config handler for the "server" namespace."""
    atoms = k.split('.', 1)
    if len(atoms) > 1:
        # Special-case config keys of the form 'server.servername.socket_port'
        # to configure additional HTTP servers.
        if not hasattr(cherrypy, 'servers'):
            cherrypy.servers = {}

        servername, k = atoms
        if servername not in cherrypy.servers:
            from cherrypy import _cpserver
            cherrypy.servers[servername] = _cpserver.Server()
            # On by default, but 'on = False' can unsubscribe it (see below).
            cherrypy.servers[servername].subscribe()

        if k == 'on':
            if v:
                cherrypy.servers[servername].subscribe()
            else:
                cherrypy.servers[servername].unsubscribe()
        else:
            setattr(cherrypy.servers[servername], k, v)
    else:
        setattr(cherrypy.server, k, v)


Config.namespaces['server'] = _server_namespace_handler


def _engine_namespace_handler(k, v):
    """Config handler for the "engine" namespace."""
    engine = cherrypy.engine

    if k in {'SIGHUP', 'SIGTERM'}:
        engine.subscribe(k, v)
        return

    if '.' in k:
        plugin, attrname = k.split('.', 1)
        plugin = getattr(engine, plugin)
        op = 'subscribe' if v else 'unsubscribe'
        sub_unsub = getattr(plugin, op, None)
        if attrname == 'on' and callable(sub_unsub):
            sub_unsub()
            return
        setattr(plugin, attrname, v)
    else:
        setattr(engine, k, v)


Config.namespaces['engine'] = _engine_namespace_handler


def _tree_namespace_handler(k, v):
    """Namespace handler for the 'tree' config namespace."""
    if isinstance(v, dict):
        for script_name, app in v.items():
            cherrypy.tree.graft(app, script_name)
            msg = 'Mounted: %s on %s' % (app, script_name or '/')
            cherrypy.engine.log(msg)
    else:
        cherrypy.tree.graft(v, v.script_name)
        cherrypy.engine.log('Mounted: %s on %s' % (v, v.script_name or '/'))


Config.namespaces['tree'] = _tree_namespace_handler
