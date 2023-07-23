import cherrypy
from cherrypy import _json as json
from cherrypy._cpcompat import text_or_bytes, ntou


def json_processor(entity):
    """Read application/json data into request.json."""
    if not entity.headers.get(ntou('Content-Length'), ntou('')):
        raise cherrypy.HTTPError(411)

    body = entity.fp.read()
    with cherrypy.HTTPError.handle(ValueError, 400, 'Invalid JSON document'):
        cherrypy.serving.request.json = json.decode(body.decode('utf-8'))


def json_in(content_type=[ntou('application/json'), ntou('text/javascript')],
            force=True, debug=False, processor=json_processor):
    """Add a processor to parse JSON request entities:
    The default processor places the parsed data into request.json.

    Incoming request entities which match the given content_type(s) will
    be deserialized from JSON to the Python equivalent, and the result
    stored at cherrypy.request.json. The 'content_type' argument may
    be a Content-Type string or a list of allowable Content-Type strings.

    If the 'force' argument is True (the default), then entities of other
    content types will not be allowed; "415 Unsupported Media Type" is
    raised instead.

    Supply your own processor to use a custom decoder, or to handle the parsed
    data differently.  The processor can be configured via
    tools.json_in.processor or via the decorator method.

    Note that the deserializer requires the client send a Content-Length
    request header, or it will raise "411 Length Required". If for any
    other reason the request entity cannot be deserialized from JSON,
    it will raise "400 Bad Request: Invalid JSON document".
    """
    request = cherrypy.serving.request
    if isinstance(content_type, text_or_bytes):
        content_type = [content_type]

    if force:
        if debug:
            cherrypy.log('Removing body processors %s' %
                         repr(request.body.processors.keys()), 'TOOLS.JSON_IN')
        request.body.processors.clear()
        request.body.default_proc = cherrypy.HTTPError(
            415, 'Expected an entity of content type %s' %
            ', '.join(content_type))

    for ct in content_type:
        if debug:
            cherrypy.log('Adding body processor for %s' % ct, 'TOOLS.JSON_IN')
        request.body.processors[ct] = processor


def json_handler(*args, **kwargs):
    value = cherrypy.serving.request._json_inner_handler(*args, **kwargs)
    return json.encode(value)


def json_out(content_type='application/json', debug=False,
             handler=json_handler):
    """Wrap request.handler to serialize its output to JSON. Sets Content-Type.

    If the given content_type is None, the Content-Type response header
    is not set.

    Provide your own handler to use a custom encoder.  For example
    cherrypy.config['tools.json_out.handler'] = <function>, or
    @json_out(handler=function).
    """
    request = cherrypy.serving.request
    # request.handler may be set to None by e.g. the caching tool
    # to signal to all components that a response body has already
    # been attached, in which case we don't need to wrap anything.
    if request.handler is None:
        return
    if debug:
        cherrypy.log('Replacing %s with JSON handler' % request.handler,
                     'TOOLS.JSON_OUT')
    request._json_inner_handler = request.handler
    request.handler = handler
    if content_type is not None:
        if debug:
            cherrypy.log('Setting Content-Type to %s' %
                         content_type, 'TOOLS.JSON_OUT')
        cherrypy.serving.response.headers['Content-Type'] = content_type
