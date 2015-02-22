#
# Copyright (C) 2010-2013 Vinay Sajip. See LICENSE.txt for details.
#
import logging
from logging.handlers import BufferingHandler

class TestHandler(BufferingHandler):
    """
    This handler collects records in a buffer for later inspection by
    your unit test code.
    
    :param matcher: The :class:`~logutils.testing.Matcher` instance to
                    use for matching.
    """
    def __init__(self, matcher):
        # BufferingHandler takes a "capacity" argument
        # so as to know when to flush. As we're overriding
        # shouldFlush anyway, we can set a capacity of zero.
        # You can call flush() manually to clear out the
        # buffer.
        BufferingHandler.__init__(self, 0)
        self.formatted = []
        self.matcher = matcher

    def shouldFlush(self):
        """
        Should the buffer be flushed?

        This returns `False` - you'll need to flush manually, usually after
        your unit test code checks the buffer contents against your
        expectations.
        """
        return False

    def emit(self, record):
        """
        Saves the `__dict__` of the record in the `buffer` attribute,
        and the formatted records in the `formatted` attribute.

        :param record: The record to emit.
        """
        self.formatted.append(self.format(record))
        self.buffer.append(record.__dict__)

    def flush(self):
        """
        Clears out the `buffer` and `formatted` attributes.
        """
        BufferingHandler.flush(self)
        self.formatted = []

    def matches(self, **kwargs):
        """
        Look for a saved dict whose keys/values match the supplied arguments.

        Return `True` if found, else `False`.
        
        :param kwargs: A set of keyword arguments whose names are LogRecord
                       attributes and whose values are what you want to 
                       match in a stored LogRecord.
        """
        result = False
        for d in self.buffer:
            if self.matcher.matches(d, **kwargs):
                result = True
                break
        #if not result:
        #    print('*** matcher failed completely on %d records' % len(self.buffer))
        return result

    def matchall(self, kwarglist):
        """
        Accept a list of keyword argument values and ensure that the handler's
        buffer of stored records matches the list one-for-one.

        Return `True` if exactly matched, else `False`.
        
        :param kwarglist: A list of keyword-argument dictionaries, each of
                          which will be passed to :meth:`matches` with the
                          corresponding record from the buffer.
        """
        if self.count != len(kwarglist):
            result = False
        else:
            result = True
            for d, kwargs in zip(self.buffer, kwarglist):
                if not self.matcher.matches(d, **kwargs):
                    result = False
                    break
        return result

    @property
    def count(self):
        """
        The number of records in the buffer.
        """
        return len(self.buffer)

class Matcher(object):
    """
    This utility class matches a stored dictionary of
    :class:`logging.LogRecord` attributes with keyword arguments
    passed to its :meth:`~logutils.testing.Matcher.matches` method.
    """
    
    _partial_matches = ('msg', 'message')
    """
    A list of :class:`logging.LogRecord` attribute names which
    will be checked for partial matches. If not in this list,
    an exact match will be attempted.
    """
    
    def matches(self, d, **kwargs):
        """
        Try to match a single dict with the supplied arguments.

        Keys whose values are strings and which are in self._partial_matches
        will be checked for partial (i.e. substring) matches. You can extend
        this scheme to (for example) do regular expression matching, etc.
        
        Return `True` if found, else `False`.

        :param kwargs: A set of keyword arguments whose names are LogRecord
                       attributes and whose values are what you want to 
                       match in a stored LogRecord.
        """
        result = True
        for k in kwargs:
            v = kwargs[k]
            dv = d.get(k)
            if not self.match_value(k, dv, v):
                #print('*** matcher failed: %s, %r, %r' % (k, dv, v))
                result = False
                break
        return result

    def match_value(self, k, dv, v):
        """
        Try to match a single stored value (dv) with a supplied value (v).

        Return `True` if found, else `False`.

        :param k: The key value (LogRecord attribute name).
        :param dv: The stored value to match against.
        :param v: The value to compare with the stored value.
        """
        if type(v) != type(dv):
            result = False
        elif type(dv) is not str or k not in self._partial_matches:
            result = (v == dv)
        else:
            result = dv.find(v) >= 0
        #if not result:
        #    print('*** matcher failed on %s: %r vs. %r' % (k, dv, v))
        return result

