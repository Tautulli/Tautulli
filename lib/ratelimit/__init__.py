from math import floor

import time
import sys
import threading
import functools


def clamp(value):
    '''
    Clamp integer between 1 and max

    There must be at least 1 method invocation
    made over the time period. Make sure the
    value passed is at least 1 and is not a
    fraction of an invocation.

    :param float value: The number of method invocations.
    :return: Clamped number of invocations.
    :rtype: int
    '''
    return max(1, min(sys.maxsize, floor(value)))


class RateLimitDecorator:
    def __init__(self, period=1, every=1.0):
        self.frequency = abs(every) / float(clamp(period))
        self.last_called = 0.0
        self.lock = threading.RLock()

    def __call__(self, func):
        '''
        Extend the behaviour of the following
        function, forwarding method invocations
        if the time window hes elapsed.

        :param function func: The function to decorate.
        :return: Decorated function.
        :rtype: function
        '''
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            '''Decorator wrapper function'''
            with self.lock:
                elapsed = time.time() - self.last_called
                left_to_wait = self.frequency - elapsed
                if left_to_wait > 0:
                    time.sleep(left_to_wait)
                self.last_called = time.time()
            return func(*args, **kwargs)
        return wrapper


rate_limited = RateLimitDecorator


__all__ = [
    'rate_limited'
]
