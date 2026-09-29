"""Archive controls in a real browser.

The tests start Tautulli in a subprocess with an empty data directory and
drive it with Playwright. They skip when Playwright is not installed. To
run them, install it with `pip install playwright` and
`playwright install chromium`.

The seed is the shared six-row history from test_history_table. alice
(user_id 1) and bob (user_id 2) both played rating_key 202.
"""

import os
import socket
import sqlite3
import subprocess
import sys
import time

import pytest

sync_api = pytest.importorskip("playwright.sync_api")

from tests.test_history_table import seed_history

pytestmark = pytest.mark.slow

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CONFIG = """[General]
first_run_complete = 1
http_host = 127.0.0.1
launch_browser = 0
check_github = 0
check_github_on_startup = 0
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
    # Plex server. It needs the library and a summary.
    db.action("INSERT INTO library_sections (server_id, section_id, section_name, section_type) "
              "VALUES ('', 1, 'Movies', 'movie')")
    db.action("UPDATE session_history_metadata SET summary = ''")
    yield db
    db.connection.close()


@pytest.fixture(scope="module")
def browser():
    with sync_api.sync_playwright() as playwright:
        browser = playwright.chromium.launch()
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
        page.click("#show-archived-users")
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

    page.click("#show-archived-history")
    sync_api.expect(user_stats).to_contain_text("bob")
    sync_api.expect(all_time_plays).to_have_text("2")

    page.click("#show-archived-history")
    sync_api.expect(user_stats).not_to_contain_text("bob")
    sync_api.expect(all_time_plays).to_have_text("1")
