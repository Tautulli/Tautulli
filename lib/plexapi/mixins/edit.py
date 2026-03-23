from datetime import datetime
from urllib.parse import quote


class EditFieldMixin:
    """ Mixin for editing Plex object fields. """

    def editField(self, field, value, locked=True, **kwargs):
        """ Edit the field of a Plex object. All field editing methods can be chained together.
            Also see :func:`~plexapi.base.PlexPartialObject.batchEdits` for batch editing fields.

            Parameters:
                field (str): The name of the field to edit.
                value (str): The value to edit the field to.
                locked (bool): True (default) to lock the field, False to unlock the field.

            Example:

                .. code-block:: python

                    # Chaining multiple field edits with reloading
                    Movie.editTitle('A New Title').editSummary('A new summary').editTagline('A new tagline').reload()

        """
        edits = {
            f'{field}.value': value or '',
            f'{field}.locked': 1 if locked else 0
        }
        edits.update(kwargs)
        return self._edit(**edits)


class AddedAtMixin(EditFieldMixin):
    """ Mixin for Plex objects that can have an added at date. """

    def editAddedAt(self, addedAt, locked=True):
        """ Edit the added at date.

            Parameters:
                addedAt (int or str or datetime): The new value as a unix timestamp (int),
                    "YYYY-MM-DD" (str), or datetime object.
                locked (bool): True (default) to lock the field, False to unlock the field.
        """
        if isinstance(addedAt, str):
            addedAt = int(round(datetime.strptime(addedAt, '%Y-%m-%d').timestamp()))
        elif isinstance(addedAt, datetime):
            addedAt = int(round(addedAt.timestamp()))
        return self.editField('addedAt', addedAt, locked=locked)


class AudienceRatingMixin(EditFieldMixin):
    """ Mixin for Plex objects that can have an audience rating. """

    def editAudienceRating(self, audienceRating, locked=True):
        """ Edit the audience rating.

            Parameters:
                audienceRating (float): The new value.
                locked (bool): True (default) to lock the field, False to unlock the field.
        """
        return self.editField('audienceRating', audienceRating, locked=locked)


class ContentRatingMixin(EditFieldMixin):
    """ Mixin for Plex objects that can have a content rating. """

    def editContentRating(self, contentRating, locked=True):
        """ Edit the content rating.

            Parameters:
                contentRating (str): The new value.
                locked (bool): True (default) to lock the field, False to unlock the field.
        """
        return self.editField('contentRating', contentRating, locked=locked)


class CriticRatingMixin(EditFieldMixin):
    """ Mixin for Plex objects that can have a critic rating. """

    def editCriticRating(self, criticRating, locked=True):
        """ Edit the critic rating.

            Parameters:
                criticRating (float): The new value.
                locked (bool): True (default) to lock the field, False to unlock the field.
        """
        return self.editField('rating', criticRating, locked=locked)


class EditionTitleMixin(EditFieldMixin):
    """ Mixin for Plex objects that can have an edition title. """

    def editEditionTitle(self, editionTitle, locked=True):
        """ Edit the edition title. Plex Pass is required to edit this field.

            Parameters:
                editionTitle (str): The new value.
                locked (bool): True (default) to lock the field, False to unlock the field.
        """
        return self.editField('editionTitle', editionTitle, locked=locked)


class OriginallyAvailableMixin(EditFieldMixin):
    """ Mixin for Plex objects that can have an originally available date. """

    def editOriginallyAvailable(self, originallyAvailable, locked=True):
        """ Edit the originally available date.

            Parameters:
                originallyAvailable (str or datetime): The new value "YYYY-MM-DD (str) or datetime object.
                locked (bool): True (default) to lock the field, False to unlock the field.
        """
        if isinstance(originallyAvailable, datetime):
            originallyAvailable = originallyAvailable.strftime('%Y-%m-%d')
        return self.editField('originallyAvailableAt', originallyAvailable, locked=locked)


class OriginalTitleMixin(EditFieldMixin):
    """ Mixin for Plex objects that can have an original title. """

    def editOriginalTitle(self, originalTitle, locked=True):
        """ Edit the original title.

            Parameters:
                originalTitle (str): The new value.
                locked (bool): True (default) to lock the field, False to unlock the field.
        """
        return self.editField('originalTitle', originalTitle, locked=locked)


class SortTitleMixin(EditFieldMixin):
    """ Mixin for Plex objects that can have a sort title. """

    def editSortTitle(self, sortTitle, locked=True):
        """ Edit the sort title.

            Parameters:
                sortTitle (str): The new value.
                locked (bool): True (default) to lock the field, False to unlock the field.
        """
        return self.editField('titleSort', sortTitle, locked=locked)


