"Objects and routines pertaining to date and time (tempora)"

import datetime
import time
import re
import numbers
import functools
import contextlib

from jaraco.functools import once


# some useful constants
osc_per_year = 290_091_329_207_984_000
"""
mean vernal equinox year expressed in oscillations of atomic cesium at the
year 2000 (see http://webexhibits.org/calendars/timeline.html for more info).
"""
osc_per_second = 9_192_631_770
seconds_per_second = 1
seconds_per_year = 31_556_940
seconds_per_minute = 60
minutes_per_hour = 60
hours_per_day = 24
seconds_per_hour = seconds_per_minute * minutes_per_hour
seconds_per_day = seconds_per_hour * hours_per_day
days_per_year = seconds_per_year / seconds_per_day
thirty_days = datetime.timedelta(days=30)
# these values provide useful averages
six_months = datetime.timedelta(days=days_per_year / 2)
seconds_per_month = seconds_per_year / 12
hours_per_month = hours_per_day * days_per_year / 12


@once
def _needs_year_help():
    """
    Some versions of Python render %Y with only three characters :(
    https://bugs.python.org/issue39103
    """
    return len(datetime.date(900, 1, 1).strftime('%Y')) != 4


def ensure_datetime(ob):
    """
    Given a datetime or date or time object from the ``datetime``
    module, always return a datetime using default values.
    """
    if isinstance(ob, datetime.datetime):
        return ob
    date = time = ob
    if isinstance(ob, datetime.date):
        time = datetime.time()
    if isinstance(ob, datetime.time):
        date = datetime.date(1900, 1, 1)
    return datetime.datetime.combine(date, time)


