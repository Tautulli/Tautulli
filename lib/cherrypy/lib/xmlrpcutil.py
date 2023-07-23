"""XML-RPC tool helpers."""
import sys
from xmlrpc.client import (
    loads as xmlrpc_loads, dumps as xmlrpc_dumps,
    Fault as XMLRPCFault
)

import cherrypy
from cherrypy._cpcompat import ntob


def process_body():
    """Return (params, method) from request body."""
    try:
        return xmlrpc_loads(cherrypy.request.body.read())
    except Exception:
        return ('ERROR PARAMS', ), 'ERRORMETHOD'


def patched_path(path):
    """Return 'path', doctored for RPC."""
    if not path.endswith('/'):
        path += '/'
    if path.startswith('/RPC2/'):
        # strip the first /rpc2
        path = path[5:]
    return path


def _set_response(body):
    """Set up HTTP status, headers and body within CherryPy."""
    # The XML-RPC spec (http://www.xmlrpc.com/spec) says:
    # "Unless there's a lower-level error, always return 200 OK."
    # Since Python's xmlrpc_client interprets a non-200 response
    # as a "Protocol Error", we'll just return 200 every time.
    response = cherrypy.response
    response.status = '200 OK'
    response.body = ntob(body, 'utf-8')
    response.headers['Content-Type'] = 'text/xml'
    response.headers['Content-Length'] = len(body)


def respond(body, encoding='utf-8', allow_none=0):
    """Construct HTTP response body."""
    if not isinstance(body, XMLRPCFault):
        body = (body,)

    _set_response(
        xmlrpc_dumps(
            body, methodresponse=1,
            encoding=encoding,
            allow_none=allow_none
        )
    )


def on_error(*args, **kwargs):
    """Construct HTTP response body for an error response."""
    body = str(sys.exc_info()[1])
    _set_response(xmlrpc_dumps(XMLRPCFault(1, body)))
