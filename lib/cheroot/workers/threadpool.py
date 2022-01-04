"""A thread-based worker pool.

.. spelling::

   joinable
"""

from __future__ import absolute_import, division, print_function
__metaclass__ = type


import collections
import threading
import time
import socket
import warnings

from six.moves import queue

from jaraco.functools import pass_none


__all__ = ('WorkerThread', 'ThreadPool')


class TrueyZero:
    """Object which equals and does math like the integer 0 but evals True."""

    def __add__(self, other):
        return other

    def __radd__(self, other):
        return other


trueyzero = TrueyZero()

_SHUTDOWNREQUEST = None


class WorkerThread(threading.Thread):
    """Thread which continuously polls a Queue for Connection objects.

    Due to the timing issues of polling a Queue, a WorkerThread does not
    check its own 'ready' flag after it has started. To stop the thread,
    it is necessary to stick a _SHUTDOWNREQUEST object onto the Queue
    (one for each running WorkerThread).
    """

    conn = None
    """The current connection pulled off the Queue, or None."""

    server = None
    """The HTTP Server which spawned this thread, and which owns the
    Queue and is placing active connections into it."""

    ready = False
    """A simple flag for the calling server to know when this thread
    has begun polling the Queue."""

    def __init__(self, server):
        """Initialize WorkerThread instance.

        Args:
            server (cheroot.server.HTTPServer): web server object
                receiving this request
        """
        self.ready = False
        self.server = server

        self.requests_seen = 0
        self.bytes_read = 0
        self.bytes_written = 0
        self.start_time = None
        self.work_time = 0
        self.stats = {
            'Requests': lambda s: self.requests_seen + (
                self.start_time is None
                and trueyzero
                or self.conn.requests_seen
            ),
            'Bytes Read': lambda s: self.bytes_read + (
                self.start_time is None
                and trueyzero
                or self.conn.rfile.bytes_read
            ),
            'Bytes Written': lambda s: self.bytes_written + (
                self.start_time is None
                and trueyzero
                or self.conn.wfile.bytes_written
            ),
            'Work Time': lambda s: self.work_time + (
                self.start_time is None
                and trueyzero
                or time.time() - self.start_time
            ),
            'Read Throughput': lambda s: s['Bytes Read'](s) / (
                s['Work Time'](s) or 1e-6
            ),
            'Write Throughput': lambda s: s['Bytes Written'](s) / (
                s['Work Time'](s) or 1e-6
            ),
        }
        threading.Thread.__init__(self)

    def run(self):
        """Process incoming HTTP connections.

        Retrieves incoming connections from thread pool.
        """
        self.server.stats['Worker Threads'][self.name] = self.stats
        try:
            self.ready = True
            while True:
                conn = self.server.requests.get()
                if conn is _SHUTDOWNREQUEST:
                    return

                self.conn = conn
                is_stats_enabled = self.server.stats['Enabled']
                if is_stats_enabled:
                    self.start_time = time.time()
                keep_conn_open = False
                try:
                    keep_conn_open = conn.communicate()
                finally:
                    if keep_conn_open:
                        self.server.put_conn(conn)
                    else:
                        conn.close()
                    if is_stats_enabled:
                        self.requests_seen += self.conn.requests_seen
                        self.bytes_read += self.conn.rfile.bytes_read
                        self.bytes_written += self.conn.wfile.bytes_written
                        self.work_time += time.time() - self.start_time
                        self.start_time = None
                    self.conn = None
        except (KeyboardInterrupt, SystemExit) as ex:
            self.server.interrupt = ex


