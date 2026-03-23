import re
from typing import TYPE_CHECKING, Generic, Iterable, List, Optional, TypeVar, Union
import weakref
from functools import cached_property
from urllib.parse import parse_qsl, urlencode, urlparse
from xml.etree import ElementTree
from xml.etree.ElementTree import Element

from plexapi import CONFIG, X_PLEX_CONTAINER_SIZE, log, utils
from plexapi.exceptions import BadRequest, NotFound, UnknownType, Unsupported

if TYPE_CHECKING:
    from plexapi.server import PlexServer

PlexObjectT = TypeVar("PlexObjectT", bound='PlexObject')
MediaContainerT = TypeVar("MediaContainerT", bound="MediaContainer")

USER_DONT_RELOAD_FOR_KEYS = set()
_DONT_RELOAD_FOR_KEYS = {'key', 'sourceURI'}
OPERATORS = {
    'exact': lambda v, q: v == q,
    'iexact': lambda v, q: v.lower() == q.lower(),
    'contains': lambda v, q: q in v,
    'icontains': lambda v, q: q.lower() in v.lower(),
    'ne': lambda v, q: v != q,
    'in': lambda v, q: v in q,
    'gt': lambda v, q: v > q,
    'gte': lambda v, q: v >= q,
    'lt': lambda v, q: v < q,
    'lte': lambda v, q: v <= q,
    'startswith': lambda v, q: v.startswith(q),
    'istartswith': lambda v, q: v.lower().startswith(q.lower()),
    'endswith': lambda v, q: v.endswith(q),
    'iendswith': lambda v, q: v.lower().endswith(q.lower()),
    'exists': lambda v, q: v is not None if q else v is None,
    'regex': lambda v, q: bool(re.search(q, v)),
    'iregex': lambda v, q: bool(re.search(q, v, flags=re.IGNORECASE)),
}


class cached_data_property(cached_property):
    """Caching for PlexObject data properties.

    This decorator creates properties that cache their values with
    automatic invalidation on data changes.
    """

    def __set_name__(self, owner, name):
        """Register the annotated property in the parent class's _cached_data_properties set."""
        super().__set_name__(owner, name)
        if not hasattr(owner, '_cached_data_properties'):
            owner._cached_data_properties = set()
        owner._cached_data_properties.add(name)


class PlexObjectMeta(type):
    """Metaclass for PlexObject to handle cached_data_properties."""
    def __new__(mcs, name, bases, attrs):
        cached_data_props = set()

        # Merge all _cached_data_properties from parent classes
        for base in bases:
            if hasattr(base, '_cached_data_properties'):
                cached_data_props.update(base._cached_data_properties)

        # Find all properties annotated with cached_data_property in the current class
        for attr_name, attr_value in attrs.items():
            if isinstance(attr_value, cached_data_property):
                cached_data_props.add(attr_name)

        attrs['_cached_data_properties'] = cached_data_props

        return super().__new__(mcs, name, bases, attrs)


