# -*- coding: utf-8 -*-
from datetime import datetime

from urllib.parse import parse_qsl, quote_plus, unquote, urlencode, urlsplit

from plexapi import media, settings, utils
from plexapi.exceptions import BadRequest, NotFound
from plexapi.utils import deprecated


class AdvancedSettingsMixin(object):
    """ Mixin for Plex objects that can have advanced settings. """

    def preferences(self):
        """ Returns a list of :class:`~plexapi.settings.Preferences` objects. """
        data = self._server.query(self._details_key)
        return self.findItems(data, settings.Preferences, rtag='Preferences')

    def preference(self, pref):
        """ Returns a :class:`~plexapi.settings.Preferences` object for the specified pref.

            Parameters:
                pref (str): The id of the preference to return.
        """
        prefs = self.preferences()
        try:
            return next(p for p in prefs if p.id == pref)
        except StopIteration:
            availablePrefs = [p.id for p in prefs]
            raise NotFound('Unknown preference "%s" for %s. '
                           'Available preferences: %s'
                           % (pref, self.TYPE, availablePrefs)) from None

    def editAdvanced(self, **kwargs):
        """ Edit a Plex object's advanced settings. """
        data = {}
        key = '%s/prefs?' % self.key
        preferences = {pref.id: pref for pref in self.preferences() if pref.enumValues}
        for settingID, value in kwargs.items():
            try:
                pref = preferences[settingID]
            except KeyError:
                raise NotFound('%s not found in %s' % (value, list(preferences.keys())))
            
            enumValues = pref.enumValues
            if enumValues.get(value, enumValues.get(str(value))):
                data[settingID] = value
            else:
                raise NotFound('%s not found in %s' % (value, list(enumValues)))
        url = key + urlencode(data)
        self._server.query(url, method=self._server._session.put)

    def defaultAdvanced(self):
        """ Edit all of a Plex object's advanced settings to default. """
        data = {}
        key = '%s/prefs?' % self.key
        for preference in self.preferences():
            data[preference.id] = preference.default
        url = key + urlencode(data)
        self._server.query(url, method=self._server._session.put)


class SmartFilterMixin(object):
    """ Mixing for Plex objects that can have smart filters. """

    def _parseFilters(self, content):
        """ Parse the content string and returns the filter dict. """
        content = urlsplit(unquote(content))
        filters = {}
        filterOp = 'and'
        filterGroups = [[]]
        
        for key, value in parse_qsl(content.query):
            # Move = sign to key when operator is ==
            if value.startswith('='):
                key += '='
                value = value[1:]

            if key == 'includeGuids':
                filters['includeGuids'] = int(value)
            elif key == 'type':
                filters['libtype'] = utils.reverseSearchType(value)
            elif key == 'sort':
                filters['sort'] = value.split(',')
            elif key == 'limit':
                filters['limit'] = int(value)
            elif key == 'push':
                filterGroups[-1].append([])
                filterGroups.append(filterGroups[-1][-1])
            elif key == 'and':
                filterOp = 'and'
            elif key == 'or':
                filterOp = 'or'
            elif key == 'pop':
                filterGroups[-1].insert(0, filterOp)
                filterGroups.pop()
            else:
                filterGroups[-1].append({key: value})
        
        if filterGroups:
            filters['filters'] = self._formatFilterGroups(filterGroups.pop())
        return filters
    
    def _formatFilterGroups(self, groups):
        """ Formats the filter groups into the advanced search rules. """
        if len(groups) == 1 and isinstance(groups[0], list):
            groups = groups.pop()

        filterOp = 'and'
        rules = []

        for g in groups:
            if isinstance(g, list):
                rules.append(self._formatFilterGroups(g))
            elif isinstance(g, dict):
                rules.append(g)
            elif g in {'and', 'or'}:
                filterOp = g

        return {filterOp: rules}


class SplitMergeMixin(object):
    """ Mixin for Plex objects that can be split and merged. """

    def split(self):
        """ Split duplicated Plex object into separate objects. """
        key = '/library/metadata/%s/split' % self.ratingKey
        return self._server.query(key, method=self._server._session.put)

    def merge(self, ratingKeys):
        """ Merge other Plex objects into the current object.
        
            Parameters:
                ratingKeys (list): A list of rating keys to merge.
        """
        if not isinstance(ratingKeys, list):
            ratingKeys = str(ratingKeys).split(',')

        key = '%s/merge?ids=%s' % (self.key, ','.join([str(r) for r in ratingKeys]))
        return self._server.query(key, method=self._server._session.put)


