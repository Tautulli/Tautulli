from plexapi.exceptions import BadRequest


class RatingMixin:
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
        key = f'/:/rate?key={self.ratingKey}&identifier=com.plexapp.plugins.library&rating={rating}'
        self._server.query(key, method=self._server._session.put)
        return self
