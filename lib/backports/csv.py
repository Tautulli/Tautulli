# -*- coding: utf-8 -*-
"""A port of Python 3's csv module to Python 2.

The API of the csv module in Python 2 is drastically different from
the csv module in Python 3. This is due, for the most part, to the
difference between str in Python 2 and Python 3.

The semantics of Python 3's version are more useful because they support
unicode natively, while Python 2's csv does not.
"""
from __future__ import unicode_literals, absolute_import

__all__ = [ "QUOTE_MINIMAL", "QUOTE_ALL", "QUOTE_NONNUMERIC", "QUOTE_NONE",
            "Error", "Dialect", "__doc__", "excel", "excel_tab",
            "field_size_limit", "reader", "writer",
            "register_dialect", "get_dialect", "list_dialects", "Sniffer",
            "unregister_dialect", "__version__", "DictReader", "DictWriter" ]

import re
import numbers
from io import StringIO
from csv import (
    QUOTE_MINIMAL, QUOTE_ALL, QUOTE_NONNUMERIC, QUOTE_NONE,
    __version__, __doc__, Error, field_size_limit,
)

# Stuff needed from six
import sys
PY3 = sys.version_info[0] == 3
if PY3:
    string_types = str
    text_type = str
    binary_type = bytes
    unichr = chr
else:
    string_types = basestring
    text_type = unicode
    binary_type = str


class QuoteStrategy(object):
    quoting = None

    def __init__(self, dialect):
        if self.quoting is not None:
            assert dialect.quoting == self.quoting
        self.dialect = dialect
        self.setup()

        escape_pattern_quoted = r'({quotechar})'.format(
            quotechar=re.escape(self.dialect.quotechar or '"'))
        escape_pattern_unquoted = r'([{specialchars}])'.format(
            specialchars=re.escape(self.specialchars))

        self.escape_re_quoted = re.compile(escape_pattern_quoted)
        self.escape_re_unquoted = re.compile(escape_pattern_unquoted)

    def setup(self):
        """Optional method for strategy-wide optimizations."""

    def quoted(self, field=None, raw_field=None, only=None):
        """Determine whether this field should be quoted."""
        raise NotImplementedError(
            'quoted must be implemented by a subclass')

    @property
    def specialchars(self):
        """The special characters that need to be escaped."""
        raise NotImplementedError(
            'specialchars must be implemented by a subclass')

    def escape_re(self, quoted=None):
        if quoted:
            return self.escape_re_quoted
        return self.escape_re_unquoted

    def escapechar(self, quoted=None):
        if quoted and self.dialect.doublequote:
            return self.dialect.quotechar
        return self.dialect.escapechar

    def prepare(self, raw_field, only=None):
        field = text_type(raw_field if raw_field is not None else '')
        quoted = self.quoted(field=field, raw_field=raw_field, only=only)

        escape_re = self.escape_re(quoted=quoted)
        escapechar = self.escapechar(quoted=quoted)

        if escape_re.search(field):
            escapechar = '\\\\' if escapechar == '\\' else escapechar
            if not escapechar:
                raise Error('No escapechar is set')
            escape_replace = r'{escapechar}\1'.format(escapechar=escapechar)
            field = escape_re.sub(escape_replace, field)

        if quoted:
            field = '{quotechar}{field}{quotechar}'.format(
                quotechar=self.dialect.quotechar, field=field)

        return field


class QuoteMinimalStrategy(QuoteStrategy):
    quoting = QUOTE_MINIMAL

    def setup(self):
        self.quoted_re = re.compile(r'[{specialchars}]'.format(
            specialchars=re.escape(self.specialchars)))

    @property
    def specialchars(self):
        return (
            self.dialect.lineterminator +
            self.dialect.quotechar +
            self.dialect.delimiter +
            (self.dialect.escapechar or '')
        )

    def quoted(self, field, only, **kwargs):
        if field == self.dialect.quotechar and not self.dialect.doublequote:
            # If the only character in the field is the quotechar, and
            # doublequote is false, then just escape without outer quotes.
            return False
        return field == '' and only or bool(self.quoted_re.search(field))


class QuoteAllStrategy(QuoteStrategy):
    quoting = QUOTE_ALL

    @property
    def specialchars(self):
        return self.dialect.quotechar

    def quoted(self, **kwargs):
        return True


