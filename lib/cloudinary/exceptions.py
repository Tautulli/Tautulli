# Copyright Cloudinary


class Error(Exception):
    pass


class NotFound(Error):
    pass


class NotAllowed(Error):
    pass


class AlreadyExists(Error):
    pass


class RateLimited(Error):
    pass


class BadRequest(Error):
    pass


class GeneralError(Error):
    pass


class AuthorizationRequired(Error):
    pass
