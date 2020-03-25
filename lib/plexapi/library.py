# -*- coding: utf-8 -*-
from plexapi import X_PLEX_CONTAINER_SIZE, log, utils
from plexapi.base import PlexObject
from plexapi.compat import unquote, urlencode, quote_plus
from plexapi.media import MediaTag
from plexapi.exceptions import BadRequest, NotFound


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
        self._server.query('/library/clean/bundles')

    def emptyTrash(self):
        """ If a library has items in the Library Trash, use this option to empty the Trash. """
        for section in self.sections():
            section.emptyTrash()

    def optimize(self):
        """ The Optimize option cleans up the server database from unused or fragmented data.
            For example, if you have deleted or added an entire library or many items in a
            library, you may like to optimize the database.
        """
        self._server.query('/library/optimize')

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

                * **agent** (str): com.plexapp.agents.none, com.plexapp.agents.imdb, com.plexapp.agents.themoviedb
                * **enableBIFGeneration** (bool): Enable video preview thumbnails. Default value true.
                * **enableCinemaTrailers** (bool): Enable Cinema Trailers. Default value true.
                * **includeInGlobal** (bool): Include in dashboard. Default value true.
                * **scanner** (str): Plex Movie Scanner, Plex Video Files Scanner

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


class LibrarySection(PlexObject):
    """ Base class for a single library section.

        Attributes:
            ALLOWED_FILTERS (tuple): ()
            ALLOWED_SORT (tuple): ()
            BOOLEAN_FILTERS (tuple<str>): ('unwatched', 'duplicate')
            server (:class:`~plexapi.server.PlexServer`): Server this client is connected to.
            initpath (str): Path requested when building this object.
            agent (str): Unknown (com.plexapp.agents.imdb, etc)
            allowSync (bool): True if you allow syncing content from this section.
            art (str): Wallpaper artwork used to respresent this section.
            composite (str): Composit image used to represent this section.
            createdAt (datetime): Datetime this library section was created.
            filters (str): Unknown
            key (str): Key (or ID) of this library section.
            language (str): Language represented in this section (en, xn, etc).
            locations (str): Paths on disk where section content is stored.
            refreshing (str): True if this section is currently being refreshed.
            scanner (str): Internal scanner used to find media (Plex Movie Scanner, Plex Premium Music Scanner, etc.)
            thumb (str): Thumbnail image used to represent this section.
            title (str): Title of this section.
            type (str): Type of content section represents (movie, artist, photo, show).
            updatedAt (datetime): Datetime this library section was last updated.
            uuid (str): Unique id for this section (32258d7c-3e6c-4ac5-98ad-bad7a3b78c63)
    """
    ALLOWED_FILTERS = ()
    ALLOWED_SORT = ()
    BOOLEAN_FILTERS = ('unwatched', 'duplicate')

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

    def delete(self):
        """ Delete a library section. """
        try:
            return self._server.query('/library/sections/%s' % self.key, method=self._server._session.delete)
        except BadRequest:  # pragma: no cover
            msg = 'Failed to delete library %s' % self.key
            msg += 'You may need to allow this permission in your Plex settings.'
            log.error(msg)
            raise

    def edit(self, **kwargs):
        """ Edit a library (Note: agent is required). See :class:`~plexapi.library.Library` for example usage.

            Parameters:
                kwargs (dict): Dict of settings to edit.
        """
        part = '/library/sections/%s?%s' % (self.key, urlencode(kwargs))
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
        key = '/library/sections/%s/all' % self.key
        return self.fetchItem(key, title__iexact=title)

    def all(self, sort=None, **kwargs):
        """ Returns a list of media from this library section.

            Parameters:
                    sort (string): The sort string
        """
        sortStr = ''
        if sort is not None:
            sortStr = '?sort=' + sort

        key = '/library/sections/%s/all%s' % (self.key, sortStr)
        return self.fetchItems(key, **kwargs)

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

    def update(self):
        """ Scan this section for new media. """
        key = '/library/sections/%s/refresh' % self.key
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
            :func:`plexapi.library.LibraySection.search()` to help narrow down the choices
            to only those that matter in your current context.

            Parameters:
                category (str): Category to list choices for (genre, contentRating, etc).
                libtype (int): Library type of item filter.
                **kwargs (dict): Additional kwargs to narrow down the choices.

            Raises:
                :class:`plexapi.exceptions.BadRequest`: Cannot include kwarg equal to specified category.
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

    def search(self, title=None, sort=None, maxresults=999999, libtype=None, **kwargs):
        """ Search the library. If there are many results, they will be fetched from the server
            in batches of X_PLEX_CONTAINER_SIZE amounts. If you're only looking for the first <num>
            results, it would be wise to set the maxresults option to that amount so this functions
            doesn't iterate over all results on the server.

            Parameters:
                title (str): General string query to search for (optional).
                sort (str): column:dir; column can be any of {addedAt, originallyAvailableAt, lastViewedAt,
                      titleSort, rating, mediaHeight, duration}. dir can be asc or desc (optional).
                maxresults (int): Only return the specified number of results (optional).
                libtype (str): Filter results to a spcifiec libtype (movie, show, episode, artist,
                    album, track; optional).
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
                :class:`plexapi.exceptions.BadRequest`: when applying unknown filter
        """
        # cleanup the core arguments
        args = {}
        for category, value in kwargs.items():
            args[category] = self._cleanSearchFilter(category, value, libtype)
        if title is not None:
            args['title'] = title
        if sort is not None:
            args['sort'] = self._cleanSearchSort(sort)
        if libtype is not None:
            args['type'] = utils.searchType(libtype)
        # iterate over the results
        results, subresults = [], '_init'
        args['X-Plex-Container-Start'] = 0
        args['X-Plex-Container-Size'] = min(X_PLEX_CONTAINER_SIZE, maxresults)
        while subresults and maxresults > len(results):
            key = '/library/sections/%s/all%s' % (self.key, utils.joinArgs(args))
            subresults = self.fetchItems(key)
            results += subresults[:maxresults - len(results)]
            args['X-Plex-Container-Start'] += args['X-Plex-Container-Size']
        return results

    def _cleanSearchFilter(self, category, value, libtype=None):
        # check a few things before we begin
        if category.endswith('!'):
            if category[:-1] not in self.ALLOWED_FILTERS:
                raise BadRequest('Unknown filter category: %s' % category[:-1])
        elif category not in self.ALLOWED_FILTERS:
            raise BadRequest('Unknown filter category: %s' % category)
        if category in self.BOOLEAN_FILTERS:
            return '1' if value else '0'
        if not isinstance(value, (list, tuple)):
            value = [value]
        # convert list of values to list of keys or ids
        result = set()
        choices = self.listChoices(category, libtype)
        lookup = {c.title.lower(): unquote(unquote(c.key)) for c in choices}
        allowed = set(c.key for c in choices)
        for item in value:
            item = str((item.id or item.tag) if isinstance(item, MediaTag) else item).lower()
            # find most logical choice(s) to use in url
            if item in allowed: result.add(item); continue
            if item in lookup: result.add(lookup[item]); continue
            matches = [k for t, k in lookup.items() if item in t]
            if matches: map(result.add, matches); continue
            # nothing matched; use raw item value
            log.warning('Filter value not listed, using raw item value: %s' % item)
            result.add(item)
        return ','.join(result)

    def _cleanSearchSort(self, sort):
        sort = '%s:asc' % sort if ':' not in sort else sort
        scol, sdir = sort.lower().split(':')
        lookup = {s.lower(): s for s in self.ALLOWED_SORT}
        if scol not in lookup:
            raise BadRequest('Unknown sort column: %s' % scol)
        if sdir not in ('asc', 'desc'):
            raise BadRequest('Unknown sort dir: %s' % sdir)
        return '%s:%s' % (lookup[scol], sdir)

    def sync(self, policy, mediaSettings, client=None, clientId=None, title=None, sort=None, libtype=None,
             **kwargs):
        """ Add current library section as sync item for specified device.
            See description of :func:`~plexapi.library.LibrarySection.search()` for details about filtering / sorting
            and :func:`plexapi.myplex.MyPlexAccount.sync()` for possible exceptions.

            Parameters:
                policy (:class:`plexapi.sync.Policy`): policy of syncing the media (how many items to sync and process
                                                       watched media or not), generated automatically when method
                                                       called on specific LibrarySection object.
                mediaSettings (:class:`plexapi.sync.MediaSettings`): Transcoding settings used for the media, generated
                                                                     automatically when method called on specific
                                                                     LibrarySection object.
                client (:class:`plexapi.myplex.MyPlexDevice`): sync destination, see
                                                               :func:`plexapi.myplex.MyPlexAccount.sync`.
                clientId (str): sync destination, see :func:`plexapi.myplex.MyPlexAccount.sync`.
                title (str): descriptive title for the new :class:`plexapi.sync.SyncItem`, if empty the value would be
                             generated from metadata of current media.
                sort (str): formatted as `column:dir`; column can be any of {`addedAt`, `originallyAvailableAt`,
                            `lastViewedAt`, `titleSort`, `rating`, `mediaHeight`, `duration`}. dir can be `asc` or
                            `desc`.
                libtype (str): Filter results to a specific libtype (`movie`, `show`, `episode`, `artist`, `album`,
                               `track`).

            Returns:
                :class:`plexapi.sync.SyncItem`: an instance of created syncItem.

            Raises:
                :class:`plexapi.exceptions.BadRequest`: when the library is not allowed to sync

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


class MovieSection(LibrarySection):
    """ Represents a :class:`~plexapi.library.LibrarySection` section containing movies.

        Attributes:
            ALLOWED_FILTERS (list<str>): List of allowed search filters. ('unwatched',
                'duplicate', 'year', 'decade', 'genre', 'contentRating', 'collection',
                'director', 'actor', 'country', 'studio', 'resolution', 'guid', 'label')
            ALLOWED_SORT (list<str>): List of allowed sorting keys. ('addedAt',
                'originallyAvailableAt', 'lastViewedAt', 'titleSort', 'rating',
                'mediaHeight', 'duration')
            TAG (str): 'Directory'
            TYPE (str): 'movie'
    """
    ALLOWED_FILTERS = ('unwatched', 'duplicate', 'year', 'decade', 'genre', 'contentRating',
                       'collection', 'director', 'actor', 'country', 'studio', 'resolution',
                       'guid', 'label', 'writer', 'producer', 'subtitleLanguage', 'audioLanguage',
                       'lastViewedAt', 'viewCount', 'addedAt')
    ALLOWED_SORT = ('addedAt', 'originallyAvailableAt', 'lastViewedAt', 'titleSort', 'rating',
                    'mediaHeight', 'duration')
    TAG = 'Directory'
    TYPE = 'movie'
    METADATA_TYPE = 'movie'
    CONTENT_TYPE = 'video'

    def collection(self, **kwargs):
        """ Returns a list of collections from this library section. """
        return self.search(libtype='collection', **kwargs)

    def sync(self, videoQuality, limit=None, unwatched=False, **kwargs):
        """ Add current Movie library section as sync item for specified device.
            See description of :func:`plexapi.library.LibrarySection.search()` for details about filtering / sorting and
            :func:`plexapi.library.LibrarySection.sync()` for details on syncing libraries and possible exceptions.

            Parameters:
                videoQuality (int): idx of quality of the video, one of VIDEO_QUALITY_* values defined in
                                    :mod:`plexapi.sync` module.
                limit (int): maximum count of movies to sync, unlimited if `None`.
                unwatched (bool): if `True` watched videos wouldn't be synced.

            Returns:
                :class:`plexapi.sync.SyncItem`: an instance of created syncItem.

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
            ALLOWED_FILTERS (list<str>): List of allowed search filters. ('unwatched',
                'year', 'genre', 'contentRating', 'network', 'collection', 'guid', 'label')
            ALLOWED_SORT (list<str>): List of allowed sorting keys. ('addedAt', 'lastViewedAt',
                'originallyAvailableAt', 'titleSort', 'rating', 'unwatched')
            TAG (str): 'Directory'
            TYPE (str): 'show'
    """
    ALLOWED_FILTERS = ('unwatched', 'year', 'genre', 'contentRating', 'network', 'collection',
                       'guid', 'duplicate', 'label', 'show.title', 'show.year', 'show.userRating',
                       'show.viewCount', 'show.lastViewedAt', 'show.actor', 'show.addedAt', 'episode.title',
                       'episode.originallyAvailableAt', 'episode.resolution', 'episode.subtitleLanguage',
                       'episode.unwatched', 'episode.addedAt', 'episode.userRating', 'episode.viewCount',
                       'episode.lastViewedAt')
    ALLOWED_SORT = ('addedAt', 'lastViewedAt', 'originallyAvailableAt', 'titleSort',
                    'rating', 'unwatched')
    TAG = 'Directory'
    TYPE = 'show'
    METADATA_TYPE = 'episode'
    CONTENT_TYPE = 'video'

    def searchShows(self, **kwargs):
        """ Search for a show. See :func:`~plexapi.library.LibrarySection.search()` for usage. """
        return self.search(libtype='show', **kwargs)

    def searchEpisodes(self, **kwargs):
        """ Search for an episode. See :func:`~plexapi.library.LibrarySection.search()` for usage. """
        return self.search(libtype='episode', **kwargs)

    def recentlyAdded(self, libtype='episode', maxresults=50):
        """ Returns a list of recently added episodes from this library section.

            Parameters:
                maxresults (int): Max number of items to return (default 50).
        """
        return self.search(sort='addedAt:desc', libtype=libtype, maxresults=maxresults)

    def collection(self, **kwargs):
        """ Returns a list of collections from this library section. """
        return self.search(libtype='collection', **kwargs)

    def sync(self, videoQuality, limit=None, unwatched=False, **kwargs):
        """ Add current Show library section as sync item for specified device.
            See description of :func:`plexapi.library.LibrarySection.search()` for details about filtering / sorting and
            :func:`plexapi.library.LibrarySection.sync()` for details on syncing libraries and possible exceptions.

            Parameters:
                videoQuality (int): idx of quality of the video, one of VIDEO_QUALITY_* values defined in
                                    :mod:`plexapi.sync` module.
                limit (int): maximum count of episodes to sync, unlimited if `None`.
                unwatched (bool): if `True` watched videos wouldn't be synced.

            Returns:
                :class:`plexapi.sync.SyncItem`: an instance of created syncItem.

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
            ALLOWED_FILTERS (list<str>): List of allowed search filters. ('genre',
                'country', 'collection')
            ALLOWED_SORT (list<str>): List of allowed sorting keys. ('addedAt',
                'lastViewedAt', 'viewCount', 'titleSort')
            TAG (str): 'Directory'
            TYPE (str): 'artist'
    """
    ALLOWED_FILTERS = ('genre', 'country', 'collection', 'mood', 'year', 'track.userRating', 'artist.title',
                       'artist.userRating', 'artist.genre', 'artist.country', 'artist.collection', 'artist.addedAt',
                       'album.title', 'album.userRating', 'album.genre', 'album.decade', 'album.collection',
                       'album.viewCount', 'album.lastViewedAt', 'album.studio', 'album.addedAt', 'track.title',
                       'track.userRating', 'track.viewCount', 'track.lastViewedAt', 'track.skipCount',
                       'track.lastSkippedAt')
    ALLOWED_SORT = ('addedAt', 'lastViewedAt', 'viewCount', 'titleSort', 'userRating')
    TAG = 'Directory'
    TYPE = 'artist'

    CONTENT_TYPE = 'audio'
    METADATA_TYPE = 'track'

    def albums(self):
        """ Returns a list of :class:`~plexapi.audio.Album` objects in this section. """
        key = '/library/sections/%s/albums' % self.key
        return self.fetchItems(key)

    def searchArtists(self, **kwargs):
        """ Search for an artist. See :func:`~plexapi.library.LibrarySection.search()` for usage. """
        return self.search(libtype='artist', **kwargs)

    def searchAlbums(self, **kwargs):
        """ Search for an album. See :func:`~plexapi.library.LibrarySection.search()` for usage. """
        return self.search(libtype='album', **kwargs)

    def searchTracks(self, **kwargs):
        """ Search for a track. See :func:`~plexapi.library.LibrarySection.search()` for usage. """
        return self.search(libtype='track', **kwargs)

    def collection(self, **kwargs):
        """ Returns a list of collections from this library section. """
        return self.search(libtype='collection', **kwargs)

    def sync(self, bitrate, limit=None, **kwargs):
        """ Add current Music library section as sync item for specified device.
            See description of :func:`plexapi.library.LibrarySection.search()` for details about filtering / sorting and
            :func:`plexapi.library.LibrarySection.sync()` for details on syncing libraries and possible exceptions.

            Parameters:
                bitrate (int): maximum bitrate for synchronized music, better use one of MUSIC_BITRATE_* values from the
                               module :mod:`plexapi.sync`.
                limit (int): maximum count of tracks to sync, unlimited if `None`.

            Returns:
                :class:`plexapi.sync.SyncItem`: an instance of created syncItem.

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
            ALLOWED_FILTERS (list<str>): List of allowed search filters. ('all', 'iso',
                'make', 'lens', 'aperture', 'exposure', 'device', 'resolution')
            ALLOWED_SORT (list<str>): List of allowed sorting keys. ('addedAt')
            TAG (str): 'Directory'
            TYPE (str): 'photo'
    """
    ALLOWED_FILTERS = ('all', 'iso', 'make', 'lens', 'aperture', 'exposure', 'device', 'resolution', 'place',
                       'originallyAvailableAt', 'addedAt', 'title', 'userRating')
    ALLOWED_SORT = ('addedAt',)
    TAG = 'Directory'
    TYPE = 'photo'
    CONTENT_TYPE = 'photo'
    METADATA_TYPE = 'photo'

    def searchAlbums(self, title, **kwargs):
        """ Search for an album. See :func:`~plexapi.library.LibrarySection.search()` for usage. """
        return self.search(libtype='photoalbum', title=title, **kwargs)

    def searchPhotos(self, title, **kwargs):
        """ Search for a photo. See :func:`~plexapi.library.LibrarySection.search()` for usage. """
        return self.search(libtype='photo', title=title, **kwargs)

    def sync(self, resolution, limit=None, **kwargs):
        """ Add current Music library section as sync item for specified device.
            See description of :func:`plexapi.library.LibrarySection.search()` for details about filtering / sorting and
            :func:`plexapi.library.LibrarySection.sync()` for details on syncing libraries and possible exceptions.

            Parameters:
                resolution (str): maximum allowed resolution for synchronized photos, see PHOTO_QUALITY_* values in the
                                  module :mod:`plexapi.sync`.
                limit (int): maximum count of tracks to sync, unlimited if `None`.

            Returns:
                :class:`plexapi.sync.SyncItem`: an instance of created syncItem.

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
        :func:`~plexapi.library.LibrarySection.listChoices()`.

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
class Hub(PlexObject):
    """ Represents a single Hub (or category) in the PlexServer search.

        Attributes:
            TAG (str): 'Hub'
            hubIdentifier (str): Unknown.
            size (int): Number of items found.
            title (str): Title of this Hub.
            type (str): Type of items in the Hub.
            items (str): List of items in the Hub.
    """
    TAG = 'Hub'

    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        self._data = data
        self.hubIdentifier = data.attrib.get('hubIdentifier')
        self.size = utils.cast(int, data.attrib.get('size'))
        self.title = data.attrib.get('title')
        self.type = data.attrib.get('type')
        self.items = self.findItems(data)

    def __len__(self):
        return self.size