class PlexObject(metaclass=PlexObjectMeta):
    """ Base class for all Plex objects.

        Parameters:
            server (:class:`~plexapi.server.PlexServer`): PlexServer this client is connected to (optional)
            data (ElementTree): Response from PlexServer used to build this object (optional).
            initpath (str): Relative path requested when retrieving specified `data` (optional).
            parent (:class:`~plexapi.base.PlexObject`): The parent object that this object is built from (optional).
    """
    TAG = None      # xml element tag
    TYPE = None     # xml element type
    key = None      # plex relative url

    def __init__(self, server, data, initpath=None, parent=None):
        self._server = server
        self._data = data
        self._initpath = initpath or self.key
        self._parent = weakref.ref(parent) if parent is not None else None
        self._details_key = None

        # Allow overwriting previous attribute values with `None` when manually reloading
        self._overwriteNone = True
        # Automatically reload the object when accessing a missing attribute
        self._autoReload = CONFIG.get('plexapi.autoreload', True, bool)
        # Attribute to save batch edits for a single API call
        self._edits = None

        if data is not None:
            self._loadData(data)
        self._details_key = self._buildDetailsKey()

    def __repr__(self):
        uid = self._clean(self.firstAttr('_baseurl', 'ratingKey', 'id', 'key', 'playQueueID', 'uri', 'type'))
        name = self._clean(self.firstAttr('title', 'name', 'username', 'product', 'tag', 'value'))
        return f"<{':'.join([p for p in [self.__class__.__name__, uid, name] if p])}>"

    def __setattr__(self, attr, value):
        overwriteNone = self.__dict__.get('_overwriteNone')
        # Don't overwrite an attr with None unless it's a private variable or overwrite None is True
        if value is not None or attr.startswith('_') or attr not in self.__dict__ or overwriteNone:
            self.__dict__[attr] = value

    def _clean(self, value):
        """ Clean attr value for display in __repr__. """
        if value:
            value = str(value).replace('/library/metadata/', '')
            value = value.replace('/children', '')
            value = value.replace('/accounts/', '')
            value = value.replace('/devices/', '')
            return value.replace(' ', '-')[:20]

    def _buildItem(self, elem, cls=None, initpath=None):
        """ Factory function to build objects based on registered PLEXOBJECTS. """
        # cls is specified, build the object and return
        initpath = initpath or self._initpath
        if cls is not None:
            return cls(self._server, elem, initpath, parent=self)
        # cls is not specified, try looking it up in PLEXOBJECTS
        etype = elem.attrib.get('streamType', elem.attrib.get('tagType', elem.attrib.get('type')))
        ehash = f'{elem.tag}.{etype}' if etype else elem.tag
        if initpath == '/status/sessions':
            ehash = f"{ehash}.session"
        elif initpath.startswith('/status/sessions/history'):
            ehash = f"{ehash}.history"
        ecls = utils.getPlexObject(ehash, default=elem.tag)
        # log.debug('Building %s as %s', elem.tag, ecls.__name__)
        if ecls is not None:
            return ecls(self._server, elem, initpath, parent=self)
        raise UnknownType(f"Unknown library type <{elem.tag} type='{etype}'../>")

    def _buildItemOrNone(self, elem, cls=None, initpath=None):
        """ Calls :func:`~plexapi.base.PlexObject._buildItem` but returns
            None if elem is an unknown type.
        """
        try:
            return self._buildItem(elem, cls, initpath)
        except UnknownType:
            return None

    def _buildDetailsKey(self, **kwargs):
        """ Builds the details key with the XML include parameters.
            All parameters are included by default with the option to override each parameter
            or disable each parameter individually by setting it to False or 0.
        """
        details_key = self.key
        params = {}

        if details_key and hasattr(self, '_INCLUDES'):
            for k, v in self._INCLUDES.items():
                value = kwargs.pop(k, v)
                if value not in [False, 0, '0']:
                    params[k] = 1 if value is True else value

        if details_key and hasattr(self, '_EXCLUDES'):
            for k, v in self._EXCLUDES.items():
                value = kwargs.pop(k, None)
                if value is not None:
                    params[k] = 1 if value is True else value

        if params:
            details_key += '?' + urlencode(sorted(params.items()))
        return details_key

    def _isChildOf(self, **kwargs):
        """ Returns True if this object is a child of the given attributes.
            This will search the parent objects all the way to the top.

            Parameters:
                **kwargs (dict): The attributes and values to search for in the parent objects.
                    See all possible `**kwargs*` in :func:`~plexapi.base.PlexObject.fetchItem`.
        """
        obj = self
        while obj and obj._parent is not None:
            obj = obj._parent()
            if obj and obj._checkAttrs(obj._data, **kwargs):
                return True
        return False

    def _manuallyLoadXML(self, xml, cls=None):
        """ Manually load an XML string as a :class:`~plexapi.base.PlexObject`.

            Parameters:
                xml (str): The XML string to load.
                cls (:class:`~plexapi.base.PlexObject`): If you know the class of the
                    items to be fetched, passing this in will help the parser ensure
                    it only returns those items. By default we convert the xml elements
                    with the best guess PlexObjects based on tag and type attrs.
        """
        elem = ElementTree.fromstring(xml)
        return self._buildItemOrNone(elem, cls)

    def fetchItems(
        self,
        ekey,
        cls=None,
        container_start=None,
        container_size=None,
        maxresults=None,
        params=None,
        **kwargs,
    ):
        """ Load the specified key to find and build all items with the specified tag
            and attrs.

            Parameters:
                ekey (str or List<int>): API URL path in Plex to fetch items from. If a list of ints is passed
                    in, the key will be translated to /library/metadata/<key1,key2,key3>. This allows
                    fetching multiple items only knowing their key-ids.
                cls (:class:`~plexapi.base.PlexObject`): If you know the class of the
                    items to be fetched, passing this in will help the parser ensure
                    it only returns those items. By default we convert the xml elements
                    with the best guess PlexObjects based on tag and type attrs.
                etag (str): Only fetch items with the specified tag.
                container_start (None, int): offset to get a subset of the data
                container_size (None, int): How many items in data
                maxresults (int, optional): Only return the specified number of results.
                params (dict, optional): Any additional params to add to the request.
                **kwargs (dict): Optionally add XML attribute to filter the items.
                    See the details below for more info.

            **Filtering XML Attributes**

            Any XML attribute can be filtered when fetching results. Filtering is done before
            the Python objects are built to help keep things speedy. For example, passing in
            ``viewCount=0`` will only return matching items where the view count is ``0``.
            Note that case matters when specifying attributes. Attributes further down in the XML
            tree can be filtered by *prepending* the attribute with each element tag ``Tag__``.

            Examples:

                .. code-block:: python

                    fetchItem(ekey, viewCount=0)
                    fetchItem(ekey, contentRating="PG")
                    fetchItem(ekey, Genre__tag="Animation")
                    fetchItem(ekey, Media__videoCodec="h265")
                    fetchItem(ekey, Media__Part__container="mp4)

            Note that because some attribute names are already used as arguments to this
            function, such as ``tag``, you may still reference the attr tag by prepending an
            underscore. For example, passing in ``_tag='foobar'`` will return all items where
            ``tag='foobar'``.

            **Using PlexAPI Operators**

            Optionally, PlexAPI operators can be specified by *appending* it to the end of the
            attribute for more complex lookups. For example, passing in ``viewCount__gte=0``
            will return all items where ``viewCount >= 0``.

            List of Available Operators:

            * ``__contains``: Value contains specified arg.
            * ``__endswith``: Value ends with specified arg.
            * ``__exact``: Value matches specified arg.
            * ``__exists`` (*bool*): Value is or is not present in the attrs.
            * ``__gt``: Value is greater than specified arg.
            * ``__gte``: Value is greater than or equal to specified arg.
            * ``__icontains``: Case insensitive value contains specified arg.
            * ``__iendswith``: Case insensitive value ends with specified arg.
            * ``__iexact``: Case insensitive value matches specified arg.
            * ``__in``: Value is in a specified list or tuple.
            * ``__iregex``: Case insensitive value matches the specified regular expression.
            * ``__istartswith``: Case insensitive value starts with specified arg.
            * ``__lt``: Value is less than specified arg.
            * ``__lte``: Value is less than or equal to specified arg.
            * ``__regex``: Value matches the specified regular expression.
            * ``__startswith``: Value starts with specified arg.

            Examples:

                .. code-block:: python

                    fetchItem(ekey, viewCount__gte=0)
                    fetchItem(ekey, Media__container__in=["mp4", "mkv"])
                    fetchItem(ekey, guid__regex=r"com\\.plexapp\\.agents\\.(imdb|themoviedb)://|tt\\d+")
                    fetchItem(ekey, guid__id__regex=r"(imdb|tmdb|tvdb)://")
                    fetchItem(ekey, Media__Part__file__startswith="D:\\Movies")

        """
        if ekey is None:
            raise BadRequest('ekey was not provided')

        if isinstance(ekey, list) and all(isinstance(key, int) for key in ekey):
            ekey = f'/library/metadata/{",".join(str(key) for key in ekey)}'

        container_start = container_start or 0
        container_size = container_size or X_PLEX_CONTAINER_SIZE
        offset = container_start

        if maxresults is not None:
            container_size = min(container_size, maxresults)

        results = MediaContainer[cls](self._server, Element('MediaContainer'), initpath=ekey)
        headers = {}

        while True:
            headers['X-Plex-Container-Start'] = str(container_start)
            headers['X-Plex-Container-Size'] = str(container_size)

            data = self._server.query(ekey, headers=headers, params=params)
            subresults = self.findItems(data, cls, ekey, **kwargs)
            total_size = utils.cast(int, data.attrib.get('totalSize') or data.attrib.get('size')) or len(subresults)

            if not subresults:
                if offset > total_size:
                    log.info('container_start is greater than the number of items')

            librarySectionID = utils.cast(int, data.attrib.get('librarySectionID'))
            if librarySectionID:
                for item in subresults:
                    item.librarySectionID = librarySectionID

            results.extend(subresults)

            container_start += container_size

            if container_start > total_size:
                break

            wanted_number_of_items = total_size - offset
            if maxresults is not None:
                wanted_number_of_items = min(maxresults, wanted_number_of_items)
                container_size = min(container_size, wanted_number_of_items - len(results))

            if wanted_number_of_items <= len(results):
                break

        return results

    def fetchItem(self, ekey, cls=None, **kwargs):
        """ Load the specified key to find and build the first item with the
            specified tag and attrs. If no tag or attrs are specified then
            the first item in the result set is returned.

            Parameters:
                ekey (str or int): Path in Plex to fetch items from. If an int is passed
                    in, the key will be translated to /library/metadata/<key>. This allows
                    fetching an item only knowing its key-id.
                cls (:class:`~plexapi.base.PlexObject`): If you know the class of the
                    items to be fetched, passing this in will help the parser ensure
                    it only returns those items. By default we convert the xml elements
                    with the best guess PlexObjects based on tag and type attrs.
                etag (str): Only fetch items with the specified tag.
                **kwargs (dict): Optionally add XML attribute to filter the items.
                    See :func:`~plexapi.base.PlexObject.fetchItems` for more details
                    on how this is used.
        """
        if isinstance(ekey, int):
            ekey = f'/library/metadata/{ekey}'

        try:
            return self.fetchItems(ekey, cls, **kwargs)[0]
        except IndexError:
            clsname = cls.__name__ if cls else 'None'
            raise NotFound(f'Unable to find elem: cls={clsname}, attrs={kwargs}') from None

    def findItems(self, data, cls=None, initpath=None, rtag=None, **kwargs):
        """ Load the specified data to find and build all items with the specified tag
            and attrs. See :func:`~plexapi.base.PlexObject.fetchItem` for more details
            on how this is used.
        """
        # filter on cls attrs if specified
        if cls and cls.TAG and 'tag' not in kwargs:
            kwargs['etag'] = cls.TAG
        if cls and cls.TYPE and 'type' not in kwargs:
            kwargs['type'] = cls.TYPE
        # rtag to iter on a specific root tag using breadth-first search
        if rtag:
            data = next(utils.iterXMLBFS(data, rtag), Element('Empty'))
        # loop through all data elements to find matches
        items = MediaContainer[cls](self._server, data, initpath=initpath) if data.tag == 'MediaContainer' else []
        for elem in data:
            if self._checkAttrs(elem, **kwargs):
                item = self._buildItemOrNone(elem, cls, initpath)
                if item is not None:
                    items.append(item)
        return items

    def findItem(self, data, cls=None, initpath=None, rtag=None, **kwargs):
        """ Load the specified data to find and build the first items with the specified tag
            and attrs. See :func:`~plexapi.base.PlexObject.fetchItem` for more details
            on how this is used.
        """
        try:
            return self.findItems(data, cls, initpath, rtag, **kwargs)[0]
        except IndexError:
            return None

    def firstAttr(self, *attrs):
        """ Return the first attribute in attrs that is not None. """
        for attr in attrs:
            value = getattr(self, attr, None)
            if value is not None:
                return value

    def listAttrs(self, data, attr, rtag=None, **kwargs):
        """ Return a list of values from matching attribute. """
        results = []
        # rtag to iter on a specific root tag using breadth-first search
        if rtag:
            data = next(utils.iterXMLBFS(data, rtag), [])
        for elem in data:
            kwargs[f'{attr}__exists'] = True
            if self._checkAttrs(elem, **kwargs):
                results.append(elem.attrib.get(attr))
        return results

    def reload(self, key=None, **kwargs):
        """ Reload the data for this object.

            Parameters:
                key (string, optional): Override the key to reload.
                **kwargs (dict): A dictionary of XML include parameters to include/exclude or override.
                    See :class:`~plexapi.base.PlexPartialObject` for all the available include parameters.
                    Set parameter to True to include and False to exclude.

            Example:

                .. code-block:: python

                    from plexapi.server import PlexServer
                    plex = PlexServer('http://localhost:32400', token='xxxxxxxxxxxxxxxxxxxx')

                    # Search results are partial objects.
                    movie = plex.library.section('Movies').get('Cars')
                    movie.isPartialObject()  # Returns True

                    # Partial reload of the movie without a default include parameter.
                    # The movie object will remain as a partial object.
                    movie.reload(includeMarkers=False)
                    movie.isPartialObject()  # Returns True

                    # Full reload of the movie with all default include parameters.
                    # The movie object will be a full object.
                    movie.reload()
                    movie.isFullObject()  # Returns True

                    # Full reload of the movie with all default and extra include parameter.
                    # Including `checkFiles` will tell the Plex server to check if the file
                    # still exists and is accessible.
                    # The movie object will be a full object.
                    movie.reload(checkFiles=True)
                    movie.isFullObject()  # Returns True

        """
        return self._reload(key=key, **kwargs)

    def _reload(self, key=None, _overwriteNone=True, **kwargs):
        """ Perform the actual reload. """
        details_key = self._buildDetailsKey(**kwargs) if kwargs else self._details_key
        key = key or details_key or self.key
        if not key:
            raise Unsupported('Cannot reload an object not built from a URL.')
        self._initpath = key
        data = self._server.query(key)
        self._overwriteNone = _overwriteNone
        self._invalidateCacheAndLoadData(data[0])
        self._overwriteNone = True
        return self

    def _checkAttrs(self, elem, **kwargs):
        attrsFound = {}
        for attr, query in kwargs.items():
            attr, op, operator = self._getAttrOperator(attr)
            values = self._getAttrValue(elem, attr)
            # special case query in (None, 0, '') to include missing attr
            if op == 'exact' and not values and query in (None, 0, ''):
                return True
            # return if attr were looking for is missing
            attrsFound[attr] = False
            for value in values:
                value = self._castAttrValue(op, query, value)
                if operator(value, query):
                    attrsFound[attr] = True
                    break
        # log.debug('Checking %s for %s found: %s', elem.tag, kwargs, attrsFound)
        return all(attrsFound.values())

    def _getAttrOperator(self, attr):
        for op, operator in OPERATORS.items():
            if attr.endswith(f'__{op}'):
                attr = attr.rsplit('__', 1)[0]
                return attr, op, operator
        # default to exact match
        return attr, 'exact', OPERATORS['exact']

    def _getAttrValue(self, elem, attrstr, results=None):
        # log.debug('Fetching %s in %s', attrstr, elem.tag)
        parts = attrstr.split('__', 1)
        attr = parts[0]
        attrstr = parts[1] if len(parts) == 2 else None
        if attrstr:
            results = [] if results is None else results
            for child in (c for c in elem if c.tag.lower() == attr.lower()):
                results += self._getAttrValue(child, attrstr, results)
            return [r for r in results if r is not None]
        # check were looking for the tag
        if attr.lower() == 'etag':
            return [elem.tag]
        # loop through attrs so we can perform case-insensitive match
        for _attr, value in elem.attrib.items():
            if attr.lower() == _attr.lower():
                return [value]
        return []

    def _castAttrValue(self, op, query, value):
        if op == 'exists':
            return value
        if isinstance(query, bool):
            return bool(int(value))
        if isinstance(query, int) and '.' in value:
            return float(value)
        if isinstance(query, int):
            return int(value)
        if isinstance(query, float):
            return float(value)
        return value

    def _invalidateCacheAndLoadData(self, data):
        """Load attribute values from Plex XML response and invalidate cached properties."""
        old_data_id = id(getattr(self, '_data', None))
        self._data = data

        # If the data's object ID has changed, invalidate cached properties
        if id(data) != old_data_id:
            self._invalidateCachedProperties()

        self._loadData(data)

    def _invalidateCachedProperties(self):
        """Invalidate all cached data property values."""
        cached_props = getattr(self.__class__, '_cached_data_properties', set())

        for prop_name in cached_props:
            if prop_name in self.__dict__:
                del self.__dict__[prop_name]

    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        raise NotImplementedError('Abstract method not implemented.')

    def _findAndLoadElem(self, data, **kwargs):
        """ Find and load the first element in the data that matches the specified attributes. """
        for elem in data:
            if self._checkAttrs(elem, **kwargs):
                self._invalidateCacheAndLoadData(elem)

    @property
    def _searchType(self):
        return self.TYPE


