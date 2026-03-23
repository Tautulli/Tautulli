class SplitMergeMixin:
    """ Mixin for Plex objects that can be split and merged. """

    def split(self):
        """ Split duplicated Plex object into separate objects. """
        key = f'{self.key}/split'
        self._server.query(key, method=self._server._session.put)
        return self

    def merge(self, ratingKeys):
        """ Merge other Plex objects into the current object.

            Parameters:
                ratingKeys (list): A list of rating keys to merge.
        """
        if not isinstance(ratingKeys, list):
            ratingKeys = str(ratingKeys).split(',')

        key = f"{self.key}/merge?ids={','.join(str(r) for r in ratingKeys)}"
        self._server.query(key, method=self._server._session.put)
        return self
