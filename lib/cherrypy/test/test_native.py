"""Test the native server."""

import pytest
from requests_toolbelt import sessions

import cherrypy._cpnative_server


pytestmark = pytest.mark.skipif(
    'sys.platform == "win32"',
    reason='tests fail on Windows',
)


@pytest.fixture
def cp_native_server(request):
    """A native server."""
    class Root(object):
        @cherrypy.expose
        def index(self):
            return 'Hello World!'

    cls = cherrypy._cpnative_server.CPHTTPServer
    cherrypy.server.httpserver = cls(cherrypy.server)

    cherrypy.tree.mount(Root(), '/')
    cherrypy.engine.start()
    request.addfinalizer(cherrypy.engine.stop)
    url = 'http://localhost:{cherrypy.server.socket_port}'.format(**globals())
    return sessions.BaseUrlSession(url)


def test_basic_request(cp_native_server):
    """A request to a native server should succeed."""
    resp = cp_native_server.get('/')
    assert resp.ok
    assert resp.status_code == 200
    assert resp.text == 'Hello World!'
