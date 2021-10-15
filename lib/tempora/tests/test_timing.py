import datetime
import time
import contextlib
import os
from unittest import mock

import pytest
from tempora import timing


def test_IntervalGovernor():
    """
    IntervalGovernor should prevent a function from being called more than
    once per interval.
    """
    func_under_test = mock.MagicMock()
    # to look like a function, it needs a __name__ attribute
    func_under_test.__name__ = 'func_under_test'
    interval = datetime.timedelta(seconds=1)
    governed = timing.IntervalGovernor(interval)(func_under_test)
    governed('a')
    governed('b')
    governed(3, 'sir')
    func_under_test.assert_called_once_with('a')


@pytest.fixture
def alt_tz(monkeypatch):
    hasattr(time, 'tzset') or pytest.skip("tzset not available")

    @contextlib.contextmanager
    def change():
        val = 'AEST-10AEDT-11,M10.5.0,M3.5.0'
        with monkeypatch.context() as ctx:
            ctx.setitem(os.environ, 'TZ', val)
            time.tzset()
            yield
        time.tzset()

    return change()


def test_Stopwatch_timezone_change(alt_tz):
    """
    The stopwatch should provide a consistent duration even
    if the timezone changes.
    """
    watch = timing.Stopwatch()
    with alt_tz:
        assert abs(watch.split().total_seconds()) < 0.1
