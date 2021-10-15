"""
Classes for calling functions a schedule. Has time zone support.

For example, to run a job at 08:00 every morning in 'Asia/Calcutta':

>>> job = lambda: print("time is now", datetime.datetime())
>>> time = datetime.time(8, tzinfo=pytz.timezone('Asia/Calcutta'))
>>> cmd = PeriodicCommandFixedDelay.daily_at(time, job)
>>> sched = InvokeScheduler()
>>> sched.add(cmd)
>>> while True:  # doctest: +SKIP
...     sched.run_pending()
...     time.sleep(.1)
"""

import datetime
import numbers
import abc
import bisect

import pytz


def now():
    """
    Provide the current timezone-aware datetime.

    A client may override this function to change the default behavior,
    such as to use local time or timezone-naïve times.
    """
    return datetime.datetime.utcnow().replace(tzinfo=pytz.utc)


def from_timestamp(ts):
    """
    Convert a numeric timestamp to a timezone-aware datetime.

    A client may override this function to change the default behavior,
    such as to use local time or timezone-naïve times.
    """
    return datetime.datetime.utcfromtimestamp(ts).replace(tzinfo=pytz.utc)


class DelayedCommand(datetime.datetime):
    """
    A command to be executed after some delay (seconds or timedelta).
    """

    @classmethod
    def from_datetime(cls, other):
        return cls(
            other.year,
            other.month,
            other.day,
            other.hour,
            other.minute,
            other.second,
            other.microsecond,
            other.tzinfo,
        )

    @classmethod
    def after(cls, delay, target):
        if not isinstance(delay, datetime.timedelta):
            delay = datetime.timedelta(seconds=delay)
        due_time = now() + delay
        cmd = cls.from_datetime(due_time)
        cmd.delay = delay
        cmd.target = target
        return cmd

    @staticmethod
    def _from_timestamp(input):
        """
        If input is a real number, interpret it as a Unix timestamp
        (seconds sinc Epoch in UTC) and return a timezone-aware
        datetime object. Otherwise return input unchanged.
        """
        if not isinstance(input, numbers.Real):
            return input
        return from_timestamp(input)

    @classmethod
    def at_time(cls, at, target):
        """
        Construct a DelayedCommand to come due at `at`, where `at` may be
        a datetime or timestamp.
        """
        at = cls._from_timestamp(at)
        cmd = cls.from_datetime(at)
        cmd.delay = at - now()
        cmd.target = target
        return cmd

    def due(self):
        return now() >= self


class PeriodicCommand(DelayedCommand):
    """
    Like a delayed command, but expect this command to run every delay
    seconds.
    """

    def _next_time(self):
        """
        Add delay to self, localized
        """
        return self._localize(self + self.delay)

    @staticmethod
    def _localize(dt):
        """
        Rely on pytz.localize to ensure new result honors DST.
        """
        try:
            tz = dt.tzinfo
            return tz.localize(dt.replace(tzinfo=None))
        except AttributeError:
            return dt

    def next(self):
        cmd = self.__class__.from_datetime(self._next_time())
        cmd.delay = self.delay
        cmd.target = self.target
        return cmd

    def __setattr__(self, key, value):
        if key == 'delay' and not value > datetime.timedelta():
            raise ValueError(
                "A PeriodicCommand must have a positive, " "non-zero delay."
            )
        super(PeriodicCommand, self).__setattr__(key, value)


class PeriodicCommandFixedDelay(PeriodicCommand):
    """
    Like a periodic command, but don't calculate the delay based on
    the current time. Instead use a fixed delay following the initial
    run.
    """

    @classmethod
    def at_time(cls, at, delay, target):
        """
        >>> cmd = PeriodicCommandFixedDelay.at_time(0, 30, None)
        >>> cmd.delay.total_seconds()
        30.0
        """
        at = cls._from_timestamp(at)
        cmd = cls.from_datetime(at)
        if isinstance(delay, numbers.Number):
            delay = datetime.timedelta(seconds=delay)
        cmd.delay = delay
        cmd.target = target
        return cmd

    @classmethod
    def daily_at(cls, at, target):
        """
        Schedule a command to run at a specific time each day.

        >>> from tempora import utc
        >>> noon = utc.time(12, 0)
        >>> cmd = PeriodicCommandFixedDelay.daily_at(noon, None)
        >>> cmd.delay.total_seconds()
        86400.0
        """
        daily = datetime.timedelta(days=1)
        # convert when to the next datetime matching this time
        when = datetime.datetime.combine(datetime.date.today(), at)
        when -= daily
        while when < now():
            when += daily
        return cls.at_time(cls._localize(when), daily, target)


class Scheduler:
    """
    A rudimentary abstract scheduler accepting DelayedCommands
    and dispatching them on schedule.
    """

    def __init__(self):
        self.queue = []

    def add(self, command):
        assert isinstance(command, DelayedCommand)
        bisect.insort(self.queue, command)

    def run_pending(self):
        while self.queue:
            command = self.queue[0]
            if not command.due():
                break
            self.run(command)
            if isinstance(command, PeriodicCommand):
                self.add(command.next())
            del self.queue[0]

    @abc.abstractmethod
    def run(self, command):
        """
        Run the command
        """


class InvokeScheduler(Scheduler):
    """
    Command targets are functions to be invoked on schedule.
    """

    def run(self, command):
        command.target()


class CallbackScheduler(Scheduler):
    """
    Command targets are passed to a dispatch callable on schedule.
    """

    def __init__(self, dispatch):
        super().__init__()
        self.dispatch = dispatch

    def run(self, command):
        self.dispatch(command.target)