class UnmatchMatchMixin(object):
    """ Mixin for Plex objects that can be unmatched and matched. """

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


class ExtrasMixin(object):
    """ Mixin for Plex objects that can have extras. """

    def extras(self):
        """ Returns a list of :class:`~plexapi.video.Extra` objects. """
        from plexapi.video import Extra
        data = self._server.query(self._details_key)
        return self.findItems(data, Extra, rtag='Extras')


class HubsMixin(object):
    """ Mixin for Plex objects that can have related hubs. """

    def hubs(self):
        """ Returns a list of :class:`~plexapi.library.Hub` objects. """
        from plexapi.library import Hub
        data = self._server.query(self._details_key)
        return self.findItems(data, Hub, rtag='Related')


class RatingMixin(object):
    """ Mixin for Plex objects that can have user star ratings. """

    def rate(self, rating=None):
        """ Rate the Plex object. Note: Plex ratings are displayed out of 5 stars (e.g. rating 7.0 = 3.5 stars).

            Parameters:
                rating (float, optional): Rating from 0 to 10. Exclude to reset the rating.

            Raises:
                :exc:`~plexapi.exceptions.BadRequest`: If the rating is invalid.
        """
        if rating is None:
            rating = -1
        elif not isinstance(rating, (int, float)) or rating < 0 or rating > 10:
            raise BadRequest('Rating must be between 0 to 10.')
        key = '/:/rate?key=%s&identifier=com.plexapp.plugins.library&rating=%s' % (self.ratingKey, rating)
        self._server.query(key, method=self._server._session.put)


class ArtUrlMixin(object):
    """ Mixin for Plex objects that can have a background artwork url. """
    
    @property
    def artUrl(self):
        """ Return the art url for the Plex object. """
        art = self.firstAttr('art', 'grandparentArt')
        return self._server.url(art, includeToken=True) if art else None


class ArtMixin(ArtUrlMixin):
    """ Mixin for Plex objects that can have background artwork. """

    def arts(self):
        """ Returns list of available :class:`~plexapi.media.Art` objects. """
        return self.fetchItems('/library/metadata/%s/arts' % self.ratingKey, cls=media.Art)

    def uploadArt(self, url=None, filepath=None):
        """ Upload a background artwork from a url or filepath.
        
            Parameters:
                url (str): The full URL to the image to upload.
                filepath (str): The full file path the the image to upload.
        """
        if url:
            key = '/library/metadata/%s/arts?url=%s' % (self.ratingKey, quote_plus(url))
            self._server.query(key, method=self._server._session.post)
        elif filepath:
            key = '/library/metadata/%s/arts?' % self.ratingKey
            data = open(filepath, 'rb').read()
            self._server.query(key, method=self._server._session.post, data=data)

    def setArt(self, art):
        """ Set the background artwork for a Plex object.
        
            Parameters:
                art (:class:`~plexapi.media.Art`): The art object to select.
        """
        art.select()

    def lockArt(self):
        """ Lock the background artwork for a Plex object. """
        return self._edit(**{'art.locked': 1})

    def unlockArt(self):
        """ Unlock the background artwork for a Plex object. """
        return self._edit(**{'art.locked': 0})


class BannerUrlMixin(object):
    """ Mixin for Plex objects that can have a banner url. """

    @property
    def bannerUrl(self):
        """ Return the banner url for the Plex object. """
        banner = self.firstAttr('banner')
        return self._server.url(banner, includeToken=True) if banner else None


