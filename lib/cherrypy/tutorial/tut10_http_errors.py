"""

Tutorial: HTTP errors

HTTPError is used to return an error response to the client.
CherryPy has lots of options regarding how such errors are
logged, displayed, and formatted.

"""

import os
import os.path

import cherrypy

localDir = os.path.dirname(__file__)
curpath = os.path.normpath(os.path.join(os.getcwd(), localDir))


class HTTPErrorDemo(object):

    # Set a custom response for 403 errors.
    _cp_config = {'error_page.403':
                  os.path.join(curpath, 'custom_error.html')}

    @cherrypy.expose
    def index(self):
        # display some links that will result in errors
        tracebacks = cherrypy.request.show_tracebacks
        if tracebacks:
            trace = 'off'
        else:
            trace = 'on'

        return """
        <html><body>
            <p>Toggle tracebacks <a href="toggleTracebacks">%s</a></p>
            <p><a href="/doesNotExist">Click me; I'm a broken link!</a></p>
            <p>
              <a href="/error?code=403">
                Use a custom error page from a file.
              </a>
            </p>
            <p>These errors are explicitly raised by the application:</p>
            <ul>
                <li><a href="/error?code=400">400</a></li>
                <li><a href="/error?code=401">401</a></li>
                <li><a href="/error?code=402">402</a></li>
                <li><a href="/error?code=500">500</a></li>
            </ul>
            <p><a href="/messageArg">You can also set the response body
            when you raise an error.</a></p>
        </body></html>
        """ % trace

    @cherrypy.expose
    def toggleTracebacks(self):
        # simple function to toggle tracebacks on and off
        tracebacks = cherrypy.request.show_tracebacks
        cherrypy.config.update({'request.show_tracebacks': not tracebacks})

        # redirect back to the index
        raise cherrypy.HTTPRedirect('/')

    @cherrypy.expose
    def error(self, code):
        # raise an error based on the get query
        raise cherrypy.HTTPError(status=code)

    @cherrypy.expose
    def messageArg(self):
        message = ("If you construct an HTTPError with a 'message' "
                   'argument, it wil be placed on the error page '
                   '(underneath the status line by default).')
        raise cherrypy.HTTPError(500, message=message)


tutconf = os.path.join(os.path.dirname(__file__), 'tutorial.conf')

if __name__ == '__main__':
    # CherryPy always starts with app.root when trying to map request URIs
    # to objects, so we need to mount a request handler root. A request
    # to '/' will be mapped to HelloWorld().index().
    cherrypy.quickstart(HTTPErrorDemo(), config=tutconf)