class StudioMixin(EditFieldMixin):
    """ Mixin for Plex objects that can have a studio. """

    def editStudio(self, studio, locked=True):
        """ Edit the studio.

            Parameters:
                studio (str): The new value.
                locked (bool): True (default) to lock the field, False to unlock the field.
        """
        return self.editField('studio', studio, locked=locked)


class SummaryMixin(EditFieldMixin):
    """ Mixin for Plex objects that can have a summary. """

    def editSummary(self, summary, locked=True):
        """ Edit the summary.

            Parameters:
                summary (str): The new value.
                locked (bool): True (default) to lock the field, False to unlock the field.
        """
        return self.editField('summary', summary, locked=locked)


class TaglineMixin(EditFieldMixin):
    """ Mixin for Plex objects that can have a tagline. """

    def editTagline(self, tagline, locked=True):
        """ Edit the tagline.

            Parameters:
                tagline (str): The new value.
                locked (bool): True (default) to lock the field, False to unlock the field.
        """
        return self.editField('tagline', tagline, locked=locked)


class TitleMixin(EditFieldMixin):
    """ Mixin for Plex objects that can have a title. """

    def editTitle(self, title, locked=True):
        """ Edit the title.

            Parameters:
                title (str): The new value.
                locked (bool): True (default) to lock the field, False to unlock the field.
        """
        kwargs = {}
        if self.TYPE == 'album':
            # Editing album title also requires the artist ratingKey
            kwargs['artist.id.value'] = self.parentRatingKey
        return self.editField('title', title, locked=locked, **kwargs)


class TrackArtistMixin(EditFieldMixin):
    """ Mixin for Plex objects that can have a track artist. """

    def editTrackArtist(self, trackArtist, locked=True):
        """ Edit the track artist.

            Parameters:
                trackArtist (str): The new value.
                locked (bool): True (default) to lock the field, False to unlock the field.
        """
        return self.editField('originalTitle', trackArtist, locked=locked)


class TrackNumberMixin(EditFieldMixin):
    """ Mixin for Plex objects that can have a track number. """

    def editTrackNumber(self, trackNumber, locked=True):
        """ Edit the track number.

            Parameters:
                trackNumber (int): The new value.
                locked (bool): True (default) to lock the field, False to unlock the field.
        """
        return self.editField('index', trackNumber, locked=locked)


class TrackDiscNumberMixin(EditFieldMixin):
    """ Mixin for Plex objects that can have a track disc number. """

    def editDiscNumber(self, discNumber, locked=True):
        """ Edit the track disc number.

            Parameters:
                discNumber (int): The new value.
                locked (bool): True (default) to lock the field, False to unlock the field.
        """
        return self.editField('parentIndex', discNumber, locked=locked)


class PhotoCapturedTimeMixin(EditFieldMixin):
    """ Mixin for Plex objects that can have a captured time. """

    def editCapturedTime(self, capturedTime, locked=True):
        """ Edit the photo captured time.

            Parameters:
                capturedTime (str or datetime): The new value "YYYY-MM-DD hh:mm:ss" (str) or datetime object.
                locked (bool): True (default) to lock the field, False to unlock the field.
        """
        if isinstance(capturedTime, datetime):
            capturedTime = capturedTime.strftime('%Y-%m-%d %H:%M:%S')
        return self.editField('originallyAvailableAt', capturedTime, locked=locked)


class UserRatingMixin(EditFieldMixin):
    """ Mixin for Plex objects that can have a user rating. """

    def editUserRating(self, userRating, locked=True):
        """ Edit the user rating.

            Parameters:
                userRating (float): The new value.
                locked (bool): True (default) to lock the field, False to unlock the field.
        """
        return self.editField('userRating', userRating, locked=locked)


