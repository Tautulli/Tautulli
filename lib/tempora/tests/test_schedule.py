import time
import random
import datetime
from unittest import mock

import pytest
import pytz
import freezegun

from tempora import schedule


do_nothing = type(None)


def test_delayed_command_order():
    """
    delayed commands should be sorted by delay time
    """
    delays = [random.randint(0, 99) for x in range(5)]
    cmds = sorted(
        [schedule.DelayedCommand.after(delay, do_nothing) for delay in delays]
    )
    assert [c.delay.seconds for c in cmds] == sorted(delays)


def test_periodic_command_delay():
    "A PeriodicCommand must have a positive, non-zero delay."
    with pytest.raises(ValueError) as exc_info:
        schedule.PeriodicCommand.after(0, None)
    assert str(exc_info.value) == test_periodic_command_delay.__doc__


def test_periodic_command_fixed_delay():
    """
    Test that we can construct a periodic command with a fixed initial
    delay.
    """
    fd = schedule.PeriodicCommandFixedDelay.at_time(
        at=schedule.now(), delay=datetime.timedelta(seconds=2), target=lambda: None
    )
    assert fd.due() is True
    assert fd.next().due() is False


class TestCommands:
    def test_delayed_command_from_timestamp(self):
        """
        Ensure a delayed command can be constructed from a timestamp.
        """
        t = time.time()
        schedule.DelayedCommand.at_time(t, do_nothing)

    def test_command_at_noon(self):
        """
        Create a periodic command that's run at noon every day.
        """
        when = datetime.time(12, 0, tzinfo=pytz.utc)
        cmd = schedule.PeriodicCommandFixedDelay.daily_at(when, target=None)
        assert cmd.due() is False
        next_cmd = cmd.next()
        daily = datetime.timedelta(days=1)
        day_from_now = schedule.now() + daily
        two_days_from_now = day_from_now + daily
        assert day_from_now < next_cmd < two_days_from_now

    @pytest.mark.parametrize("hour", range(10, 14))
    @pytest.mark.parametrize("tz_offset", (14, -14))
    def test_command_at_noon_distant_local(self, hour, tz_offset):
        """
        Run test_command_at_noon, but with the local timezone
        more than 12 hours away from UTC.
        """
        with freezegun.freeze_time(f"2020-01-10 {hour:02}:01", tz_offset=tz_offset):
            self.test_command_at_noon()


class TestTimezones:
    def test_alternate_timezone_west(self):
        target_tz = pytz.timezone('US/Pacific')
        target = schedule.now().astimezone(target_tz)
        cmd = schedule.DelayedCommand.at_time(target, target=None)
        assert cmd.due()

    def test_alternate_timezone_east(self):
        target_tz = pytz.timezone('Europe/Amsterdam')
        target = schedule.now().astimezone(target_tz)
        cmd = schedule.DelayedCommand.at_time(target, target=None)
        assert cmd.due()

    def test_daylight_savings(self):
        """
        A command at 9am should always be 9am regardless of
        a DST boundary.
        """
        with freezegun.freeze_time('2018-03-10 08:00:00'):
            target_tz = pytz.timezone('US/Eastern')
            target_time = datetime.time(9, tzinfo=target_tz)
            cmd = schedule.PeriodicCommandFixedDelay.daily_at(
                target_time, target=lambda: None
            )

        def naive(dt):
            return dt.replace(tzinfo=None)

        assert naive(cmd) == datetime.datetime(2018, 3, 10, 9, 0, 0)
        next_ = cmd.next()
        assert naive(next_) == datetime.datetime(2018, 3, 11, 9, 0, 0)
        assert next_ - cmd == datetime.timedelta(hours=23)


class TestScheduler:
    def test_invoke_scheduler(self):
        sched = schedule.InvokeScheduler()
        target = mock.MagicMock()
        cmd = schedule.DelayedCommand.after(0, target)
        sched.add(cmd)
        sched.run_pending()
        target.assert_called_once()
        assert not sched.queue

    def test_callback_scheduler(self):
        callback = mock.MagicMock()
        sched = schedule.CallbackScheduler(callback)
        target = mock.MagicMock()
        cmd = schedule.DelayedCommand.after(0, target)
        sched.add(cmd)
        sched.run_pending()
        callback.assert_called_once_with(target)

    def test_periodic_command(self):
        sched = schedule.InvokeScheduler()
        target = mock.MagicMock()

        before = datetime.datetime.utcnow()

        cmd = schedule.PeriodicCommand.after(10, target)
        sched.add(cmd)
        sched.run_pending()
        target.assert_not_called()

        with freezegun.freeze_time(before + datetime.timedelta(seconds=15)):
            sched.run_pending()
        assert sched.queue
        target.assert_called_once()

        with freezegun.freeze_time(before + datetime.timedelta(seconds=25)):
            sched.run_pending()
        assert target.call_count == 2
