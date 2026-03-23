class ExtrasMixin:
    """ Mixin for Plex objects that can have extras. """

    def extras(self):
        """ Returns a list of :class:`~plexapi.video.Extra` objects. """
        from plexapi.video import Extra
        key = f'{self.key}/extras'
        return self.fetchItems(key, cls=Extra)


class HubsMixin:
    """ Mixin for Plex objects that can have related hubs. """

    def hubs(self):
        """ Returns a list of :class:`~plexapi.library.Hub` objects. """
        from plexapi.library import Hub
        key = f'{self.key}/related'
        return self.fetchItems(key, cls=Hub)
