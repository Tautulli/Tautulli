from collections import deque
from typing import Deque, Set, Tuple, Union
from urllib.parse import parse_qsl, unquote, urlsplit

from plexapi import utils


class SmartFilterMixin:
    """ Mixin for Plex objects that can have smart filters. """

    def _parseFilterGroups(self, feed: Deque[Tuple[str, str]], returnOn: Union[Set[str], None] = None) -> dict:
        """ Parse filter groups from input lines between push and pop. """
        currentFiltersStack: list[dict] = []
        operatorForStack = None
        if returnOn is None:
            returnOn = set("pop")
        else:
            returnOn.add("pop")
        allowedLogicalOperators = ["and", "or"]  # first is the default

        while feed:
            key, value = feed.popleft()  # consume the first item
            if key == "push":
                # recurse and add the result to the current stack
                currentFiltersStack.append(
                    self._parseFilterGroups(feed, returnOn)
                )
            elif key in returnOn:
                # stop iterating and return the current stack
                if not key == "pop":
                    feed.appendleft((key, value))  # put the item back
                break

            elif key in allowedLogicalOperators:
                # set the operator
                if operatorForStack and not operatorForStack == key:
                    raise ValueError(
                        "cannot have different logical operators for the same"
                        " filter group"
                    )
                operatorForStack = key

            else:
                # add the key value pair to the current filter
                currentFiltersStack.append({key: value})

        if not operatorForStack and len(currentFiltersStack) > 1:
            # consider 'and' as the default operator
            operatorForStack = allowedLogicalOperators[0]

        if operatorForStack:
            return {operatorForStack: currentFiltersStack}
        return currentFiltersStack.pop()

    def _parseQueryFeed(self, feed: "deque[Tuple[str, str]]") -> dict:
        """ Parse the query string into a dict. """
        filtersDict: dict[str, Union[str, int, list, dict]] = {}
        special_keys = {"type", "sort"}
        integer_keys = {"includeGuids", "limit"}
        as_is_keys = {"group", "having"}
        reserved_keys = special_keys | integer_keys | as_is_keys
        while feed:
            key, value = feed.popleft()
            if key in integer_keys:
                filtersDict[key] = int(value)
            elif key in as_is_keys:
                filtersDict[key] = value
            elif key == "type":
                filtersDict["libtype"] = utils.reverseSearchType(value)
            elif key == "sort":
                filtersDict["sort"] = value.split(",")
            else:
                feed.appendleft((key, value))  # put the item back
                filter_group = self._parseFilterGroups(
                    feed, returnOn=reserved_keys
                )
                if "filters" in filtersDict:
                    filtersDict["filters"] = {
                        "and": [filtersDict["filters"], filter_group]
                    }
                else:
                    filtersDict["filters"] = filter_group

        return filtersDict

    def _parseFilters(self, content):
        """ Parse the content string and returns the filter dict. """
        content = urlsplit(unquote(content))
        feed = deque()

        for key, value in parse_qsl(content.query):
            # Move = sign to key when operator is ==
            if value.startswith("="):
                key, value = f"{key}=", value[1:]

            feed.append((key, value))

        return self._parseQueryFeed(feed)
