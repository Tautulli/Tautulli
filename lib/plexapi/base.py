# -*- coding: utf-8 -*-
import re
import weakref
from urllib.parse import quote_plus, urlencode
from xml.etree import ElementTree

from plexapi import log, utils
from plexapi.exceptions import BadRequest, NotFound, UnknownType, Unsupported

USER_DONT_RELOAD_FOR_KEYS = set()
_DONT_RELOAD_FOR_KEYS = {'key', 'session'}
_DONT_OVERWRITE_SESSION_KEYS = {'usernames', 'players', 'transcodeSessions', 'session'}
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
    'istartswith': lambda v, q: v.lower().startswith(q),
    'endswith': lambda v, q: v.endswith(q),
    'iendswith': lambda v, q: v.lower().endswith(q),
    'exists': lambda v, q: v is not None if q else v is None,
    'regex': lambda v, q: re.match(q, v),
    'iregex': lambda v, q: re.match(q, v, flags=re.IGNORECASE),
}


class PlexObject(object):
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
        if data is not None:
            self._loadData(data)
        self._details_key = self._buildDetailsKey()
        self._autoReload = False

    def __repr__(self):
        uid = self._clean(self.firstAttr('_baseurl', 'key', 'id', 'playQueueID', 'uri'))
        name = self._clean(self.firstAttr('title', 'name', 'username', 'product', 'tag', 'value'))
        return '<%s>' % ':'.join([p for p in [self.__class__.__name__, uid, name] if p])

    def __setattr__(self, attr, value):
        # Don't overwrite session specific attr with []
        if attr in _DONT_OVERWRITE_SESSION_KEYS and value == []:
            value = getattr(self, attr, [])

        autoReload = self.__dict__.get('_autoReload')
        # Don't overwrite an attr with None unless it's a private variable or not auto reload
        if value is not None or attr.startswith('_') or attr not in self.__dict__ or not autoReload:
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
        ehash = '%s.%s' % (elem.tag, etype) if etype else elem.tag
        ecls = utils.PLEXOBJECTS.get(ehash, utils.PLEXOBJECTS.get(elem.tag))
        # log.debug('Building %s as %s', elem.tag, ecls.__name__)
        if ecls is not None:
            return ecls(self._server, elem, initpath)
        raise UnknownType("Unknown library type <%s type='%s'../>" % (elem.tag, etype))

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
        if details_key and hasattr(self, '_INCLUDES'):
            includes = {}
            for k, v in self._INCLUDES.items():
                value = kwargs.get(k, v)
                if value not in [False, 0, '0']:
                    includes[k] = 1 if value is True else value
            if includes:
                details_key += '?' + urlencode(sorted(includes.items()))
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
        if ekey is None:
            raise BadRequest('ekey was not provided')
        if isinstance(ekey, int):
            ekey = '/library/metadata/%s' % ekey
        for elem in self._server.query(ekey):
            if self._checkAttrs(elem, **kwargs):
                return self._buildItem(elem, cls, ekey)
        clsname = cls.__name__ if cls else 'None'
        raise NotFound('Unable to find elem: cls=%s, attrs=%s' % (clsname, kwargs))

    def fetchItems(self, ekey, cls=None, container_start=None, container_size=None, **kwargs):
        """ Load the specified key to find and build all items with the specified tag
            and attrs.

            Parameters:
                ekey (str): API URL path in Plex to fetch items from.
                cls (:class:`~plexapi.base.PlexObject`): If you know the class of the
                    items to be fetched, passing this in will help the parser ensure
                    it only returns those items. By default we convert the xml elements
                    with the best guess PlexObjects based on tag and type attrs.
                etag (str): Only fetch items with the specified tag.
                container_start (None, int): offset to get a subset of the data
                container_size (None, int): How many items in data
                **kwargs (dict): Optionally add XML attribute to filter the items.
                    See the details below for more info.

            **Filtering XML Attributes**

            Any XML attribute can be filtered when fetching results. Filtering is done before
            the Python objects are built to help keep things speedy. For example, passing in
            ``viewCount=0`` will only return matching items where the view count is ``0``.
            Note that case matters when specifying attributes. Attributes futher down in the XML
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
            * ``__icontains``: Case insensative value contains specified arg.
            * ``__iendswith``: Case insensative value ends with specified arg.
            * ``__iexact``: Case insensative value matches specified arg.
            * ``__in``: Value is in a specified list or tuple.
            * ``__iregex``: Case insensative value matches the specified regular expression.
            * ``__istartswith``: Case insensative value starts with specified arg.
            * ``__lt``: Value is less than specified arg.
            * ``__lte``: Value is less than or equal to specified arg.
            * ``__regex``: Value matches the specified regular expression.
            * ``__startswith``: Value starts with specified arg.

            Examples:

                .. code-block:: python

                    fetchItem(ekey, viewCount__gte=0)
                    fetchItem(ekey, Media__container__in=["mp4", "mkv"])
                    fetchItem(ekey, guid__iregex=r"(imdb:\/\/|themoviedb:\/\/)")
                    fetchItem(ekey, Media__Part__file__startswith="D:\\Movies")

        """
        url_kw = {}
        if container_start is not None:
            url_kw["X-Plex-Container-Start"] = container_start
        if container_size is not None:
            url_kw["X-Plex-Container-Size"] = container_size

        if ekey is None:
            raise BadRequest('ekey was not provided')
        data = self._server.query(ekey, params=url_kw)
        items = self.findItems(data, cls, ekey, **kwargs)

        librarySectionID = utils.cast(int, data.attrib.get('librarySectionID'))
        if librarySectionID:
            for item in items:
                item.librarySectionID = librarySectionID
        return items

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
        # rtag to iter on a specific root tag
        if rtag:
            data = next(data.iter(rtag), [])
        # loop through all data elements to find matches
        items = []
        for elem in data:
            if self._checkAttrs(elem, **kwargs):
                item = self._buildItemOrNone(elem, cls, initpath)
                if item is not None:
                    items.append(item)
        return items

    def firstAttr(self, *attrs):
        """ Return the first attribute in attrs that is not None. """
        for attr in attrs:
            value = getattr(self, attr, None)
            if value is not None:
                return value

    def listAttrs(self, data, attr, rtag=None, **kwargs):
        """ Return a list of values from matching attribute. """
        results = []
        # rtag to iter on a specific root tag
        if rtag:
            data = next(data.iter(rtag), [])
        for elem in data:
            kwargs['%s__exists' % attr] = True
            if self._checkAttrs(elem, **kwargs):
                results.append(elem.attrib.get(attr))
        return results

    def reload(self, key=None, **kwargs):
        """ Reload the data for this object from self.key.

            Parameters:
                key (string, optional): Override the key to reload.
                **kwargs (dict): A dictionary of XML include parameters to exclude or override.
                    All parameters are included by default with the option to override each parameter
                    or disable each parameter individually by setting it to False or 0.
                    See :class:`~plexapi.base.PlexPartialObject` for all the available include parameters.

            Example:

                .. code-block:: python

                    from plexapi.server import PlexServer
                    plex = PlexServer('http://localhost:32400', token='xxxxxxxxxxxxxxxxxxxx')
                    movie = plex.library.section('Movies').get('Cars')

                    # Partial reload of the movie without the `checkFiles` parameter.
                    # Excluding `checkFiles` will prevent the Plex server from reading the
                    # file to check if the file still exists and is accessible.
                    # The movie object will remain as a partial object.
                    movie.reload(checkFiles=False)
                    movie.isPartialObject()  # Returns True

                    # Full reload of the movie with all include parameters.
                    # The movie object will be a full object.
                    movie.reload()
                    movie.isFullObject()  # Returns True

        """
        return self._reload(key=key, **kwargs)

    def _reload(self, key=None, _autoReload=False, **kwargs):
        """ Perform the actual reload. """
        details_key = self._buildDetailsKey(**kwargs) if kwargs else self._details_key
        key = key or details_key or self.key
        if not key:
            raise Unsupported('Cannot reload an object not built from a URL.')
        self._initpath = key
        data = self._server.query(key)
        self._autoReload = _autoReload
        self._loadData(data[0])
        self._autoReload = False
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
            if attr.endswith('__%s' % op):
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
            for child in [c for c in elem if c.tag.lower() == attr.lower()]:
                results += self._getAttrValue(child, attrstr, results)
            return [r for r in results if r is not None]
        # check were looking for the tag
        if attr.lower() == 'etag':
            return [elem.tag]
        # loop through attrs so we can perform case-insensative match
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

    def _loadData(self, data):
        raise NotImplementedError('Abstract method not implemented.')


