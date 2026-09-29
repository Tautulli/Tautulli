"""Archive controls in a real browser.

The tests start Tautulli in a subprocess with an empty data directory and
drive it with Playwright. They skip when Playwright is not installed. To
run them, install it with `pip install playwright` and
`playwright install chromium`. CI sets BROWSER_CHANNEL=chrome to use the
Google Chrome that the runner already has.

The seed is the shared six-row history from test_history_table. alice
(user_id 1) and bob (user_id 2) both played rating_key 202.
"""

import json
import os
import socket
import sqlite3
import subprocess
import sys
import time

import pytest

sync_api = pytest.importorskip("playwright.sync_api")

from tests.test_history_table import insert_history_row, seed_history

pytestmark = pytest.mark.slow

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CONFIG = """[General]
first_run_complete = 1
http_host = 127.0.0.1
launch_browser = 0
check_github = 0
check_github_on_startup = 0
home_library_cards = 1,
update_show_changelog = 0
[PMS]
# Nothing listens on port 1, so a Plex server on this machine stays out of the test
pms_port = 1
[Advanced]
system_analytics = 0
"""


@pytest.fixture(scope="module")
def server(tmp_path_factory):
    data_dir = tmp_path_factory.mktemp("tautulli")
    config = data_dir / "config.ini"
    config.write_text(CONFIG)
    log = data_dir / "stdout.log"
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]

    with open(log, "w") as out:
        process = subprocess.Popen([sys.executable, "Tautulli.py", "--datadir", str(data_dir),
                                    "--config", str(config), "--nolaunch", "--port", str(port)],
                                   cwd=REPO, stdout=out, stderr=subprocess.STDOUT)
    try:
        deadline = time.time() + 60
        while "Tautulli is ready!" not in log.read_text():
            assert process.poll() is None and time.time() < deadline, log.read_text()
            time.sleep(0.2)
        yield {"url": "http://127.0.0.1:%d" % port, "db": str(data_dir / "tautulli.db")}
    finally:
        process.terminate()
        try:
            process.wait(timeout=30)
        except subprocess.TimeoutExpired:
            process.kill()


class Database:
    # The seed helpers only need action().
    def __init__(self, path):
        self.connection = sqlite3.connect(path, isolation_level=None)

    def action(self, query, args=None):
        self.connection.execute(query, args or [])


@pytest.fixture
def db(server):
    db = Database(server["db"])
    for table in ("session_history", "session_history_metadata", "session_history_media_info"):
        db.action("DELETE FROM %s" % table)
    db.action("DELETE FROM users WHERE user_id != 0")
    db.action("DELETE FROM library_sections")
    seed_history(db)
    # The info page reads an item's metadata from history when there is no
    # Plex server. It needs the library and a summary. Recently Played needs
    # a parent title.
    db.action("INSERT INTO library_sections (server_id, section_id, section_name, section_type) "
              "VALUES ('', 1, 'Movies', 'movie')")
    db.action("UPDATE session_history_metadata SET summary = '', parent_title = ''")
    yield db
    db.connection.close()


@pytest.fixture(scope="module")
def browser():
    with sync_api.sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel=os.environ.get("BROWSER_CHANNEL"))
        yield browser
        browser.close()


@pytest.fixture
def page(browser):
    context = browser.new_context(viewport={"width": 1400, "height": 900})
    yield context.new_page()
    context.close()


def user_names(page):
    return page.locator("#users_list_table td.edit-user-control input").evaluate_all(
        "inputs => inputs.map(input => input.value)")


def toggle_show_archived(page):
    # The hover plugin opens the menu when the pointer lands on the link's edge.
    # The cog icon covers its center. A click on the link opens the settings page.
    page.hover("a.dropdown-toggle", position={"x": 2, "y": 2})
    with page.expect_navigation():
        page.click("#nav-show-archived")


def test_archiving_in_edit_mode_keeps_the_row(server, db, page):
    page.goto(server["url"] + "/users")
    page.locator("#users_list_table td.edit-user-control input").first.wait_for(state="attached")
    page.click("#row-edit-mode")
    before = user_names(page)

    # Hold any table redraw, so it lands while the admin already hovers
    # another row's toggle, as it does on a large users table.
    held = []
    page.route("**/get_user_list", lambda route: held.append(route))
    with page.expect_response("**/edit_user"):
        page.click('label[for="is_archived-1"]')
    page.hover('label[for="keep_history-2"]')
    page.wait_for_timeout(500)
    for route in held:
        route.continue_()
    page.unroute("**/get_user_list")
    page.wait_for_timeout(500)
    page.mouse.move(0, 0)
    page.wait_for_timeout(500)

    # The rows keep their places, and no tooltip is left without its row.
    assert user_names(page) == before
    alice = page.locator("#users_list_table tr", has=page.locator('label[for="is_archived-1"]'))
    assert "archived-user" in alice.get_attribute("class")
    assert page.locator("body > .tooltip").count() == 0

    # Leaving edit mode drops the archived row.
    with page.expect_response("**/get_user_list"):
        page.click("#row-edit-mode")
    page.wait_for_timeout(200)
    assert user_names(page) == [name for name in before if name != "Alice"]


