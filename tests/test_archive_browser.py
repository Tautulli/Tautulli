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
from urllib.parse import parse_qs

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

    def value(self, query):
        return self.connection.execute(query).fetchone()[0]


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
    # Edit mode reloads the table with the archived and deleted users
    with page.expect_response("**/get_user_list"):
        page.click("#row-edit-mode")
    page.wait_for_timeout(200)
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
    with page.expect_response("**/get_user_list"):
        page.click("#row-edit-mode")
    page.wait_for_timeout(200)

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


@pytest.fixture
def other_library(db):
    # bob's rows 3 and 5 move to a second library, which stays unarchived
    # until a test archives it.
    db.action("INSERT INTO library_sections (server_id, section_id, section_name, section_type) "
              "VALUES ('', 2, 'Other', 'movie')")
    db.action("UPDATE session_history SET section_id = 2 WHERE id IN (3, 5)")
    return db


def library_rows(page):
    return page.locator("#libraries_list_table tbody tr")


def test_libraries_table_follows_show_archived_data(server, other_library, page):
    other_library.action("UPDATE library_sections SET is_archived = 1 WHERE section_id = 2")

    page.goto(server["url"] + "/libraries")
    sync_api.expect(library_rows(page)).to_have_count(1)
    sync_api.expect(library_rows(page).first).to_contain_text("Movies")

    toggle_show_archived(page)
    sync_api.expect(library_rows(page)).to_have_count(2)
    other = library_rows(page).filter(has_text="Other")
    assert "archived-library" in other.get_attribute("class")
    assert "archived-library" not in library_rows(page).filter(has_text="Movies").get_attribute("class")
    sync_api.expect(other.locator(".inactive-library-tooltip")).to_have_count(1)


def test_archiving_a_library_in_edit_mode_keeps_the_row(server, other_library, page):
    page.goto(server["url"] + "/libraries")
    sync_api.expect(library_rows(page)).to_have_count(2)
    page.click("#row-edit-mode")

    with page.expect_response("**/edit_library"):
        page.click('label[for="is_archived-2"]')
    other = library_rows(page).filter(has=page.locator('label[for="is_archived-2"]'))
    page.wait_for_timeout(200)
    assert "archived-library" in other.get_attribute("class")
    assert other_library.connection.execute(
        "SELECT is_archived FROM library_sections WHERE section_id = 2").fetchone() == (1,)

    # Leaving edit mode drops the archived row.
    with page.expect_response("**/get_library_list"):
        page.click("#row-edit-mode")
    sync_api.expect(library_rows(page)).to_have_count(1)


def test_show_archived_data_shows_while_only_a_library_is_archived(server, other_library, page):
    other_library.action("UPDATE library_sections SET is_archived = 1 WHERE section_id = 2")

    page.goto(server["url"] + "/home")
    page.hover("a.dropdown-toggle", position={"x": 2, "y": 2})
    sync_api.expect(page.locator("#nav-show-archived")).to_contain_text("Show Archived Data")

    # The choice resets after the last library is unarchived.
    page.evaluate("localStorage.setItem('include_archived', '1')")
    other_library.action("UPDATE library_sections SET is_archived = 0 WHERE section_id = 2")
    page.reload()
    assert page.evaluate("localStorage.getItem('include_archived')") == "0"
    sync_api.expect(page.locator("#nav-archived-indicator")).to_have_count(0)


def test_library_modal_saves_the_archive_checkbox(server, db, page):
    page.goto(server["url"] + "/library?section_id=1")
    page.click("#toggle-edit-library-modal")
    box = page.locator("#edit-library-modal #is_archived")
    box.wait_for()
    assert not box.is_checked()
    box.check()
    with page.expect_response("**/edit_library"):
        with page.expect_navigation():
            page.click("#save_library")
    assert db.connection.execute("SELECT is_archived FROM library_sections WHERE section_id = 1").fetchone() == (1,)

    # The modal shows the saved state, and a save without the box unarchives.
    page.click("#toggle-edit-library-modal")
    box = page.locator("#edit-library-modal #is_archived")
    box.wait_for()
    assert box.is_checked()
    box.uncheck()
    with page.expect_navigation():
        page.click("#save_library")
    assert db.connection.execute("SELECT is_archived FROM library_sections WHERE section_id = 1").fetchone() == (0,)


USER_PAGE_REQUESTS = ("get_history", "get_user_ips", "get_user_recently_watched", "user_watch_time_stats",
                      "user_player_stats")


