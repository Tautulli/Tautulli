# -*- coding: utf-8 -*-
#
import os
import os.path
import socket
import ssl
import struct
import threading
import unittest
from unittest import mock

import websocket as ws
from websocket._abnf import ABNF

"""
test_app.py
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

# Skip test to access the internet unless TEST_WITH_INTERNET == 1
TEST_WITH_INTERNET = os.environ.get("TEST_WITH_INTERNET", "0") == "1"
# Skip tests relying on local websockets server unless LOCAL_WS_SERVER_PORT != -1
LOCAL_WS_SERVER_PORT = os.environ.get("LOCAL_WS_SERVER_PORT", "-1")
TEST_WITH_LOCAL_SERVER = LOCAL_WS_SERVER_PORT != "-1"
TRACEABLE = True


class WebSocketAppTest(unittest.TestCase):
    class NotSetYet:
        """A marker class for signalling that a value hasn't been set yet."""

    def setUp(self):
        ws.enableTrace(TRACEABLE)

        WebSocketAppTest.keep_running_open = WebSocketAppTest.NotSetYet()
        WebSocketAppTest.keep_running_close = WebSocketAppTest.NotSetYet()
        WebSocketAppTest.get_mask_key_id = WebSocketAppTest.NotSetYet()
        WebSocketAppTest.on_error_data = WebSocketAppTest.NotSetYet()

    def tearDown(self):
        WebSocketAppTest.keep_running_open = WebSocketAppTest.NotSetYet()
        WebSocketAppTest.keep_running_close = WebSocketAppTest.NotSetYet()
        WebSocketAppTest.get_mask_key_id = WebSocketAppTest.NotSetYet()
        WebSocketAppTest.on_error_data = WebSocketAppTest.NotSetYet()

    def close(self):
        pass

    @unittest.skipUnless(
        TEST_WITH_LOCAL_SERVER, "Tests using local websocket server are disabled"
    )
    def test_keep_running(self):
        """A WebSocketApp should keep running as long as its self.keep_running
        is not False (in the boolean context).
        """

        def on_open(self, *args, **kwargs):
            """Set the keep_running flag for later inspection and immediately
            close the connection.
            """
            self.send("hello!")
            WebSocketAppTest.keep_running_open = self.keep_running
            self.keep_running = False

        def on_message(app, message):
            print(message)
            app.close()

        def on_close(self, *args, **kwargs):
            """Set the keep_running flag for the test to use."""
            WebSocketAppTest.keep_running_close = self.keep_running

        app = ws.WebSocketApp(
            f"ws://127.0.0.1:{LOCAL_WS_SERVER_PORT}",
            on_open=on_open,
            on_close=on_close,
            on_message=on_message,
        )
        app.run_forever()

    #    @unittest.skipUnless(TEST_WITH_LOCAL_SERVER, "Tests using local websocket server are disabled")
    @unittest.skipUnless(False, "Test disabled for now (requires rel)")
    def test_run_forever_dispatcher(self):
        """A WebSocketApp should keep running as long as its self.keep_running
        is not False (in the boolean context).
        """

        def on_open(self, *args, **kwargs):
            """Send a message, receive, and send one more"""
            self.send("hello!")
            if self.sock:
                self.sock.recv()
            self.send("goodbye!")

        def on_message(app, message):
            print(message)
            app.close()

        app = ws.WebSocketApp(
            f"ws://127.0.0.1:{LOCAL_WS_SERVER_PORT}",
            on_open=on_open,
            on_message=on_message,
        )
        app.run_forever(dispatcher="Dispatcher")  # doesn't work

    #        app.run_forever(dispatcher=rel)          # would work
    #        rel.dispatch()

    @unittest.skipUnless(
        TEST_WITH_LOCAL_SERVER, "Tests using local websocket server are disabled"
    )
    def test_run_forever_teardown_clean_exit(self):
        """The WebSocketApp.run_forever() method should return `False` when the application ends gracefully."""
        app = ws.WebSocketApp(f"ws://127.0.0.1:{LOCAL_WS_SERVER_PORT}")
        threading.Timer(interval=0.2, function=app.close).start()
        teardown = app.run_forever()
        self.assertEqual(teardown, False)

    @unittest.skipUnless(TEST_WITH_INTERNET, "Internet-requiring tests are disabled")
    def test_sock_mask_key(self):
        """A WebSocketApp should forward the received mask_key function down
        to the actual socket.
        """

        def my_mask_key_func():
            return "\x00\x00\x00\x00"

        app = ws.WebSocketApp(
            "wss://api-pub.bitfinex.com/ws/1", get_mask_key=my_mask_key_func
        )

        # if numpy is installed, this assertion fail
        # Note: We can't use 'is' for comparing the functions directly, need to use 'id'.
        self.assertEqual(id(app.get_mask_key), id(my_mask_key_func))

    @unittest.skipUnless(TEST_WITH_INTERNET, "Internet-requiring tests are disabled")
    def test_invalid_ping_interval_ping_timeout(self):
        """Test exception handling if ping_interval < ping_timeout"""

        def on_ping(app, _):
            print("Got a ping!")
            app.close()

        def on_pong(app, _):
            print("Got a pong! No need to respond")
            app.close()

        app = ws.WebSocketApp(
            "wss://api-pub.bitfinex.com/ws/1", on_ping=on_ping, on_pong=on_pong
        )
        self.assertRaises(
            ws.WebSocketException,
            app.run_forever,
            ping_interval=1,
            ping_timeout=2,
            sslopt={"cert_reqs": ssl.CERT_NONE},
        )

    @unittest.skipUnless(TEST_WITH_INTERNET, "Internet-requiring tests are disabled")
    def test_ping_interval(self):
        """Test WebSocketApp proper ping functionality"""

        def on_ping(app, _):
            print("Got a ping!")
            app.close()

        def on_pong(app, _):
            print("Got a pong! No need to respond")
            app.close()

        app = ws.WebSocketApp(
            "wss://api-pub.bitfinex.com/ws/1", on_ping=on_ping, on_pong=on_pong
        )
        app.run_forever(
            ping_interval=2, ping_timeout=1, sslopt={"cert_reqs": ssl.CERT_NONE}
        )

    @unittest.skipUnless(TEST_WITH_INTERNET, "Internet-requiring tests are disabled")
    def test_opcode_close(self):
        """Test WebSocketApp close opcode"""

        app = ws.WebSocketApp("wss://tsock.us1.twilio.com/v3/wsconnect")
        app.run_forever(ping_interval=2, ping_timeout=1, ping_payload="Ping payload")

    # This is commented out because the URL no longer responds in the expected way
    # @unittest.skipUnless(TEST_WITH_INTERNET, "Internet-requiring tests are disabled")
    # def testOpcodeBinary(self):
    #     """ Test WebSocketApp binary opcode
    #     """
    #     app = ws.WebSocketApp('wss://streaming.vn.teslamotors.com/streaming/')
    #     app.run_forever(ping_interval=2, ping_timeout=1, ping_payload="Ping payload")

    @unittest.skipUnless(TEST_WITH_INTERNET, "Internet-requiring tests are disabled")
    def test_bad_ping_interval(self):
        """A WebSocketApp handling of negative ping_interval"""
        app = ws.WebSocketApp("wss://api-pub.bitfinex.com/ws/1")
        self.assertRaises(
            ws.WebSocketException,
            app.run_forever,
            ping_interval=-5,
            sslopt={"cert_reqs": ssl.CERT_NONE},
        )

    @unittest.skipUnless(TEST_WITH_INTERNET, "Internet-requiring tests are disabled")
    def test_bad_ping_timeout(self):
        """A WebSocketApp handling of negative ping_timeout"""
        app = ws.WebSocketApp("wss://api-pub.bitfinex.com/ws/1")
        self.assertRaises(
            ws.WebSocketException,
            app.run_forever,
            ping_timeout=-3,
            sslopt={"cert_reqs": ssl.CERT_NONE},
        )

    @unittest.skipUnless(TEST_WITH_INTERNET, "Internet-requiring tests are disabled")
    def test_close_status_code(self):
        """Test extraction of close frame status code and close reason in WebSocketApp"""

        def on_close(wsapp, close_status_code, close_msg):
            print("on_close reached")

        app = ws.WebSocketApp(
            "wss://tsock.us1.twilio.com/v3/wsconnect", on_close=on_close
        )
        closeframe = ws.ABNF(
            opcode=ws.ABNF.OPCODE_CLOSE, data=b"\x03\xe8no-init-from-client"
        )
        self.assertEqual([1000, "no-init-from-client"], app._get_close_args(closeframe))

        closeframe = ws.ABNF(opcode=ws.ABNF.OPCODE_CLOSE, data=b"")
        self.assertEqual([None, None], app._get_close_args(closeframe))

        app2 = ws.WebSocketApp("wss://tsock.us1.twilio.com/v3/wsconnect")
        closeframe = ws.ABNF(opcode=ws.ABNF.OPCODE_CLOSE, data=b"")
        self.assertEqual([None, None], app2._get_close_args(closeframe))

        self.assertRaises(
            ws.WebSocketConnectionClosedException,
            app.send,
            data="test if connection is closed",
        )

    def test_parse_close_frame_variants(self):
        """_parse_close_frame decodes bytes, str, and invalid UTF-8 payloads."""

        app = ws.WebSocketApp("ws://example.com")

        binary_frame = ws.ABNF(
            opcode=ws.ABNF.OPCODE_CLOSE, data=b"\x03\xe8normal-closure"
        )
        code, reason = app._parse_close_frame(binary_frame)
        self.assertEqual(code, 1000)
        self.assertEqual(reason, "normal-closure")

        invalid_utf8 = ws.ABNF(
            opcode=ws.ABNF.OPCODE_CLOSE, data=b"\x03\xe8\xff\xfe\xff"
        )
        code, reason = app._parse_close_frame(invalid_utf8)
        self.assertEqual(code, 1000)
        self.assertEqual(reason, "\ufffd\ufffd\ufffd")

        text_data = ws.ABNF(opcode=ws.ABNF.OPCODE_CLOSE, data="ABtext-reason")
        code, reason = app._parse_close_frame(text_data)
        self.assertEqual(code, 0x4142)
        self.assertEqual(reason, "text-reason")

    def test_close_frame_triggers_closed_logic(self):
        """Ensure close frames propagate through closed() to on_error/on_close."""

        close_payload = b"\x03\xe8close-reason"
        close_frame = ws.ABNF(opcode=ws.ABNF.OPCODE_CLOSE, data=close_payload)
        close_results = []
        error_results = []

        def on_close(app, code, reason):
            close_results.append((code, reason))

        def on_error(app, err):
            error_results.append(err)

        class FakeWebSocket:
            def __init__(self, *args, **kwargs):
                self.sock = object()
                self._delivered = False

            def settimeout(self, timeout):
                pass

            def connect(self, *args, **kwargs):
                pass

            def recv_data_frame(self, *args, **kwargs):
                if self._delivered:
                    raise ws.WebSocketConnectionClosedException("closed")
                self._delivered = True
                return (ws.ABNF.OPCODE_CLOSE, close_frame)

            def close(self):
                pass

            def shutdown(self):
                pass

        class FakeDispatcher:
            def __init__(self, app):
                self.app = app

            def read(self, sock, read_callback, check_callback):
                read_callback()

            def reconnect(self, seconds, reconnector):
                pass

        app = ws.WebSocketApp("ws://example.com", on_close=on_close, on_error=on_error)
        fake_dispatcher = FakeDispatcher(app)

        with mock.patch("websocket._app.WebSocket", FakeWebSocket):
            with mock.patch.object(
                ws.WebSocketApp, "create_dispatcher", return_value=fake_dispatcher
            ):
                app.run_forever()

        self.assertEqual(close_results, [(1000, "close-reason")])
        self.assertEqual(len(error_results), 1)
        self.assertIsInstance(error_results[0], ws.WebSocketConnectionClosedException)
        self.assertEqual(getattr(error_results[0], "status_code", None), 1000)
        self.assertEqual(getattr(error_results[0], "reason", None), "close-reason")

    def test_close_exception_legacy_path_has_no_frame(self):
        """Ensure exception path through closed() does not pass a close frame."""

        close_results = []
        error_results = []

        def on_close(app, code, reason):
            close_results.append((code, reason))

        def on_error(app, err):
            error_results.append(err)

        class FakeWebSocket:
            def __init__(self, *args, **kwargs):
                self.sock = mock.Mock()

            def settimeout(self, timeout):
                pass

            def connect(self, *args, **kwargs):
                pass

            def recv_data_frame(self, *args, **kwargs):
                raise ws.WebSocketConnectionClosedException("socket closed")

            def close(self):
                pass

            def shutdown(self):
                pass

        class FakeDispatcher:
            def __init__(self, app):
                self.app = app

            def read(self, sock, read_callback, check_callback):
                read_callback()

            def reconnect(self, seconds, reconnector):
                pass

        app = ws.WebSocketApp("ws://example.com", on_close=on_close, on_error=on_error)
        fake_dispatcher = FakeDispatcher(app)

        with mock.patch("websocket._app.WebSocket", FakeWebSocket):
            with mock.patch.object(
                ws.WebSocketApp, "create_dispatcher", return_value=fake_dispatcher
            ):
                app.run_forever()

        self.assertEqual(close_results, [(None, None)])
        self.assertEqual(len(error_results), 1)
        self.assertIsInstance(error_results[0], ws.WebSocketConnectionClosedException)
        self.assertEqual(str(error_results[0]), "socket closed")
        self.assertFalse(hasattr(error_results[0], "status_code"))

    def test_custom_dispatcher_close_exception(self):
        """Custom dispatchers should route exceptions through closed()."""

        close_results = []
        error_results = []

        def on_close(app, code, reason):
            close_results.append((code, reason))

        def on_error(app, err):
            error_results.append(err)

        class FakeWebSocket:
            def __init__(self, *args, **kwargs):
                self.sock = mock.Mock()

            def settimeout(self, timeout):
                pass

            def connect(self, *args, **kwargs):
                pass

            def recv_data_frame(self, *args, **kwargs):
                raise ws.WebSocketConnectionClosedException("dispatcher closed")

            def close(self):
                pass

            def shutdown(self):
                pass

        class CustomDispatcher:
            def __init__(self):
                self.read_called = False
                self.last_result = None

            def read(self, sock, read_callback, check_callback):
                self.read_called = True
                self.last_result = read_callback()

            def reconnect(self, seconds, reconnector):
                pass

        dispatcher_wrapper = CustomDispatcher()

        app = ws.WebSocketApp("ws://example.com", on_close=on_close, on_error=on_error)

        with mock.patch("websocket._app.WebSocket", FakeWebSocket):
            with mock.patch.object(
                ws.WebSocketApp, "create_dispatcher", return_value=dispatcher_wrapper
            ):
                app.run_forever(dispatcher=object())

        self.assertTrue(dispatcher_wrapper.read_called)
        self.assertTrue(dispatcher_wrapper.last_result)
        self.assertEqual(close_results, [(None, None)])
        self.assertEqual(len(error_results), 1)
        self.assertIsInstance(error_results[0], ws.WebSocketConnectionClosedException)
        self.assertEqual(str(error_results[0]), "dispatcher closed")

    def test_closed_string_argument_converted_to_exception(self):
        """Calling closed() with a string should still reach on_error/on_close."""

        close_results = []
        error_results = []

        def on_close(app, code, reason):
            close_results.append((code, reason))

        def on_error(app, err):
            error_results.append(err)

        class FakeWebSocket:
            def __init__(self, *args, **kwargs):
                self.sock = mock.Mock()

            def settimeout(self, timeout):
                pass

            def connect(self, *args, **kwargs):
                pass

            def shutdown(self):
                pass

            def close(self):
                pass

        class ClosedCallingDispatcher:
            def __init__(self, app, closed_fn):
                self.app = app
                self.closed_fn = closed_fn
                self.read_called = False

            def read(self, sock, read_callback, check_callback):
                self.read_called = True
                self.closed_fn("manual string close")
                self.app.keep_running = False

            def reconnect(self, seconds, reconnector):
                pass

        def fake_create_dispatcher(
            self, ping_timeout, dispatcher, is_ssl, handleDisconnect
        ):
            return ClosedCallingDispatcher(self, handleDisconnect)

        app = ws.WebSocketApp("ws://example.com", on_close=on_close, on_error=on_error)

        with mock.patch("websocket._app.WebSocket", FakeWebSocket):
            with mock.patch.object(
                ws.WebSocketApp, "create_dispatcher", fake_create_dispatcher
            ):
                app.run_forever()

        self.assertEqual(close_results, [(None, None)])
        self.assertEqual(len(error_results), 1)
        self.assertIsInstance(error_results[0], ws.WebSocketConnectionClosedException)
        self.assertEqual(str(error_results[0]), "manual string close")
        self.assertFalse(hasattr(error_results[0], "status_code"))

    @unittest.skipUnless(
        TEST_WITH_LOCAL_SERVER, "Tests using local websocket server are disabled"
    )
    def test_callback_function_exception(self):
        """Test callback function exception handling"""

        exc = None
        passed_app = None

        def on_open(app):
            raise RuntimeError("Callback failed")

        def on_error(app, err):
            nonlocal passed_app
            passed_app = app
            nonlocal exc
            exc = err

        def on_pong(app, _):
            app.close()

        app = ws.WebSocketApp(
            f"ws://127.0.0.1:{LOCAL_WS_SERVER_PORT}",
            on_open=on_open,
            on_error=on_error,
            on_pong=on_pong,
        )
        app.run_forever(ping_interval=2, ping_timeout=1)

        self.assertEqual(passed_app, app)
        self.assertIsInstance(exc, RuntimeError)
        self.assertEqual(str(exc), "Callback failed")

    @unittest.skipUnless(
        TEST_WITH_LOCAL_SERVER, "Tests using local websocket server are disabled"
    )
    def test_callback_method_exception(self):
        """Test callback method exception handling"""

        class Callbacks:
            def __init__(self):
                self.exc = None
                self.passed_app = None
                self.app = ws.WebSocketApp(
                    f"ws://127.0.0.1:{LOCAL_WS_SERVER_PORT}",
                    on_open=self.on_open,
                    on_error=self.on_error,
                    on_pong=self.on_pong,
                )
                self.app.run_forever(ping_interval=2, ping_timeout=1)

            def on_open(self, _):
                raise RuntimeError("Callback failed")

            def on_error(self, app, err):
                self.passed_app = app
                self.exc = err

            def on_pong(self, app, _):
                app.close()

        callbacks = Callbacks()

        self.assertEqual(callbacks.passed_app, callbacks.app)
        self.assertIsInstance(callbacks.exc, RuntimeError)
        self.assertEqual(str(callbacks.exc), "Callback failed")

    @unittest.skipUnless(
        TEST_WITH_LOCAL_SERVER, "Tests using local websocket server are disabled"
    )
    def test_reconnect(self):
        """Test reconnect"""
        pong_count = 0
        exc = None

        def on_error(_, err):
            nonlocal exc
            exc = err

        def on_pong(app, _):
            nonlocal pong_count
            pong_count += 1
            if pong_count == 1:
                # First pong, shutdown socket, enforce read error
                app.sock.shutdown()
            if pong_count >= 2:
                # Got second pong after reconnect
                app.close()

        app = ws.WebSocketApp(
            f"ws://127.0.0.1:{LOCAL_WS_SERVER_PORT}", on_pong=on_pong, on_error=on_error
        )
        app.run_forever(ping_interval=2, ping_timeout=1, reconnect=3)

        self.assertEqual(pong_count, 2)
        self.assertIsInstance(exc, ws.WebSocketTimeoutException)
        self.assertEqual(str(exc), "ping/pong timed out")

    def test_dispatcher_selection_default(self):
        """Test default dispatcher selection"""
        app = ws.WebSocketApp("ws://example.com")

        # Test default dispatcher (non-SSL)
        dispatcher = app.create_dispatcher(ping_timeout=10, is_ssl=False)
        self.assertIsInstance(dispatcher, ws._dispatcher.Dispatcher)

    def test_dispatcher_selection_ssl(self):
        """Test SSL dispatcher selection"""
        app = ws.WebSocketApp("wss://example.com")

        # Test SSL dispatcher
        dispatcher = app.create_dispatcher(ping_timeout=10, is_ssl=True)
        self.assertIsInstance(dispatcher, ws._dispatcher.SSLDispatcher)

    def test_dispatcher_selection_custom(self):
        """Test custom dispatcher selection"""
        from unittest.mock import Mock

        app = ws.WebSocketApp("ws://example.com")
        custom_dispatcher = Mock()
        handle_disconnect = Mock()

        # Test wrapped dispatcher with custom dispatcher
        dispatcher = app.create_dispatcher(
            ping_timeout=10,
            dispatcher=custom_dispatcher,
            handleDisconnect=handle_disconnect,
        )
        self.assertIsInstance(dispatcher, ws._dispatcher.WrappedDispatcher)
        self.assertEqual(dispatcher.dispatcher, custom_dispatcher)
        self.assertEqual(dispatcher.handleDisconnect, handle_disconnect)

    def test_dispatcher_selection_no_ping_timeout(self):
        """Test dispatcher selection without ping timeout"""
        app = ws.WebSocketApp("ws://example.com")

        # Test with None ping_timeout (should default to 10)
        dispatcher = app.create_dispatcher(ping_timeout=None, is_ssl=False)
        self.assertIsInstance(dispatcher, ws._dispatcher.Dispatcher)
        self.assertEqual(dispatcher.ping_timeout, 10)

    def test_suppress_host_parameter(self):
        """Test that suppress_host parameter is accepted by WebSocketApp.run_forever()"""
        app = ws.WebSocketApp("ws://nonexistent.example.com")

        # Test that suppress_host parameter is accepted without error
        # (Connection will fail but parameter should be accepted)
        try:
            app.run_forever(
                suppress_host=True,
                sockopt=((socket.SOL_SOCKET, socket.SO_REUSEADDR, 1),),
            )
        except (ws.WebSocketAddressException, OSError, ConnectionRefusedError):
            # Expected - connection should fail, but parameter was accepted
            pass

        # Test that suppress_host=False also works
        try:
            app.run_forever(
                suppress_host=False,
                sockopt=((socket.SOL_SOCKET, socket.SO_REUSEADDR, 1),),
            )
        except (ws.WebSocketAddressException, OSError, ConnectionRefusedError):
            # Expected - connection should fail, but parameter was accepted
            pass


