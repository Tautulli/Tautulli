import json

from cloudinary.api_client.call_api import call_json_api
from cloudinary.utils import unique


class Search(object):
    ASSETS = 'resources'

    _endpoint = ASSETS

    _KEYS_WITH_UNIQUE_VALUES = {
        'sort_by': lambda x: next(iter(x)),
        'aggregate': None,
        'with_field': None,
    }

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

    def to_json(self):
        return json.dumps(self.as_dict())

    def execute(self, **options):
        """Execute the search and return results."""
        options["content_type"] = 'application/json'
        uri = [self._endpoint, 'search']
        return call_json_api('post', uri, self.as_dict(), **options)

    def _add(self, name, value):
        if name not in self.query:
            self.query[name] = []
        self.query[name].append(value)
        return self

    def as_dict(self):
        to_return = {}

        for key, value in self.query.items():
            if key in self._KEYS_WITH_UNIQUE_VALUES:
                value = unique(value, self._KEYS_WITH_UNIQUE_VALUES[key])

            to_return[key] = value

        return to_return

    def endpoint(self, endpoint):
        self._endpoint = endpoint
        return self