@pytest.mark.parametrize("shown", ["1", "0"])
def test_user_page_requests_send_show_archived(server, db, page, shown):
    db.action("UPDATE users SET is_archived = 1 WHERE user_id = 2")
    page.add_init_script("localStorage.setItem('include_archived', '%s')" % shown)
    seen = {}

    def note(request):
        for name in USER_PAGE_REQUESTS:
            if name in request.url.split("?")[0]:
                seen[name] = request.url + (request.post_data or "")

    page.on("request", note)
    page.goto(server["url"] + "/user?user_id=1")
    page.click("#nav-tabs-history")
    page.click("#nav-tabs-ipaddresses")
    page.wait_for_timeout(2500)
    assert set(seen) == set(USER_PAGE_REQUESTS)
    for name, sent in seen.items():
        assert "include_archived=%s" % shown in sent, name


def edit_row(page, table, key):
    return page.locator("#%s tr" % table, has=page.locator('label[for="keep_history-%s"]' % key))


def queue_restore_and_exit(page, row, kind, *more_rows):
    for queued in (row,) + more_rows:
        queued.locator("button.restore-%s" % kind).click()
    page.click("#row-edit-mode")
    sync_api.expect(page.locator("#confirm-modal-delete")).to_be_visible()


def confirm_restore(page, kind):
    sent = []
    page.on("request", lambda request: sent.append(request.post_data) if "undelete_%s" % kind in request.url else None)
    with page.expect_response("**/undelete_%s" % kind):
        page.click("#confirm-delete")
    page.wait_for_timeout(300)
    return sent


def is_green(button):
    return "btn-success" in button.get_attribute("class")


def test_restoring_a_deleted_user_in_edit_mode(server, db, page):
    db.action("UPDATE users SET deleted_user = 1, keep_history = 0 WHERE user_id = 2")
    page.goto(server["url"] + "/users")
    page.locator("#users_list_table td.edit-user-control a").first.wait_for(state="attached")
    assert edit_row(page, "users_list_table", 2).count() == 0

    with page.expect_response(lambda r: "get_user_list" in r.url):
        page.click("#row-edit-mode")
    bob = edit_row(page, "users_list_table", 2)
    bob.wait_for()

    # A deleted row is dimmed, has the Deleted user icon, and offers Restore only.
    assert "deleted-user" in bob.get_attribute("class")
    assert bob.locator(".inactive-user-tooltip").get_attribute("title") == "Deleted user"
    sync_api.expect(bob.locator("button.restore-user")).to_be_visible()
    sync_api.expect(bob.locator("button.delete-user")).to_be_hidden()
    sync_api.expect(bob.locator("button.purge-user")).to_be_hidden()

    # Restore queues the user and turns the button green. A second click unqueues it.
    # The tooltip names restore. A second click unqueues the user, so leaving edit mode opens no popup.
    sync_api.expect(page.locator(".tooltip-inner")).to_contain_text("restore")
    restore = bob.locator("button.restore-user")
    restore.click()
    assert is_green(restore)
    restore.click()
    assert not is_green(restore)
    page.click("#row-edit-mode")
    page.wait_for_timeout(500)
    sync_api.expect(page.locator("#confirm-modal-delete")).to_be_hidden()
    with page.expect_response("**/get_user_list"):
        page.click("#row-edit-mode")
    bob = edit_row(page, "users_list_table", 2)
    bob.wait_for()

    restore = bob.locator("button.restore-user")
    restore.click()
    assert is_green(restore)
    sync_api.expect(page.locator("#confirm-modal-delete")).to_be_hidden()
    assert db.value("SELECT deleted_user FROM users WHERE user_id = 2") == 1

    # A redraw keeps the queued button green.
    with page.expect_response("**/get_user_list"):
        page.evaluate("users_list_table.draw(false)")
    page.wait_for_timeout(200)
    assert is_green(bob.locator("button.restore-user"))

    # Leaving edit mode with only a restore queued opens the popup. Cancel restores nothing.
    saved = []
    page.on("request", lambda request: saved.append(request.url) if "undelete_user" in request.url else None)
    page.click("#row-edit-mode")
    popup = page.locator("#confirm-modal-delete")
    sync_api.expect(popup).to_be_visible()
    sync_api.expect(popup.locator("#users-to-restore")).to_contain_text("bob")
    sync_api.expect(popup.locator("#users-permanent")).to_be_hidden()
    popup.locator("button", has_text="Cancel").click()
    sync_api.expect(popup).to_be_hidden()
    page.wait_for_timeout(200)
    assert saved == []
    assert db.value("SELECT deleted_user FROM users WHERE user_id = 2") == 1

    # The next edit mode starts with an empty queue.
    with page.expect_response("**/get_user_list"):
        page.click("#row-edit-mode")
    bob = edit_row(page, "users_list_table", 2)
    bob.wait_for()
    page.click("#row-edit-mode")
    page.wait_for_timeout(500)
    sync_api.expect(popup).to_be_hidden()

    # The popup lists a name once each time it opens.
    with page.expect_response("**/get_user_list"):
        page.click("#row-edit-mode")
    bob.locator("button.restore-user").click()
    page.click("#row-edit-mode")
    sync_api.expect(popup).to_be_visible()
    sync_api.expect(popup.locator("#users-to-restore li")).to_have_count(1)
    sync_api.expect(popup.locator(".modal-title")).to_contain_text("Restore")


