"""Without a password, only loopback and local network clients get in.

The tests send requests through a WSGI call with a chosen peer address,
so no socket is opened.
"""

import io
import os
import re
import sys

import cherrypy
import pytest

import plexpy
from plexpy import webserve, webstart


class Mounted(Exception):
    pass


def build_conf(app_config, monkeypatch, password=""):
    config = {}

    def mount(root, script_name='', config=None, _captured=config):
        _captured.update(config)
        raise Mounted

    monkeypatch.setattr(plexpy, "PROG_DIR", os.path.dirname(os.path.dirname(plexpy.__file__)))
    monkeypatch.setattr(plexpy, "HTTP_ROOT", plexpy.HTTP_ROOT)
    monkeypatch.setattr(plexpy, "AUTH_ENABLED", plexpy.AUTH_ENABLED)
    monkeypatch.setattr(cherrypy.tree, "mount", mount)
    monkeypatch.setattr(cherrypy.config, "update", lambda *args, **kwargs: None)
    webstart._log_refused.cache_clear()

    with pytest.raises(Mounted):
        webstart.initialize({"enable_https": False, "https_cert": "", "https_cert_chain": "", "https_key": "",
                             "http_host": "0.0.0.0", "http_port": 0, "http_environment": "production",
                             "http_proxy": False, "http_root": "/", "http_username": "admin",
                             "http_password": password, "http_basic_auth": False})
    return config


@pytest.fixture
def conf(app_config, monkeypatch):
    return build_conf(app_config, monkeypatch)


def get(conf, path, peer, **headers):
    app = cherrypy.Application(webserve.WebInterface(), "", config=conf)
    status = []
    environ = {"REQUEST_METHOD": "GET", "PATH_INFO": path, "SCRIPT_NAME": "", "QUERY_STRING": "",
               "SERVER_NAME": "localhost", "SERVER_PORT": "80", "SERVER_PROTOCOL": "HTTP/1.1",
               "HTTP_HOST": "localhost", "REMOTE_ADDR": peer,
               "wsgi.url_scheme": "http", "wsgi.input": io.BytesIO(), "wsgi.errors": sys.stderr,
               "wsgi.version": (1, 0), "wsgi.multithread": False, "wsgi.multiprocess": False, "wsgi.run_once": False}
    for name, value in headers.items():
        environ["HTTP_" + name.upper()] = value
    body = b"".join(app(environ, lambda s, h, exc_info=None: status.append(s)))
    return status[0], body


@pytest.mark.parametrize("peer", [
    "127.0.0.1", "::1", "10.1.2.3", "172.16.0.5", "192.168.1.20", "100.64.0.9", "100.100.1.1",
    "169.254.1.1", "fe80::1", "fe80::1%eth0", "fd12:3456::1", "::ffff:192.168.1.5",
])
def test_local_clients_are_allowed(conf, peer):
    status, _ = get(conf, "/", peer)

    assert not status.startswith("403")


@pytest.mark.parametrize("peer", [
    "8.8.8.8", "2001:4860:4860::8888", "::ffff:8.8.8.8", "2002:808:808::1", "2001:0:4136:e378:8000:63bf:3fff:fdd2", "not an address", "",
])
def test_other_clients_are_refused(conf, peer):
    status, _ = get(conf, "/", peer)

    assert status.startswith("403")


@pytest.fixture
def warnings(monkeypatch):
    messages = []
    monkeypatch.setattr(webstart.logger, "warn", lambda fmt, *args: messages.append(fmt % args))
    return messages


def refusal(conf, warnings, peer, **headers):
    """Return the log line. The body must hold no address and no config key."""
    status, body = get(conf, "/", peer, **headers)
    assert status.startswith("403")
    assert b"allow_public_no_password" not in body
    assert b"config.ini" not in body
    assert not re.search(rb"\d+\.\d+\.\d+\.\d+|::", body)
    return warnings[-1]


