from typing import Any

from . import Adapter

DEFAULT_BUFFER_SIZE: int

class BuiltinSSLAdapter(Adapter):
    CERT_KEY_TO_ENV: Any
    CERT_KEY_TO_LDAP_CODE: Any
    def __init__(
        self,
        certificate,
        private_key,
        certificate_chain: Any | None = ...,
        ciphers: Any | None = ...,
        *,
        private_key_password: str | bytes | None = ...,
    ) -> None: ...
    @property
    def context(self): ...
    @context.setter
    def context(self, context) -> None: ...
    def bind(self, sock): ...
    def wrap(self, sock): ...
    def get_environ(self, sock): ...
    def makefile(self, sock, mode: str = ..., bufsize: int = ...): ...
