# -*- coding: utf-8 -*-
import re
from datetime import datetime
from urllib.parse import quote_plus, urlencode

from plexapi import X_PLEX_CONTAINER_SIZE, log, media, utils
from plexapi.base import OPERATORS, PlexObject
from plexapi.exceptions import BadRequest, NotFound
from plexapi.settings import Setting
from plexapi.utils import cached_property, deprecated


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
        self.identifier = data.attrib.get('identifier')
        self.mediaTagVersion = data.attrib.get('mediaTagVersion')
        self.title1 = data.attrib.get('title1')
        self.title2 = data.attrib.get('title2')
        self._sectionsByID = {}  # cached sections by key
        self._sectionsByTitle = {}  # cached sections by title

    def _loadSections(self):
        """ Loads and caches all the library sections. """
        key = '/library/sections'
        self._sectionsByID = {}
        self._sectionsByTitle = {}
        for elem in self._server.query(key):
            for cls in (MovieSection, ShowSection, MusicSection, PhotoSection):
                if elem.attrib.get('type') == cls.TYPE:
                    section = cls(self._server, elem, key)
                    self._sectionsByID[section.key] = section
                    self._sectionsByTitle[section.title.lower().strip()] = section

    def sections(self):
        """ Returns a list of all media sections in this library. Library sections may be any of
            :class:`~plexapi.library.MovieSection`, :class:`~plexapi.library.ShowSection`,
            :class:`~plexapi.library.MusicSection`, :class:`~plexapi.library.PhotoSection`.
        """
        self._loadSections()
        return list(self._sectionsByID.values())

    def section(self, title):
        """ Returns the :class:`~plexapi.library.LibrarySection` that matches the specified title.

            Parameters:
                title (str): Title of the section to return.
        """
        normalized_title = title.lower().strip()
        if not self._sectionsByTitle or normalized_title not in self._sectionsByTitle:
            self._loadSections()
        try:
            return self._sectionsByTitle[normalized_title]
        except KeyError:
            raise NotFound(f'Invalid library section: {title}') from None

    def sectionByID(self, sectionID):
        """ Returns the :class:`~plexapi.library.LibrarySection` that matches the specified sectionID.

            Parameters:
                sectionID (int): ID of the section to return.

            Raises:
                :exc:`~plexapi.exceptions.NotFound`: The library section ID is not found on the server.
        """
        if not self._sectionsByID or sectionID not in self._sectionsByID:
            self._loadSections()
        try:
            return self._sectionsByID[sectionID]
        except KeyError:
            raise NotFound(f'Invalid library sectionID: {sectionID}') from None

    def hubs(self, sectionID=None, identifier=None, **kwargs):
        """ Returns a list of :class:`~plexapi.library.Hub` across all library sections.

            Parameters:
                sectionID (int or str or list, optional):
                    IDs of the sections to limit results or "playlists".
                identifier (str or list, optional):
                    Names of identifiers to limit results.
                    Available on `Hub` instances as the `hubIdentifier` attribute.
                    Examples: 'home.continue' or 'home.ondeck'
        """
        if sectionID:
            if not isinstance(sectionID, list):
                sectionID = [sectionID]
            kwargs['contentDirectoryID'] = ",".join(map(str, sectionID))
        if identifier:
            if not isinstance(identifier, list):
                identifier = [identifier]
            kwargs['identifier'] = ",".join(identifier)
        key = f'/hubs{utils.joinArgs(kwargs)}'
        return self.fetchItems(key)

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
            a bit, but I haven't found the documentation for it.

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
        key = f'/library/all{utils.joinArgs(args)}'
        return self.fetchItems(key)

    def cleanBundles(self):
        """ Poster images and other metadata for items in your library are kept in "bundle"
            packages. When you remove items from your library, these bundles aren't immediately
            removed. Removing these old bundles can reduce the size of your install. By default, your
            server will automatically clean up old bundles once a week as part of Scheduled Tasks.
        """
        # TODO: Should this check the response for success or the correct mediaprefix?
        self._server.query('/library/clean/bundles?async=1', method=self._server._session.put)
        return self

    def emptyTrash(self):
        """ If a library has items in the Library Trash, use this option to empty the Trash. """
        for section in self.sections():
            section.emptyTrash()
        return self

    def optimize(self):
        """ The Optimize option cleans up the server database from unused or fragmented data.
            For example, if you have deleted or added an entire library or many items in a
            library, you may like to optimize the database.
        """
        self._server.query('/library/optimize?async=1', method=self._server._session.put)
        return self

    def update(self):
        """ Scan this library for new items."""
        self._server.query('/library/sections/all/refresh')
        return self

    def cancelUpdate(self):
        """ Cancel a library update. """
        key = '/library/sections/all/refresh'
        self._server.query(key, method=self._server._session.delete)
        return self

    def refresh(self):
        """ Forces a download of fresh media information from the internet.
            This can take a long time. Any locked fields are not modified.
        """
        self._server.query('/library/sections/all/refresh?force=1')
        return self

    def deleteMediaPreviews(self):
        """ Delete the preview thumbnails for the all sections. This cannot be
            undone. Recreating media preview files can take hours or even days.
        """
        for section in self.sections():
            section.deleteMediaPreviews()
        return self

    def add(self, name='', type='', agent='', scanner='', location='', language='en', *args, **kwargs):
        """ Simplified add for the most common options.

            Parameters:
                name (str): Name of the library
                agent (str): Example com.plexapp.agents.imdb
                type (str): movie, show, # check me
                location (str or list): /path/to/files, ["/path/to/files", "/path/to/morefiles"]
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

                * **agent** (str): com.plexapp.agents.none, com.plexapp.agents.thetvdb, com.plexapp.agents.themoviedb,
                  tv.plex.agents.series
                * **enableBIFGeneration** (bool): Enable video preview thumbnails. Default value true.
                * **episodeSort** (int): Episode order. Default -1 Possible options: 0:Oldest first, 1:Newest first.
                * **flattenSeasons** (int): Seasons. Default value 0 Possible options: 0:Show,1:Hide.
                * **includeInGlobal** (bool): Include in dashboard. Default value true.
                * **scanner** (str): Plex TV Series, Plex Series Scanner

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
        if isinstance(location, str):
            location = [location]
        locations = []
        for path in location:
            if not self._server.isBrowsable(path):
                raise BadRequest(f'Path: {path} does not exist.')
            locations.append(('location', path))

        part = (f'/library/sections?name={quote_plus(name)}&type={type}&agent={agent}'
                f'&scanner={quote_plus(scanner)}&language={language}&{urlencode(locations, doseq=True)}')
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

    def tags(self, tag):
        """ Returns a list of :class:`~plexapi.library.LibraryMediaTag` objects for the specified tag.

            Parameters:
                tag (str): Tag name (see :data:`~plexapi.utils.TAGTYPES`).
        """
        tagType = utils.tagType(tag)
        data = self._server.query(f'/library/tags?type={tagType}')
        return self.findItems(data)


class LibrarySection(PlexObject):
    """ Base class for a single library section.

        Attributes:
            agent (str): The metadata agent used for the library section (com.plexapp.agents.imdb, etc).
            allowSync (bool): True if you allow syncing content from the library section.
            art (str): Background artwork used to respresent the library section.
            composite (str): Composite image used to represent the library section.
            createdAt (datetime): Datetime the library section was created.
            filters (bool): True if filters are available for the library section.
            key (int): Key (or ID) of this library section.
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
        self.filters = utils.cast(bool, data.attrib.get('filters'))
        self.key = utils.cast(int, data.attrib.get('key'))
        self.language = data.attrib.get('language')
        self.locations = self.listAttrs(data, 'path', etag='Location')
        self.refreshing = utils.cast(bool, data.attrib.get('refreshing'))
        self.scanner = data.attrib.get('scanner')
        self.thumb = data.attrib.get('thumb')
        self.title = data.attrib.get('title')
        self.type = data.attrib.get('type')
        self.updatedAt = utils.toDatetime(data.attrib.get('updatedAt'))
        self.uuid = data.attrib.get('uuid')
        # Private attrs as we don't want a reload.
        self._filterTypes = None
        self._fieldTypes = None
        self._totalViewSize = None
        self._totalDuration = None
        self._totalStorage = None

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
            self._totalViewSize = utils.cast(int, total_size)

        items = self.findItems(data, cls, ekey, **kwargs)

        librarySectionID = utils.cast(int, data.attrib.get('librarySectionID'))
        if librarySectionID:
            for item in items:
                item.librarySectionID = librarySectionID
        return items

    @cached_property
    def totalSize(self):
        """ Returns the total number of items in the library for the default library type. """
        return self.totalViewSize(includeCollections=False)

    @property
    def totalDuration(self):
        """ Returns the total duration (in milliseconds) of items in the library. """
        if self._totalDuration is None:
            self._getTotalDurationStorage()
        return self._totalDuration

    @property
    def totalStorage(self):
        """ Returns the total storage (in bytes) of items in the library. """
        if self._totalStorage is None:
            self._getTotalDurationStorage()
        return self._totalStorage

    def _getTotalDurationStorage(self):
        """ Queries the Plex server for the total library duration and storage and caches the values. """
        data = self._server.query('/media/providers?includeStorage=1')
        xpath = (
            './MediaProvider[@identifier="com.plexapp.plugins.library"]'
            '/Feature[@type="content"]'
            f'/Directory[@id="{self.key}"]'
        )
        directory = next(iter(data.findall(xpath)), None)
        if directory:
            self._totalDuration = utils.cast(int, directory.attrib.get('durationTotal'))
            self._totalStorage = utils.cast(int, directory.attrib.get('storageTotal'))

    def totalViewSize(self, libtype=None, includeCollections=True):
        """ Returns the total number of items in the library for a specified libtype.
            The number of items for the default library type will be returned if no libtype is specified.
            (e.g. Specify ``libtype='episode'`` for the total number of episodes
            or ``libtype='albums'`` for the total number of albums.)

            Parameters:
                libtype (str, optional): The type of items to return the total number for (movie, show, season, episode,
                    artist, album, track, photoalbum). Default is the main library type.
                includeCollections (bool, optional): True or False to include collections in the total number.
                    Default is True.
        """
        args = {
            'includeCollections': int(bool(includeCollections)),
            'X-Plex-Container-Start': 0,
            'X-Plex-Container-Size': 0
        }
        if libtype is not None:
            if libtype == 'photo':
                args['clusterZoomLevel'] = 1
            else:
                args['type'] = utils.searchType(libtype)
        part = f'/library/sections/{self.key}/all{utils.joinArgs(args)}'
        data = self._server.query(part)
        return utils.cast(int, data.attrib.get("totalSize"))

    def delete(self):
        """ Delete a library section. """
        try:
            return self._server.query(f'/library/sections/{self.key}', method=self._server._session.delete)
        except BadRequest:  # pragma: no cover
            msg = f'Failed to delete library {self.key}'
            msg += 'You may need to allow this permission in your Plex settings.'
            log.error(msg)
            raise

    def reload(self):
        """ Reload the data for the library section. """
        self._server.library._loadSections()
        newLibrary = self._server.library.sectionByID(self.key)
        self.__dict__.update(newLibrary.__dict__)
        return self

    def edit(self, agent=None, **kwargs):
        """ Edit a library. See :class:`~plexapi.library.Library` for example usage.

            Parameters:
                agent (str, optional): The library agent.
                kwargs (dict): Dict of settings to edit.
        """
        if not agent:
            agent = self.agent

        locations = []
        if kwargs.get('location'):
            if isinstance(kwargs['location'], str):
                kwargs['location'] = [kwargs['location']]
            for path in kwargs.pop('location'):
                if not self._server.isBrowsable(path):
                    raise BadRequest(f'Path: {path} does not exist.')
                locations.append(('location', path))

        params = list(kwargs.items()) + locations

        part = f'/library/sections/{self.key}?agent={agent}&{urlencode(params, doseq=True)}'
        self._server.query(part, method=self._server._session.put)
        return self

    def addLocations(self, location):
        """ Add a location to a library.
        
            Parameters:
                location (str or list): A single folder path, list of paths.

            Example:

                .. code-block:: python

                LibrarySection.addLocations('/path/1')
                LibrarySection.addLocations(['/path/1', 'path/2', '/path/3'])
        """
        locations = self.locations
        if isinstance(location, str):
            location = [location]
        for path in location:
            if not self._server.isBrowsable(path):
                raise BadRequest(f'Path: {path} does not exist.')
            locations.append(path)
        return self.edit(location=locations)

    def removeLocations(self, location):
        """ Remove a location from a library.
        
            Parameters:
                location (str or list): A single folder path, list of paths.

            Example:

                .. code-block:: python

                LibrarySection.removeLocations('/path/1')
                LibrarySection.removeLocations(['/path/1', 'path/2', '/path/3'])
        """
        locations = self.locations
        if isinstance(location, str):
            location = [location]
        for path in location:
            if path in locations:
                locations.remove(path)
            else:
                raise BadRequest(f'Path: {location} does not exist in the library.')
        if len(locations) == 0:
            raise BadRequest('You are unable to remove all locations from a library.')
        return self.edit(location=locations)

    def get(self, title):
        """ Returns the media item with the specified title.

            Parameters:
                title (str): Title of the item to return.

            Raises:
                :exc:`~plexapi.exceptions.NotFound`: The title is not found in the library.
        """
        try:
            return self.search(title)[0]
        except IndexError:
            raise NotFound(f"Unable to find item '{title}'") from None

    def getGuid(self, guid):
        """ Returns the media item with the specified external Plex, IMDB, TMDB, or TVDB ID.
            Note: Only available for the Plex Movie and Plex TV Series agents.

            Parameters:
                guid (str): The external guid of the item to return.
                    Examples: Plex ``plex://show/5d9c086c46115600200aa2fe``
                    IMDB ``imdb://tt0944947``, TMDB ``tmdb://1399``, TVDB ``tvdb://121361``.

            Raises:
                :exc:`~plexapi.exceptions.NotFound`: The guid is not found in the library.

            Example:

                .. code-block:: python

                    result1 = library.getGuid('plex://show/5d9c086c46115600200aa2fe')
                    result2 = library.getGuid('imdb://tt0944947')
                    result3 = library.getGuid('tmdb://1399')
                    result4 = library.getGuid('tvdb://121361')

                    # Alternatively, create your own guid lookup dictionary for faster performance
                    guidLookup = {}
                    for item in library.all():
                        guidLookup[item.guid] = item
                        guidLookup.update({guid.id: item for guid in item.guids}}

                    result1 = guidLookup['plex://show/5d9c086c46115600200aa2fe']
                    result2 = guidLookup['imdb://tt0944947']
                    result3 = guidLookup['tmdb://1399']
                    result4 = guidLookup['tvdb://121361']

        """

        try:
            if guid.startswith('plex://'):
                result = self.search(guid=guid)[0]
                return result
            else:
                dummy = self.search(maxresults=1)[0]
                match = dummy.matches(agent=self.agent, title=guid.replace('://', '-'))
                return self.search(guid=match[0].guid)[0]
        except IndexError:
            raise NotFound(f"Guid '{guid}' is not found in the library") from None

    def all(self, libtype=None, **kwargs):
        """ Returns a list of all items from this library section.
            See description of :func:`~plexapi.library.LibrarySection.search()` for details about filtering / sorting.
        """
        libtype = libtype or self.TYPE
        return self.search(libtype=libtype, **kwargs)

    def folders(self):
        """ Returns a list of available :class:`~plexapi.library.Folder` for this library section.
        """
        key = f'/library/sections/{self.key}/folder'
        return self.fetchItems(key, Folder)

    def managedHubs(self):
        """ Returns a list of available :class:`~plexapi.library.ManagedHub` for this library section.
        """
        key = f'/hubs/sections/{self.key}/manage'
        return self.fetchItems(key, ManagedHub)

    def resetManagedHubs(self):
        """ Reset the managed hub customizations for this library section.
        """
        key = f'/hubs/sections/{self.key}/manage'
        self._server.query(key, method=self._server._session.delete)

    def hubs(self):
        """ Returns a list of available :class:`~plexapi.library.Hub` for this library section.
        """
        key = f'/hubs/sections/{self.key}?includeStations=1'
        return self.fetchItems(key)

    def agents(self):
        """ Returns a list of available :class:`~plexapi.media.Agent` for this library section.
        """
        return self._server.agents(self.type)

    def settings(self):
        """ Returns a list of all library settings. """
        key = f'/library/sections/{self.key}/prefs'
        data = self._server.query(key)
        return self.findItems(data, cls=Setting)

    def editAdvanced(self, **kwargs):
        """ Edit a library's advanced settings. """
        data = {}
        idEnums = {}
        key = 'prefs[{}]'

        for setting in self.settings():
            if setting.type != 'bool':
                idEnums[setting.id] = setting.enumValues
            else:
                idEnums[setting.id] = {0: False, 1: True}

        for settingID, value in kwargs.items():
            try:
                enums = idEnums[settingID]
            except KeyError:
                raise NotFound(f'{value} not found in {list(idEnums.keys())}')
            if value in enums:
                data[key.format(settingID)] = value
            else:
                raise NotFound(f'{value} not found in {enums}')

        return self.edit(**data)

    def defaultAdvanced(self):
        """ Edit all of library's advanced settings to default. """
        data = {}
        key = 'prefs[{}]'
        for setting in self.settings():
            if setting.type == 'bool':
                data[key.format(setting.id)] = int(setting.default)
            else:
                data[key.format(setting.id)] = setting.default

        return self.edit(**data)

    def _lockUnlockAllField(self, field, libtype=None, locked=True):
        """ Lock or unlock a field for all items in the library. """
        libtype = libtype or self.TYPE
        args = {
            'type': utils.searchType(libtype),
            f'{field}.locked': int(locked)
        }
        key = f'/library/sections/{self.key}/all{utils.joinArgs(args)}'
        self._server.query(key, method=self._server._session.put)
        return self

    def lockAllField(self, field, libtype=None):
        """ Lock a field for all items in the library.
        
            Parameters:
                field (str): The field to lock (e.g. thumb, rating, collection).
                libtype (str, optional): The library type to lock (movie, show, season, episode,
                    artist, album, track, photoalbum, photo). Default is the main library type.
        """
        return self._lockUnlockAllField(field, libtype=libtype, locked=True)

    def unlockAllField(self, field, libtype=None):
        """ Unlock a field for all items in the library.
        
            Parameters:
                field (str): The field to unlock (e.g. thumb, rating, collection).
                libtype (str, optional): The library type to lock (movie, show, season, episode,
                    artist, album, track, photoalbum, photo). Default is the main library type.
        """
        return self._lockUnlockAllField(field, libtype=libtype, locked=False)

    def timeline(self):
        """ Returns a timeline query for this library section. """
        key = f'/library/sections/{self.key}/timeline'
        data = self._server.query(key)
        return LibraryTimeline(self, data)

    def onDeck(self):
        """ Returns a list of media items on deck from this library section. """
        key = f'/library/sections/{self.key}/onDeck'
        return self.fetchItems(key)

    def recentlyAdded(self, maxresults=50, libtype=None):
        """ Returns a list of media items recently added from this library section.

            Parameters:
                maxresults (int): Max number of items to return (default 50).
                libtype (str, optional): The library type to filter (movie, show, season, episode,
                    artist, album, track, photoalbum, photo). Default is the main library type.
        """
        libtype = libtype or self.TYPE
        return self.search(sort='addedAt:desc', maxresults=maxresults, libtype=libtype)

    def firstCharacter(self):
        key = f'/library/sections/{self.key}/firstCharacter'
        return self.fetchItems(key, cls=FirstCharacter)

    def analyze(self):
        """ Run an analysis on all of the items in this library section. See
            See :func:`~plexapi.base.PlexPartialObject.analyze` for more details.
        """
        key = f'/library/sections/{self.key}/analyze'
        self._server.query(key, method=self._server._session.put)
        return self

    def emptyTrash(self):
        """ If a section has items in the Trash, use this option to empty the Trash. """
        key = f'/library/sections/{self.key}/emptyTrash'
        self._server.query(key, method=self._server._session.put)
        return self

    def update(self, path=None):
        """ Scan this section for new media.

            Parameters:
                path (str, optional): Full path to folder to scan.
        """
        key = f'/library/sections/{self.key}/refresh'
        if path is not None:
            key += f'?path={quote_plus(path)}'
        self._server.query(key)
        return self

    def cancelUpdate(self):
        """ Cancel update of this Library Section. """
        key = f'/library/sections/{self.key}/refresh'
        self._server.query(key, method=self._server._session.delete)
        return self

    def refresh(self):
        """ Forces a download of fresh media information from the internet.
            This can take a long time. Any locked fields are not modified.
        """
        key = f'/library/sections/{self.key}/refresh?force=1'
        self._server.query(key)
        return self

    def deleteMediaPreviews(self):
        """ Delete the preview thumbnails for items in this library. This cannot
            be undone. Recreating media preview files can take hours or even days.
        """
        key = f'/library/sections/{self.key}/indexes'
        self._server.query(key, method=self._server._session.delete)
        return self

    def _loadFilters(self):
        """ Retrieves and caches the list of :class:`~plexapi.library.FilteringType` and
            list of :class:`~plexapi.library.FilteringFieldType` for this library section.
        """
        _key = ('/library/sections/{key}/{filter}?includeMeta=1&includeAdvanced=1'
                '&X-Plex-Container-Start=0&X-Plex-Container-Size=0')
               
        key = _key.format(key=self.key, filter='all')
        data = self._server.query(key)
        self._filterTypes = self.findItems(data, FilteringType, rtag='Meta')
        self._fieldTypes = self.findItems(data, FilteringFieldType, rtag='Meta')

        if self.TYPE != 'photo':  # No collections for photo library
            key = _key.format(key=self.key, filter='collections')
            data = self._server.query(key)
            self._filterTypes.extend(self.findItems(data, FilteringType, rtag='Meta'))

        # Manually add guid field type, only allowing "is" operator
        guidFieldType = '<FieldType type="guid"><Operator key="=" title="is"/></FieldType>'
        self._fieldTypes.append(self._manuallyLoadXML(guidFieldType, FilteringFieldType))

    def filterTypes(self):
        """ Returns a list of available :class:`~plexapi.library.FilteringType` for this library section. """
        if self._filterTypes is None:
            self._loadFilters()
        return self._filterTypes

    def getFilterType(self, libtype=None):
        """ Returns a :class:`~plexapi.library.FilteringType` for a specified libtype.

            Parameters:
                libtype (str, optional): The library type to filter (movie, show, season, episode,
                    artist, album, track, photoalbum, photo, collection).

            Raises:
                :exc:`~plexapi.exceptions.NotFound`: Unknown libtype for this library.
        """
        libtype = libtype or self.TYPE
        try:
            return next(f for f in self.filterTypes() if f.type == libtype)
        except StopIteration:
            availableLibtypes = [f.type for f in self.filterTypes()]
            raise NotFound(f'Unknown libtype "{libtype}" for this library. '
                           f'Available libtypes: {availableLibtypes}') from None

    def fieldTypes(self):
        """ Returns a list of available :class:`~plexapi.library.FilteringFieldType` for this library section. """
        if self._fieldTypes is None:
            self._loadFilters()
        return self._fieldTypes

    def getFieldType(self, fieldType):
        """ Returns a :class:`~plexapi.library.FilteringFieldType` for a specified fieldType.
        
            Parameters:
                fieldType (str): The data type for the field (tag, integer, string, boolean, date,
                    subtitleLanguage, audioLanguage, resolution).

            Raises:
                :exc:`~plexapi.exceptions.NotFound`: Unknown fieldType for this library.
        """
        try:
            return next(f for f in self.fieldTypes() if f.type == fieldType)
        except StopIteration:
            availableFieldTypes = [f.type for f in self.fieldTypes()]
            raise NotFound(f'Unknown field type "{fieldType}" for this library. '
                           f'Available field types: {availableFieldTypes}') from None

    def listFilters(self, libtype=None):
        """ Returns a list of available :class:`~plexapi.library.FilteringFilter` for a specified libtype.
            This is the list of options in the filter dropdown menu
            (`screenshot <../_static/images/LibrarySection.listFilters.png>`__).

            Parameters:
                libtype (str, optional): The library type to filter (movie, show, season, episode,
                    artist, album, track, photoalbum, photo, collection).

            Example:

                .. code-block:: python

                    availableFilters = [f.filter for f in library.listFilters()]
                    print("Available filter fields:", availableFilters)

        """
        return self.getFilterType(libtype).filters
        
    def listSorts(self, libtype=None):
        """ Returns a list of available :class:`~plexapi.library.FilteringSort` for a specified libtype.
            This is the list of options in the sorting dropdown menu
            (`screenshot <../_static/images/LibrarySection.listSorts.png>`__).

            Parameters:
                libtype (str, optional): The library type to filter (movie, show, season, episode,
                    artist, album, track, photoalbum, photo, collection).

            Example:

                .. code-block:: python

                    availableSorts = [f.key for f in library.listSorts()]
                    print("Available sort fields:", availableSorts)

        """
        return self.getFilterType(libtype).sorts

    def listFields(self, libtype=None):
        """ Returns a list of available :class:`~plexapi.library.FilteringFields` for a specified libtype.
            This is the list of options in the custom filter dropdown menu
            (`screenshot <../_static/images/LibrarySection.search.png>`__).

            Parameters:
                libtype (str, optional): The library type to filter (movie, show, season, episode,
                    artist, album, track, photoalbum, photo, collection).

            Example:

                .. code-block:: python

                    availableFields = [f.key.split('.')[-1] for f in library.listFields()]
                    print("Available fields:", availableFields)

        """
        return self.getFilterType(libtype).fields

    def listOperators(self, fieldType):
        """ Returns a list of available :class:`~plexapi.library.FilteringOperator` for a specified fieldType.
            This is the list of options in the custom filter operator dropdown menu
            (`screenshot <../_static/images/LibrarySection.search.png>`__).
        
            Parameters:
                fieldType (str): The data type for the field (tag, integer, string, boolean, date,
                    subtitleLanguage, audioLanguage, resolution).

            Example:

                .. code-block:: python

                    field = 'genre'  # Available filter field from listFields()
                    filterField = next(f for f in library.listFields() if f.key.endswith(field))
                    availableOperators = [o.key for o in library.listOperators(filterField.type)]
                    print(f"Available operators for {field}:", availableOperators)

        """
        return self.getFieldType(fieldType).operators

    def listFilterChoices(self, field, libtype=None):
        """ Returns a list of available :class:`~plexapi.library.FilterChoice` for a specified
            :class:`~plexapi.library.FilteringFilter` or filter field.
            This is the list of available values for a custom filter
            (`screenshot <../_static/images/LibrarySection.search.png>`__).
            
            Parameters:
                field (str): :class:`~plexapi.library.FilteringFilter` object,
                    or the name of the field (genre, year, contentRating, etc.).
                libtype (str, optional): The library type to filter (movie, show, season, episode,
                    artist, album, track, photoalbum, photo, collection).

            Raises:
                :exc:`~plexapi.exceptions.BadRequest`: Invalid filter field.
                :exc:`~plexapi.exceptions.NotFound`: Unknown filter field.

            Example:

                .. code-block:: python

                    field = 'genre'  # Available filter field from listFilters()
                    availableChoices = [f.title for f in library.listFilterChoices(field)]
                    print(f"Available choices for {field}:", availableChoices)

        """
        if isinstance(field, str):
            match = re.match(r'(?:([a-zA-Z]*)\.)?([a-zA-Z]+)', field)
            if not match:
                raise BadRequest(f'Invalid filter field: {field}')
            _libtype, field = match.groups()
            libtype = _libtype or libtype or self.TYPE
            try:
                field = next(f for f in self.listFilters(libtype) if f.filter == field)
            except StopIteration:
                availableFilters = [f.filter for f in self.listFilters(libtype)]
                raise NotFound(f'Unknown filter field "{field}" for libtype "{libtype}". '
                               f'Available filters: {availableFilters}') from None
                
        data = self._server.query(field.key)
        return self.findItems(data, FilterChoice)

    def _validateFilterField(self, field, values, libtype=None):
        """ Validates a filter field and values are available as a custom filter for the library.
            Returns the validated field and values as a URL encoded parameter string.
        """
        match = re.match(r'(?:([a-zA-Z]*)\.)?([a-zA-Z]+)([!<>=&]*)', field)
        if not match:
            raise BadRequest(f'Invalid filter field: {field}')
        _libtype, field, operator = match.groups()
        libtype = _libtype or libtype or self.TYPE

        try:
            filterField = next(f for f in self.listFields(libtype) if f.key.split('.')[-1] == field)
        except StopIteration:
            for filterType in reversed(self.filterTypes()):
                if filterType.type != libtype:
                    filterField = next((f for f in filterType.fields if f.key.split('.')[-1] == field), None)
                    if filterField:
                        break
            else:
                availableFields = [f.key for f in self.listFields(libtype)]
                raise NotFound(f'Unknown filter field "{field}" for libtype "{libtype}". '
                               f'Available filter fields: {availableFields}') from None

        field = filterField.key
        operator = self._validateFieldOperator(filterField, operator)
        result = self._validateFieldValue(filterField, values, libtype)

        if operator == '&=':
            args = {field: result}
            return urlencode(args, doseq=True)
        else:
            args = {field + operator[:-1]: ','.join(result)}
            return urlencode(args)

    def _validateFieldOperator(self, filterField, operator):
        """ Validates filter operator is in the available operators.
            Returns the validated operator string.
        """
        fieldType = self.getFieldType(filterField.type)

        and_operator = False
        if operator in {'&', '&='}:
            and_operator = True
            operator = ''
        if fieldType.type == 'string' and operator in {'=', '!='}:
            operator += '='
        operator = (operator[:-1] if operator[-1:] == '=' else operator) + '='

        try:
            next(o for o in fieldType.operators if o.key == operator)
        except StopIteration:
            availableOperators = [o.key for o in self.listOperators(filterField.type)]
            raise NotFound(f'Unknown operator "{operator}" for filter field "{filterField.key}". '
                           f'Available operators: {availableOperators}') from None

        return '&=' if and_operator else operator

    def _validateFieldValue(self, filterField, values, libtype=None):
        """ Validates filter values are the correct datatype and in the available filter choices.
            Returns the validated list of values.
        """
        if not isinstance(values, (list, tuple)):
            values = [values]

        fieldType = self.getFieldType(filterField.type)
        results = []

        try:
            for value in values:
                if fieldType.type == 'boolean':
                    value = int(bool(value))
                elif fieldType.type == 'date':
                    value = self._validateFieldValueDate(value)
                elif fieldType.type == 'integer':
                    value = float(value) if '.' in str(value) else int(value)
                elif fieldType.type == 'string':
                    value = str(value)
                elif fieldType.type in {'tag', 'subtitleLanguage', 'audioLanguage', 'resolution'}:
                    value = self._validateFieldValueTag(value, filterField, libtype)
                results.append(str(value))
        except (ValueError, AttributeError):
            raise BadRequest(f'Invalid value "{value}" for filter field "{filterField.key}", '
                             f'value should be type {fieldType.type}') from None
    
        return results

    def _validateFieldValueDate(self, value):
        """ Validates a filter date value. A filter date value can be a datetime object,
            a relative date (e.g. -30d), or a date in YYYY-MM-DD format.
        """
        if isinstance(value, datetime):
            return int(value.timestamp())
        elif re.match(r'^-?\d+(mon|[smhdwy])$', value):
            return '-' + value.lstrip('-')
        else:
            return int(utils.toDatetime(value, '%Y-%m-%d').timestamp())

    def _validateFieldValueTag(self, value, filterField, libtype):
        """ Validates a filter tag value. A filter tag value can be a :class:`~plexapi.library.FilterChoice` object,
            a :class:`~plexapi.media.MediaTag` object, the exact name :attr:`MediaTag.tag` (*str*),
            or the exact id :attr:`MediaTag.id` (*int*).
        """
        if isinstance(value, FilterChoice):
            return value.key
        if isinstance(value, (media.MediaTag, LibraryMediaTag)):
            value = str(value.id or value.tag)
        else:
            value = str(value)
        filterChoices = self.listFilterChoices(filterField.key, libtype)
        matchValue = value.lower()
        return next((f.key for f in filterChoices if matchValue in {f.key.lower(), f.title.lower()}), value)

    def _validateSortFields(self, sort, libtype=None):
        """ Validates a list of filter sort fields is available for the library. Sort fields can be a
            list of :class:`~plexapi.library.FilteringSort` objects, or a comma separated string.
            Returns the validated comma separated sort fields string.
        """
        if isinstance(sort, str):
            sort = sort.split(',')

        if not isinstance(sort, (list, tuple)):
            sort = [sort]

        validatedSorts = []
        for _sort in sort:
            validatedSorts.append(self._validateSortField(_sort, libtype))

        return ','.join(validatedSorts)

    def _validateSortField(self, sort, libtype=None):
        """ Validates a filter sort field is available for the library. A sort field can be a
            :class:`~plexapi.library.FilteringSort` object, or a string.
            Returns the validated sort field string.
        """
        if isinstance(sort, FilteringSort):
            return f'{libtype or self.TYPE}.{sort.key}:{sort.defaultDirection}'

        match = re.match(r'(?:([a-zA-Z]*)\.)?([a-zA-Z]+):?([a-zA-Z]*)', sort.strip())
        if not match:
            raise BadRequest(f'Invalid filter sort: {sort}')
        _libtype, sortField, sortDir = match.groups()
        libtype = _libtype or libtype or self.TYPE

        try:
            filterSort = next(f for f in self.listSorts(libtype) if f.key == sortField)
        except StopIteration:
            availableSorts = [f.key for f in self.listSorts(libtype)]
            raise NotFound(f'Unknown sort field "{sortField}" for libtype "{libtype}". '
                           f'Available sort fields: {availableSorts}') from None

        sortField = libtype + '.' + filterSort.key

        availableDirections = ['', 'asc', 'desc', 'nullsLast']
        if sortDir not in availableDirections:
            raise NotFound(f'Unknown sort direction "{sortDir}". Available sort directions: {availableDirections}')

        return f'{sortField}:{sortDir}' if sortDir else sortField

    def _validateAdvancedSearch(self, filters, libtype):
        """ Validates an advanced search filter dictionary.
            Returns the list of validated URL encoded parameter strings for the advanced search.
        """
        if not isinstance(filters, dict):
            raise BadRequest('Filters must be a dictionary.')

        validatedFilters = []

        for field, values in filters.items():
            if field.lower() in {'and', 'or'}:
                if len(filters.items()) > 1:
                    raise BadRequest('Multiple keys in the same dictionary with and/or is not allowed.')
                if not isinstance(values, list):
                    raise BadRequest('Value for and/or keys must be a list of dictionaries.')

                validatedFilters.append('push=1')

                for value in values:
                    validatedFilters.extend(self._validateAdvancedSearch(value, libtype))
                    validatedFilters.append(f'{field.lower()}=1')

                del validatedFilters[-1]
                validatedFilters.append('pop=1')

            else:
                validatedFilters.append(self._validateFilterField(field, values, libtype))

        return validatedFilters

    def _buildSearchKey(self, title=None, sort=None, libtype=None, limit=None, filters=None, returnKwargs=False, **kwargs):
        """ Returns the validated and formatted search query API key
            (``/library/sections/<sectionKey>/all?<params>``).
        """
        args = {}
        filter_args = []

        args['includeGuids'] = int(bool(kwargs.pop('includeGuids', True)))
        for field, values in list(kwargs.items()):
            if field.split('__')[-1] not in OPERATORS:
                filter_args.append(self._validateFilterField(field, values, libtype))
                del kwargs[field]
        if title is not None:
            if isinstance(title, (list, tuple)):
                filter_args.append(self._validateFilterField('title', title, libtype))
            else:
                args['title'] = title
        if filters is not None:
            filter_args.extend(self._validateAdvancedSearch(filters, libtype))
        if sort is not None:
            args['sort'] = self._validateSortFields(sort, libtype)
        if libtype is not None:
            args['type'] = utils.searchType(libtype)
        if limit is not None:
            args['limit'] = limit

        joined_args = utils.joinArgs(args).lstrip('?')
        joined_filter_args = '&'.join(filter_args) if filter_args else ''
        params = '&'.join([joined_args, joined_filter_args]).strip('&')
        key = f'/library/sections/{self.key}/all?{params}'

        if returnKwargs:
            return key, kwargs
        return key

    def hubSearch(self, query, mediatype=None, limit=None):
        """ Returns the hub search results for this library. See :func:`plexapi.server.PlexServer.search`
            for details and parameters.
        """
        return self._server.search(query, mediatype, limit, sectionId=self.key)

    def search(self, title=None, sort=None, maxresults=None, libtype=None,
               container_start=0, container_size=X_PLEX_CONTAINER_SIZE, limit=None, filters=None, **kwargs):
        """ Search the library. The http requests will be batched in container_size. If you are only looking for the
            first <num> results, it would be wise to set the maxresults option to that amount so the search doesn't iterate
            over all results on the server.

            Parameters:
                title (str, optional): General string query to search for. Partial string matches are allowed.
                sort (:class:`~plexapi.library.FilteringSort` or str or list, optional): A field to sort the results.
                    See the details below for more info.
                maxresults (int, optional): Only return the specified number of results.
                libtype (str, optional): Return results of a specific type (movie, show, season, episode,
                    artist, album, track, photoalbum, photo, collection) (e.g. ``libtype='episode'`` will only
                    return :class:`~plexapi.video.Episode` objects)
                container_start (int, optional): Default 0.
                container_size (int, optional): Default X_PLEX_CONTAINER_SIZE in your config file.
                limit (int, optional): Limit the number of results from the filter.
                filters (dict, optional): A dictionary of advanced filters. See the details below for more info.
                **kwargs (dict): Additional custom filters to apply to the search results.
                    See the details below for more info.

            Raises:
                :exc:`~plexapi.exceptions.BadRequest`: When the sort or filter is invalid.
                :exc:`~plexapi.exceptions.NotFound`: When applying an unknown sort or filter.

            **Sorting Results**

            The search results can be sorted by including the ``sort`` parameter.

            * See :func:`~plexapi.library.LibrarySection.listSorts` to get a list of available sort fields.

            The ``sort`` parameter can be a :class:`~plexapi.library.FilteringSort` object or a sort string in the
            format ``field:dir``. The sort direction ``dir`` can be ``asc``, ``desc``, or ``nullsLast``. Omitting the
            sort direction or using a :class:`~plexapi.library.FilteringSort` object will sort the results in the default
            direction of the field. Multi-sorting on multiple fields can be achieved by using a comma separated list of
            sort strings, or a list of :class:`~plexapi.library.FilteringSort` object or strings.

            Examples:

                .. code-block:: python

                    library.search(sort="titleSort:desc")  # Sort title in descending order
                    library.search(sort="titleSort")  # Sort title in the default order
                    # Multi-sort by year in descending order, then by audience rating in descending order
                    library.search(sort="year:desc,audienceRating:desc")
                    library.search(sort=["year:desc", "audienceRating:desc"])

            **Using Plex Filters**

            Any of the available custom filters can be applied to the search results
            (`screenshot <../_static/images/LibrarySection.search.png>`__).

            * See :func:`~plexapi.library.LibrarySection.listFields` to get a list of all available fields.
            * See :func:`~plexapi.library.LibrarySection.listOperators` to get a list of all available operators.
            * See :func:`~plexapi.library.LibrarySection.listFilterChoices` to get a list of all available filter values.

            The following filter fields are just some examples of the possible filters. The list is not exhaustive,
            and not all filters apply to all library types.

            * **actor** (:class:`~plexapi.media.MediaTag`): Search for the name of an actor.
            * **addedAt** (*datetime*): Search for items added before or after a date. See operators below.
            * **audioLanguage** (*str*): Search for a specific audio language (3 character code, e.g. jpn).
            * **collection** (:class:`~plexapi.media.MediaTag`): Search for the name of a collection.
            * **contentRating** (:class:`~plexapi.media.MediaTag`): Search for a specific content rating.
            * **country** (:class:`~plexapi.media.MediaTag`): Search for the name of a country.
            * **decade** (*int*): Search for a specific decade (e.g. 2000).
            * **director** (:class:`~plexapi.media.MediaTag`): Search for the name of a director.
            * **duplicate** (*bool*) Search for duplicate items.
            * **genre** (:class:`~plexapi.media.MediaTag`): Search for a specific genre.
            * **hdr** (*bool*): Search for HDR items.
            * **inProgress** (*bool*): Search for in progress items.
            * **label** (:class:`~plexapi.media.MediaTag`): Search for a specific label.
            * **lastViewedAt** (*datetime*): Search for items watched before or after a date. See operators below.
            * **mood** (:class:`~plexapi.media.MediaTag`): Search for a specific mood.
            * **producer** (:class:`~plexapi.media.MediaTag`): Search for the name of a producer.
            * **resolution** (*str*): Search for a specific resolution (e.g. 1080).
            * **studio** (*str*): Search for the name of a studio.
            * **style** (:class:`~plexapi.media.MediaTag`): Search for a specific style.
            * **subtitleLanguage** (*str*): Search for a specific subtitle language (3 character code, e.g. eng)
            * **unmatched** (*bool*): Search for unmatched items.
            * **unwatched** (*bool*): Search for unwatched items.
            * **userRating** (*int*): Search for items with a specific user rating.
            * **writer** (:class:`~plexapi.media.MediaTag`): Search for the name of a writer.
            * **year** (*int*): Search for a specific year.

            Tag type filter values can be a :class:`~plexapi.library.FilterChoice` object,
            :class:`~plexapi.media.MediaTag` object, the exact name :attr:`MediaTag.tag` (*str*),
            or the exact id :attr:`MediaTag.id` (*int*).
            
            Date type filter values can be a ``datetime`` object, a relative date using a one of the
            available date suffixes (e.g. ``30d``) (*str*), or a date in ``YYYY-MM-DD`` (*str*) format.

            Relative date suffixes:

            * ``s``: ``seconds``
            * ``m``: ``minutes``
            * ``h``: ``hours``
            * ``d``: ``days``
            * ``w``: ``weeks``
            * ``mon``: ``months``
            * ``y``: ``years``
            
            Multiple values can be ``OR`` together by providing a list of values.

            Examples:

                .. code-block:: python

                    library.search(unwatched=True, year=2020, resolution="4k")
                    library.search(actor="Arnold Schwarzenegger", decade=1990)
                    library.search(contentRating="TV-G", genre="animation")
                    library.search(genre=["animation", "comedy"])  # Genre is animation OR comedy
                    library.search(studio=["Disney", "Pixar"])  # Studio contains Disney OR Pixar

            **Using a** ``libtype`` **Prefix**

            Some filters may be prefixed by the ``libtype`` separated by a ``.`` (e.g. ``show.collection``,
            ``episode.title``, ``artist.style``, ``album.genre``, ``track.userRating``, etc.). This should not be
            confused with the ``libtype`` parameter. If no ``libtype`` prefix is provided, then the default library
            type is assumed. For example, in a TV show library ``viewCount`` is assumed to be ``show.viewCount``.
            If you want to filter using episode view count then you must specify ``episode.viewCount`` explicitly.
            In addition, if the filter does not exist for the default library type it will fallback to the most
            specific ``libtype`` available. For example, ``show.unwatched`` does not exists so it will fallback to
            ``episode.unwatched``. The ``libtype`` prefix cannot be included directly in the function parameters so
            the filters must be provided as a filters dictionary.

            Examples:

                .. code-block:: python

                    library.search(filters={"show.collection": "Documentary", "episode.inProgress": True})
                    library.search(filters={"artist.genre": "pop", "album.decade": 2000})

                    # The following three options are identical and will return Episode objects
                    showLibrary.search(title="Winter is Coming", libtype='episode')
                    showLibrary.search(libtype='episode', filters={"episode.title": "Winter is Coming"})
                    showLibrary.searchEpisodes(title="Winter is Coming")

                    # The following will search for the episode title but return Show objects
                    showLibrary.search(filters={"episode.title": "Winter is Coming"})

                    # The following will fallback to episode.unwatched
                    showLibrary.search(unwatched=True)

            **Using Plex Operators**

            Operators can be appended to the filter field to narrow down results with more granularity.
            The following is a list of possible operators depending on the data type of the filter being applied.
            A special ``&`` operator can also be used to ``AND`` together a list of values.

            Type: :class:`~plexapi.media.MediaTag` or *subtitleLanguage* or *audioLanguage*

            * no operator: ``is``
            * ``!``: ``is not``

            Type: *int*

            * no operator: ``is``
            * ``!``: ``is not``
            * ``>>``: ``is greater than``
            * ``<<``: ``is less than``

            Type: *str*

            * no operator: ``contains``
            * ``!``: ``does not contain``
            * ``=``: ``is``
            * ``!=``: ``is not``
            * ``<``: ``begins with``
            * ``>``: ``ends with``

            Type: *bool*

            * no operator: ``is true``
            * ``!``: ``is false``

            Type: *datetime*

            * ``<<``: ``is before``
            * ``>>``: ``is after``

            Type: *resolution* or *guid*

            * no operator: ``is``

            Operators cannot be included directly in the function parameters so the filters
            must be provided as a filters dictionary.

            Examples:

                .. code-block:: python

                    # Genre is horror AND thriller
                    library.search(filters={"genre&": ["horror", "thriller"]})

                    # Director is not Steven Spielberg
                    library.search(filters={"director!": "Steven Spielberg"})

                    # Title starts with Marvel and added before 2021-01-01
                    library.search(filters={"title<": "Marvel", "addedAt<<": "2021-01-01"})

                    # Added in the last 30 days using relative dates
                    library.search(filters={"addedAt>>": "30d"})

                    # Collection is James Bond and user rating is greater than 8
                    library.search(filters={"collection": "James Bond", "userRating>>": 8})

            **Using Advanced Filters**

            Any of the Plex filters described above can be combined into a single ``filters`` dictionary that mimics
            the advanced filters used in Plex Web with a tree of ``and``/``or`` branches. Each level of the tree must
            start with ``and`` (Match all of the following) or ``or`` (Match any of the following) as the dictionary
            key, and a list of dictionaries with the desired filters as the dictionary value.

            The following example matches `this <../_static/images/LibrarySection.search_filters.png>`__ advanced filter
            in Plex Web.

            Examples:

                .. code-block:: python

                    advancedFilters = {
                        'and': [                            # Match all of the following in this list
                            {
                                'or': [                     # Match any of the following in this list
                                    {'title': 'elephant'},
                                    {'title': 'bunny'}
                                ]
                            },
                            {'year>>': 1990},
                            {'unwatched': True}
                        ]
                    }
                    library.search(filters=advancedFilters)

            **Using PlexAPI Operators**

            For even more advanced filtering which cannot be achieved in Plex, the PlexAPI operators can be applied
            to any XML attribute. See :func:`plexapi.base.PlexObject.fetchItems` for a list of operators and how they
            are used. Note that using the Plex filters above will be faster since the filters are applied by the Plex
            server before the results are returned to PlexAPI. Using the PlexAPI operators requires the Plex server
            to return *all* results to allow PlexAPI to do the filtering. The Plex filters and the PlexAPI operators
            can be used in conjunction with each other.

            Examples:

                .. code-block:: python

                    library.search(summary__icontains="Christmas")
                    library.search(duration__gt=7200000)
                    library.search(audienceRating__lte=6.0, audienceRatingImage__startswith="rottentomatoes://")
                    library.search(media__videoCodec__exact="h265")
                    library.search(genre="holiday", viewCount__gte=3)

        """
        key, kwargs = self._buildSearchKey(
            title=title, sort=sort, libtype=libtype, limit=limit, filters=filters, returnKwargs=True, **kwargs)
        return self._search(key, maxresults, container_start, container_size, **kwargs)

    def _search(self, key, maxresults, container_start, container_size, **kwargs):
        """ Perform the actual library search and return the results. """
        results = []
        subresults = []
        offset = container_start

        if maxresults is not None:
            container_size = min(container_size, maxresults)

        while True:
            subresults = self.fetchItems(key, container_start=container_start,
                                         container_size=container_size, **kwargs)
            if not len(subresults):
                if offset > self._totalViewSize:
                    log.info("container_start is higher than the number of items in the library")

            results.extend(subresults)

            # self._totalViewSize is not used as a condition in the while loop as
            # this require a additional http request.
            # self._totalViewSize is updated from self.fetchItems
            wanted_number_of_items = self._totalViewSize - offset
            if maxresults is not None:
                wanted_number_of_items = min(maxresults, wanted_number_of_items)
                container_size = min(container_size, maxresults - len(results))

            if wanted_number_of_items <= len(results):
                break

            container_start += container_size

            if container_start > self._totalViewSize:
                break

        return results

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
                :exc:`~plexapi.exceptions.BadRequest`: When the sort or filter is invalid.
                :exc:`~plexapi.exceptions.NotFound`: When applying an unknown sort or filter.

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

        myplex = self._server.myPlexAccount()
        sync_item = SyncItem(self._server, None)
        sync_item.title = title if title else self.title
        sync_item.rootTitle = self.title
        sync_item.contentType = self.CONTENT_TYPE
        sync_item.metadataType = self.METADATA_TYPE
        sync_item.machineIdentifier = self._server.machineIdentifier

        key = self._buildSearchKey(title=title, sort=sort, libtype=libtype, **kwargs)

        sync_item.location = f'library://{self.uuid}/directory/{quote_plus(key)}'
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

    def createCollection(self, title, items=None, smart=False, limit=None,
                         libtype=None, sort=None, filters=None, **kwargs):
        """ Alias for :func:`~plexapi.server.PlexServer.createCollection` using this
            :class:`~plexapi.library.LibrarySection`.
        """
        return self._server.createCollection(
            title, section=self, items=items, smart=smart, limit=limit,
            libtype=libtype, sort=sort, filters=filters, **kwargs)

    def collection(self, title):
        """ Returns the collection with the specified title.

            Parameters:
                title (str): Title of the item to return.

            Raises:
                :exc:`~plexapi.exceptions.NotFound`: Unable to find collection.
        """
        try:
            return self.collections(title=title, title__iexact=title)[0]
        except IndexError:
            raise NotFound(f'Unable to find collection with title "{title}".') from None

    def collections(self, **kwargs):
        """ Returns a list of collections from this library section.
            See description of :func:`~plexapi.library.LibrarySection.search` for details about filtering / sorting.
        """
        return self.search(libtype='collection', **kwargs)

    def createPlaylist(self, title, items=None, smart=False, limit=None,
                       sort=None, filters=None, m3ufilepath=None, **kwargs):
        """ Alias for :func:`~plexapi.server.PlexServer.createPlaylist` using this
            :class:`~plexapi.library.LibrarySection`.
        """
        return self._server.createPlaylist(
            title, section=self, items=items, smart=smart, limit=limit,
            sort=sort, filters=filters, m3ufilepath=m3ufilepath, **kwargs)

    def playlist(self, title):
        """ Returns the playlist with the specified title.

            Parameters:
                title (str): Title of the item to return.

            Raises:
                :exc:`~plexapi.exceptions.NotFound`: Unable to find playlist.
        """
        try:
            return self.playlists(title=title, title__iexact=title)[0]
        except IndexError:
            raise NotFound(f'Unable to find playlist with title "{title}".') from None

    def playlists(self, sort=None, **kwargs):
        """ Returns a list of playlists from this library section. """
        return self._server.playlists(
            playlistType=self.CONTENT_TYPE, sectionId=self.key, sort=sort, **kwargs)

    @deprecated('use "listFields" instead')
    def filterFields(self, mediaType=None):
        return self.listFields(libtype=mediaType)

    @deprecated('use "listFilterChoices" instead')
    def listChoices(self, category, libtype=None, **kwargs):
        return self.listFilterChoices(field=category, libtype=libtype)

    def getWebURL(self, base=None, tab=None, key=None):
        """ Returns the Plex Web URL for the library.

            Parameters:
                base (str): The base URL before the fragment (``#!``).
                    Default is https://app.plex.tv/desktop.
                tab (str): The library tab (recommended, library, collections, playlists, timeline).
                key (str): A hub key.
        """
        params = {'source': self.key}
        if tab is not None:
            params['pivot'] = tab
        if key is not None:
            params['key'] = key
            params['pageType'] = 'list'
        return self._server._buildWebURL(base=base, **params)


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

    def searchMovies(self, **kwargs):
        """ Search for a movie. See :func:`~plexapi.library.LibrarySection.search` for usage. """
        return self.search(libtype='movie', **kwargs)

    def recentlyAddedMovies(self, maxresults=50):
        """ Returns a list of recently added movies from this library section.

            Parameters:
                maxresults (int): Max number of items to return (default 50).
        """
        return self.recentlyAdded(maxresults=maxresults, libtype='movie')

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

    def searchSeasons(self, **kwargs):
        """ Search for a season. See :func:`~plexapi.library.LibrarySection.search` for usage. """
        return self.search(libtype='season', **kwargs)

    def searchEpisodes(self, **kwargs):
        """ Search for an episode. See :func:`~plexapi.library.LibrarySection.search` for usage. """
        return self.search(libtype='episode', **kwargs)

    def recentlyAddedShows(self, maxresults=50):
        """ Returns a list of recently added shows from this library section.

            Parameters:
                maxresults (int): Max number of items to return (default 50).
        """
        return self.recentlyAdded(maxresults=maxresults, libtype='show')

    def recentlyAddedSeasons(self, maxresults=50):
        """ Returns a list of recently added seasons from this library section.

            Parameters:
                maxresults (int): Max number of items to return (default 50).
        """
        return self.recentlyAdded(maxresults=maxresults, libtype='season')

    def recentlyAddedEpisodes(self, maxresults=50):
        """ Returns a list of recently added episodes from this library section.

            Parameters:
                maxresults (int): Max number of items to return (default 50).
        """
        return self.recentlyAdded(maxresults=maxresults, libtype='episode')

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
    METADATA_TYPE = 'track'
    CONTENT_TYPE = 'audio'

    def albums(self):
        """ Returns a list of :class:`~plexapi.audio.Album` objects in this section. """
        key = f'/library/sections/{self.key}/albums'
        return self.fetchItems(key)

    def stations(self):
        """ Returns a list of :class:`~plexapi.playlist.Playlist` stations in this section. """
        return next((hub.items for hub in self.hubs() if hub.context == 'hub.music.stations'), None)

    def searchArtists(self, **kwargs):
        """ Search for an artist. See :func:`~plexapi.library.LibrarySection.search` for usage. """
        return self.search(libtype='artist', **kwargs)

    def searchAlbums(self, **kwargs):
        """ Search for an album. See :func:`~plexapi.library.LibrarySection.search` for usage. """
        return self.search(libtype='album', **kwargs)

    def searchTracks(self, **kwargs):
        """ Search for a track. See :func:`~plexapi.library.LibrarySection.search` for usage. """
        return self.search(libtype='track', **kwargs)

    def recentlyAddedArtists(self, maxresults=50):
        """ Returns a list of recently added artists from this library section.

            Parameters:
                maxresults (int): Max number of items to return (default 50).
        """
        return self.recentlyAdded(maxresults=maxresults, libtype='artist')

    def recentlyAddedAlbums(self, maxresults=50):
        """ Returns a list of recently added albums from this library section.

            Parameters:
                maxresults (int): Max number of items to return (default 50).
        """
        return self.recentlyAdded(maxresults=maxresults, libtype='album')

    def recentlyAddedTracks(self, maxresults=50):
        """ Returns a list of recently added tracks from this library section.

            Parameters:
                maxresults (int): Max number of items to return (default 50).
        """
        return self.recentlyAdded(maxresults=maxresults, libtype='track')

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
    METADATA_TYPE = 'photo'
    CONTENT_TYPE = 'photo'

    def all(self, libtype=None, **kwargs):
        """ Returns a list of all items from this library section.
            See description of :func:`plexapi.library.LibrarySection.search()` for details about filtering / sorting.
        """
        libtype = libtype or 'photoalbum'
        return self.search(libtype=libtype, **kwargs)

    def collections(self, **kwargs):
        raise NotImplementedError('Collections are not available for a Photo library.')

    def searchAlbums(self, title, **kwargs):
        """ Search for a photo album. See :func:`~plexapi.library.LibrarySection.search` for usage. """
        return self.search(libtype='photoalbum', title=title, **kwargs)

    def searchPhotos(self, title, **kwargs):
        """ Search for a photo. See :func:`~plexapi.library.LibrarySection.search` for usage. """
        return self.search(libtype='photo', title=title, **kwargs)

    def recentlyAddedAlbums(self, maxresults=50):
        """ Returns a list of recently added photo albums from this library section.

            Parameters:
                maxresults (int): Max number of items to return (default 50).
        """
        # Use search() instead of recentlyAdded() because libtype=None
        return self.search(sort='addedAt:desc', maxresults=maxresults)

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