def test_confirming_a_queued_restore_restores_the_user(server, db, page):
    db.action("UPDATE users SET deleted_user = 1, keep_history = 0 WHERE user_id = 2")
    page.goto(server["url"] + "/users")
    page.locator("#users_list_table td.edit-user-control a").first.wait_for(state="attached")
    with page.expect_response(lambda r: "get_user_list" in r.url):
        page.click("#row-edit-mode")
    bob = edit_row(page, "users_list_table", 2)
    bob.wait_for()

    queue_restore_and_exit(page, bob, "user")
    confirm_restore(page, "user")

    assert db.value("SELECT deleted_user FROM users WHERE user_id = 2") == 0
    assert db.value("SELECT keep_history FROM users WHERE user_id = 2") == 1
    # The redraw lists bob as a normal row.
    assert edit_row(page, "users_list_table", 2).count() == 1
    assert "deleted-user" not in edit_row(page, "users_list_table", 2).get_attribute("class")
    assert edit_row(page, "users_list_table", 2).locator(".inactive-user-tooltip").count() == 0


def test_confirming_two_queued_restores_sends_one_undelete_user_call(server, db, page):
    db.action("UPDATE users SET deleted_user = 1, keep_history = 0 WHERE user_id IN (1, 2)")
    row_ids = [str(db.value("SELECT id FROM users WHERE user_id = %d" % user_id)) for user_id in (1, 2)]
    page.goto(server["url"] + "/users")
    page.locator("#users_list_table td.edit-user-control a").first.wait_for(state="attached")
    with page.expect_response(lambda r: "get_user_list" in r.url):
        page.click("#row-edit-mode")
    alice = edit_row(page, "users_list_table", 1)
    bob = edit_row(page, "users_list_table", 2)
    bob.wait_for()

    queue_restore_and_exit(page, alice, "user", bob)
    sent = confirm_restore(page, "user")

    assert len(sent) == 1
    assert sorted(parse_qs(sent[0])["row_ids"][0].split(",")) == sorted(row_ids)
    assert db.value("SELECT COUNT(*) FROM users WHERE user_id IN (1, 2) AND deleted_user = 0 "
                    "AND keep_history = 1") == 2
    assert "deleted-user" not in edit_row(page, "users_list_table", 1).get_attribute("class")
    assert "deleted-user" not in edit_row(page, "users_list_table", 2).get_attribute("class")


def test_confirming_a_purge_sends_no_undelete_user_call(server, db, page):
    page.goto(server["url"] + "/users")
    page.locator("#users_list_table td.edit-user-control a").first.wait_for(state="attached")
    with page.expect_response(lambda r: "get_user_list" in r.url):
        page.click("#row-edit-mode")
    row = edit_row(page, "users_list_table", 1)
    row.wait_for()
    sent = []
    page.on("request", lambda request: sent.append(request.url) if "undelete_user" in request.url else None)

    row.locator("button.purge-user").click()
    page.click("#row-edit-mode")
    sync_api.expect(page.locator("#confirm-modal-delete")).to_be_visible()
    with page.expect_response("**/delete_all_user_history"):
        page.click("#confirm-delete")
    page.wait_for_timeout(300)

    assert sent == []


def test_queued_restore_is_pressed_and_resets_on_exit(server, db, page):
    db.action("UPDATE users SET deleted_user = 1, keep_history = 0 WHERE user_id = 2")
    page.goto(server["url"] + "/users")
    page.locator("#users_list_table td.edit-user-control a").first.wait_for(state="attached")
    with page.expect_response(lambda r: "get_user_list" in r.url):
        page.click("#row-edit-mode")
    bob = edit_row(page, "users_list_table", 2)
    bob.wait_for()
    restore = bob.locator("button.restore-user")
    restore.click()
    assert "active" in restore.get_attribute("class")

    # Hold the redraw, so the old row is still there when edit mode ends.
    held = []
    page.route("**/get_user_list", lambda route: held.append(route))
    page.click("#row-edit-mode")
    sync_api.expect(page.locator("#confirm-modal-delete")).to_be_visible()
    assert not is_green(restore)
    for route in held:
        route.continue_()


