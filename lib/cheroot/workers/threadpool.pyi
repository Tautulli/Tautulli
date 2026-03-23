import threading
from typing import Any

__all__ = ('ThreadPool', 'WorkerThread')

class TrueyZero:
    def __add__(self, other): ...
    def __radd__(self, other): ...

trueyzero: TrueyZero

class WorkerThread(threading.Thread):
    conn: Any
    server: Any
    ready: bool
    requests_seen: int
    bytes_read: int
    bytes_written: int
    start_time: Any
    work_time: int
    stats: Any
    def __init__(self, server): ...
    def run(self) -> None: ...

class ThreadPool:
    server: Any
    min: Any
    max: Any
    get: Any
    def __init__(
        self,
        server,
        min: int = ...,
        max: int = ...,
        accepted_queue_size: int = ...,
        accepted_queue_timeout: int = ...,
    ) -> None: ...
    def start(self) -> None: ...
    @property
    def idle(self): ...
    def put(self, obj) -> None: ...
    def grow(self, amount) -> None: ...
    def shrink(self, amount) -> None: ...
    def stop(self, timeout: int = ...) -> None: ...
    @property
    def qsize(self) -> int: ...
