import cherrypy
import pytest

from plexpy import webstart


@pytest.fixture
def response_headers():
    # cherrypy.response is thread local and outlives the test, so put the
    # headers back the way they were.
    original = dict(cherrypy.response.headers)
    cherrypy.response.headers.clear()
    yield cherrypy.response.headers
    cherrypy.response.headers.clear()
    cherrypy.response.headers.update(original)


def test_x_frame_options_defaults_to_sameorigin(app_config, response_headers):
    assert app_config.X_FRAME_OPTIONS == 'SAMEORIGIN'

    webstart.set_security_headers()

    assert response_headers['X-Frame-Options'] == 'SAMEORIGIN'


def test_x_frame_options_comes_from_the_config(app_config, response_headers):
    # Reverse proxy setups that frame Tautulli from another origin need to
    # widen this, which is why it moved out of the hard coded header list.
    app_config.X_FRAME_OPTIONS = 'ALLOW-FROM https://example.com'

    webstart.set_security_headers()

    assert response_headers['X-Frame-Options'] == 'ALLOW-FROM https://example.com'


def test_the_other_security_headers_stay_fixed(app_config, response_headers):
    webstart.set_security_headers()

    assert response_headers['X-Content-Type-Options'] == 'nosniff'
    assert response_headers['Referrer-Policy'] == 'strict-origin-when-cross-origin'