def test_deleted_user_row_leaves_with_edit_mode(server, db, page):
    db.action("UPDATE users SET deleted_user = 1 WHERE user_id = 2")
    page.goto(server["url"] + "/users")
    page.locator("#users_list_table td.edit-user-control a").first.wait_for(state="attached")

    with page.expect_response("**/get_user_list"):
        page.click("#row-edit-mode")
    edit_row(page, "users_list_table", 2).wait_for()

    with page.expect_response("**/get_user_list"):
        page.click("#row-edit-mode")
    page.wait_for_timeout(200)
    assert edit_row(page, "users_list_table", 2).count() == 0


def test_restoring_a_deleted_library_in_edit_mode(server, db, page):
    db.action("UPDATE library_sections SET deleted_section = 1, keep_history = 0")
    page.goto(server["url"] + "/libraries")
    sync_api.expect(page.locator("#libraries_list_table")).to_contain_text("No matching records found")

    with page.expect_response("**/get_library_list"):
        page.click("#row-edit-mode")
    movies = edit_row(page, "libraries_list_table", 1)
    movies.wait_for()

    assert "deleted-library" in movies.get_attribute("class")
    assert movies.locator(".inactive-library-tooltip").get_attribute("title") == "Deleted library"
    sync_api.expect(movies.locator("button.restore-library")).to_be_visible()
    sync_api.expect(movies.locator("button.delete-library")).to_be_hidden()
    sync_api.expect(movies.locator("button.purge-library")).to_be_hidden()

    # The tooltip names restore. A second click unqueues the user, so leaving edit mode opens no popup.
    sync_api.expect(page.locator(".tooltip-inner")).to_contain_text("restore")
    restore = movies.locator("button.restore-library")
    restore.click()
    assert is_green(restore)
    restore.click()
    assert not is_green(restore)
    page.click("#row-edit-mode")
    page.wait_for_timeout(500)
    sync_api.expect(page.locator("#confirm-modal-delete")).to_be_hidden()
    with page.expect_response("**/get_library_list"):
        page.click("#row-edit-mode")
    movies = edit_row(page, "libraries_list_table", 1)
    movies.wait_for()

    restore = movies.locator("button.restore-library")
    restore.click()
    assert is_green(restore)
    sync_api.expect(page.locator("#confirm-modal-delete")).to_be_hidden()
    assert db.value("SELECT deleted_section FROM library_sections WHERE section_id = 1") == 1

    with page.expect_response("**/get_library_list"):
        page.evaluate("libraries_list_table.draw(false)")
    page.wait_for_timeout(200)
    assert is_green(movies.locator("button.restore-library"))

    saved = []
    page.on("request", lambda request: saved.append(request.url) if "undelete_library" in request.url else None)
    page.click("#row-edit-mode")
    popup = page.locator("#confirm-modal-delete")
    sync_api.expect(popup).to_be_visible()
    sync_api.expect(popup.locator("#libraries-to-restore")).to_contain_text("Movies")
    sync_api.expect(popup.locator("#libraries-permanent")).to_be_hidden()
    popup.locator("button", has_text="Cancel").click()
    sync_api.expect(popup).to_be_hidden()
    page.wait_for_timeout(200)
    assert saved == []
    assert db.value("SELECT deleted_section FROM library_sections WHERE section_id = 1") == 1

    with page.expect_response("**/get_library_list"):
        page.click("#row-edit-mode")
    movies = edit_row(page, "libraries_list_table", 1)
    movies.wait_for()
    page.click("#row-edit-mode")
    page.wait_for_timeout(500)
    sync_api.expect(popup).to_be_hidden()

    # The popup lists a name once each time it opens.
    with page.expect_response("**/get_library_list"):
        page.click("#row-edit-mode")
    movies.locator("button.restore-library").click()
    page.click("#row-edit-mode")
    sync_api.expect(popup).to_be_visible()
    sync_api.expect(popup.locator("#libraries-to-restore li")).to_have_count(1)
    sync_api.expect(popup.locator(".modal-title")).to_contain_text("Restore")


def test_confirming_a_queued_restore_restores_the_library(server, db, page):
    db.action("UPDATE library_sections SET deleted_section = 1, keep_history = 0")
    page.goto(server["url"] + "/libraries")
    sync_api.expect(page.locator("#libraries_list_table")).to_contain_text("No matching records found")
    with page.expect_response("**/get_library_list"):
        page.click("#row-edit-mode")
    movies = edit_row(page, "libraries_list_table", 1)
    movies.wait_for()

    queue_restore_and_exit(page, movies, "library")
    confirm_restore(page, "library")

    assert db.value("SELECT deleted_section FROM library_sections WHERE section_id = 1") == 0
    assert db.value("SELECT keep_history FROM library_sections WHERE section_id = 1") == 1
    assert edit_row(page, "libraries_list_table", 1).count() == 1
    assert "deleted-library" not in edit_row(page, "libraries_list_table", 1).get_attribute("class")
    assert edit_row(page, "libraries_list_table", 1).locator(".inactive-library-tooltip").count() == 0