class BannerMixin(BannerUrlMixin):
    """ Mixin for Plex objects that can have banners. """

    def banners(self):
        """ Returns list of available :class:`~plexapi.media.Banner` objects. """
        return self.fetchItems('/library/metadata/%s/banners' % self.ratingKey, cls=media.Banner)

    def uploadBanner(self, url=None, filepath=None):
        """ Upload a banner from a url or filepath.
        
            Parameters:
                url (str): The full URL to the image to upload.
                filepath (str): The full file path the the image to upload.
        """
        if url:
            key = '/library/metadata/%s/banners?url=%s' % (self.ratingKey, quote_plus(url))
            self._server.query(key, method=self._server._session.post)
        elif filepath:
            key = '/library/metadata/%s/banners?' % self.ratingKey
            data = open(filepath, 'rb').read()
            self._server.query(key, method=self._server._session.post, data=data)

    def setBanner(self, banner):
        """ Set the banner for a Plex object.
        
            Parameters:
                banner (:class:`~plexapi.media.Banner`): The banner object to select.
        """
        banner.select()

    def lockBanner(self):
        """ Lock the banner for a Plex object. """
        return self._edit(**{'banner.locked': 1})

    def unlockBanner(self):
        """ Unlock the banner for a Plex object. """
        return self._edit(**{'banner.locked': 0})


class PosterUrlMixin(object):
    """ Mixin for Plex objects that can have a poster url. """

    @property
    def thumbUrl(self):
        """ Return the thumb url for the Plex object. """
        thumb = self.firstAttr('thumb', 'parentThumb', 'grandparentThumb')
        return self._server.url(thumb, includeToken=True) if thumb else None

    @property
    def posterUrl(self):
        """ Alias to self.thumbUrl. """
        return self.thumbUrl


class PosterMixin(PosterUrlMixin):
    """ Mixin for Plex objects that can have posters. """

    def posters(self):
        """ Returns list of available :class:`~plexapi.media.Poster` objects. """
        return self.fetchItems('/library/metadata/%s/posters' % self.ratingKey, cls=media.Poster)

    def uploadPoster(self, url=None, filepath=None):
        """ Upload a poster from a url or filepath.

            Parameters:
                url (str): The full URL to the image to upload.
                filepath (str): The full file path the the image to upload.
        """
        if url:
            key = '/library/metadata/%s/posters?url=%s' % (self.ratingKey, quote_plus(url))
            self._server.query(key, method=self._server._session.post)
        elif filepath:
            key = '/library/metadata/%s/posters?' % self.ratingKey
            data = open(filepath, 'rb').read()
            self._server.query(key, method=self._server._session.post, data=data)

    def setPoster(self, poster):
        """ Set the poster for a Plex object.
        
            Parameters:
                poster (:class:`~plexapi.media.Poster`): The poster object to select.
        """
        poster.select()

    def lockPoster(self):
        """ Lock the poster for a Plex object. """
        return self._edit(**{'thumb.locked': 1})

    def unlockPoster(self):
        """ Unlock the poster for a Plex object. """
        return self._edit(**{'thumb.locked': 0})


class ThemeUrlMixin(object):
    """ Mixin for Plex objects that can have a theme url. """

    @property
    def themeUrl(self):
        """ Return the theme url for the Plex object. """
        theme = self.firstAttr('theme', 'parentTheme', 'grandparentTheme')
        return self._server.url(theme, includeToken=True) if theme else None


class ThemeMixin(ThemeUrlMixin):
    """ Mixin for Plex objects that can have themes. """

    def themes(self):
        """ Returns list of available :class:`~plexapi.media.Theme` objects. """
        return self.fetchItems('/library/metadata/%s/themes' % self.ratingKey, cls=media.Theme)

    def uploadTheme(self, url=None, filepath=None):
        """ Upload a theme from url or filepath.

            Warning: Themes cannot be deleted using PlexAPI!

            Parameters:
                url (str): The full URL to the theme to upload.
                filepath (str): The full file path to the theme to upload.
        """
        if url:
            key = '/library/metadata/%s/themes?url=%s' % (self.ratingKey, quote_plus(url))
            self._server.query(key, method=self._server._session.post)
        elif filepath:
            key = '/library/metadata/%s/themes?' % self.ratingKey
            data = open(filepath, 'rb').read()
            self._server.query(key, method=self._server._session.post, data=data)

    def setTheme(self, theme):
        raise NotImplementedError(
            'Themes cannot be set through the API. '
            'Re-upload the theme using "uploadTheme" to set it.'
        )

    def lockTheme(self):
        """ Lock the theme for a Plex object. """
        self._edit(**{'theme.locked': 1})

    def unlockTheme(self):
        """ Unlock the theme for a Plex object. """
        self._edit(**{'theme.locked': 0})