class QuoteNonnumericStrategy(QuoteStrategy):
    quoting = QUOTE_NONNUMERIC

    @property
    def specialchars(self):
        return (
            self.dialect.lineterminator +
            self.dialect.quotechar +
            self.dialect.delimiter +
            (self.dialect.escapechar or '')
        )

    def quoted(self, raw_field, **kwargs):
        return not isinstance(raw_field, numbers.Number)


class QuoteNoneStrategy(QuoteStrategy):
    quoting = QUOTE_NONE

    @property
    def specialchars(self):
        return (
            self.dialect.lineterminator +
            (self.dialect.quotechar or '') +
            self.dialect.delimiter +
            (self.dialect.escapechar or '')
        )

    def quoted(self, field, only, **kwargs):
        if field == '' and only:
            raise Error('single empty field record must be quoted')
        return False


class writer(object):
    def __init__(self, fileobj, dialect='excel', **fmtparams):
        if fileobj is None:
            raise TypeError('fileobj must be file-like, not None')

        self.fileobj = fileobj

        if isinstance(dialect, text_type):
            dialect = get_dialect(dialect)

        try:
            self.dialect = Dialect.combine(dialect, fmtparams)
        except Error as e:
            raise TypeError(*e.args)

        strategies = {
            QUOTE_MINIMAL: QuoteMinimalStrategy,
            QUOTE_ALL: QuoteAllStrategy,
            QUOTE_NONNUMERIC: QuoteNonnumericStrategy,
            QUOTE_NONE: QuoteNoneStrategy,
        }
        self.strategy = strategies[self.dialect.quoting](self.dialect)

    def writerow(self, row):
        if row is None:
            raise Error('row must be an iterable')

        row = list(row)
        only = len(row) == 1
        row = [self.strategy.prepare(field, only=only) for field in row]

        line = self.dialect.delimiter.join(row) + self.dialect.lineterminator
        return self.fileobj.write(line)

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)


START_RECORD = 0
START_FIELD = 1
ESCAPED_CHAR = 2
IN_FIELD = 3
IN_QUOTED_FIELD = 4
ESCAPE_IN_QUOTED_FIELD = 5
QUOTE_IN_QUOTED_FIELD = 6
EAT_CRNL = 7
AFTER_ESCAPED_CRNL = 8


