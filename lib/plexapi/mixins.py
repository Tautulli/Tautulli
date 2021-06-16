# -*- coding: utf-8 -*-
from urllib.parse import quote_plus, urlencode

from plexapi import media, settings, utils
from plexapi.exceptions import BadRequest, NotFound


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


class PosterUrlMixin(object):
    """ Mixin for Plex objects that can have a poster url. """

    @property
    def thumbUrl(self):
        """ Return the thumb url for the Plex object. """
        thumb = self.firstAttr('thumb', 'parentThumb', 'granparentThumb')
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


class CollectionMixin(object):
    """ Mixin for Plex objects that can have collections. """

    def addCollection(self, collections, locked=True):
        """ Add a collection tag(s).

           Parameters:
                collections (list): List of strings.
                locked (bool): True (default) to lock the field, False to unlock the field.
        """
        self._edit_tags('collection', collections, locked=locked)

    def removeCollection(self, collections, locked=True):
        """ Remove a collection tag(s).

           Parameters:
                collections (list): List of strings.
                locked (bool): True (default) to lock the field, False to unlock the field.
        """
        self._edit_tags('collection', collections, locked=locked, remove=True)


class CountryMixin(object):
    """ Mixin for Plex objects that can have countries. """

    def addCountry(self, countries, locked=True):
        """ Add a country tag(s).

           Parameters:
                countries (list): List of strings.
                locked (bool): True (default) to lock the field, False to unlock the field.
        """
        self._edit_tags('country', countries, locked=locked)

    def removeCountry(self, countries, locked=True):
        """ Remove a country tag(s).

           Parameters:
                countries (list): List of strings.
                locked (bool): True (default) to lock the field, False to unlock the field.
        """
        self._edit_tags('country', countries, locked=locked, remove=True)


class DirectorMixin(object):
    """ Mixin for Plex objects that can have directors. """

    def addDirector(self, directors, locked=True):
        """ Add a director tag(s).

           Parameters:
                directors (list): List of strings.
                locked (bool): True (default) to lock the field, False to unlock the field.
        """
        self._edit_tags('director', directors, locked=locked)

    def removeDirector(self, directors, locked=True):
        """ Remove a director tag(s).

           Parameters:
                directors (list): List of strings.
                locked (bool): True (default) to lock the field, False to unlock the field.
        """
        self._edit_tags('director', directors, locked=locked, remove=True)


class GenreMixin(object):
    """ Mixin for Plex objects that can have genres. """

    def addGenre(self, genres, locked=True):
        """ Add a genre tag(s).

           Parameters:
                genres (list): List of strings.
                locked (bool): True (default) to lock the field, False to unlock the field.
        """
        self._edit_tags('genre', genres, locked=locked)

    def removeGenre(self, genres, locked=True):
        """ Remove a genre tag(s).

           Parameters:
                genres (list): List of strings.
                locked (bool): True (default) to lock the field, False to unlock the field.
        """
        self._edit_tags('genre', genres, locked=locked, remove=True)


class LabelMixin(object):
    """ Mixin for Plex objects that can have labels. """

    def addLabel(self, labels, locked=True):
        """ Add a label tag(s).

           Parameters:
                labels (list): List of strings.
                locked (bool): True (default) to lock the field, False to unlock the field.
        """
        self._edit_tags('label', labels, locked=locked)

    def removeLabel(self, labels, locked=True):
        """ Remove a label tag(s).

           Parameters:
                labels (list): List of strings.
                locked (bool): True (default) to lock the field, False to unlock the field.
        """
        self._edit_tags('label', labels, locked=locked, remove=True)


class MoodMixin(object):
    """ Mixin for Plex objects that can have moods. """

    def addMood(self, moods, locked=True):
        """ Add a mood tag(s).

           Parameters:
                moods (list): List of strings.
                locked (bool): True (default) to lock the field, False to unlock the field.
        """
        self._edit_tags('mood', moods, locked=locked)

    def removeMood(self, moods, locked=True):
        """ Remove a mood tag(s).

           Parameters:
                moods (list): List of strings.
                locked (bool): True (default) to lock the field, False to unlock the field.
        """
        self._edit_tags('mood', moods, locked=locked, remove=True)


class ProducerMixin(object):
    """ Mixin for Plex objects that can have producers. """

    def addProducer(self, producers, locked=True):
        """ Add a producer tag(s).

           Parameters:
                producers (list): List of strings.
                locked (bool): True (default) to lock the field, False to unlock the field.
        """
        self._edit_tags('producer', producers, locked=locked)

    def removeProducer(self, producers, locked=True):
        """ Remove a producer tag(s).

           Parameters:
                producers (list): List of strings.
                locked (bool): True (default) to lock the field, False to unlock the field.
        """
        self._edit_tags('producer', producers, locked=locked, remove=True)


class SimilarArtistMixin(object):
    """ Mixin for Plex objects that can have similar artists. """

    def addSimilarArtist(self, artists, locked=True):
        """ Add a similar artist tag(s).

           Parameters:
                artists (list): List of strings.
                locked (bool): True (default) to lock the field, False to unlock the field.
        """
        self._edit_tags('similar', artists, locked=locked)

    def removeSimilarArtist(self, artists, locked=True):
        """ Remove a similar artist tag(s).

           Parameters:
                artists (list): List of strings.
                locked (bool): True (default) to lock the field, False to unlock the field.
        """
        self._edit_tags('similar', artists, locked=locked, remove=True)


class StyleMixin(object):
    """ Mixin for Plex objects that can have styles. """

    def addStyle(self, styles, locked=True):
        """ Add a style tag(s).

           Parameters:
                styles (list): List of strings.
                locked (bool): True (default) to lock the field, False to unlock the field.
        """
        self._edit_tags('style', styles, locked=locked)

    def removeStyle(self, styles, locked=True):
        """ Remove a style tag(s).

           Parameters:
                styles (list): List of strings.
                locked (bool): True (default) to lock the field, False to unlock the field.
        """
        self._edit_tags('style', styles, locked=locked, remove=True)


class TagMixin(object):
    """ Mixin for Plex objects that can have tags. """

    def addTag(self, tags, locked=True):
        """ Add a tag(s).

           Parameters:
                tags (list): List of strings.
                locked (bool): True (default) to lock the field, False to unlock the field.
        """
        self._edit_tags('tag', tags, locked=locked)

    def removeTag(self, tags, locked=True):
        """ Remove a tag(s).

           Parameters:
                tags (list): List of strings.
                locked (bool): True (default) to lock the field, False to unlock the field.
        """
        self._edit_tags('tag', tags, locked=locked, remove=True)


class WriterMixin(object):
    """ Mixin for Plex objects that can have writers. """

    def addWriter(self, writers, locked=True):
        """ Add a writer tag(s).

           Parameters:
                writers (list): List of strings.
                locked (bool): True (default) to lock the field, False to unlock the field.
        """
        self._edit_tags('writer', writers, locked=locked)

    def removeWriter(self, writers, locked=True):
        """ Remove a writer tag(s).

           Parameters:
                writers (list): List of strings.
                locked (bool): True (default) to lock the field, False to unlock the field.
        """
        self._edit_tags('writer', writers, locked=locked, remove=True)