class EditFieldMixin(object):
    """ Mixin for editing Plex object fields. """
    
    def editField(self, field, value, locked=True, **kwargs):
        """ Edit the field of a Plex object. All field editing methods can be chained together.
            Also see :func:`~plexapi.base.PlexPartialObject.batchEdits` for batch editing fields.
        
            Parameters:
                field (str): The name of the field to edit.
                value (str): The value to edit the field to.
                locked (bool): True (default) to lock the field, False to unlock the field.

            Example:

                .. code-block:: python

                    # Chaining multiple field edits with reloading
                    Movie.editTitle('A New Title').editSummary('A new summary').editTagline('A new tagline').reload()

        """
        edits = {
            '%s.value' % field: value or '',
            '%s.locked' % field: 1 if locked else 0
        }
        edits.update(kwargs)
        return self._edit(**edits)


class ContentRatingMixin(EditFieldMixin):
    """ Mixin for Plex objects that can have a content rating. """

    def editContentRating(self, contentRating, locked=True):
        """ Edit the content rating.

            Parameters:
                contentRating (str): The new value.
                locked (bool): True (default) to lock the field, False to unlock the field.
        """
        return self.editField('contentRating', contentRating, locked=locked)


class OriginallyAvailableMixin(EditFieldMixin):
    """ Mixin for Plex objects that can have an originally available date. """

    def editOriginallyAvailable(self, originallyAvailable, locked=True):
        """ Edit the originally available date.

            Parameters:
                originallyAvailable (str or datetime): The new value (YYYY-MM-DD) or datetime object.
                locked (bool): True (default) to lock the field, False to unlock the field.
        """
        if isinstance(originallyAvailable, datetime):
            originallyAvailable = originallyAvailable.strftime('%Y-%m-%d')
        return self.editField('originallyAvailableAt', originallyAvailable, locked=locked)


class OriginalTitleMixin(EditFieldMixin):
    """ Mixin for Plex objects that can have an original title. """

    def editOriginalTitle(self, originalTitle, locked=True):
        """ Edit the original title.

            Parameters:
                originalTitle (str): The new value.
                locked (bool): True (default) to lock the field, False to unlock the field.
        """
        return self.editField('originalTitle', originalTitle, locked=locked)


class SortTitleMixin(EditFieldMixin):
    """ Mixin for Plex objects that can have a sort title. """

    def editSortTitle(self, sortTitle, locked=True):
        """ Edit the sort title.

            Parameters:
                sortTitle (str): The new value.
                locked (bool): True (default) to lock the field, False to unlock the field.
        """
        return self.editField('titleSort', sortTitle, locked=locked)


class StudioMixin(EditFieldMixin):
    """ Mixin for Plex objects that can have a studio. """

    def editStudio(self, studio, locked=True):
        """ Edit the studio.

            Parameters:
                studio (str): The new value.
                locked (bool): True (default) to lock the field, False to unlock the field.
        """
        return self.editField('studio', studio, locked=locked)


class SummaryMixin(EditFieldMixin):
    """ Mixin for Plex objects that can have a summary. """

    def editSummary(self, summary, locked=True):
        """ Edit the summary.

            Parameters:
                summary (str): The new value.
                locked (bool): True (default) to lock the field, False to unlock the field.
        """
        return self.editField('summary', summary, locked=locked)


class TaglineMixin(EditFieldMixin):
    """ Mixin for Plex objects that can have a tagline. """

    def editTagline(self, tagline, locked=True):
        """ Edit the tagline.

            Parameters:
                tagline (str): The new value.
                locked (bool): True (default) to lock the field, False to unlock the field.
        """
        return self.editField('tagline', tagline, locked=locked)


class TitleMixin(EditFieldMixin):
    """ Mixin for Plex objects that can have a title. """

    def editTitle(self, title, locked=True):
        """ Edit the title.

            Parameters:
                title (str): The new value.
                locked (bool): True (default) to lock the field, False to unlock the field.
        """
        kwargs = {}
        if self.TYPE == 'album':
            # Editing album title also requires the artist ratingKey
            kwargs['artist.id.value'] = self.parentRatingKey
        return self.editField('title', title, locked=locked, **kwargs)


class TrackArtistMixin(EditFieldMixin):
    """ Mixin for Plex objects that can have a track artist. """

    def editTrackArtist(self, trackArtist, locked=True):
        """ Edit the track artist.

            Parameters:
                trackArtist (str): The new value.
                locked (bool): True (default) to lock the field, False to unlock the field.
        """
        return self.editField('originalTitle', trackArtist, locked=locked)


