# -*- coding: utf-8 -*-
from urllib.parse import quote, quote_plus, unquote, urlencode

from plexapi import X_PLEX_CONTAINER_SIZE, log, media, utils
from plexapi.base import OPERATORS, PlexObject, PlexPartialObject
from plexapi.exceptions import BadRequest, NotFound
from plexapi.settings import Setting
from plexapi.utils import deprecated


class Library(PlexObject):
    """ Represents a PlexServer library. This contains all sections of media defined
        in your Plex server including video, shows and audio.

        Attributes:
            key (str): '/library'
            identifier (str): Unknown ('com.plexapp.plugins.library').
            mediaTagVersion (str): Unknown (/system/bundle/media/flags/)
            server (:class:`~plexapi.server.PlexServer`): PlexServer this client is connected to.
            title1 (str): 'Plex Library' (not sure how useful this is).
            title2 (str): Second title (this is blank on my setup).
    """
    key = '/library'

    def _loadData(self, data):
        self._data = data
        self._sectionsByID = {}  # cached Section UUIDs
        self.identifier = data.attrib.get('identifier')
        self.mediaTagVersion = data.attrib.get('mediaTagVersion')
        self.title1 = data.attrib.get('title1')
        self.title2 = data.attrib.get('title2')

    def sections(self):
        """ Returns a list of all media sections in this library. Library sections may be any of
            :class:`~plexapi.library.MovieSection`, :class:`~plexapi.library.ShowSection`,
            :class:`~plexapi.library.MusicSection`, :class:`~plexapi.library.PhotoSection`.
        """
        key = '/library/sections'
        sections = []
        for elem in self._server.query(key):
            for cls in (MovieSection, ShowSection, MusicSection, PhotoSection):
                if elem.attrib.get('type') == cls.TYPE:
                    section = cls(self._server, elem, key)
                    self._sectionsByID[section.key] = section
                    sections.append(section)
        return sections

    def section(self, title=None):
        """ Returns the :class:`~plexapi.library.LibrarySection` that matches the specified title.

            Parameters:
                title (str): Title of the section to return.
        """
        for section in self.sections():
            if section.title.lower() == title.lower():
                return section
        raise NotFound('Invalid library section: %s' % title)

    def sectionByID(self, sectionID):
        """ Returns the :class:`~plexapi.library.LibrarySection` that matches the specified sectionID.

            Parameters:
                sectionID (str): ID of the section to return.
        """
        if not self._sectionsByID or sectionID not in self._sectionsByID:
            self.sections()
        return self._sectionsByID[sectionID]

    def all(self, **kwargs):
        """ Returns a list of all media from all library sections.
            This may be a very large dataset to retrieve.
        """
        items = []
        for section in self.sections():
            for item in section.all(**kwargs):
                items.append(item)
        return items

    def onDeck(self):
        """ Returns a list of all media items on deck. """
        return self.fetchItems('/library/onDeck')

    def recentlyAdded(self):
        """ Returns a list of all media items recently added. """
        return self.fetchItems('/library/recentlyAdded')

    def search(self, title=None, libtype=None, **kwargs):
        """ Searching within a library section is much more powerful. It seems certain
            attributes on the media objects can be targeted to filter this search down
            a bit, but I havent found the documentation for it.

            Example: "studio=Comedy%20Central" or "year=1999" "title=Kung Fu" all work. Other items
            such as actor=<id> seem to work, but require you already know the id of the actor.
            TLDR: This is untested but seems to work. Use library section search when you can.
        """
        args = {}
        if title:
            args['title'] = title
        if libtype:
            args['type'] = utils.searchType(libtype)
        for attr, value in kwargs.items():
            args[attr] = value
        key = '/library/all%s' % utils.joinArgs(args)
        return self.fetchItems(key)

    def cleanBundles(self):
        """ Poster images and other metadata for items in your library are kept in "bundle"
            packages. When you remove items from your library, these bundles aren't immediately
            removed. Removing these old bundles can reduce the size of your install. By default, your
            server will automatically clean up old bundles once a week as part of Scheduled Tasks.
        """
        # TODO: Should this check the response for success or the correct mediaprefix?
        self._server.query('/library/clean/bundles?async=1', method=self._server._session.put)

    def emptyTrash(self):
        """ If a library has items in the Library Trash, use this option to empty the Trash. """
        for section in self.sections():
            section.emptyTrash()

    def optimize(self):
        """ The Optimize option cleans up the server database from unused or fragmented data.
            For example, if you have deleted or added an entire library or many items in a
            library, you may like to optimize the database.
        """
        self._server.query('/library/optimize?async=1', method=self._server._session.put)

    def update(self):
        """ Scan this library for new items."""
        self._server.query('/library/sections/all/refresh')

    def cancelUpdate(self):
        """ Cancel a library update. """
        key = '/library/sections/all/refresh'
        self._server.query(key, method=self._server._session.delete)

    def refresh(self):
        """ Forces a download of fresh media information from the internet.
            This can take a long time. Any locked fields are not modified.
        """
        self._server.query('/library/sections/all/refresh?force=1')

    def deleteMediaPreviews(self):
        """ Delete the preview thumbnails for the all sections. This cannot be
            undone. Recreating media preview files can take hours or even days.
        """
        for section in self.sections():
            section.deleteMediaPreviews()

    def add(self, name='', type='', agent='', scanner='', location='', language='en', *args, **kwargs):
        """ Simplified add for the most common options.

            Parameters:
                name (str): Name of the library
                agent (str): Example com.plexapp.agents.imdb
                type (str): movie, show, # check me
                location (str): /path/to/files
                language (str): Two letter language fx en
                kwargs (dict): Advanced options should be passed as a dict. where the id is the key.

            **Photo Preferences**

                * **agent** (str): com.plexapp.agents.none
                * **enableAutoPhotoTags** (bool): Tag photos. Default value false.
                * **enableBIFGeneration** (bool): Enable video preview thumbnails. Default value true.
                * **includeInGlobal** (bool): Include in dashboard. Default value true.
                * **scanner** (str): Plex Photo Scanner

            **Movie Preferences**

                * **agent** (str): com.plexapp.agents.none, com.plexapp.agents.imdb, tv.plex.agents.movie,
                  com.plexapp.agents.themoviedb
                * **enableBIFGeneration** (bool): Enable video preview thumbnails. Default value true.
                * **enableCinemaTrailers** (bool): Enable Cinema Trailers. Default value true.
                * **includeInGlobal** (bool): Include in dashboard. Default value true.
                * **scanner** (str): Plex Movie, Plex Movie Scanner, Plex Video Files Scanner, Plex Video Files

            **IMDB Movie Options** (com.plexapp.agents.imdb)

                * **title** (bool): Localized titles. Default value false.
                * **extras** (bool): Find trailers and extras automatically (Plex Pass required). Default value true.
                * **only_trailers** (bool): Skip extras which aren't trailers. Default value false.
                * **redband** (bool): Use red band (restricted audiences) trailers when available. Default value false.
                * **native_subs** (bool): Include extras with subtitles in Library language. Default value false.
                * **cast_list** (int): Cast List Source: Default value 1 Possible options: 0:IMDb,1:The Movie Database.
                * **ratings** (int): Ratings Source, Default value 0 Possible options:
                  0:Rotten Tomatoes, 1:IMDb, 2:The Movie Database.
                * **summary** (int): Plot Summary Source: Default value 1 Possible options: 0:IMDb,1:The Movie Database.
                * **country** (int): Default value 46 Possible options 0:Argentina, 1:Australia, 2:Austria,
                  3:Belgium, 4:Belize, 5:Bolivia, 6:Brazil, 7:Canada, 8:Chile, 9:Colombia, 10:Costa Rica,
                  11:Czech Republic, 12:Denmark, 13:Dominican Republic, 14:Ecuador, 15:El Salvador,
                  16:France, 17:Germany, 18:Guatemala, 19:Honduras, 20:Hong Kong SAR, 21:Ireland,
                  22:Italy, 23:Jamaica, 24:Korea, 25:Liechtenstein, 26:Luxembourg, 27:Mexico, 28:Netherlands,
                  29:New Zealand, 30:Nicaragua, 31:Panama, 32:Paraguay, 33:Peru, 34:Portugal,
                  35:Peoples Republic of China, 36:Puerto Rico, 37:Russia, 38:Singapore, 39:South Africa,
                  40:Spain, 41:Sweden, 42:Switzerland, 43:Taiwan, 44:Trinidad, 45:United Kingdom,
                  46:United States, 47:Uruguay, 48:Venezuela.
                * **collections** (bool): Use collection info from The Movie Database. Default value false.
                * **localart** (bool): Prefer artwork based on library language. Default value true.
                * **adult** (bool): Include adult content. Default value false.
                * **usage** (bool): Send anonymous usage data to Plex. Default value true.

            **TheMovieDB Movie Options** (com.plexapp.agents.themoviedb)

                * **collections** (bool): Use collection info from The Movie Database. Default value false.
                * **localart** (bool): Prefer artwork based on library language. Default value true.
                * **adult** (bool): Include adult content. Default value false.
                * **country** (int): Country (used for release date and content rating). Default value 47 Possible
                  options 0:, 1:Argentina, 2:Australia, 3:Austria, 4:Belgium, 5:Belize, 6:Bolivia, 7:Brazil, 8:Canada,
                  9:Chile, 10:Colombia, 11:Costa Rica, 12:Czech Republic, 13:Denmark, 14:Dominican Republic, 15:Ecuador,
                  16:El Salvador, 17:France, 18:Germany, 19:Guatemala, 20:Honduras, 21:Hong Kong SAR, 22:Ireland,
                  23:Italy, 24:Jamaica, 25:Korea, 26:Liechtenstein, 27:Luxembourg, 28:Mexico, 29:Netherlands,
                  30:New Zealand, 31:Nicaragua, 32:Panama, 33:Paraguay, 34:Peru, 35:Portugal,
                  36:Peoples Republic of China, 37:Puerto Rico, 38:Russia, 39:Singapore, 40:South Africa, 41:Spain,
                  42:Sweden, 43:Switzerland, 44:Taiwan, 45:Trinidad, 46:United Kingdom, 47:United States, 48:Uruguay,
                  49:Venezuela.

            **Show Preferences**

                * **agent** (str): com.plexapp.agents.none, com.plexapp.agents.thetvdb, com.plexapp.agents.themoviedb
                * **enableBIFGeneration** (bool): Enable video preview thumbnails. Default value true.
                * **episodeSort** (int): Episode order. Default -1 Possible options: 0:Oldest first, 1:Newest first.
                * **flattenSeasons** (int): Seasons. Default value 0 Possible options: 0:Show,1:Hide.
                * **includeInGlobal** (bool): Include in dashboard. Default value true.
                * **scanner** (str): Plex Series Scanner

            **TheTVDB Show Options** (com.plexapp.agents.thetvdb)

                * **extras** (bool): Find trailers and extras automatically (Plex Pass required). Default value true.
                * **native_subs** (bool): Include extras with subtitles in Library language. Default value false.

            **TheMovieDB Show Options** (com.plexapp.agents.themoviedb)

                * **collections** (bool): Use collection info from The Movie Database. Default value false.
                * **localart** (bool): Prefer artwork based on library language. Default value true.
                * **adult** (bool): Include adult content. Default value false.
                * **country** (int): Country (used for release date and content rating). Default value 47 options
                  0:, 1:Argentina, 2:Australia, 3:Austria, 4:Belgium, 5:Belize, 6:Bolivia, 7:Brazil, 8:Canada, 9:Chile,
                  10:Colombia, 11:Costa Rica, 12:Czech Republic, 13:Denmark, 14:Dominican Republic, 15:Ecuador,
                  16:El Salvador, 17:France, 18:Germany, 19:Guatemala, 20:Honduras, 21:Hong Kong SAR, 22:Ireland,
                  23:Italy, 24:Jamaica, 25:Korea, 26:Liechtenstein, 27:Luxembourg, 28:Mexico, 29:Netherlands,
                  30:New Zealand, 31:Nicaragua, 32:Panama, 33:Paraguay, 34:Peru, 35:Portugal,
                  36:Peoples Republic of China, 37:Puerto Rico, 38:Russia, 39:Singapore, 40:South Africa,
                  41:Spain, 42:Sweden, 43:Switzerland, 44:Taiwan, 45:Trinidad, 46:United Kingdom, 47:United States,
                  48:Uruguay, 49:Venezuela.

            **Other Video Preferences**

                * **agent** (str): com.plexapp.agents.none, com.plexapp.agents.imdb, com.plexapp.agents.themoviedb
                * **enableBIFGeneration** (bool): Enable video preview thumbnails. Default value true.
                * **enableCinemaTrailers** (bool): Enable Cinema Trailers. Default value true.
                * **includeInGlobal** (bool): Include in dashboard. Default value true.
                * **scanner** (str): Plex Movie Scanner, Plex Video Files Scanner

            **IMDB Other Video Options** (com.plexapp.agents.imdb)

                * **title** (bool): Localized titles. Default value false.
                * **extras** (bool): Find trailers and extras automatically (Plex Pass required). Default value true.
                * **only_trailers** (bool): Skip extras which aren't trailers. Default value false.
                * **redband** (bool): Use red band (restricted audiences) trailers when available. Default value false.
                * **native_subs** (bool): Include extras with subtitles in Library language. Default value false.
                * **cast_list** (int): Cast List Source: Default value 1 Possible options: 0:IMDb,1:The Movie Database.
                * **ratings** (int): Ratings Source Default value 0 Possible options:
                  0:Rotten Tomatoes,1:IMDb,2:The Movie Database.
                * **summary** (int): Plot Summary Source: Default value 1 Possible options: 0:IMDb,1:The Movie Database.
                * **country** (int): Country: Default value 46 Possible options: 0:Argentina, 1:Australia, 2:Austria,
                  3:Belgium, 4:Belize, 5:Bolivia, 6:Brazil, 7:Canada, 8:Chile, 9:Colombia, 10:Costa Rica,
                  11:Czech Republic, 12:Denmark, 13:Dominican Republic, 14:Ecuador, 15:El Salvador, 16:France,
                  17:Germany, 18:Guatemala, 19:Honduras, 20:Hong Kong SAR, 21:Ireland, 22:Italy, 23:Jamaica,
                  24:Korea, 25:Liechtenstein, 26:Luxembourg, 27:Mexico, 28:Netherlands, 29:New Zealand, 30:Nicaragua,
                  31:Panama, 32:Paraguay, 33:Peru, 34:Portugal, 35:Peoples Republic of China, 36:Puerto Rico,
                  37:Russia, 38:Singapore, 39:South Africa, 40:Spain, 41:Sweden, 42:Switzerland, 43:Taiwan, 44:Trinidad,
                  45:United Kingdom, 46:United States, 47:Uruguay, 48:Venezuela.
                * **collections** (bool): Use collection info from The Movie Database. Default value false.
                * **localart** (bool): Prefer artwork based on library language. Default value true.
                * **adult** (bool): Include adult content. Default value false.
                * **usage** (bool): Send anonymous usage data to Plex. Default value true.

            **TheMovieDB Other Video Options** (com.plexapp.agents.themoviedb)

                * **collections** (bool): Use collection info from The Movie Database. Default value false.
                * **localart** (bool): Prefer artwork based on library language. Default value true.
                * **adult** (bool): Include adult content. Default value false.
                * **country** (int): Country (used for release date and content rating). Default
                  value 47 Possible options 0:, 1:Argentina, 2:Australia, 3:Austria, 4:Belgium, 5:Belize,
                  6:Bolivia, 7:Brazil, 8:Canada, 9:Chile, 10:Colombia, 11:Costa Rica, 12:Czech Republic,
                  13:Denmark, 14:Dominican Republic, 15:Ecuador, 16:El Salvador, 17:France, 18:Germany,
                  19:Guatemala, 20:Honduras, 21:Hong Kong SAR, 22:Ireland, 23:Italy, 24:Jamaica,
                  25:Korea, 26:Liechtenstein, 27:Luxembourg, 28:Mexico, 29:Netherlands, 30:New Zealand,
                  31:Nicaragua, 32:Panama, 33:Paraguay, 34:Peru, 35:Portugal,
                  36:Peoples Republic of China, 37:Puerto Rico, 38:Russia, 39:Singapore,
                  40:South Africa, 41:Spain, 42:Sweden, 43:Switzerland, 44:Taiwan, 45:Trinidad,
                  46:United Kingdom, 47:United States, 48:Uruguay, 49:Venezuela.
        """
        part = '/library/sections?name=%s&type=%s&agent=%s&scanner=%s&language=%s&location=%s' % (
            quote_plus(name), type, agent, quote_plus(scanner), language, quote_plus(location))  # noqa E126
        if kwargs:
            part += urlencode(kwargs)
        return self._server.query(part, method=self._server._session.post)

    def history(self, maxresults=9999999, mindate=None):
        """ Get Play History for all library Sections for the owner.
            Parameters:
                maxresults (int): Only return the specified number of results (optional).
                mindate (datetime): Min datetime to return results from.
        """
        hist = []
        for section in self.sections():
            hist.extend(section.history(maxresults=maxresults, mindate=mindate))
        return hist