def test_confirming_two_queued_restores_sends_one_undelete_library_call(server, other_library, page):
    other_library.action("UPDATE library_sections SET deleted_section = 1, keep_history = 0")
    row_ids = [str(other_library.value("SELECT id FROM library_sections WHERE section_id = %d" % section_id))
               for section_id in (1, 2)]
    page.goto(server["url"] + "/libraries")
    sync_api.expect(page.locator("#libraries_list_table")).to_contain_text("No matching records found")
    with page.expect_response("**/get_library_list"):
        page.click("#row-edit-mode")
    movies = edit_row(page, "libraries_list_table", 1)
    other = edit_row(page, "libraries_list_table", 2)
    other.wait_for()

    queue_restore_and_exit(page, movies, "library", other)
    sent = confirm_restore(page, "library")

    assert len(sent) == 1
    assert sorted(parse_qs(sent[0])["row_ids"][0].split(",")) == sorted(row_ids)
    assert other_library.value("SELECT COUNT(*) FROM library_sections WHERE deleted_section = 0 "
                               "AND keep_history = 1") == 2
    assert "deleted-library" not in edit_row(page, "libraries_list_table", 1).get_attribute("class")
    assert "deleted-library" not in edit_row(page, "libraries_list_table", 2).get_attribute("class")


def test_confirming_a_purge_sends_no_undelete_library_call(server, db, page):
    page.goto(server["url"] + "/libraries")
    sync_api.expect(page.locator("#libraries_list_table")).to_contain_text("Movies")
    with page.expect_response(lambda r: "get_library_list" in r.url):
        page.click("#row-edit-mode")
    row = edit_row(page, "libraries_list_table", 1)
    row.wait_for()
    sent = []
    page.on("request", lambda request: sent.append(request.url) if "undelete_library" in request.url else None)

    row.locator("button.purge-library").click()
    page.click("#row-edit-mode")
    sync_api.expect(page.locator("#confirm-modal-delete")).to_be_visible()
    with page.expect_response("**/delete_all_library_history"):
        page.click("#confirm-delete")
    page.wait_for_timeout(300)

    assert sent == []


def test_deleted_library_row_leaves_with_edit_mode(server, db, page):
    db.action("UPDATE library_sections SET deleted_section = 1")
    page.goto(server["url"] + "/libraries")
    sync_api.expect(page.locator("#libraries_list_table")).to_contain_text("No matching records found")

    with page.expect_response("**/get_library_list"):
        page.click("#row-edit-mode")
    edit_row(page, "libraries_list_table", 1).wait_for()

    with page.expect_response("**/get_library_list"):
        page.click("#row-edit-mode")
    page.wait_for_timeout(200)
    assert edit_row(page, "libraries_list_table", 1).count() == 0


def test_edit_mode_lists_an_archived_library_with_its_box_checked(server, other_library, page):
    other_library.action("UPDATE library_sections SET is_archived = 1 WHERE section_id = 2")
    page.goto(server["url"] + "/libraries")
    sync_api.expect(library_rows(page)).to_have_count(1)
    with page.expect_response("**/get_library_list"):
        page.click("#row-edit-mode")
    other = library_rows(page).filter(has=page.locator('label[for="is_archived-2"]'))
    other.wait_for()
    sync_api.expect(other.locator("#is_archived-2")).to_be_checked()
    sync_api.expect(library_rows(page).filter(has=page.locator('label[for="is_archived-1"]'))
                    .locator("#is_archived-1")).not_to_be_checked()
    assert other.locator(".inactive-library-tooltip").get_attribute("title") == "Archived library"

    # Unarchiving in edit mode undims the row.
    with page.expect_response("**/edit_library"):
        page.click('label[for="is_archived-2"]')
    page.wait_for_timeout(200)
    assert "archived-library" not in other.get_attribute("class")


def td_opacity(row):
    return row.locator("td").nth(1).evaluate("td => getComputedStyle(td).opacity")


def test_archived_and_deleted_rows_are_dimmed_until_hovered(server, db, other_library, page):
    db.action("UPDATE users SET is_archived = 1 WHERE user_id = 1")
    db.action("UPDATE users SET deleted_user = 1 WHERE user_id = 2")
    page.goto(server["url"] + "/users")
    page.locator("#users_list_table td.edit-user-control a").first.wait_for(state="attached")
    with page.expect_response("**/get_user_list"):
        page.click("#row-edit-mode")
    edit_row(page, "users_list_table", 2).wait_for()
    for key in (1, 2):
        row = edit_row(page, "users_list_table", key)
        assert td_opacity(row) == "0.5"
        row.hover()
        page.wait_for_timeout(100)
        assert td_opacity(row) == "1"
        page.mouse.move(0, 0)

    db.action("UPDATE library_sections SET is_archived = 1 WHERE section_id = 1")
    db.action("UPDATE library_sections SET deleted_section = 1 WHERE section_id = 2")
    page.goto(server["url"] + "/libraries")
    with page.expect_response("**/get_library_list"):
        page.click("#row-edit-mode")
    edit_row(page, "libraries_list_table", 2).wait_for()
    for key in (1, 2):
        row = edit_row(page, "libraries_list_table", key)
        assert td_opacity(row) == "0.5"
        row.hover()
        page.wait_for_timeout(100)
        assert td_opacity(row) == "1"
        page.mouse.move(0, 0)