class TrackNumberMixin(EditFieldMixin):
    """ Mixin for Plex objects that can have a track number. """

    def editTrackNumber(self, trackNumber, locked=True):
        """ Edit the track number.

            Parameters:
                trackNumber (int): The new value.
                locked (bool): True (default) to lock the field, False to unlock the field.
        """
        return self.editField('index', trackNumber, locked=locked)


class TrackDiscNumberMixin(EditFieldMixin):
    """ Mixin for Plex objects that can have a track disc number. """

    def editDiscNumber(self, discNumber, locked=True):
        """ Edit the track disc number.

            Parameters:
                discNumber (int): The new value.
                locked (bool): True (default) to lock the field, False to unlock the field.
        """
        return self.editField('parentIndex', discNumber, locked=locked)


class PhotoCapturedTimeMixin(EditFieldMixin):
    """ Mixin for Plex objects that can have a captured time. """

    def editCapturedTime(self, capturedTime, locked=True):
        """ Edit the photo captured time.

            Parameters:
                capturedTime (str or datetime): The new value (YYYY-MM-DD hh:mm:ss) or datetime object.
                locked (bool): True (default) to lock the field, False to unlock the field.
        """
        if isinstance(capturedTime, datetime):
            capturedTime = capturedTime.strftime('%Y-%m-%d %H:%M:%S')
        return self.editField('originallyAvailableAt', capturedTime, locked=locked)


class EditTagsMixin(object):
    """ Mixin for editing Plex object tags. """

    @deprecated('use "editTags" instead')
    def _edit_tags(self, tag, items, locked=True, remove=False):
        return self.editTags(tag, items, locked, remove)

    def editTags(self, tag, items, locked=True, remove=False, **kwargs):
        """ Edit the tags of a Plex object. All tag editing methods can be chained together.
            Also see :func:`~plexapi.base.PlexPartialObject.batchEdits` for batch editing tags.

            Parameters:
                tag (str): Name of the tag to edit.
                items (List<str>): List of tags to add or remove.
                locked (bool): True (default) to lock the tags, False to unlock the tags.
                remove (bool): True to remove the tags in items.

            Example:

                .. code-block:: python

                    # Chaining multiple tag edits with reloading
                    Show.addCollection('New Collection').removeGenre('Action').addLabel('Favorite').reload()

        """
        if not isinstance(items, list):
            items = [items]

        value = getattr(self, self._tagPlural(tag))
        existing_tags = [t.tag for t in value if t and remove is False]
        edits = self._tagHelper(self._tagSingular(tag), existing_tags + items, locked, remove)
        edits.update(kwargs)
        return self._edit(**edits)

    @staticmethod
    def _tagSingular(tag):
        """ Return the singular name of a tag. """
        if tag == 'countries':
            return 'country'
        elif tag == 'similar':
            return 'similar'
        elif tag[-1] == 's':
            return tag[:-1]
        return tag

    @staticmethod
    def _tagPlural(tag):
        """ Return the plural name of a tag. """
        if tag == 'country':
            return 'countries'
        elif tag == 'similar':
            return 'similar'
        elif tag[-1] != 's':
            return tag + 's'
        return tag

    @staticmethod
    def _tagHelper(tag, items, locked=True, remove=False):
        """ Return a dict of the query parameters for editing a tag. """
        if not isinstance(items, list):
            items = [items]

        data = {
            '%s.locked' % tag: 1 if locked else 0
        }

        if remove:
            tagname = '%s[].tag.tag-' % tag
            data[tagname] = ','.join(items)
        else:
            for i, item in enumerate(items):
                tagname = '%s[%s].tag.tag' % (tag, i)
                data[tagname] = item

        return data


class CollectionMixin(EditTagsMixin):
    """ Mixin for Plex objects that can have collections. """

    def addCollection(self, collections, locked=True):
        """ Add a collection tag(s).

            Parameters:
                collections (list): List of strings.
                locked (bool): True (default) to lock the field, False to unlock the field.
        """
        return self.editTags('collection', collections, locked=locked)

    def removeCollection(self, collections, locked=True):
        """ Remove a collection tag(s).

            Parameters:
                collections (list): List of strings.
                locked (bool): True (default) to lock the field, False to unlock the field.
        """
        return self.editTags('collection', collections, locked=locked, remove=True)


