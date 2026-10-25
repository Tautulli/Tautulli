"""The user page header shows username and email to admins."""

import re

import pytest

import plexpy
from plexpy import webserve

from tests.test_archive_users import library, seeded, web_pages  # noqa: F401  (fixtures)


@pytest.fixture
def user_page(web_pages, app_db, monkeypatch):  # noqa: F811
    def render(username="bobby", friendly_name="", email=None, guest=False):
        app_db.action("INSERT INTO users (user_id, username, friendly_name, email) VALUES (9, ?, ?, ?)",
                      [username, friendly_name, email])
        if guest:
            monkeypatch.setattr(plexpy.session, "get_session_user_id", lambda: "9")
            monkeypatch.setattr(plexpy.session, "get_session_user", lambda: friendly_name or username)
            monkeypatch.setattr(webserve, "get_session_info",
                                lambda: {"user_id": "9", "user": username, "user_group": "guest", "exp": None})
        page = web_pages.user(user_id="9")
        block = re.search(r'<span class="user-info-account">(.*?)</span>\s*</div>', page, re.S)
        return page, (re.findall(r"<span>(.*?)</span>", block.group(1)) if block else None)

    return render


def test_custom_name_and_email_show_both(user_page):
    _, values = user_page(friendly_name="Bob", email="bob@example.com")
    assert values == ["bobby", "bob@example.com"]


def test_no_custom_name_hides_the_username(user_page):
    _, values = user_page(friendly_name="", email="bob@example.com")
    assert values == ["bob@example.com"]


@pytest.mark.parametrize("email", [None, ""])
def test_unset_email_is_hidden(user_page, email):
    _, values = user_page(friendly_name="Bob", email=email)
    assert values == ["bobby"]


def test_html_is_escaped(user_page):
    page, values = user_page(username="<b>x</b>", friendly_name="N", email="a&b<i>@x")
    assert values == ["&lt;b&gt;x&lt;/b&gt;", "a&amp;b&lt;i&gt;@x"]
    assert "<b>x</b>" not in page


def test_guest_does_not_see_the_account_info(user_page):
    page, values = user_page(friendly_name="Bob", email="bob@example.com", guest=True)
    assert "set-username" in page
    assert values is None
    assert "bob@example.com" not in page
