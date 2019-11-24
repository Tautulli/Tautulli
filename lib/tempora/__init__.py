# -*- coding: UTF-8 -*-

"Objects and routines pertaining to date and time (tempora)"

from __future__ import division, unicode_literals

import datetime
import time
import re
import numbers
import functools

import six

__metaclass__ = type


class Parser:
	"""
	Datetime parser: parses a date-time string using multiple possible
	formats.

	>>> p = Parser(('%H%M', '%H:%M'))
	>>> tuple(p.parse('1319'))
	(1900, 1, 1, 13, 19, 0, 0, 1, -1)
	>>> dateParser = Parser(('%m/%d/%Y', '%Y-%m-%d', '%d-%b-%Y'))
	>>> tuple(dateParser.parse('2003-12-20'))
	(2003, 12, 20, 0, 0, 0, 5, 354, -1)
	>>> tuple(dateParser.parse('16-Dec-1994'))
	(1994, 12, 16, 0, 0, 0, 4, 350, -1)
	>>> tuple(dateParser.parse('5/19/2003'))
	(2003, 5, 19, 0, 0, 0, 0, 139, -1)
	>>> dtParser = Parser(('%Y-%m-%d %H:%M:%S', '%a %b %d %H:%M:%S %Y'))
	>>> tuple(dtParser.parse('2003-12-20 19:13:26'))
	(2003, 12, 20, 19, 13, 26, 5, 354, -1)
	>>> tuple(dtParser.parse('Tue Jan 20 16:19:33 2004'))
	(2004, 1, 20, 16, 19, 33, 1, 20, -1)

	Be forewarned, a ValueError will be raised if more than one format
	matches:

	>>> Parser(('%H%M', '%H%M%S')).parse('732')
	Traceback (most recent call last):
		...
	ValueError: More than one format string matched target 732.
	"""

	formats = ('%m/%d/%Y', '%m/%d/%y', '%Y-%m-%d', '%d-%b-%Y', '%d-%b-%y')
	"some common default formats"

	def __init__(self, formats=None):
		if formats:
			self.formats = formats

	def parse(self, target):
		self.target = target
		results = tuple(filter(None, map(self._parse, self.formats)))
		del self.target
		if not results:
			tmpl = "No format strings matched the target {target}."
			raise ValueError(tmpl.format(**locals()))
		if not len(results) == 1:
			tmpl = "More than one format string matched target {target}."
			raise ValueError(tmpl.format(**locals()))
		return results[0]

	def _parse(self, format):
		try:
			result = time.strptime(self.target, format)
		except ValueError:
			result = False
		return result


# some useful constants
osc_per_year = 290091329207984000
"""
mean vernal equinox year expressed in oscillations of atomic cesium at the
year 2000 (see http://webexhibits.org/calendars/timeline.html for more info).
"""
osc_per_second = 9192631770
seconds_per_second = 1
seconds_per_year = 31556940
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


