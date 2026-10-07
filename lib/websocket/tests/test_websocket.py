# -*- coding: utf-8 -*-
#
import os
import os.path
import socket
import unittest
from base64 import decodebytes as base64decode
from unittest import mock

import websocket as ws
from websocket._abnf import ABNF
from websocket._exceptions import (
    WebSocketBadStatusException,
    WebSocketAddressException,
    WebSocketException,
)
from websocket._handshake import _create_sec_websocket_key
from websocket._handshake import _validate as _validate_header
from websocket._handshake import _get_handshake_headers
from websocket._handshake import handshake_response
from websocket._http import read_headers
from websocket._utils import validate_utf8

"""
test_websocket.py
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
    import ssl
except ImportError:
    # dummy class of SSLError for ssl none-support environment.
    class SSLError(Exception):
        pass


# Skip test to access the internet unless TEST_WITH_INTERNET == 1
TEST_WITH_INTERNET = os.environ.get("TEST_WITH_INTERNET", "0") == "1"
# Skip tests relying on local websockets server unless LOCAL_WS_SERVER_PORT != -1
LOCAL_WS_SERVER_PORT = os.environ.get("LOCAL_WS_SERVER_PORT", "-1")
TEST_WITH_LOCAL_SERVER = LOCAL_WS_SERVER_PORT != "-1"
TRACEABLE = True


def create_mask_key(_):
    return "abcd"


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


class WebSocketTest(unittest.TestCase):
    def setUp(self):
        ws.enableTrace(TRACEABLE)

    def tearDown(self):
        pass

    def test_default_timeout(self):
        self.assertEqual(ws.getdefaulttimeout(), None)
        ws.setdefaulttimeout(10)
        self.assertEqual(ws.getdefaulttimeout(), 10)
        ws.setdefaulttimeout(None)

    def test_ws_key(self):
        key = _create_sec_websocket_key()
        self.assertTrue(key != 24)
        self.assertTrue("¥n" not in key)

    def test_nonce(self):
        """WebSocket key should be a random 16-byte nonce."""
        key = _create_sec_websocket_key()
        nonce = base64decode(key.encode("utf-8"))
        self.assertEqual(16, len(nonce))

    def test_ws_utils(self):
        key = "c6b8hTg4EeGb2gQMztV1/g=="
        required_header = {
            "upgrade": "websocket",
            "connection": "upgrade",
            "sec-websocket-accept": "Kxep+hNu9n51529fGidYu7a3wO0=",
        }
        self.assertEqual(_validate_header(required_header, key, None), (True, None))

        header = required_header.copy()
        header["upgrade"] = "http"
        self.assertEqual(_validate_header(header, key, None), (False, None))
        del header["upgrade"]
        self.assertEqual(_validate_header(header, key, None), (False, None))

        header = required_header.copy()
        header["connection"] = "something"
        self.assertEqual(_validate_header(header, key, None), (False, None))
        del header["connection"]
        self.assertEqual(_validate_header(header, key, None), (False, None))

        header = required_header.copy()
        header["sec-websocket-accept"] = "something"
        self.assertEqual(_validate_header(header, key, None), (False, None))
        del header["sec-websocket-accept"]
        self.assertEqual(_validate_header(header, key, None), (False, None))

        header = required_header.copy()
        header["sec-websocket-protocol"] = "sub1"
        self.assertEqual(
            _validate_header(header, key, ["sub1", "sub2"]), (True, "sub1")
        )
        # This case will print out a logging error using the error() function, but that is expected
        self.assertEqual(_validate_header(header, key, ["sub2", "sub3"]), (False, None))

        header = required_header.copy()
        header["sec-websocket-protocol"] = "sUb1"
        self.assertEqual(
            _validate_header(header, key, ["Sub1", "suB2"]), (True, "sub1")
        )

        header = required_header.copy()
        # This case will print out a logging error using the error() function, but that is expected
        self.assertEqual(_validate_header(header, key, ["Sub1", "suB2"]), (False, None))

    def test_read_header(self):
        status, header, _ = read_headers(HeaderSockMock("data/header01.txt"))
        self.assertEqual(status, 101)
        self.assertEqual(header["connection"], "Upgrade")

        status, header, _ = read_headers(HeaderSockMock("data/header03.txt"))
        self.assertEqual(status, 101)
        self.assertEqual(header["connection"], "Upgrade, Keep-Alive")

        HeaderSockMock("data/header02.txt")
        self.assertRaises(
            ws.WebSocketException, read_headers, HeaderSockMock("data/header02.txt")
        )

    def test_send(self):
        # TODO: add longer frame data
        sock = ws.WebSocket()
        sock.set_mask_key(create_mask_key)
        s = sock.sock = HeaderSockMock("data/header01.txt")
        sock.send("Hello")
        self.assertEqual(s.sent[0], b"\x81\x85abcd)\x07\x0f\x08\x0e")

        sock.send("こんにちは")
        self.assertEqual(
            s.sent[1],
            b"\x81\x8fabcd\x82\xe3\xf0\x87\xe3\xf1\x80\xe5\xca\x81\xe2\xc5\x82\xe3\xcc",
        )

        #        sock.send("x" * 5000)
        #        self.assertEqual(s.sent[1], b'\x81\x8fabcd\x82\xe3\xf0\x87\xe3\xf1\x80\xe5\xca\x81\xe2\xc5\x82\xe3\xcc")

        self.assertEqual(sock.send_binary(b"1111111111101"), 19)

    def test_send_close_accepts_text_reason(self):
        sock = ws.WebSocket()
        captured = {}

        def fake_send(payload, opcode):
            captured["payload"] = payload
            captured["opcode"] = opcode
            return len(payload)

        sock.send = fake_send  # type: ignore[assignment]
        sock.connected = True

        sock.send_close(reason="normal close")

        self.assertEqual(captured["opcode"], ws.ABNF.OPCODE_CLOSE)
        self.assertIsInstance(captured["payload"], (bytes, bytearray))
        self.assertTrue(captured["payload"].endswith(b"normal close"))

    def test_close_accepts_text_reason(self):
        sock = ws.WebSocket()
        captured = {}

        def fake_send(payload, opcode):
            captured["payload"] = payload
            captured["opcode"] = opcode
            return len(payload)

        sock.send = fake_send  # type: ignore[assignment]
        sock.connected = True

        sock.close(reason="normal close")

        self.assertEqual(captured["opcode"], ws.ABNF.OPCODE_CLOSE)
        self.assertIsInstance(captured["payload"], (bytes, bytearray))
        self.assertTrue(captured["payload"].endswith(b"normal close"))

    def test_recv(self):
        # TODO: add longer frame data
        sock = ws.WebSocket()
        s = sock.sock = SockMock()
        something = (
            b"\x81\x8fabcd\x82\xe3\xf0\x87\xe3\xf1\x80\xe5\xca\x81\xe2\xc5\x82\xe3\xcc"
        )
        s.add_packet(something)
        data = sock.recv()
        self.assertEqual(data, "こんにちは")

        s.add_packet(b"\x81\x85abcd)\x07\x0f\x08\x0e")
        data = sock.recv()
        self.assertEqual(data, "Hello")

    @unittest.skipUnless(TEST_WITH_INTERNET, "Internet-requiring tests are disabled")
    def test_iter(self):
        count = 2
        s = ws.create_connection("wss://api.bitfinex.com/ws/2")
        try:
            s.send('{"event": "subscribe", "channel": "ticker"}')
            for _ in s:
                count -= 1
                if count == 0:
                    break
            self.assertEqual(
                count, 0, "WebSocket iterator failed to yield the expected frames"
            )
        finally:
            s.close()

    @unittest.skipUnless(TEST_WITH_INTERNET, "Internet-requiring tests are disabled")
    def test_next(self):
        sock = ws.create_connection("wss://api.bitfinex.com/ws/2")
        try:
            self.assertEqual(str, type(next(sock)))
        finally:
            sock.close()

    def test_internal_recv_strict(self):
        sock = ws.WebSocket()
        s = sock.sock = SockMock()
        s.add_packet(b"foo")
        s.add_packet(socket.timeout())
        s.add_packet(b"bar")
        # s.add_packet(SSLError("The read operation timed out"))
        s.add_packet(b"baz")
        with self.assertRaises(ws.WebSocketTimeoutException):
            sock.frame_buffer.recv_strict(9)
        #     with self.assertRaises(SSLError):
        #         data = sock._recv_strict(9)
        data = sock.frame_buffer.recv_strict(9)
        self.assertEqual(data, b"foobarbaz")
        with self.assertRaises(ws.WebSocketConnectionClosedException):
            sock.frame_buffer.recv_strict(1)

    def test_recv_timeout(self):
        sock = ws.WebSocket()
        s = sock.sock = SockMock()
        s.add_packet(b"\x81")
        s.add_packet(socket.timeout())
        s.add_packet(b"\x8dabcd\x29\x07\x0f\x08\x0e")
        s.add_packet(socket.timeout())
        s.add_packet(b"\x4e\x43\x33\x0e\x10\x0f\x00\x40")
        with self.assertRaises(ws.WebSocketTimeoutException):
            sock.recv()
        with self.assertRaises(ws.WebSocketTimeoutException):
            sock.recv()
        data = sock.recv()
        self.assertEqual(data, "Hello, World!")
        with self.assertRaises(ws.WebSocketConnectionClosedException):
            sock.recv()

    def test_recv_with_simple_fragmentation(self):
        sock = ws.WebSocket()
        s = sock.sock = SockMock()
        # OPCODE=TEXT, FIN=0, MSG="Brevity is "
        s.add_packet(b"\x01\x8babcd#\x10\x06\x12\x08\x16\x1aD\x08\x11C")
        # OPCODE=CONT, FIN=1, MSG="the soul of wit"
        s.add_packet(b"\x80\x8fabcd\x15\n\x06D\x12\r\x16\x08A\r\x05D\x16\x0b\x17")
        data = sock.recv()
        self.assertEqual(data, "Brevity is the soul of wit")
        with self.assertRaises(ws.WebSocketConnectionClosedException):
            sock.recv()

    def test_recv_with_fire_event_of_fragmentation(self):
        sock = ws.WebSocket(fire_cont_frame=True)
        s = sock.sock = SockMock()
        # OPCODE=TEXT, FIN=0, MSG="Brevity is "
        s.add_packet(b"\x01\x8babcd#\x10\x06\x12\x08\x16\x1aD\x08\x11C")
        # OPCODE=CONT, FIN=0, MSG="Brevity is "
        s.add_packet(b"\x00\x8babcd#\x10\x06\x12\x08\x16\x1aD\x08\x11C")
        # OPCODE=CONT, FIN=1, MSG="the soul of wit"
        s.add_packet(b"\x80\x8fabcd\x15\n\x06D\x12\r\x16\x08A\r\x05D\x16\x0b\x17")

        _, data = sock.recv_data()
        self.assertEqual(data, b"Brevity is ")
        _, data = sock.recv_data()
        self.assertEqual(data, b"Brevity is ")
        _, data = sock.recv_data()
        self.assertEqual(data, b"the soul of wit")

        # OPCODE=CONT, FIN=0, MSG="Brevity is "
        s.add_packet(b"\x80\x8babcd#\x10\x06\x12\x08\x16\x1aD\x08\x11C")

        with self.assertRaises(ws.WebSocketException):
            sock.recv_data()

        with self.assertRaises(ws.WebSocketConnectionClosedException):
            sock.recv()

    def test_close(self):
        sock = ws.WebSocket()
        sock.connected = True
        sock.close()

        sock = ws.WebSocket()
        s = sock.sock = SockMock()
        sock.connected = True
        s.add_packet(b"\x88\x80\x17\x98p\x84")
        sock.recv()
        self.assertEqual(sock.connected, False)

    def test_recv_cont_fragmentation(self):
        sock = ws.WebSocket()
        s = sock.sock = SockMock()
        # OPCODE=CONT, FIN=1, MSG="the soul of wit"
        s.add_packet(b"\x80\x8fabcd\x15\n\x06D\x12\r\x16\x08A\r\x05D\x16\x0b\x17")
        self.assertRaises(ws.WebSocketException, sock.recv)

    def test_recv_with_prolonged_fragmentation(self):
        sock = ws.WebSocket()
        s = sock.sock = SockMock()
        # OPCODE=TEXT, FIN=0, MSG="Once more unto the breach, "
        s.add_packet(
            b"\x01\x9babcd.\x0c\x00\x01A\x0f\x0c\x16\x04B\x16\n\x15\rC\x10\t\x07C\x06\x13\x07\x02\x07\tNC"
        )
        # OPCODE=CONT, FIN=0, MSG="dear friends, "
        s.add_packet(b"\x00\x8eabcd\x05\x07\x02\x16A\x04\x11\r\x04\x0c\x07\x17MB")
        # OPCODE=CONT, FIN=1, MSG="once more"
        s.add_packet(b"\x80\x89abcd\x0e\x0c\x00\x01A\x0f\x0c\x16\x04")
        data = sock.recv()
        self.assertEqual(data, "Once more unto the breach, dear friends, once more")
        with self.assertRaises(ws.WebSocketConnectionClosedException):
            sock.recv()

    def test_recv_with_fragmentation_and_control_frame(self):
        sock = ws.WebSocket()
        sock.set_mask_key(create_mask_key)
        s = sock.sock = SockMock()
        # OPCODE=TEXT, FIN=0, MSG="Too much "
        s.add_packet(b"\x01\x89abcd5\r\x0cD\x0c\x17\x00\x0cA")
        # OPCODE=PING, FIN=1, MSG="Please PONG this"
        s.add_packet(b"\x89\x90abcd1\x0e\x06\x05\x12\x07C4.,$D\x15\n\n\x17")
        # OPCODE=CONT, FIN=1, MSG="of a good thing"
        s.add_packet(b"\x80\x8fabcd\x0e\x04C\x05A\x05\x0c\x0b\x05B\x17\x0c\x08\x0c\x04")
        data = sock.recv()
        self.assertEqual(data, "Too much of a good thing")
        with self.assertRaises(ws.WebSocketConnectionClosedException):
            sock.recv()
        self.assertEqual(
            s.sent[0], b"\x8a\x90abcd1\x0e\x06\x05\x12\x07C4.,$D\x15\n\n\x17"
        )

    @unittest.skipUnless(
        TEST_WITH_LOCAL_SERVER, "Tests using local websocket server are disabled"
    )
    def test_websocket(self):
        s = ws.create_connection(f"ws://127.0.0.1:{LOCAL_WS_SERVER_PORT}")
        self.assertNotEqual(s, None)
        s.send("Hello, World")
        result = s.next()
        s.fileno()
        self.assertEqual(result, "Hello, World")

        s.send("こにゃにゃちは、世界")
        result = s.recv()
        self.assertEqual(result, "こにゃにゃちは、世界")
        self.assertRaises(ValueError, s.send_close, -1, "")
        s.close()

    @unittest.skipUnless(
        TEST_WITH_LOCAL_SERVER, "Tests using local websocket server are disabled"
    )
    def test_ping_pong(self):
        s = ws.create_connection(f"ws://127.0.0.1:{LOCAL_WS_SERVER_PORT}")
        self.assertNotEqual(s, None)
        s.ping("Hello")
        s.pong("Hi")
        s.close()

    @unittest.skipUnless(TEST_WITH_INTERNET, "Internet-requiring tests are disabled")
    def test_support_redirect(self):
        s = ws.WebSocket()
        self.assertRaises(WebSocketBadStatusException, s.connect, "ws://google.com/")
        # Need to find a URL that has a redirect code leading to a websocket

    @unittest.skipUnless(TEST_WITH_INTERNET, "Internet-requiring tests are disabled")
    def test_secure_websocket(self):
        s = ws.create_connection("wss://api.bitfinex.com/ws/2")
        self.assertNotEqual(s, None)
        self.assertTrue(isinstance(s.sock, ssl.SSLSocket))
        self.assertEqual(s.getstatus(), 101)
        self.assertNotEqual(s.getheaders(), None)
        s.settimeout(10)
        self.assertEqual(s.gettimeout(), 10)
        self.assertEqual(s.getsubprotocol(), None)
        s.abort()

    @unittest.skipUnless(
        TEST_WITH_LOCAL_SERVER, "Tests using local websocket server are disabled"
    )
    def test_websocket_with_custom_header(self):
        s = ws.create_connection(
            f"ws://127.0.0.1:{LOCAL_WS_SERVER_PORT}",
            header={"User-Agent": "PythonWebsocketClient"},
        )
        self.assertNotEqual(s, None)
        self.assertEqual(s.getsubprotocol(), None)
        s.send("Hello, World")
        result = s.recv()
        self.assertEqual(result, "Hello, World")
        self.assertRaises(ValueError, s.close, -1, "")
        s.close()

    @unittest.skipUnless(
        TEST_WITH_LOCAL_SERVER, "Tests using local websocket server are disabled"
    )
    def test_after_close(self):
        s = ws.create_connection(f"ws://127.0.0.1:{LOCAL_WS_SERVER_PORT}")
        self.assertNotEqual(s, None)
        s.close()
        self.assertRaises(ws.WebSocketConnectionClosedException, s.send, "Hello")
        self.assertRaises(ws.WebSocketConnectionClosedException, s.recv)


class SockOptTest(unittest.TestCase):
    @unittest.skipUnless(
        TEST_WITH_LOCAL_SERVER, "Tests using local websocket server are disabled"
    )
    def test_sockopt(self):
        sockopt = ((socket.IPPROTO_TCP, socket.TCP_NODELAY, 1),)
        s = ws.create_connection(
            f"ws://127.0.0.1:{LOCAL_WS_SERVER_PORT}", sockopt=sockopt
        )
        self.assertNotEqual(
            s.sock.getsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY), 0
        )
        s.close()


class UtilsTest(unittest.TestCase):
    def test_utf8_validator(self):
        state = validate_utf8(b"\xf0\x90\x80\x80")
        self.assertEqual(state, True)
        state = validate_utf8(
            b"\xce\xba\xe1\xbd\xb9\xcf\x83\xce\xbc\xce\xb5\xed\xa0\x80edited"
        )
        self.assertEqual(state, False)
        state = validate_utf8(b"")
        self.assertEqual(state, True)
        state = validate_utf8("κόσμε")
        self.assertEqual(state, True)
        state = validate_utf8("a\ud800b")
        self.assertEqual(state, False)
        state = validate_utf8("")
        self.assertEqual(state, True)


class HandshakeTest(unittest.TestCase):
    def test_bad_status_exception_carries_status_message(self):
        exc = WebSocketBadStatusException(
            "Handshake status 404 Not Found", 404, "Not Found"
        )
        self.assertEqual(exc.status_code, 404)
        self.assertEqual(exc.status_message, "Not Found")
        self.assertIsNone(exc.resp_headers)
        self.assertIsNone(exc.resp_body)

    @unittest.skipUnless(TEST_WITH_INTERNET, "Internet-requiring tests are disabled")
    def test_http_ssl(self):
        websock1 = ws.WebSocket(
            sslopt={"cert_chain": ssl.get_default_verify_paths().capath},
            enable_multithread=False,
        )
        self.assertRaises(ValueError, websock1.connect, "wss://api.bitfinex.com/ws/2")
        websock2 = ws.WebSocket(sslopt={"certfile": "myNonexistentCertFile"})
        self.assertRaises(
            WebSocketException, websock2.connect, "wss://api.bitfinex.com/ws/2"
        )

    @unittest.skipUnless(TEST_WITH_INTERNET, "Internet-requiring tests are disabled")
    def test_manual_headers(self):
        websock3 = ws.WebSocket(
            sslopt={
                "ca_certs": ssl.get_default_verify_paths().cafile,
                "ca_cert_path": ssl.get_default_verify_paths().capath,
            }
        )
        self.assertRaises(
            WebSocketBadStatusException,
            websock3.connect,
            "wss://api.bitfinex.com/ws/2",
            cookie="chocolate",
            origin="testing_websockets.com",
            host="echo.websocket.events/websocket-client-test",
            subprotocols=["testproto"],
            connection="Upgrade",
            header={
                "CustomHeader1": "123",
                "Cookie": "TestValue",
                "Sec-WebSocket-Key": "k9kFAUWNAMmf5OEMfTlOEA==",
                "Sec-WebSocket-Protocol": "newprotocol",
            },
        )

    def test_ipv6(self):
        websock2 = ws.WebSocket()
        self.assertRaises(ValueError, websock2.connect, "2001:4860:4860::8888")

    def test_bad_urls(self):
        websock3 = ws.WebSocket()
        self.assertRaises(ValueError, websock3.connect, "ws//example.com")
        self.assertRaises(WebSocketAddressException, websock3.connect, "ws://example")
        self.assertRaises(ValueError, websock3.connect, "example.com")

    def test_suppress_host_header(self):
        """Test suppress_host parameter in _get_handshake_headers function"""
        # Test normal behavior (Host header included)
        headers, key = _get_handshake_headers(
            "/path", "ws://example.com:8080", "example.com", 8080, {}
        )
        host_headers = [h for h in headers if h.startswith("Host:")]
        self.assertEqual(len(host_headers), 1)
        self.assertEqual(host_headers[0], "Host: example.com:8080")

        # Test suppress_host=False (explicit, should still include Host header)
        headers, key = _get_handshake_headers(
            "/path",
            "ws://example.com:8080",
            "example.com",
            8080,
            {"suppress_host": False},
        )
        host_headers = [h for h in headers if h.startswith("Host:")]
        self.assertEqual(len(host_headers), 1)
        self.assertEqual(host_headers[0], "Host: example.com:8080")

        # Test suppress_host=True (Host header should be suppressed)
        headers, key = _get_handshake_headers(
            "/path",
            "ws://example.com:8080",
            "example.com",
            8080,
            {"suppress_host": True},
        )
        host_headers = [h for h in headers if h.startswith("Host:")]
        self.assertEqual(len(host_headers), 0)

        # Test with custom host header and suppress_host=False
        headers, key = _get_handshake_headers(
            "/path",
            "ws://example.com:8080",
            "example.com",
            8080,
            {"host": "custom-host.example.com", "suppress_host": False},
        )
        host_headers = [h for h in headers if h.startswith("Host:")]
        self.assertEqual(len(host_headers), 1)
        self.assertEqual(host_headers[0], "Host: custom-host.example.com")

        # Test with custom host header and suppress_host=True (should suppress even custom host)
        headers, key = _get_handshake_headers(
            "/path",
            "ws://example.com:8080",
            "example.com",
            8080,
            {"host": "custom-host.example.com", "suppress_host": True},
        )
        host_headers = [h for h in headers if h.startswith("Host:")]
        self.assertEqual(len(host_headers), 0)

        # Test with standard ports (80, 443) - should not include port in host
        headers, key = _get_handshake_headers(
            "/path", "ws://example.com", "example.com", 80, {}
        )
        host_headers = [h for h in headers if h.startswith("Host:")]
        self.assertEqual(len(host_headers), 1)
        self.assertEqual(host_headers[0], "Host: example.com")

        # Test suppress_host=True with standard port
        headers, key = _get_handshake_headers(
            "/path", "ws://example.com", "example.com", 80, {"suppress_host": True}
        )
        host_headers = [h for h in headers if h.startswith("Host:")]
        self.assertEqual(len(host_headers), 0)

    def test_suppress_host_websocket_connect(self):
        """Test suppress_host parameter with WebSocket.connect()"""
        websock = ws.WebSocket()

        # Test that suppress_host parameter is accepted without error
        # (Connection will fail but parameter should be accepted)
        try:
            websock.connect(
                "ws://nonexistent.example.com", suppress_host=True, timeout=0.1
            )
        except (WebSocketAddressException, OSError, socket.timeout):
            # Expected - connection should fail, but parameter was accepted
            pass

        # Test that suppress_host=False also works
        try:
            websock.connect(
                "ws://nonexistent.example.com", suppress_host=False, timeout=0.1
            )
        except (WebSocketAddressException, OSError, socket.timeout):
            # Expected - connection should fail, but parameter was accepted
            pass


class WebSocketCoreUnitTests(unittest.TestCase):
    def test_iteration_helpers_and_next_aliases(self):
        class TestError(Exception):
            pass

        sock = ws.WebSocket()
        sock.recv = mock.Mock(side_effect=["first", TestError("stop")])

        iterator = iter(sock)
        self.assertEqual(next(iterator), "first")
        with self.assertRaises(TestError):
            next(iterator)

        sock.recv = mock.Mock(return_value="again")
        self.assertEqual(sock.__next__(), "again")
        self.assertEqual(sock.next(), "again")

    def test_fileno_requires_socket(self):
        sock = ws.WebSocket()
        with self.assertRaises(WebSocketException):
            sock.fileno()

        fake_socket = mock.Mock()
        fake_socket.fileno.return_value = 42
        sock.sock = fake_socket
        self.assertEqual(sock.fileno(), 42)

    def test_settimeout_updates_underlying_socket(self):
        sock = ws.WebSocket()
        fake_socket = mock.Mock()
        sock.sock = fake_socket

        sock.settimeout(5)
        self.assertEqual(sock.gettimeout(), 5)
        fake_socket.settimeout.assert_called_once_with(5)

    def test_is_ssl_detection(self):
        sock = ws.WebSocket()
        self.assertFalse(sock.is_ssl())

        class FakeSSLSocket:
            pass

        with mock.patch("websocket._core.ssl.SSLSocket", FakeSSLSocket):
            sock.sock = FakeSSLSocket()
            self.assertTrue(sock.is_ssl())

    def test_send_frame_emits_trace_when_enabled(self):
        sock = ws.WebSocket()
        sock._send = mock.Mock(side_effect=lambda data: len(data))
        sock.lock = mock.MagicMock()

        frame = ABNF.create_frame("hi", ABNF.OPCODE_TEXT)

        with mock.patch(
            "websocket._core.isEnabledForTrace", return_value=True
        ), mock.patch("websocket._core.trace") as trace_mock:
            length = sock.send_frame(frame)

        self.assertGreater(length, 0)
        self.assertEqual(trace_mock.call_count, 2)

    def test_connect_handles_redirects(self):
        sock = ws.WebSocket()
        first_socket = mock.Mock()
        second_socket = mock.Mock()
        connect_results = [
            (first_socket, ("origin", 80, "/")),
            (second_socket, ("redirect", 80, "/")),
        ]

        def fake_connect(url, *_):
            return connect_results.pop(0)

        redirect_resp = handshake_response(301, {"location": "ws://redirect"}, None)
        success_resp = handshake_response(101, {}, None)

        with mock.patch(
            "websocket._core.connect", side_effect=fake_connect
        ) as connect_mock, mock.patch(
            "websocket._core.handshake", side_effect=[redirect_resp, success_resp]
        ) as handshake_mock:
            sock.connect("ws://origin", redirect_limit=1)

        self.assertTrue(sock.connected)
        self.assertIs(sock.sock, second_socket)
        first_socket.close.assert_called_once()
        self.assertEqual(
            [call.args[0] for call in connect_mock.call_args_list],
            ["ws://origin", "ws://redirect"],
        )
        self.assertEqual(handshake_mock.call_count, 2)

    def test_connect_redirect_limit_exhausted_raises(self):
        sock = ws.WebSocket()
        sockets = []
        redirect_resp = handshake_response(302, {"location": "ws://redirect"}, None)

        def fake_connect(url, *args, **kwargs):
            socket_mock = mock.Mock()
            sockets.append(socket_mock)
            return socket_mock, ("redirect", 80, "/")

        with mock.patch(
            "websocket._core.connect", side_effect=fake_connect
        ) as connect_mock, mock.patch(
            "websocket._core.handshake", return_value=redirect_resp
        ):
            with self.assertRaisesRegex(
                ws.WebSocketException, "Redirect limit exhausted"
            ):
                sock.connect("ws://origin", redirect_limit=2)

        self.assertEqual(connect_mock.call_count, 3)
        self.assertFalse(sock.connected)
        self.assertIsNone(sock.sock)
        for socket_mock in sockets:
            socket_mock.close.assert_called_once()

    def test_connect_redirect_invalid_target_raises(self):
        sock = ws.WebSocket()
        redirect_resp = handshake_response(302, {"location": "https://redirect"}, None)

        def fake_connect(url, *args, **kwargs):
            if url == "https://redirect":
                raise ValueError("scheme https is invalid")
            return mock.Mock(), ("origin", 80, "/")

        with mock.patch(
            "websocket._core.connect", side_effect=fake_connect
        ), mock.patch("websocket._core.handshake", return_value=redirect_resp):
            with self.assertRaisesRegex(
                ws.WebSocketException, "Invalid redirect target 'https://redirect'"
            ):
                sock.connect("ws://origin", redirect_limit=2)

        self.assertFalse(sock.connected)
        self.assertIsNone(sock.sock)

    def test_connect_redirect_without_location_raises(self):
        sock = ws.WebSocket()
        redirect_resp = handshake_response(302, {}, None)  # no location header

        def fake_connect(url, *args, **kwargs):
            return mock.Mock(), ("origin", 80, "/")

        with mock.patch(
            "websocket._core.connect", side_effect=fake_connect
        ), mock.patch("websocket._core.handshake", return_value=redirect_resp):
            with self.assertRaisesRegex(ws.WebSocketException, "Location"):
                sock.connect("ws://origin", redirect_limit=2)

        self.assertFalse(sock.connected)
        self.assertIsNone(sock.sock)

    def test_shutdown_and_abort(self):
        sock = ws.WebSocket()
        socket_mock = mock.Mock()
        socket_mock._closed = False
        sock.sock = socket_mock
        sock.connected = True

        sock.shutdown()
        socket_mock.close.assert_called_once()
        self.assertIsNone(sock.sock)
        self.assertFalse(sock.connected)

        socket_mock = mock.Mock()
        sock.sock = socket_mock
        sock.connected = True
        sock.abort()
        socket_mock.shutdown.assert_called_once_with(socket.SHUT_RDWR)

    def test_abort_tolerates_dead_socket(self):
        sock = ws.WebSocket()
        # never-connected socket: shutdown() raises ENOTCONN
        # which abort() must not leak to the caller
        real = socket.socket()
        sock.sock = real
        sock.connected = True

        sock.abort()  # must not raise
        real.close()

    def test_create_connection_uses_custom_class(self):
        class DummySocket:
            def __init__(self, **kwargs):
                self.init_kwargs = kwargs
                self.timeout_value = None
                self.url = None
                self.options = None

            def settimeout(self, value):
                self.timeout_value = value

            def connect(self, url, **options):
                self.url = url
                self.options = options

        conn = ws.create_connection(
            "ws://example.com",
            timeout=5,
            class_=DummySocket,
            header={"User-Agent": "tester"},
            origin="https://origin",
        )

        self.assertIsInstance(conn, DummySocket)
        self.assertEqual(conn.url, "ws://example.com")
        self.assertEqual(conn.timeout_value, 5)
        self.assertIn("header", conn.options)
        self.assertEqual(conn.options["origin"], "https://origin")


if __name__ == "__main__":
    unittest.main()
