from urllib.parse import quote_plus

from plexapi import media
from plexapi.utils import openOrRead


class ArtUrlMixin:
    """ Mixin for Plex objects that can have a background artwork url. """

    @property
    def artUrl(self):
        """ Return the art url for the Plex object. """
        art = self.firstAttr('art', 'grandparentArt')
        return self._server.url(art, includeToken=True) if art else None


class ArtLockMixin:
    """ Mixin for Plex objects that can have a locked background artwork. """

    def lockArt(self):
        """ Lock the background artwork for a Plex object. """
        return self._edit(**{'art.locked': 1})

    def unlockArt(self):
        """ Unlock the background artwork for a Plex object. """
        return self._edit(**{'art.locked': 0})


class ArtMixin(ArtUrlMixin, ArtLockMixin):
    """ Mixin for Plex objects that can have background artwork. """

    def arts(self):
        """ Returns list of available :class:`~plexapi.media.Art` objects. """
        return self.fetchItems(f'/library/metadata/{self.ratingKey}/arts', cls=media.Art)

    def uploadArt(self, url=None, filepath=None):
        """ Upload a background artwork from a url or filepath.

            Parameters:
                url (str): The full URL to the image to upload.
                filepath (str): The full file path to the image to upload or file-like object.
        """
        if url:
            key = f'/library/metadata/{self.ratingKey}/arts?url={quote_plus(url)}'
            self._server.query(key, method=self._server._session.post)
        elif filepath:
            key = f'/library/metadata/{self.ratingKey}/arts'
            data = openOrRead(filepath)
            self._server.query(key, method=self._server._session.post, data=data)
        return self

    def setArt(self, art):
        """ Set the background artwork for a Plex object.

            Parameters:
                art (:class:`~plexapi.media.Art`): The art object to select.
        """
        art.select()
        return self

    def deleteArt(self):
        """ Delete the art from a Plex object. """
        key = f'/library/metadata/{self.ratingKey}/art'
        self._server.query(key, method=self._server._session.delete)
        return self


class LogoUrlMixin:
    """ Mixin for Plex objects that can have a logo url. """

    @property
    def logo(self):
        """ Return the API path to the logo image. """
        return next((i.url for i in self.images if i.type == 'clearLogo'), None)

    @property
    def logoUrl(self):
        """ Return the logo url for the Plex object. """
        return self._server.url(self.logo, includeToken=True) if self.logo else None


class LogoLockMixin:
    """ Mixin for Plex objects that can have a locked logo. """

    def lockLogo(self):
        """ Lock the logo for a Plex object. """
        return self._edit(**{'clearLogo.locked': 1})

    def unlockLogo(self):
        """ Unlock the logo for a Plex object. """
        return self._edit(**{'clearLogo.locked': 0})


class LogoMixin(LogoUrlMixin, LogoLockMixin):
    """ Mixin for Plex objects that can have logos. """

    def logos(self):
        """ Returns list of available :class:`~plexapi.media.Logo` objects. """
        return self.fetchItems(f'/library/metadata/{self.ratingKey}/clearLogos', cls=media.Logo)

    def uploadLogo(self, url=None, filepath=None):
        """ Upload a logo from a url or filepath.

            Parameters:
                url (str): The full URL to the image to upload.
                filepath (str): The full file path to the image to upload or file-like object.
        """
        if url:
            key = f'/library/metadata/{self.ratingKey}/clearLogos?url={quote_plus(url)}'
            self._server.query(key, method=self._server._session.post)
        elif filepath:
            key = f'/library/metadata/{self.ratingKey}/clearLogos'
            data = openOrRead(filepath)
            self._server.query(key, method=self._server._session.post, data=data)
        return self

    def setLogo(self, logo):
        """ Set the logo for a Plex object.

            Parameters:
                logo (:class:`~plexapi.media.Logo`): The logo object to select.
        """
        logo.select()
        return self

    def deleteLogo(self):
        """ Delete the logo from a Plex object. """
        key = f'/library/metadata/{self.ratingKey}/clearLogo'
        self._server.query(key, method=self._server._session.delete)
        return self


class PosterUrlMixin:
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


class PosterLockMixin:
    """ Mixin for Plex objects that can have a locked poster. """

    def lockPoster(self):
        """ Lock the poster for a Plex object. """
        return self._edit(**{'thumb.locked': 1})

    def unlockPoster(self):
        """ Unlock the poster for a Plex object. """
        return self._edit(**{'thumb.locked': 0})


class PosterMixin(PosterUrlMixin, PosterLockMixin):
    """ Mixin for Plex objects that can have posters. """

    def posters(self):
        """ Returns list of available :class:`~plexapi.media.Poster` objects. """
        return self.fetchItems(f'/library/metadata/{self.ratingKey}/posters', cls=media.Poster)

    def uploadPoster(self, url=None, filepath=None):
        """ Upload a poster from a url or filepath.

            Parameters:
                url (str): The full URL to the image to upload.
                filepath (str): The full file path to the image to upload or file-like object.
        """
        if url:
            key = f'/library/metadata/{self.ratingKey}/posters?url={quote_plus(url)}'
            self._server.query(key, method=self._server._session.post)
        elif filepath:
            key = f'/library/metadata/{self.ratingKey}/posters'
            data = openOrRead(filepath)
            self._server.query(key, method=self._server._session.post, data=data)
        return self

    def setPoster(self, poster):
        """ Set the poster for a Plex object.

            Parameters:
                poster (:class:`~plexapi.media.Poster`): The poster object to select.
        """
        poster.select()
        return self

    def deletePoster(self):
        """ Delete the poster from a Plex object. """
        key = f'/library/metadata/{self.ratingKey}/thumb'
        self._server.query(key, method=self._server._session.delete)
        return self


