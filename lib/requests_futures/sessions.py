# -*- coding: utf-8 -*-
"""
requests_futures
~~~~~~~~~~~~~~~~

This module provides a small add-on for the requests http library. It makes use
of python 3.3's concurrent.futures or the futures backport for previous
releases of python.

    from requests_futures import FuturesSession

    session = FuturesSession()
    # request is run in the background
    future = session.get('http://httpbin.org/get')
    # ... do other stuff ...
    # wait for the request to complete, if it hasn't already
    response = future.result()
    print('response status: {0}'.format(response.status_code))
    print(response.content)

"""

from concurrent.futures import ThreadPoolExecutor
from requests import Session
from requests.adapters import DEFAULT_POOLSIZE, HTTPAdapter

class FuturesSession(Session):

    def __init__(self, executor=None, max_workers=2, *args, **kwargs):
        """Creates a FuturesSession

        Notes
        ~~~~~

        * ProcessPoolExecutor is not supported b/c Response objects are
          not picklable.

        * If you provide both `executor` and `max_workers`, the latter is
          ignored and provided executor is used as is.
        """
        super(FuturesSession, self).__init__(*args, **kwargs)
        if executor is None:
            executor = ThreadPoolExecutor(max_workers=max_workers)
            # set connection pool size equal to max_workers if needed
            if max_workers > DEFAULT_POOLSIZE:
                adapter_kwargs = dict(pool_connections=max_workers,
                                      pool_maxsize=max_workers)
                self.mount('https://', HTTPAdapter(**adapter_kwargs))
                self.mount('http://', HTTPAdapter(**adapter_kwargs))

        self.executor = executor

    def request(self, *args, **kwargs):
        """Maintains the existing api for Session.request.

        Used by all of the higher level methods, e.g. Session.get.

        The background_callback param allows you to do some processing on the
        response in the background, e.g. call resp.json() so that json parsing
        happens in the background thread.
        """
        func = sup = super(FuturesSession, self).request

        background_callback = kwargs.pop('background_callback', None)
        if background_callback:
            def wrap(*args_, **kwargs_):
                resp = sup(*args_, **kwargs_)
                background_callback(self, resp)
                return resp

            func = wrap

        return self.executor.submit(func, *args, **kwargs)