class PlexPartialObject(PlexObject):
    """ Not all objects in the Plex listings return the complete list of elements
        for the object. This object will allow you to assume each object is complete,
        and if the specified value you request is None it will fetch the full object
        automatically and update itself.
    """
    _INCLUDES = {
        'checkFiles': 1,
        'includeAllConcerts': 1,
        'includeBandwidths': 1,
        'includeChapters': 1,
        'includeChildren': 1,
        'includeConcerts': 1,
        'includeExternalMedia': 1,
        'includeExtras': 1,
        'includeFields': 'thumbBlurHash,artBlurHash',
        'includeGeolocation': 1,
        'includeLoudnessRamps': 1,
        'includeMarkers': 1,
        'includeOnDeck': 1,
        'includePopularLeaves': 1,
        'includePreferences': 1,
        'includeRelated': 1,
        'includeRelatedCount': 1,
        'includeReviews': 1,
        'includeStations': 1
    }

    def __eq__(self, other):
        return other not in [None, []] and self.key == other.key

    def __hash__(self):
        return hash(repr(self))

    def __iter__(self):
        yield self

    def __getattribute__(self, attr):
        # Dragons inside.. :-/
        value = super(PlexPartialObject, self).__getattribute__(attr)
        # Check a few cases where we dont want to reload
        if attr in _DONT_RELOAD_FOR_KEYS: return value
        if attr in _DONT_OVERWRITE_SESSION_KEYS: return value
        if attr in USER_DONT_RELOAD_FOR_KEYS: return value
        if attr.startswith('_'): return value
        if value not in (None, []): return value
        if self.isFullObject(): return value
        # Log the reload.
        clsname = self.__class__.__name__
        title = self.__dict__.get('title', self.__dict__.get('name'))
        objname = "%s '%s'" % (clsname, title) if title else clsname
        log.debug("Reloading %s for attr '%s'", objname, attr)
        # Reload and return the value
        self._reload(_autoReload=True)
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
        key = '/%s/analyze' % self.key.lstrip('/')
        self._server.query(key, method=self._server._session.put)

    def isFullObject(self):
        """ Returns True if this is already a full object. A full object means all attributes
            were populated from the api path representing only this item. For example, the
            search result for a movie often only contain a portion of the attributes a full
            object (main url) for that movie would contain.
        """
        return not self.key or (self._details_key or self.key) == self._initpath

    def isPartialObject(self):
        """ Returns True if this is not a full object. """
        return not self.isFullObject()

    def edit(self, **kwargs):
        """ Edit an object.

            Parameters:
                kwargs (dict): Dict of settings to edit.

            Example:
                {'type': 1,
                 'id': movie.ratingKey,
                 'collection[0].tag.tag': 'Super',
                 'collection.locked': 0}
        """
        if 'id' not in kwargs:
            kwargs['id'] = self.ratingKey
        if 'type' not in kwargs:
            kwargs['type'] = utils.searchType(self.type)

        part = '/library/sections/%s/all?%s' % (self.librarySectionID,
                                                urlencode(kwargs))
        self._server.query(part, method=self._server._session.put)

    def _edit_tags(self, tag, items, locked=True, remove=False):
        """ Helper to edit tags.

            Parameters:
                tag (str): Tag name.
                items (list): List of tags to add.
                locked (bool): True to lock the field.
                remove (bool): True to remove the tags in items.
        """
        if not isinstance(items, list):
            items = [items]
        value = getattr(self, utils.tag_plural(tag))
        existing_tags = [t.tag for t in value if t and remove is False]
        tag_edits = utils.tag_helper(tag, existing_tags + items, locked, remove)
        self.edit(**tag_edits)

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
        key = '%s/refresh' % self.key
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

    def history(self, maxresults=9999999, mindate=None):
        """ Get Play History for a media item.
            Parameters:
                maxresults (int): Only return the specified number of results (optional).
                mindate (datetime): Min datetime to return results from.
        """
        return self._server.history(maxresults=maxresults, mindate=mindate, ratingKey=self.ratingKey)