class SquareArtUrlMixin:
    """ Mixin for Plex objects that can have a square art url. """

    @property
    def squareArt(self):
        """ Return the API path to the square art image. """
        return next((i.url for i in self.images if i.type == 'backgroundSquare'), None)

    @property
    def squareArtUrl(self):
        """ Return the square art url for the Plex object. """
        return self._server.url(self.squareArt, includeToken=True) if self.squareArt else None


class SquareArtLockMixin:
    """ Mixin for Plex objects that can have a locked square art. """

    def lockSquareArt(self):
        """ Lock the square art for a Plex object. """
        return self._edit(**{'squareArt.locked': 1})

    def unlockSquareArt(self):
        """ Unlock the square art for a Plex object. """
        return self._edit(**{'squareArt.locked': 0})


class SquareArtMixin(SquareArtUrlMixin, SquareArtLockMixin):
    """ Mixin for Plex objects that can have square art. """

    def squareArts(self):
        """ Returns list of available :class:`~plexapi.media.SquareArt` objects. """
        return self.fetchItems(f'/library/metadata/{self.ratingKey}/squareArts', cls=media.SquareArt)

    def uploadSquareArt(self, url=None, filepath=None):
        """ Upload a square art from a url or filepath.

            Parameters:
                url (str): The full URL to the image to upload.
                filepath (str): The full file path to the image to upload or file-like object.
        """
        if url:
            key = f'/library/metadata/{self.ratingKey}/squareArts?url={quote_plus(url)}'
            self._server.query(key, method=self._server._session.post)
        elif filepath:
            key = f'/library/metadata/{self.ratingKey}/squareArts'
            data = openOrRead(filepath)
            self._server.query(key, method=self._server._session.post, data=data)
        return self

    def setSquareArt(self, squareArt):
        """ Set the square art for a Plex object.

            Parameters:
                squareArt (:class:`~plexapi.media.SquareArt`): The square art object to select.
        """
        squareArt.select()
        return self

    def deleteSquareArt(self):
        """ Delete the square art from a Plex object. """
        key = f'/library/metadata/{self.ratingKey}/squareArt'
        self._server.query(key, method=self._server._session.delete)
        return self


class ThemeUrlMixin:
    """ Mixin for Plex objects that can have a theme url. """

    @property
    def themeUrl(self):
        """ Return the theme url for the Plex object. """
        theme = self.firstAttr('theme', 'parentTheme', 'grandparentTheme')
        return self._server.url(theme, includeToken=True) if theme else None


class ThemeLockMixin:
    """ Mixin for Plex objects that can have a locked theme. """

    def lockTheme(self):
        """ Lock the theme for a Plex object. """
        return self._edit(**{'theme.locked': 1})

    def unlockTheme(self):
        """ Unlock the theme for a Plex object. """
        return self._edit(**{'theme.locked': 0})


class ThemeMixin(ThemeUrlMixin, ThemeLockMixin):
    """ Mixin for Plex objects that can have themes. """

    def themes(self):
        """ Returns list of available :class:`~plexapi.media.Theme` objects. """
        return self.fetchItems(f'/library/metadata/{self.ratingKey}/themes', cls=media.Theme)

    def uploadTheme(self, url=None, filepath=None, timeout=None):
        """ Upload a theme from url or filepath.

            Warning: Themes cannot be deleted using PlexAPI!

            Parameters:
                url (str): The full URL to the theme to upload.
                filepath (str): The full file path to the theme to upload or file-like object.
                timeout (int, optional): Timeout, in seconds, to use when uploading themes to the server.
                    (default config.TIMEOUT).
        """
        if url:
            key = f'/library/metadata/{self.ratingKey}/themes?url={quote_plus(url)}'
            self._server.query(key, method=self._server._session.post, timeout=timeout)
        elif filepath:
            key = f'/library/metadata/{self.ratingKey}/themes'
            data = openOrRead(filepath)
            self._server.query(key, method=self._server._session.post, data=data, timeout=timeout)
        return self

    def setTheme(self, theme):
        """ Set the theme for a Plex object.

            Raises:
                :exc:`~plexapi.exceptions.NotImplementedError`: Themes cannot be set through the API.
        """
        raise NotImplementedError(
            'Themes cannot be set through the API. '
            'Re-upload the theme using "uploadTheme" to set it.'
        )

    def deleteTheme(self):
        """ Delete the theme from a Plex object. """
        key = f'/library/metadata/{self.ratingKey}/theme'
        self._server.query(key, method=self._server._session.delete)
        return self
