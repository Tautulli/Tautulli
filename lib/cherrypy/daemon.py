"""The CherryPy daemon."""

import sys

import cherrypy
from cherrypy.process import plugins, servers
from cherrypy import Application


def start(configfiles=None, daemonize=False, environment=None,
          fastcgi=False, scgi=False, pidfile=None, imports=None,
          cgi=False):
    """Subscribe all engine plugins and start the engine."""
    sys.path = [''] + sys.path
    for i in imports or []:
        exec("import %s" % i)

    for c in configfiles or []:
        cherrypy.config.update(c)
        # If there's only one app mounted, merge config into it.
        if len(cherrypy.tree.apps) == 1:
            for app in cherrypy.tree.apps.values():
                if isinstance(app, Application):
                    app.merge(c)

    engine = cherrypy.engine

    if environment is not None:
        cherrypy.config.update({'environment': environment})

    # Only daemonize if asked to.
    if daemonize:
        # Don't print anything to stdout/sterr.
        cherrypy.config.update({'log.screen': False})
        plugins.Daemonizer(engine).subscribe()

    if pidfile:
        plugins.PIDFile(engine, pidfile).subscribe()

    if hasattr(engine, "signal_handler"):
        engine.signal_handler.subscribe()
    if hasattr(engine, "console_control_handler"):
        engine.console_control_handler.subscribe()

    if (fastcgi and (scgi or cgi)) or (scgi and cgi):
        cherrypy.log.error("You may only specify one of the cgi, fastcgi, and "
                           "scgi options.", 'ENGINE')
        sys.exit(1)
    elif fastcgi or scgi or cgi:
        # Turn off autoreload when using *cgi.
        cherrypy.config.update({'engine.autoreload_on': False})
        # Turn off the default HTTP server (which is subscribed by default).
        cherrypy.server.unsubscribe()

        addr = cherrypy.server.bind_addr
        cls = (
            servers.FlupFCGIServer if fastcgi else
            servers.FlupSCGIServer if scgi else
            servers.FlupCGIServer
        )
        f = cls(application=cherrypy.tree, bindAddress=addr)
        s = servers.ServerAdapter(engine, httpserver=f, bind_addr=addr)
        s.subscribe()

    # Always start the engine; this will start all other services
    try:
        engine.start()
    except:
        # Assume the error has been logged already via bus.log.
        sys.exit(1)
    else:
        engine.block()


def run():
    from optparse import OptionParser

    p = OptionParser()
    p.add_option('-c', '--config', action="append", dest='config',
                 help="specify config file(s)")
    p.add_option('-d', action="store_true", dest='daemonize',
                 help="run the server as a daemon")
    p.add_option('-e', '--environment', dest='environment', default=None,
                 help="apply the given config environment")
    p.add_option('-f', action="store_true", dest='fastcgi',
                 help="start a fastcgi server instead of the default HTTP "
                      "server")
    p.add_option('-s', action="store_true", dest='scgi',
                 help="start a scgi server instead of the default HTTP server")
    p.add_option('-x', action="store_true", dest='cgi',
                 help="start a cgi server instead of the default HTTP server")
    p.add_option('-i', '--import', action="append", dest='imports',
                 help="specify modules to import")
    p.add_option('-p', '--pidfile', dest='pidfile', default=None,
                 help="store the process id in the given file")
    p.add_option('-P', '--Path', action="append", dest='Path',
                 help="add the given paths to sys.path")
    options, args = p.parse_args()

    if options.Path:
        for p in options.Path:
            sys.path.insert(0, p)

    start(options.config, options.daemonize,
          options.environment, options.fastcgi, options.scgi,
          options.pidfile, options.imports, options.cgi)
