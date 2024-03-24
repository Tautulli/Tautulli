import base64
import json

import cloudinary
from cloudinary.api_client.call_api import call_json_api
from cloudinary.utils import (unique, build_distribution_domain, base64url_encode, json_encode, compute_hex_hash,
                              SIGNATURE_SHA256, build_array)


class Search(object):
    ASSETS = 'resources'

    _endpoint = ASSETS

    _KEYS_WITH_UNIQUE_VALUES = {
        'sort_by': lambda x: next(iter(x)),
        'aggregate': None,
        'with_field': None,
        'fields': None,
    }

    _ttl = 300  # Used for search URLs

    """Build and execute a search query."""

    def __init__(self):
        self.query = {}

    def expression(self, value):
        """Specify the search query expression."""
        self.query["expression"] = value
        return self

    def max_results(self, value):
        """Set the max results to return"""
        self.query["max_results"] = value
        return self

    def next_cursor(self, value):
        """Get next page in the query using the ``next_cursor`` value from a previous invocation."""
        self.query["next_cursor"] = value
        return self

    def sort_by(self, field_name, direction=None):
        """Add a field to sort results by. If not provided, direction is ``desc``."""
        if direction is None:
            direction = 'desc'
        self._add("sort_by", {field_name: direction})
        return self

    def aggregate(self, value):
        """Aggregate field."""
        self._add("aggregate", value)
        return self

    def with_field(self, value):
        """Request an additional field in the result set."""
        self._add("with_field", value)
        return self

    def fields(self, value):
        """Request which fields to return in the result set."""
        self._add("fields", value)
        return self

    def ttl(self, ttl):
        """
        Sets the time to live of the search URL.

        :param ttl: The time to live in seconds.
        :return: self
        """
        self._ttl = ttl
        return self

    def to_json(self):
        return json.dumps(self.as_dict())

    def execute(self, **options):
        """Execute the search and return results."""
        options["content_type"] = 'application/json'
        uri = [self._endpoint, 'search']
        return call_json_api('post', uri, self.as_dict(), **options)

    def as_dict(self):
        to_return = {}

        for key, value in self.query.items():
            if key in self._KEYS_WITH_UNIQUE_VALUES:
                value = unique(value, self._KEYS_WITH_UNIQUE_VALUES[key])

            to_return[key] = value

        return to_return

    def to_url(self, ttl=None, next_cursor=None, **options):
        """
        Creates a signed Search URL that can be used on the client side.

        :param ttl: The time to live in seconds.
        :param next_cursor: Starting position.
        :param options: Additional url delivery options.
        :return: The resulting search URL.
        """
        api_secret = options.get("api_secret", cloudinary.config().api_secret or None)
        if not api_secret:
            raise ValueError("Must supply api_secret")

        if ttl is None:
            ttl = self._ttl

        query = self.as_dict()

        _next_cursor = query.pop("next_cursor", None)
        if next_cursor is None:
            next_cursor = _next_cursor

        b64query = base64url_encode(json_encode(query, sort_keys=True))

        prefix = build_distribution_domain(options)

        signature = compute_hex_hash("{ttl}{b64query}{api_secret}".format(
            ttl=ttl,
            b64query=b64query,
            api_secret=api_secret
        ), algorithm=SIGNATURE_SHA256)

        return "{prefix}/search/{signature}/{ttl}/{b64query}{next_cursor}".format(
            prefix=prefix,
            signature=signature,
            ttl=ttl,
            b64query=b64query,
            next_cursor="/{}".format(next_cursor) if next_cursor else "")

    def endpoint(self, endpoint):
        self._endpoint = endpoint
        return self

    def _add(self, name, value):
        if name not in self.query:
            self.query[name] = []
        self.query[name].extend(build_array(value))
        return self
