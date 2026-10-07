# -*- coding: utf-8 -*-
#
import os
import os.path
import socket
import ssl
import unittest
from types import SimpleNamespace
from unittest import mock

import websocket
from websocket._exceptions import (
    WebSocketAddressException,
    WebSocketProxyException,
    WebSocketException,
)
from websocket._http import (
    _get_addrinfo_list,
    _start_proxied_socket,
    _tunnel,
    _wrap_sni_socket,
    connect,
    proxy_info,
    read_headers,
    HAVE_PYTHON_SOCKS,
)

"""
test_http.py
websocket - WebSocket client library for Python

Copyright 2026 engn33r

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

try:
    from python_socks._errors import ProxyConnectionError, ProxyError, ProxyTimeoutError
except:
    from websocket._http import ProxyConnectionError, ProxyError, ProxyTimeoutError

# Skip test to access the internet unless TEST_WITH_INTERNET == 1
TEST_WITH_INTERNET = os.environ.get("TEST_WITH_INTERNET", "0") == "1"
TEST_WITH_PROXY = os.environ.get("TEST_WITH_PROXY", "0") == "1"
# Skip tests relying on local websockets server unless LOCAL_WS_SERVER_PORT != -1
LOCAL_WS_SERVER_PORT = os.environ.get("LOCAL_WS_SERVER_PORT", "-1")
TEST_WITH_LOCAL_SERVER = LOCAL_WS_SERVER_PORT != "-1"


class SockMock:
    def __init__(self):
        self.data = []
        self.sent = []

    def add_packet(self, data):
        self.data.append(data)

    def gettimeout(self):
        return None

    def recv(self, bufsize):
        if self.data:
            e = self.data.pop(0)
            if isinstance(e, Exception):
                raise e
            if len(e) > bufsize:
                self.data.insert(0, e[bufsize:])
            return e[:bufsize]

    def send(self, data):
        self.sent.append(data)
        return len(data)

    def close(self):
        pass


class HeaderSockMock(SockMock):
    def __init__(self, fname):
        SockMock.__init__(self)
        path = os.path.join(os.path.dirname(__file__), fname)
        with open(path, "rb") as f:
            self.add_packet(f.read())


class OptsList:
    def __init__(self):
        self.timeout = 1
        self.sockopt = []
        self.sslopt = {"cert_reqs": ssl.CERT_NONE}


class HttpTest(unittest.TestCase):
    def test_read_header(self):
        status, header, _ = read_headers(HeaderSockMock("data/header01.txt"))
        self.assertEqual(status, 101)
        self.assertEqual(header["connection"], "Upgrade")
        # header02.txt is intentionally malformed
        self.assertRaises(
            WebSocketException, read_headers, HeaderSockMock("data/header02.txt")
        )

    def test_read_header_malformed_status_line(self):
        """Malformed responses surface as WebSocketException, not raw
        IndexError, ValueError, or UnicodeDecodeError."""
        one_token = SockMock()
        one_token.add_packet(b"GARBAGE\r\n\r\n")
        with self.assertRaises(WebSocketException) as cm:
            read_headers(one_token)
        self.assertIn("Invalid status line", str(cm.exception))

        bad_status = SockMock()
        bad_status.add_packet(b"HTTP/1.1 XX Switching Protocols\r\n\r\n")
        with self.assertRaises(WebSocketException) as cm:
            read_headers(bad_status)
        self.assertIn("Invalid status line", str(cm.exception))

        bad_utf8 = SockMock()
        bad_utf8.add_packet(b"HTTP/1.1\xff 101 Switching Protocols\r\n\r\n")
        with self.assertRaises(WebSocketException) as cm:
            read_headers(bad_utf8)
        self.assertIn("UTF-8", str(cm.exception))
        self.assertIn("at byte 8", str(cm.exception))

    def test_get_resp_headers_invalid_content_length(self):
        """A non-numeric Content-Length on an error response surfaces as
        WebSocketException, not raw ValueError."""
        from websocket._handshake import _get_resp_headers

        sock = SockMock()
        sock.add_packet(b"HTTP/1.1 400 Bad Request\r\nContent-Length: abc\r\n\r\n")
        with self.assertRaises(WebSocketException) as cm:
            _get_resp_headers(sock)
        self.assertIn("Invalid content-length", str(cm.exception))

    def test_tunnel(self):
        self.assertRaises(
            WebSocketProxyException,
            _tunnel,
            HeaderSockMock("data/header01.txt"),
            "example.com",
            80,
            ("username", "password"),
        )
        self.assertRaises(
            WebSocketProxyException,
            _tunnel,
            HeaderSockMock("data/header02.txt"),
            "example.com",
            80,
            ("username", "password"),
        )

    def test_connect(self):
        # Test proxy error handling without requiring internet - using fast local addresses and short timeouts
        if HAVE_PYTHON_SOCKS:
            # Test SOCKS proxy types with non-routable addresses (fast failure)
            for proxy_type in ["socks4", "socks4a", "socks5", "socks5h"]:
                self.assertRaises(
                    (ProxyTimeoutError, OSError, ConnectionRefusedError),
                    _start_proxied_socket,
                    "wss://127.0.0.1",  # Use localhost instead of example.com
                    OptsList(),
                    proxy_info(
                        http_proxy_host="127.0.0.1",  # Use localhost
                        http_proxy_port="9999",  # Non-existent port for fast failure
                        proxy_type=proxy_type,
                        http_proxy_timeout=0.1,  # Very short timeout
                    ),
                )

            # Test SOCKS connection error with guaranteed-closed port
            self.assertRaises(
                (ProxyConnectionError, ConnectionRefusedError, OSError),
                connect,
                "wss://127.0.0.1",
                OptsList(),
                proxy_info(
                    http_proxy_host="127.0.0.1",
                    http_proxy_port=9999,
                    proxy_type="socks4",
                    http_proxy_timeout=0.1,  # Very short timeout
                ),
                None,
            )

        # Test TypeError with None hostname (no network required)
        self.assertRaises(
            WebSocketAddressException,
            _get_addrinfo_list,
            None,
            80,
            True,
            proxy_info(
                http_proxy_host="127.0.0.1", http_proxy_port="9999", proxy_type="http"
            ),
        )

        # Test HTTP proxy timeout with non-existent port (fast failure)
        self.assertRaises(
            (socket.timeout, ConnectionRefusedError, OSError),
            connect,
            "wss://127.0.0.1",  # Use localhost
            OptsList(),
            proxy_info(
                http_proxy_host="127.0.0.1",  # Use localhost
                http_proxy_port=9999,  # Non-existent port
                proxy_type="http",
                http_proxy_timeout=0.1,  # Very short timeout
            ),
            None,
        )

    @unittest.skipUnless(TEST_WITH_INTERNET, "Internet-requiring tests are disabled")
    def test_connect_with_internet(self):
        # Separate test for cases that actually need internet
        self.assertEqual(
            connect(
                "wss://google.com",
                OptsList(),
                proxy_info(
                    http_proxy_host="8.8.8.8", http_proxy_port=8080, proxy_type="http"
                ),
                True,
            ),
            (True, ("google.com", 443, "/")),
        )

    def test_proxy_connect(self):
        """Proxy logic should exercise SOCKS path and HTTP tunnel path offline."""

        proxy_cfg = proxy_info(
            http_proxy_host="proxy.local",
            http_proxy_port="1080",
            proxy_type="socks5",
            http_proxy_auth=("user", "pass"),
        )
        options = OptsList()
        proxy_instance = mock.Mock()
        proxied_socket = mock.Mock()
        ssl_wrapped_socket = mock.Mock()
        proxy_instance.connect.return_value = proxied_socket

        proxy_types = SimpleNamespace(SOCKS4="socks4", SOCKS5="socks5")

        with mock.patch("websocket._http.HAVE_PYTHON_SOCKS", True), mock.patch.object(
            websocket._http, "ProxyType", proxy_types
        ), mock.patch("websocket._http.Proxy", create=True) as proxy_cls, mock.patch(
            "websocket._http._ssl_socket", return_value=ssl_wrapped_socket
        ) as ssl_socket:
            proxy_cls.create.return_value = proxy_instance
            sock, addr = _start_proxied_socket(
                "wss://example.com/ws", options, proxy_cfg
            )

        proxy_cls.create.assert_called_once()
        proxy_instance.connect.assert_called_once_with("example.com", 443, timeout=None)
        ssl_socket.assert_called_once_with(
            proxied_socket, options.sslopt, "example.com"
        )
        self.assertIs(sock, ssl_wrapped_socket)
        self.assertEqual(addr, ("example.com", 443, "/ws"))

        fake_sock = mock.Mock()
        with mock.patch("websocket._http.send") as send_mock, mock.patch(
            "websocket._http.read_headers", return_value=(200, {}, "OK")
        ):
            returned = _tunnel(fake_sock, "endpoint", 9000, ("demo", "secret"))

        self.assertIs(returned, fake_sock)
        send_mock.assert_called_once()

    def test_proxy_connect_no_port_raises(self):
        """A SOCKS proxy with an explicit host but no port raises the same
        WebSocketProxyException as the http-proxy path, instead of passing
        port 0 (or None) to python-socks."""
        for proxy_cfg in (
            proxy_info(http_proxy_host="proxy.local", proxy_type="socks5"),
            proxy_info(
                http_proxy_host="proxy.local",
                http_proxy_port=None,
                proxy_type="socks5",
            ),
        ):
            with self.assertRaises(WebSocketProxyException):
                _start_proxied_socket("ws://example.com/ws", OptsList(), proxy_cfg)

    @unittest.skipUnless(TEST_WITH_INTERNET, "Internet-requiring tests are disabled")
    def test_sslopt(self):
        ssloptions = {
            "check_hostname": False,
            "server_hostname": "ServerName",
            "ssl_version": ssl.PROTOCOL_TLS_CLIENT,
            "ciphers": "TLS_AES_256_GCM_SHA384:TLS_CHACHA20_POLY1305_SHA256:\
                        TLS_AES_128_GCM_SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:\
                        ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384:\
                        ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:\
                        DHE-RSA-CHACHA20-POLY1305:ECDHE-ECDSA-AES128-GCM-SHA256:\
                        ECDHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES128-GCM-SHA256:\
                        ECDHE-ECDSA-AES256-SHA384:ECDHE-RSA-AES256-SHA384:\
                        DHE-RSA-AES256-SHA256:ECDHE-ECDSA-AES128-SHA256:\
                        ECDHE-RSA-AES128-SHA256:DHE-RSA-AES128-SHA256:\
                        ECDHE-ECDSA-AES256-SHA:ECDHE-RSA-AES256-SHA",
            "ecdh_curve": "prime256v1",
        }
        ws_ssl1 = websocket.WebSocket(sslopt=ssloptions)
        ws_ssl1.connect("wss://api.bitfinex.com/ws/2")
        ws_ssl1.send("Hello")
        ws_ssl1.close()

        ws_ssl2 = websocket.WebSocket(sslopt={"check_hostname": True})
        ws_ssl2.connect("wss://api.bitfinex.com/ws/2")
        ws_ssl2.close()

    def test_proxy_info(self):
        self.assertEqual(
            proxy_info(
                http_proxy_host="127.0.0.1", http_proxy_port="8080", proxy_type="http"
            ).proxy_protocol,
            "http",
        )
        self.assertRaises(
            ProxyError,
            proxy_info,
            http_proxy_host="127.0.0.1",
            http_proxy_port="8080",
            proxy_type="badval",
        )
        self.assertEqual(
            proxy_info(
                http_proxy_host="example.com", http_proxy_port="8080", proxy_type="http"
            ).proxy_host,
            "example.com",
        )
        self.assertEqual(
            proxy_info(
                http_proxy_host="127.0.0.1", http_proxy_port="8080", proxy_type="http"
            ).proxy_port,
            "8080",
        )
        self.assertEqual(
            proxy_info(
                http_proxy_host="127.0.0.1", http_proxy_port="8080", proxy_type="http"
            ).auth,
            None,
        )
        self.assertEqual(
            proxy_info(
                http_proxy_host="127.0.0.1",
                http_proxy_port="8080",
                proxy_type="http",
                http_proxy_auth=("my_username123", "my_pass321"),
            ).auth[0],
            "my_username123",
        )
        self.assertEqual(
            proxy_info(
                http_proxy_host="127.0.0.1",
                http_proxy_port="8080",
                proxy_type="http",
                http_proxy_auth=("my_username123", "my_pass321"),
            ).auth[1],
            "my_pass321",
        )
        self.assertIsNone(proxy_info().proxy_timeout)


class HttpPureUnitTests(unittest.TestCase):
    def test_get_addrinfo_list_uses_proxy_host(self):
        proxy = proxy_info(
            http_proxy_host="proxy.example", http_proxy_port=8080, proxy_type="http"
        )

        with mock.patch(
            "websocket._http.socket.getaddrinfo", return_value=[("addr",)]
        ) as mocked_getaddrinfo:
            addrinfo, need_tunnel, auth = _get_addrinfo_list(
                "realhost.example", 443, True, proxy
            )

        self.assertTrue(need_tunnel)
        self.assertIsNone(auth)
        mocked_getaddrinfo.assert_called_once_with(
            "proxy.example", 8080, 0, socket.SOCK_STREAM, socket.SOL_TCP
        )
        self.assertEqual(addrinfo, [("addr",)])

    def test_get_addrinfo_list_wraps_gaierror(self):
        proxy = proxy_info()

        with mock.patch(
            "websocket._http.socket.getaddrinfo", side_effect=socket.gaierror("boom")
        ):
            with self.assertRaises(WebSocketAddressException):
                _get_addrinfo_list("example.com", 80, False, proxy)

    def test_wrap_sni_socket_raises_for_missing_ca_file(self):
        dummy_sock = mock.Mock()
        sslopt = {"cert_reqs": ssl.CERT_REQUIRED, "ca_certs": "/does/not/exist"}

        with mock.patch(
            "websocket._http.ssl.SSLContext.load_verify_locations",
            side_effect=FileNotFoundError("missing"),
        ):
            with self.assertRaises(WebSocketException) as ctx:
                _wrap_sni_socket(dummy_sock, sslopt, "example.com", True)

        self.assertIn("SSL CA certificate loading failed", str(ctx.exception))

    def test_start_proxied_socket_requires_python_socks(self):
        proxy = proxy_info(
            http_proxy_host="127.0.0.1", http_proxy_port=1080, proxy_type="socks5"
        )
        options = SimpleNamespace(sslopt={})

        with mock.patch("websocket._http.HAVE_PYTHON_SOCKS", False):
            with self.assertRaises(WebSocketException):
                _start_proxied_socket("wss://example.com", options, proxy)

    def test_tunnel_raises_for_non_200(self):
        fake_socket = object()

        with mock.patch("websocket._http.send") as send_mock, mock.patch(
            "websocket._http.read_headers", return_value=(403, {}, "Forbidden")
        ):
            with self.assertRaises(WebSocketProxyException):
                _tunnel(fake_socket, "example.com", 443, ("user", "pass"))

        send_mock.assert_called()


if __name__ == "__main__":
    unittest.main()