class LibrarySection(PlexObject):
    """ Base class for a single library section.

        Attributes:
            agent (str): The metadata agent used for the library section (com.plexapp.agents.imdb, etc).
            allowSync (bool): True if you allow syncing content from the library section.
            art (str): Background artwork used to respresent the library section.
            composite (str): Composite image used to represent the library section.
            createdAt (datetime): Datetime the library section was created.
            filters (str): Unknown
            key (str): Key (or ID) of this library section.
            language (str): Language represented in this section (en, xn, etc).
            locations (List<str>): List of folder paths added to the library section.
            refreshing (bool): True if this section is currently being refreshed.
            scanner (str): Internal scanner used to find media (Plex Movie Scanner, Plex Premium Music Scanner, etc.)
            thumb (str): Thumbnail image used to represent the library section.
            title (str): Name of the library section.
            type (str): Type of content section represents (movie, show, artist, photo).
            updatedAt (datetime): Datetime the library section was last updated.
            uuid (str): Unique id for the section (32258d7c-3e6c-4ac5-98ad-bad7a3b78c63)
    """

    def _loadData(self, data):
        self._data = data
        self.agent = data.attrib.get('agent')
        self.allowSync = utils.cast(bool, data.attrib.get('allowSync'))
        self.art = data.attrib.get('art')
        self.composite = data.attrib.get('composite')
        self.createdAt = utils.toDatetime(data.attrib.get('createdAt'))
        self.filters = data.attrib.get('filters')
        self.key = data.attrib.get('key')  # invalid key from plex
        self.language = data.attrib.get('language')
        self.locations = self.listAttrs(data, 'path', etag='Location')
        self.refreshing = utils.cast(bool, data.attrib.get('refreshing'))
        self.scanner = data.attrib.get('scanner')
        self.thumb = data.attrib.get('thumb')
        self.title = data.attrib.get('title')
        self.type = data.attrib.get('type')
        self.updatedAt = utils.toDatetime(data.attrib.get('updatedAt'))
        self.uuid = data.attrib.get('uuid')
        # Private attrs as we dont want a reload.
        self._total_size = None

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

        if '/all' in ekey:
            # totalSize is only included in the xml response
            # if container size is used.
            total_size = data.attrib.get("totalSize") or data.attrib.get("size")
            self._total_size = utils.cast(int, total_size)

        items = self.findItems(data, cls, ekey, **kwargs)

        librarySectionID = data.attrib.get('librarySectionID')
        if librarySectionID:
            for item in items:
                item.librarySectionID = librarySectionID
        return items

    @property
    def totalSize(self):
        """ Returns the total number of items in the library. """
        if self._total_size is None:
            part = '/library/sections/%s/all?X-Plex-Container-Start=0&X-Plex-Container-Size=1' % self.key
            data = self._server.query(part)
            self._total_size = int(data.attrib.get("totalSize"))

        return self._total_size

    def delete(self):
        """ Delete a library section. """
        try:
            return self._server.query('/library/sections/%s' % self.key, method=self._server._session.delete)
        except BadRequest:  # pragma: no cover
            msg = 'Failed to delete library %s' % self.key
            msg += 'You may need to allow this permission in your Plex settings.'
            log.error(msg)
            raise

    def reload(self, key=None):
        return self._server.library.section(self.title)

    def edit(self, agent=None, **kwargs):
        """ Edit a library (Note: agent is required). See :class:`~plexapi.library.Library` for example usage.

            Parameters:
                kwargs (dict): Dict of settings to edit.
        """
        if not agent:
            agent = self.agent
        part = '/library/sections/%s?agent=%s&%s' % (self.key, agent, urlencode(kwargs))
        self._server.query(part, method=self._server._session.put)

        # Reload this way since the self.key dont have a full path, but is simply a id.
        for s in self._server.library.sections():
            if s.key == self.key:
                return s

    def get(self, title):
        """ Returns the media item with the specified title.

            Parameters:
                title (str): Title of the item to return.
        """
        key = '/library/sections/%s/all?title=%s' % (self.key, quote(title, safe=''))
        return self.fetchItem(key, title__iexact=title)

    def all(self, libtype=None, **kwargs):
        """ Returns a list of all items from this library section.
            See description of :func:`plexapi.library.LibrarySection.search()` for details about filtering / sorting.
        """
        libtype = libtype or self.TYPE
        return self.search(libtype=libtype, **kwargs)

    def folders(self):
        """ Returns a list of available :class:`~plexapi.library.Folder` for this library section.
        """
        key = '/library/sections/%s/folder' % self.key
        return self.fetchItems(key, Folder)

    def hubs(self):
        """ Returns a list of available :class:`~plexapi.library.Hub` for this library section.
        """
        key = '/hubs/sections/%s' % self.key
        return self.fetchItems(key)

    def _filters(self):
        """ Returns a list of :class:`~plexapi.library.Filter` from this library section. """
        key = '/library/sections/%s/filters' % self.key
        return self.fetchItems(key, cls=Filter)

    def _sorts(self, mediaType=None):
        """ Returns a list of available :class:`~plexapi.library.Sort` for this library section.
        """
        items = []
        for data in self.listChoices('sorts', mediaType):
            sort = Sort(server=self._server, data=data._data)
            sort._initpath = data._initpath
            items.append(sort)
        return items

    def filterFields(self, mediaType=None):
        """ Returns a list of available :class:`~plexapi.library.FilterField` for this library section.
        """
        items = []
        key = '/library/sections/%s/filters?includeMeta=1' % self.key
        data = self._server.query(key)
        for meta in data.iter('Meta'):
            for metaType in meta.iter('Type'):
                if not mediaType or metaType.attrib.get('type') == mediaType:
                    fields = self.findItems(metaType, FilterField)
                    for field in fields:
                        field._initpath = metaType.attrib.get('key')
                        fieldType = [_ for _ in self.findItems(meta, FieldType) if _.type == field.type]
                        field.operators = fieldType[0].operators
                    items += fields
        if not items and mediaType:
            raise BadRequest('mediaType (%s) not found.' % mediaType)
        return items

    def agents(self):
        """ Returns a list of available :class:`~plexapi.media.Agent` for this library section.
        """
        return self._server.agents(utils.searchType(self.type))

    def settings(self):
        """ Returns a list of all library settings. """
        key = '/library/sections/%s/prefs' % self.key
        data = self._server.query(key)
        return self.findItems(data, cls=Setting)

    def editAdvanced(self, **kwargs):
        """ Edit a library's advanced settings. """
        data = {}
        idEnums = {}
        key = 'prefs[%s]'

        for setting in self.settings():
            if setting.type != 'bool':
                idEnums[setting.id] = setting.enumValues
            else:
                idEnums[setting.id] = {0: False, 1: True}

        for settingID, value in kwargs.items():
            try:
                enums = idEnums.get(settingID)
                enumValues = [int(x) for x in enums]
            except TypeError:
                raise NotFound('%s not found in %s' % (value, list(idEnums.keys())))
            if value in enumValues:
                data[key % settingID] = value
            else:
                raise NotFound('%s not found in %s' % (value, enums))

        self.edit(**data)

    def defaultAdvanced(self):
        """ Edit all of library's advanced settings to default. """
        data = {}
        key = 'prefs[%s]'
        for setting in self.settings():
            if setting.type == 'bool':
                data[key % setting.id] = int(setting.default)
            else:
                data[key % setting.id] = setting.default

        self.edit(**data)

    def timeline(self):
        """ Returns a timeline query for this library section. """
        key = '/library/sections/%s/timeline' % self.key
        data = self._server.query(key)
        return LibraryTimeline(self, data)

    def onDeck(self):
        """ Returns a list of media items on deck from this library section. """
        key = '/library/sections/%s/onDeck' % self.key
        return self.fetchItems(key)

    def recentlyAdded(self, maxresults=50):
        """ Returns a list of media items recently added from this library section.

            Parameters:
                maxresults (int): Max number of items to return (default 50).
        """
        return self.search(sort='addedAt:desc', maxresults=maxresults)

    def firstCharacter(self):
        key = '/library/sections/%s/firstCharacter' % self.key
        return self.fetchItems(key, cls=FirstCharacter)

    def analyze(self):
        """ Run an analysis on all of the items in this library section. See
            See :func:`~plexapi.base.PlexPartialObject.analyze` for more details.
        """
        key = '/library/sections/%s/analyze' % self.key
        self._server.query(key, method=self._server._session.put)

    def emptyTrash(self):
        """ If a section has items in the Trash, use this option to empty the Trash. """
        key = '/library/sections/%s/emptyTrash' % self.key
        self._server.query(key, method=self._server._session.put)

    def update(self, path=None):
        """ Scan this section for new media.

            Parameters:
                path (str, optional): Full path to folder to scan.
        """
        key = '/library/sections/%s/refresh' % self.key
        if path is not None:
            key += '?path=%s' % quote_plus(path)
        self._server.query(key)

    def cancelUpdate(self):
        """ Cancel update of this Library Section. """
        key = '/library/sections/%s/refresh' % self.key
        self._server.query(key, method=self._server._session.delete)

    def refresh(self):
        """ Forces a download of fresh media information from the internet.
            This can take a long time. Any locked fields are not modified.
        """
        key = '/library/sections/%s/refresh?force=1' % self.key
        self._server.query(key)

    def deleteMediaPreviews(self):
        """ Delete the preview thumbnails for items in this library. This cannot
            be undone. Recreating media preview files can take hours or even days.
        """
        key = '/library/sections/%s/indexes' % self.key
        self._server.query(key, method=self._server._session.delete)

    def listChoices(self, category, libtype=None, **kwargs):
        """ Returns a list of :class:`~plexapi.library.FilterChoice` objects for the
            specified category and libtype. kwargs can be any of the same kwargs in
            :func:`~plexapi.library.LibraySection.search` to help narrow down the choices
            to only those that matter in your current context.

            Parameters:
                category (str): Category to list choices for (genre, contentRating, etc).
                libtype (int): Library type of item filter.
                **kwargs (dict): Additional kwargs to narrow down the choices.

            Raises:
                :exc:`~plexapi.exceptions.BadRequest`: Cannot include kwarg equal to specified category.
        """
        # TODO: Should this be moved to base?
        if category in kwargs:
            raise BadRequest('Cannot include kwarg equal to specified category: %s' % category)
        args = {}
        for subcategory, value in kwargs.items():
            args[category] = self._cleanSearchFilter(subcategory, value)
        if libtype is not None:
            args['type'] = utils.searchType(libtype)
        key = '/library/sections/%s/%s%s' % (self.key, category, utils.joinArgs(args))
        return self.fetchItems(key, cls=FilterChoice)

    def search(self, title=None, sort=None, maxresults=None,
               libtype=None, container_start=0, container_size=X_PLEX_CONTAINER_SIZE, **kwargs):
        """ Search the library. The http requests will be batched in container_size. If you're only looking for the first <num>
            results, it would be wise to set the maxresults option to that amount so this functions
            doesn't iterate over all results on the server.

            Parameters:
                title (str): General string query to search for (optional).
                sort (str): column:dir; column can be any of {addedAt, originallyAvailableAt, lastViewedAt,
                      titleSort, rating, mediaHeight, duration}. dir can be asc or desc (optional).
                maxresults (int): Only return the specified number of results (optional).
                libtype (str): Filter results to a spcifiec libtype (movie, show, episode, artist,
                    album, track; optional).
                container_start (int): default 0
                container_size (int): default X_PLEX_CONTAINER_SIZE in your config file.
                **kwargs (dict): Any of the available filters for the current library section. Partial string
                        matches allowed. Multiple matches OR together. Negative filtering also possible, just add an
                        exclamation mark to the end of filter name, e.g. `resolution!=1x1`.

                        * unwatched: Display or hide unwatched content (True, False). [all]
                        * duplicate: Display or hide duplicate items (True, False). [movie]
                        * actor: List of actors to search ([actor_or_id, ...]). [movie]
                        * collection: List of collections to search within ([collection_or_id, ...]). [all]
                        * contentRating: List of content ratings to search within ([rating_or_key, ...]). [movie,tv]
                        * country: List of countries to search within ([country_or_key, ...]). [movie,music]
                        * decade: List of decades to search within ([yyy0, ...]). [movie]
                        * director: List of directors to search ([director_or_id, ...]). [movie]
                        * genre: List Genres to search within ([genere_or_id, ...]). [all]
                        * network: List of TV networks to search within ([resolution_or_key, ...]). [tv]
                        * resolution: List of video resolutions to search within ([resolution_or_key, ...]). [movie]
                        * studio: List of studios to search within ([studio_or_key, ...]). [music]
                        * year: List of years to search within ([yyyy, ...]). [all]

            Raises:
                :exc:`~plexapi.exceptions.BadRequest`: When applying an unknown filter.
        """
        # cleanup the core arguments
        args = {}
        for category, value in list(kwargs.items()):
            if category.split('__')[-1] not in OPERATORS:
                args[category] = self._cleanSearchFilter(category, value, libtype)
                del kwargs[category]
        if title is not None:
            args['title'] = title
        if sort is not None:
            args['sort'] = self._cleanSearchSort(sort)
        if libtype is not None:
            args['type'] = utils.searchType(libtype)

        results = []
        subresults = []
        offset = container_start

        if maxresults is not None:
            container_size = min(container_size, maxresults)
        while True:
            key = '/library/sections/%s/all%s' % (self.key, utils.joinArgs(args))
            subresults = self.fetchItems(key, container_start=container_start,
                                         container_size=container_size, **kwargs)
            if not len(subresults):
                if offset > self.totalSize:
                    log.info("container_start is higher then the number of items in the library")
                break

            results.extend(subresults)

            # self.totalSize is not used as a condition in the while loop as
            # this require a additional http request.
            # self.totalSize is updated from .fetchItems
            wanted_number_of_items = self.totalSize - offset
            if maxresults is not None:
                wanted_number_of_items = min(maxresults, wanted_number_of_items)
                container_size = min(container_size, maxresults - len(results))

            if wanted_number_of_items <= len(results):
                break

            container_start += container_size

        return results

    def _cleanSearchFilter(self, category, value, libtype=None):
        # check a few things before we begin
        categories = [x.key for x in self.filterFields()]
        booleanFilters = [x.key for x in self.filterFields() if x.type == 'boolean']
        if category.endswith('!'):
            if category[:-1] not in categories:
                raise BadRequest('Unknown filter category: %s' % category[:-1])
        elif category not in categories:
            raise BadRequest('Unknown filter category: %s' % category)
        if category in booleanFilters:
            return '1' if value else '0'
        if not isinstance(value, (list, tuple)):
            value = [value]
        # convert list of values to list of keys or ids
        result = set()
        choices = self.listChoices(category, libtype)
        lookup = {c.title.lower(): unquote(unquote(c.key)) for c in choices}
        allowed = set(c.key for c in choices)
        for item in value:
            item = str((item.id or item.tag) if isinstance(item, media.MediaTag) else item).lower()
            # find most logical choice(s) to use in url
            if item in allowed: result.add(item); continue
            if item in lookup: result.add(lookup[item]); continue
            matches = [k for t, k in lookup.items() if item in t]
            if matches: map(result.add, matches); continue
            # nothing matched; use raw item value
            log.debug('Filter value not listed, using raw item value: %s' % item)
            result.add(item)
        return ','.join(result)

    def _cleanSearchSort(self, sort):
        sort = '%s:asc' % sort if ':' not in sort else sort
        scol, sdir = sort.lower().split(':')
        allowedSort = [sort.key for sort in self._sorts()]
        lookup = {s.lower(): s for s in allowedSort}
        if scol not in lookup:
            raise BadRequest('Unknown sort column: %s' % scol)
        if sdir not in ('asc', 'desc'):
            raise BadRequest('Unknown sort dir: %s' % sdir)
        return '%s:%s' % (lookup[scol], sdir)

    def _locations(self):
        """ Returns a list of :class:`~plexapi.library.Location` objects
        """
        return self.findItems(self._data, Location)

    def sync(self, policy, mediaSettings, client=None, clientId=None, title=None, sort=None, libtype=None,
             **kwargs):
        """ Add current library section as sync item for specified device.
            See description of :func:`~plexapi.library.LibrarySection.search` for details about filtering / sorting
            and :func:`~plexapi.myplex.MyPlexAccount.sync` for possible exceptions.

            Parameters:
                policy (:class:`~plexapi.sync.Policy`): policy of syncing the media (how many items to sync and process
                                                       watched media or not), generated automatically when method
                                                       called on specific LibrarySection object.
                mediaSettings (:class:`~plexapi.sync.MediaSettings`): Transcoding settings used for the media, generated
                                                                     automatically when method called on specific
                                                                     LibrarySection object.
                client (:class:`~plexapi.myplex.MyPlexDevice`): sync destination, see
                                                               :func:`~plexapi.myplex.MyPlexAccount.sync`.
                clientId (str): sync destination, see :func:`~plexapi.myplex.MyPlexAccount.sync`.
                title (str): descriptive title for the new :class:`~plexapi.sync.SyncItem`, if empty the value would be
                             generated from metadata of current media.
                sort (str): formatted as `column:dir`; column can be any of {`addedAt`, `originallyAvailableAt`,
                            `lastViewedAt`, `titleSort`, `rating`, `mediaHeight`, `duration`}. dir can be `asc` or
                            `desc`.
                libtype (str): Filter results to a specific libtype (`movie`, `show`, `episode`, `artist`, `album`,
                               `track`).

            Returns:
                :class:`~plexapi.sync.SyncItem`: an instance of created syncItem.

            Raises:
                :exc:`~plexapi.exceptions.BadRequest`: When the library is not allowed to sync.

            Example:

                .. code-block:: python

                    from plexapi import myplex
                    from plexapi.sync import Policy, MediaSettings, VIDEO_QUALITY_3_MBPS_720p

                    c = myplex.MyPlexAccount()
                    target = c.device('Plex Client')
                    sync_items_wd = c.syncItems(target.clientIdentifier)
                    srv = c.resource('Server Name').connect()
                    section = srv.library.section('Movies')
                    policy = Policy('count', unwatched=True, value=1)
                    media_settings = MediaSettings.create(VIDEO_QUALITY_3_MBPS_720p)
                    section.sync(target, policy, media_settings, title='Next best movie', sort='rating:desc')

        """
        from plexapi.sync import SyncItem

        if not self.allowSync:
            raise BadRequest('The requested library is not allowed to sync')

        args = {}
        for category, value in kwargs.items():
            args[category] = self._cleanSearchFilter(category, value, libtype)
        if sort is not None:
            args['sort'] = self._cleanSearchSort(sort)
        if libtype is not None:
            args['type'] = utils.searchType(libtype)

        myplex = self._server.myPlexAccount()
        sync_item = SyncItem(self._server, None)
        sync_item.title = title if title else self.title
        sync_item.rootTitle = self.title
        sync_item.contentType = self.CONTENT_TYPE
        sync_item.metadataType = self.METADATA_TYPE
        sync_item.machineIdentifier = self._server.machineIdentifier

        key = '/library/sections/%s/all' % self.key

        sync_item.location = 'library://%s/directory/%s' % (self.uuid, quote_plus(key + utils.joinArgs(args)))
        sync_item.policy = policy
        sync_item.mediaSettings = mediaSettings

        return myplex.sync(client=client, clientId=clientId, sync_item=sync_item)

    def history(self, maxresults=9999999, mindate=None):
        """ Get Play History for this library Section for the owner.
            Parameters:
                maxresults (int): Only return the specified number of results (optional).
                mindate (datetime): Min datetime to return results from.
        """
        return self._server.history(maxresults=maxresults, mindate=mindate, librarySectionID=self.key, accountID=1)

    @deprecated('use "collections" (plural) instead')
    def collection(self, **kwargs):
        return self.collections()

    def collections(self, **kwargs):
        """ Returns a list of collections from this library section.
            See description of :func:`~plexapi.library.LibrarySection.search` for details about filtering / sorting.
        """
        return self.search(libtype='collection', **kwargs)

    def playlists(self, **kwargs):
        """ Returns a list of playlists from this library section. """
        key = '/playlists?type=15&playlistType=%s&sectionID=%s' % (self.CONTENT_TYPE, self.key)
        return self.fetchItems(key, **kwargs)


