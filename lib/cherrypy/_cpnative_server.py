"""Native adapter for serving CherryPy via its builtin server."""

import logging
import sys
import io

import cheroot.server

import cherrypy
from cherrypy._cperror import format_exc, bare_error
from cherrypy.lib import httputil
from ._cpcompat import tonative


class NativeGateway(cheroot.server.Gateway):
    """Native gateway implementation allowing to bypass WSGI."""

    recursive = False

    def respond(self):
        """Obtain response from CherryPy machinery and then send it."""
        req = self.req
        try:
            # Obtain a Request object from CherryPy
            local = req.server.bind_addr  # FIXME: handle UNIX sockets
            local = tonative(local[0]), local[1]
            local = httputil.Host(local[0], local[1], '')
            remote = tonative(req.conn.remote_addr), req.conn.remote_port
            remote = httputil.Host(remote[0], remote[1], '')

            scheme = tonative(req.scheme)
            sn = cherrypy.tree.script_name(tonative(req.uri or '/'))
            if sn is None:
                self.send_response('404 Not Found', [], [''])
            else:
                app = cherrypy.tree.apps[sn]
                method = tonative(req.method)
                path = tonative(req.path)
                qs = tonative(req.qs or '')
                headers = (
                    (tonative(h), tonative(v))
                    for h, v in req.inheaders.items()
                )
                rfile = req.rfile
                prev = None

                try:
                    redirections = []
                    while True:
                        request, response = app.get_serving(
                            local, remote, scheme, 'HTTP/1.1')
                        request.multithread = True
                        request.multiprocess = False
                        request.app = app
                        request.prev = prev

                        # Run the CherryPy Request object and obtain the
                        # response
                        try:
                            request.run(
                                method, path, qs,
                                tonative(req.request_protocol),
                                headers, rfile,
                            )
                            break
                        except cherrypy.InternalRedirect:
                            ir = sys.exc_info()[1]
                            app.release_serving()
                            prev = request

                            if not self.recursive:
                                if ir.path in redirections:
                                    raise RuntimeError(
                                        'InternalRedirector visited the same '
                                        'URL twice: %r' % ir.path)
                                else:
                                    # Add the *previous* path_info + qs to
                                    # redirections.
                                    if qs:
                                        qs = '?' + qs
                                    redirections.append(sn + path + qs)

                            # Munge environment and try again.
                            method = 'GET'
                            path = ir.path
                            qs = ir.query_string
                            rfile = io.BytesIO()

                    self.send_response(
                        response.output_status, response.header_list,
                        response.body)
                finally:
                    app.release_serving()
        except Exception:
            tb = format_exc()
            # print tb
            cherrypy.log(tb, 'NATIVE_ADAPTER', severity=logging.ERROR)
            s, h, b = bare_error()
            self.send_response(s, h, b)

    def send_response(self, status, headers, body):
        """Send response to HTTP request."""
        req = self.req

        # Set response status
        req.status = status or b'500 Server Error'

        # Set response headers
        for header, value in headers:
            req.outheaders.append((header, value))
        if (req.ready and not req.sent_headers):
            req.sent_headers = True
            req.send_headers()

        # Set response body
        for seg in body:
            req.write(seg)


class CPHTTPServer(cheroot.server.HTTPServer):
    """Wrapper for cheroot.server.HTTPServer.

    cheroot has been designed to not reference CherryPy in any way, so
    that it can be used in other frameworks and applications. Therefore,
    we wrap it here, so we can apply some attributes from config ->
    cherrypy.server -> HTTPServer.
    """

    def __init__(self, server_adapter=cherrypy.server):
        """Initialize CPHTTPServer."""
        self.server_adapter = server_adapter

        server_name = (self.server_adapter.socket_host or
                       self.server_adapter.socket_file or
                       None)

        cheroot.server.HTTPServer.__init__(
            self, server_adapter.bind_addr, NativeGateway,
            minthreads=server_adapter.thread_pool,
            maxthreads=server_adapter.thread_pool_max,
            server_name=server_name)

        self.max_request_header_size = (
            self.server_adapter.max_request_header_size or 0)
        self.max_request_body_size = (
            self.server_adapter.max_request_body_size or 0)
        self.request_queue_size = self.server_adapter.socket_queue_size
        self.timeout = self.server_adapter.socket_timeout
        self.shutdown_timeout = self.server_adapter.shutdown_timeout
        self.protocol = self.server_adapter.protocol_version
        self.nodelay = self.server_adapter.nodelay

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
