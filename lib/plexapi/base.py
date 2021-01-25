# -*- coding: utf-8 -*-
import re
import weakref
from urllib.parse import quote_plus, urlencode

from plexapi import log, utils
from plexapi.exceptions import BadRequest, NotFound, UnknownType, Unsupported
from plexapi.utils import tag_helper

DONT_RELOAD_FOR_KEYS = ['key', 'session']
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
        self._parent = weakref.ref(parent) if parent else None
        if data is not None:
            self._loadData(data)
        self._details_key = self._buildDetailsKey()

    def __repr__(self):
        uid = self._clean(self.firstAttr('_baseurl', 'key', 'id', 'playQueueID', 'uri'))
        name = self._clean(self.firstAttr('title', 'name', 'username', 'product', 'tag', 'value'))
        return '<%s>' % ':'.join([p for p in [self.__class__.__name__, uid, name] if p])

    def __setattr__(self, attr, value):
        # Don't overwrite an attr with None or [] unless it's a private variable
        if value not in [None, []] or attr.startswith('_') or attr not in self.__dict__:
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
        while obj._parent is not None:
            obj = obj._parent()
            if obj._checkAttrs(obj._data, **kwargs):
                return True
        return False

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
                **kwargs (dict): Optionally add attribute filters on the items to fetch. For
                    example, passing in viewCount=0 will only return matching items. Filtering
                    is done before the Python objects are built to help keep things speedy.
                    Note: Because some attribute names are already used as arguments to this
                    function, such as 'tag', you may still reference the attr tag byappending
                    an underscore. For example, passing in _tag='foobar' will return all items
                    where tag='foobar'. Also Note: Case very much matters when specifying kwargs
                    -- Optionally, operators can be specified by append it
                    to the end of the attribute name for more complex lookups. For example,
                    passing in viewCount__gte=0 will return all items where viewCount >= 0.
                    Available operations include:

                    * __contains: Value contains specified arg.
                    * __endswith: Value ends with specified arg.
                    * __exact: Value matches specified arg.
                    * __exists (bool): Value is or is not present in the attrs.
                    * __gt: Value is greater than specified arg.
                    * __gte: Value is greater than or equal to specified arg.
                    * __icontains: Case insensative value contains specified arg.
                    * __iendswith: Case insensative value ends with specified arg.
                    * __iexact: Case insensative value matches specified arg.
                    * __in: Value is in a specified list or tuple.
                    * __iregex: Case insensative value matches the specified regular expression.
                    * __istartswith: Case insensative value starts with specified arg.
                    * __lt: Value is less than specified arg.
                    * __lte: Value is less than or equal to specified arg.
                    * __regex: Value matches the specified regular expression.
                    * __startswith: Value starts with specified arg.
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
            and attrs. See :func:`~plexapi.base.PlexObject.fetchItem` for more details
            on how this is used.

            Parameters:
                container_start (None, int): offset to get a subset of the data
                container_size (None, int): How many items in data

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

        librarySectionID = data.attrib.get('librarySectionID')
        if librarySectionID:
            for item in items:
                item.librarySectionID = librarySectionID
        return items

    def findItems(self, data, cls=None, initpath=None, **kwargs):
        """ Load the specified data to find and build all items with the specified tag
            and attrs. See :func:`~plexapi.base.PlexObject.fetchItem` for more details
            on how this is used.
        """
        # filter on cls attrs if specified
        if cls and cls.TAG and 'tag' not in kwargs:
            kwargs['etag'] = cls.TAG
        if cls and cls.TYPE and 'type' not in kwargs:
            kwargs['type'] = cls.TYPE
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
            value = self.__dict__.get(attr)
            if value is not None:
                return value

    def listAttrs(self, data, attr, **kwargs):
        """ Return a list of values from matching attribute. """
        results = []
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
        details_key = self._buildDetailsKey(**kwargs) if kwargs else self._details_key
        key = key or details_key or self.key
        if not key:
            raise Unsupported('Cannot reload an object not built from a URL.')
        self._initpath = key
        data = self._server.query(key)
        self._loadData(data[0])
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
        if attr in DONT_RELOAD_FOR_KEYS: return value
        if attr.startswith('_'): return value
        if value not in (None, []): return value
        if self.isFullObject(): return value
        # Log the reload.
        clsname = self.__class__.__name__
        title = self.__dict__.get('title', self.__dict__.get('name'))
        objname = "%s '%s'" % (clsname, title) if title else clsname
        log.debug("Reloading %s for attr '%s'" % (objname, attr))
        # Reload and return the value
        self.reload()
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
        """ Retruns True if this is already a full object. A full object means all attributes
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
        """ Helper to edit and refresh a tags.

            Parameters:
                tag (str): tag name
                items (list): list of tags to add
                locked (bool): lock this field.
                remove (bool): If this is active remove the tags in items.
        """
        if not isinstance(items, list):
            items = [items]
        value = getattr(self, tag + 's')
        existing_cols = [t.tag for t in value if t and remove is False]
        d = tag_helper(tag, existing_cols + items, locked, remove)
        self.edit(**d)
        self.refresh()

    def addCollection(self, collections):
        """ Add a collection(s).

           Parameters:
                collections (list): list of strings
        """
        self._edit_tags('collection', collections)

    def removeCollection(self, collections):
        """ Remove a collection(s). """
        self._edit_tags('collection', collections, remove=True)

    def addLabel(self, labels):
        """ Add a label(s). """
        self._edit_tags('label', labels)

    def removeLabel(self, labels):
        """ Remove a label(s). """
        self._edit_tags('label', labels, remove=True)

    def addGenre(self, genres):
        """ Add a genre(s). """
        self._edit_tags('genre', genres)

    def removeGenre(self, genres):
        """ Remove a genre(s). """
        self._edit_tags('genre', genres, remove=True)

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
                'havnt allowed items to be deleted' % self.key)
            raise

    def history(self, maxresults=9999999, mindate=None):
        """ Get Play History for a media item.
            Parameters:
                maxresults (int): Only return the specified number of results (optional).
                mindate (datetime): Min datetime to return results from.
        """
        return self._server.history(maxresults=maxresults, mindate=mindate, ratingKey=self.ratingKey)

    def posters(self):
        """ Returns list of available poster objects. :class:`~plexapi.media.Poster`. """

        return self.fetchItems('%s/posters' % self.key)

    def uploadPoster(self, url=None, filepath=None):
        """ Upload poster from url or filepath. :class:`~plexapi.media.Poster` to :class:`~plexapi.video.Video`. """
        if url:
            key = '%s/posters?url=%s' % (self.key, quote_plus(url))
            self._server.query(key, method=self._server._session.post)
        elif filepath:
            key = '%s/posters?' % self.key
            data = open(filepath, 'rb').read()
            self._server.query(key, method=self._server._session.post, data=data)

    def setPoster(self, poster):
        """ Set . :class:`~plexapi.media.Poster` to :class:`~plexapi.video.Video` """
        poster.select()

    def arts(self):
        """ Returns list of available art objects. :class:`~plexapi.media.Poster`. """

        return self.fetchItems('%s/arts' % self.key)

    def uploadArt(self, url=None, filepath=None):
        """ Upload art from url or filepath. :class:`~plexapi.media.Poster` to :class:`~plexapi.video.Video`. """
        if url:
            key = '/library/metadata/%s/arts?url=%s' % (self.ratingKey, quote_plus(url))
            self._server.query(key, method=self._server._session.post)
        elif filepath:
            key = '/library/metadata/%s/arts?' % self.ratingKey
            data = open(filepath, 'rb').read()
            self._server.query(key, method=self._server._session.post, data=data)

    def setArt(self, art):
        """ Set :class:`~plexapi.media.Poster` to :class:`~plexapi.video.Video` """
        art.select()

    def unmatch(self):
        """ Unmatches metadata match from object. """
        key = '/library/metadata/%s/unmatch' % self.ratingKey
        self._server.query(key, method=self._server._session.put)

    def matches(self, agent=None, title=None, year=None, language=None):
        """ Return list of (:class:`~plexapi.media.SearchResult`) metadata matches.

             Parameters:
                agent (str): Agent name to be used (imdb, thetvdb, themoviedb, etc.)
                title (str): Title of item to search for
                year (str): Year of item to search in
                language (str) : Language of item to search in

            Examples:
                1. video.matches()
                2. video.matches(title="something", year=2020)
                3. video.matches(title="something")
                4. video.matches(year=2020)
                5. video.matches(title="something", year="")
                6. video.matches(title="", year=2020)
                7. video.matches(title="", year="")

                1. The default behaviour in Plex Web = no params in plexapi
                2. Both title and year specified by user
                3. Year automatically filled in
                4. Title automatically filled in
                5. Explicitly searches for title with blank year
                6. Explicitly searches for blank title with year
                7. I don't know what the user is thinking... return the same result as 1

                For 2 to 7, the agent and language is automatically filled in
        """
        key = '/library/metadata/%s/matches' % self.ratingKey
        params = {'manual': 1}

        if agent and not any([title, year, language]):
            params['language'] = self.section().language
            params['agent'] = utils.getAgentIdentifier(self.section(), agent)
        else:
            if any(x is not None for x in [agent, title, year, language]):
                if title is None:
                    params['title'] = self.title
                else:
                    params['title'] = title

                if year is None:
                    params['year'] = self.year
                else:
                    params['year'] = year

                params['language'] = language or self.section().language

                if agent is None:
                    params['agent'] = self.section().agent
                else:
                    params['agent'] = utils.getAgentIdentifier(self.section(), agent)

        key = key + '?' + urlencode(params)
        data = self._server.query(key, method=self._server._session.get)
        return self.findItems(data, initpath=key)

    def fixMatch(self, searchResult=None, auto=False, agent=None):
        """ Use match result to update show metadata.

            Parameters:
                auto (bool): True uses first match from matches
                    False allows user to provide the match
                searchResult (:class:`~plexapi.media.SearchResult`): Search result from
                    ~plexapi.base.matches()
                agent (str): Agent name to be used (imdb, thetvdb, themoviedb, etc.)
        """
        key = '/library/metadata/%s/match' % self.ratingKey
        if auto:
            autoMatch = self.matches(agent=agent)
            if autoMatch:
                searchResult = autoMatch[0]
            else:
                raise NotFound('No matches found using this agent: (%s:%s)' % (agent, autoMatch))
        elif not searchResult:
            raise NotFound('fixMatch() requires either auto=True or '
                           'searchResult=:class:`~plexapi.media.SearchResult`.')

        params = {'guid': searchResult.guid,
                  'name': searchResult.name}

        data = key + '?' + urlencode(params)
        self._server.query(data, method=self._server._session.put)

    # The photo tag cant be built atm. TODO
    # def arts(self):
    #     part = '%s/arts' % self.key
    #     return self.fetchItem(part)

    # def poster(self):
    #     part = '%s/posters' % self.key
    #     return self.fetchItem(part, etag='Photo')


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
        if self.TYPE not in ('movie', 'episode', 'track'):
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

    def split(self):
        """Split a duplicate."""
        key = '%s/split' % self.key
        return self._server.query(key, method=self._server._session.put)

    def merge(self, ratingKeys):
        """Merge duplicate items."""
        if not isinstance(ratingKeys, list):
            ratingKeys = str(ratingKeys).split(",")

        key = '%s/merge?ids=%s' % (self.key, ','.join(ratingKeys))
        return self._server.query(key, method=self._server._session.put)

    def unmatch(self):
        """Unmatch a media file."""
        key = '%s/unmatch' % self.key
        return self._server.query(key, method=self._server._session.put)

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
        self.reload()

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
        self.reload()


@utils.registerPlexObject
class Release(PlexObject):
    TAG = 'Release'
    key = '/updater/status'

    def _loadData(self, data):
        self.download_key = data.attrib.get('key')
        self.version = data.attrib.get('version')
        self.added = data.attrib.get('added')
        self.fixed = data.attrib.get('fixed')
        self.downloadURL = data.attrib.get('downloadURL')
        self.state = data.attrib.get('state')
