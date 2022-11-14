# -*- coding: utf-8 -*-


class RumpsError(Exception):
    """A generic rumps error occurred."""


class InternalRumpsError(RumpsError):
    """Internal mechanism powering functionality of rumps failed."""
