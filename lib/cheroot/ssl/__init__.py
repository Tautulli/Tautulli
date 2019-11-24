"""Implementation of the SSL adapter base interface."""

from __future__ import absolute_import, division, print_function
__metaclass__ = type

from abc import ABCMeta, abstractmethod

from six import add_metaclass


@add_metaclass(ABCMeta)
class Adapter:
    """Base class for SSL driver library adapters.

    Required methods:

        * ``wrap(sock) -> (wrapped socket, ssl environ dict)``
        * ``makefile(sock, mode='r', bufsize=DEFAULT_BUFFER_SIZE) ->
          socket file object``
    """

    @abstractmethod
    def __init__(
            self, certificate, private_key, certificate_chain=None,
            ciphers=None,
    ):
        """Set up certificates, private key ciphers and reset context."""
        self.certificate = certificate
        self.private_key = private_key
        self.certificate_chain = certificate_chain
        self.ciphers = ciphers
        self.context = None

    @abstractmethod
    def bind(self, sock):
        """Wrap and return the given socket."""
        return sock

    @abstractmethod
    def wrap(self, sock):
        """Wrap and return the given socket, plus WSGI environ entries."""
        raise NotImplementedError  # pragma: no cover

    @abstractmethod
    def get_environ(self):
        """Return WSGI environ entries to be merged into each request."""
        raise NotImplementedError  # pragma: no cover

    @abstractmethod
    def makefile(self, sock, mode='r', bufsize=-1):
        """Return socket file object."""
        raise NotImplementedError  # pragma: no cover