class MovieSection(LibrarySection):
    """ Represents a :class:`~plexapi.library.LibrarySection` section containing movies.

        Attributes:
            TAG (str): 'Directory'
            TYPE (str): 'movie'
    """
    TAG = 'Directory'
    TYPE = 'movie'
    METADATA_TYPE = 'movie'
    CONTENT_TYPE = 'video'

    def sync(self, videoQuality, limit=None, unwatched=False, **kwargs):
        """ Add current Movie library section as sync item for specified device.
            See description of :func:`~plexapi.library.LibrarySection.search` for details about filtering / sorting and
            :func:`~plexapi.library.LibrarySection.sync` for details on syncing libraries and possible exceptions.

            Parameters:
                videoQuality (int): idx of quality of the video, one of VIDEO_QUALITY_* values defined in
                                    :mod:`~plexapi.sync` module.
                limit (int): maximum count of movies to sync, unlimited if `None`.
                unwatched (bool): if `True` watched videos wouldn't be synced.

            Returns:
                :class:`~plexapi.sync.SyncItem`: an instance of created syncItem.

            Example:

                .. code-block:: python

                    from plexapi import myplex
                    from plexapi.sync import VIDEO_QUALITY_3_MBPS_720p

                    c = myplex.MyPlexAccount()
                    target = c.device('Plex Client')
                    sync_items_wd = c.syncItems(target.clientIdentifier)
                    srv = c.resource('Server Name').connect()
                    section = srv.library.section('Movies')
                    section.sync(VIDEO_QUALITY_3_MBPS_720p, client=target, limit=1, unwatched=True,
                                 title='Next best movie', sort='rating:desc')

        """
        from plexapi.sync import Policy, MediaSettings
        kwargs['mediaSettings'] = MediaSettings.createVideo(videoQuality)
        kwargs['policy'] = Policy.create(limit, unwatched)
        return super(MovieSection, self).sync(**kwargs)