def test_history_rows_of_an_archived_library_are_dimmed(server, db, other_library, page):
    db.action("UPDATE library_sections SET is_archived = 1 WHERE section_id = 2")
    page.add_init_script("localStorage.setItem('include_archived', '1')")
    page.goto(server["url"] + "/history")
    rows = page.locator("#history_table tbody tr")
    archived = page.locator("#history_table tbody tr.archived-library")
    normal = page.locator("#history_table tbody tr:not(.archived-library)")
    rows.first.wait_for()
    page.mouse.move(0, 0)

    assert archived.count() > 0
    assert normal.count() > 0
    assert {td_opacity(archived.nth(i)) for i in range(archived.count())} == {"0.5"}
    assert {td_opacity(normal.nth(i)) for i in range(normal.count())} == {"1"}


def test_history_group_of_an_archived_library_shows_its_plays_undimmed(server, db, other_library, page):
    db.action("UPDATE session_history SET section_id = 2 WHERE id IN (1, 2)")
    db.action("UPDATE library_sections SET is_archived = 1 WHERE section_id = 2")
    page.add_init_script("localStorage.setItem('include_archived', '1')")
    page.goto(server["url"] + "/history")
    parent = page.locator("#history_table > tbody > tr", has=page.locator("td.expand-history a"))
    parent.wait_for()

    with page.expect_response("**/get_history"):
        parent.locator("td.expand-history a").click()
    child = page.locator("table[id^='history_child'] tbody tr")
    child.first.wait_for()
    page.mouse.move(0, 0)

    assert "archived-library" in parent.get_attribute("class")
    assert td_opacity(parent) == "0.5"
    assert child.count() == 2
    assert {td_opacity(child.nth(i)) for i in range(2)} == {"1"}


def test_home_library_cards_picker_marks_an_archived_library(server, db, other_library, page):
    db.action("UPDATE library_sections SET is_archived = 1 WHERE section_id = 2")
    page.goto(server["url"] + "/settings")
    page.click("#nav-tabs-homepage")
    cards = page.locator("#sortable_home_library_cards li.card")
    cards.first.wait_for()
    archived = cards.filter(has_text="Other")
    normal = cards.filter(has_text="Movies")
    icon = archived.locator("i.fa-archive")
    page.locator("#sortable_home_library_cards").screenshot(
        path="/var/tmp/claude/claude-1001/-home-phernandez-orca-workspaces-Tautulli-archive-undelete-hide-lib/"
             "dc5ac4fe-ab3f-4582-9d7d-bf7bb1a1c383/scratchpad/home-library-cards-picker.png")

    assert icon.count() == 1
    assert normal.locator("i.fa-archive").count() == 0
    assert archived.locator("span[title='Archived library']").count() == 1
    card_box, icon_box = archived.bounding_box(), icon.bounding_box()
    assert 0 <= card_box["x"] + card_box["width"] - (icon_box["x"] + icon_box["width"]) <= 25
    assert abs((icon_box["y"] + icon_box["height"] / 2) - (card_box["y"] + card_box["height"] / 2)) <= 3


def test_restore_button_error_keeps_the_user_row_deleted(server, db, page):
    db.action("UPDATE users SET deleted_user = 1, keep_history = 0 WHERE user_id = 2")
    page.goto(server["url"] + "/users")
    page.locator("#users_list_table td.edit-user-control a").first.wait_for(state="attached")
    with page.expect_response("**/get_user_list"):
        page.click("#row-edit-mode")
    bob = edit_row(page, "users_list_table", 2)
    bob.wait_for()
    page.route("**/undelete_user", lambda route: route.fulfill(
        status=200, content_type="application/json",
        body='{"result": "error", "message": "Unable to restore user."}'))
    queue_restore_and_exit(page, bob, "user")
    confirm_restore(page, "user")
    sync_api.expect(page.locator("#ajaxMsg")).to_have_css("background-color", "rgba(255, 0, 0, 0.5)")
    assert db.value("SELECT deleted_user FROM users WHERE user_id = 2") == 1


