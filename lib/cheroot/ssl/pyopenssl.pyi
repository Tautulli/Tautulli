from typing import Any, Type

from OpenSSL import SSL

from ..makefile import StreamReader, StreamWriter
from . import Adapter

ssl_conn_type: Type[SSL.Connection]

class SSLFileobjectMixin:
    ssl_timeout: int
    ssl_retry: float
    def recv(self, size): ...
    def readline(self, size: int = ...): ...
    def sendall(self, *args, **kwargs): ...
    def send(self, *args, **kwargs): ...

class SSLFileobjectStreamReader(SSLFileobjectMixin, StreamReader): ...  # type:ignore[misc]
class SSLFileobjectStreamWriter(SSLFileobjectMixin, StreamWriter): ...  # type:ignore[misc]

class SSLConnectionProxyMeta:
    def __new__(mcl, name, bases, nmspc): ...

class SSLConnection:
    def __init__(self, *args) -> None: ...

class pyOpenSSLAdapter(Adapter):
    def __init__(
        self,
        certificate,
        private_key,
        certificate_chain: Any | None = ...,
        ciphers: Any | None = ...,
        *,
        private_key_password: str | bytes | None = ...,
    ) -> None: ...
    def bind(self, sock): ...
    def wrap(self, sock): ...
    def _password_callback(
        self,
        password_max_length: int,
        _verify_twice: bool,
        password: bytes | str | None,
        /,
    ) -> bytes: ...
    def get_environ(self): ...
    def makefile(self, sock, mode: str = ..., bufsize: int = ...): ...
    def get_context(self) -> SSL.Context: ...
