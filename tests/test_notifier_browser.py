"""The Ace editor in the notifier config modal, in a real browser.

The fixtures come from test_archive_browser, so these tests skip when
Playwright is missing.
"""

import sqlite3

import pytest

from tests.test_archive_browser import browser, page, server  # noqa: F401

pytestmark = pytest.mark.slow

DISCORD = 20
BODY = "{user} ({player}) started playing {title}."
FIRST_SECTION = "#accordion-notify_text > li:first-child > .link"
EDITOR_INPUT = ".editor-container textarea.ace_text-input"


def open_first_section(server, page):
    page.goto(server["url"] + "/settings")
    added = page.evaluate("() => new Promise(done => $.post('add_notifier_config', {agent_id: %d}, done))" % DISCORD)
    page.evaluate("id => loadNotifierConfig(id)", added["notifier_id"])
    page.wait_for_selector("#notifier-config-modal.in")
    # The first trigger is Playback Start. Its editor appears when the section opens.
    page.click('a[href="#tabs-notify_text"]:has-text("Text")')
    page.click(FIRST_SECTION)
    return added["notifier_id"]


@pytest.fixture
def notifier(server, page):
    notifier_id = open_first_section(server, page)
    page.wait_for_selector(".editor-container .ace_line")
    return notifier_id


def saved_body(server, notifier_id):
    connection = sqlite3.connect(server["db"])
    try:
        return connection.execute("SELECT on_play_body FROM notifiers WHERE id = ?", [notifier_id]).fetchone()[0]
    finally:
        connection.close()


def type_in_editor(page, text):
    page.locator(EDITOR_INPUT).focus()
    page.keyboard.press("Control+A")
    if text:
        page.keyboard.type(text)
    else:
        page.keyboard.press("Delete")


def test_the_editor_shows_the_saved_text(page, notifier):
    assert page.locator(".editor-container .ace_line").first.inner_text() == BODY
    assert page.input_value("#on_play_body") == BODY
    assert page.locator("#on_play_body").is_hidden()


def test_the_editor_looks_like_the_newsletter_editor(page, notifier):
    editor = page.locator(".editor-container.ace_editor")

    assert "ace-tautulli" in editor.get_attribute("class")
    assert editor.evaluate("el => getComputedStyle(el).fontSize") == "14px"
    assert page.locator(".editor-container .ace_print-margin").is_hidden()


def test_an_edit_in_the_editor_is_saved(server, page, notifier):
    type_in_editor(page, "{user} started {title}.")
    assert page.input_value("#on_play_body") == "{user} started {title}."

    with page.expect_response("**/set_notifier_config"):
        page.click("#save-notifier-item")

    assert saved_body(server, notifier) == "{user} started {title}."


def test_typing_at_load_goes_before_the_saved_text(page, notifier):
    page.locator(EDITOR_INPUT).focus()
    page.keyboard.type("X")

    assert page.input_value("#on_play_body") == "X" + BODY


def test_undo_at_load_keeps_the_saved_text(page, notifier):
    # The saved text must not be on the undo stack.
    page.locator(EDITOR_INPUT).focus()
    page.keyboard.press("Control+Z")

    assert page.input_value("#on_play_body") == BODY


def test_reopening_a_section_keeps_one_editor(page, notifier):
    page.click(FIRST_SECTION)
    page.click(FIRST_SECTION)
    page.wait_for_timeout(600)

    assert page.locator(".editor-container").count() == 1


def test_esc_and_tab_leave_the_editor(page, notifier):
    page.locator(EDITOR_INPUT).focus()
    page.keyboard.press("Escape")
    page.keyboard.press("Tab")

    assert page.locator("#notifier-config-modal.in").is_visible()
    assert not page.evaluate("() => document.activeElement.classList.contains('ace_text-input')")


def test_required_still_applies_to_an_empty_body(page, notifier):
    # Parsley reads the hidden textarea. Nothing in the modal calls it on save.
    assert page.evaluate("() => $('#set_notifier_config').parsley().isValid()")

    type_in_editor(page, "")

    assert not page.evaluate("() => $('#set_notifier_config').parsley().isValid()")


def test_a_failed_ace_load_leaves_the_textarea(server, page):
    page.route("**/ace/ace.js*", lambda route: route.fulfill(status=404, body=""))

    open_first_section(server, page)
    page.wait_for_timeout(600)

    assert page.locator(".editor-container").count() == 0
    assert page.locator("#on_play_body").is_visible()