@utils.registerPlexObject
class Hub(PlexObject):
    """ Represents a single Hub (or category) in the PlexServer search.

        Attributes:
            TAG (str): 'Hub'
            context (str): The context of the hub.
            hubKey (str): API URL for these specific hub items.
            hubIdentifier (str): The identifier of the hub.
            items (list): List of items in the hub.
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
        self._section = None  # cache for self.section

    def __len__(self):
        return self.size

    def reload(self):
        """ Reloads the hub to fetch all items in the hub. """
        if self.more and self.key:
            self.items = self.fetchItems(self.key)
            self.more = False
            self.size = len(self.items)

    def section(self):
        """ Returns the :class:`~plexapi.library.LibrarySection` this hub belongs to.
        """
        if self._section is None:
            self._section = self._server.library.sectionByID(self.librarySectionID)
        return self._section


class LibraryMediaTag(PlexObject):
    """ Base class of library media tags.

        Attributes:
            TAG (str): 'Directory'
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

    def items(self, *args, **kwargs):
        """ Return the list of items within this tag. """
        if not self.key:
            raise BadRequest(f'Key is not defined for this tag: {self.tag}')
        return self.fetchItems(self.key)


@utils.registerPlexObject
class Aperture(LibraryMediaTag):
    """ Represents a single Aperture library media tag.

        Attributes:
            TAGTYPE (int): 202
    """
    TAGTYPE = 202