def strftime(fmt, t):
    """
    Portable strftime.

    In the stdlib, strftime has `known portability problems
    <https://bugs.python.org/issue13305>`_. This function
    aims to smooth over those issues and provide a
    consistent experience across the major platforms.

    >>> strftime('%Y', datetime.datetime(1890, 1, 1))
    '1890'
    >>> strftime('%Y', datetime.datetime(900, 1, 1))
    '0900'

    Supports time.struct_time, tuples, and datetime.datetime objects.

    >>> strftime('%Y-%m-%d', (1976, 5, 7))
    '1976-05-07'

    Also supports date objects

    >>> strftime('%Y', datetime.date(1976, 5, 7))
    '1976'

    Also supports milliseconds using %s.

    >>> strftime('%s', datetime.time(microsecond=20000))
    '020'

    Also supports microseconds (3 digits) using %µ

    >>> strftime('%µ', datetime.time(microsecond=123456))
    '456'

    Historically, %u was used for microseconds, but now
    it honors the value rendered by stdlib.

    >>> strftime('%u', datetime.date(1976, 5, 7))
    '5'

    Also supports microseconds (6 digits) using %f

    >>> strftime('%f', datetime.time(microsecond=23456))
    '023456'

    Even supports time values on date objects (discouraged):

    >>> strftime('%f', datetime.date(1976, 1, 1))
    '000000'
    >>> strftime('%µ', datetime.date(1976, 1, 1))
    '000'
    >>> strftime('%s', datetime.date(1976, 1, 1))
    '000'

    And vice-versa:

    >>> strftime('%Y', datetime.time())
    '1900'
    """
    if isinstance(t, (time.struct_time, tuple)):
        t = datetime.datetime(*t[:6])
    t = ensure_datetime(t)
    subs = (
        ('%s', '%03d' % (t.microsecond // 1000)),
        ('%µ', '%03d' % (t.microsecond % 1000)),
    )
    if _needs_year_help():  # pragma: nocover
        subs += (('%Y', '%04d' % t.year),)

    def doSub(s, sub):
        return s.replace(*sub)

    def doSubs(s):
        return functools.reduce(doSub, subs, s)

    fmt = '%%'.join(map(doSubs, fmt.split('%%')))
    return t.strftime(fmt)


def datetime_mod(dt, period, start=None):
    """
    Find the time which is the specified date/time truncated to the time delta
    relative to the start date/time.
    By default, the start time is midnight of the same day as the specified
    date/time.

    >>> datetime_mod(datetime.datetime(2004, 1, 2, 3),
    ...     datetime.timedelta(days = 1.5),
    ...     start = datetime.datetime(2004, 1, 1))
    datetime.datetime(2004, 1, 1, 0, 0)
    >>> datetime_mod(datetime.datetime(2004, 1, 2, 13),
    ...     datetime.timedelta(days = 1.5),
    ...     start = datetime.datetime(2004, 1, 1))
    datetime.datetime(2004, 1, 2, 12, 0)
    >>> datetime_mod(datetime.datetime(2004, 1, 2, 13),
    ...     datetime.timedelta(days = 7),
    ...     start = datetime.datetime(2004, 1, 1))
    datetime.datetime(2004, 1, 1, 0, 0)
    >>> datetime_mod(datetime.datetime(2004, 1, 10, 13),
    ...     datetime.timedelta(days = 7),
    ...     start = datetime.datetime(2004, 1, 1))
    datetime.datetime(2004, 1, 8, 0, 0)
    """
    if start is None:
        # use midnight of the same day
        start = datetime.datetime.combine(dt.date(), datetime.time())
    # calculate the difference between the specified time and the start date.
    delta = dt - start

    # now aggregate the delta and the period into microseconds
    # Use microseconds because that's the highest precision of these time
    # pieces.  Also, using microseconds ensures perfect precision (no floating
    # point errors).
    def get_time_delta_microseconds(td):
        return (td.days * seconds_per_day + td.seconds) * 1000000 + td.microseconds

    delta, period = map(get_time_delta_microseconds, (delta, period))
    offset = datetime.timedelta(microseconds=delta % period)
    # the result is the original specified time minus the offset
    result = dt - offset
    return result


def datetime_round(dt, period, start=None):
    """
    Find the nearest even period for the specified date/time.

    >>> datetime_round(datetime.datetime(2004, 11, 13, 8, 11, 13),
    ...     datetime.timedelta(hours = 1))
    datetime.datetime(2004, 11, 13, 8, 0)
    >>> datetime_round(datetime.datetime(2004, 11, 13, 8, 31, 13),
    ...     datetime.timedelta(hours = 1))
    datetime.datetime(2004, 11, 13, 9, 0)
    >>> datetime_round(datetime.datetime(2004, 11, 13, 8, 30),
    ...     datetime.timedelta(hours = 1))
    datetime.datetime(2004, 11, 13, 9, 0)
    """
    result = datetime_mod(dt, period, start)
    if abs(dt - result) >= period // 2:
        result += period
    return result


def get_nearest_year_for_day(day):
    """
    Returns the nearest year to now inferred from a Julian date.

    >>> freezer = getfixture('freezer')
    >>> freezer.move_to('2019-05-20')
    >>> get_nearest_year_for_day(20)
    2019
    >>> get_nearest_year_for_day(340)
    2018
    >>> freezer.move_to('2019-12-15')
    >>> get_nearest_year_for_day(20)
    2020
    """
    now = time.gmtime()
    result = now.tm_year
    # if the day is far greater than today, it must be from last year
    if day - now.tm_yday > 365 // 2:
        result -= 1
    # if the day is far less than today, it must be for next year.
    if now.tm_yday - day > 365 // 2:
        result += 1
    return result


def gregorian_date(year, julian_day):
    """
    Gregorian Date is defined as a year and a julian day (1-based
    index into the days of the year).

    >>> gregorian_date(2007, 15)
    datetime.date(2007, 1, 15)
    """
    result = datetime.date(year, 1, 1)
    result += datetime.timedelta(days=julian_day - 1)
    return result


def get_period_seconds(period):
    """
    return the number of seconds in the specified period

    >>> get_period_seconds('day')
    86400
    >>> get_period_seconds(86400)
    86400
    >>> get_period_seconds(datetime.timedelta(hours=24))
    86400
    >>> get_period_seconds('day + os.system("rm -Rf *")')
    Traceback (most recent call last):
    ...
    ValueError: period not in (second, minute, hour, day, month, year)
    """
    if isinstance(period, str):
        try:
            name = 'seconds_per_' + period.lower()
            result = globals()[name]
        except KeyError:
            msg = "period not in (second, minute, hour, day, month, year)"
            raise ValueError(msg)
    elif isinstance(period, numbers.Number):
        result = period
    elif isinstance(period, datetime.timedelta):
        result = period.days * get_period_seconds('day') + period.seconds
    else:
        raise TypeError('period must be a string or integer')
    return result


def get_date_format_string(period):
    """
    For a given period (e.g. 'month', 'day', or some numeric interval
    such as 3600 (in secs)), return the format string that can be
    used with strftime to format that time to specify the times
    across that interval, but no more detailed.
    For example,

    >>> get_date_format_string('month')
    '%Y-%m'
    >>> get_date_format_string(3600)
    '%Y-%m-%d %H'
    >>> get_date_format_string('hour')
    '%Y-%m-%d %H'
    >>> get_date_format_string(None)
    Traceback (most recent call last):
        ...
    TypeError: period must be a string or integer
    >>> get_date_format_string('garbage')
    Traceback (most recent call last):
        ...
    ValueError: period not in (second, minute, hour, day, month, year)
    """
    # handle the special case of 'month' which doesn't have
    #  a static interval in seconds
    if isinstance(period, str) and period.lower() == 'month':
        return '%Y-%m'
    file_period_secs = get_period_seconds(period)
    format_pieces = ('%Y', '-%m-%d', ' %H', '-%M', '-%S')
    seconds_per_second = 1
    intervals = (
        seconds_per_year,
        seconds_per_day,
        seconds_per_hour,
        seconds_per_minute,
        seconds_per_second,
    )
    mods = list(map(lambda interval: file_period_secs % interval, intervals))
    format_pieces = format_pieces[: mods.index(0) + 1]
    return ''.join(format_pieces)


def calculate_prorated_values():
    """
    >>> monkeypatch = getfixture('monkeypatch')
    >>> import builtins
    >>> monkeypatch.setattr(builtins, 'input', lambda prompt: '3/hour')
    >>> calculate_prorated_values()
    per minute: 0.05
    per hour: 3.0
    per day: 72.0
    per month: 2191.454166666667
    per year: 26297.45
    """
    rate = input("Enter the rate (3/hour, 50/month)> ")
    for period, value in _prorated_values(rate):
        print("per {period}: {value}".format(**locals()))


def _prorated_values(rate):
    """
    Given a rate (a string in units per unit time), and return that same
    rate for various time periods.

    >>> for period, value in _prorated_values('20/hour'):
    ...     print('{period}: {value:0.3f}'.format(**locals()))
    minute: 0.333
    hour: 20.000
    day: 480.000
    month: 14609.694
    year: 175316.333

    """
    res = re.match(r'(?P<value>[\d.]+)/(?P<period>\w+)$', rate).groupdict()
    value = float(res['value'])
    value_per_second = value / get_period_seconds(res['period'])
    for period in ('minute', 'hour', 'day', 'month', 'year'):
        period_value = value_per_second * get_period_seconds(period)
        yield period, period_value


def parse_timedelta(str):
    """
    Take a string representing a span of time and parse it to a time delta.
    Accepts any string of comma-separated numbers each with a unit indicator.

    >>> parse_timedelta('1 day')
    datetime.timedelta(days=1)

    >>> parse_timedelta('1 day, 30 seconds')
    datetime.timedelta(days=1, seconds=30)

    >>> parse_timedelta('47.32 days, 20 minutes, 15.4 milliseconds')
    datetime.timedelta(days=47, seconds=28848, microseconds=15400)

    Supports weeks, months, years

    >>> parse_timedelta('1 week')
    datetime.timedelta(days=7)

    >>> parse_timedelta('1 year, 1 month')
    datetime.timedelta(days=395, seconds=58685)

    Note that months and years strict intervals, not aligned
    to a calendar:

    >>> now = datetime.datetime.now()
    >>> later = now + parse_timedelta('1 year')
    >>> diff = later.replace(year=now.year) - now
    >>> diff.seconds
    20940

    >>> parse_timedelta('foo')
    Traceback (most recent call last):
    ...
    ValueError: Unexpected 'foo'

    >>> parse_timedelta('14 seconds foo')
    Traceback (most recent call last):
    ...
    ValueError: Unexpected 'foo'

    Supports abbreviations:

    >>> parse_timedelta('1s')
    datetime.timedelta(seconds=1)

    >>> parse_timedelta('1sec')
    datetime.timedelta(seconds=1)

    >>> parse_timedelta('5min1sec')
    datetime.timedelta(seconds=301)

    >>> parse_timedelta('1 ms')
    datetime.timedelta(microseconds=1000)

    >>> parse_timedelta('1 µs')
    datetime.timedelta(microseconds=1)

    >>> parse_timedelta('1 us')
    datetime.timedelta(microseconds=1)

    And supports the common colon-separated duration:

    >>> parse_timedelta('14:00:35.362')
    datetime.timedelta(seconds=50435, microseconds=362000)

    TODO: Should this be 14 hours or 14 minutes?

    >>> parse_timedelta('14:00')
    datetime.timedelta(seconds=50400)

    >>> parse_timedelta('14:00 minutes')
    Traceback (most recent call last):
    ...
    ValueError: Cannot specify units with composite delta

    Nanoseconds get rounded to the nearest microsecond:

    >>> parse_timedelta('600 ns')
    datetime.timedelta(microseconds=1)

    >>> parse_timedelta('.002 µs, 499 ns')
    datetime.timedelta(microseconds=1)

    Expect ValueError for other invalid inputs.

    >>> parse_timedelta('13 feet')
    Traceback (most recent call last):
    ...
    ValueError: Invalid unit feets
    """
    return _parse_timedelta_nanos(str).resolve()


def _parse_timedelta_nanos(str):
    parts = re.finditer(r'(?P<value>[\d.:]+)\s?(?P<unit>[^\W\d_]+)?', str)
    chk_parts = _check_unmatched(parts, str)
    deltas = map(_parse_timedelta_part, chk_parts)
    return sum(deltas, _Saved_NS())


def _check_unmatched(matches, text):
    """
    Ensure no words appear in unmatched text.
    """

    def check_unmatched(unmatched):
        found = re.search(r'\w+', unmatched)
        if found:
            raise ValueError(f"Unexpected {found.group(0)!r}")

    pos = 0
    for match in matches:
        check_unmatched(text[pos : match.start()])
        yield match
        pos = match.end()
    check_unmatched(text[pos:])


_unit_lookup = {
    'µs': 'microsecond',
    'µsec': 'microsecond',
    'us': 'microsecond',
    'usec': 'microsecond',
    'micros': 'microsecond',
    'ms': 'millisecond',
    'msec': 'millisecond',
    'millis': 'millisecond',
    's': 'second',
    'sec': 'second',
    'h': 'hour',
    'hr': 'hour',
    'm': 'minute',
    'min': 'minute',
    'w': 'week',
    'wk': 'week',
    'd': 'day',
    'ns': 'nanosecond',
    'nsec': 'nanosecond',
    'nanos': 'nanosecond',
}


def _resolve_unit(raw_match):
    if raw_match is None:
        return 'second'
    text = raw_match.lower()
    return _unit_lookup.get(text, text)


def _parse_timedelta_composite(raw_value, unit):
    if unit != 'seconds':
        raise ValueError("Cannot specify units with composite delta")
    values = raw_value.split(':')
    units = 'hours', 'minutes', 'seconds'
    composed = ' '.join(f'{value} {unit}' for value, unit in zip(values, units))
    return _parse_timedelta_nanos(composed)


def _parse_timedelta_part(match):
    unit = _resolve_unit(match.group('unit'))
    if not unit.endswith('s'):
        unit += 's'
    raw_value = match.group('value')
    if ':' in raw_value:
        return _parse_timedelta_composite(raw_value, unit)
    value = float(raw_value)
    if unit == 'months':
        unit = 'years'
        value = value / 12
    if unit == 'years':
        unit = 'days'
        value = value * days_per_year
    return _Saved_NS.derive(unit, value)


class _Saved_NS:
    """
    Bundle a timedelta with nanoseconds.

    >>> _Saved_NS.derive('microseconds', .001)
    _Saved_NS(td=datetime.timedelta(0), nanoseconds=1)
    """

    td = datetime.timedelta()
    nanoseconds = 0
    multiplier = dict(
        seconds=1000000000,
        milliseconds=1000000,
        microseconds=1000,
    )

    def __init__(self, **kwargs):
        vars(self).update(kwargs)

    @classmethod
    def derive(cls, unit, value):
        if unit == 'nanoseconds':
            return _Saved_NS(nanoseconds=value)

        try:
            raw_td = datetime.timedelta(**{unit: value})
        except TypeError:
            raise ValueError(f"Invalid unit {unit}")
        res = _Saved_NS(td=raw_td)
        with contextlib.suppress(KeyError):
            res.nanoseconds = int(value * cls.multiplier[unit]) % 1000
        return res

    def __add__(self, other):
        return _Saved_NS(
            td=self.td + other.td, nanoseconds=self.nanoseconds + other.nanoseconds
        )

    def resolve(self):
        """
        Resolve any nanoseconds into the microseconds field,
        discarding any nanosecond resolution (but honoring partial
        microseconds).
        """
        addl_micros = round(self.nanoseconds / 1000)
        return self.td + datetime.timedelta(microseconds=addl_micros)

    def __repr__(self):
        return f'_Saved_NS(td={self.td!r}, nanoseconds={self.nanoseconds!r})'


def date_range(start=None, stop=None, step=None):
    """
    Much like the built-in function range, but works with dates

    >>> range_items = date_range(
    ...     datetime.datetime(2005,12,21),
    ...     datetime.datetime(2005,12,25),
    ... )
    >>> my_range = tuple(range_items)
    >>> datetime.datetime(2005,12,21) in my_range
    True
    >>> datetime.datetime(2005,12,22) in my_range
    True
    >>> datetime.datetime(2005,12,25) in my_range
    False
    >>> from_now = date_range(stop=datetime.datetime(2099, 12, 31))
    >>> next(from_now)
    datetime.datetime(...)
    """
    if step is None:
        step = datetime.timedelta(days=1)
    if start is None:
        start = datetime.datetime.now()
    while start < stop:
        yield start
        start += step