def test_the_body_points_a_client_to_the_settings(conf):
    status, body = get(conf, "/", "8.8.8.8")

    assert body == (b"Tautulli refused this connection because no password is set and you are not on the "
                    b"local network.\n\nConnect to Tautulli from the local network to set a password in the Settings.\n")


def test_a_remote_peer_is_logged_without_the_proxy_setting(conf, warnings):
    line = refusal(conf, warnings, "8.8.8.8")

    assert line.endswith("Refused 8.8.8.8. No password is set. The client address 8.8.8.8 is not on the local network.")
    assert "HTTP Proxy" not in line
    assert "IPv6" not in line


def test_a_remote_forwarded_client_is_logged(conf, app_config, warnings):
    app_config.HTTP_PROXY = 1

    line = refusal(conf, warnings, "127.0.0.1", X_Forwarded_For="1.1.1.1, 8.8.8.8")

    assert "The client address 8.8.8.8 is not on the local network." in line
    assert "HTTP Proxy" not in line


def test_a_remote_ipv6_client_gets_the_ipv6_line(conf, warnings):
    line = refusal(conf, warnings, "2001:4860:4860::8888")

    assert "Public IPv6 addresses count as remote." in line


def test_a_forwarding_header_with_the_proxy_setting_off_is_logged(conf, warnings):
    line = refusal(conf, warnings, "127.0.0.1", X_Real_IP="192.168.1.5")

    assert "A reverse proxy forwarded this request, and Enable HTTP Proxy is off." in line


def test_a_proxy_without_x_forwarded_for_is_logged(conf, app_config, warnings):
    app_config.HTTP_PROXY = 1

    line = refusal(conf, warnings, "127.0.0.1", X_Real_IP="192.168.1.5")

    assert "The reverse proxy must send X-Forwarded-For." in line
    assert "Enable HTTP Proxy" not in line


def test_an_unreadable_address_is_logged(conf, warnings):
    line = refusal(conf, warnings, "not an address")

    assert "Tautulli could not read the client address." in line


@pytest.mark.parametrize("peer", [
    "11.0.0.1", "192.169.0.1", "100.63.255.255", "100.128.0.1", "169.255.0.1", "fb00::1", "fe00::1", "fec0::1",
])
def test_addresses_just_outside_the_local_networks_are_refused(conf, peer):
    status, _ = get(conf, "/", peer)

    assert status.startswith("403")


def test_the_refusal_is_plain_text(conf):
    app = cherrypy.Application(webserve.WebInterface(), "", config=conf)
    headers = []
    environ = {"REQUEST_METHOD": "GET", "PATH_INFO": "/", "SCRIPT_NAME": "", "QUERY_STRING": "",
               "SERVER_NAME": "localhost", "SERVER_PORT": "80", "SERVER_PROTOCOL": "HTTP/1.1",
               "HTTP_HOST": "localhost", "REMOTE_ADDR": "8.8.8.8",
               "wsgi.url_scheme": "http", "wsgi.input": io.BytesIO(), "wsgi.errors": sys.stderr,
               "wsgi.version": (1, 0), "wsgi.multithread": False, "wsgi.multiprocess": False, "wsgi.run_once": False}
    b"".join(app(environ, lambda s, h, exc_info=None: headers.extend(h)))

    assert dict(headers)["Content-Type"].startswith("text/plain")


def test_the_api_is_gated(conf):
    status, _ = get(conf, "/api/v2?cmd=get_apikey", "8.8.8.8")

    assert status.startswith("403")


@pytest.mark.parametrize("path", ["/status", "/image", "/newsletter", "/favicon.ico",
                                  "/css/tautulli.css", "/js/script.js", "/images/logo.png",
                                  "/interfaces/default/css/tautulli.css", "/fonts/fontawesome-webfont.woff"])
def test_exempt_routes_stay_open(conf, path):
    status, _ = get(conf, path, "8.8.8.8")

    assert not status.startswith("403")


def test_the_newsletter_login_redirect_is_gated(conf):
    status, _ = get(conf, "/newsletter_auth", "8.8.8.8")

    assert status.startswith("403")


