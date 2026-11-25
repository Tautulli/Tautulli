"""API2 handlers borrowed from WebInterface run with an API2 instance as self.

helpers.addtoapi copies the handler onto API2. A self call to a helper that
only WebInterface has raised AttributeError, and /api/v2 answered 500.
"""

import ast
import inspect
import json
import textwrap

import cherrypy
import pytest

from plexpy import plextv, pmsconnect
from plexpy import webserve  # noqa: F401  (registers the handlers on API2)
from plexpy.api2 import API2

URL = "http://img.invalid/avatar.png"


@pytest.fixture
def api(app_db, app_config, tmp_path):
    app_config.API_ENABLED = 1
    app_config.API_KEY = "a" * 32
    app_config.CACHE_DIR = str(tmp_path)
    app_config.CACHE_IMAGES = 0

    def run(**kwargs):
        out = API2()._api_run(apikey=app_config.API_KEY, **kwargs)
        return cherrypy.response.status, out
    return run


def test_image_proxy_serves_a_stored_http_image(api, app_db, monkeypatch):
    app_db.upsert("users", {"user_id": 1}, {"username": "u", "thumb": URL})
    monkeypatch.setattr(pmsconnect.PmsConnect, "get_image", lambda self, **kwargs: (b"image", "image/png"))

    assert api(cmd="pms_image_proxy", img=URL) == (200, b"image")


def test_image_proxy_serves_the_fallback_image(api, monkeypatch):
    requests = []

    def get_image(self, **kwargs):
        requests.append(kwargs)
        if kwargs["img"] == "/library/metadata/6/thumb":
            return b"fallback", "image/png"

    monkeypatch.setattr(pmsconnect.PmsConnect, "get_image", get_image)

    assert api(cmd="pms_image_proxy", img="/library/metadata/5/thumb", fallback="/library/metadata/6/thumb",
               width="300", img_format="jpg", refresh="1", clip="1") == (200, b"fallback")
    first, fallback = requests
    assert fallback == dict(first, img="/library/metadata/6/thumb")
    assert (fallback["width"], fallback["img_format"], fallback["refresh"], fallback["clip"]) == ("300", "jpg", "1", True)


def test_get_server_id_returns_the_server_url(api, monkeypatch):
    servers = [{"ip": "1.2.3.4", "port": "32400", "clientIdentifier": "abc"}]
    requests = []

    def get_server_resources(**kwargs):
        requests.append(kwargs)
        return {"pms_url": "https://1.2.3.4:32400"}

    monkeypatch.setattr(plextv.PlexTV, "discover", lambda self: servers)
    monkeypatch.setattr(plextv, "get_server_resources", get_server_resources)

    status, out = api(cmd="get_server_id", hostname="1.2.3.4", port="32400", ssl="1", manual="1", get_url=1)

    assert status == 200
    assert json.loads(out)["response"]["data"] == {"identifier": "abc", "url": "https://1.2.3.4:32400", "ws": None}
    # ssl and manual differ so a swap of the two also fails.
    assert requests == [{"return_server": True, "pms_ip": "1.2.3.4", "pms_port": "32400", "pms_ssl": True,
                         "pms_url_manual": "1", "pms_identifier": "abc"}]


def test_borrowed_handlers_use_only_api2_attributes():
    api = API2()
    missing = []
    for name in dir(API2):
        function = getattr(API2, name)
        if not inspect.isfunction(function) or function.__qualname__.startswith("API2."):
            continue
        tree = ast.parse(textwrap.dedent(inspect.getsource(function)))
        missing += ["%s: self.%s" % (name, node.attr) for node in ast.walk(tree)
                    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name)
                    and node.value.id == "self" and not hasattr(api, node.attr)]

    assert missing == []