@utils.registerPlexObject
class Art(LibraryMediaTag):
    """ Represents a single Art library media tag.

        Attributes:
            TAGTYPE (int): 313
    """
    TAGTYPE = 313


@utils.registerPlexObject
class Autotag(LibraryMediaTag):
    """ Represents a single Autotag library media tag.

        Attributes:
            TAGTYPE (int): 207
    """
    TAGTYPE = 207


@utils.registerPlexObject
class Banner(LibraryMediaTag):
    """ Represents a single Banner library media tag.

        Attributes:
            TAGTYPE (int): 311
    """
    TAGTYPE = 311


@utils.registerPlexObject
class Chapter(LibraryMediaTag):
    """ Represents a single Chapter library media tag.

        Attributes:
            TAGTYPE (int): 9
    """
    TAGTYPE = 9


@utils.registerPlexObject
class Collection(LibraryMediaTag):
    """ Represents a single Collection library media tag.

        Attributes:
            TAGTYPE (int): 2
    """
    TAGTYPE = 2


@utils.registerPlexObject
class Concert(LibraryMediaTag):
    """ Represents a single Concert library media tag.

        Attributes:
            TAGTYPE (int): 306
    """
    TAGTYPE = 306


@utils.registerPlexObject
class Country(LibraryMediaTag):
    """ Represents a single Country library media tag.

        Attributes:
            TAGTYPE (int): 8
    """
    TAGTYPE = 8


