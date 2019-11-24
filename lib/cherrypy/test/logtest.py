"""logtest, a unittest.TestCase helper for testing log output."""

import sys
import time
from uuid import UUID

import six

from cherrypy._cpcompat import text_or_bytes, ntob


try:
    # On Windows, msvcrt.getch reads a single char without output.
    import msvcrt

    def getchar():
        return msvcrt.getch()
except ImportError:
    # Unix getchr
    import tty
    import termios

    def getchar():
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch


class LogCase(object):

    """unittest.TestCase mixin for testing log messages.

    logfile: a filename for the desired log. Yes, I know modes are evil,
        but it makes the test functions so much cleaner to set this once.

    lastmarker: the last marker in the log. This can be used to search for
        messages since the last marker.

    markerPrefix: a string with which to prefix log markers. This should be
        unique enough from normal log output to use for marker identification.
    """

    logfile = None
    lastmarker = None
    markerPrefix = b'test suite marker: '

    def _handleLogError(self, msg, data, marker, pattern):
        print('')
        print('    ERROR: %s' % msg)

        if not self.interactive:
            raise self.failureException(msg)

        p = ('    Show: '
             '[L]og [M]arker [P]attern; '
             '[I]gnore, [R]aise, or sys.e[X]it >> ')
        sys.stdout.write(p + ' ')
        # ARGH
        sys.stdout.flush()
        while True:
            i = getchar().upper()
            if i not in 'MPLIRX':
                continue
            print(i.upper())  # Also prints new line
            if i == 'L':
                for x, line in enumerate(data):
                    if (x + 1) % self.console_height == 0:
                        # The \r and comma should make the next line overwrite
                        sys.stdout.write('<-- More -->\r ')
                        m = getchar().lower()
                        # Erase our "More" prompt
                        sys.stdout.write('            \r ')
                        if m == 'q':
                            break
                    print(line.rstrip())
            elif i == 'M':
                print(repr(marker or self.lastmarker))
            elif i == 'P':
                print(repr(pattern))
            elif i == 'I':
                # return without raising the normal exception
                return
            elif i == 'R':
                raise self.failureException(msg)
            elif i == 'X':
                self.exit()
            sys.stdout.write(p + ' ')

    def exit(self):
        sys.exit()

    def emptyLog(self):
        """Overwrite self.logfile with 0 bytes."""
        open(self.logfile, 'wb').write('')

    def markLog(self, key=None):
        """Insert a marker line into the log and set self.lastmarker."""
        if key is None:
            key = str(time.time())
        self.lastmarker = key

        open(self.logfile, 'ab+').write(
            ntob('%s%s\n' % (self.markerPrefix, key), 'utf-8'))

    def _read_marked_region(self, marker=None):
        """Return lines from self.logfile in the marked region.

        If marker is None, self.lastmarker is used. If the log hasn't
        been marked (using self.markLog), the entire log will be returned.
        """
# Give the logger time to finish writing?
# time.sleep(0.5)

        logfile = self.logfile
        marker = marker or self.lastmarker
        if marker is None:
            return open(logfile, 'rb').readlines()

        if isinstance(marker, six.text_type):
            marker = marker.encode('utf-8')
        data = []
        in_region = False
        for line in open(logfile, 'rb'):
            if in_region:
                if line.startswith(self.markerPrefix) and marker not in line:
                    break
                else:
                    data.append(line)
            elif marker in line:
                in_region = True
        return data

    def assertInLog(self, line, marker=None):
        """Fail if the given (partial) line is not in the log.

        The log will be searched from the given marker to the next marker.
        If marker is None, self.lastmarker is used. If the log hasn't
        been marked (using self.markLog), the entire log will be searched.
        """
        data = self._read_marked_region(marker)
        for logline in data:
            if line in logline:
                return
        msg = '%r not found in log' % line
        self._handleLogError(msg, data, marker, line)

    def assertNotInLog(self, line, marker=None):
        """Fail if the given (partial) line is in the log.

        The log will be searched from the given marker to the next marker.
        If marker is None, self.lastmarker is used. If the log hasn't
        been marked (using self.markLog), the entire log will be searched.
        """
        data = self._read_marked_region(marker)
        for logline in data:
            if line in logline:
                msg = '%r found in log' % line
                self._handleLogError(msg, data, marker, line)

    def assertValidUUIDv4(self, marker=None):
        """Fail if the given UUIDv4 is not valid.

        The log will be searched from the given marker to the next marker.
        If marker is None, self.lastmarker is used. If the log hasn't
        been marked (using self.markLog), the entire log will be searched.
        """
        data = self._read_marked_region(marker)
        data = [
            chunk.decode('utf-8').rstrip('\n').rstrip('\r')
            for chunk in data
        ]
        for log_chunk in data:
            try:
                uuid_log = data[-1]
                uuid_obj = UUID(uuid_log, version=4)
            except (TypeError, ValueError):
                pass  # it might be in other chunk
            else:
                if str(uuid_obj) == uuid_log:
                    return
                msg = '%r is not a valid UUIDv4' % uuid_log
                self._handleLogError(msg, data, marker, log_chunk)

        msg = 'UUIDv4 not found in log'
        self._handleLogError(msg, data, marker, log_chunk)

    def assertLog(self, sliceargs, lines, marker=None):
        """Fail if log.readlines()[sliceargs] is not contained in 'lines'.

        The log will be searched from the given marker to the next marker.
        If marker is None, self.lastmarker is used. If the log hasn't
        been marked (using self.markLog), the entire log will be searched.
        """
        data = self._read_marked_region(marker)
        if isinstance(sliceargs, int):
            # Single arg. Use __getitem__ and allow lines to be str or list.
            if isinstance(lines, (tuple, list)):
                lines = lines[0]
            if isinstance(lines, six.text_type):
                lines = lines.encode('utf-8')
            if lines not in data[sliceargs]:
                msg = '%r not found on log line %r' % (lines, sliceargs)
                self._handleLogError(
                    msg,
                    [data[sliceargs], '--EXTRA CONTEXT--'] + data[
                        sliceargs + 1:sliceargs + 6],
                    marker,
                    lines)
        else:
            # Multiple args. Use __getslice__ and require lines to be list.
            if isinstance(lines, tuple):
                lines = list(lines)
            elif isinstance(lines, text_or_bytes):
                raise TypeError("The 'lines' arg must be a list when "
                                "'sliceargs' is a tuple.")

            start, stop = sliceargs
            for line, logline in zip(lines, data[start:stop]):
                if isinstance(line, six.text_type):
                    line = line.encode('utf-8')
                if line not in logline:
                    msg = '%r not found in log' % line
                    self._handleLogError(msg, data[start:stop], marker, line)