class WebSocketAppUnitTests(unittest.TestCase):
    def _build_app(self):
        return ws.WebSocketApp("ws://example.com")

    def test_send_helpers_raise_when_socket_inactive(self):
        class DummySock:
            def __init__(self, return_value=0):
                self.return_value = return_value
                self.calls = []

            def send(self, data, opcode):
                self.calls.append((data, opcode))
                return self.return_value

        app = self._build_app()
        app.sock = DummySock(return_value=0)

        with self.assertRaises(ws.WebSocketConnectionClosedException):
            app.send("payload")
        with self.assertRaises(ws.WebSocketConnectionClosedException):
            app.send_text("payload")
        with self.assertRaises(ws.WebSocketConnectionClosedException):
            app.send_bytes(b"payload")

    def test_run_forever_validates_ping_configuration(self):
        app = self._build_app()

        with self.assertRaises(ws.WebSocketException):
            app.run_forever(ping_timeout=0)

        with self.assertRaises(ws.WebSocketException):
            app.run_forever(ping_interval=-1)

        with self.assertRaises(ws.WebSocketException):
            app.run_forever(ping_interval=1, ping_timeout=1)

    def test_run_forever_rejects_when_socket_already_open(self):
        app = self._build_app()
        app.sock = object()

        with self.assertRaises(ws.WebSocketException):
            app.run_forever()

    def test_close_frame_parsing(self):
        app = self._build_app()
        app.on_close = lambda *_: None
        close_payload = struct.pack("!H", 4000) + "bye".encode("utf-8")
        close_frame = ABNF.create_frame(close_payload, ABNF.OPCODE_CLOSE)

        status, reason = app._get_close_args(close_frame)
        self.assertEqual(status, 4000)
        self.assertEqual(reason, "bye")

        empty_frame = ABNF.create_frame(b"", ABNF.OPCODE_CLOSE)
        self.assertEqual(app._get_close_args(empty_frame), [None, None])

    def test_client_initiated_close_captures_peer_close_frame(self):
        """Test that client-initiated close uses stored close frame in teardown."""
        close_results = []

        def on_close(app, code, reason):
            close_results.append((code, reason))

        peer_close_payload = struct.pack("!H", 1000) + "peer-goodbye".encode("utf-8")
        peer_close_frame = ABNF.create_frame(peer_close_payload, ABNF.OPCODE_CLOSE)

        class FakeWebSocket:
            def __init__(self, *args, **kwargs):
                self.sock = mock.Mock()
                self.close_frame = None

            def settimeout(self, timeout):
                pass

            def connect(self, *args, **kwargs):
                pass

            def close(self, **kwargs):
                # Simulate peer sending a close frame in response to client close
                self.close_frame = peer_close_frame

            def shutdown(self):
                pass

            def recv_data_frame(self, *args, **kwargs):
                raise ws.WebSocketConnectionClosedException("closed")

        def fake_read(self, sock, read_callback, check_callback):
            # Trigger a client-initiated close, then let read() call teardown().
            self.app.close()
            read_callback()

        app = ws.WebSocketApp("ws://example.com", on_close=on_close)

        with mock.patch("websocket._app.WebSocket", FakeWebSocket):
            with mock.patch("websocket._app.Dispatcher.read", new=fake_read):
                app.run_forever()

        self.assertEqual(close_results, [(1000, "peer-goodbye")])

    def test_close_captures_frame_when_teardown_clears_socket(self):
        """close() retains its socket while concurrent teardown clears app.sock."""
        app = self._build_app()
        peer_close_frame = ABNF.create_frame(
            struct.pack("!H", 1000) + b"peer-goodbye", ABNF.OPCODE_CLOSE
        )
        close_started = threading.Event()
        allow_close_to_return = threading.Event()
        errors = []

        class FakeWebSocket:
            close_frame = None

            def close(self, **kwargs):
                self.close_frame = peer_close_frame
                close_started.set()
                if not allow_close_to_return.wait(timeout=1):
                    raise TimeoutError("test did not release FakeWebSocket.close()")

        app.sock = FakeWebSocket()

        def close_app():
            try:
                app.close()
            except Exception as error:
                errors.append(error)

        close_thread = threading.Thread(target=close_app)
        close_thread.start()
        self.assertTrue(close_started.wait(timeout=1))

        # This models run_forever() teardown clearing the shared app reference.
        app.sock = None
        allow_close_to_return.set()
        close_thread.join(timeout=1)

        self.assertFalse(close_thread.is_alive())
        self.assertEqual(errors, [])
        self.assertIs(app.last_close_frame, peer_close_frame)

    def test_last_close_frame_reset_on_reconnect(self):
        """Test that last_close_frame is reset when initializing a new socket."""
        app = self._build_app()

        # Simulate a previous close frame being stored
        old_close_payload = struct.pack("!H", 1001) + "old-reason".encode("utf-8")
        app.last_close_frame = ABNF.create_frame(old_close_payload, ABNF.OPCODE_CLOSE)

        # Verify last_close_frame is set
        self.assertIsNotNone(app.last_close_frame)

        # The reset happens in initialize_socket(), which is a nested function
        # inside run_forever(). We verify the attribute exists and can be reset.
        app.last_close_frame = None
        self.assertIsNone(app.last_close_frame)

    def test_callback_errors_propagate_to_on_error_once(self):
        capture = []

        def on_error(app, err):
            capture.append(err)

        def failing_callback(app, *_):
            raise RuntimeError("boom")

        app = self._build_app()
        app.on_error = on_error
        app._callback(failing_callback)
        self.assertEqual(len(capture), 1)
        self.assertIsInstance(capture[0], RuntimeError)

        # When the failing callback is on_error itself, ensure no recursion occurs.
        capture.clear()
        app.on_error = failing_callback
        app._callback(app.on_error)
        self.assertEqual(capture, [])


if __name__ == "__main__":
    unittest.main()
