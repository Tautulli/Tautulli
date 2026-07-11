"""The last played row of a table follows the latest start.

Two plays overlap. The one with the higher id started earlier, so a pick
by highest id shows the title of the wrong play next to last_seen.
"""

import json

import plexpy
from plexpy import libraries, users

from tests.test_history_table import insert_history_row


def draw(columns, order_column):
    return {"json_data": json.dumps({
        "draw": 1, "start": 0, "length": 25,
        "search": {"value": "", "regex": False},
        "order": [{"column": order_column, "dir": "asc"}],
        "columns": [{"data": c, "name": "", "searchable": True, "orderable": True,
                     "search": {"value": "", "regex": False}} for c in columns],
    })}


def seed_overlapping_plays(app_db):
    plexpy.CONFIG.PMS_IDENTIFIER = "server"
    app_db.action("INSERT INTO users (user_id, username, friendly_name) VALUES (1, 'alice', 'Alice')")
    app_db.action("INSERT INTO library_sections (server_id, section_id, section_name, section_type) "
                  "VALUES ('server', 1, 'Movies', 'movie')")
    insert_history_row(app_db, 1, 1, 1, "alice", 8000, 8600, 301, "Later Movie", "movie")
    insert_history_row(app_db, 2, 2, 1, "alice", 7000, 7600, 302, "Earlier Movie", "movie")


def test_users_table_shows_the_play_that_matches_last_seen(app_db):
    seed_overlapping_plays(app_db)
    columns = ["edit", "user_thumb", "friendly_name", "last_seen", "last_played"]

    row = users.Users().get_datatables_list(kwargs=draw(columns, 2))["data"][0]

    assert row["last_seen"] == 8000
    assert row["last_played"] == "Later Movie"


def test_libraries_table_shows_the_play_that_matches_last_accessed(app_db):
    seed_overlapping_plays(app_db)
    columns = ["edit", "library_thumb", "section_name", "last_accessed", "last_played"]

    row = libraries.Libraries().get_datatables_list(kwargs=draw(columns, 2))["data"][0]

    assert row["last_accessed"] == 8000
    assert row["last_played"] == "Later Movie"
