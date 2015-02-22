#  This file is part of PlexPy.
#
#  PlexPy is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  PlexPy is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with PlexPy.  If not, see <http://www.gnu.org/licenses/>.

import os
import plexpy

from plexpy import db, helpers, logger, request

LASTFM_API_KEY = "690e1ed3bc00bc91804cd8f7fe5ed6d4"


class Cache(object):
    """
    This class deals with getting, storing and serving up artwork (album art,
    artist images, etc) and info/descriptions (album info, artist descrptions)
    to and from the cache folder. This can be called from within a web
    interface. For example, using the helper functions `getInfo(id)` and
    `getArtwork(id)`, to utilize the cached images rather than having to
    retrieve them every time the page is reloaded.

    You can call `getArtwork(id)` which will return an absolute path to the
    image file on the local machine, or if the cache directory doesn't exist,
    or can not be written to, it will return a url to the image.

    Call `getInfo(id)` to grab the artist/album info. This will return the
    text description.

    The basic format for art in the cache is `<musicbrainzid>.<date>.<ext>`
    and for info it is `<musicbrainzid>.<date>.txt`
    """

    path_to_art_cache = os.path.join(plexpy.CONFIG.CACHE_DIR, 'artwork')

    def __init__(self):
        self.id = None
        self.id_type = None # 'artist' or 'album' - set automatically depending on whether ArtistID or AlbumID is passed
        self.query_type = None # 'artwork','thumb' or 'info' - set automatically

        self.artwork_files = []
        self.thumb_files = []

        self.artwork_errors = False
        self.artwork_url = None

        self.thumb_errors = False
        self.thumb_url = None

        self.info_summary = None
        self.info_content = None

    def _findfilesstartingwith(self, pattern, folder):
        files = []
        if os.path.exists(folder):
            for fname in os.listdir(folder):
                if fname.startswith(pattern):
                    files.append(os.path.join(folder, fname))
        return files

    def _exists(self, type):
        self.artwork_files = []
        self.thumb_files = []

        if type == 'artwork':
            self.artwork_files = self._findfilesstartingwith(self.id, self.path_to_art_cache)
            if self.artwork_files:
                return True
            else:
                return False

        elif type == 'thumb':
            self.thumb_files = self._findfilesstartingwith("T_" + self.id, self.path_to_art_cache)
            if self.thumb_files:
                return True
            else:
                return False

    def _get_age(self, date):
        # There's probably a better way to do this
        split_date = date.split('-')
        days_old = int(split_date[0]) * 365 + int(split_date[1]) * 30 + int(split_date[2])

        return days_old

    def _is_current(self, filename=None, date=None):

        if filename:
            base_filename = os.path.basename(filename)
            date = base_filename.split('.')[1]

        # Calculate how old the cached file is based on todays date & file date stamp
        # helpers.today() returns todays date in yyyy-mm-dd format
        if self._get_age(helpers.today()) - self._get_age(date) < 30:
            return True
        else:
            return False

    def _get_thumb_url(self, data):

        thumb_url = None

        try:
            images = data[self.id_type]['image']
        except KeyError:
            return None

        for image in images:
            if image['size'] == 'medium':
                thumb_url = image['#text']
                break

        return thumb_url

    def get_artwork_from_cache(self, ArtistID=None, AlbumID=None):
        """
        Pass a musicbrainz id to this function (either ArtistID or AlbumID)
        """

        self.query_type = 'artwork'

        if ArtistID:
            self.id = ArtistID
            self.id_type = 'artist'
        else:
            self.id = AlbumID
            self.id_type = 'album'

        if self._exists('artwork') and self._is_current(filename=self.artwork_files[0]):
            return self.artwork_files[0]
        else:
            self._update_cache()
            # If we failed to get artwork, either return the url or the older file
            if self.artwork_errors and self.artwork_url:
                return self.artwork_url
            elif self._exists('artwork'):
                return self.artwork_files[0]
            else:
                return None

    def get_thumb_from_cache(self, ArtistID=None, AlbumID=None):
        """
        Pass a musicbrainz id to this function (either ArtistID or AlbumID)
        """

        self.query_type = 'thumb'

        if ArtistID:
            self.id = ArtistID
            self.id_type = 'artist'
        else:
            self.id = AlbumID
            self.id_type = 'album'

        if self._exists('thumb') and self._is_current(filename=self.thumb_files[0]):
            return self.thumb_files[0]
        else:
            self._update_cache()
            # If we failed to get artwork, either return the url or the older file
            if self.thumb_errors and self.thumb_url:
                return self.thumb_url
            elif self._exists('thumb'):
                return self.thumb_files[0]
            else:
                return None

    def get_info_from_cache(self, ArtistID=None, AlbumID=None):

        self.query_type = 'info'
        myDB = db.DBConnection()

        if ArtistID:
            self.id = ArtistID
            self.id_type = 'artist'
            db_info = myDB.action('SELECT Summary, Content, LastUpdated FROM descriptions WHERE ArtistID=?', [self.id]).fetchone()
        else:
            self.id = AlbumID
            self.id_type = 'album'
            db_info = myDB.action('SELECT Summary, Content, LastUpdated FROM descriptions WHERE ReleaseGroupID=?', [self.id]).fetchone()

        if not db_info or not db_info['LastUpdated'] or not self._is_current(date=db_info['LastUpdated']):

            self._update_cache()
            info_dict = {'Summary': self.info_summary, 'Content': self.info_content}
            return info_dict

        else:
            info_dict = {'Summary': db_info['Summary'], 'Content': db_info['Content']}
            return info_dict

    def get_image_links(self, ArtistID=None, AlbumID=None):
        """
        Here we're just going to open up the last.fm url, grab the image links and return them
        Won't save any image urls, or save the artwork in the cache. Useful for search results, etc.
        """
        if ArtistID:

            self.id_type = 'artist'
            data = lastfm.request_lastfm("artist.getinfo", mbid=ArtistID, api_key=LASTFM_API_KEY)

            if not data:
                return

            try:
                image_url = data['artist']['image'][-1]['#text']
            except (KeyError, IndexError):
                logger.debug('No artist image found')
                image_url = None

            thumb_url = self._get_thumb_url(data)
            if not thumb_url:
                logger.debug('No artist thumbnail image found')

        else:

            self.id_type = 'album'
            data = lastfm.request_lastfm("album.getinfo", mbid=AlbumID, api_key=LASTFM_API_KEY)

            if not data:
                return

            try:
                image_url = data['album']['image'][-1]['#text']
            except (KeyError, IndexError):
                logger.debug('No album image found on last.fm')
                image_url = None

            thumb_url = self._get_thumb_url(data)

            if not thumb_url:
                logger.debug('No album thumbnail image found on last.fm')

        return {'artwork': image_url, 'thumbnail': thumb_url}

    def remove_from_cache(self, ArtistID=None, AlbumID=None):
        """
        Pass a musicbrainz id to this function (either ArtistID or AlbumID)
        """

        if ArtistID:
            self.id = ArtistID
            self.id_type = 'artist'
        else:
            self.id = AlbumID
            self.id_type = 'album'

        self.query_type = 'artwork'

        if self._exists('artwork'):
            for artwork_file in self.artwork_files:
                try:
                    os.remove(artwork_file)
                except:
                    logger.warn('Error deleting file from the cache: %s', artwork_file)

        self.query_type = 'thumb'

        if self._exists('thumb'):
            for thumb_file in self.thumb_files:
                try:
                    os.remove(thumb_file)
                except Exception:
                    logger.warn('Error deleting file from the cache: %s', thumb_file)

    def _update_cache(self):
        """
        Since we call the same url for both info and artwork, we'll update both at the same time
        """

        myDB = db.DBConnection()

        # Since lastfm uses release ids rather than release group ids for albums, we have to do a artist + album search for albums
        # Exception is when adding albums manually, then we should use release id
        if self.id_type == 'artist':

            data = lastfm.request_lastfm("artist.getinfo", mbid=self.id, api_key=LASTFM_API_KEY)

            if not data:
                return

            try:
                self.info_summary = data['artist']['bio']['summary']
            except KeyError:
                logger.debug('No artist bio summary found')
                self.info_summary = None
            try:
                self.info_content = data['artist']['bio']['content']
            except KeyError:
                logger.debug('No artist bio found')
                self.info_content = None
            try:
                image_url = data['artist']['image'][-1]['#text']
            except KeyError:
                logger.debug('No artist image found')
                image_url = None

            thumb_url = self._get_thumb_url(data)
            if not thumb_url:
                logger.debug('No artist thumbnail image found')

        else:
            dbalbum = myDB.action('SELECT ArtistName, AlbumTitle, ReleaseID FROM albums WHERE AlbumID=?', [self.id]).fetchone()
            if dbalbum['ReleaseID'] != self.id:
                data = lastfm.request_lastfm("album.getinfo", mbid=dbalbum['ReleaseID'], api_key=LASTFM_API_KEY)
                if not data:
                    data = lastfm.request_lastfm("album.getinfo", artist=dbalbum['ArtistName'], album=dbalbum['AlbumTitle'], api_key=LASTFM_API_KEY)
            else:
                data = lastfm.request_lastfm("album.getinfo", artist=dbalbum['ArtistName'], album=dbalbum['AlbumTitle'], api_key=LASTFM_API_KEY)

            if not data:
                return

            try:
                self.info_summary = data['album']['wiki']['summary']
            except KeyError:
                logger.debug('No album summary found')
                self.info_summary = None
            try:
                self.info_content = data['album']['wiki']['content']
            except KeyError:
                logger.debug('No album infomation found')
                self.info_content = None
            try:
                image_url = data['album']['image'][-1]['#text']
            except KeyError:
                logger.debug('No album image link found')
                image_url = None

            thumb_url = self._get_thumb_url(data)

            if not thumb_url:
                logger.debug('No album thumbnail image found')

        # Save the content & summary to the database no matter what if we've
        # opened up the url
        if self.id_type == 'artist':
            controlValueDict = {"ArtistID": self.id}
        else:
            controlValueDict = {"ReleaseGroupID": self.id}

        newValueDict = {"Summary": self.info_summary,
                        "Content": self.info_content,
                        "LastUpdated": helpers.today()}

        myDB.upsert("descriptions", newValueDict, controlValueDict)

        # Save the image URL to the database
        if image_url:
            if self.id_type == 'artist':
                myDB.action('UPDATE artists SET ArtworkURL=? WHERE ArtistID=?', [image_url, self.id])
            else:
                myDB.action('UPDATE albums SET ArtworkURL=? WHERE AlbumID=?', [image_url, self.id])

        # Save the thumb URL to the database
        if thumb_url:
            if self.id_type == 'artist':
                myDB.action('UPDATE artists SET ThumbURL=? WHERE ArtistID=?', [thumb_url, self.id])
            else:
                myDB.action('UPDATE albums SET ThumbURL=? WHERE AlbumID=?', [thumb_url, self.id])

        # Should we grab the artwork here if we're just grabbing thumbs or
        # info? Probably not since the files can be quite big
        if image_url and self.query_type == 'artwork':
            artwork = request.request_content(image_url, timeout=20)

            if artwork:
                # Make sure the artwork dir exists:
                if not os.path.isdir(self.path_to_art_cache):
                    try:
                        os.makedirs(self.path_to_art_cache)
                        os.chmod(self.path_to_art_cache, int(plexpy.CONFIG.FOLDER_PERMISSIONS, 8))
                    except OSError as e:
                        logger.error('Unable to create artwork cache dir. Error: %s', e)
                        self.artwork_errors = True
                        self.artwork_url = image_url

                # Delete the old stuff
                for artwork_file in self.artwork_files:
                    try:
                        os.remove(artwork_file)
                    except:
                        logger.error('Error deleting file from the cache: %s', artwork_file)

                ext = os.path.splitext(image_url)[1]

                artwork_path = os.path.join(self.path_to_art_cache, self.id + '.' + helpers.today() + ext)
                try:
                    with open(artwork_path, 'wb') as f:
                        f.write(artwork)

                    os.chmod(artwork_path, int(plexpy.CONFIG.FILE_PERMISSIONS, 8))
                except (OSError, IOError) as e:
                    logger.error('Unable to write to the cache dir: %s', e)
                    self.artwork_errors = True
                    self.artwork_url = image_url

        # Grab the thumbnail as well if we're getting the full artwork (as long
        # as it's missing/outdated.
        if thumb_url and self.query_type in ['thumb', 'artwork'] and not (self.thumb_files and self._is_current(self.thumb_files[0])):
            artwork = request.request_content(thumb_url, timeout=20)

            if artwork:
                # Make sure the artwork dir exists:
                if not os.path.isdir(self.path_to_art_cache):
                    try:
                        os.makedirs(self.path_to_art_cache)
                        os.chmod(self.path_to_art_cache, int(plexpy.CONFIG.FOLDER_PERMISSIONS, 8))
                    except OSError as e:
                        logger.error('Unable to create artwork cache dir. Error: %s' + e)
                        self.thumb_errors = True
                        self.thumb_url = thumb_url

                # Delete the old stuff
                for thumb_file in self.thumb_files:
                    try:
                        os.remove(thumb_file)
                    except OSError as e:
                        logger.error('Error deleting file from the cache: %s', thumb_file)

                ext = os.path.splitext(image_url)[1]

                thumb_path = os.path.join(self.path_to_art_cache, 'T_' + self.id + '.' + helpers.today() + ext)
                try:
                    with open(thumb_path, 'wb') as f:
                        f.write(artwork)

                    os.chmod(thumb_path, int(plexpy.CONFIG.FILE_PERMISSIONS, 8))
                except (OSError, IOError) as e:
                    logger.error('Unable to write to the cache dir: %s', e)
                    self.thumb_errors = True
                    self.thumb_url = image_url


def getArtwork(ArtistID=None, AlbumID=None):
    c = Cache()
    artwork_path = c.get_artwork_from_cache(ArtistID, AlbumID)

    if not artwork_path:
        return None

    if artwork_path.startswith('http://'):
        return artwork_path
    else:
        artwork_file = os.path.basename(artwork_path)
        return "cache/artwork/" + artwork_file


def getThumb(ArtistID=None, AlbumID=None):
    c = Cache()
    artwork_path = c.get_thumb_from_cache(ArtistID, AlbumID)

    if not artwork_path:
        return None

    if artwork_path.startswith('http://'):
        return artwork_path
    else:
        thumbnail_file = os.path.basename(artwork_path)
        return "cache/artwork/" + thumbnail_file


def getInfo(ArtistID=None, AlbumID=None):
    c = Cache()
    info_dict = c.get_info_from_cache(ArtistID, AlbumID)

    return info_dict


def getImageLinks(ArtistID=None, AlbumID=None):
    c = Cache()
    image_links = c.get_image_links(ArtistID, AlbumID)

    return image_links
