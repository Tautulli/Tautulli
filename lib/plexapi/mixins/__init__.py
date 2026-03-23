"""
PlexAPI Mixins Module

This module contains mixins for Plex objects.
"""

from .advanced_settings import AdvancedSettingsMixin
from .edit import (
    AddedAtMixin, AudienceRatingMixin, CollectionMixin, ContentRatingMixin,
    CountryMixin, CriticRatingMixin, DirectorMixin, EditionTitleMixin,
    EditFieldMixin, EditTagsMixin, GenreMixin, LabelMixin, MoodMixin,
    OriginallyAvailableMixin, OriginalTitleMixin, PhotoCapturedTimeMixin,
    ProducerMixin, SimilarArtistMixin, SortTitleMixin, StudioMixin,
    StyleMixin, SummaryMixin, TaglineMixin, TagMixin, TitleMixin,
    TrackArtistMixin, TrackDiscNumberMixin, TrackNumberMixin,
    UserRatingMixin, WriterMixin
)
from .objects import ExtrasMixin, HubsMixin
from .played_unplayed import PlayedUnplayedMixin
from .rating import RatingMixin
from .resources import (
    ArtLockMixin, ArtMixin, ArtUrlMixin,
    LogoLockMixin, LogoMixin, LogoUrlMixin,
    PosterLockMixin, PosterMixin, PosterUrlMixin,
    SquareArtLockMixin, SquareArtMixin, SquareArtUrlMixin,
    ThemeLockMixin, ThemeMixin, ThemeUrlMixin
)
from .smart_filter import SmartFilterMixin
from .split_merge import SplitMergeMixin
from .unmatch_match import UnmatchMatchMixin
from .watchlist import WatchlistMixin


class MovieEditMixins(
    ArtLockMixin, PosterLockMixin, ThemeLockMixin,
    AddedAtMixin, AudienceRatingMixin, ContentRatingMixin, CriticRatingMixin, EditionTitleMixin,
    OriginallyAvailableMixin, OriginalTitleMixin, SortTitleMixin,
    StudioMixin, SummaryMixin, TaglineMixin, TitleMixin, UserRatingMixin,
    CollectionMixin, CountryMixin, DirectorMixin, GenreMixin, LabelMixin, ProducerMixin, WriterMixin
):
    pass


class ShowEditMixins(
    ArtLockMixin, PosterLockMixin, ThemeLockMixin,
    AddedAtMixin, AudienceRatingMixin, ContentRatingMixin, CriticRatingMixin,
    OriginallyAvailableMixin, OriginalTitleMixin, SortTitleMixin, StudioMixin,
    SummaryMixin, TaglineMixin, TitleMixin, UserRatingMixin,
    CollectionMixin, GenreMixin, LabelMixin,
):
    pass


class SeasonEditMixins(
    ArtLockMixin, PosterLockMixin, ThemeLockMixin,
    AddedAtMixin, AudienceRatingMixin, CriticRatingMixin,
    SummaryMixin, TitleMixin, UserRatingMixin,
    CollectionMixin, LabelMixin
):
    pass


class EpisodeEditMixins(
    ArtLockMixin, PosterLockMixin, ThemeLockMixin,
    AddedAtMixin, AudienceRatingMixin, ContentRatingMixin, CriticRatingMixin,
    OriginallyAvailableMixin, SortTitleMixin, SummaryMixin, TitleMixin, UserRatingMixin,
    CollectionMixin, DirectorMixin, LabelMixin, WriterMixin
):
    pass


class ArtistEditMixins(
    ArtLockMixin, PosterLockMixin, ThemeLockMixin,
    AddedAtMixin, AudienceRatingMixin, CriticRatingMixin,
    SortTitleMixin, SummaryMixin, TitleMixin, UserRatingMixin,
    CollectionMixin, CountryMixin, GenreMixin, LabelMixin, MoodMixin, SimilarArtistMixin, StyleMixin
):
    pass


class AlbumEditMixins(
    ArtLockMixin, PosterLockMixin, ThemeLockMixin,
    AddedAtMixin, AudienceRatingMixin, CriticRatingMixin,
    OriginallyAvailableMixin, SortTitleMixin, StudioMixin, SummaryMixin, TitleMixin, UserRatingMixin,
    CollectionMixin, GenreMixin, LabelMixin, MoodMixin, StyleMixin
):
    pass


class TrackEditMixins(
    ArtLockMixin, PosterLockMixin, ThemeLockMixin,
    AddedAtMixin, AudienceRatingMixin, CriticRatingMixin,
    TitleMixin, TrackArtistMixin, TrackNumberMixin, TrackDiscNumberMixin, UserRatingMixin,
    CollectionMixin, GenreMixin, LabelMixin, MoodMixin
):
    pass


class PhotoalbumEditMixins(
    ArtLockMixin, PosterLockMixin,
    AddedAtMixin, SortTitleMixin, SummaryMixin, TitleMixin, UserRatingMixin
):
    pass


class PhotoEditMixins(
    ArtLockMixin, PosterLockMixin,
    AddedAtMixin, PhotoCapturedTimeMixin, SortTitleMixin, SummaryMixin, TitleMixin, UserRatingMixin,
    TagMixin
):
    pass


class CollectionEditMixins(
    ArtLockMixin, PosterLockMixin, ThemeLockMixin,
    AddedAtMixin, AudienceRatingMixin, ContentRatingMixin, CriticRatingMixin,
    SortTitleMixin, SummaryMixin, TitleMixin, UserRatingMixin,
    LabelMixin
):
    pass


