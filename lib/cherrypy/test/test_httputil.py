"""Test helpers from ``cherrypy.lib.httputil`` module."""
import pytest
from six.moves import http_client

from cherrypy.lib import httputil


@pytest.mark.parametrize(
    'script_name,path_info,expected_url',
    [
        ('/sn/', '/pi/', '/sn/pi/'),
        ('/sn/', '/pi', '/sn/pi'),
        ('/sn/', '/', '/sn/'),
        ('/sn/', '', '/sn/'),
        ('/sn', '/pi/', '/sn/pi/'),
        ('/sn', '/pi', '/sn/pi'),
        ('/sn', '/', '/sn/'),
        ('/sn', '', '/sn'),
        ('/', '/pi/', '/pi/'),
        ('/', '/pi', '/pi'),
        ('/', '/', '/'),
        ('/', '', '/'),
        ('', '/pi/', '/pi/'),
        ('', '/pi', '/pi'),
        ('', '/', '/'),
        ('', '', '/'),
    ]
)
def test_urljoin(script_name, path_info, expected_url):
    """Test all slash+atom combinations for SCRIPT_NAME and PATH_INFO."""
    actual_url = httputil.urljoin(script_name, path_info)
    assert actual_url == expected_url


EXPECTED_200 = (200, 'OK', 'Request fulfilled, document follows')
EXPECTED_500 = (
    500,
    'Internal Server Error',
    'The server encountered an unexpected condition which '
    'prevented it from fulfilling the request.',
)
EXPECTED_404 = (404, 'Not Found', 'Nothing matches the given URI')
EXPECTED_444 = (444, 'Non-existent reason', '')


@pytest.mark.parametrize(
    'status,expected_status',
    [
        (None, EXPECTED_200),
        (200, EXPECTED_200),
        ('500', EXPECTED_500),
        (http_client.NOT_FOUND, EXPECTED_404),
        ('444 Non-existent reason', EXPECTED_444),
    ]
)
def test_valid_status(status, expected_status):
    """Check valid int, string and http_client-constants
    statuses processing."""
    assert httputil.valid_status(status) == expected_status


@pytest.mark.parametrize(
    'status_code,error_msg',
    [
        ('hey', "Illegal response status from server ('hey' is non-numeric)."),
        (
            {'hey': 'hi'},
            'Illegal response status from server '
            "({'hey': 'hi'} is non-numeric).",
        ),
        (1, 'Illegal response status from server (1 is out of range).'),
        (600, 'Illegal response status from server (600 is out of range).'),
    ]
)
def test_invalid_status(status_code, error_msg):
    """Check that invalid status cause certain errors."""
    with pytest.raises(ValueError) as excinfo:
        httputil.valid_status(status_code)

    assert error_msg in str(excinfo)