class reader(object):
    def __init__(self, fileobj, dialect='excel', **fmtparams):
        self.input_iter = iter(fileobj)

        if isinstance(dialect, text_type):
            dialect = get_dialect(dialect)

        try:
            self.dialect = Dialect.combine(dialect, fmtparams)
        except Error as e:
            raise TypeError(*e.args)

        self.fields = None
        self.field = None
        self.line_num = 0

    def parse_reset(self):
        self.fields = []
        self.field = []
        self.state = START_RECORD
        self.numeric_field = False

    def parse_save_field(self):
        field = ''.join(self.field)
        self.field = []
        if self.numeric_field:
            field = float(field)
            self.numeric_field = False
        self.fields.append(field)

    def parse_add_char(self, c):
        if len(self.field) >= field_size_limit():
            raise Error('field size limit exceeded')
        self.field.append(c)

    def parse_process_char(self, c):
        switch = {
            START_RECORD: self._parse_start_record,
            START_FIELD: self._parse_start_field,
            ESCAPED_CHAR: self._parse_escaped_char,
            AFTER_ESCAPED_CRNL: self._parse_after_escaped_crnl,
            IN_FIELD: self._parse_in_field,
            IN_QUOTED_FIELD: self._parse_in_quoted_field,
            ESCAPE_IN_QUOTED_FIELD: self._parse_escape_in_quoted_field,
            QUOTE_IN_QUOTED_FIELD: self._parse_quote_in_quoted_field,
            EAT_CRNL: self._parse_eat_crnl,
        }
        return switch[self.state](c)

    def _parse_start_record(self, c):
        if c == '\0':
            return
        elif c == '\n' or c == '\r':
            self.state = EAT_CRNL
            return

        self.state = START_FIELD
        return self._parse_start_field(c)

    def _parse_start_field(self, c):
        if c == '\n' or c == '\r' or c == '\0':
            self.parse_save_field()
            self.state = START_RECORD if c == '\0' else EAT_CRNL
        elif (c == self.dialect.quotechar and
              self.dialect.quoting != QUOTE_NONE):
            self.state = IN_QUOTED_FIELD
        elif c == self.dialect.escapechar:
            self.state = ESCAPED_CHAR
        elif c == ' ' and self.dialect.skipinitialspace:
            pass  # Ignore space at start of field
        elif c == self.dialect.delimiter:
            # Save empty field
            self.parse_save_field()
        else:
            # Begin new unquoted field
            if self.dialect.quoting == QUOTE_NONNUMERIC:
                self.numeric_field = True
            self.parse_add_char(c)
            self.state = IN_FIELD

    def _parse_escaped_char(self, c):
        if c == '\n' or c == '\r':
            self.parse_add_char(c)
            self.state = AFTER_ESCAPED_CRNL
            return
        if c == '\0':
            c = '\n'
        self.parse_add_char(c)
        self.state = IN_FIELD

    def _parse_after_escaped_crnl(self, c):
        if c == '\0':
            return
        return self._parse_in_field(c)

    def _parse_in_field(self, c):
        # In unquoted field
        if c == '\n' or c == '\r' or c == '\0':
            # End of line - return [fields]
            self.parse_save_field()
            self.state = START_RECORD if c == '\0' else EAT_CRNL
        elif c == self.dialect.escapechar:
            self.state = ESCAPED_CHAR
        elif c == self.dialect.delimiter:
            self.parse_save_field()
            self.state = START_FIELD
        else:
            # Normal character - save in field
            self.parse_add_char(c)

    def _parse_in_quoted_field(self, c):
        if c == '\0':
            pass
        elif c == self.dialect.escapechar:
            self.state = ESCAPE_IN_QUOTED_FIELD
        elif (c == self.dialect.quotechar and
              self.dialect.quoting != QUOTE_NONE):
            if self.dialect.doublequote:
                self.state = QUOTE_IN_QUOTED_FIELD
            else:
                self.state = IN_FIELD
        else:
            self.parse_add_char(c)

    def _parse_escape_in_quoted_field(self, c):
        if c == '\0':
            c = '\n'

        self.parse_add_char(c)
        self.state = IN_QUOTED_FIELD

    def _parse_quote_in_quoted_field(self, c):
        if (self.dialect.quoting != QUOTE_NONE and
                c == self.dialect.quotechar):
            # save "" as "
            self.parse_add_char(c)
            self.state = IN_QUOTED_FIELD
        elif c == self.dialect.delimiter:
            self.parse_save_field()
            self.state = START_FIELD
        elif c == '\n' or c == '\r' or c == '\0':
            # End of line = return [fields]
            self.parse_save_field()
            self.state = START_RECORD if c == '\0' else EAT_CRNL
        elif not self.dialect.strict:
            self.parse_add_char(c)
            self.state = IN_FIELD
        else:
            # illegal
            raise Error("{delimiter}' expected after '{quotechar}".format(
                delimiter=self.dialect.delimiter,
                quotechar=self.dialect.quotechar,
            ))

    def _parse_eat_crnl(self, c):
        if c == '\n' or c == '\r':
            pass
        elif c == '\0':
            self.state = START_RECORD
        else:
            raise Error('new-line character seen in unquoted field - do you '
                        'need to open the file in universal-newline mode?')


    def __iter__(self):
        return self

    def __next__(self):
        self.parse_reset()

        while True:
            try:
                lineobj = next(self.input_iter)
            except StopIteration:
                if len(self.field) != 0 or self.state == IN_QUOTED_FIELD:
                    if self.dialect.strict:
                        raise Error('unexpected end of data')
                    self.parse_save_field()
                if self.fields:
                    break
                raise

            if not isinstance(lineobj, text_type):
                typ = type(lineobj)
                typ_name = 'bytes' if typ == bytes else typ.__name__
                err_str = ('iterator should return strings, not {0}'
                           ' (did you open the file in text mode?)')
                raise Error(err_str.format(typ_name))

            self.line_num += 1
            for c in lineobj:
                if c == '\0':
                    raise Error('line contains NULL byte')
                self.parse_process_char(c)

            self.parse_process_char('\0')

            if self.state == START_RECORD:
                break

        fields = self.fields
        self.fields = None
        return fields

    next = __next__


