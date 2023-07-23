from . import server
from typing import Any

class Server(server.HTTPServer):
    wsgi_version: Any
    wsgi_app: Any
    request_queue_size: Any
    timeout: Any
    shutdown_timeout: Any
    requests: Any
    def __init__(self, bind_addr, wsgi_app, numthreads: int = ..., server_name: Any | None = ..., max: int = ..., request_queue_size: int = ..., timeout: int = ..., shutdown_timeout: int = ..., accepted_queue_size: int = ..., accepted_queue_timeout: int = ..., peercreds_enabled: bool = ..., peercreds_resolve_enabled: bool = ...) -> None: ...
    @property
    def numthreads(self): ...
    @numthreads.setter
    def numthreads(self, value) -> None: ...

class Gateway(server.Gateway):
    started_response: bool
    env: Any
    remaining_bytes_out: Any
    def __init__(self, req) -> None: ...
    @classmethod
    def gateway_map(cls): ...
    def get_environ(self) -> None: ...
    def respond(self) -> None: ...
    def start_response(self, status, headers, exc_info: Any | None = ...): ...
    def write(self, chunk) -> None: ...

class Gateway_10(Gateway):
    version: Any
    def get_environ(self): ...

class Gateway_u0(Gateway_10):
    version: Any
    def get_environ(self): ...

wsgi_gateways: Any

class PathInfoDispatcher:
    apps: Any
    def __init__(self, apps): ...
    def __call__(self, environ, start_response): ...


WSGIServer = Server
WSGIGateway = Gateway
WSGIGateway_u0 = Gateway_u0
WSGIGateway_10 = Gateway_10
WSGIPathInfoDispatcher = PathInfoDispatcher