def strftime(fmt, t):
	"""A class to replace the strftime in datetime package or time module.
	Identical to strftime behavior in those modules except supports any
	year.
	Also supports datetime.datetime times.
	Also supports milliseconds using %s
	Also supports microseconds using %u"""
	if isinstance(t, (time.struct_time, tuple)):
		t = datetime.datetime(*t[:6])
	assert isinstance(t, (datetime.datetime, datetime.time, datetime.date))
	try:
		year = t.year
		if year < 1900:
			t = t.replace(year=1900)
	except AttributeError:
		year = 1900
	subs = (
		('%Y', '%04d' % year),
		('%y', '%02d' % (year % 100)),
		('%s', '%03d' % (t.microsecond // 1000)),
		('%u', '%03d' % (t.microsecond % 1000))
	)

	def doSub(s, sub):
		return s.replace(*sub)

	def doSubs(s):
		return functools.reduce(doSub, subs, s)

	fmt = '%%'.join(map(doSubs, fmt.split('%%')))
	return t.strftime(fmt)


def strptime(s, fmt, tzinfo=None):
	"""
	A function to replace strptime in the time module.  Should behave
	identically to the strptime function except it returns a datetime.datetime
	object instead of a time.struct_time object.
	Also takes an optional tzinfo parameter which is a time zone info object.
	"""
	res = time.strptime(s, fmt)
	return datetime.datetime(tzinfo=tzinfo, *res[:6])


class DatetimeConstructor:
	"""
	>>> cd = DatetimeConstructor.construct_datetime
	>>> cd(datetime.datetime(2011,1,1))
	datetime.datetime(2011, 1, 1, 0, 0)
	"""
	@classmethod
	def construct_datetime(cls, *args, **kwargs):
		"""Construct a datetime.datetime from a number of different time
		types found in python and pythonwin"""
		if len(args) == 1:
			arg = args[0]
			method = cls.__get_dt_constructor(
				type(arg).__module__,
				type(arg).__name__,
			)
			result = method(arg)
			try:
				result = result.replace(tzinfo=kwargs.pop('tzinfo'))
			except KeyError:
				pass
			if kwargs:
				first_key = kwargs.keys()[0]
				tmpl = (
					"{first_key} is an invalid keyword "
					"argument for this function."
				)
				raise TypeError(tmpl.format(**locals()))
		else:
			result = datetime.datetime(*args, **kwargs)
		return result

	@classmethod
	def __get_dt_constructor(cls, moduleName, name):
		try:
			method_name = '__dt_from_{moduleName}_{name}__'.format(**locals())
			return getattr(cls, method_name)
		except AttributeError:
			tmpl = (
				"No way to construct datetime.datetime from "
				"{moduleName}.{name}"
			)
			raise TypeError(tmpl.format(**locals()))

	@staticmethod
	def __dt_from_datetime_datetime__(source):
		dtattrs = (
			'year', 'month', 'day', 'hour', 'minute', 'second',
			'microsecond', 'tzinfo',
		)
		attrs = map(lambda a: getattr(source, a), dtattrs)
		return datetime.datetime(*attrs)

	@staticmethod
	def __dt_from___builtin___time__(pyt):
		"Construct a datetime.datetime from a pythonwin time"
		fmtString = '%Y-%m-%d %H:%M:%S'
		result = strptime(pyt.Format(fmtString), fmtString)
		# get milliseconds and microseconds.  The only way to do this is
		#  to use the __float__ attribute of the time, which is in days.
		microseconds_per_day = seconds_per_day * 1000000
		microseconds = float(pyt) * microseconds_per_day
		microsecond = int(microseconds % 1000000)
		result = result.replace(microsecond=microsecond)
		return result

	@staticmethod
	def __dt_from_timestamp__(timestamp):
		return datetime.datetime.utcfromtimestamp(timestamp)
	__dt_from___builtin___float__ = __dt_from_timestamp__
	__dt_from___builtin___long__ = __dt_from_timestamp__
	__dt_from___builtin___int__ = __dt_from_timestamp__

	@staticmethod
	def __dt_from_time_struct_time__(s):
		return datetime.datetime(*s[:6])


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
	if isinstance(period, six.string_types):
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
	if isinstance(period, six.string_types) and period.lower() == 'month':
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


def divide_timedelta_float(td, divisor):
	"""
	Divide a timedelta by a float value

	>>> one_day = datetime.timedelta(days=1)
	>>> half_day = datetime.timedelta(days=.5)
	>>> divide_timedelta_float(one_day, 2.0) == half_day
	True
	>>> divide_timedelta_float(one_day, 2) == half_day
	True
	"""
	# td is comprised of days, seconds, microseconds
	dsm = [getattr(td, attr) for attr in ('days', 'seconds', 'microseconds')]
	dsm = map(lambda elem: elem / divisor, dsm)
	return datetime.timedelta(*dsm)


def calculate_prorated_values():
	"""
	A utility function to prompt for a rate (a string in units per
	unit time), and return that same rate for various time periods.
	"""
	rate = six.moves.input("Enter the rate (3/hour, 50/month)> ")
	res = re.match(r'(?P<value>[\d.]+)/(?P<period>\w+)$', rate).groupdict()
	value = float(res['value'])
	value_per_second = value / get_period_seconds(res['period'])
	for period in ('minute', 'hour', 'day', 'month', 'year'):
		period_value = value_per_second * get_period_seconds(period)
		print("per {period}: {period_value}".format(**locals()))


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
	"""
	deltas = (_parse_timedelta_part(part.strip()) for part in str.split(','))
	return sum(deltas, datetime.timedelta())


def _parse_timedelta_part(part):
	match = re.match(r'(?P<value>[\d.]+) (?P<unit>\w+)', part)
	if not match:
		msg = "Unable to parse {part!r} as a time delta".format(**locals())
		raise ValueError(msg)
	unit = match.group('unit').lower()
	if not unit.endswith('s'):
		unit += 's'
	value = float(match.group('value'))
	if unit == 'months':
		unit = 'years'
		value = value / 12
	if unit == 'years':
		unit = 'days'
		value = value * days_per_year
	return datetime.timedelta(**{unit: value})


def divide_timedelta(td1, td2):
	"""
	Get the ratio of two timedeltas

	>>> one_day = datetime.timedelta(days=1)
	>>> one_hour = datetime.timedelta(hours=1)
	>>> divide_timedelta(one_hour, one_day) == 1 / 24
	True
	"""
	try:
		return td1 / td2
	except TypeError:
		# Python 3.2 gets division
		# http://bugs.python.org/issue2706
		return td1.total_seconds() / td2.total_seconds()


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
	"""
	if step is None:
		step = datetime.timedelta(days=1)
	if start is None:
		start = datetime.datetime.now()
	while start < stop:
		yield start
		start += step
