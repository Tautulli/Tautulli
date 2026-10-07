"""The image proxy fetches an http image only when Tautulli stored its URL."""

import pytest

from plexpy import pmsconnect
from plexpy import webserve

IMG = "http://img.invalid/a.png"
OTHER = "http://img.invalid/b.png"
IMAGE = b"image"


@pytest.fixture
def proxy(app_db, app_config, tmp_path, monkeypatch):
    app_config.CACHE_DIR = str(tmp_path)
    app_config.CACHE_IMAGES = 0
    calls = []

    def get_image(self, **kwargs):
        calls.append(kwargs["img"])
        return IMAGE, "image/png"

    monkeypatch.setattr(pmsconnect.PmsConnect, "get_image", get_image)
    return calls


def get(**kwargs):
    return webserve.WebInterface().real_pms_image_proxy(**kwargs)


def history(db, **values):
    db.upsert("session_history_metadata", {"id": 1}, values)


def test_unstored_url_is_not_fetched(proxy, monkeypatch):
    warnings = []
    monkeypatch.setattr(webserve.logger, "warn", lambda *args: warnings.append(args[0]))
    assert get(img=IMG, rating_key="5") is None
    assert warnings == ["Unknown image URL received."]
    assert get(img=IMG) is None
    assert proxy == []


def test_stored_history_url_is_fetched_with_its_rating_key(proxy, app_db):
    history(app_db, rating_key=5, thumb=IMG, parent_rating_key=6, parent_thumb=OTHER,
            grandparent_rating_key=7, grandparent_thumb="http://img.invalid/c.png",
            channel_thumb="http://img.invalid/d.png")
    assert get(img=IMG, rating_key="5") == IMAGE
    assert get(img=OTHER, rating_key="6") == IMAGE
    assert get(img="http://img.invalid/c.png", rating_key="7") == IMAGE
    assert get(img="http://img.invalid/d.png", rating_key="5") == IMAGE
    assert len(proxy) == 4


def test_live_row_url_is_fetched_with_the_item_rating_key(proxy, app_db):
    # Live rows have no parent or grandparent rating key.
    history(app_db, rating_key=5, grandparent_thumb=IMG, parent_thumb=OTHER)
    assert get(img=IMG, rating_key="5") == IMAGE
    assert get(img=OTHER, rating_key="5") == IMAGE


def test_stored_url_with_the_wrong_rating_key_is_rejected(proxy, app_db):
    history(app_db, rating_key=5, thumb=IMG, parent_rating_key=6, parent_thumb=OTHER)
    assert get(img=IMG, rating_key="6") is None
    assert get(img=OTHER, rating_key="7") is None
    assert get(img=IMG) is None
    assert get(img=IMG, rating_key="x") is None
    assert proxy == []


def test_uppercase_scheme_is_checked(proxy):
    assert get(img="HTTP://img.invalid/a.png") is None
    assert proxy == []


def test_stored_history_art_is_fetched(proxy, app_db):
    history(app_db, rating_key=5, art=IMG)
    assert get(img=IMG, rating_key="5") == IMAGE
    assert proxy == [IMG]


def test_session_thumb_columns_are_fetched_with_the_row_rating_key(proxy, app_db):
    for key, col in ((11, "thumb"), (12, "parent_thumb"), (13, "grandparent_thumb")):
        app_db.upsert("sessions", {"session_key": key, "rating_key": key}, {col: IMG + str(key)})
        assert get(img=IMG + str(key), rating_key=str(key)) == IMAGE
    assert len(proxy) == 3


def test_session_url_is_fetched_with_its_rating_key(proxy, app_db):
    app_db.upsert("sessions", {"session_key": 1, "rating_key": 8}, {"channel_thumb": IMG})
    assert get(img=IMG, rating_key="8") == IMAGE
    assert get(img=IMG, rating_key="9") is None
    assert proxy == [IMG]


def test_user_avatar_needs_no_rating_key(proxy, app_db):
    app_db.upsert("users", {"user_id": 1}, {"username": "u", "thumb": IMG, "custom_avatar_url": OTHER})
    assert get(img=IMG) == IMAGE
    assert get(img=OTHER) == IMAGE
    assert proxy == [IMG, OTHER]


def test_library_image_needs_no_rating_key(proxy, app_db):
    app_db.upsert("library_sections", {"server_id": "s", "section_id": 1},
                    {"section_name": "l", "art": IMG, "custom_art_url": OTHER})
    assert get(img=IMG) == IMAGE
    assert get(img=OTHER) == IMAGE


def test_http_fallback_is_not_fetched(proxy, monkeypatch):
    def get_image(self, **kwargs):
        proxy.append(kwargs["img"])
        return None

    monkeypatch.setattr(pmsconnect.PmsConnect, "get_image", get_image)
    assert get(img="/library/metadata/1/thumb", fallback=IMG) is None
    assert proxy == ["/library/metadata/1/thumb"]


def test_unstored_url_with_return_hash_writes_nothing(proxy, app_db):
    assert get(img=IMG, return_hash=True) is None
    assert app_db.select("SELECT * FROM image_hash_lookup") == []


def test_hash_route_serves_an_http_image_stored_in_the_hash_table(proxy, app_db):
    app_db.upsert("image_hash_lookup", {"img_hash": "abc"}, {"img": IMG, "rating_key": None})
    assert webserve.WebInterface().image("abc.png") == IMAGE
    assert proxy == [IMG]


def test_unstored_url_with_a_default_fallback_serves_the_default_image(proxy, monkeypatch):
    monkeypatch.setattr(webserve.plexpy, "PROG_DIR", "/prog")
    served = []
    monkeypatch.setattr(webserve, "serve_file", lambda **kwargs: served.append(kwargs["path"]) or "default")
    assert get(img=IMG, fallback="cover") == "default"
    assert served[0].endswith(webserve.common.DEFAULT_IMAGES["cover"])
    assert get(img=IMG, fallback=OTHER) is None
    assert proxy == []
    assert len(served) == 1


def test_lookup_without_a_rating_key_skips_history_and_sessions(proxy, monkeypatch):
    seen = []
    select_single = webserve.database.MonitorDatabase.select_single

    def spy(self, query, args=None):
        seen.append(query)
        return select_single(self, query, args)

    monkeypatch.setattr(webserve.database.MonitorDatabase, "select_single", spy)
    get(img=IMG)
    get(img=IMG, rating_key="5")
    assert "session_history_metadata" not in seen[0] and "sessions" not in seen[0]
    assert "session_history_metadata" in seen[1] and "sessions" in seen[1]
