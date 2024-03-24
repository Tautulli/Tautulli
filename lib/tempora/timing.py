import collections.abc
import contextlib
import datetime
import functools
import numbers
import time

import jaraco.functools


class Stopwatch:
    """
    A simple stopwatch that starts automatically.

    >>> w = Stopwatch()
    >>> _1_sec = datetime.timedelta(seconds=1)
    >>> w.split() < _1_sec
    True
    >>> time.sleep(1.0)
    >>> w.split() >= _1_sec
    True
    >>> w.stop() >= _1_sec
    True
    >>> w.reset()
    >>> w.start()
    >>> w.split() < _1_sec
    True

    Launch the Stopwatch in a context:

    >>> with Stopwatch() as watch:
    ...     assert isinstance(watch.split(), datetime.timedelta)

    After exiting the context, the watch is stopped; read the
    elapsed time directly:

    >>> watch.elapsed
    datetime.timedelta(...)
    >>> watch.elapsed.seconds
    0
    """

    def __init__(self):
        self.reset()
        self.start()

    def reset(self):
        self.elapsed = datetime.timedelta(0)
        with contextlib.suppress(AttributeError):
            del self._start

    def _diff(self):
        return datetime.timedelta(seconds=time.monotonic() - self._start)

    def start(self):
        self._start = time.monotonic()

    def stop(self):
        self.elapsed += self._diff()
        del self._start
        return self.elapsed

    def split(self):
        return self.elapsed + self._diff()

    # context manager support
    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.stop()


class IntervalGovernor:
    """
    Decorate a function to only allow it to be called once per
    min_interval. Otherwise, it returns None.

    >>> gov = IntervalGovernor(30)
    >>> gov.min_interval.total_seconds()
    30.0
    """

    def __init__(self, min_interval):
        if isinstance(min_interval, numbers.Number):
            min_interval = datetime.timedelta(seconds=min_interval)
        self.min_interval = min_interval
        self.last_call = None

    def decorate(self, func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            allow = not self.last_call or self.last_call.split() > self.min_interval
            if allow:
                self.last_call = Stopwatch()
                return func(*args, **kwargs)

        return wrapper

    __call__ = decorate


class Timer(Stopwatch):
    """
    Watch for a target elapsed time.

    >>> t = Timer(0.1)
    >>> t.expired()
    False
    >>> __import__('time').sleep(0.15)
    >>> t.expired()
    True
    """

    def __init__(self, target=float('Inf')):
        self.target = self._accept(target)
        super().__init__()

    @staticmethod
    def _accept(target):
        """
        Accept None or ∞ or datetime or numeric for target

        >>> Timer._accept(datetime.timedelta(seconds=30))
        30.0
        >>> Timer._accept(None)
        inf
        """
        if isinstance(target, datetime.timedelta):
            target = target.total_seconds()

        if target is None:
            # treat None as infinite target
            target = float('Inf')

        return target

    def expired(self):
        return self.split().total_seconds() > self.target


class BackoffDelay(collections.abc.Iterator):
    """
    Exponential backoff delay.

    Useful for defining delays between retries. Consider for use
    with ``jaraco.functools.retry_call`` as the cleanup.

    Default behavior has no effect; a delay or jitter must
    be supplied for the call to be non-degenerate.

    >>> bd = BackoffDelay()
    >>> bd()
    >>> bd()

    The following instance will delay 10ms for the first call,
    20ms for the second, etc.

    >>> bd = BackoffDelay(delay=0.01, factor=2)
    >>> bd()
    >>> bd()

    Inspect and adjust the state of the delay anytime.

    >>> bd.delay
    0.04
    >>> bd.delay = 0.01

    Set limit to prevent the delay from exceeding bounds.

    >>> bd = BackoffDelay(delay=0.01, factor=2, limit=0.015)
    >>> bd()
    >>> bd.delay
    0.015

    To reset the backoff, simply call ``.reset()``:

    >>> bd.reset()
    >>> bd.delay
    0.01

    Iterate on the object to retrieve/advance the delay values.

    >>> next(bd)
    0.01
    >>> next(bd)
    0.015
    >>> import itertools
    >>> tuple(itertools.islice(bd, 3))
    (0.015, 0.015, 0.015)

    Limit may be a callable taking a number and returning
    the limited number.

    >>> at_least_one = lambda n: max(n, 1)
    >>> bd = BackoffDelay(delay=0.01, factor=2, limit=at_least_one)
    >>> next(bd)
    0.01
    >>> next(bd)
    1

    Pass a jitter to add or subtract seconds to the delay.

    >>> bd = BackoffDelay(jitter=0.01)
    >>> next(bd)
    0
    >>> next(bd)
    0.01

    Jitter may be a callable. To supply a non-deterministic jitter
    between -0.5 and 0.5, consider:

    >>> import random
    >>> jitter=functools.partial(random.uniform, -0.5, 0.5)
    >>> bd = BackoffDelay(jitter=jitter)
    >>> next(bd)
    0
    >>> 0 <= next(bd) <= 0.5
    True
    """

    delay = 0

    factor = 1
    "Multiplier applied to delay"

    jitter = 0
    "Number or callable returning extra seconds to add to delay"

    @jaraco.functools.save_method_args
    def __init__(self, delay=0, factor=1, limit=float('inf'), jitter=0):
        self.delay = delay
        self.factor = factor
        if isinstance(limit, numbers.Number):
            limit_ = limit

            def limit(n):
                return max(0, min(limit_, n))

        self.limit = limit
        if isinstance(jitter, numbers.Number):
            jitter_ = jitter

            def jitter():
                return jitter_

        self.jitter = jitter

    def __call__(self):
        time.sleep(next(self))

    def __next__(self):
        delay = self.delay
        self.bump()
        return delay

    def __iter__(self):
        return self

    def bump(self):
        self.delay = self.limit(self.delay * self.factor + self.jitter())

    def reset(self):
        saved = self._saved___init__
        self.__init__(*saved.args, **saved.kwargs)