@utils.registerPlexObject
class Device(LibraryMediaTag):
    """ Represents a single Device library media tag.

        Attributes:
            TAGTYPE (int): 206
    """
    TAGTYPE = 206


@utils.registerPlexObject
class Director(LibraryMediaTag):
    """ Represents a single Director library media tag.

        Attributes:
            TAGTYPE (int): 4
    """
    TAGTYPE = 4


@utils.registerPlexObject
class Exposure(LibraryMediaTag):
    """ Represents a single Exposure library media tag.

        Attributes:
            TAGTYPE (int): 203
    """
    TAGTYPE = 203


@utils.registerPlexObject
class Format(LibraryMediaTag):
    """ Represents a single Format library media tag.

        Attributes:
            TAGTYPE (int): 302
    """
    TAGTYPE = 302


@utils.registerPlexObject
class Genre(LibraryMediaTag):
    """ Represents a single Genre library media tag.

        Attributes:
            TAGTYPE (int): 1
    """
    TAGTYPE = 1


@utils.registerPlexObject
class Guid(LibraryMediaTag):
    """ Represents a single Guid library media tag.

        Attributes:
            TAGTYPE (int): 314
    """
    TAGTYPE = 314


@utils.registerPlexObject
class ISO(LibraryMediaTag):
    """ Represents a single ISO library media tag.

        Attributes:
            TAGTYPE (int): 204
    """
    TAGTYPE = 204


