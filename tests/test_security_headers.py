import re

import cherrypy
import pytest

from plexpy import webstart

from tests.test_archive_users import library, seeded, web_pages  # noqa: F401  (fixtures)


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


@pytest.mark.parametrize('value, selected', [
    ('SAMEORIGIN', 'SAMEORIGIN'),
    ('DENY', 'DENY'),
    ('*', '*'),
    # #2807 told users to set a blank value by hand. It sends no header, same as *.
    ('', '*'),
])
def test_settings_page_selects_the_saved_frame_option(web_pages, app_config, value, selected):
    # A save posts the selected option's value. If the page does not select
    # that value again, the next save writes SAMEORIGIN over it.
    app_config.X_FRAME_OPTIONS = value

    select = re.search(r'<select[^>]*id="x_frame_options".*?</select>', web_pages.settings(), re.S).group(0)

    assert re.findall(r'<option value="([^"]*)" selected>', select) == [selected]
