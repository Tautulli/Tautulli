#
# Copyright (C) 2011-2013 Vinay Sajip. See LICENSE.txt for details.
#
"""
This module contains classes which help you work with Redis queues.
"""

from logutils.queue import QueueHandler, QueueListener
try:
    import cPickle as pickle
except ImportError:
    import pickle

class RedisQueueHandler(QueueHandler):
    """
    A QueueHandler implementation which pushes pickled
    records to a Redis queue using a specified key.
    
    :param key: The key to use for the queue. Defaults to
                "python.logging".
    :param redis: If specified, this instance is used to
                  communicate with a Redis instance.
    :param limit: If specified, the queue is restricted to
                  have only this many elements.
    """
    def __init__(self, key='python.logging', redis=None, limit=0):
        if redis is None:
            from redis import Redis
            redis = Redis()
        self.key = key
        assert limit >= 0
        self.limit = limit
        QueueHandler.__init__(self, redis)
        
    def enqueue(self, record):
        s = pickle.dumps(vars(record))
        self.queue.rpush(self.key, s)
        if self.limit:
            self.queue.ltrim(self.key, -self.limit, -1)

class RedisQueueListener(QueueListener):
    """
    A QueueListener implementation which fetches pickled
    records from a Redis queue using a specified key.
    
    :param key: The key to use for the queue. Defaults to
                "python.logging".
    :param redis: If specified, this instance is used to
                  communicate with a Redis instance.
    """
    def __init__(self, *handlers, **kwargs):
        redis = kwargs.get('redis')
        if redis is None:
            from redis import Redis
            redis = Redis()
        self.key = kwargs.get('key', 'python.logging')
        QueueListener.__init__(self, redis, *handlers)

    def dequeue(self, block):
        """
        Dequeue and return a record.
        """
        if block:
            s = self.queue.blpop(self.key)[1]
        else:
            s = self.queue.lpop(self.key)        
        if not s:
            record = None
        else:
            record = pickle.loads(s)
        return record

    def enqueue_sentinel(self):
        self.queue.rpush(self.key, '')