class PlexPartialObject(PlexObject):
    """ Not all objects in the Plex listings return the complete list of elements
        for the object. This object will allow you to assume each object is complete,
        and if the specified value you request is None it will fetch the full object
        automatically and update itself.
    """
    _INCLUDES = {
        'checkFiles': 0,
        'includeAllConcerts': 0,
        'includeBandwidths': 1,
        'includeChapters': 1,
        'includeChildren': 0,
        'includeConcerts': 0,
        'includeExternalMedia': 0,
        'includeExtras': 0,
        'includeFields': 'thumbBlurHash,artBlurHash',
        'includeGeolocation': 1,
        'includeLoudnessRamps': 1,
        'includeMarkers': 1,
        'includeOnDeck': 0,
        'includePopularLeaves': 0,
        'includePreferences': 0,
        'includeRelated': 0,
        'includeRelatedCount': 0,
        'includeReviews': 0,
        'includeStations': 0,
    }
    _EXCLUDES = {
        'excludeElements': (
            'Media,Genre,Country,Guid,Rating,Collection,Director,Writer,Role,Producer,Similar,Style,Mood,Format'
        ),
        'excludeFields': 'summary,tagline',
        'skipRefresh': 1,
    }

    def __eq__(self, other):
        if isinstance(other, PlexPartialObject):
            return self.key == other.key
        return NotImplemented

    def __hash__(self):
        return hash(repr(self))

    def __iter__(self):
        yield self

    def __getattribute__(self, attr):
        # Dragons inside.. :-/
        value = super(PlexPartialObject, self).__getattribute__(attr)
        # Check a few cases where we don't want to reload
        if attr in _DONT_RELOAD_FOR_KEYS: return value
        if attr in USER_DONT_RELOAD_FOR_KEYS: return value
        if attr.startswith('_'): return value
        if value not in (None, []): return value
        if self.isFullObject(): return value
        if isinstance(self, (PlexSession, PlexHistory)): return value
        if self._autoReload is False: return value
        # Log the reload.
        clsname = self.__class__.__name__
        title = self.__dict__.get('title', self.__dict__.get('name'))
        objname = f"{clsname} '{title}'" if title else clsname
        log.debug("Reloading %s for attr '%s'", objname, attr)
        # Reload and return the value
        self._reload(_overwriteNone=False)
        return super(PlexPartialObject, self).__getattribute__(attr)

    def analyze(self):
        """ Tell Plex Media Server to performs analysis on it this item to gather
            information. Analysis includes:

            * Gather Media Properties: All of the media you add to a Library has
                properties that are useful to know–whether it's a video file, a
                music track, or one of your photos (container, codec, resolution, etc).
            * Generate Default Artwork: Artwork will automatically be grabbed from a
                video file. A background image will be pulled out as well as a
                smaller image to be used for poster/thumbnail type purposes.
            * Generate Video Preview Thumbnails: Video preview thumbnails are created,
                if you have that feature enabled. Video preview thumbnails allow
                graphical seeking in some Apps. It's also used in the Plex Web App Now
                Playing screen to show a graphical representation of where playback
                is. Video preview thumbnails creation is a CPU-intensive process akin
                to transcoding the file.
            * Generate intro video markers: Detects show intros, exposing the
                'Skip Intro' button in clients.
        """
        key = f"/{self.key.lstrip('/')}/analyze"
        self._server.query(key, method=self._server._session.put)

    def isFullObject(self):
        """ Returns True if this is already a full object. A full object means all attributes
            were populated from the api path representing only this item. For example, the
            search result for a movie often only contain a portion of the attributes a full
            object (main url) for that movie would contain.
        """
        parsed_key = urlparse(self._details_key or self.key)
        parsed_initpath = urlparse(self._initpath)
        query_key = set(parse_qsl(parsed_key.query))
        query_init = set(parse_qsl(parsed_initpath.query))
        return not self.key or (parsed_key.path == parsed_initpath.path and query_key <= query_init)

    def isPartialObject(self):
        """ Returns True if this is not a full object. """
        return not self.isFullObject()

    def isLocked(self, field: str):
        """ Returns True if the specified field is locked, otherwise False.

            Parameters:
                field (str): The name of the field.
        """
        return next((f.locked for f in self.fields if f.name == field), False)

    def _edit(self, **kwargs):
        """ Actually edit an object. """
        if isinstance(self._edits, dict):
            self._edits.update(kwargs)
            return self

        if 'type' not in kwargs:
            kwargs['type'] = utils.searchType(self._searchType)

        self.section()._edit(items=self, **kwargs)
        return self

    def edit(self, **kwargs):
        """ Edit an object.
            Note: This is a low level method and you need to know all the field/tag keys.
            See :class:`~plexapi.mixins.EditFieldMixin` and :class:`~plexapi.mixins.EditTagsMixin`
            for individual field and tag editing methods.

            Parameters:
                kwargs (dict): Dict of settings to edit.

            Example:

                .. code-block:: python

                    edits = {
                        'type': 1,
                        'id': movie.ratingKey,
                        'title.value': 'A new title',
                        'title.locked': 1,
                        'summary.value': 'This is a summary.',
                        'summary.locked': 1,
                        'collection[0].tag.tag': 'A tag',
                        'collection.locked': 1}
                    }
                    movie.edit(**edits)

        """
        return self._edit(**kwargs)

    def batchEdits(self):
        """ Enable batch editing mode to save API calls.
            Must call :func:`~plexapi.base.PlexPartialObject.saveEdits` at the end to save all the edits.
            See :class:`~plexapi.mixins.EditFieldMixin` and :class:`~plexapi.mixins.EditTagsMixin`
            for individual field and tag editing methods.

            Example:

                .. code-block:: python

                    # Batch editing multiple fields and tags in a single API call
                    Movie.batchEdits()
                    Movie.editTitle('A New Title').editSummary('A new summary').editTagline('A new tagline') \\
                        .addCollection('New Collection').removeGenre('Action').addLabel('Favorite')
                    Movie.saveEdits()

        """
        self._edits = {}
        return self

    def saveEdits(self):
        """ Save all the batch edits. The object needs to be reloaded manually,
            if required.
            See :func:`~plexapi.base.PlexPartialObject.batchEdits` for details.
        """
        if not isinstance(self._edits, dict):
            raise BadRequest('Batch editing mode not enabled. Must call `batchEdits()` first.')

        edits = self._edits
        self._edits = None
        self._edit(**edits)
        return self

    def refresh(self):
        """ Refreshing a Library or individual item causes the metadata for the item to be
            refreshed, even if it already has metadata. You can think of refreshing as
            "update metadata for the requested item even if it already has some". You should
            refresh a Library or individual item if:

            * You've changed the Library Metadata Agent.
            * You've added "Local Media Assets" (such as artwork, theme music, external
                subtitle files, etc.)
            * You want to freshen the item posters, summary, etc.
            * There's a problem with the poster image that's been downloaded.
            * Items are missing posters or other downloaded information. This is possible if
                the refresh process is interrupted (the Server is turned off, internet
                connection dies, etc).
        """
        key = f'{self.key}/refresh'
        self._server.query(key, method=self._server._session.put)

    def section(self):
        """ Returns the :class:`~plexapi.library.LibrarySection` this item belongs to. """
        return self._server.library.sectionByID(self.librarySectionID)

    def delete(self):
        """ Delete a media element. This has to be enabled under settings > server > library in plex webui. """
        try:
            return self._server.query(self.key, method=self._server._session.delete)
        except BadRequest:  # pragma: no cover
            log.error('Failed to delete %s. This could be because you '
                'have not allowed items to be deleted', self.key)
            raise

    def history(self, maxresults=None, mindate=None):
        """ Get Play History for a media item.

            Parameters:
                maxresults (int): Only return the specified number of results (optional).
                mindate (datetime): Min datetime to return results from.
        """
        return self._server.history(maxresults=maxresults, mindate=mindate, ratingKey=self.ratingKey)

    def _getWebURL(self, base=None):
        """ Get the Plex Web URL with the correct parameters.
            Private method to allow overriding parameters from subclasses.
        """
        return self._server._buildWebURL(base=base, endpoint='details', key=self.key)

    def getWebURL(self, base=None):
        """ Returns the Plex Web URL for a media item.

            Parameters:
                base (str): The base URL before the fragment (``#!``).
                    Default is https://app.plex.tv/desktop.
        """
        return self._getWebURL(base=base)

    def playQueue(self, *args, **kwargs):
        """ Returns a new :class:`~plexapi.playqueue.PlayQueue` from this media item.
            See :func:`~plexapi.playqueue.PlayQueue.create` for available parameters.
        """
        from plexapi.playqueue import PlayQueue
        return PlayQueue.create(self._server, self, *args, **kwargs)