def test_unarchiving_in_edit_mode_undims_the_row(server, db, page):
    db.action("UPDATE users SET is_archived = 1 WHERE user_id = 1")
    page.goto(server["url"] + "/users")
    with page.expect_response("**/get_user_list"):
        toggle_show_archived(page)
    page.click("#row-edit-mode")

    with page.expect_response("**/edit_user"):
        page.click('label[for="is_archived-1"]')
    page.wait_for_timeout(200)

    alice = page.locator("#users_list_table tr", has=page.locator('label[for="is_archived-1"]'))
    assert "archived-user" not in alice.get_attribute("class")


def test_info_page_stats_follow_show_archived(server, db, page):
    db.action("UPDATE users SET is_archived = 1 WHERE user_id = 2")
    user_stats = page.locator("#user-stats")
    all_time_plays = page.locator("#watch-time-stats .user-overview-stats-instance",
                                  has_text="All Time").locator("h3").first

    page.goto(server["url"] + "/info?rating_key=202&source=history")
    sync_api.expect(user_stats).to_contain_text("Alice")
    sync_api.expect(all_time_plays).to_have_text("1")
    assert "bob" not in user_stats.inner_text()

    toggle_show_archived(page)
    sync_api.expect(user_stats).to_contain_text("bob")
    sync_api.expect(all_time_plays).to_have_text("2")

    toggle_show_archived(page)
    sync_api.expect(user_stats).not_to_contain_text("bob")
    sync_api.expect(all_time_plays).to_have_text("1")


def test_library_stats_follow_show_archived(server, db, page):
    db.action("UPDATE users SET is_archived = 1 WHERE user_id = 2")
    user_stats = page.locator("#library-user-stats")
    # Grouped plays. alice has 3 and bob has 2.
    all_time_plays = page.locator("#library-time-stats .user-overview-stats-instance",
                                  has_text="All Time").locator("h3").first

    page.goto(server["url"] + "/library?section_id=1")
    sync_api.expect(user_stats).to_contain_text("Alice")
    sync_api.expect(all_time_plays).to_have_text("3")
    assert "bob" not in user_stats.inner_text()

    toggle_show_archived(page)
    sync_api.expect(user_stats).to_contain_text("bob")
    sync_api.expect(all_time_plays).to_have_text("5")

    toggle_show_archived(page)
    sync_api.expect(user_stats).not_to_contain_text("bob")
    sync_api.expect(all_time_plays).to_have_text("3")


def test_library_recently_played_follows_show_archived(server, db, page):
    # Only bob played Delta Movie.
    insert_history_row(db, 7, 15, 2, "bob", 5100, 6100, 204, "Delta Movie", "movie")
    db.action("UPDATE users SET is_archived = 1 WHERE user_id = 2")
    recently_played = page.locator("#library-recently-watched")

    page.goto(server["url"] + "/library?section_id=1")
    sync_api.expect(recently_played).to_contain_text("Beta Movie")
    assert "Delta Movie" not in recently_played.text_content()

    toggle_show_archived(page)
    sync_api.expect(recently_played).to_contain_text("Delta Movie")

    toggle_show_archived(page)
    sync_api.expect(recently_played).not_to_contain_text("Delta Movie")


@pytest.mark.parametrize("path, endpoint", [("/history", "get_history"), ("/graphs", "get_plays_by_date")])
def test_history_and_graphs_send_show_archived(server, db, page, path, endpoint):
    # get_history is a POST and the graphs use GET, so check the body and the URL.
    db.action("UPDATE users SET is_archived = 1 WHERE user_id = 2")
    page.add_init_script("localStorage.setItem('include_archived', '1')")

    with page.expect_request(lambda r: endpoint in r.url) as request:
        page.goto(server["url"] + path)

    assert "include_archived=1" in (request.value.post_data or "") + request.value.url


def test_show_archived_carries_to_the_next_page(server, db, page):
    db.action("UPDATE users SET is_archived = 1 WHERE user_id = 2")
    user_stats = page.locator("#library-user-stats")
    indicator = page.locator("#nav-archived-indicator")

    page.goto(server["url"] + "/info?rating_key=202&source=history")
    sync_api.expect(indicator).to_be_hidden()
    toggle_show_archived(page)
    sync_api.expect(indicator).to_be_visible()

    page.goto(server["url"] + "/library?section_id=1")
    sync_api.expect(user_stats).to_contain_text("bob")
    sync_api.expect(page.locator("#nav-show-archived i")).to_have_class("fa fa-fw fa-check-square-o")

    # A click on the indicator hides archived users again.
    with page.expect_navigation():
        page.click("#nav-archived-indicator a")
    sync_api.expect(user_stats).to_contain_text("Alice")
    sync_api.expect(indicator).to_be_hidden()
    assert "bob" not in user_stats.inner_text()