class PlaylistEditMixins(
    ArtLockMixin, PosterLockMixin,
    SortTitleMixin, SummaryMixin, TitleMixin
):
    pass


class MovieMixins(
    AdvancedSettingsMixin, SplitMergeMixin, UnmatchMatchMixin, ExtrasMixin, HubsMixin, RatingMixin,
    ArtMixin, LogoMixin, PosterMixin, SquareArtMixin, ThemeMixin,
    MovieEditMixins,
    WatchlistMixin
):
    pass


class ShowMixins(
    AdvancedSettingsMixin, SplitMergeMixin, UnmatchMatchMixin, ExtrasMixin, HubsMixin, RatingMixin,
    ArtMixin, LogoMixin, PosterMixin, SquareArtMixin, ThemeMixin,
    ShowEditMixins,
    WatchlistMixin
):
    pass


class SeasonMixins(
    AdvancedSettingsMixin, ExtrasMixin, RatingMixin,
    ArtMixin, LogoMixin, PosterMixin, SquareArtMixin, ThemeUrlMixin,
    SeasonEditMixins
):
    pass


class EpisodeMixins(
    ExtrasMixin, RatingMixin,
    ArtMixin, LogoMixin, PosterMixin, SquareArtMixin, ThemeUrlMixin,
    EpisodeEditMixins
):
    pass


class ClipMixins(
    ArtUrlMixin, LogoUrlMixin, PosterUrlMixin, SquareArtUrlMixin
):
    pass


class ArtistMixins(
    AdvancedSettingsMixin, SplitMergeMixin, UnmatchMatchMixin, ExtrasMixin, HubsMixin, RatingMixin,
    ArtMixin, LogoMixin, PosterMixin, SquareArtMixin, ThemeMixin,
    ArtistEditMixins
):
    pass


class AlbumMixins(
    SplitMergeMixin, UnmatchMatchMixin, RatingMixin,
    ArtMixin, LogoMixin, PosterMixin, SquareArtMixin, ThemeUrlMixin,
    AlbumEditMixins
):
    pass


class TrackMixins(
    ExtrasMixin, RatingMixin,
    ArtUrlMixin, LogoUrlMixin, PosterUrlMixin, SquareArtUrlMixin, ThemeUrlMixin,
    TrackEditMixins
):
    pass


class PhotoalbumMixins(
    RatingMixin,
    ArtMixin, LogoMixin, PosterMixin, SquareArtMixin,
    PhotoalbumEditMixins
):
    pass


class PhotoMixins(
    RatingMixin,
    ArtUrlMixin, LogoUrlMixin, PosterUrlMixin, SquareArtUrlMixin,
    PhotoEditMixins
):
    pass


class CollectionMixins(
    AdvancedSettingsMixin, SmartFilterMixin, HubsMixin, RatingMixin,
    ArtMixin, LogoMixin, PosterMixin, SquareArtMixin, ThemeMixin,
    CollectionEditMixins
):
    pass


class PlaylistMixins(
    SmartFilterMixin,
    ArtMixin, LogoMixin, PosterMixin, SquareArtMixin,
    PlaylistEditMixins
):
    pass


__all__ = [
    # Advanced settings
    'AdvancedSettingsMixin',
    # Edit mixins
    'AddedAtMixin', 'AudienceRatingMixin', 'CollectionMixin', 'ContentRatingMixin',
    'CountryMixin', 'CriticRatingMixin', 'DirectorMixin', 'EditionTitleMixin',
    'EditFieldMixin', 'EditTagsMixin', 'GenreMixin', 'LabelMixin', 'MoodMixin',
    'OriginallyAvailableMixin', 'OriginalTitleMixin', 'PhotoCapturedTimeMixin',
    'ProducerMixin', 'SimilarArtistMixin', 'SortTitleMixin', 'StudioMixin',
    'StyleMixin', 'SummaryMixin', 'TaglineMixin', 'TagMixin', 'TitleMixin',
    'TrackArtistMixin', 'TrackDiscNumberMixin', 'TrackNumberMixin',
    'UserRatingMixin', 'WriterMixin',
    # Objects
    'ExtrasMixin', 'HubsMixin',
    # Played/Unplayed
    'PlayedUnplayedMixin',
    # Rating
    'RatingMixin',
    # Resource mixins
    'ArtLockMixin', 'ArtMixin', 'ArtUrlMixin',
    'LogoLockMixin', 'LogoMixin', 'LogoUrlMixin',
    'PosterLockMixin', 'PosterMixin', 'PosterUrlMixin',
    'SquareArtLockMixin', 'SquareArtMixin', 'SquareArtUrlMixin',
    'ThemeLockMixin', 'ThemeMixin', 'ThemeUrlMixin',
    # Smart Filter
    'SmartFilterMixin',
    # Split/Merge
    'SplitMergeMixin',
    # Unmatch/Match
    'UnmatchMatchMixin',
    # Watchlist
    'WatchlistMixin',
    # Composite Edit Mixins
    'AlbumEditMixins', 'ArtistEditMixins', 'CollectionEditMixins', 'EpisodeEditMixins',
    'MovieEditMixins', 'PhotoEditMixins', 'PhotoalbumEditMixins', 'PlaylistEditMixins',
    'SeasonEditMixins', 'ShowEditMixins', 'TrackEditMixins',
    # Composite Mixins
    'AlbumMixins', 'ArtistMixins', 'ClipMixins', 'CollectionMixins', 'EpisodeMixins',
    'MovieMixins', 'PhotoMixins', 'PhotoalbumMixins', 'PlaylistMixins',
    'SeasonMixins', 'ShowMixins', 'TrackMixins',
]