class ShowSection(LibrarySection):
    """ Represents a :class:`~plexapi.library.LibrarySection` section containing tv shows.

        Attributes:
            TAG (str): 'Directory'
            TYPE (str): 'show'
    """

    TAG = 'Directory'
    TYPE = 'show'
    METADATA_TYPE = 'episode'
    CONTENT_TYPE = 'video'

    def searchShows(self, **kwargs):
        """ Search for a show. See :func:`~plexapi.library.LibrarySection.search` for usage. """
        return self.search(libtype='show', **kwargs)

    def searchEpisodes(self, **kwargs):
        """ Search for an episode. See :func:`~plexapi.library.LibrarySection.search` for usage. """
        return self.search(libtype='episode', **kwargs)

    def recentlyAdded(self, libtype='episode', maxresults=50):
        """ Returns a list of recently added episodes from this library section.

            Parameters:
                maxresults (int): Max number of items to return (default 50).
        """
        return self.search(sort='episode.addedAt:desc', libtype=libtype, maxresults=maxresults)

    def sync(self, videoQuality, limit=None, unwatched=False, **kwargs):
        """ Add current Show library section as sync item for specified device.
            See description of :func:`~plexapi.library.LibrarySection.search` for details about filtering / sorting and
            :func:`~plexapi.library.LibrarySection.sync` for details on syncing libraries and possible exceptions.

            Parameters:
                videoQuality (int): idx of quality of the video, one of VIDEO_QUALITY_* values defined in
                                    :mod:`~plexapi.sync` module.
                limit (int): maximum count of episodes to sync, unlimited if `None`.
                unwatched (bool): if `True` watched videos wouldn't be synced.

            Returns:
                :class:`~plexapi.sync.SyncItem`: an instance of created syncItem.

            Example:

                .. code-block:: python

                    from plexapi import myplex
                    from plexapi.sync import VIDEO_QUALITY_3_MBPS_720p

                    c = myplex.MyPlexAccount()
                    target = c.device('Plex Client')
                    sync_items_wd = c.syncItems(target.clientIdentifier)
                    srv = c.resource('Server Name').connect()
                    section = srv.library.section('TV-Shows')
                    section.sync(VIDEO_QUALITY_3_MBPS_720p, client=target, limit=1, unwatched=True,
                                 title='Next unwatched episode')

        """
        from plexapi.sync import Policy, MediaSettings
        kwargs['mediaSettings'] = MediaSettings.createVideo(videoQuality)
        kwargs['policy'] = Policy.create(limit, unwatched)
        return super(ShowSection, self).sync(**kwargs)