class CountryMixin(EditTagsMixin):
    """ Mixin for Plex objects that can have countries. """

    def addCountry(self, countries, locked=True):
        """ Add a country tag(s).

            Parameters:
                countries (list): List of strings.
                locked (bool): True (default) to lock the field, False to unlock the field.
        """
        return self.editTags('country', countries, locked=locked)

    def removeCountry(self, countries, locked=True):
        """ Remove a country tag(s).

            Parameters:
                countries (list): List of strings.
                locked (bool): True (default) to lock the field, False to unlock the field.
        """
        return self.editTags('country', countries, locked=locked, remove=True)


class DirectorMixin(EditTagsMixin):
    """ Mixin for Plex objects that can have directors. """

    def addDirector(self, directors, locked=True):
        """ Add a director tag(s).

            Parameters:
                directors (list): List of strings.
                locked (bool): True (default) to lock the field, False to unlock the field.
        """
        return self.editTags('director', directors, locked=locked)

    def removeDirector(self, directors, locked=True):
        """ Remove a director tag(s).

            Parameters:
                directors (list): List of strings.
                locked (bool): True (default) to lock the field, False to unlock the field.
        """
        return self.editTags('director', directors, locked=locked, remove=True)


class GenreMixin(EditTagsMixin):
    """ Mixin for Plex objects that can have genres. """

    def addGenre(self, genres, locked=True):
        """ Add a genre tag(s).

            Parameters:
                genres (list): List of strings.
                locked (bool): True (default) to lock the field, False to unlock the field.
        """
        return self.editTags('genre', genres, locked=locked)

    def removeGenre(self, genres, locked=True):
        """ Remove a genre tag(s).

            Parameters:
                genres (list): List of strings.
                locked (bool): True (default) to lock the field, False to unlock the field.
        """
        return self.editTags('genre', genres, locked=locked, remove=True)


class LabelMixin(EditTagsMixin):
    """ Mixin for Plex objects that can have labels. """

    def addLabel(self, labels, locked=True):
        """ Add a label tag(s).

            Parameters:
                labels (list): List of strings.
                locked (bool): True (default) to lock the field, False to unlock the field.
        """
        return self.editTags('label', labels, locked=locked)

    def removeLabel(self, labels, locked=True):
        """ Remove a label tag(s).

            Parameters:
                labels (list): List of strings.
                locked (bool): True (default) to lock the field, False to unlock the field.
        """
        return self.editTags('label', labels, locked=locked, remove=True)


class MoodMixin(EditTagsMixin):
    """ Mixin for Plex objects that can have moods. """

    def addMood(self, moods, locked=True):
        """ Add a mood tag(s).

            Parameters:
                moods (list): List of strings.
                locked (bool): True (default) to lock the field, False to unlock the field.
        """
        return self.editTags('mood', moods, locked=locked)

    def removeMood(self, moods, locked=True):
        """ Remove a mood tag(s).

            Parameters:
                moods (list): List of strings.
                locked (bool): True (default) to lock the field, False to unlock the field.
        """
        return self.editTags('mood', moods, locked=locked, remove=True)


class ProducerMixin(EditTagsMixin):
    """ Mixin for Plex objects that can have producers. """

    def addProducer(self, producers, locked=True):
        """ Add a producer tag(s).

            Parameters:
                producers (list): List of strings.
                locked (bool): True (default) to lock the field, False to unlock the field.
        """
        return self.editTags('producer', producers, locked=locked)

    def removeProducer(self, producers, locked=True):
        """ Remove a producer tag(s).

            Parameters:
                producers (list): List of strings.
                locked (bool): True (default) to lock the field, False to unlock the field.
        """
        return self.editTags('producer', producers, locked=locked, remove=True)


class SimilarArtistMixin(EditTagsMixin):
    """ Mixin for Plex objects that can have similar artists. """

    def addSimilarArtist(self, artists, locked=True):
        """ Add a similar artist tag(s).

            Parameters:
                artists (list): List of strings.
                locked (bool): True (default) to lock the field, False to unlock the field.
        """
        return self.editTags('similar', artists, locked=locked)

    def removeSimilarArtist(self, artists, locked=True):
        """ Remove a similar artist tag(s).

            Parameters:
                artists (list): List of strings.
                locked (bool): True (default) to lock the field, False to unlock the field.
        """
        return self.editTags('similar', artists, locked=locked, remove=True)


