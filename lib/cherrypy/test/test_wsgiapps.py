import sys

import cherrypy
from cherrypy._cpcompat import ntob
from cherrypy.test import helper


class WSGIGraftTests(helper.CPWebCase):

    @staticmethod
    def setup_server():

        def test_app(environ, start_response):
            status = '200 OK'
            response_headers = [('Content-type', 'text/plain')]
            start_response(status, response_headers)
            output = ['Hello, world!\n',
                      'This is a wsgi app running within CherryPy!\n\n']
            keys = list(environ.keys())
            keys.sort()
            for k in keys:
                output.append('%s: %s\n' % (k, environ[k]))
            return [ntob(x, 'utf-8') for x in output]

        def test_empty_string_app(environ, start_response):
            status = '200 OK'
            response_headers = [('Content-type', 'text/plain')]
            start_response(status, response_headers)
            return [
                b'Hello', b'', b' ', b'', b'world',
            ]

        class WSGIResponse(object):

            def __init__(self, appresults):
                self.appresults = appresults
                self.iter = iter(appresults)

            def __iter__(self):
                return self

            if sys.version_info >= (3, 0):
                def __next__(self):
                    return next(self.iter)
            else:
                def next(self):
                    return self.iter.next()

            def close(self):
                if hasattr(self.appresults, 'close'):
                    self.appresults.close()

        class ReversingMiddleware(object):

            def __init__(self, app):
                self.app = app

            def __call__(self, environ, start_response):
                results = app(environ, start_response)

                class Reverser(WSGIResponse):

                    if sys.version_info >= (3, 0):
                        def __next__(this):
                            line = list(next(this.iter))
                            line.reverse()
                            return bytes(line)
                    else:
                        def next(this):
                            line = list(this.iter.next())
                            line.reverse()
                            return ''.join(line)

                return Reverser(results)

        class Root:

            @cherrypy.expose
            def index(self):
                return ntob("I'm a regular CherryPy page handler!")

        cherrypy.tree.mount(Root())

        cherrypy.tree.graft(test_app, '/hosted/app1')
        cherrypy.tree.graft(test_empty_string_app, '/hosted/app3')

        # Set script_name explicitly to None to signal CP that it should
        # be pulled from the WSGI environ each time.
        app = cherrypy.Application(Root(), script_name=None)
        cherrypy.tree.graft(ReversingMiddleware(app), '/hosted/app2')

    wsgi_output = '''Hello, world!
This is a wsgi app running within CherryPy!'''

    def test_01_standard_app(self):
        self.getPage('/')
        self.assertBody("I'm a regular CherryPy page handler!")

    def test_04_pure_wsgi(self):
        if not cherrypy.server.using_wsgi:
            return self.skip('skipped (not using WSGI)... ')
        self.getPage('/hosted/app1')
        self.assertHeader('Content-Type', 'text/plain')
        self.assertInBody(self.wsgi_output)

    def test_05_wrapped_cp_app(self):
        if not cherrypy.server.using_wsgi:
            return self.skip('skipped (not using WSGI)... ')
        self.getPage('/hosted/app2/')
        body = list("I'm a regular CherryPy page handler!")
        body.reverse()
        body = ''.join(body)
        self.assertInBody(body)

    def test_06_empty_string_app(self):
        if not cherrypy.server.using_wsgi:
            return self.skip('skipped (not using WSGI)... ')
        self.getPage('/hosted/app3')
        self.assertHeader('Content-Type', 'text/plain')
        self.assertInBody('Hello world')