class MusicSection(LibrarySection):
    """ Represents a :class:`~plexapi.library.LibrarySection` section containing music artists.

        Attributes:
            TAG (str): 'Directory'
            TYPE (str): 'artist'
    """
    TAG = 'Directory'
    TYPE = 'artist'

    CONTENT_TYPE = 'audio'
    METADATA_TYPE = 'track'

    def albums(self):
        """ Returns a list of :class:`~plexapi.audio.Album` objects in this section. """
        key = '/library/sections/%s/albums' % self.key
        return self.fetchItems(key)

    def stations(self):
        """ Returns a list of :class:`~plexapi.audio.Album` objects in this section. """
        key = '/hubs/sections/%s?includeStations=1' % self.key
        return self.fetchItems(key, cls=Station)

    def searchArtists(self, **kwargs):
        """ Search for an artist. See :func:`~plexapi.library.LibrarySection.search` for usage. """
        return self.search(libtype='artist', **kwargs)

    def searchAlbums(self, **kwargs):
        """ Search for an album. See :func:`~plexapi.library.LibrarySection.search` for usage. """
        return self.search(libtype='album', **kwargs)

    def searchTracks(self, **kwargs):
        """ Search for a track. See :func:`~plexapi.library.LibrarySection.search` for usage. """
        return self.search(libtype='track', **kwargs)

    def sync(self, bitrate, limit=None, **kwargs):
        """ Add current Music library section as sync item for specified device.
            See description of :func:`~plexapi.library.LibrarySection.search` for details about filtering / sorting and
            :func:`~plexapi.library.LibrarySection.sync` for details on syncing libraries and possible exceptions.

            Parameters:
                bitrate (int): maximum bitrate for synchronized music, better use one of MUSIC_BITRATE_* values from the
                               module :mod:`~plexapi.sync`.
                limit (int): maximum count of tracks to sync, unlimited if `None`.

            Returns:
                :class:`~plexapi.sync.SyncItem`: an instance of created syncItem.

            Example:

                .. code-block:: python

                    from plexapi import myplex
                    from plexapi.sync import AUDIO_BITRATE_320_KBPS

                    c = myplex.MyPlexAccount()
                    target = c.device('Plex Client')
                    sync_items_wd = c.syncItems(target.clientIdentifier)
                    srv = c.resource('Server Name').connect()
                    section = srv.library.section('Music')
                    section.sync(AUDIO_BITRATE_320_KBPS, client=target, limit=100, sort='addedAt:desc',
                                 title='New music')

        """
        from plexapi.sync import Policy, MediaSettings
        kwargs['mediaSettings'] = MediaSettings.createMusic(bitrate)
        kwargs['policy'] = Policy.create(limit)
        return super(MusicSection, self).sync(**kwargs)


