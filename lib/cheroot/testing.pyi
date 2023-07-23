from typing import Any, Iterator, Optional, TypeVar

from .server import HTTPServer
from .wsgi import Server

T = TypeVar('T', bound=HTTPServer)

EPHEMERAL_PORT: int
NO_INTERFACE: Optional[str]
ANY_INTERFACE_IPV4: str
ANY_INTERFACE_IPV6: str
config: dict

def cheroot_server(server_factory: T) -> Iterator[T]: ...
def wsgi_server() -> Iterator[Server]: ...
def native_server() -> Iterator[HTTPServer]: ...
def get_server_client(server) -> Any: ...