class ThreadPool:
    """A Request Queue for an HTTPServer which pools threads.

    ThreadPool objects must provide min, get(), put(obj), start()
    and stop(timeout) attributes.
    """

    def __init__(
            self, server, min=10, max=-1, accepted_queue_size=-1,
            accepted_queue_timeout=10,
    ):
        """Initialize HTTP requests queue instance.

        Args:
            server (cheroot.server.HTTPServer): web server object
                receiving this request
            min (int): minimum number of worker threads
            max (int): maximum number of worker threads
            accepted_queue_size (int): maximum number of active
                requests in queue
            accepted_queue_timeout (int): timeout for putting request
                into queue
        """
        self.server = server
        self.min = min
        self.max = max
        self._threads = []
        self._queue = queue.Queue(maxsize=accepted_queue_size)
        self._queue_put_timeout = accepted_queue_timeout
        self.get = self._queue.get
        self._pending_shutdowns = collections.deque()

    def start(self):
        """Start the pool of threads."""
        for _ in range(self.min):
            self._threads.append(WorkerThread(self.server))
        for worker in self._threads:
            worker.name = (
                'CP Server {worker_name!s}'.
                format(worker_name=worker.name),
            )
            worker.start()
        for worker in self._threads:
            while not worker.ready:
                time.sleep(.1)

    @property
    def idle(self):  # noqa: D401; irrelevant for properties
        """Number of worker threads which are idle. Read-only."""  # noqa: D401
        idles = len([t for t in self._threads if t.conn is None])
        return max(idles - len(self._pending_shutdowns), 0)

    def put(self, obj):
        """Put request into queue.

        Args:
            obj (:py:class:`~cheroot.server.HTTPConnection`): HTTP connection
                waiting to be processed
        """
        self._queue.put(obj, block=True, timeout=self._queue_put_timeout)

    def _clear_dead_threads(self):
        # Remove any dead threads from our list
        for t in [t for t in self._threads if not t.is_alive()]:
            self._threads.remove(t)
            try:
                self._pending_shutdowns.popleft()
            except IndexError:
                pass

    def grow(self, amount):
        """Spawn new worker threads (not above self.max)."""
        if self.max > 0:
            budget = max(self.max - len(self._threads), 0)
        else:
            # self.max <= 0 indicates no maximum
            budget = float('inf')

        n_new = min(amount, budget)

        workers = [self._spawn_worker() for i in range(n_new)]
        while not all(worker.ready for worker in workers):
            time.sleep(.1)
        self._threads.extend(workers)

    def _spawn_worker(self):
        worker = WorkerThread(self.server)
        worker.name = (
            'CP Server {worker_name!s}'.
            format(worker_name=worker.name),
        )
        worker.start()
        return worker

    def shrink(self, amount):
        """Kill off worker threads (not below self.min)."""
        # Grow/shrink the pool if necessary.
        # Remove any dead threads from our list
        amount -= len(self._pending_shutdowns)
        self._clear_dead_threads()
        if amount <= 0:
            return

        # calculate the number of threads above the minimum
        n_extra = max(len(self._threads) - self.min, 0)

        # don't remove more than amount
        n_to_remove = min(amount, n_extra)

        # put shutdown requests on the queue equal to the number of threads
        # to remove. As each request is processed by a worker, that worker
        # will terminate and be culled from the list.
        for _ in range(n_to_remove):
            self._pending_shutdowns.append(None)
            self._queue.put(_SHUTDOWNREQUEST)

    def stop(self, timeout=5):
        """Terminate all worker threads.

        Args:
            timeout (int): time to wait for threads to stop gracefully
        """
        # for compatability, negative timeouts are treated like None
        # TODO: treat negative timeouts like already expired timeouts
        if timeout is not None and timeout < 0:
            timeout = None
            warnings.warning(
                'In the future, negative timeouts to Server.stop() '
                'will be equivalent to a timeout of zero.',
                stacklevel=2,
            )

        if timeout is not None:
            endtime = time.time() + timeout

        # Must shut down threads here so the code that calls
        # this method can know when all threads are stopped.
        for worker in self._threads:
            self._queue.put(_SHUTDOWNREQUEST)

        ignored_errors = (
            # Raised when start_response called >1 time w/o exc_info or
            # wsgi write is called before start_response. See cheroot#261
            RuntimeError,
            # Ignore repeated Ctrl-C. See cherrypy#691.
            KeyboardInterrupt,
        )

        for worker in self._clear_threads():
            remaining_time = timeout and endtime - time.time()
            try:
                worker.join(remaining_time)
                if worker.is_alive():
                    # Timeout exhausted; forcibly shut down the socket.
                    self._force_close(worker.conn)
                    worker.join()
            except ignored_errors:
                pass

    @staticmethod
    @pass_none
    def _force_close(conn):
        if conn.rfile.closed:
            return
        try:
            try:
                conn.socket.shutdown(socket.SHUT_RD)
            except TypeError:
                # pyOpenSSL sockets don't take an arg
                conn.socket.shutdown()
        except OSError:
            # shutdown sometimes fails (race with 'closed' check?)
            # ref #238
            pass

    def _clear_threads(self):
        """Clear self._threads and yield all joinable threads."""
        # threads = pop_all(self._threads)
        threads, self._threads[:] = self._threads[:], []
        return (
            thread
            for thread in threads
            if thread is not threading.current_thread()
        )

    @property
    def qsize(self):
        """Return the queue size."""
        return self._queue.qsize()
