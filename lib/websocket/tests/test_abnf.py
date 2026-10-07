# -*- coding: utf-8 -*-
#
import importlib
import sys
import unittest
from unittest import mock

from websocket._abnf import ABNF, continuous_frame, frame_buffer
from websocket._exceptions import WebSocketPayloadException, WebSocketProtocolException

"""
test_abnf.py
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


class ABNFTest(unittest.TestCase):
    def test_init(self):
        a = ABNF(0, 0, 0, 0, opcode=ABNF.OPCODE_PING)
        self.assertEqual(a.fin, 0)
        self.assertEqual(a.rsv1, 0)
        self.assertEqual(a.rsv2, 0)
        self.assertEqual(a.rsv3, 0)
        self.assertEqual(a.opcode, 9)
        self.assertEqual(a.data, "")
        a_bad = ABNF(0, 1, 0, 0, opcode=77)
        self.assertEqual(a_bad.rsv1, 1)
        self.assertEqual(a_bad.opcode, 77)

    def test_status_constants_exported(self):
        """Every STATUS_ constant in _abnf must be exported via __all__."""
        import websocket
        import websocket._abnf as abnf_mod

        defined = {n for n in dir(abnf_mod) if n.startswith("STATUS_")}
        exported = {n for n in abnf_mod.__all__ if n.startswith("STATUS_")}
        self.assertSetEqual(exported, defined)
        self.assertEqual(websocket.STATUS_SERVICE_RESTART, 1012)
        self.assertEqual(websocket.STATUS_TRY_AGAIN_LATER, 1013)

    def test_validate(self):
        a_invalid_ping = ABNF(0, 0, 0, 0, opcode=ABNF.OPCODE_PING)
        self.assertRaises(
            WebSocketProtocolException,
            a_invalid_ping.validate,
            skip_utf8_validation=False,
        )
        a_bad_rsv_value = ABNF(0, 1, 0, 0, opcode=ABNF.OPCODE_TEXT)
        self.assertRaises(
            WebSocketProtocolException,
            a_bad_rsv_value.validate,
            skip_utf8_validation=False,
        )
        a_bad_opcode = ABNF(0, 0, 0, 0, opcode=77)
        self.assertRaises(
            WebSocketProtocolException,
            a_bad_opcode.validate,
            skip_utf8_validation=False,
        )
        a_bad_close_frame = ABNF(0, 0, 0, 0, opcode=ABNF.OPCODE_CLOSE, data=b"\x01")
        self.assertRaises(
            WebSocketProtocolException,
            a_bad_close_frame.validate,
            skip_utf8_validation=False,
        )
        a_bad_close_frame_2 = ABNF(
            0, 0, 0, 0, opcode=ABNF.OPCODE_CLOSE, data=b"\x01\x8a\xaa\xff\xdd"
        )
        self.assertRaises(
            WebSocketProtocolException,
            a_bad_close_frame_2.validate,
            skip_utf8_validation=False,
        )
        a_bad_close_frame_3 = ABNF(
            0, 0, 0, 0, opcode=ABNF.OPCODE_CLOSE, data=b"\x03\xe7"
        )
        self.assertRaises(
            WebSocketProtocolException,
            a_bad_close_frame_3.validate,
            skip_utf8_validation=True,
        )

    def test_validate_exception_messages_are_formatted(self):
        invalid_opcode = ABNF(0, 0, 0, 0, opcode=5)
        with self.assertRaisesRegex(WebSocketProtocolException, r"^Invalid opcode 5$"):
            invalid_opcode.validate()

        invalid_close_status = ABNF(
            1, 0, 0, 0, opcode=ABNF.OPCODE_CLOSE, mask_value=0, data=b"\x03\xe7"
        )
        with self.assertRaisesRegex(
            WebSocketProtocolException, r"^Invalid close opcode 999$"
        ):
            invalid_close_status.validate()

    def test_mask(self):
        abnf_none_data = ABNF(
            0, 0, 0, 0, opcode=ABNF.OPCODE_PING, mask_value=1, data=None
        )
        bytes_val = b"aaaa"
        self.assertEqual(abnf_none_data._get_masked(bytes_val), bytes_val)
        abnf_str_data = ABNF(
            0, 0, 0, 0, opcode=ABNF.OPCODE_PING, mask_value=1, data="a"
        )
        self.assertEqual(abnf_str_data._get_masked(bytes_val), b"aaaa\x00")

    def test_format(self):
        abnf_bad_rsv_bits = ABNF(2, 0, 0, 0, opcode=ABNF.OPCODE_TEXT)
        self.assertRaises(ValueError, abnf_bad_rsv_bits.format)
        abnf_bad_opcode = ABNF(0, 0, 0, 0, opcode=5)
        self.assertRaises(ValueError, abnf_bad_opcode.format)
        abnf_length_10 = ABNF(0, 0, 0, 0, opcode=ABNF.OPCODE_TEXT, data="abcdefghij")
        self.assertEqual(b"\x01", abnf_length_10.format()[0].to_bytes(1, "big"))
        self.assertEqual(b"\x8a", abnf_length_10.format()[1].to_bytes(1, "big"))
        self.assertEqual("fin=0 opcode=1 data=abcdefghij", abnf_length_10.__str__())
        abnf_length_20 = ABNF(
            0, 0, 0, 0, opcode=ABNF.OPCODE_BINARY, data="abcdefghijabcdefghij"
        )
        self.assertEqual(b"\x02", abnf_length_20.format()[0].to_bytes(1, "big"))
        self.assertEqual(b"\x94", abnf_length_20.format()[1].to_bytes(1, "big"))
        abnf_no_mask = ABNF(
            0, 0, 0, 0, opcode=ABNF.OPCODE_TEXT, mask_value=0, data=b"\x01\x8a\xcc"
        )
        self.assertEqual(b"\x01\x03\x01\x8a\xcc", abnf_no_mask.format())

    def test_frame_buffer(self):
        fb = frame_buffer(0, True)
        self.assertEqual(fb.recv, 0)
        self.assertEqual(fb.skip_utf8_validation, True)
        fb.header = (1, 0, 0, 0, ABNF.OPCODE_TEXT, 1, 10)
        fb.length = 10
        fb.mask_value = b"abcd"
        fb.clear()
        self.assertIsNone(fb.header)
        self.assertIsNone(fb.length)
        self.assertIsNone(fb.mask_value)
        self.assertFalse(fb.has_mask())

    def test_frame_buffer_recv_frame_handles_chunked_reads(self):
        payload = b"Hello"
        frame_bytes = b"\x81" + bytes([len(payload)]) + payload  # Unmasked text frame
        chunks = [frame_bytes[:1], frame_bytes[1:2], frame_bytes[2:4], frame_bytes[4:]]

        def chunked_recv(_):
            if not chunks:
                raise AssertionError("recv called after buffer drained")
            return chunks.pop(0)

        fb = frame_buffer(chunked_recv, skip_utf8_validation=False)
        frame = fb.recv_frame()

        self.assertEqual(frame.fin, 1)
        self.assertEqual(frame.opcode, ABNF.OPCODE_TEXT)
        self.assertEqual(frame.data, payload)
        self.assertEqual(chunks, [])

    def test_recv_strict_preserves_unconsumed_bytes(self):
        remaining = bytearray(b"abcdef")

        def greedy_recv(_):
            if not remaining:
                raise AssertionError("recv called with empty buffer")
            chunk = bytes(remaining)
            remaining.clear()
            return chunk

        fb = frame_buffer(greedy_recv, skip_utf8_validation=True)
        first = fb.recv_strict(4)
        self.assertEqual(first, b"abcd")
        # The extra bytes should stay buffered for the next strict read
        self.assertEqual(fb.recv_buffer, [b"ef"])

        second = fb.recv_strict(2)
        self.assertEqual(second, b"ef")
        self.assertEqual(fb.recv_buffer, [])

    def test_recv_strict_handles_none_and_non_bytes(self):
        calls_none = [b"ab", None, b"cd"]

        def recv_none(_):
            return calls_none.pop(0)

        fb_none = frame_buffer(recv_none, skip_utf8_validation=True)
        self.assertEqual(fb_none.recv_strict(4), b"ab")
        self.assertEqual(fb_none.recv_strict(2), b"cd")
        self.assertEqual(calls_none, [])

        calls_str = [b"xy", "zz", b"pq"]

        def recv_str(_):
            return calls_str.pop(0)

        fb_str = frame_buffer(recv_str, skip_utf8_validation=True)
        self.assertEqual(fb_str.recv_strict(4), b"xy")
        self.assertEqual(fb_str.recv_strict(2), b"pq")
        self.assertEqual(calls_str, [])


class AbnfPureUnitTests(unittest.TestCase):
    def test_mask_without_wsaccel(self):
        import websocket._abnf as abnf_module

        mask_key = b"\x01\x02\x03\x04"
        data = b"\x05\x06\x07\x08\t"
        expected = bytes(mask_key[i % 4] ^ data[i] for i in range(len(data)))

        with mock.patch.dict(sys.modules, {"wsaccel": None, "wsaccel.xormask": None}):
            reloaded = importlib.reload(abnf_module)
            self.assertEqual(reloaded.ABNF.mask(mask_key, data), expected)

        importlib.reload(reloaded)

    def test_format_encodes_large_lengths(self):
        frame_126 = ABNF(
            1, 0, 0, 0, opcode=ABNF.OPCODE_TEXT, mask_value=0, data=b"x" * 126
        )
        formatted = frame_126.format()
        self.assertEqual(formatted[1], 0x7E)
        self.assertEqual(formatted[2:4], (126).to_bytes(2, "big"))

        frame_65536 = ABNF(
            1, 0, 0, 0, opcode=ABNF.OPCODE_BINARY, mask_value=0, data=b"y" * 66000
        )
        formatted_long = frame_65536.format()
        self.assertEqual(formatted_long[1], 0x7F)
        self.assertEqual(len(formatted_long[2:10]), 8)
        self.assertEqual(int.from_bytes(formatted_long[2:10], "big"), 66000)

    def test_continuous_frame_invalid_utf8_raises(self):
        cont = continuous_frame(fire_cont_frame=False, skip_utf8_validation=False)
        start = ABNF(
            fin=0,
            opcode=ABNF.OPCODE_TEXT,
            data=b"\xf0\x28",
            mask_value=0,
        )
        cont.validate(start)
        cont.add(start)

        end = ABNF(
            fin=1,
            opcode=ABNF.OPCODE_CONT,
            data=b"\x8c\x28",
            mask_value=0,
        )
        cont.validate(end)
        cont.add(end)
        self.assertTrue(cont.is_fire(end))
        with self.assertRaises(WebSocketPayloadException):
            cont.extract(end)


if __name__ == "__main__":
    unittest.main()