@utils.registerPlexObject
class Label(LibraryMediaTag):
    """ Represents a single Label library media tag.

        Attributes:
            TAGTYPE (int): 11
    """
    TAGTYPE = 11


@utils.registerPlexObject
class Lens(LibraryMediaTag):
    """ Represents a single Lens library media tag.

        Attributes:
            TAGTYPE (int): 205
    """
    TAGTYPE = 205


@utils.registerPlexObject
class Make(LibraryMediaTag):
    """ Represents a single Make library media tag.

        Attributes:
            TAGTYPE (int): 200
    """
    TAGTYPE = 200


@utils.registerPlexObject
class Marker(LibraryMediaTag):
    """ Represents a single Marker library media tag.

        Attributes:
            TAGTYPE (int): 12
    """
    TAGTYPE = 12


@utils.registerPlexObject
class MediaProcessingTarget(LibraryMediaTag):
    """ Represents a single MediaProcessingTarget library media tag.

        Attributes:
            TAG (str): 'Tag'
            TAGTYPE (int): 42
    """
    TAG = 'Tag'
    TAGTYPE = 42


@utils.registerPlexObject
class Model(LibraryMediaTag):
    """ Represents a single Model library media tag.

        Attributes:
            TAGTYPE (int): 201
    """
    TAGTYPE = 201


