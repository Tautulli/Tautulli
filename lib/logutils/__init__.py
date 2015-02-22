#
# Copyright (C) 2010-2013 Vinay Sajip. See LICENSE.txt for details.
#
"""
The logutils package provides a set of handlers for the Python standard
library's logging package.

Some of these handlers are out-of-scope for the standard library, and
so they are packaged here. Others are updated versions which have
appeared in recent Python releases, but are usable with older versions
of Python, and so are packaged here.
"""
import logging
from string import Template

__version__ = '0.3.3'

class NullHandler(logging.Handler):
    """
    This handler does nothing. It's intended to be used to avoid the
    "No handlers could be found for logger XXX" one-off warning. This is
    important for library code, which may contain code to log events. If a user
    of the library does not configure logging, the one-off warning might be
    produced; to avoid this, the library developer simply needs to instantiate
    a NullHandler and add it to the top-level logger of the library module or
    package.
    """

    def handle(self, record):
        """
        Handle a record. Does nothing in this class, but in other
        handlers it typically filters and then emits the record in a 
        thread-safe way.
        """
        pass

    def emit(self, record):
        """
        Emit a record. This does nothing and shouldn't be called during normal
        processing, unless you redefine :meth:`~logutils.NullHandler.handle`.
        """
        pass

    def createLock(self):
        """
        Since this handler does nothing, it has no underlying I/O to protect
        against multi-threaded access, so this method returns `None`.
        """
        self.lock = None

class PercentStyle(object):

    default_format = '%(message)s'
    asctime_format = '%(asctime)s'

    def __init__(self, fmt):
        self._fmt = fmt or self.default_format

    def usesTime(self):
        return self._fmt.find(self.asctime_format) >= 0

    def format(self, record):
        return self._fmt % record.__dict__

class StrFormatStyle(PercentStyle):
    default_format = '{message}'
    asctime_format = '{asctime}'

    def format(self, record):
        return self._fmt.format(**record.__dict__)


class StringTemplateStyle(PercentStyle):
    default_format = '${message}'
    asctime_format = '${asctime}'

    def __init__(self, fmt):
        self._fmt = fmt or self.default_format
        self._tpl = Template(self._fmt)

    def usesTime(self):
        fmt = self._fmt
        return fmt.find('$asctime') >= 0 or fmt.find(self.asctime_format) >= 0

    def format(self, record):
        return self._tpl.substitute(**record.__dict__)

_STYLES = {
    '%': PercentStyle,
    '{': StrFormatStyle,
    '$': StringTemplateStyle
}

class Formatter(logging.Formatter):
    """
    Subclasses Formatter in Pythons earlier than 3.2 in order to give
    3.2 Formatter behaviour with respect to allowing %-, {} or $-
    formatting.
    """
    def __init__(self, fmt=None, datefmt=None, style='%'):
        """
        Initialize the formatter with specified format strings.

        Initialize the formatter either with the specified format string, or a
        default as described above. Allow for specialized date formatting with
        the optional datefmt argument (if omitted, you get the ISO8601 format).

        Use a style parameter of '%', '{' or '$' to specify that you want to
        use one of %-formatting, :meth:`str.format` (``{}``) formatting or
        :class:`string.Template` formatting in your format string.
        """
        if style not in _STYLES:
            raise ValueError('Style must be one of: %s' % ','.join(
                             _STYLES.keys()))
        self._style = _STYLES[style](fmt)
        self._fmt = self._style._fmt
        self.datefmt = datefmt

    def usesTime(self):
        """
        Check if the format uses the creation time of the record.
        """
        return self._style.usesTime()

    def formatMessage(self, record):
        return self._style.format(record)

    def format(self, record):
        """
        Format the specified record as text.

        The record's attribute dictionary is used as the operand to a
        string formatting operation which yields the returned string.
        Before formatting the dictionary, a couple of preparatory steps
        are carried out. The message attribute of the record is computed
        using LogRecord.getMessage(). If the formatting string uses the
        time (as determined by a call to usesTime(), formatTime() is
        called to format the event time. If there is exception information,
        it is formatted using formatException() and appended to the message.
        """
        record.message = record.getMessage()
        if self.usesTime():
            record.asctime = self.formatTime(record, self.datefmt)
        s = self.formatMessage(record)
        if record.exc_info:
            # Cache the traceback text to avoid converting it multiple times
            # (it's constant anyway)
            if not record.exc_text:
                record.exc_text = self.formatException(record.exc_info)
        if record.exc_text:
            if s[-1:] != "\n":
                s = s + "\n"
            s = s + record.exc_text
        return s


class BraceMessage(object):
    def __init__(self, fmt, *args, **kwargs):
        self.fmt = fmt
        self.args = args
        self.kwargs = kwargs
        self.str = None
        
    def __str__(self):
        if self.str is None:
            self.str = self.fmt.format(*self.args, **self.kwargs)
        return self.str

class DollarMessage(object):
    def __init__(self, fmt, **kwargs):
        self.fmt = fmt
        self.kwargs = kwargs
        self.str = None
        
    def __str__(self):
        if self.str is None:
            self.str = Template(self.fmt).substitute(**self.kwargs)
        return self.str


def hasHandlers(logger):
    """
    See if a logger has any handlers.
    """
    rv = False
    while logger:
        if logger.handlers:
            rv = True
            break
        elif not logger.propagate:
            break
        else:
            logger = logger.parent
    return rv

