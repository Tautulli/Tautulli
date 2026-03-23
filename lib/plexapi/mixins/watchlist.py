class WatchlistMixin:
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
        return self

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
        return self

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