class Playable:
    """ This is a mixin to store functions specific to media that is Playable.
        Things were getting mixed up a bit when dealing with Shows, Season, Artists,
        Albums which are all not playable.

        Attributes:
            playlistItemID (int): Playlist item ID (only populated for :class:`~plexapi.playlist.Playlist` items).
            playQueueItemID (int): PlayQueue item ID (only populated for :class:`~plexapi.playlist.PlayQueue` items).
    """

    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        self.playlistItemID = utils.cast(int, data.attrib.get('playlistItemID'))    # playlist
        self.playQueueItemID = utils.cast(int, data.attrib.get('playQueueItemID'))  # playqueue

    def getStreamURL(self, **kwargs):
        """ Returns a stream url that may be used by external applications such as VLC.

            Parameters:
                **kwargs (dict): optional parameters to manipulate the playback when accessing
                    the stream. A few known parameters include: maxVideoBitrate, videoResolution
                    offset, copyts, protocol, mediaIndex, partIndex, platform.

            Raises:
                :exc:`~plexapi.exceptions.Unsupported`: When the item doesn't support fetching a stream URL.
        """
        if self.TYPE not in ('movie', 'episode', 'track', 'clip'):
            raise Unsupported(f'Fetching stream URL for {self.TYPE} is unsupported.')

        mvb = kwargs.pop('maxVideoBitrate', None)
        vr = kwargs.pop('videoResolution', '')
        protocol = kwargs.pop('protocol', None)

        params = {
            'path': self.key,
            'mediaIndex': kwargs.pop('mediaIndex', 0),
            'partIndex': kwargs.pop('mediaIndex', 0),
            'protocol': protocol,
            'fastSeek': kwargs.pop('fastSeek', 1),
            'copyts': kwargs.pop('copyts', 1),
            'offset': kwargs.pop('offset', 0),
            'maxVideoBitrate': max(mvb, 64) if mvb else None,
            'videoResolution': vr if re.match(r'^\d+x\d+$', vr) else None,
            'X-Plex-Platform': kwargs.pop('platform', 'Chrome')
        }
        params.update(kwargs)

        # remove None values
        params = {k: v for k, v in params.items() if v is not None}
        streamtype = 'audio' if self.TYPE in ('track', 'album') else 'video'
        ext = 'mpd' if protocol == 'dash' else 'm3u8'

        return self._server.url(
            f'/{streamtype}/:/transcode/universal/start.{ext}?{urlencode(params)}',
            includeToken=True
        )

    def iterParts(self):
        """ Iterates over the parts of this media item. """
        for item in self.media:
            for part in item.parts:
                yield part

    def videoStreams(self):
        """ Returns a list of :class:`~plexapi.media.videoStream` objects for all MediaParts. """
        if self.isPartialObject():
            self.reload()
        return sum((part.videoStreams() for part in self.iterParts()), [])

    def audioStreams(self):
        """ Returns a list of :class:`~plexapi.media.AudioStream` objects for all MediaParts. """
        if self.isPartialObject():
            self.reload()
        return sum((part.audioStreams() for part in self.iterParts()), [])

    def subtitleStreams(self):
        """ Returns a list of :class:`~plexapi.media.SubtitleStream` objects for all MediaParts. """
        if self.isPartialObject():
            self.reload()
        return sum((part.subtitleStreams() for part in self.iterParts()), [])

    def lyricStreams(self):
        """ Returns a list of :class:`~plexapi.media.LyricStream` objects for all MediaParts. """
        if self.isPartialObject():
            self.reload()
        return sum((part.lyricStreams() for part in self.iterParts()), [])

    def play(self, client):
        """ Start playback on the specified client.

            Parameters:
                client (:class:`~plexapi.client.PlexClient`): Client to start playing on.
        """
        client.playMedia(self)

    def download(self, savepath=None, keep_original_name=False, **kwargs):
        """ Downloads the media item to the specified location. Returns a list of
            filepaths that have been saved to disk.

            Parameters:
                savepath (str): Defaults to current working dir.
                keep_original_name (bool): True to keep the original filename otherwise
                    a friendlier filename is generated. See filenames below.
                **kwargs (dict): Additional options passed into :func:`~plexapi.audio.Track.getStreamURL`
                    to download a transcoded stream, otherwise the media item will be downloaded
                    as-is and saved to disk.

            **Filenames**

            * Movie: ``<title> (<year>)``
            * Episode: ``<show title> - s00e00 - <episode title>``
            * Track: ``<artist title> - <album title> - 00 - <track title>``
            * Photo: ``<photoalbum title> - <photo/clip title>`` or ``<photo/clip title>``
        """
        filepaths = []
        parts = [i for i in self.iterParts() if i]

        for part in parts:
            if not keep_original_name:
                filename = utils.cleanFilename(f'{self._prettyfilename()}.{part.container}')
            else:
                filename = part.file

            if kwargs:
                # So this seems to be a a lot slower but allows transcode.
                kwargs['mediaIndex'] = self.media.index(part._parent())
                kwargs['partIndex'] = part._parent().parts.index(part)
                download_url = self.getStreamURL(**kwargs)
            else:
                download_url = self._server.url(f'{part.key}?download=1')

            filepath = utils.download(
                download_url,
                self._server._token,
                filename=filename,
                savepath=savepath,
                session=self._server._session
            )

            if filepath:
                filepaths.append(filepath)

        return filepaths

    def updateProgress(self, time, state='stopped'):
        """ Set the watched progress for this video.

            Note that setting the time to 0 will not work.
            Use :func:`~plexapi.mixins.PlayedUnplayedMixin.markPlayed` or
            :func:`~plexapi.mixins.PlayedUnplayedMixin.markUnplayed` to achieve
            that goal.

            Parameters:
                time (int): milliseconds watched
                state (string): state of the video, default 'stopped'
        """
        key = f'/:/progress?key={self.ratingKey}&identifier=com.plexapp.plugins.library&time={time}&state={state}'
        self._server.query(key)
        return self

    def updateTimeline(self, time, state='stopped', duration=None):
        """ Set the timeline progress for this video.

            Parameters:
                time (int): milliseconds watched
                state (string): state of the video, default 'stopped'
                duration (int): duration of the item
        """
        durationStr = '&duration='
        if duration is not None:
            durationStr = durationStr + str(duration)
        else:
            durationStr = durationStr + str(self.duration)
        key = (f'/:/timeline?ratingKey={self.ratingKey}&key={self.key}&'
               f'identifier=com.plexapp.plugins.library&time={int(time)}&state={state}{durationStr}')
        self._server.query(key)
        return self


