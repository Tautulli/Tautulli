"""A verified websocket trusts the system CA store and the certifi bundle."""

import ssl

import certifi
import pytest
import websocket

import plexpy
from plexpy import helpers, plextv, web_socket, webserve

PMS_URL = "https://1-2-3-4.0123456789abcdef0123456789abcdef.plex.direct:32400"


@pytest.fixture
def system_cert(app_config, tmp_path, monkeypatch):
    # The system store holds one self-signed certificate. The macOS app finds no system store at all.
    cert = tmp_path / "system.pem"
    assert helpers.create_https_certificates(str(cert), str(tmp_path / "system.key"))
    monkeypatch.setenv("SSL_CERT_FILE", str(cert))
    monkeypatch.setenv("SSL_CERT_DIR", str(tmp_path / "none"))


@pytest.fixture
def sslopts(monkeypatch):
    calls = []

    def fake_create_connection(url, sslopt=None, **kwargs):
        calls.append(sslopt)
        raise websocket.WebSocketException("stub")

    monkeypatch.setattr(websocket, "create_connection", fake_create_connection)
    return calls


def assert_trusts_system_and_certifi(sslopt):
    context = sslopt["context"]
    certifi_certs = ssl.create_default_context(cafile=certifi.where()).cert_store_stats()["x509"]
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname
    assert certifi_certs > 0
    # Windows also loads its own store, so the count can be higher there
    assert context.cert_store_stats()["x509"] >= certifi_certs + 1


def test_websocket_trusts_system_and_certifi(app_config, system_cert, sslopts, monkeypatch):
    app_config.PMS_SSL = 1
    app_config.PMS_URL = PMS_URL
    app_config.VERIFY_SSL_CERT = 1
    monkeypatch.setattr(plexpy, "WS_CONNECTED", False)
    monkeypatch.setattr(web_socket, "on_disconnect", lambda: None)

    web_socket.run()

    assert len(sslopts) == 1
    assert_trusts_system_and_certifi(sslopts[0])


def test_websocket_connection_test_trusts_system_and_certifi(app_config, system_cert, sslopts, monkeypatch):
    app_config.VERIFY_SSL_CERT = 1
    servers = [{"ip": "1.2.3.4", "port": "32400", "clientIdentifier": "abc"}]
    monkeypatch.setattr(plextv.PlexTV, "discover", lambda self: servers)
    monkeypatch.setattr(webserve.WebInterface, "get_server_resources",
                        lambda self, **kwargs: {"pms_url": PMS_URL})

    result = webserve.WebInterface().get_server_id(hostname="1.2.3.4", port="32400", ssl=1,
                                                   get_url=1, test_websocket=1)

    assert result["ws"] is False
    assert len(sslopts) == 1
    assert_trusts_system_and_certifi(sslopts[0])