class PhotoSection(LibrarySection):
    """ Represents a :class:`~plexapi.library.LibrarySection` section containing photos.

        Attributes:
            TAG (str): 'Directory'
            TYPE (str): 'photo'
    """
    TAG = 'Directory'
    TYPE = 'photo'
    CONTENT_TYPE = 'photo'
    METADATA_TYPE = 'photo'

    def all(self, libtype=None, **kwargs):
        """ Returns a list of all items from this library section.
            See description of :func:`plexapi.library.LibrarySection.search()` for details about filtering / sorting.
        """
        libtype = libtype or 'photoalbum'
        return self.search(libtype=libtype, **kwargs)

    def collections(self, **kwargs):
        raise NotImplementedError('Collections are not available for a Photo library.')

    def searchAlbums(self, title, **kwargs):
        """ Search for an album. See :func:`~plexapi.library.LibrarySection.search` for usage. """
        return self.search(libtype='photoalbum', title=title, **kwargs)

    def searchPhotos(self, title, **kwargs):
        """ Search for a photo. See :func:`~plexapi.library.LibrarySection.search` for usage. """
        return self.search(libtype='photo', title=title, **kwargs)

    def sync(self, resolution, limit=None, **kwargs):
        """ Add current Music library section as sync item for specified device.
            See description of :func:`~plexapi.library.LibrarySection.search` for details about filtering / sorting and
            :func:`~plexapi.library.LibrarySection.sync` for details on syncing libraries and possible exceptions.

            Parameters:
                resolution (str): maximum allowed resolution for synchronized photos, see PHOTO_QUALITY_* values in the
                                  module :mod:`~plexapi.sync`.
                limit (int): maximum count of tracks to sync, unlimited if `None`.

            Returns:
                :class:`~plexapi.sync.SyncItem`: an instance of created syncItem.

            Example:

                .. code-block:: python

                    from plexapi import myplex
                    from plexapi.sync import PHOTO_QUALITY_HIGH

                    c = myplex.MyPlexAccount()
                    target = c.device('Plex Client')
                    sync_items_wd = c.syncItems(target.clientIdentifier)
                    srv = c.resource('Server Name').connect()
                    section = srv.library.section('Photos')
                    section.sync(PHOTO_QUALITY_HIGH, client=target, limit=100, sort='addedAt:desc',
                                 title='Fresh photos')

        """
        from plexapi.sync import Policy, MediaSettings
        kwargs['mediaSettings'] = MediaSettings.createPhoto(resolution)
        kwargs['policy'] = Policy.create(limit)
        return super(PhotoSection, self).sync(**kwargs)


class FilterChoice(PlexObject):
    """ Represents a single filter choice. These objects are gathered when using filters
        while searching for library items and is the object returned in the result set of
        :func:`~plexapi.library.LibrarySection.listChoices`.

        Attributes:
            TAG (str): 'Directory'
            server (:class:`~plexapi.server.PlexServer`): PlexServer this client is connected to.
            initpath (str): Relative path requested when retrieving specified `data` (optional).
            fastKey (str): API path to quickly list all items in this filter
                (/library/sections/<section>/all?genre=<key>)
            key (str): Short key (id) of this filter option (used ad <key> in fastKey above).
            thumb (str): Thumbnail used to represent this filter option.
            title (str): Human readable name for this filter option.
            type (str): Filter type (genre, contentRating, etc).
    """
    TAG = 'Directory'

    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        self._data = data
        self.fastKey = data.attrib.get('fastKey')
        self.key = data.attrib.get('key')
        self.thumb = data.attrib.get('thumb')
        self.title = data.attrib.get('title')
        self.type = data.attrib.get('type')


@utils.registerPlexObject
class LibraryTimeline(PlexObject):
    """Represents a LibrarySection timeline.

        Attributes:
            TAG (str): 'LibraryTimeline'
            size (int): Unknown
            allowSync (bool): Unknown
            art (str): Relative path to art image.
            content (str): "secondary"
            identifier (str): "com.plexapp.plugins.library"
            latestEntryTime (int): Epoch timestamp
            mediaTagPrefix (str): "/system/bundle/media/flags/"
            mediaTagVersion (int): Unknown
            thumb (str): Relative path to library thumb image.
            title1 (str): Name of library section.
            updateQueueSize (int): Number of items queued to update.
            viewGroup (str): "secondary"
            viewMode (int): Unknown
    """
    TAG = 'LibraryTimeline'

    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        self._data = data
        self.size = utils.cast(int, data.attrib.get('size'))
        self.allowSync = utils.cast(bool, data.attrib.get('allowSync'))
        self.art = data.attrib.get('art')
        self.content = data.attrib.get('content')
        self.identifier = data.attrib.get('identifier')
        self.latestEntryTime = utils.cast(int, data.attrib.get('latestEntryTime'))
        self.mediaTagPrefix = data.attrib.get('mediaTagPrefix')
        self.mediaTagVersion = utils.cast(int, data.attrib.get('mediaTagVersion'))
        self.thumb = data.attrib.get('thumb')
        self.title1 = data.attrib.get('title1')
        self.updateQueueSize = utils.cast(int, data.attrib.get('updateQueueSize'))
        self.viewGroup = data.attrib.get('viewGroup')
        self.viewMode = utils.cast(int, data.attrib.get('viewMode'))


@utils.registerPlexObject
class Location(PlexObject):
    """ Represents a single library Location.

        Attributes:
            TAG (str): 'Location'
            id (int): Location path ID.
            path (str): Path used for library..
    """
    TAG = 'Location'

    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        self._data = data
        self.id = utils.cast(int, data.attrib.get('id'))
        self.path = data.attrib.get('path')


class Filter(PlexObject):
    """ Represents a single Filter.

        Attributes:
            TAG (str): 'Directory'
            TYPE (str): 'filter'
    """
    TAG = 'Directory'
    TYPE = 'filter'

    def _loadData(self, data):
        self._data = data
        self.filter = data.attrib.get('filter')
        self.filterType = data.attrib.get('filterType')
        self.key = data.attrib.get('key')
        self.title = data.attrib.get('title')
        self.type = data.attrib.get('type')