class PlexSession:
    """ This is a mixin to store functions specific to media that is a Plex Session.

        Attributes:
            live (bool): True if this is a live tv session.
            player (:class:`~plexapi.client.PlexClient`): PlexClient object for the session.
            session (:class:`~plexapi.media.Session`): Session object for the session
                if the session is using bandwidth (None otherwise).
            sessionKey (int): The session key for the session.
            transcodeSession (:class:`~plexapi.media.TranscodeSession`): TranscodeSession object
                if item is being transcoded (None otherwise).
    """

    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        self.live = utils.cast(bool, data.attrib.get('live', '0'))
        self.sessionKey = utils.cast(int, data.attrib.get('sessionKey'))

        user = data.find('User')
        self._username = user.attrib.get('title')
        self._userId = utils.cast(int, user.attrib.get('id'))

        # For backwards compatibility
        self.usernames = [self._username] if self._username else []
        # `players`, `sessions`, and `transcodeSessions` are returned with properties
        # to support lazy loading. See PR #1510

    @cached_data_property
    def player(self):
        return self.findItem(self._data, etag='Player')

    @cached_data_property
    def session(self):
        return self.findItem(self._data, etag='Session')

    @cached_data_property
    def transcodeSession(self):
        return self.findItem(self._data, etag='TranscodeSession')

    @property
    def players(self):
        return [self.player] if self.player else []

    @property
    def sessions(self):
        return [self.session] if self.session else []

    @property
    def transcodeSessions(self):
        return [self.transcodeSession] if self.transcodeSession else []

    @cached_data_property
    def user(self):
        """ Returns the :class:`~plexapi.myplex.MyPlexAccount` object (for admin)
            or :class:`~plexapi.myplex.MyPlexUser` object (for users) for this session.
        """
        myPlexAccount = self._server.myPlexAccount()
        if self._userId == 1:
            return myPlexAccount

        return myPlexAccount.user(self._username)

    def reload(self):
        """ Reload the data for the session.
            Note: This will return the object as-is if the session is no longer active.
        """
        return self._reload()

    def _reload(self, **kwargs):
        """ Reload the data for the session. """
        key = self._initpath
        data = self._server.query(key)
        self._findAndLoadElem(data, sessionKey=str(self.sessionKey))
        return self

    def source(self):
        """ Return the source media object for the session. """
        return self.fetchItem(self._details_key)

    def stop(self, reason=''):
        """ Stop playback for the session.

            Parameters:
                reason (str): Message displayed to the user for stopping playback.
        """
        params = {
            'sessionId': self.session.id,
            'reason': reason,
        }
        key = '/status/sessions/terminate'
        return self._server.query(key, params=params)


