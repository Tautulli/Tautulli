class MQTTMatcher:
    """Intended to manage topic filters including wildcards.

    Internally, MQTTMatcher use a prefix tree (trie) to store
    values associated with filters, and has an iter_match()
    method to iterate efficiently over all filters that match
    some topic name."""

    class Node:
        __slots__ = '_children', '_content'

        def __init__(self):
            self._children = {}
            self._content = None

    def __init__(self):
        self._root = self.Node()

    def __setitem__(self, key, value):
        """Add a topic filter :key to the prefix tree
        and associate it to :value"""
        node = self._root
        for sym in key.split('/'):
            node = node._children.setdefault(sym, self.Node())
        node._content = value

    def __getitem__(self, key):
        """Retrieve the value associated with some topic filter :key"""
        try:
            node = self._root
            for sym in key.split('/'):
                node = node._children[sym]
        except KeyError as err:
            raise KeyError(key) from err
        else:
            if node._content is None:
                raise KeyError(key)
            return node._content

    def __delitem__(self, key):
        """Delete the value associated with some topic filter :key"""
        lst = []
        try:
            parent, node = None, self._root
            for k in key.split('/'):
                 parent, node = node, node._children[k]
                 lst.append((parent, k, node))
        except KeyError as err:
            raise KeyError(key) from err
        else:
            if node._content is None:
                raise KeyError(key)
            node._content = None
            # cleanup
            for parent, k, node in reversed(lst):
                if node._children or node._content is not None:
                     break
                del parent._children[k]

    def iter_match(self, topic):
        """Return an iterator on all values associated with filters
        that match the :topic"""
        lst = topic.split('/')
        normal = not topic.startswith('$')
        def rec(node, i=0):
            if i == len(lst):
                if node._content is not None:
                    yield node._content
            else:
                part = lst[i]
                if part in node._children:
                    yield from rec(node._children[part], i + 1)
                if '+' in node._children and (normal or i > 0):
                    yield from rec(node._children['+'], i + 1)
            if '#' in node._children and (normal or i > 0):
                content = node._children['#']._content
                if content is not None:
                    yield content
        return rec(self._root)