@utils.registerPlexObject
class Mood(LibraryMediaTag):
    """ Represents a single Mood library media tag.

        Attributes:
            TAGTYPE (int): 300
    """
    TAGTYPE = 300


@utils.registerPlexObject
class Network(LibraryMediaTag):
    """ Represents a single Network library media tag.

        Attributes:
            TAGTYPE (int): 319
    """
    TAGTYPE = 319


@utils.registerPlexObject
class Place(LibraryMediaTag):
    """ Represents a single Place library media tag.

        Attributes:
            TAGTYPE (int): 400
    """
    TAGTYPE = 400


@utils.registerPlexObject
class Poster(LibraryMediaTag):
    """ Represents a single Poster library media tag.

        Attributes:
            TAGTYPE (int): 312
    """
    TAGTYPE = 312


@utils.registerPlexObject
class Producer(LibraryMediaTag):
    """ Represents a single Producer library media tag.

        Attributes:
            TAGTYPE (int): 7
    """
    TAGTYPE = 7


@utils.registerPlexObject
class RatingImage(LibraryMediaTag):
    """ Represents a single RatingImage library media tag.

        Attributes:
            TAGTYPE (int): 316
    """
    TAGTYPE = 316


@utils.registerPlexObject
class Review(LibraryMediaTag):
    """ Represents a single Review library media tag.

        Attributes:
            TAGTYPE (int): 10
    """
    TAGTYPE = 10