def test_restoring_a_library_removes_its_icon_and_a_failure_keeps_the_row(server, db, page):
    db.action("UPDATE library_sections SET deleted_section = 1, keep_history = 0")
    page.goto(server["url"] + "/libraries")
    with page.expect_response("**/get_library_list"):
        page.click("#row-edit-mode")
    movies = edit_row(page, "libraries_list_table", 1)
    movies.wait_for()
    page.route("**/undelete_library", lambda route: route.fulfill(
        status=200, content_type="application/json",
        body='{"result": "error", "message": "Unable to restore library."}'))
    queue_restore_and_exit(page, movies, "library")
    confirm_restore(page, "library")
    sync_api.expect(page.locator("#ajaxMsg")).to_have_css("background-color", "rgba(255, 0, 0, 0.5)")
    assert db.value("SELECT deleted_section FROM library_sections WHERE section_id = 1") == 1
    page.unroute("**/undelete_library")

    with page.expect_response("**/get_library_list"):
        page.click("#row-edit-mode")
    movies = edit_row(page, "libraries_list_table", 1)
    movies.wait_for()
    assert movies.locator(".inactive-library-tooltip").count() == 1
    queue_restore_and_exit(page, movies, "library")
    confirm_restore(page, "library")
    assert movies.locator(".inactive-library-tooltip").count() == 0


def test_edit_mode_lists_an_archived_user_and_a_deleted_archived_user_shows_the_trash(server, db, page):
    db.action("UPDATE users SET is_archived = 1 WHERE user_id = 1")
    db.action("UPDATE users SET is_archived = 1, deleted_user = 1 WHERE user_id = 2")
    page.goto(server["url"] + "/users")
    page.locator("#users_list_table td.edit-user-control a").first.wait_for(state="attached")
    with page.expect_response("**/get_user_list"):
        page.click("#row-edit-mode")
    alice = edit_row(page, "users_list_table", 1)
    bob = edit_row(page, "users_list_table", 2)
    bob.wait_for()
    sync_api.expect(alice.locator("#is_archived-1")).to_be_checked()
    assert alice.locator(".inactive-user-tooltip").get_attribute("title") == "Archived user"
    assert bob.locator(".inactive-user-tooltip").get_attribute("title") == "Deleted user"


def test_restoring_a_user_removes_its_icon(server, db, page):
    db.action("UPDATE users SET deleted_user = 1, keep_history = 0 WHERE user_id = 2")
    page.goto(server["url"] + "/users")
    page.locator("#users_list_table td.edit-user-control a").first.wait_for(state="attached")
    with page.expect_response("**/get_user_list"):
        page.click("#row-edit-mode")
    bob = edit_row(page, "users_list_table", 2)
    bob.wait_for()
    assert bob.locator(".inactive-user-tooltip").count() == 1
    queue_restore_and_exit(page, bob, "user")
    confirm_restore(page, "user")
    assert bob.locator(".inactive-user-tooltip").count() == 0


OFF = "rgb(68, 68, 68)"
ON = "rgb(238, 238, 238)"


def toggle_colors(row, names, key):
    return [row.locator('label[for="%s-%s"]' % (name, key)).evaluate("label => getComputedStyle(label).color")
            for name in names]


def test_a_deleted_users_toggles_are_disabled_until_restore(server, db, page):
    names = ("keep_history", "allow_guest", "is_archived")
    # allow_guest and is_archived stay set in the database while the user is deleted.
    db.action("UPDATE users SET deleted_user = 1, keep_history = 0, allow_guest = 1, is_archived = 1 "
              "WHERE user_id = 2")
    page.goto(server["url"] + "/users")
    page.locator("#users_list_table td.edit-user-control a").first.wait_for(state="attached")
    with page.expect_response(lambda r: "get_user_list" in r.url):
        page.click("#row-edit-mode")
    bob = edit_row(page, "users_list_table", 2)
    bob.wait_for()

    for name in names:
        sync_api.expect(bob.locator("#%s-2" % name)).to_be_disabled()
    sync_api.expect(bob.locator("#allow_guest-2")).to_be_checked()
    assert toggle_colors(bob, names, 2) == [OFF, OFF, OFF]
    assert bob.locator('label[for="allow_guest-2"]').evaluate("label => getComputedStyle(label).cursor") == "default"

    # A click on a disabled toggle changes nothing and saves nothing.
    saved = []
    page.on("request", lambda request: saved.append(request.url) if "edit_user" in request.url else None)
    bob.locator('label[for="allow_guest-2"]').click(force=True)
    bob.locator('label[for="keep_history-2"]').click(force=True)
    page.wait_for_timeout(300)
    sync_api.expect(bob.locator("#allow_guest-2")).to_be_checked()
    sync_api.expect(bob.locator("#keep_history-2")).not_to_be_checked()
    assert saved == []

    queue_restore_and_exit(page, bob, "user")
    confirm_restore(page, "user")

    for name in names:
        sync_api.expect(bob.locator("#%s-2" % name)).to_be_enabled()
    sync_api.expect(bob.locator("#keep_history-2")).to_be_checked()
    sync_api.expect(bob.locator("#allow_guest-2")).to_be_checked()
    sync_api.expect(bob.locator("#is_archived-2")).not_to_be_checked()
    assert "archived-user" not in bob.get_attribute("class")
    assert toggle_colors(bob, names, 2) == [ON, ON, OFF]