class EditTagsMixin:
    """ Mixin for editing Plex object tags. """

    def editTags(self, tag, items, locked=True, remove=False, **kwargs):
        """ Edit the tags of a Plex object. All tag editing methods can be chained together.
            Also see :func:`~plexapi.base.PlexPartialObject.batchEdits` for batch editing tags.

            Parameters:
                tag (str): Name of the tag to edit.
                items (List<str> or List<:class:`~plexapi.media.MediaTag`>): List of tags to add or remove.
                locked (bool): True (default) to lock the tags, False to unlock the tags.
                remove (bool): True to remove the tags in items.

            Example:

                .. code-block:: python

                    # Chaining multiple tag edits with reloading
                    Show.addCollection('New Collection').removeGenre('Action').addLabel('Favorite').reload()

        """
        if not isinstance(items, list):
            items = [items]

        if not remove:
            tags = getattr(self, self._tagPlural(tag), [])
            if isinstance(tags, list):
                items = tags + items

        edits = self._tagHelper(self._tagSingular(tag), items, locked, remove)
        edits.update(kwargs)
        return self._edit(**edits)

    @staticmethod
    def _tagSingular(tag):
        """ Return the singular name of a tag. """
        if tag == 'countries':
            return 'country'
        elif tag == 'similar':
            return 'similar'
        elif tag[-1] == 's':
            return tag[:-1]
        return tag

    @staticmethod
    def _tagPlural(tag):
        """ Return the plural name of a tag. """
        if tag == 'country':
            return 'countries'
        elif tag == 'similar':
            return 'similar'
        elif tag[-1] != 's':
            return tag + 's'
        return tag

    @staticmethod
    def _tagHelper(tag, items, locked=True, remove=False):
        """ Return a dict of the query parameters for editing a tag. """
        if not isinstance(items, list):
            items = [items]

        data = {
            f'{tag}.locked': 1 if locked else 0
        }

        if remove:
            tagname = f'{tag}[].tag.tag-'
            data[tagname] = ','.join(quote(str(t)) for t in items)
        else:
            for i, item in enumerate(items):
                tagname = f'{str(tag)}[{i}].tag.tag'
                data[tagname] = item

        return data


class CollectionMixin(EditTagsMixin):
    """ Mixin for Plex objects that can have collections. """

    def addCollection(self, collections, locked=True):
        """ Add a collection tag(s).

            Parameters:
                collections (List<str> or List<:class:`~plexapi.media.MediaTag`>): List of tags.
                locked (bool): True (default) to lock the field, False to unlock the field.
        """
        return self.editTags('collection', collections, locked=locked)

    def removeCollection(self, collections, locked=True):
        """ Remove a collection tag(s).

            Parameters:
                collections (List<str> or List<:class:`~plexapi.media.MediaTag`>): List of tags.
                locked (bool): True (default) to lock the field, False to unlock the field.
        """
        return self.editTags('collection', collections, locked=locked, remove=True)


class CountryMixin(EditTagsMixin):
    """ Mixin for Plex objects that can have countries. """

    def addCountry(self, countries, locked=True):
        """ Add a country tag(s).

            Parameters:
                countries (List<str> or List<:class:`~plexapi.media.MediaTag`>): List of tags.
                locked (bool): True (default) to lock the field, False to unlock the field.
        """
        return self.editTags('country', countries, locked=locked)

    def removeCountry(self, countries, locked=True):
        """ Remove a country tag(s).

            Parameters:
                countries (List<str> or List<:class:`~plexapi.media.MediaTag`>): List of tags.
                locked (bool): True (default) to lock the field, False to unlock the field.
        """
        return self.editTags('country', countries, locked=locked, remove=True)


class DirectorMixin(EditTagsMixin):
    """ Mixin for Plex objects that can have directors. """

    def addDirector(self, directors, locked=True):
        """ Add a director tag(s).

            Parameters:
                directors (List<str> or List<:class:`~plexapi.media.MediaTag`>): List of tags.
                locked (bool): True (default) to lock the field, False to unlock the field.
        """
        return self.editTags('director', directors, locked=locked)

    def removeDirector(self, directors, locked=True):
        """ Remove a director tag(s).

            Parameters:
                directors (List<str> or List<:class:`~plexapi.media.MediaTag`>): List of tags.
                locked (bool): True (default) to lock the field, False to unlock the field.
        """
        return self.editTags('director', directors, locked=locked, remove=True)


class GenreMixin(EditTagsMixin):
    """ Mixin for Plex objects that can have genres. """

    def addGenre(self, genres, locked=True):
        """ Add a genre tag(s).

            Parameters:
                genres (List<str> or List<:class:`~plexapi.media.MediaTag`>): List of tags.
                locked (bool): True (default) to lock the field, False to unlock the field.
        """
        return self.editTags('genre', genres, locked=locked)

    def removeGenre(self, genres, locked=True):
        """ Remove a genre tag(s).

            Parameters:
                genres (List<str> or List<:class:`~plexapi.media.MediaTag`>): List of tags.
                locked (bool): True (default) to lock the field, False to unlock the field.
        """
        return self.editTags('genre', genres, locked=locked, remove=True)


class LabelMixin(EditTagsMixin):
    """ Mixin for Plex objects that can have labels. """

    def addLabel(self, labels, locked=True):
        """ Add a label tag(s).

            Parameters:
                labels (List<str> or List<:class:`~plexapi.media.MediaTag`>): List of tags.
                locked (bool): True (default) to lock the field, False to unlock the field.
        """
        return self.editTags('label', labels, locked=locked)

    def removeLabel(self, labels, locked=True):
        """ Remove a label tag(s).

            Parameters:
                labels (List<str> or List<:class:`~plexapi.media.MediaTag`>): List of tags.
                locked (bool): True (default) to lock the field, False to unlock the field.
        """
        return self.editTags('label', labels, locked=locked, remove=True)


