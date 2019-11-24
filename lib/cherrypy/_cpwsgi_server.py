"""
WSGI server interface (see PEP 333).

This adds some CP-specific bits to the framework-agnostic cheroot package.
"""
import sys

import cheroot.wsgi
import cheroot.server

import cherrypy


class CPWSGIHTTPRequest(cheroot.server.HTTPRequest):
    """Wrapper for cheroot.server.HTTPRequest.

    This is a layer, which preserves URI parsing mode like it which was
    before Cheroot v5.8.0.
    """

    def __init__(self, server, conn):
        """Initialize HTTP request container instance.

        Args:
            server (cheroot.server.HTTPServer):
                web server object receiving this request
            conn (cheroot.server.HTTPConnection):
                HTTP connection object for this request
        """
        super(CPWSGIHTTPRequest, self).__init__(
            server, conn, proxy_mode=True
        )


class CPWSGIServer(cheroot.wsgi.Server):
    """Wrapper for cheroot.wsgi.Server.

    cheroot has been designed to not reference CherryPy in any way,
    so that it can be used in other frameworks and applications. Therefore,
    we wrap it here, so we can set our own mount points from cherrypy.tree
    and apply some attributes from config -> cherrypy.server -> wsgi.Server.
    """

    fmt = 'CherryPy/{cherrypy.__version__} {cheroot.wsgi.Server.version}'
    version = fmt.format(**globals())

    def __init__(self, server_adapter=cherrypy.server):
        """Initialize CPWSGIServer instance.

        Args:
            server_adapter (cherrypy._cpserver.Server): ...
        """
        self.server_adapter = server_adapter
        self.max_request_header_size = (
            self.server_adapter.max_request_header_size or 0
        )
        self.max_request_body_size = (
            self.server_adapter.max_request_body_size or 0
        )

        server_name = (self.server_adapter.socket_host or
                       self.server_adapter.socket_file or
                       None)

        self.wsgi_version = self.server_adapter.wsgi_version

        super(CPWSGIServer, self).__init__(
            server_adapter.bind_addr, cherrypy.tree,
            self.server_adapter.thread_pool,
            server_name,
            max=self.server_adapter.thread_pool_max,
            request_queue_size=self.server_adapter.socket_queue_size,
            timeout=self.server_adapter.socket_timeout,
            shutdown_timeout=self.server_adapter.shutdown_timeout,
            accepted_queue_size=self.server_adapter.accepted_queue_size,
            accepted_queue_timeout=self.server_adapter.accepted_queue_timeout,
            peercreds_enabled=self.server_adapter.peercreds,
            peercreds_resolve_enabled=self.server_adapter.peercreds_resolve,
        )
        self.ConnectionClass.RequestHandlerClass = CPWSGIHTTPRequest

        self.protocol = self.server_adapter.protocol_version
        self.nodelay = self.server_adapter.nodelay

        if sys.version_info >= (3, 0):
            ssl_module = self.server_adapter.ssl_module or 'builtin'
        else:
            ssl_module = self.server_adapter.ssl_module or 'pyopenssl'
        if self.server_adapter.ssl_context:
            adapter_class = cheroot.server.get_ssl_adapter_class(ssl_module)
            self.ssl_adapter = adapter_class(
                self.server_adapter.ssl_certificate,
                self.server_adapter.ssl_private_key,
                self.server_adapter.ssl_certificate_chain,
                self.server_adapter.ssl_ciphers)
            self.ssl_adapter.context = self.server_adapter.ssl_context
        elif self.server_adapter.ssl_certificate:
            adapter_class = cheroot.server.get_ssl_adapter_class(ssl_module)
            self.ssl_adapter = adapter_class(
                self.server_adapter.ssl_certificate,
                self.server_adapter.ssl_private_key,
                self.server_adapter.ssl_certificate_chain,
                self.server_adapter.ssl_ciphers)

        self.stats['Enabled'] = getattr(
            self.server_adapter, 'statistics', False)

    def error_log(self, msg='', level=20, traceback=False):
        """Write given message to the error log."""
        cherrypy.engine.log(msg, level, traceback)
