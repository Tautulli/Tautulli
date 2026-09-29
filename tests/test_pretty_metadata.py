from unittest.mock import MagicMock

import pytest

from plexpy import notification_handler
from plexpy.notifiers import PrettyMetadata


# PrettyMetadata.get_title builds the card title for Discord, Slack, Teams, and
# LunaSea. A grouped recently added notification carries the added season,
# episode, or track numbers in the existing *_num and *_count parameters.

# The parameter prefix that holds the grouped range for each media type.
RANGE_KEY = {"show": "season", "season": "episode", "album": "track"}

BASE_TITLE = {
    "show": "Lanterns (2026)",
    "season": "Lanterns - Season 1",
    "album": "An Artist - An Album",
}


def params(media_type, **overrides):
    parameters = {
        "media_type": media_type, "action": "created", "title": "A Movie",
        "year": 2026, "show_name": "Lanterns", "season_name": "Season 1",
        "episode_name": "Pilot", "episode_num": "7", "episode_count": 1,
        "season_num": "1", "season_count": 1, "artist_name": "An Artist",
        "album_name": "An Album", "track_name": "A Track",
        "track_artist": "An Artist", "track_num": "7", "track_count": 1,
    }
    for key, value in overrides.items():
        if value is None:
            parameters.pop(key)
        else:
            parameters[key] = value
    return parameters


def title(parameters, divider="-"):
    # Every notifier gets the same parameters dict, so get_title must not change it.
    original = dict(parameters)
    result = PrettyMetadata(parameters).get_title(divider)
    assert parameters == original
    return result


@pytest.mark.parametrize("media_type, numbers, count, expected", [
    ("show", "1-3,5", 4, "Lanterns (2026) - Seasons 1-3,5"),
    ("show", "2", 1, "Lanterns (2026) - Season 2"),
    ("show", "0", 1, "Lanterns (2026) - Season 0"),
    ("season", "2-4,7", 4, "Lanterns - Season 1 - Episodes 2-4,7"),
    ("season", "7", 1, "Lanterns - Season 1 - Episode 7"),
    ("season", "0", 1, "Lanterns - Season 1 - Episode 0"),
    ("album", "2-4,7", 4, "An Artist - An Album - Tracks 2-4,7"),
    ("album", "7", 1, "An Artist - An Album - Track 7"),
    ("album", "0", 1, "An Artist - An Album - Track 0"),
])
def test_grouped_title_appends_range(media_type, numbers, count, expected):
    key = RANGE_KEY[media_type]
    parameters = params(media_type, episode_name="",
                        **{key + "_num": numbers, key + "_count": count})
    assert title(parameters) == expected


# format_group_index returns "0" for an empty list, so the count decides
# whether a range exists. None removes the parameter.
@pytest.mark.parametrize("media_type", ["show", "season", "album"])
@pytest.mark.parametrize("numbers, count", [
    ("0", 0), ("1-2", 0), ("", 2), (None, 2), ("1-2", None),
])
def test_grouped_title_skips_missing_range(media_type, numbers, count):
    key = RANGE_KEY[media_type]
    parameters = params(media_type, episode_name="",
                        **{key + "_num": numbers, key + "_count": count})
    assert title(parameters) == BASE_TITLE[media_type]


# Only a created notification with an empty episode_name is grouped.
@pytest.mark.parametrize("media_type", ["show", "season", "album"])
@pytest.mark.parametrize("overrides", [
    {"episode_name": "", "action": "play"},
    {"episode_name": "", "action": "watched"},
    {"episode_name": "", "action": None},
    {"episode_name": None},
    {"episode_name": "Season 1"},
])
def test_ungrouped_title_has_no_range(media_type, overrides):
    assert title(params(media_type, **overrides)) == BASE_TITLE[media_type]


@pytest.mark.parametrize("media_type, divider, expected", [
    ("movie", "-", "A Movie (2026)"),
    ("episode", "-", "Lanterns - Pilot (S1 - E7)"),
    ("episode", "·", "Lanterns - Pilot (S1 · E7)"),
    ("artist", "-", "An Artist"),
    ("track", "-", "A Track - An Artist"),
])
def test_other_media_titles_are_unchanged(media_type, divider, expected):
    assert title(params(media_type), divider) == expected


@pytest.mark.parametrize("grouping", [False, True])
@pytest.mark.parametrize("media_type, item_title, parent_title, suffix", [
    ("show", "Lanterns", "", " - Seasons 2,4"),
    ("season", "Season 1", "Lanterns", " - Episodes 2,4"),
    ("album", "An Album", "An Artist", " - Tracks 2,4"),
])
def test_notify_params_title_follows_grouping(app_config, monkeypatch, grouping,
                                              media_type, item_title,
                                              parent_title, suffix):
    app_config.NOTIFY_GROUP_RECENTLY_ADDED_PARENT = grouping
    app_config.NOTIFY_GROUP_RECENTLY_ADDED_GRANDPARENT = grouping

    metadata = {"rating_key": "parent", "media_type": media_type,
                "title": item_title, "parent_title": parent_title,
                "year": 2026, "media_index": "1"}
    details = {"parent": metadata}
    for number in ("2", "4"):
        details["child-" + number] = {"rating_key": "child-" + number,
                                      "parent_rating_key": "parent",
                                      "media_index": number}
    pms = MagicMock()
    pms.return_value.get_metadata_details.side_effect = (
        lambda rating_key: details.get(rating_key))
    activity = MagicMock()
    activity.return_value.get_sessions.return_value = []
    monkeypatch.setattr(notification_handler.pmsconnect, "PmsConnect", pms)
    monkeypatch.setattr(notification_handler.activity_processor,
                        "ActivityProcessor", activity)
    monkeypatch.setattr(notification_handler.helpers, "get_img_service",
                        lambda *args, **kwargs: "")
    monkeypatch.setattr(notification_handler.helpers, "pms_name", lambda: "Server")

    parameters = notification_handler.build_media_notify_params(
        notify_action="on_created", timeline=metadata,
        child_keys=["child-2", "child-4"])

    # get_title reads an empty episode_name as the grouped marker.
    assert parameters["episode_name"] == ("" if grouping else item_title)
    base = {"show": "{show_name} ({year})",
            "season": "{show_name} - {season_name}",
            "album": "{artist_name} - {album_name}"}[media_type]
    expected = base.format(**parameters) + (suffix if grouping else "")
    assert title(parameters) == expected