class MoodMixin(EditTagsMixin):
    """ Mixin for Plex objects that can have moods. """

    def addMood(self, moods, locked=True):
        """ Add a mood tag(s).

            Parameters:
                moods (List<str> or List<:class:`~plexapi.media.MediaTag`>): List of tags.
                locked (bool): True (default) to lock the field, False to unlock the field.
        """
        return self.editTags('mood', moods, locked=locked)

    def removeMood(self, moods, locked=True):
        """ Remove a mood tag(s).

            Parameters:
                moods (List<str> or List<:class:`~plexapi.media.MediaTag`>): List of tags.
                locked (bool): True (default) to lock the field, False to unlock the field.
        """
        return self.editTags('mood', moods, locked=locked, remove=True)


class ProducerMixin(EditTagsMixin):
    """ Mixin for Plex objects that can have producers. """

    def addProducer(self, producers, locked=True):
        """ Add a producer tag(s).

            Parameters:
                producers (List<str> or List<:class:`~plexapi.media.MediaTag`>): List of tags.
                locked (bool): True (default) to lock the field, False to unlock the field.
        """
        return self.editTags('producer', producers, locked=locked)

    def removeProducer(self, producers, locked=True):
        """ Remove a producer tag(s).

            Parameters:
                producers (List<str> or List<:class:`~plexapi.media.MediaTag`>): List of tags.
                locked (bool): True (default) to lock the field, False to unlock the field.
        """
        return self.editTags('producer', producers, locked=locked, remove=True)


class SimilarArtistMixin(EditTagsMixin):
    """ Mixin for Plex objects that can have similar artists. """

    def addSimilarArtist(self, artists, locked=True):
        """ Add a similar artist tag(s).

            Parameters:
                artists (List<str> or List<:class:`~plexapi.media.MediaTag`>): List of tags.
                locked (bool): True (default) to lock the field, False to unlock the field.
        """
        return self.editTags('similar', artists, locked=locked)

    def removeSimilarArtist(self, artists, locked=True):
        """ Remove a similar artist tag(s).

            Parameters:
                artists (List<str> or List<:class:`~plexapi.media.MediaTag`>): List of tags.
                locked (bool): True (default) to lock the field, False to unlock the field.
        """
        return self.editTags('similar', artists, locked=locked, remove=True)


class StyleMixin(EditTagsMixin):
    """ Mixin for Plex objects that can have styles. """

    def addStyle(self, styles, locked=True):
        """ Add a style tag(s).

            Parameters:
                styles (List<str> or List<:class:`~plexapi.media.MediaTag`>): List of tags.
                locked (bool): True (default) to lock the field, False to unlock the field.
        """
        return self.editTags('style', styles, locked=locked)

    def removeStyle(self, styles, locked=True):
        """ Remove a style tag(s).

            Parameters:
                styles (List<str> or List<:class:`~plexapi.media.MediaTag`>): List of tags.
                locked (bool): True (default) to lock the field, False to unlock the field.
        """
        return self.editTags('style', styles, locked=locked, remove=True)


class TagMixin(EditTagsMixin):
    """ Mixin for Plex objects that can have tags. """

    def addTag(self, tags, locked=True):
        """ Add a tag(s).

            Parameters:
                tags (List<str> or List<:class:`~plexapi.media.MediaTag`>): List of tags.
                locked (bool): True (default) to lock the field, False to unlock the field.
        """
        return self.editTags('tag', tags, locked=locked)

    def removeTag(self, tags, locked=True):
        """ Remove a tag(s).

            Parameters:
                tags (List<str> or List<:class:`~plexapi.media.MediaTag`>): List of tags.
                locked (bool): True (default) to lock the field, False to unlock the field.
        """
        return self.editTags('tag', tags, locked=locked, remove=True)


class WriterMixin(EditTagsMixin):
    """ Mixin for Plex objects that can have writers. """

    def addWriter(self, writers, locked=True):
        """ Add a writer tag(s).

            Parameters:
                writers (List<str> or List<:class:`~plexapi.media.MediaTag`>): List of tags.
                locked (bool): True (default) to lock the field, False to unlock the field.
        """
        return self.editTags('writer', writers, locked=locked)

    def removeWriter(self, writers, locked=True):
        """ Remove a writer tag(s).

            Parameters:
                writers (List<str> or List<:class:`~plexapi.media.MediaTag`>): List of tags.
                locked (bool): True (default) to lock the field, False to unlock the field.
        """
        return self.editTags('writer', writers, locked=locked, remove=True)