class PlexHistory:
    """ This is a mixin to store functions specific to media that is a Plex history item.

        Attributes:
            accountID (int): The associated :class:`~plexapi.server.SystemAccount` ID.
            deviceID (int): The associated :class:`~plexapi.server.SystemDevice` ID.
            historyKey (str): API URL (/status/sessions/history/<historyID>).
            viewedAt (datetime): Datetime item was last watched.
    """

    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        self.accountID = utils.cast(int, data.attrib.get('accountID'))
        self.deviceID = utils.cast(int, data.attrib.get('deviceID'))
        self.historyKey = data.attrib.get('historyKey')
        self.viewedAt = utils.toDatetime(data.attrib.get('viewedAt'))

    def _reload(self, **kwargs):
        """ Reload the data for the history entry. """
        raise NotImplementedError('History objects cannot be reloaded. Use source() to get the source media item.')

    def source(self):
        """ Return the source media object for the history entry
            or None if the media no longer exists on the server.
        """
        return self.fetchItem(self._details_key) if self._details_key else None

    def delete(self):
        """ Delete the history entry. """
        return self._server.query(self.historyKey, method=self._server._session.delete)


class MediaContainer(
    Generic[PlexObjectT],
    List[PlexObjectT],
    PlexObject,
):
    """ Represents a single MediaContainer.

        Attributes:
            TAG (str): 'MediaContainer'
            allowSync (int): Sync/Download is allowed/disallowed for feature.
            augmentationKey (str): API URL (/library/metadata/augmentations/<augmentationKey>).
            identifier (str): "com.plexapp.plugins.library"
            librarySectionID (int): :class:`~plexapi.library.LibrarySection` ID.
            librarySectionTitle (str): :class:`~plexapi.library.LibrarySection` title.
            librarySectionUUID (str): :class:`~plexapi.library.LibrarySection` UUID.
            mediaTagPrefix (str): "/system/bundle/media/flags/"
            mediaTagVersion (int): Unknown
            offset (int): The offset of current results.
            size (int): The number of items in the hub.
            totalSize (int): The total number of items for the query.

    """
    TAG = 'MediaContainer'

    def __init__(
        self,
        server: "PlexServer",
        data: Element,
        *args: PlexObjectT,
        initpath: Optional[str] = None,
        parent: Optional[PlexObject] = None,
    ) -> None:
        # super calls Generic.__init__ which calls list.__init__ eventually
        super().__init__(*args)
        PlexObject.__init__(self, server, data, initpath, parent)

    def extend(
        self: MediaContainerT,
        __iterable: Union[Iterable[PlexObjectT], MediaContainerT],
    ) -> None:
        curr_size = self.size if self.size is not None else len(self)
        super().extend(__iterable)
        # update size, totalSize, and offset
        if not isinstance(__iterable, MediaContainer):
            return

        # prefer the totalSize of the new iterable even if it is smaller
        self.totalSize = (
            __iterable.totalSize
            if __iterable.totalSize is not None
            else self.totalSize
        )  # ideally both should be equal

        # the size of the new iterable is added to the current size
        self.size = curr_size + (
            __iterable.size if __iterable.size is not None else len(__iterable)
        )

        # the offset is the minimum of the two, prefering older values
        if self.offset is not None and __iterable.offset is not None:
            self.offset = min(self.offset, __iterable.offset)
        else:
            self.offset = (
                self.offset if self.offset is not None else __iterable.offset
            )

        # for all other attributes, overwrite with the new iterable's values if previously None
        for key in (
            "allowSync",
            "augmentationKey",
            "identifier",
            "librarySectionID",
            "librarySectionTitle",
            "librarySectionUUID",
            "mediaTagPrefix",
            "mediaTagVersion",
        ):
            if (not hasattr(self, key)) or (getattr(self, key) is None):
                if not hasattr(__iterable, key):
                    continue
                setattr(self, key, getattr(__iterable, key))

    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        self.allowSync = utils.cast(int, data.attrib.get('allowSync'))
        self.augmentationKey = data.attrib.get('augmentationKey')
        self.identifier = data.attrib.get('identifier')
        self.librarySectionID = utils.cast(int, data.attrib.get('librarySectionID'))
        self.librarySectionTitle = data.attrib.get('librarySectionTitle')
        self.librarySectionUUID = data.attrib.get('librarySectionUUID')
        self.mediaTagPrefix = data.attrib.get('mediaTagPrefix')
        self.mediaTagVersion = data.attrib.get('mediaTagVersion')
        self.offset = utils.cast(int, data.attrib.get("offset"))
        self.size = utils.cast(int, data.attrib.get('size'))
        self.totalSize = utils.cast(int, data.attrib.get("totalSize"))
