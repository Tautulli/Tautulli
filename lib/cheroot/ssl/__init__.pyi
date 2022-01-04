from abc import abstractmethod
from typing import Any

class Adapter():
    certificate: Any
    private_key: Any
    certificate_chain: Any
    ciphers: Any
    context: Any
    @abstractmethod
    def __init__(self, certificate, private_key, certificate_chain: Any | None = ..., ciphers: Any | None = ...): ...
    @abstractmethod
    def bind(self, sock): ...
    @abstractmethod
    def wrap(self, sock): ...
    @abstractmethod
    def get_environ(self): ...
    @abstractmethod
    def makefile(self, sock, mode: str = ..., bufsize: int = ...): ...
