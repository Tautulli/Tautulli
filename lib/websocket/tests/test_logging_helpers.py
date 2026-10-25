# -*- coding: utf-8 -*-
#
import importlib
import io
import logging
import unittest

import websocket
import websocket._logging as logging_module


class LoggingHelperTests(unittest.TestCase):
    def setUp(self):
        # Reload to ensure a clean logger for each test
        self.logging_mod = importlib.reload(logging_module)
        self.logger = logging.getLogger("websocket")

    def tearDown(self):
        importlib.reload(logging_module)

    def test_enable_trace_toggles_handler_and_level(self):
        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        original_level = self.logger.level

        self.logging_mod.enableTrace(True, handler=handler)
        self.assertTrue(self.logging_mod.isEnabledForTrace())
        self.assertIn(handler, self.logger.handlers)
        self.assertEqual(self.logger.level, logging.DEBUG)

        self.logging_mod.enableTrace(False)
        self.assertFalse(self.logging_mod.isEnabledForTrace())
        self.assertNotIn(handler, self.logger.handlers)
        self.assertEqual(self.logger.level, original_level)

    def test_dump_and_trace_emit_only_when_enabled(self):
        stream = io.StringIO()
        handler = logging.StreamHandler(stream)

        self.logging_mod.enableTrace(True, handler=handler)
        self.logging_mod.dump("header", "payload")
        self.logging_mod.trace("trace-line")
        handler.flush()
        logged = stream.getvalue()
        self.assertIn("header", logged)
        self.assertIn("payload", logged)
        self.assertIn("trace-line", logged)

        stream.truncate(0)
        stream.seek(0)
        self.logging_mod.enableTrace(False)
        self.logging_mod.dump("hidden", "secret")
        self.logging_mod.trace("should-not-log")
        handler.flush()
        self.assertEqual(stream.getvalue(), "")


class WebSocketModuleTraceTests(unittest.TestCase):
    def tearDown(self):
        websocket.enableTrace(False)

    def test_public_enable_trace_controls_logging(self):
        stream = io.StringIO()
        handler = logging.StreamHandler(stream)

        websocket.enableTrace(True, handler=handler)
        websocket.dump("public", "message")
        websocket.trace("visible-trace")
        handler.flush()
        logged = stream.getvalue()
        self.assertIn("public", logged)
        self.assertIn("message", logged)
        self.assertIn("visible-trace", logged)

        stream.truncate(0)
        stream.seek(0)
        websocket.enableTrace(False)
        websocket.dump("hidden", "payload")
        websocket.trace("not-logged")
        handler.flush()
        self.assertEqual(stream.getvalue(), "")


if __name__ == "__main__":
    unittest.main()
