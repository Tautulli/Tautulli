# -*- coding: utf-8 -*-


class PlexApiException(Exception):
    """ Base class for all PlexAPI exceptions. """
    pass


class BadRequest(PlexApiException):
    """ An invalid request, generally a user error. """
    pass


class NotFound(PlexApiException):
    """ Request media item or device is not found. """
    pass


class UnknownType(PlexApiException):
    """ Unknown library type. """
    pass


class Unsupported(PlexApiException):
    """ Unsupported client request. """
    pass


class Unauthorized(BadRequest):
    """ Invalid username/password or token. """
    pass
