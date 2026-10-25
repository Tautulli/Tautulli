import pytest

from plexpy.helpers import check_watched


# media_type -> the config attribute that sets its watched-percent threshold.
# 'clip' (trailers/extras) shares the TV setting, same as the real lookup
# table inside check_watched.
MEDIA_TYPE_CONFIG_ATTR = [
    ("movie", "MOVIE_WATCHED_PERCENT"),
    ("episode", "TV_WATCHED_PERCENT"),
    ("track", "MUSIC_WATCHED_PERCENT"),
    ("clip", "TV_WATCHED_PERCENT"),
]


@pytest.mark.parametrize("media_type,config_attr", MEDIA_TYPE_CONFIG_ATTR)
@pytest.mark.parametrize("view_offset,expected", [(499, False), (500, True)])
def test_percent_threshold_per_media_type(app_config, media_type, config_attr, view_offset, expected):
    # WATCHED_MARKER defaults to 3 (earliest of percent/first-marker), and no
    # marker is passed here, so this exercises the plain percent threshold.
    setattr(app_config, config_attr, 50)
    assert check_watched(media_type, view_offset, 1000) is expected


def test_unrecognized_media_type_is_never_watched(app_config):
    # e.g. a 'photo' library item: not in the watched_percent map, so the
    # threshold is 0 and check_watched bails out regardless of position.
    app_config.MOVIE_WATCHED_PERCENT = 50
    assert check_watched("photo", 1000, 1000) is False


@pytest.mark.parametrize("duration", [0, None])
def test_zero_or_missing_duration_is_never_watched(app_config, duration):
    app_config.MOVIE_WATCHED_PERCENT = 50
    assert check_watched("movie", 1000, duration) is False


def test_watched_marker_mode_1_uses_credits_final_marker(app_config):
    app_config.WATCHED_MARKER = 1
    app_config.MOVIE_WATCHED_PERCENT = 50  # percent threshold (500000) well below the marker
    assert check_watched("movie", 179999, 1000000, marker_credits_final=180000) is False
    assert check_watched("movie", 180000, 1000000, marker_credits_final=180000) is True


def test_watched_marker_mode_1_accepts_marker_dict(app_config):
    # activity_processor/datafactory pass markers as the raw Plex marker
    # dict, keyed by 'start_time_offset'; check_watched must unwrap it.
    app_config.WATCHED_MARKER = 1
    app_config.MOVIE_WATCHED_PERCENT = 50
    marker = {"start_time_offset": 180000}
    assert check_watched("movie", 179999, 1000000, marker_credits_final=marker) is False
    assert check_watched("movie", 180000, 1000000, marker_credits_final=marker) is True


def test_watched_marker_mode_1_falls_back_to_percent_without_marker(app_config):
    app_config.WATCHED_MARKER = 1
    app_config.MOVIE_WATCHED_PERCENT = 50
    assert check_watched("movie", 499, 1000, marker_credits_final=None) is False
    assert check_watched("movie", 500, 1000, marker_credits_final=None) is True


def test_watched_marker_mode_2_uses_credits_first_marker(app_config):
    app_config.WATCHED_MARKER = 2
    app_config.MOVIE_WATCHED_PERCENT = 50
    assert check_watched("movie", 179999, 1000000, marker_credits_first=180000) is False
    assert check_watched("movie", 180000, 1000000, marker_credits_first=180000) is True


def test_watched_marker_mode_2_falls_back_to_percent_without_marker(app_config):
    app_config.WATCHED_MARKER = 2
    app_config.MOVIE_WATCHED_PERCENT = 50
    assert check_watched("movie", 499, 1000, marker_credits_first=None) is False
    assert check_watched("movie", 500, 1000, marker_credits_first=None) is True


def test_watched_marker_mode_3_stops_at_earlier_of_threshold_and_first_marker(app_config):
    app_config.WATCHED_MARKER = 3
    app_config.MOVIE_WATCHED_PERCENT = 50  # threshold = 500

    # Marker earlier than the percent threshold: marker wins.
    assert check_watched("movie", 299, 1000, marker_credits_first=300) is False
    assert check_watched("movie", 300, 1000, marker_credits_first=300) is True

    # Marker later than the percent threshold: threshold wins.
    assert check_watched("movie", 499, 1000, marker_credits_first=700) is False
    assert check_watched("movie", 500, 1000, marker_credits_first=700) is True


def test_watched_marker_mode_3_falls_back_to_percent_without_marker(app_config):
    app_config.WATCHED_MARKER = 3
    app_config.MOVIE_WATCHED_PERCENT = 50
    assert check_watched("movie", 499, 1000, marker_credits_first=None) is False
    assert check_watched("movie", 500, 1000, marker_credits_first=None) is True


def test_watched_marker_mode_0_ignores_markers(app_config):
    # 0 = "At selected threshold percentage" in the settings UI: markers are
    # ignored even when present.
    app_config.WATCHED_MARKER = 0
    app_config.MOVIE_WATCHED_PERCENT = 50
    assert check_watched("movie", 499, 1000, marker_credits_first=1, marker_credits_final=1) is False
    assert check_watched("movie", 500, 1000, marker_credits_first=1, marker_credits_final=1) is True