_dialect_registry = {}
def register_dialect(name, dialect='excel', **fmtparams):
    if not isinstance(name, text_type):
        raise TypeError('"name" must be a string')

    dialect = Dialect.extend(dialect, fmtparams)

    try:
        Dialect.validate(dialect)
    except:
        raise TypeError('dialect is invalid')

    assert name not in _dialect_registry
    _dialect_registry[name] = dialect

def unregister_dialect(name):
    try:
        _dialect_registry.pop(name)
    except KeyError:
        raise Error('"{name}" not a registered dialect'.format(name=name))

def get_dialect(name):
    try:
        return _dialect_registry[name]
    except KeyError:
        raise Error('Could not find dialect {0}'.format(name))

def list_dialects():
    return list(_dialect_registry)


class Dialect(object):
    """Describe a CSV dialect.
    This must be subclassed (see csv.excel).  Valid attributes are:
    delimiter, quotechar, escapechar, doublequote, skipinitialspace,
    lineterminator, quoting, strict.
    """
    _name = ""
    _valid = False
    # placeholders
    delimiter = None
    quotechar = None
    escapechar = None
    doublequote = None
    skipinitialspace = None
    lineterminator = None
    quoting = None
    strict = None

    def __init__(self):
        self.validate(self)
        if self.__class__ != Dialect:
            self._valid = True

    @classmethod
    def validate(cls, dialect):
        dialect = cls.extend(dialect)

        if not isinstance(dialect.quoting, int):
            raise Error('"quoting" must be an integer')

        if dialect.delimiter is None:
            raise Error('delimiter must be set')
        cls.validate_text(dialect, 'delimiter')

        if dialect.lineterminator is None:
            raise Error('lineterminator must be set')
        if not isinstance(dialect.lineterminator, text_type):
            raise Error('"lineterminator" must be a string')

        if dialect.quoting not in [
                QUOTE_NONE, QUOTE_MINIMAL, QUOTE_NONNUMERIC, QUOTE_ALL]:
            raise Error('Invalid quoting specified')

        if dialect.quoting != QUOTE_NONE:
            if dialect.quotechar is None and dialect.escapechar is None:
                raise Error('quotechar must be set if quoting enabled')
            if dialect.quotechar is not None:
                cls.validate_text(dialect, 'quotechar')

    @staticmethod
    def validate_text(dialect, attr):
        val = getattr(dialect, attr)
        if not isinstance(val, text_type):
            if type(val) == bytes:
                raise Error('"{0}" must be string, not bytes'.format(attr))
            raise Error('"{0}" must be string, not {1}'.format(
                attr, type(val).__name__))

        if len(val) != 1:
            raise Error('"{0}" must be a 1-character string'.format(attr))

    @staticmethod
    def defaults():
        return {
            'delimiter': ',',
            'doublequote': True,
            'escapechar': None,
            'lineterminator': '\r\n',
            'quotechar': '"',
            'quoting': QUOTE_MINIMAL,
            'skipinitialspace': False,
            'strict': False,
        }

    @classmethod
    def extend(cls, dialect, fmtparams=None):
        if isinstance(dialect, string_types):
            dialect = get_dialect(dialect)

        if fmtparams is None:
            return dialect

        defaults = cls.defaults()

        if any(param not in defaults for param in fmtparams):
            raise TypeError('Invalid fmtparam')

        specified = dict(
            (attr, getattr(dialect, attr, None))
            for attr in cls.defaults()
        )

        specified.update(fmtparams)
        return type(str('ExtendedDialect'), (cls,), specified)

    @classmethod
    def combine(cls, dialect, fmtparams):
        """Create a new dialect with defaults and added parameters."""
        dialect = cls.extend(dialect, fmtparams)
        defaults = cls.defaults()
        specified = dict(
            (attr, getattr(dialect, attr, None))
            for attr in defaults
            if getattr(dialect, attr, None) is not None or
                attr in ['quotechar', 'delimiter', 'lineterminator', 'quoting']
        )

        defaults.update(specified)
        dialect = type(str('CombinedDialect'), (cls,), defaults)
        cls.validate(dialect)
        return dialect()

    def __delattr__(self, attr):
        if self._valid:
            raise AttributeError('dialect is immutable.')
        super(Dialect, self).__delattr__(attr)

    def __setattr__(self, attr, value):
        if self._valid:
            raise AttributeError('dialect is immutable.')
        super(Dialect, self).__setattr__(attr, value)


