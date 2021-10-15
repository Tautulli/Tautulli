"""Socket file object."""

from __future__ import absolute_import, division, print_function
__metaclass__ = type

import socket

try:
    # prefer slower Python-based io module
    import _pyio as io
except ImportError:
    # Python 2.6
    import io

import six

from . import errors
from ._compat import extract_bytes, memoryview


# Write only 16K at a time to sockets
SOCK_WRITE_BLOCKSIZE = 16384


class BufferedWriter(io.BufferedWriter):
    """Faux file object attached to a socket object."""

    def write(self, b):
        """Write bytes to buffer."""
        self._checkClosed()
        if isinstance(b, str):
            raise TypeError("can't write str to binary stream")

        with self._write_lock:
            self._write_buf.extend(b)
            self._flush_unlocked()
            return len(b)

    def _flush_unlocked(self):
        self._checkClosed('flush of closed file')
        while self._write_buf:
            try:
                # ssl sockets only except 'bytes', not bytearrays
                # so perhaps we should conditionally wrap this for perf?
                n = self.raw.write(bytes(self._write_buf))
            except io.BlockingIOError as e:
                n = e.characters_written
            del self._write_buf[:n]


class MakeFile_PY2(getattr(socket, '_fileobject', object)):
    """Faux file object attached to a socket object."""

    def __init__(self, *args, **kwargs):
        """Initialize faux file object."""
        self.bytes_read = 0
        self.bytes_written = 0
        socket._fileobject.__init__(self, *args, **kwargs)
        self._refcount = 0

    def _reuse(self):
        self._refcount += 1

    def _drop(self):
        if self._refcount < 0:
            self.close()
        else:
            self._refcount -= 1

    def write(self, data):
        """Send entire data contents for non-blocking sockets."""
        bytes_sent = 0
        data_mv = memoryview(data)
        payload_size = len(data_mv)
        while bytes_sent < payload_size:
            try:
                bytes_sent += self.send(
                    data_mv[bytes_sent:bytes_sent + SOCK_WRITE_BLOCKSIZE],
                )
            except socket.error as e:
                if e.args[0] not in errors.socket_errors_nonblocking:
                    raise

    def send(self, data):
        """Send some part of message to the socket."""
        bytes_sent = self._sock.send(extract_bytes(data))
        self.bytes_written += bytes_sent
        return bytes_sent

    def flush(self):
        """Write all data from buffer to socket and reset write buffer."""
        if self._wbuf:
            buffer = ''.join(self._wbuf)
            self._wbuf = []
            self.write(buffer)

    def recv(self, size):
        """Receive message of a size from the socket."""
        while True:
            try:
                data = self._sock.recv(size)
                self.bytes_read += len(data)
                return data
            except socket.error as e:
                what = (
                    e.args[0] not in errors.socket_errors_nonblocking
                    and e.args[0] not in errors.socket_error_eintr
                )
                if what:
                    raise

    class FauxSocket:
        """Faux socket with the minimal interface required by pypy."""

        def _reuse(self):
            pass

    _fileobject_uses_str_type = six.PY2 and isinstance(
        socket._fileobject(FauxSocket())._rbuf, six.string_types,
    )

    # FauxSocket is no longer needed
    del FauxSocket

    if not _fileobject_uses_str_type:  # noqa: C901  # FIXME
        def read(self, size=-1):
            """Read data from the socket to buffer."""
            # Use max, disallow tiny reads in a loop as they are very
            # inefficient.
            # We never leave read() with any leftover data from a new recv()
            # call in our internal buffer.
            rbufsize = max(self._rbufsize, self.default_bufsize)
            # Our use of StringIO rather than lists of string objects returned
            # by recv() minimizes memory usage and fragmentation that occurs
            # when rbufsize is large compared to the typical return value of
            # recv().
            buf = self._rbuf
            buf.seek(0, 2)  # seek end
            if size < 0:
                # Read until EOF
                # reset _rbuf.  we consume it via buf.
                self._rbuf = io.BytesIO()
                while True:
                    data = self.recv(rbufsize)
                    if not data:
                        break
                    buf.write(data)
                return buf.getvalue()
            else:
                # Read until size bytes or EOF seen, whichever comes first
                buf_len = buf.tell()
                if buf_len >= size:
                    # Already have size bytes in our buffer?  Extract and
                    # return.
                    buf.seek(0)
                    rv = buf.read(size)
                    self._rbuf = io.BytesIO()
                    self._rbuf.write(buf.read())
                    return rv

                # reset _rbuf.  we consume it via buf.
                self._rbuf = io.BytesIO()
                while True:
                    left = size - buf_len
                    # recv() will malloc the amount of memory given as its
                    # parameter even though it often returns much less data
                    # than that.  The returned data string is short lived
                    # as we copy it into a StringIO and free it.  This avoids
                    # fragmentation issues on many platforms.
                    data = self.recv(left)
                    if not data:
                        break
                    n = len(data)
                    if n == size and not buf_len:
                        # Shortcut.  Avoid buffer data copies when:
                        # - We have no data in our buffer.
                        # AND
                        # - Our call to recv returned exactly the
                        #   number of bytes we were asked to read.
                        return data
                    if n == left:
                        buf.write(data)
                        del data  # explicit free
                        break
                    assert n <= left, 'recv(%d) returned %d bytes' % (left, n)
                    buf.write(data)
                    buf_len += n
                    del data  # explicit free
                    # assert buf_len == buf.tell()
                return buf.getvalue()

        def readline(self, size=-1):
            """Read line from the socket to buffer."""
            buf = self._rbuf
            buf.seek(0, 2)  # seek end
            if buf.tell() > 0:
                # check if we already have it in our buffer
                buf.seek(0)
                bline = buf.readline(size)
                if bline.endswith('\n') or len(bline) == size:
                    self._rbuf = io.BytesIO()
                    self._rbuf.write(buf.read())
                    return bline
                del bline
            if size < 0:
                # Read until \n or EOF, whichever comes first
                if self._rbufsize <= 1:
                    # Speed up unbuffered case
                    buf.seek(0)
                    buffers = [buf.read()]
                    # reset _rbuf.  we consume it via buf.
                    self._rbuf = io.BytesIO()
                    data = None
                    recv = self.recv
                    while data != '\n':
                        data = recv(1)
                        if not data:
                            break
                        buffers.append(data)
                    return ''.join(buffers)

                buf.seek(0, 2)  # seek end
                # reset _rbuf.  we consume it via buf.
                self._rbuf = io.BytesIO()
                while True:
                    data = self.recv(self._rbufsize)
                    if not data:
                        break
                    nl = data.find('\n')
                    if nl >= 0:
                        nl += 1
                        buf.write(data[:nl])
                        self._rbuf.write(data[nl:])
                        del data
                        break
                    buf.write(data)
                return buf.getvalue()

            else:
                # Read until size bytes or \n or EOF seen, whichever comes
                # first
                buf.seek(0, 2)  # seek end
                buf_len = buf.tell()
                if buf_len >= size:
                    buf.seek(0)
                    rv = buf.read(size)
                    self._rbuf = io.BytesIO()
                    self._rbuf.write(buf.read())
                    return rv
                # reset _rbuf.  we consume it via buf.
                self._rbuf = io.BytesIO()
                while True:
                    data = self.recv(self._rbufsize)
                    if not data:
                        break
                    left = size - buf_len
                    # did we just receive a newline?
                    nl = data.find('\n', 0, left)
                    if nl >= 0:
                        nl += 1
                        # save the excess data to _rbuf
                        self._rbuf.write(data[nl:])
                        if buf_len:
                            buf.write(data[:nl])
                            break
                        else:
                            # Shortcut.  Avoid data copy through buf when
                            # returning a substring of our first recv().
                            return data[:nl]
                    n = len(data)
                    if n == size and not buf_len:
                        # Shortcut.  Avoid data copy through buf when
                        # returning exactly all of our first recv().
                        return data
                    if n >= left:
                        buf.write(data[:left])
                        self._rbuf.write(data[left:])
                        break
                    buf.write(data)
                    buf_len += n
                    # assert buf_len == buf.tell()
                return buf.getvalue()

        def has_data(self):
            """Return true if there is buffered data to read."""
            return bool(self._rbuf.getvalue())

    else:
        def read(self, size=-1):
            """Read data from the socket to buffer."""
            if size < 0:
                # Read until EOF
                buffers = [self._rbuf]
                self._rbuf = ''
                if self._rbufsize <= 1:
                    recv_size = self.default_bufsize
                else:
                    recv_size = self._rbufsize

                while True:
                    data = self.recv(recv_size)
                    if not data:
                        break
                    buffers.append(data)
                return ''.join(buffers)
            else:
                # Read until size bytes or EOF seen, whichever comes first
                data = self._rbuf
                buf_len = len(data)
                if buf_len >= size:
                    self._rbuf = data[size:]
                    return data[:size]
                buffers = []
                if data:
                    buffers.append(data)
                self._rbuf = ''
                while True:
                    left = size - buf_len
                    recv_size = max(self._rbufsize, left)
                    data = self.recv(recv_size)
                    if not data:
                        break
                    buffers.append(data)
                    n = len(data)
                    if n >= left:
                        self._rbuf = data[left:]
                        buffers[-1] = data[:left]
                        break
                    buf_len += n
                return ''.join(buffers)

        def readline(self, size=-1):
            """Read line from the socket to buffer."""
            data = self._rbuf
            if size < 0:
                # Read until \n or EOF, whichever comes first
                if self._rbufsize <= 1:
                    # Speed up unbuffered case
                    assert data == ''
                    buffers = []
                    while data != '\n':
                        data = self.recv(1)
                        if not data:
                            break
                        buffers.append(data)
                    return ''.join(buffers)
                nl = data.find('\n')
                if nl >= 0:
                    nl += 1
                    self._rbuf = data[nl:]
                    return data[:nl]
                buffers = []
                if data:
                    buffers.append(data)
                self._rbuf = ''
                while True:
                    data = self.recv(self._rbufsize)
                    if not data:
                        break
                    buffers.append(data)
                    nl = data.find('\n')
                    if nl >= 0:
                        nl += 1
                        self._rbuf = data[nl:]
                        buffers[-1] = data[:nl]
                        break
                return ''.join(buffers)
            else:
                # Read until size bytes or \n or EOF seen, whichever comes
                # first
                nl = data.find('\n', 0, size)
                if nl >= 0:
                    nl += 1
                    self._rbuf = data[nl:]
                    return data[:nl]
                buf_len = len(data)
                if buf_len >= size:
                    self._rbuf = data[size:]
                    return data[:size]
                buffers = []
                if data:
                    buffers.append(data)
                self._rbuf = ''
                while True:
                    data = self.recv(self._rbufsize)
                    if not data:
                        break
                    buffers.append(data)
                    left = size - buf_len
                    nl = data.find('\n', 0, left)
                    if nl >= 0:
                        nl += 1
                        self._rbuf = data[nl:]
                        buffers[-1] = data[:nl]
                        break
                    n = len(data)
                    if n >= left:
                        self._rbuf = data[left:]
                        buffers[-1] = data[:left]
                        break
                    buf_len += n
                return ''.join(buffers)

        def has_data(self):
            """Return true if there is buffered data to read."""
            return bool(self._rbuf)