@utils.registerPlexObject
class Role(LibraryMediaTag):
    """ Represents a single Role library media tag.

        Attributes:
            TAGTYPE (int): 6
    """
    TAGTYPE = 6


@utils.registerPlexObject
class Similar(LibraryMediaTag):
    """ Represents a single Similar library media tag.

        Attributes:
            TAGTYPE (int): 305
    """
    TAGTYPE = 305


@utils.registerPlexObject
class Studio(LibraryMediaTag):
    """ Represents a single Studio library media tag.

        Attributes:
            TAGTYPE (int): 318
    """
    TAGTYPE = 318


@utils.registerPlexObject
class Style(LibraryMediaTag):
    """ Represents a single Style library media tag.

        Attributes:
            TAGTYPE (int): 301
    """
    TAGTYPE = 301


@utils.registerPlexObject
class Tag(LibraryMediaTag):
    """ Represents a single Tag library media tag.

        Attributes:
            TAGTYPE (int): 0
    """
    TAGTYPE = 0


@utils.registerPlexObject
class Theme(LibraryMediaTag):
    """ Represents a single Theme library media tag.

        Attributes:
            TAGTYPE (int): 317
    """
    TAGTYPE = 317


@utils.registerPlexObject
class Writer(LibraryMediaTag):
    """ Represents a single Writer library media tag.

        Attributes:
            TAGTYPE (int): 5
    """
    TAGTYPE = 5


class FilteringType(PlexObject):
    """ Represents a single filtering Type object for a library.

        Attributes:
            TAG (str): 'Type'
            active (bool): True if this filter type is currently active.
            fields (List<:class:`~plexapi.library.FilteringField`>): List of field objects.
            filters (List<:class:`~plexapi.library.FilteringFilter`>): List of filter objects.
            key (str): The API URL path for the libtype filter.
            sorts (List<:class:`~plexapi.library.FilteringSort`>): List of sort objects.
            title (str): The title for the libtype filter.
            type (str): The libtype for the filter.
    """
    TAG = 'Type'

    def __repr__(self):
        _type = self._clean(self.firstAttr('type'))
        return f"<{':'.join([p for p in [self.__class__.__name__, _type] if p])}>"

    def _loadData(self, data):
        self._data = data
        self.active = utils.cast(bool, data.attrib.get('active', '0'))
        self.fields = self.findItems(data, FilteringField)
        self.filters = self.findItems(data, FilteringFilter)
        self.key = data.attrib.get('key')
        self.sorts = self.findItems(data, FilteringSort)
        self.title = data.attrib.get('title')
        self.type = data.attrib.get('type')

        self._librarySectionID = self._parent().key

        # Add additional manual filters, sorts, and fields which are available
        # but not exposed on the Plex server
        self.filters += self._manualFilters()
        self.sorts += self._manualSorts()
        self.fields += self._manualFields()

    def _manualFilters(self):
        """ Manually add additional filters which are available
            but not exposed on the Plex server.
        """
        # Filters: (filter, type, title)
        additionalFilters = [
        ]

        if self.type == 'season':
            additionalFilters.extend([
                ('label', 'string', 'Labels')
            ])
        elif self.type == 'episode':
            additionalFilters.extend([
                ('label', 'string', 'Labels')
            ])
        elif self.type == 'artist':
            additionalFilters.extend([
                ('label', 'string', 'Labels')
            ])
        elif self.type == 'track':
            additionalFilters.extend([
                ('label', 'string', 'Labels')
            ])
        elif self.type == 'collection':
            additionalFilters.extend([
                ('label', 'string', 'Labels')
            ])

        manualFilters = []
        for filterTag, filterType, filterTitle in additionalFilters:
            filterKey = f'/library/sections/{self._librarySectionID}/{filterTag}?type={utils.searchType(self.type)}'
            filterXML = (
                f'<Filter filter="{filterTag}" '
                f'filterType="{filterType}" '
                f'key="{filterKey}" '
                f'title="{filterTitle}" '
                f'type="filter" />'
            )
            manualFilters.append(self._manuallyLoadXML(filterXML, FilteringFilter))

        return manualFilters

    def _manualSorts(self):
        """ Manually add additional sorts which are available
            but not exposed on the Plex server.
        """
        # Sorts: (key, dir, title)
        additionalSorts = [
            ('guid', 'asc', 'Guid'),
            ('id', 'asc', 'Rating Key'),
            ('index', 'asc', f'{self.type.capitalize()} Number'),
            ('summary', 'asc', 'Summary'),
            ('tagline', 'asc', 'Tagline'),
            ('updatedAt', 'asc', 'Date Updated')
        ]

        if self.type == 'season':
            additionalSorts.extend([
                ('titleSort', 'asc', 'Title')
            ])
        elif self.type == 'track':
            # Don't know what this is but it is valid
            additionalSorts.extend([
                ('absoluteIndex', 'asc', 'Absolute Index')
            ])
        elif self.type == 'photo':
            additionalSorts.extend([
                ('viewUpdatedAt', 'desc', 'View Updated At')
            ])
        elif self.type == 'collection':
            additionalSorts.extend([
                ('addedAt', 'asc', 'Date Added')
            ])

        manualSorts = []
        for sortField, sortDir, sortTitle in additionalSorts:
            sortXML = (
                f'<Sort defaultDirection="{sortDir}" '
                f'descKey="{sortField}:desc" '
                f'key="{sortField}" '
                f'title="{sortTitle}" />'
            )
            manualSorts.append(self._manuallyLoadXML(sortXML, FilteringSort))

        return manualSorts

    def _manualFields(self):
        """ Manually add additional fields which are available
            but not exposed on the Plex server.
        """
        # Fields: (key, type, title)
        additionalFields = [
            ('guid', 'guid', 'Guid'),
            ('id', 'integer', 'Rating Key'),
            ('index', 'integer', f'{self.type.capitalize()} Number'),
            ('lastRatedAt', 'date', f'{self.type.capitalize()} Last Rated'),
            ('updatedAt', 'date', 'Date Updated')
        ]

        if self.type == 'movie':
            additionalFields.extend([
                ('audienceRating', 'integer', 'Audience Rating'),
                ('rating', 'integer', 'Critic Rating'),
                ('viewOffset', 'integer', 'View Offset')
            ])
        elif self.type == 'show':
            additionalFields.extend([
                ('audienceRating', 'integer', 'Audience Rating'),
                ('originallyAvailableAt', 'date', 'Show Release Date'),
                ('rating', 'integer', 'Critic Rating'),
                ('unviewedLeafCount', 'integer', 'Episode Unplayed Count')
            ])
        elif self.type == 'season':
            additionalFields.extend([
                ('addedAt', 'date', 'Date Season Added'),
                ('unviewedLeafCount', 'integer', 'Episode Unplayed Count'),
                ('year', 'integer', 'Season Year'),
                ('label', 'tag', 'Label')
            ])
        elif self.type == 'episode':
            additionalFields.extend([
                ('audienceRating', 'integer', 'Audience Rating'),
                ('duration', 'integer', 'Duration'),
                ('rating', 'integer', 'Critic Rating'),
                ('viewOffset', 'integer', 'View Offset'),
                ('label', 'tag', 'Label')
            ])
        elif self.type == 'artist':
            additionalFields.extend([
                ('label', 'tag', 'Label')
            ])
        elif self.type == 'track':
            additionalFields.extend([
                ('duration', 'integer', 'Duration'),
                ('viewOffset', 'integer', 'View Offset'),
                ('label', 'tag', 'Label')
            ])
        elif self.type == 'collection':
            additionalFields.extend([
                ('addedAt', 'date', 'Date Added'),
                ('label', 'tag', 'Label')
            ])

        prefix = '' if self.type == 'movie' else self.type + '.'

        manualFields = []
        for field, fieldType, fieldTitle in additionalFields:
            fieldXML = (
                f'<Field key="{prefix}{field}" '
                f'title="{fieldTitle}" '
                f'type="{fieldType}"/>'
            )
            manualFields.append(self._manuallyLoadXML(fieldXML, FilteringField))

        return manualFields