@utils.registerPlexObject
class Hub(PlexObject):
    """ Represents a single Hub (or category) in the PlexServer search.

        Attributes:
            TAG (str): 'Hub'
            context (str): The context of the hub.
            hubKey (str): API URL for these specific hub items.
            hubIdentifier (str): The identifier of the hub.
            key (str): API URL for the hub.
            more (bool): True if there are more items to load (call reload() to fetch all items).
            size (int): The number of items in the hub.
            style (str): The style of the hub.
            title (str): The title of the hub.
            type (str): The type of items in the hub.
    """
    TAG = 'Hub'

    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        self._data = data
        self.context = data.attrib.get('context')
        self.hubKey = data.attrib.get('hubKey')
        self.hubIdentifier = data.attrib.get('hubIdentifier')
        self.items = self.findItems(data)
        self.key = data.attrib.get('key')
        self.more = utils.cast(bool, data.attrib.get('more'))
        self.size = utils.cast(int, data.attrib.get('size'))
        self.style = data.attrib.get('style')
        self.title = data.attrib.get('title')
        self.type = data.attrib.get('type')

    def __len__(self):
        return self.size

    def reload(self):
        """ Reloads the hub to fetch all items in the hub. """
        if self.more and self.key:
            self.items = self.fetchItems(self.key)
            self.more = False
            self.size = len(self.items)


class HubMediaTag(PlexObject):
    """ Base class of hub media tag search results.

        Attributes:
            count (int): The number of items where this tag is found.
            filter (str): The URL filter for the tag.
            id (int): The id of the tag.
            key (str): API URL (/library/section/<librarySectionID>/all?<filter>).
            librarySectionID (int): The library section ID where the tag is found.
            librarySectionKey (str): API URL for the library section (/library/section/<librarySectionID>)
            librarySectionTitle (str): The library title where the tag is found.
            librarySectionType (int): The library type where the tag is found.
            reason (str): The reason for the search result.
            reasonID (int): The reason ID for the search result.
            reasonTitle (str): The reason title for the search result.
            type (str): The type of search result (tag).
            tag (str): The title of the tag.
            tagType (int): The type ID of the tag.
            tagValue (int): The value of the tag.
            thumb (str): The URL for the thumbnail of the tag (if available).
    """
    TAG = 'Directory'

    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        self._data = data
        self.count = utils.cast(int, data.attrib.get('count'))
        self.filter = data.attrib.get('filter')
        self.id = utils.cast(int, data.attrib.get('id'))
        self.key = data.attrib.get('key')
        self.librarySectionID = utils.cast(int, data.attrib.get('librarySectionID'))
        self.librarySectionKey = data.attrib.get('librarySectionKey')
        self.librarySectionTitle = data.attrib.get('librarySectionTitle')
        self.librarySectionType = utils.cast(int, data.attrib.get('librarySectionType'))
        self.reason = data.attrib.get('reason')
        self.reasonID = utils.cast(int, data.attrib.get('reasonID'))
        self.reasonTitle = data.attrib.get('reasonTitle')
        self.type = data.attrib.get('type')
        self.tag = data.attrib.get('tag')
        self.tagType = utils.cast(int, data.attrib.get('tagType'))
        self.tagValue = utils.cast(int, data.attrib.get('tagValue'))
        self.thumb = data.attrib.get('thumb')


@utils.registerPlexObject
class Tag(HubMediaTag):
    """ Represents a single Tag hub search media tag.

        Attributes:
            TAGTYPE (int): 0
    """
    TAGTYPE = 0


@utils.registerPlexObject
class Genre(HubMediaTag):
    """ Represents a single Genre hub search media tag.

        Attributes:
            TAGTYPE (int): 1
    """
    TAGTYPE = 1


@utils.registerPlexObject
class Director(HubMediaTag):
    """ Represents a single Director hub search media tag.

        Attributes:
            TAGTYPE (int): 4
    """
    TAGTYPE = 4


@utils.registerPlexObject
class Actor(HubMediaTag):
    """ Represents a single Actor hub search media tag.

        Attributes:
            TAGTYPE (int): 6
    """
    TAGTYPE = 6


@utils.registerPlexObject
class AutoTag(HubMediaTag):
    """ Represents a single AutoTag hub search media tag.

        Attributes:
            TAGTYPE (int): 207
    """
    TAGTYPE = 207


@utils.registerPlexObject
class Place(HubMediaTag):
    """ Represents a single Place hub search media tag.

        Attributes:
            TAGTYPE (int): 400
    """
    TAGTYPE = 400


@utils.registerPlexObject
class Station(PlexObject):
    """ Represents the Station area in the MusicSection.

        Attributes:
            TITLE (str): 'Stations'
            TYPE (str): 'station'
            hubIdentifier (str): Unknown.
            size (int): Number of items found.
            title (str): Title of this Hub.
            type (str): Type of items in the Hub.
            more (str): Unknown.
            style (str): Unknown
            items (str): List of items in the Hub.
    """
    TITLE = 'Stations'
    TYPE = 'station'

    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        self._data = data
        self.hubIdentifier = data.attrib.get('hubIdentifier')
        self.size = utils.cast(int, data.attrib.get('size'))
        self.title = data.attrib.get('title')
        self.type = data.attrib.get('type')
        self.more = data.attrib.get('more')
        self.style = data.attrib.get('style')
        self.items = self.findItems(data)

    def __len__(self):
        return self.size


class Sort(PlexObject):
    """ Represents a Sort element found in library.

        Attributes:
            TAG (str): 'Sort'
            defaultDirection (str): Default sorting direction.
            descKey (str): Url key for sorting with desc.
            key (str): Url key for sorting,
            title (str): Title of sorting,
            firstCharacterKey (str): Url path for first character endpoint.
    """
    TAG = 'Sort'

    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        self._data = data
        self.defaultDirection = data.attrib.get('defaultDirection')
        self.descKey = data.attrib.get('descKey')
        self.key = data.attrib.get('key')
        self.title = data.attrib.get('title')
        self.firstCharacterKey = data.attrib.get('firstCharacterKey')


class FilterField(PlexObject):
    """ Represents a Filters Field element found in library.

        Attributes:
            TAG (str): 'Field'
            key (str): Url key for filter,
            title (str): Title of filter.
            type (str): Type of filter (string, boolean, integer, date, etc).
            subType (str): Subtype of filter (decade, rating, etc).
            operators (str): Operators available for this filter.
    """
    TAG = 'Field'

    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        self._data = data
        self.key = data.attrib.get('key')
        self.title = data.attrib.get('title')
        self.type = data.attrib.get('type')
        self.subType = data.attrib.get('subType')
        self.operators = []


@utils.registerPlexObject
class Operator(PlexObject):
    """ Represents an Operator available for filter.

        Attributes:
            TAG (str): 'Operator'
            key (str): Url key for operator.
            title (str): Title of operator.
    """
    TAG = 'Operator'

    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        self.key = data.attrib.get('key')
        self.title = data.attrib.get('title')


class Folder(PlexObject):
    """ Represents a Folder inside a library.

        Attributes:
            key (str): Url key for folder.
            title (str): Title of folder.
    """

    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        self.key = data.attrib.get('key')
        self.title = data.attrib.get('title')

    def subfolders(self):
        """ Returns a list of available :class:`~plexapi.library.Folder` for this folder.
            Continue down subfolders until a mediaType is found.
        """
        if self.key.startswith('/library/metadata'):
            return self.fetchItems(self.key)
        else:
            return self.fetchItems(self.key, Folder)

    def allSubfolders(self):
        """ Returns a list of all available :class:`~plexapi.library.Folder` for this folder.
            Only returns :class:`~plexapi.library.Folder`.
        """
        folders = []
        for folder in self.subfolders():
            if not folder.key.startswith('/library/metadata'):
                folders.append(folder)
                while True:
                    for subfolder in folder.subfolders():
                        if not subfolder.key.startswith('/library/metadata'):
                            folders.append(subfolder)
                            continue
                    break
        return folders


@utils.registerPlexObject
class FieldType(PlexObject):
    """ Represents a FieldType for filter.

        Attributes:
            TAG (str): 'Operator'
            type (str): Type of filter (string, boolean, integer, date, etc),
            operators (str): Operators available for this filter.
    """
    TAG = 'FieldType'

    def __repr__(self):
        _type = self._clean(self.firstAttr('type'))
        return '<%s>' % ':'.join([p for p in [self.__class__.__name__, _type] if p])

    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        self._data = data
        self.type = data.attrib.get('type')
        self.operators = self.findItems(data, Operator)


class FirstCharacter(PlexObject):
    """ Represents a First Character element from a library.

        Attributes:
            key (str): Url key for character.
            size (str): Total amount of library items starting with this character.
            title (str): Character (#, !, A, B, C, ...).
    """
    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        self._data = data
        self.key = data.attrib.get('key')
        self.size = data.attrib.get('size')
        self.title = data.attrib.get('title')