@utils.registerPlexObject
class Collections(PlexObject):

    TAG = 'Directory'
    TYPE = 'collection'

    def _loadData(self, data):
        self.ratingKey = utils.cast(int, data.attrib.get('ratingKey'))
        self.key = data.attrib.get('key')
        self.type = data.attrib.get('type')
        self.title = data.attrib.get('title')
        self.subtype = data.attrib.get('subtype')
        self.summary = data.attrib.get('summary')
        self.index = utils.cast(int, data.attrib.get('index'))
        self.thumb = data.attrib.get('thumb')
        self.addedAt = utils.toDatetime(data.attrib.get('addedAt'))
        self.updatedAt = utils.toDatetime(data.attrib.get('updatedAt'))
        self.childCount = utils.cast(int, data.attrib.get('childCount'))
        self.minYear = utils.cast(int, data.attrib.get('minYear'))
        self.maxYear = utils.cast(int, data.attrib.get('maxYear'))
        self.collectionMode = data.attrib.get('collectionMode')
        self.collectionSort = data.attrib.get('collectionSort')

    @property
    def children(self):
        return self.fetchItems(self.key)

    def __len__(self):
        return self.childCount

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
        mode_dict = {'default': '-2',
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

    # def edit(self, **kwargs):
    #    TODO
