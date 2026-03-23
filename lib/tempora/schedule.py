"""
Classes for calling functions a schedule. Has time zone support.

For example, to run a job at 08:00 every morning in 'Asia/Calcutta':

>>> import zoneinfo
>>> job = lambda: print("time is now", datetime.datetime())
>>> time = datetime.time(8, tzinfo=zoneinfo.ZoneInfo('Asia/Calcutta'))
>>> cmd = PeriodicCommandFixedDelay.daily_at(time, job)
>>> sched = InvokeScheduler()
>>> sched.add(cmd)
>>> while True:  # doctest: +SKIP
...     sched.run_pending()
...     time.sleep(.1)

By default, the scheduler uses timezone-aware times in UTC. A
client may override the default behavior by overriding ``now``
and ``from_timestamp`` functions.

>>> now()
datetime.datetime(...utc)
>>> from_timestamp(1718723533.7685602)
datetime.datetime(...utc)
"""

from __future__ import annotations

import abc
import bisect
import datetime
import numbers
from typing import TYPE_CHECKING, Any

from .utc import fromtimestamp as from_timestamp
from .utc import now

if TYPE_CHECKING:
    from typing_extensions import Self


class DelayedCommand(datetime.datetime):
    """
    A command to be executed after some delay (seconds or timedelta).
    """

    delay: datetime.timedelta = datetime.timedelta()
    target: Any  # Expected type depends on the scheduler used

    @classmethod
    def from_datetime(cls, other) -> Self:
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
    def after(cls, delay, target) -> Self:
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
    def at_time(cls, at, target) -> Self:
        """
        Construct a DelayedCommand to come due at `at`, where `at` may be
        a datetime or timestamp.
        """
        at = cls._from_timestamp(at)
        cmd = cls.from_datetime(at)
        cmd.delay = at - now()
        cmd.target = target
        return cmd

    def due(self) -> bool:
        return now() >= self


class PeriodicCommand(DelayedCommand):
    """
    Like a delayed command, but expect this command to run every delay
    seconds.
    """

    def _next_time(self) -> Self:
        """
        Add delay to self, localized
        """
        return self + self.delay

    def next(self) -> Self:
        cmd = self.__class__.from_datetime(self._next_time())
        cmd.delay = self.delay
        cmd.target = self.target
        return cmd

    def __setattr__(self, key, value) -> None:
        if key == 'delay' and not value > datetime.timedelta():
            raise ValueError("A PeriodicCommand must have a positive, non-zero delay.")
        super().__setattr__(key, value)


class PeriodicCommandFixedDelay(PeriodicCommand):
    """
    Like a periodic command, but don't calculate the delay based on
    the current time. Instead use a fixed delay following the initial
    run.
    """

    @classmethod
    def at_time(cls, at, delay, target) -> Self:  # type: ignore[override] # jaraco/tempora#39
        """
        >>> cmd = PeriodicCommandFixedDelay.at_time(0, 30, None)
        >>> cmd.delay.total_seconds()
        30.0
        """
        at = cls._from_timestamp(at)
        cmd = cls.from_datetime(at)
        if isinstance(delay, numbers.Number):
            delay = datetime.timedelta(seconds=delay)  # type: ignore[arg-type] # python/mypy#3186#issuecomment-1571512649
        cmd.delay = delay
        cmd.target = target
        return cmd

    @classmethod
    def daily_at(cls, at, target) -> Self:
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
        return cls.at_time(when, daily, target)


class Scheduler:
    """
    A rudimentary abstract scheduler accepting DelayedCommands
    and dispatching them on schedule.
    """

    def __init__(self) -> None:
        self.queue: list[DelayedCommand] = []

    def add(self, command: DelayedCommand) -> None:
        bisect.insort(self.queue, command)

    def run_pending(self) -> None:
        while self.queue:
            command = self.queue[0]
            if not command.due():
                break
            self.run(command)
            if isinstance(command, PeriodicCommand):
                self.add(command.next())
            del self.queue[0]

    @abc.abstractmethod
    def run(self, command: DelayedCommand) -> None:
        """
        Run the command
        """


class InvokeScheduler(Scheduler):
    """
    Command targets are functions to be invoked on schedule.
    """

    def run(self, command: DelayedCommand) -> None:
        command.target()


class CallbackScheduler(Scheduler):
    """
    Command targets are passed to a dispatch callable on schedule.
    """

    def __init__(self, dispatch) -> None:
        super().__init__()
        self.dispatch = dispatch

    def run(self, command: DelayedCommand) -> None:
        self.dispatch(command.target)
