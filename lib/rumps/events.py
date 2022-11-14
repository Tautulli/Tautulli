# -*- coding: utf-8 -*-

import traceback

from . import _internal


class EventEmitter(object):
    def __init__(self, name):
        self.name = name
        self.callbacks = set()
        self._executor = _internal.call_as_function_or_method

    def register(self, func):
        self.callbacks.add(func)
        return func

    def unregister(self, func):
        try:
            self.callbacks.remove(func)
            return True
        except KeyError:
            return False

    def emit(self, *args, **kwargs):
        #print('EventEmitter("%s").emit called' % self.name)
        for callback in self.callbacks:
            try:
                self._executor(callback, *args, **kwargs)
            except Exception:
                traceback.print_exc()

    __call__ = register


before_start = EventEmitter('before_start')
on_notification = EventEmitter('on_notification')
on_sleep = EventEmitter('on_sleep')
on_wake = EventEmitter('on_wake')
before_quit = EventEmitter('before_quit')
