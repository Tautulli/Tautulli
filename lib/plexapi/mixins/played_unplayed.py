class PlayedUnplayedMixin:
    """ Mixin for Plex objects that can be marked played and unplayed. """

    @property
    def isPlayed(self):
        """ Returns True if this video is played. """
        return bool(self.viewCount > 0) if self.viewCount else False

    def markPlayed(self):
        """ Mark the Plex object as played. """
        key = '/:/scrobble'
        params = {'key': self.ratingKey, 'identifier': 'com.plexapp.plugins.library'}
        self._server.query(key, params=params)
        return self

    def markUnplayed(self):
        """ Mark the Plex object as unplayed. """
        key = '/:/unscrobble'
        params = {'key': self.ratingKey, 'identifier': 'com.plexapp.plugins.library'}
        self._server.query(key, params=params)
        return self

    @property
    def isWatched(self):
        """ Alias to self.isPlayed. """
        return self.isPlayed

    def markWatched(self):
        """ Alias to :func:`~plexapi.mixins.PlayedUnplayedMixin.markPlayed`. """
        self.markPlayed()

    def markUnwatched(self):
        """ Alias to :func:`~plexapi.mixins.PlayedUnplayedMixin.markUnplayed`. """
        self.markUnplayed()
