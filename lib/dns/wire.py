# Copyright (C) Dnspython Contributors, see LICENSE for text of ISC license

import contextlib
import struct

import dns.exception
import dns.name

class Parser:
    def __init__(self, wire, current=0):
        self.wire = wire
        self.current = 0
        self.end = len(self.wire)
        if current:
            self.seek(current)
        self.furthest = current

    def remaining(self):
        return self.end - self.current

    def get_bytes(self, size):
        if size > self.remaining():
            raise dns.exception.FormError
        output = self.wire[self.current:self.current + size]
        self.current += size
        self.furthest = max(self.furthest, self.current)
        return output

    def get_counted_bytes(self, length_size=1):
        length = int.from_bytes(self.get_bytes(length_size), 'big')
        return self.get_bytes(length)

    def get_remaining(self):
        return self.get_bytes(self.remaining())

    def get_uint8(self):
        return struct.unpack('!B', self.get_bytes(1))[0]

    def get_uint16(self):
        return struct.unpack('!H', self.get_bytes(2))[0]

    def get_uint32(self):
        return struct.unpack('!I', self.get_bytes(4))[0]

    def get_uint48(self):
        return int.from_bytes(self.get_bytes(6), 'big')

    def get_struct(self, format):
        return struct.unpack(format, self.get_bytes(struct.calcsize(format)))

    def get_name(self, origin=None):
        name = dns.name.from_wire_parser(self)
        if origin:
            name = name.relativize(origin)
        return name

    def seek(self, where):
        # Note that seeking to the end is OK!  (If you try to read
        # after such a seek, you'll get an exception as expected.)
        if where < 0 or where > self.end:
            raise dns.exception.FormError
        self.current = where

    @contextlib.contextmanager
    def restrict_to(self, size):
        if size > self.remaining():
            raise dns.exception.FormError
        saved_end = self.end
        try:
            self.end = self.current + size
            yield
            # We make this check here and not in the finally as we
            # don't want to raise if we're already raising for some
            # other reason.
            if self.current != self.end:
                raise dns.exception.FormError
        finally:
            self.end = saved_end

    @contextlib.contextmanager
    def restore_furthest(self):
        try:
            yield None
        finally:
            self.current = self.furthest