class excel(Dialect):
    """Describe the usual properties of Excel-generated CSV files."""
    delimiter = ','
    quotechar = '"'
    doublequote = True
    skipinitialspace = False
    lineterminator = '\r\n'
    quoting = QUOTE_MINIMAL
register_dialect("excel", excel)

class excel_tab(excel):
    """Describe the usual properties of Excel-generated TAB-delimited files."""
    delimiter = '\t'
register_dialect("excel-tab", excel_tab)

class unix_dialect(Dialect):
    """Describe the usual properties of Unix-generated CSV files."""
    delimiter = ','
    quotechar = '"'
    doublequote = True
    skipinitialspace = False
    lineterminator = '\n'
    quoting = QUOTE_ALL
register_dialect("unix", unix_dialect)


class DictReader(object):
    def __init__(self, f, fieldnames=None, restkey=None, restval=None,
                 dialect="excel", *args, **kwds):
        self._fieldnames = fieldnames   # list of keys for the dict
        self.restkey = restkey          # key to catch long rows
        self.restval = restval          # default value for short rows
        self.reader = reader(f, dialect, *args, **kwds)
        self.dialect = dialect
        self.line_num = 0

    def __iter__(self):
        return self

    @property
    def fieldnames(self):
        if self._fieldnames is None:
            try:
                self._fieldnames = next(self.reader)
            except StopIteration:
                pass
        self.line_num = self.reader.line_num
        return self._fieldnames

    @fieldnames.setter
    def fieldnames(self, value):
        self._fieldnames = value

    def __next__(self):
        if self.line_num == 0:
            # Used only for its side effect.
            self.fieldnames
        row = next(self.reader)
        self.line_num = self.reader.line_num

        # unlike the basic reader, we prefer not to return blanks,
        # because we will typically wind up with a dict full of None
        # values
        while row == []:
            row = next(self.reader)
        d = dict(zip(self.fieldnames, row))
        lf = len(self.fieldnames)
        lr = len(row)
        if lf < lr:
            d[self.restkey] = row[lf:]
        elif lf > lr:
            for key in self.fieldnames[lr:]:
                d[key] = self.restval
        return d

    next = __next__


class DictWriter(object):
    def __init__(self, f, fieldnames, restval="", extrasaction="raise",
                 dialect="excel", *args, **kwds):
        self.fieldnames = fieldnames    # list of keys for the dict
        self.restval = restval          # for writing short dicts
        if extrasaction.lower() not in ("raise", "ignore"):
            raise ValueError("extrasaction (%s) must be 'raise' or 'ignore'"
                             % extrasaction)
        self.extrasaction = extrasaction
        self.writer = writer(f, dialect, *args, **kwds)

    def writeheader(self):
        header = dict(zip(self.fieldnames, self.fieldnames))
        self.writerow(header)

    def _dict_to_list(self, rowdict):
        if self.extrasaction == "raise":
            wrong_fields = [k for k in rowdict if k not in self.fieldnames]
            if wrong_fields:
                raise ValueError("dict contains fields not in fieldnames: "
                                 + ", ".join([repr(x) for x in wrong_fields]))
        return (rowdict.get(key, self.restval) for key in self.fieldnames)

    def writerow(self, rowdict):
        return self.writer.writerow(self._dict_to_list(rowdict))

    def writerows(self, rowdicts):
        return self.writer.writerows(map(self._dict_to_list, rowdicts))

# Guard Sniffer's type checking against builds that exclude complex()
try:
    complex
except NameError:
    complex = float

