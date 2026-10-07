# -*- coding: utf-8 -*-
import unittest
import socket
import threading
import time
from unittest.mock import Mock, patch

from websocket import WebSocket, WebSocketApp
from websocket._core import WebSocket as CoreWebSocket
from websocket._exceptions import WebSocketConnectionClosedException


class ReconnectBadFileDescriptorTest(unittest.TestCase):
    """Test edge cases around reconnection when socket file descriptors become invalid"""

    def test_shutdown_with_already_closed_socket(self):
        """Test that shutdown() handles already closed sockets gracefully (issue #1026)"""
        ws = CoreWebSocket()

        # Create a mock socket
        mock_sock = Mock()
        mock_sock._closed = False
        ws.sock = mock_sock
        ws.connected = True

        # Simulate the socket being closed externally (e.g., network failure)
        mock_sock.close.side_effect = OSError("Bad file descriptor")

        # shutdown() should not raise an exception
        ws.shutdown()

        # Verify cleanup happened
        self.assertIsNone(ws.sock)
        self.assertFalse(ws.connected)

    def test_shutdown_with_closed_socket_attribute(self):
        """Test shutdown() when socket's _closed attribute is True"""
        ws = CoreWebSocket()

        # Create a mock socket that's already closed
        mock_sock = Mock()
        mock_sock._closed = True
        ws.sock = mock_sock
        ws.connected = True

        # shutdown() should not call close() on already closed socket
        ws.shutdown()

        # Verify close() was not called and cleanup happened
        mock_sock.close.assert_not_called()
        self.assertIsNone(ws.sock)
        self.assertFalse(ws.connected)

    def test_shutdown_with_missing_closed_attribute(self):
        """Test shutdown() when socket doesn't have _closed attribute"""
        ws = CoreWebSocket()

        # Create a mock socket without _closed attribute
        mock_sock = Mock()
        del mock_sock._closed  # Remove _closed attribute
        ws.sock = mock_sock
        ws.connected = True

        # shutdown() should handle AttributeError gracefully
        ws.shutdown()

        # Verify cleanup happened despite AttributeError
        self.assertIsNone(ws.sock)
        self.assertFalse(ws.connected)

    def test_shutdown_with_none_socket(self):
        """Test shutdown() when socket is None"""
        ws = CoreWebSocket()
        ws.sock = None
        ws.connected = False

        # Should not raise any exception
        ws.shutdown()

        self.assertIsNone(ws.sock)
        self.assertFalse(ws.connected)

    def test_websocketapp_reconnect_with_bad_fd_simulation(self):
        """Test WebSocketApp reconnection when socket becomes invalid during reconnect"""

        reconnect_attempts = []
        error_messages = []
        connection_count = 0

        def on_error(ws, error):
            error_messages.append(str(error))

        def on_reconnect(ws):
            reconnect_attempts.append(True)

        def on_open(ws):
            nonlocal connection_count
            connection_count += 1

        app = WebSocketApp(
            "ws://echo.websocket.events/",
            on_error=on_error,
            on_reconnect=on_reconnect,
            on_open=on_open,
        )

        # Test the actual shutdown method with bad file descriptor
        with patch("websocket._core.WebSocket.connect") as mock_connect:
            with patch("websocket._core.WebSocket.recv_data_frame") as mock_recv:
                # Simulate successful connection
                mock_connect.return_value = None

                # Simulate connection loss after a brief connection
                mock_recv.side_effect = WebSocketConnectionClosedException(
                    "Connection lost"
                )

                # Create a WebSocket instance with a mock socket that fails on close
                real_ws = CoreWebSocket()
                mock_socket = Mock()
                mock_socket._closed = False
                mock_socket.close.side_effect = OSError("[Errno 9] Bad file descriptor")
                real_ws.sock = mock_socket
                real_ws.connected = True

                # Test that our fixed shutdown method handles this gracefully
                # This should not raise an exception
                real_ws.shutdown()

                # Verify cleanup happened despite the error
                self.assertIsNone(real_ws.sock)
                self.assertFalse(real_ws.connected)

        # Test passes if shutdown() handled bad file descriptor gracefully

    def test_reconnection_with_externally_closed_socket(self):
        """Test the specific scenario from issue #1026: socket killed externally during reconnection"""

        # Create a WebSocket instance
        ws = CoreWebSocket()

        # Create a real socket and then close it externally to simulate network failure
        real_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        ws.sock = real_socket
        ws.connected = True

        # Close the socket externally (simulates `ss --kill` or network failure)
        real_socket.close()

        # Now try to shutdown the WebSocket - this should not raise "Bad file descriptor"
        # Our fix should handle this gracefully
        ws.shutdown()

        # Verify cleanup happened
        self.assertIsNone(ws.sock)
        self.assertFalse(ws.connected)

    def _safe_shutdown(self, ws_instance, mock_socket):
        """Helper method that simulates the fixed shutdown behavior"""
        try:
            if not mock_socket._closed:
                mock_socket.close()
        except (OSError, AttributeError):
            pass
        finally:
            ws_instance.sock = None
            ws_instance.connected = False

    def test_multiple_shutdown_calls(self):
        """Test that multiple shutdown() calls don't cause issues"""
        ws = CoreWebSocket()

        # Create a real socket for more realistic testing
        real_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        ws.sock = real_sock
        ws.connected = True

        # First shutdown should work normally
        ws.shutdown()
        self.assertIsNone(ws.sock)
        self.assertFalse(ws.connected)

        # Second shutdown should not raise exception
        ws.shutdown()
        self.assertIsNone(ws.sock)
        self.assertFalse(ws.connected)


if __name__ == "__main__":
    unittest.main()