class Playable(object):
    """ This is a general place to store functions specific to media that is Playable.
        Things were getting mixed up a bit when dealing with Shows, Season, Artists,
        Albums which are all not playable.

        Attributes:
            sessionKey (int): Active session key.
            usernames (str): Username of the person playing this item (for active sessions).
            players (:class:`~plexapi.client.PlexClient`): Client objects playing this item (for active sessions).
            session (:class:`~plexapi.media.Session`): Session object, for a playing media file.
            transcodeSessions (:class:`~plexapi.media.TranscodeSession`): Transcode Session object
                if item is being transcoded (None otherwise).
            viewedAt (datetime): Datetime item was last viewed (history).
            accountID (int): The associated :class:`~plexapi.server.SystemAccount` ID.
            deviceID (int): The associated :class:`~plexapi.server.SystemDevice` ID.
            playlistItemID (int): Playlist item ID (only populated for :class:`~plexapi.playlist.Playlist` items).
            playQueueItemID (int): PlayQueue item ID (only populated for :class:`~plexapi.playlist.PlayQueue` items).
    """

    def _loadData(self, data):
        self.sessionKey = utils.cast(int, data.attrib.get('sessionKey'))            # session
        self.usernames = self.listAttrs(data, 'title', etag='User')                 # session
        self.players = self.findItems(data, etag='Player')                          # session
        self.transcodeSessions = self.findItems(data, etag='TranscodeSession')      # session
        self.session = self.findItems(data, etag='Session')                         # session
        self.viewedAt = utils.toDatetime(data.attrib.get('viewedAt'))               # history
        self.accountID = utils.cast(int, data.attrib.get('accountID'))              # history
        self.deviceID = utils.cast(int, data.attrib.get('deviceID'))                # history
        self.playlistItemID = utils.cast(int, data.attrib.get('playlistItemID'))    # playlist
        self.playQueueItemID = utils.cast(int, data.attrib.get('playQueueItemID'))  # playqueue

    def getStreamURL(self, **params):
        """ Returns a stream url that may be used by external applications such as VLC.

            Parameters:
                **params (dict): optional parameters to manipulate the playback when accessing
                    the stream. A few known parameters include: maxVideoBitrate, videoResolution
                    offset, copyts, protocol, mediaIndex, platform.

            Raises:
                :exc:`~plexapi.exceptions.Unsupported`: When the item doesn't support fetching a stream URL.
        """
        if self.TYPE not in ('movie', 'episode', 'track', 'clip'):
            raise Unsupported('Fetching stream URL for %s is unsupported.' % self.TYPE)
        mvb = params.get('maxVideoBitrate')
        vr = params.get('videoResolution', '')
        params = {
            'path': self.key,
            'offset': params.get('offset', 0),
            'copyts': params.get('copyts', 1),
            'protocol': params.get('protocol'),
            'mediaIndex': params.get('mediaIndex', 0),
            'X-Plex-Platform': params.get('platform', 'Chrome'),
            'maxVideoBitrate': max(mvb, 64) if mvb else None,
            'videoResolution': vr if re.match(r'^\d+x\d+$', vr) else None
        }
        # remove None values
        params = {k: v for k, v in params.items() if v is not None}
        streamtype = 'audio' if self.TYPE in ('track', 'album') else 'video'
        # sort the keys since the randomness fucks with my tests..
        sorted_params = sorted(params.items(), key=lambda val: val[0])
        return self._server.url('/%s/:/transcode/universal/start.m3u8?%s' %
            (streamtype, urlencode(sorted_params)), includeToken=True)

    def iterParts(self):
        """ Iterates over the parts of this media item. """
        for item in self.media:
            for part in item.parts:
                yield part

    def play(self, client):
        """ Start playback on the specified client.

            Parameters:
                client (:class:`~plexapi.client.PlexClient`): Client to start playing on.
        """
        client.playMedia(self)

    def download(self, savepath=None, keep_original_name=False, **kwargs):
        """ Downloads this items media to the specified location. Returns a list of
            filepaths that have been saved to disk.

            Parameters:
                savepath (str): Title of the track to return.
                keep_original_name (bool): Set True to keep the original filename as stored in
                    the Plex server. False will create a new filename with the format
                    "<Artist> - <Album> <Track>".
                kwargs (dict): If specified, a :func:`~plexapi.audio.Track.getStreamURL` will
                    be returned and the additional arguments passed in will be sent to that
                    function. If kwargs is not specified, the media items will be downloaded
                    and saved to disk.
        """
        filepaths = []
        locations = [i for i in self.iterParts() if i]
        for location in locations:
            filename = location.file
            if keep_original_name is False:
                filename = '%s.%s' % (self._prettyfilename(), location.container)
            # So this seems to be a alot slower but allows transcode.
            if kwargs:
                download_url = self.getStreamURL(**kwargs)
            else:
                download_url = self._server.url('%s?download=1' % location.key)
            filepath = utils.download(download_url, self._server._token, filename=filename,
                savepath=savepath, session=self._server._session)
            if filepath:
                filepaths.append(filepath)
        return filepaths

    def stop(self, reason=''):
        """ Stop playback for a media item. """
        key = '/status/sessions/terminate?sessionId=%s&reason=%s' % (self.session[0].id, quote_plus(reason))
        return self._server.query(key)

    def updateProgress(self, time, state='stopped'):
        """ Set the watched progress for this video.

        Note that setting the time to 0 will not work.
        Use `markWatched` or `markUnwatched` to achieve
        that goal.

            Parameters:
                time (int): milliseconds watched
                state (string): state of the video, default 'stopped'
        """
        key = '/:/progress?key=%s&identifier=com.plexapp.plugins.library&time=%d&state=%s' % (self.ratingKey,
                                                                                              time, state)
        self._server.query(key)
        self._reload(_autoReload=True)

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
        key = '/:/timeline?ratingKey=%s&key=%s&identifier=com.plexapp.plugins.library&time=%d&state=%s%s'
        key %= (self.ratingKey, self.key, time, state, durationStr)
        self._server.query(key)
        self._reload(_autoReload=True)


class MediaContainer(PlexObject):
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
            size (int): The number of items in the hub.

    """
    TAG = 'MediaContainer'

    def _loadData(self, data):
        self._data = data
        self.allowSync = utils.cast(int, data.attrib.get('allowSync'))
        self.augmentationKey = data.attrib.get('augmentationKey')
        self.identifier = data.attrib.get('identifier')
        self.librarySectionID = utils.cast(int, data.attrib.get('librarySectionID'))
        self.librarySectionTitle = data.attrib.get('librarySectionTitle')
        self.librarySectionUUID = data.attrib.get('librarySectionUUID')
        self.mediaTagPrefix = data.attrib.get('mediaTagPrefix')
        self.mediaTagVersion = data.attrib.get('mediaTagVersion')
        self.size = utils.cast(int, data.attrib.get('size'))
