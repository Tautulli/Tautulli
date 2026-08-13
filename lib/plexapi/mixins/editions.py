class EditionsMixin:
    """ Mixin for Plex objects that can have edition. """

    def editions(self):
        """ Returns a list of :class:`~plexapi.base.PlexPartialObject` objects
            for other editions of the same media.
        """
        filters = {
            'guid': self.guid,
            'id!': self.ratingKey
        }
        return self.section().search(libtype=self.TYPE, filters=filters)