@pytest.mark.parametrize("header", ["X-Forwarded-For", "Forwarded", "X-Real-IP", "Via"])
def test_a_forwarding_header_is_refused_without_the_proxy_setting(conf, header):
    status, _ = get(conf, "/", "127.0.0.1", **{header: "192.168.1.5"})

    assert status.startswith("403")


@pytest.mark.parametrize("xff, allowed", [
    ("192.168.1.5", True),
    ("8.8.8.8, 192.168.1.5", True),
    ("192.168.1.5, 8.8.8.8", False),
    ("garbage", False),
])
def test_the_rightmost_forwarded_address_decides_with_the_proxy_setting(conf, app_config, xff, allowed):
    app_config.HTTP_PROXY = 1

    status, _ = get(conf, "/", "127.0.0.1", X_Forwarded_For=xff)

    assert status.startswith("403") is not allowed


def test_the_proxy_setting_refuses_a_proxy_that_sends_only_x_real_ip(conf, app_config):
    app_config.HTTP_PROXY = 1

    status, _ = get(conf, "/", "127.0.0.1", X_Real_IP="192.168.1.5")

    assert status.startswith("403")


def test_the_log_names_the_forwarded_client(conf, app_config, monkeypatch):
    app_config.HTTP_PROXY = 1
    messages = []
    monkeypatch.setattr(webstart.logger, "warn", lambda *args: messages.append(args))

    get(conf, "/", "127.0.0.1", X_Forwarded_For="8.8.8.8")

    assert messages[0][1] == "8.8.8.8"
    assert messages[0][2] == "The client address 8.8.8.8 is not on the local network."


def test_the_startup_warning_follows_the_gate(app_config, monkeypatch):
    messages = []
    monkeypatch.setattr(webstart.logger, "warn", lambda *args: messages.append(args[0]))

    build_conf(app_config, monkeypatch)
    assert any("only loopback and local network" in m and "allow_public_no_password = 1 in config.ini" in m
               for m in messages)

    messages.clear()
    app_config.ALLOW_PUBLIC_NO_PASSWORD = 1
    build_conf(app_config, monkeypatch)
    assert not any("only loopback and local network" in m for m in messages)


def test_a_public_peer_is_refused_even_with_the_proxy_setting(conf, app_config):
    app_config.HTTP_PROXY = 1

    status, _ = get(conf, "/", "8.8.8.8", X_Forwarded_For="192.168.1.5")

    assert status.startswith("403")


def test_each_refused_address_is_logged_once(conf, monkeypatch):
    messages = []
    monkeypatch.setattr(webstart.logger, "warn", lambda *args: messages.append(args))

    for _ in range(3):
        get(conf, "/", "8.8.8.8")

    assert len(messages) == 1


def test_the_refusal_log_remembers_recent_addresses(conf, warnings):
    for peer in ("8.8.8.8", "8.8.4.4", "1.1.1.1", "8.8.8.8"):
        get(conf, "/", peer)

    assert len(warnings) == 3


def test_the_refusal_log_forgets_the_oldest_address_after_1000(conf, monkeypatch):
    messages = []
    monkeypatch.setattr(webstart.logger, "warn", lambda *args: messages.append(args))

    for i in range(1001):
        get(conf, "/", "2.0.%d.%d" % (i // 256, i % 256))
    get(conf, "/", "2.0.0.0")

    assert len(messages) == 1002


def test_the_gate_is_off_with_a_password(app_config, monkeypatch):
    conf = build_conf(app_config, monkeypatch, password="hash")

    assert not conf["/"]["tools.nopwgate.on"]


def test_the_gate_is_off_with_the_opt_out_key(app_config, monkeypatch):
    app_config.ALLOW_PUBLIC_NO_PASSWORD = 1
    conf = build_conf(app_config, monkeypatch)

    assert not conf["/"]["tools.nopwgate.on"]
    assert not get(conf, "/", "8.8.8.8")[0].startswith("403")


def test_the_opt_out_key_defaults_to_off(app_config):
    assert app_config.ALLOW_PUBLIC_NO_PASSWORD == 0