@utils.registerPlexObject
class Collections(PlexPartialObject):
    """ Represents a single Collection.

        Attributes:
            TAG (str): 'Directory'
            TYPE (str): 'collection'
            addedAt (datetime): Datetime the collection was added to the library.
            art (str): URL to artwork image (/library/metadata/<ratingKey>/art/<artid>).
            artBlurHash (str): BlurHash string for artwork image.
            childCount (int): Number of items in the collection.
            collectionMode (str): How the items in the collection are displayed.
            collectionSort (str): How to sort the items in the collection.
            contentRating (str) Content rating (PG-13; NR; TV-G).
            fields (List<:class:`~plexapi.media.Field`>): List of field objects.
            guid (str): Plex GUID for the collection (collection://XXXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXX).
            index (int): Plex index number for the collection.
            key (str): API URL (/library/metadata/<ratingkey>).
            labels (List<:class:`~plexapi.media.Label`>): List of label objects.
            librarySectionID (int): :class:`~plexapi.library.LibrarySection` ID.
            librarySectionKey (str): :class:`~plexapi.library.LibrarySection` key.
            librarySectionTitle (str): :class:`~plexapi.library.LibrarySection` title.
            maxYear (int): Maximum year for the items in the collection.
            minYear (int): Minimum year for the items in the collection.
            ratingKey (int): Unique key identifying the collection.
            subtype (str): Media type of the items in the collection (movie, show, artist, or album).
            summary (str): Summary of the collection.
            thumb (str): URL to thumbnail image (/library/metadata/<ratingKey>/thumb/<thumbid>).
            thumbBlurHash (str): BlurHash string for thumbnail image.
            title (str): Name of the collection.
            titleSort (str): Title to use when sorting (defaults to title).
            type (str): 'collection'
            updatedAt (datatime): Datetime the collection was updated.
    """

    TAG = 'Directory'
    TYPE = 'collection'

    def _loadData(self, data):
        self.addedAt = utils.toDatetime(data.attrib.get('addedAt'))
        self.art = data.attrib.get('art')
        self.artBlurHash = data.attrib.get('artBlurHash')
        self.childCount = utils.cast(int, data.attrib.get('childCount'))
        self.collectionMode = data.attrib.get('collectionMode')
        self.collectionSort = data.attrib.get('collectionSort')
        self.contentRating = data.attrib.get('contentRating')
        self.fields = self.findItems(data, media.Field)
        self.guid = data.attrib.get('guid')
        self.index = utils.cast(int, data.attrib.get('index'))
        self.key = data.attrib.get('key', '').replace('/children', '')  # FIX_BUG_50
        self.labels = self.findItems(data, media.Label)
        self.librarySectionID = data.attrib.get('librarySectionID')
        self.librarySectionKey = data.attrib.get('librarySectionKey')
        self.librarySectionTitle = data.attrib.get('librarySectionTitle')
        self.maxYear = utils.cast(int, data.attrib.get('maxYear'))
        self.minYear = utils.cast(int, data.attrib.get('minYear'))
        self.ratingKey = utils.cast(int, data.attrib.get('ratingKey'))
        self.subtype = data.attrib.get('subtype')
        self.summary = data.attrib.get('summary')
        self.thumb = data.attrib.get('thumb')
        self.thumbBlurHash = data.attrib.get('thumbBlurHash')
        self.title = data.attrib.get('title')
        self.titleSort = data.attrib.get('titleSort', self.title)
        self.type = data.attrib.get('type')
        self.updatedAt = utils.toDatetime(data.attrib.get('updatedAt'))

    @property
    @deprecated('use "items" instead')
    def children(self):
        return self.fetchItems(self.key)
        
    def item(self, title):
        """ Returns the item in the collection that matches the specified title.

            Parameters:
                title (str): Title of the item to return.
        """
        key = '/library/metadata/%s/children' % self.ratingKey
        return self.fetchItem(key, title__iexact=title)

    def items(self):
        """ Returns a list of all items in the collection. """
        key = '/library/metadata/%s/children' % self.ratingKey
        return self.fetchItems(key)

    def get(self, title):
        """ Alias to :func:`~plexapi.library.Collection.item`. """
        return self.item(title)

    def __len__(self):
        return self.childCount

    def _preferences(self):
        """ Returns a list of :class:`~plexapi.settings.Preferences` objects. """
        items = []
        data = self._server.query(self._details_key)
        for item in data.iter('Setting'):
            items.append(Setting(data=item, server=self._server))

        return items

    def delete(self):
        part = '/library/metadata/%s' % self.ratingKey
        return self._server.query(part, method=self._server._session.delete)

    def modeUpdate(self, mode=None):
        """ Update Collection Mode

            Parameters:
                mode: default     (Library default)
                      hide        (Hide Collection)
                      hideItems   (Hide Items in this Collection)
                      showItems   (Show this Collection and its Items)
            Example:

                collection = 'plexapi.library.Collections'
                collection.updateMode(mode="hide")
        """
        mode_dict = {'default': '-1',
                     'hide': '0',
                     'hideItems': '1',
                     'showItems': '2'}
        key = mode_dict.get(mode)
        if key is None:
            raise BadRequest('Unknown collection mode : %s. Options %s' % (mode, list(mode_dict)))
        part = '/library/metadata/%s/prefs?collectionMode=%s' % (self.ratingKey, key)
        return self._server.query(part, method=self._server._session.put)

    def sortUpdate(self, sort=None):
        """ Update Collection Sorting

            Parameters:
                sort: realease     (Order Collection by realease dates)
                      alpha        (Order Collection Alphabetically)

            Example:

                colleciton = 'plexapi.library.Collections'
                collection.updateSort(mode="alpha")
        """
        sort_dict = {'release': '0',
                     'alpha': '1'}
        key = sort_dict.get(sort)
        if key is None:
            raise BadRequest('Unknown sort dir: %s. Options: %s' % (sort, list(sort_dict)))
        part = '/library/metadata/%s/prefs?collectionSort=%s' % (self.ratingKey, key)
        return self._server.query(part, method=self._server._session.put)

    def posters(self):
        """ Returns list of available poster objects. :class:`~plexapi.media.Poster`. """

        return self.fetchItems('/library/metadata/%s/posters' % self.ratingKey)

    def uploadPoster(self, url=None, filepath=None):
        """ Upload poster from url or filepath. :class:`~plexapi.media.Poster` to :class:`~plexapi.video.Video`. """
        if url:
            key = '/library/metadata/%s/posters?url=%s' % (self.ratingKey, quote_plus(url))
            self._server.query(key, method=self._server._session.post)
        elif filepath:
            key = '/library/metadata/%s/posters?' % self.ratingKey
            data = open(filepath, 'rb').read()
            self._server.query(key, method=self._server._session.post, data=data)

    def setPoster(self, poster):
        """ Set . :class:`~plexapi.media.Poster` to :class:`~plexapi.video.Video` """
        poster.select()

    def arts(self):
        """ Returns list of available art objects. :class:`~plexapi.media.Poster`. """

        return self.fetchItems('/library/metadata/%s/arts' % self.ratingKey)

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

    # def edit(self, **kwargs):
    #    TODO


@utils.registerPlexObject
class Path(PlexObject):
    """ Represents a single directory Path.

        Attributes:
            TAG (str): 'Path'

            home (bool): True if the path is the home directory
            key (str): API URL (/services/browse/<base64path>)
            network (bool): True if path is a network location
            path (str): Full path to folder
            title (str): Folder name
    """
    TAG = 'Path'

    def _loadData(self, data):
        self.home = utils.cast(bool, data.attrib.get('home'))
        self.key = data.attrib.get('key')
        self.network = utils.cast(bool, data.attrib.get('network'))
        self.path = data.attrib.get('path')
        self.title = data.attrib.get('title')

    def browse(self, includeFiles=True):
        """ Alias for :func:`~plexapi.server.PlexServer.browse`. """
        return self._server.browse(self, includeFiles)

    def walk(self):
        """ Alias for :func:`~plexapi.server.PlexServer.walk`. """
        for path, paths, files in self._server.walk(self):
            yield path, paths, files


@utils.registerPlexObject
class File(PlexObject):
    """ Represents a single File.

        Attributes:
            TAG (str): 'File'

            key (str): API URL (/services/browse/<base64path>)
            path (str): Full path to file
            title (str): File name
    """
    TAG = 'File'

    def _loadData(self, data):
        self.key = data.attrib.get('key')
        self.path = data.attrib.get('path')
        self.title = data.attrib.get('title')