if not six.PY2:
    class StreamReader(io.BufferedReader):
        """Socket stream reader."""

        def __init__(self, sock, mode='r', bufsize=io.DEFAULT_BUFFER_SIZE):
            """Initialize socket stream reader."""
            super().__init__(socket.SocketIO(sock, mode), bufsize)
            self.bytes_read = 0

        def read(self, *args, **kwargs):
            """Capture bytes read."""
            val = super().read(*args, **kwargs)
            self.bytes_read += len(val)
            return val

        def has_data(self):
            """Return true if there is buffered data to read."""
            return len(self._read_buf) > self._read_pos

    class StreamWriter(BufferedWriter):
        """Socket stream writer."""

        def __init__(self, sock, mode='w', bufsize=io.DEFAULT_BUFFER_SIZE):
            """Initialize socket stream writer."""
            super().__init__(socket.SocketIO(sock, mode), bufsize)
            self.bytes_written = 0

        def write(self, val, *args, **kwargs):
            """Capture bytes written."""
            res = super().write(val, *args, **kwargs)
            self.bytes_written += len(val)
            return res

    def MakeFile(sock, mode='r', bufsize=io.DEFAULT_BUFFER_SIZE):
        """File object attached to a socket object."""
        cls = StreamReader if 'r' in mode else StreamWriter
        return cls(sock, mode, bufsize)
else:
    StreamReader = StreamWriter = MakeFile = MakeFile_PY2