def test_home_page_follows_show_archived(server, db, page):
    # Only bob played Delta Movie, an hour ago. The watch statistics cover the
    # last 30 days. A library card shows the thumb of the library's last play.
    now = int(time.time())
    insert_history_row(db, 7, 15, 2, "bob", now - 3600, now - 3000, 204, "Delta Movie", "movie")
    db.action("UPDATE session_history_metadata SET thumb = '/thumb/' || id")
    db.action("UPDATE users SET is_archived = 1 WHERE user_id = 2")
    home_stats = page.locator("#home-stats")
    card = page.locator("#library-stats li.dashboard-stats-info-item").first

    page.goto(server["url"] + "/home")
    sync_api.expect(home_stats).to_contain_text("No stats to show")
    sync_api.expect(card).to_have_attribute("data-thumb", "/thumb/6")

    toggle_show_archived(page)
    sync_api.expect(home_stats).to_contain_text("Delta Movie")
    sync_api.expect(card).to_have_attribute("data-thumb", "/thumb/7")


def test_libraries_table_follows_show_archived(server, db, page):
    db.action("UPDATE users SET is_archived = 1 WHERE user_id = 2")
    # Grouped plays. alice has 3 and bob has 2.
    plays = "plays => $('#libraries_list_table').DataTable().row(0).data()?.plays === plays"

    page.goto(server["url"] + "/libraries")
    page.wait_for_function(plays, arg=3)

    toggle_show_archived(page)
    page.wait_for_function(plays, arg=5)


def test_media_info_table_follows_show_archived(server, db, page):
    # With no Plex server, the media info tab reads the library items from its
    # cache file. alice and bob both played rating_key 202.
    cache = os.path.join(os.path.dirname(server["db"]), "cache", "media_info_1.json")
    row = {"section_id": 1, "section_type": "movie", "added_at": "0", "media_type": "movie",
           "rating_key": "202", "parent_rating_key": "", "grandparent_rating_key": "", "title": "Beta Movie",
           "sort_title": "Beta Movie", "year": "2020", "media_index": "", "parent_media_index": "", "thumb": "",
           "container": "", "bitrate": "", "video_codec": "", "video_resolution": "", "video_framerate": "",
           "audio_codec": "", "audio_channels": "", "file_size": ""}
    with open(cache, "w") as f:
        json.dump({"last_refreshed": 0, "rows": [row]}, f)
    db.action("UPDATE users SET is_archived = 1 WHERE user_id = 2")
    play_count = "count => media_info_table.row(0).data()?.play_count === count"

    try:
        page.goto(server["url"] + "/library?section_id=1")
        page.click("#nav-tabs-mediainfo")
        page.wait_for_function(play_count, arg=1)

        # The reload keeps the tab open through the page URL.
        toggle_show_archived(page)
        page.wait_for_function(play_count, arg=2)
    finally:
        os.remove(cache)


def test_media_info_child_rows_follow_show_archived(server, db, page):
    # Only show and artist libraries have child rows. The expander asks
    # get_library_media_info for the row's children.
    cache = os.path.join(os.path.dirname(server["db"]), "cache", "media_info_1.json")
    row = {"section_id": 1, "section_type": "show", "added_at": "0", "media_type": "show",
           "rating_key": "202", "parent_rating_key": "", "grandparent_rating_key": "", "title": "Beta Show",
           "sort_title": "Beta Show", "year": "2020", "media_index": "", "parent_media_index": "", "thumb": "",
           "container": "", "bitrate": "", "video_codec": "", "video_resolution": "", "video_framerate": "",
           "audio_codec": "", "audio_channels": "", "file_size": ""}
    with open(cache, "w") as f:
        json.dump({"last_refreshed": 0, "rows": [row]}, f)
    db.action("UPDATE library_sections SET section_type = 'show' WHERE section_id = 1")
    db.action("UPDATE users SET is_archived = 1 WHERE user_id = 2")

    try:
        page.goto(server["url"] + "/library?section_id=1")
        toggle_show_archived(page)
        page.click("#nav-tabs-mediainfo")
        with page.expect_request(lambda r: "get_library_media_info" in r.url
                                 and "rating_key=202" in (r.post_data or "")) as request:
            page.click("td.expand-media-info a")
        assert "include_archived=1" in request.value.post_data
    finally:
        os.remove(cache)


def test_show_archived_resets_while_no_user_is_archived(server, db, page):
    user_stats = page.locator("#library-user-stats")
    page.goto(server["url"] + "/library?section_id=1")
    page.evaluate("localStorage.setItem('include_archived', '1')")

    page.reload()
    assert page.evaluate("localStorage.getItem('include_archived')") == "0"

    # The next archive starts with archived users hidden.
    db.action("UPDATE users SET is_archived = 1 WHERE user_id = 2")
    page.reload()
    sync_api.expect(user_stats).to_contain_text("Alice")
    sync_api.expect(page.locator("#nav-archived-indicator")).to_be_hidden()
    assert "bob" not in user_stats.inner_text()