class StyleMixin(EditTagsMixin):
    """ Mixin for Plex objects that can have styles. """

    def addStyle(self, styles, locked=True):
        """ Add a style tag(s).

            Parameters:
                styles (list): List of strings.
                locked (bool): True (default) to lock the field, False to unlock the field.
        """
        return self.editTags('style', styles, locked=locked)

    def removeStyle(self, styles, locked=True):
        """ Remove a style tag(s).

            Parameters:
                styles (list): List of strings.
                locked (bool): True (default) to lock the field, False to unlock the field.
        """
        return self.editTags('style', styles, locked=locked, remove=True)


class TagMixin(EditTagsMixin):
    """ Mixin for Plex objects that can have tags. """

    def addTag(self, tags, locked=True):
        """ Add a tag(s).

            Parameters:
                tags (list): List of strings.
                locked (bool): True (default) to lock the field, False to unlock the field.
        """
        return self.editTags('tag', tags, locked=locked)

    def removeTag(self, tags, locked=True):
        """ Remove a tag(s).

            Parameters:
                tags (list): List of strings.
                locked (bool): True (default) to lock the field, False to unlock the field.
        """
        return self.editTags('tag', tags, locked=locked, remove=True)


class WriterMixin(EditTagsMixin):
    """ Mixin for Plex objects that can have writers. """

    def addWriter(self, writers, locked=True):
        """ Add a writer tag(s).

            Parameters:
                writers (list): List of strings.
                locked (bool): True (default) to lock the field, False to unlock the field.
        """
        return self.editTags('writer', writers, locked=locked)

    def removeWriter(self, writers, locked=True):
        """ Remove a writer tag(s).

            Parameters:
                writers (list): List of strings.
                locked (bool): True (default) to lock the field, False to unlock the field.
        """
        return self.editTags('writer', writers, locked=locked, remove=True)


class WatchlistMixin(object):
    """ Mixin for Plex objects that can be added to a user's watchlist. """

    def onWatchlist(self, account=None):
        """ Returns True if the item is on the user's watchlist.
            Also see :func:`~plexapi.myplex.MyPlexAccount.onWatchlist`.

            Parameters:
                account (:class:`~plexapi.myplex.MyPlexAccount`, optional): Account to check item on the watchlist.
                   Note: This is required if you are not connected to a Plex server instance using the admin account.
        """
        try:
            account = account or self._server.myPlexAccount()
        except AttributeError:
            account = self._server
        return account.onWatchlist(self)

    def addToWatchlist(self, account=None):
        """ Add this item to the specified user's watchlist.
            Also see :func:`~plexapi.myplex.MyPlexAccount.addToWatchlist`.

            Parameters:
                account (:class:`~plexapi.myplex.MyPlexAccount`, optional): Account to add item to the watchlist.
                   Note: This is required if you are not connected to a Plex server instance using the admin account.
        """
        try:
            account = account or self._server.myPlexAccount()
        except AttributeError:
            account = self._server
        account.addToWatchlist(self)

    def removeFromWatchlist(self, account=None):
        """ Remove this item from the specified user's watchlist.
            Also see :func:`~plexapi.myplex.MyPlexAccount.removeFromWatchlist`.

            Parameters:
                account (:class:`~plexapi.myplex.MyPlexAccount`, optional): Account to remove item from the watchlist.
                   Note: This is required if you are not connected to a Plex server instance using the admin account.
        """
        try:
            account = account or self._server.myPlexAccount()
        except AttributeError:
            account = self._server
        account.removeFromWatchlist(self)

    def streamingServices(self, account=None):
        """ Return a list of :class:`~plexapi.media.Availability`
            objects for the available streaming services for this item.

            Parameters:
                account (:class:`~plexapi.myplex.MyPlexAccount`, optional): Account used to retrieve availability.
                   Note: This is required if you are not connected to a Plex server instance using the admin account.
        """
        try:
            account = account or self._server.myPlexAccount()
        except AttributeError:
            account = self._server
        ratingKey = self.guid.rsplit('/', 1)[-1]
        data = account.query(f"{account.METADATA}/library/metadata/{ratingKey}/availabilities")
        return self.findItems(data)