class FilteringFilter(PlexObject):
    """ Represents a single Filter object for a :class:`~plexapi.library.FilteringType`.

        Attributes:
            TAG (str): 'Filter'
            filter (str): The key for the filter.
            filterType (str): The :class:`~plexapi.library.FilteringFieldType` type (string, boolean, integer, date, etc).
            key (str): The API URL path for the filter.
            title (str): The title of the filter.
            type (str): 'filter'
    """
    TAG = 'Filter'

    def _loadData(self, data):
        self._data = data
        self.filter = data.attrib.get('filter')
        self.filterType = data.attrib.get('filterType')
        self.key = data.attrib.get('key')
        self.title = data.attrib.get('title')
        self.type = data.attrib.get('type')


class FilteringSort(PlexObject):
    """ Represents a single Sort object for a :class:`~plexapi.library.FilteringType`.

        Attributes:
            TAG (str): 'Sort'
            active (bool): True if the sort is currently active.
            activeDirection (str): The currently active sorting direction.
            default (str): The currently active default sorting direction.
            defaultDirection (str): The default sorting direction.
            descKey (str): The URL key for sorting with desc.
            firstCharacterKey (str): API URL path for first character endpoint.
            key (str): The URL key for the sorting.
            title (str): The title of the sorting.
    """
    TAG = 'Sort'

    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        self._data = data
        self.active = utils.cast(bool, data.attrib.get('active', '0'))
        self.activeDirection = data.attrib.get('activeDirection')
        self.default = data.attrib.get('default')
        self.defaultDirection = data.attrib.get('defaultDirection')
        self.descKey = data.attrib.get('descKey')
        self.firstCharacterKey = data.attrib.get('firstCharacterKey')
        self.key = data.attrib.get('key')
        self.title = data.attrib.get('title')


class FilteringField(PlexObject):
    """ Represents a single Field object for a :class:`~plexapi.library.FilteringType`.

        Attributes:
            TAG (str): 'Field'
            key (str): The URL key for the filter field.
            title (str): The title of the filter field.
            type (str): The :class:`~plexapi.library.FilteringFieldType` type (string, boolean, integer, date, etc).
            subType (str): The subtype of the filter (decade, rating, etc).
    """
    TAG = 'Field'

    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        self._data = data
        self.key = data.attrib.get('key')
        self.title = data.attrib.get('title')
        self.type = data.attrib.get('type')
        self.subType = data.attrib.get('subType')


class FilteringFieldType(PlexObject):
    """ Represents a single FieldType for library filtering.

        Attributes:
            TAG (str): 'FieldType'
            type (str): The filtering data type (string, boolean, integer, date, etc).
            operators (List<:class:`~plexapi.library.FilteringOperator`>): List of operator objects.
    """
    TAG = 'FieldType'

    def __repr__(self):
        _type = self._clean(self.firstAttr('type'))
        return f"<{':'.join([p for p in [self.__class__.__name__, _type] if p])}>"

    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        self._data = data
        self.type = data.attrib.get('type')
        self.operators = self.findItems(data, FilteringOperator)


class FilteringOperator(PlexObject):
    """ Represents an single Operator for a :class:`~plexapi.library.FilteringFieldType`.

        Attributes:
            TAG (str): 'Operator'
            key (str): The URL key for the operator.
            title (str): The title of the operator.
    """
    TAG = 'Operator'

    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        self.key = data.attrib.get('key')
        self.title = data.attrib.get('title')


class FilterChoice(PlexObject):
    """ Represents a single FilterChoice object.
        These objects are gathered when using filters while searching for library items and is the
        object returned in the result set of :func:`~plexapi.library.LibrarySection.listFilterChoices`.

        Attributes:
            TAG (str): 'Directory'
            fastKey (str): API URL path to quickly list all items with this filter choice.
                (/library/sections/<section>/all?genre=<key>)
            key (str): The id value of this filter choice.
            thumb (str): Thumbnail URL for the filter choice.
            title (str): The title of the filter choice.
            type (str): The filter type (genre, contentRating, etc).
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


class ManagedHub(PlexObject):
    """ Represents a Managed Hub (recommendation) inside a library.

        Attributes:
            TAG (str): 'Hub'
            deletable (bool): True if the Hub can be deleted (promoted collection).
            homeVisibility (str): Promoted home visibility (none, all, admin, or shared).
            identifier (str): Hub identifier for the managed hub.
            promotedToOwnHome (bool): Promoted to own home.
            promotedToRecommended (bool): Promoted to recommended.
            promotedToSharedHome (bool): Promoted to shared home.
            recommendationsVisibility (str): Promoted recommendation visibility (none or all).
            title (str): Title of managed hub.
    """
    TAG = 'Hub'

    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        self._data = data
        self.deletable = utils.cast(bool, data.attrib.get('deletable', True))
        self.homeVisibility = data.attrib.get('homeVisibility', 'none')
        self.identifier = data.attrib.get('identifier')
        self.promotedToOwnHome = utils.cast(bool, data.attrib.get('promotedToOwnHome', False))
        self.promotedToRecommended = utils.cast(bool, data.attrib.get('promotedToRecommended', False))
        self.promotedToSharedHome = utils.cast(bool, data.attrib.get('promotedToSharedHome', False))
        self.recommendationsVisibility = data.attrib.get('recommendationsVisibility', 'none')
        self.title = data.attrib.get('title')
        self._promoted = True  # flag to indicate if this hub has been promoted on the list of managed recommendations

        parent = self._parent()
        self.librarySectionID = parent.key if isinstance(parent, LibrarySection) else parent.librarySectionID

    def reload(self):
        """ Reload the data for this managed hub. """
        key = f'/hubs/sections/{self.librarySectionID}/manage'
        hub = self.fetchItem(key, self.__class__, identifier=self.identifier)
        self.__dict__.update(hub.__dict__)
        return self

    def move(self, after=None):
        """ Move a managed hub to a new position in the library's Managed Recommendations.

            Parameters:
                after (obj): :class:`~plexapi.library.ManagedHub` object to move the item after in the collection.

            Raises:
                :class:`plexapi.exceptions.BadRequest`: When trying to move a Hub that is not a Managed Recommendation.
        """
        if not self._promoted:
            raise BadRequest('Collection must be a Managed Recommendation to be moved')
        key = f'/hubs/sections/{self.librarySectionID}/manage/{self.identifier}/move'
        if after:
            key = f'{key}?after={after.identifier}'
        self._server.query(key, method=self._server._session.put)

    def remove(self):
        """ Removes a managed hub from the library's Managed Recommendations.

            Raises:
                :class:`plexapi.exceptions.BadRequest`: When trying to remove a Hub that is not a Managed Recommendation
                    or when the Hub cannot be removed.
        """
        if not self._promoted:
            raise BadRequest('Collection must be a Managed Recommendation to be removed')
        if not self.deletable:
            raise BadRequest(f'{self.title} managed hub cannot be removed' % self.title)
        key = f'/hubs/sections/{self.librarySectionID}/manage/{self.identifier}'
        self._server.query(key, method=self._server._session.delete)

    def updateVisibility(self, recommended=None, home=None, shared=None):
        """ Update the managed hub's visibility settings.

            Parameters:
                recommended (bool): True to make visible on your Library Recommended page. False to hide. Default None.
                home (bool): True to make visible on your Home page. False to hide. Default None.
                shared (bool): True to make visible on your Friends' Home page. False to hide. Default None.

            Example:

                .. code-block:: python

                    managedHub.updateVisibility(recommended=True, home=True, shared=False).reload()
                    # or using chained methods
                    managedHub.promoteRecommended().promoteHome().demoteShared().reload()
        """
        params = {
            'promotedToRecommended': int(self.promotedToRecommended),
            'promotedToOwnHome': int(self.promotedToOwnHome),
            'promotedToSharedHome': int(self.promotedToSharedHome),
        }
        if recommended is not None:
            params['promotedToRecommended'] = int(recommended)
        if home is not None:
            params['promotedToOwnHome'] = int(home)
        if shared is not None:
            params['promotedToSharedHome'] = int(shared)

        if not self._promoted:
            params['metadataItemId'] = self.identifier.rsplit('.')[-1]
            key = f'/hubs/sections/{self.librarySectionID}/manage'
            self._server.query(key, method=self._server._session.post, params=params)
        else:
            key = f'/hubs/sections/{self.librarySectionID}/manage/{self.identifier}'
            self._server.query(key, method=self._server._session.put, params=params)
        return self.reload()

    def promoteRecommended(self):
        """ Show the managed hub on your Library Recommended Page. """
        return self.updateVisibility(recommended=True)

    def demoteRecommended(self):
        """ Hide the managed hub on your Library Recommended Page. """
        return self.updateVisibility(recommended=False)

    def promoteHome(self):
        """ Show the managed hub on your Home Page. """
        return self.updateVisibility(home=True)

    def demoteHome(self):
        """ Hide the manged hub on your Home Page. """
        return self.updateVisibility(home=False)

    def promoteShared(self):
        """ Show the managed hub on your Friends' Home Page. """
        return self.updateVisibility(shared=True)

    def demoteShared(self):
        """ Hide the managed hub on your Friends' Home Page. """
        return self.updateVisibility(shared=False)


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
