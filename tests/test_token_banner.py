"""Every admin page shows a banner while plex.tv rejects the Plex.tv token."""

import re

import pytest

import plexpy
from plexpy import webserve

from tests.test_archive_users import library, seeded, web_pages  # noqa: F401  (fixtures)

BAR = re.compile(r'<div id="token_error_bar"([^>]*)>')


@pytest.fixture
def pages(web_pages, monkeypatch):  # noqa: F811
    monkeypatch.setattr(plexpy, "PLEXTV_BAD_TOKEN", None)
    plexpy.CONFIG.PMS_TOKEN = "tok"
    return web_pages


def bar_style(page):
    match = BAR.search(page)
    return None if match is None else match.group(1)


def test_admin_sees_the_banner_while_the_token_is_flagged(pages, monkeypatch):
    monkeypatch.setattr(plexpy, "PLEXTV_BAD_TOKEN", "tok")
    for page in (pages.home(), pages.users(), pages.history()):
        assert bar_style(page) == ""
        assert "Your Plex.tv token is no longer valid." in page


def test_banner_is_hidden_when_the_token_is_not_flagged(pages):
    assert "display: none" in bar_style(pages.home())


def test_banner_hides_again_after_a_new_token(pages, monkeypatch):
    monkeypatch.setattr(plexpy, "PLEXTV_BAD_TOKEN", "tok")
    plexpy.CONFIG.PMS_TOKEN = "new"
    assert "display: none" in bar_style(pages.home())


def test_guest_gets_no_banner(pages, monkeypatch):
    monkeypatch.setattr(plexpy, "PLEXTV_BAD_TOKEN", "tok")
    monkeypatch.setattr(webserve, "get_session_info",
                        lambda: {"user_id": "9", "user": "guest", "user_group": "guest", "exp": None})
    page = pages.home()
    assert "token_error_bar" not in page
    assert "no longer valid" not in page


def test_link_opens_the_plex_media_server_tab_from_any_page(pages, monkeypatch):
    monkeypatch.setattr(plexpy, "PLEXTV_BAD_TOKEN", "tok")
    page = pages.history()
    assert 'href="%ssettings#tabs_tabs-plex_media_server"' % plexpy.HTTP_ROOT in page
    assert 'data-tab-destination="plex_media_server" data-target="sign-in-plex"' in page


def test_token_banner_replaces_the_update_bar(pages, monkeypatch):
    monkeypatch.setattr(plexpy.CONFIG, "CHECK_GITHUB", 1)
    monkeypatch.setattr(plexpy, "UPDATE_AVAILABLE", "release")
    monkeypatch.setattr(plexpy, "LATEST_RELEASE", "v9.9.9")
    assert "v9.9.9" in pages.home()
    monkeypatch.setattr(plexpy, "PLEXTV_BAD_TOKEN", "tok")
    page = pages.home()
    assert "v9.9.9" not in page
    assert '<div id="updatebar" style="display: none;"></div>' in page


def test_settings_page_has_one_banner(pages, monkeypatch):
    monkeypatch.setattr(plexpy, "PLEXTV_BAD_TOKEN", "tok")
    assert pages.settings().count('id="token_error_bar"') == 1


def test_link_text_is_fetch_a_new_token(pages, monkeypatch):
    monkeypatch.setattr(plexpy, "PLEXTV_BAD_TOKEN", "tok")
    assert re.search(r'<a href="[^"]*settings#[^"]*"[^>]*>fetch a new token</a>', pages.history())