def test_a_deleted_librarys_toggles_are_disabled_until_restore(server, db, page):
    names = ("keep_history", "is_archived")
    db.action("UPDATE library_sections SET deleted_section = 1, keep_history = 0, is_archived = 1")
    page.goto(server["url"] + "/libraries")
    sync_api.expect(page.locator("#libraries_list_table")).to_contain_text("No matching records found")
    with page.expect_response("**/get_library_list"):
        page.click("#row-edit-mode")
    movies = edit_row(page, "libraries_list_table", 1)
    movies.wait_for()

    for name in names:
        sync_api.expect(movies.locator("#%s-1" % name)).to_be_disabled()
    sync_api.expect(movies.locator("#is_archived-1")).to_be_checked()
    assert toggle_colors(movies, names, 1) == [OFF, OFF]
    assert movies.locator('label[for="is_archived-1"]').evaluate("label => getComputedStyle(label).cursor") == "default"

    saved = []
    page.on("request", lambda request: saved.append(request.url) if "edit_library" in request.url else None)
    movies.locator('label[for="is_archived-1"]').click(force=True)
    movies.locator('label[for="keep_history-1"]').click(force=True)
    page.wait_for_timeout(300)
    sync_api.expect(movies.locator("#is_archived-1")).to_be_checked()
    sync_api.expect(movies.locator("#keep_history-1")).not_to_be_checked()
    assert saved == []

    queue_restore_and_exit(page, movies, "library")
    confirm_restore(page, "library")

    for name in names:
        sync_api.expect(movies.locator("#%s-1" % name)).to_be_enabled()
    sync_api.expect(movies.locator("#keep_history-1")).to_be_checked()
    sync_api.expect(movies.locator("#is_archived-1")).not_to_be_checked()
    assert "archived-library" not in movies.get_attribute("class")
    assert toggle_colors(movies, names, 1) == [ON, OFF]


def box(row, selector):
    return row.locator(selector).bounding_box()


def test_a_deleted_users_toggles_line_up_with_the_rows_above(server, db, page):
    db.action("UPDATE users SET deleted_user = 1 WHERE user_id = 2")
    page.goto(server["url"] + "/users")
    page.locator("#users_list_table td.edit-user-control a").first.wait_for(state="attached")
    with page.expect_response(lambda r: "get_user_list" in r.url):
        page.click("#row-edit-mode")
    alice = edit_row(page, "users_list_table", 1)
    bob = edit_row(page, "users_list_table", 2)
    bob.wait_for()

    assert abs(box(bob, 'label[for="keep_history-2"]')["x"] - box(alice, 'label[for="keep_history-1"]')["x"]) <= 1
    # Restore sits where Delete sits, on the same line.
    delete = box(alice, "button.delete-user")
    restore = box(bob, "button.restore-user")
    assert abs(restore["x"] - delete["x"]) <= 1
    assert abs(restore["y"] - box(bob, "button.delete-user")["y"]) <= 1
    sync_api.expect(bob.locator("button.delete-user")).not_to_be_visible()
    sync_api.expect(bob.locator("button.purge-user")).not_to_be_visible()


def test_a_deleted_librarys_toggles_line_up_with_the_rows_above(server, other_library, page):
    other_library.action("UPDATE library_sections SET deleted_section = 1 WHERE section_id = 2")
    page.goto(server["url"] + "/libraries")
    with page.expect_response("**/get_library_list"):
        page.click("#row-edit-mode")
    movies = edit_row(page, "libraries_list_table", 1)
    other = edit_row(page, "libraries_list_table", 2)
    other.wait_for()

    assert abs(box(other, 'label[for="keep_history-2"]')["x"] - box(movies, 'label[for="keep_history-1"]')["x"]) <= 1
    delete = box(movies, "button.delete-library")
    restore = box(other, "button.restore-library")
    assert abs(restore["x"] - delete["x"]) <= 1
    assert abs(restore["y"] - box(other, "button.delete-library")["y"]) <= 1
    sync_api.expect(other.locator("button.delete-library")).not_to_be_visible()
    sync_api.expect(other.locator("button.purge-library")).not_to_be_visible()
