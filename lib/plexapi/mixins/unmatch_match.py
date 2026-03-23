from urllib.parse import urlencode

from plexapi import media, utils
from plexapi.exceptions import NotFound


class UnmatchMatchMixin:
    """ Mixin for Plex objects that can be unmatched and matched. """

    def unmatch(self):
        """ Unmatches metadata match from object. """
        key = f'{self.key}/unmatch'
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
        key = f'{self.key}/matches'
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
                    params['year'] = getattr(self, 'year', '')
                else:
                    params['year'] = year

                params['language'] = language or self.section().language

                if agent is None:
                    params['agent'] = self.section().agent
                else:
                    params['agent'] = utils.getAgentIdentifier(self.section(), agent)

        key = key + '?' + urlencode(params)
        return self.fetchItems(key, cls=media.SearchResult)

    def fixMatch(self, searchResult=None, auto=False, agent=None):
        """ Use match result to update show metadata.

            Parameters:
                auto (bool): True uses first match from matches
                    False allows user to provide the match
                searchResult (:class:`~plexapi.media.SearchResult`): Search result from
                    ~plexapi.base.matches()
                agent (str): Agent name to be used (imdb, thetvdb, themoviedb, etc.)
        """
        key = f'{self.key}/match'
        if auto:
            autoMatch = self.matches(agent=agent)
            if autoMatch:
                searchResult = autoMatch[0]
            else:
                raise NotFound(f'No matches found using this agent: ({agent}:{autoMatch})')
        elif not searchResult:
            raise NotFound('fixMatch() requires either auto=True or '
                           'searchResult=:class:`~plexapi.media.SearchResult`.')

        params = {'guid': searchResult.guid,
                  'name': searchResult.name}

        data = key + '?' + urlencode(params)
        self._server.query(data, method=self._server._session.put)
        return self
