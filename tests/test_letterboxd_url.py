"""Notification parameters carry a Letterboxd URL.

Letterboxd lists movies only. The URL is blank for TV items. The Letterboxd
provider also has a name and a link in PrettyMetadata.
"""

from unittest.mock import MagicMock

import pytest

from plexpy import notification_handler
from plexpy.notifiers import PrettyMetadata


def build(monkeypatch, **metadata):
    metadata.setdefault("rating_key", "1")
    pms = MagicMock()
    activity = MagicMock()
    activity.return_value.get_sessions.return_value = []
    monkeypatch.setattr(notification_handler.pmsconnect, "PmsConnect", pms)
    monkeypatch.setattr(notification_handler.activity_processor, "ActivityProcessor", activity)
    monkeypatch.setattr(notification_handler.helpers, "get_img_service", lambda *args, **kwargs: "")
    monkeypatch.setattr(notification_handler.helpers, "pms_name", lambda: "Server")
    return notification_handler.build_media_notify_params(
        notify_action="on_created", timeline=metadata)


@pytest.mark.parametrize("metadata, expected", [
    ({"media_type": "movie", "guid": "imdb://tt0133093"},
     "https://letterboxd.com/imdb/tt0133093"),
    ({"media_type": "movie", "guid": "themoviedb://603"},
     "https://letterboxd.com/tmdb/603"),
    ({"media_type": "episode", "guid": "imdb://tt0903747"}, ""),
])
def test_letterboxd_url(app_config, monkeypatch, metadata, expected):
    assert build(monkeypatch, **metadata)["letterboxd_url"] == expected


def test_letterboxd_provider_name_and_link():
    pretty = PrettyMetadata({"letterboxd_url": "https://letterboxd.com/tmdb/603"})

    assert pretty.get_provider_name("letterboxd") == "Letterboxd"
    assert pretty.get_provider_link("letterboxd") == "https://letterboxd.com/tmdb/603"


@pytest.mark.parametrize("media_type, expected", [
    ("movie", "https://letterboxd.com/tmdb/603"),
    ("episode", ""),
])
def test_letterboxd_url_from_tmdb_lookup(app_config, monkeypatch, media_type, expected):
    app_config.THEMOVIEDB_LOOKUP = 1
    monkeypatch.setattr(notification_handler, "lookup_themoviedb_by_id", lambda **kw: {"themoviedb_id": 603})

    assert build(monkeypatch, media_type=media_type, guid="plex://x/1")["letterboxd_url"] == expected


def test_letterboxd_is_a_movie_provider_only():
    assert PrettyMetadata.get_movie_providers()["letterboxd"] == "Letterboxd"
    assert "letterboxd" not in PrettyMetadata.get_tv_providers()