class Sniffer(object):
    '''
    "Sniffs" the format of a CSV file (i.e. delimiter, quotechar)
    Returns a Dialect object.
    '''
    def __init__(self):
        # in case there is more than one possible delimiter
        self.preferred = [',', '\t', ';', ' ', ':']


    def sniff(self, sample, delimiters=None):
        """
        Returns a dialect (or None) corresponding to the sample
        """

        quotechar, doublequote, delimiter, skipinitialspace = \
                   self._guess_quote_and_delimiter(sample, delimiters)
        if not delimiter:
            delimiter, skipinitialspace = self._guess_delimiter(sample,
                                                                delimiters)

        if not delimiter:
            raise Error("Could not determine delimiter")

        class dialect(Dialect):
            _name = "sniffed"
            lineterminator = '\r\n'
            quoting = QUOTE_MINIMAL
            # escapechar = ''

        dialect.doublequote = doublequote
        dialect.delimiter = delimiter
        # _csv.reader won't accept a quotechar of ''
        dialect.quotechar = quotechar or '"'
        dialect.skipinitialspace = skipinitialspace

        return dialect


    def _guess_quote_and_delimiter(self, data, delimiters):
        """
        Looks for text enclosed between two identical quotes
        (the probable quotechar) which are preceded and followed
        by the same character (the probable delimiter).
        For example:
                         ,'some text',
        The quote with the most wins, same with the delimiter.
        If there is no quotechar the delimiter can't be determined
        this way.
        """

        matches = []
        for restr in ('(?P<delim>[^\w\n"\'])(?P<space> ?)(?P<quote>["\']).*?(?P=quote)(?P=delim)', # ,".*?",
                      '(?:^|\n)(?P<quote>["\']).*?(?P=quote)(?P<delim>[^\w\n"\'])(?P<space> ?)',   #  ".*?",
                      '(?P<delim>>[^\w\n"\'])(?P<space> ?)(?P<quote>["\']).*?(?P=quote)(?:$|\n)',  # ,".*?"
                      '(?:^|\n)(?P<quote>["\']).*?(?P=quote)(?:$|\n)'):                            #  ".*?" (no delim, no space)
            regexp = re.compile(restr, re.DOTALL | re.MULTILINE)
            matches = regexp.findall(data)
            if matches:
                break

        if not matches:
            # (quotechar, doublequote, delimiter, skipinitialspace)
            return ('', False, None, 0)
        quotes = {}
        delims = {}
        spaces = 0
        groupindex = regexp.groupindex
        for m in matches:
            n = groupindex['quote'] - 1
            key = m[n]
            if key:
                quotes[key] = quotes.get(key, 0) + 1
            try:
                n = groupindex['delim'] - 1
                key = m[n]
            except KeyError:
                continue
            if key and (delimiters is None or key in delimiters):
                delims[key] = delims.get(key, 0) + 1
            try:
                n = groupindex['space'] - 1
            except KeyError:
                continue
            if m[n]:
                spaces += 1

        quotechar = max(quotes, key=quotes.get)

        if delims:
            delim = max(delims, key=delims.get)
            skipinitialspace = delims[delim] == spaces
            if delim == '\n': # most likely a file with a single column
                delim = ''
        else:
            # there is *no* delimiter, it's a single column of quoted data
            delim = ''
            skipinitialspace = 0

        # if we see an extra quote between delimiters, we've got a
        # double quoted format
        dq_regexp = re.compile(
                               r"((%(delim)s)|^)\W*%(quote)s[^%(delim)s\n]*%(quote)s[^%(delim)s\n]*%(quote)s\W*((%(delim)s)|$)" % \
                               {'delim':re.escape(delim), 'quote':quotechar}, re.MULTILINE)



        if dq_regexp.search(data):
            doublequote = True
        else:
            doublequote = False

        return (quotechar, doublequote, delim, skipinitialspace)


    def _guess_delimiter(self, data, delimiters):
        """
        The delimiter /should/ occur the same number of times on
        each row. However, due to malformed data, it may not. We don't want
        an all or nothing approach, so we allow for small variations in this
        number.
          1) build a table of the frequency of each character on every line.
          2) build a table of frequencies of this frequency (meta-frequency?),
             e.g.  'x occurred 5 times in 10 rows, 6 times in 1000 rows,
             7 times in 2 rows'
          3) use the mode of the meta-frequency to determine the /expected/
             frequency for that character
          4) find out how often the character actually meets that goal
          5) the character that best meets its goal is the delimiter
        For performance reasons, the data is evaluated in chunks, so it can
        try and evaluate the smallest portion of the data possible, evaluating
        additional chunks as necessary.
        """

        data = list(filter(None, data.split('\n')))

        ascii = [unichr(c) for c in range(127)] # 7-bit ASCII

        # build frequency tables
        chunkLength = min(10, len(data))
        iteration = 0
        charFrequency = {}
        modes = {}
        delims = {}
        start, end = 0, min(chunkLength, len(data))
        while start < len(data):
            iteration += 1
            for line in data[start:end]:
                for char in ascii:
                    metaFrequency = charFrequency.get(char, {})
                    # must count even if frequency is 0
                    freq = line.count(char)
                    # value is the mode
                    metaFrequency[freq] = metaFrequency.get(freq, 0) + 1
                    charFrequency[char] = metaFrequency

            for char in charFrequency.keys():
                items = list(charFrequency[char].items())
                if len(items) == 1 and items[0][0] == 0:
                    continue
                # get the mode of the frequencies
                if len(items) > 1:
                    modes[char] = max(items, key=lambda x: x[1])
                    # adjust the mode - subtract the sum of all
                    # other frequencies
                    items.remove(modes[char])
                    modes[char] = (modes[char][0], modes[char][1]
                                   - sum(item[1] for item in items))
                else:
                    modes[char] = items[0]

            # build a list of possible delimiters
            modeList = modes.items()
            total = float(chunkLength * iteration)
            # (rows of consistent data) / (number of rows) = 100%
            consistency = 1.0
            # minimum consistency threshold
            threshold = 0.9
            while len(delims) == 0 and consistency >= threshold:
                for k, v in modeList:
                    if v[0] > 0 and v[1] > 0:
                        if ((v[1]/total) >= consistency and
                            (delimiters is None or k in delimiters)):
                            delims[k] = v
                consistency -= 0.01

            if len(delims) == 1:
                delim = list(delims.keys())[0]
                skipinitialspace = (data[0].count(delim) ==
                                    data[0].count("%c " % delim))
                return (delim, skipinitialspace)

            # analyze another chunkLength lines
            start = end
            end += chunkLength

        if not delims:
            return ('', 0)

        # if there's more than one, fall back to a 'preferred' list
        if len(delims) > 1:
            for d in self.preferred:
                if d in delims.keys():
                    skipinitialspace = (data[0].count(d) ==
                                        data[0].count("%c " % d))
                    return (d, skipinitialspace)

        # nothing else indicates a preference, pick the character that
        # dominates(?)
        items = [(v,k) for (k,v) in delims.items()]
        items.sort()
        delim = items[-1][1]

        skipinitialspace = (data[0].count(delim) ==
                            data[0].count("%c " % delim))
        return (delim, skipinitialspace)


    def has_header(self, sample):
        # Creates a dictionary of types of data in each column. If any
        # column is of a single type (say, integers), *except* for the first
        # row, then the first row is presumed to be labels. If the type
        # can't be determined, it is assumed to be a string in which case
        # the length of the string is the determining factor: if all of the
        # rows except for the first are the same length, it's a header.
        # Finally, a 'vote' is taken at the end for each column, adding or
        # subtracting from the likelihood of the first row being a header.

        rdr = reader(StringIO(sample), self.sniff(sample))

        header = next(rdr) # assume first row is header

        columns = len(header)
        columnTypes = {}
        for i in range(columns): columnTypes[i] = None

        checked = 0
        for row in rdr:
            # arbitrary number of rows to check, to keep it sane
            if checked > 20:
                break
            checked += 1

            if len(row) != columns:
                continue # skip rows that have irregular number of columns

            for col in list(columnTypes.keys()):

                for thisType in [int, float, complex]:
                    try:
                        thisType(row[col])
                        break
                    except (ValueError, OverflowError):
                        pass
                else:
                    # fallback to length of string
                    thisType = len(row[col])

                if thisType != columnTypes[col]:
                    if columnTypes[col] is None: # add new column type
                        columnTypes[col] = thisType
                    else:
                        # type is inconsistent, remove column from
                        # consideration
                        del columnTypes[col]

        # finally, compare results against first row and "vote"
        # on whether it's a header
        hasHeader = 0
        for col, colType in columnTypes.items():
            if type(colType) == type(0): # it's a length
                if len(header[col]) != colType:
                    hasHeader += 1
                else:
                    hasHeader -= 1
            else: # attempt typecast
                try:
                    colType(header[col])
                except (ValueError, TypeError):
                    hasHeader += 1
                else:
                    hasHeader -= 1

        return hasHeader > 0
