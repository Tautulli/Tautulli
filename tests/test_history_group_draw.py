"""A history draw bounded to one group."""

import json

import plexpy
from plexpy import datafactory

from tests.test_history_table import build_draw, insert_history_row


def seed(app_db):
    plexpy.CONFIG.PMS_IDENTIFIER = "server"
    app_db.action("INSERT INTO users (user_id, username, friendly_name) VALUES (1, 'alice', 'Alice')")
    for section_id in (1, 2):
        app_db.action("INSERT INTO library_sections (server_id, section_id, section_name, section_type) "
                      "VALUES ('server', ?, ?, 'movie')", [section_id, "Lib%d" % section_id])


def test_history_of_one_group_has_no_live_session_row(app_db):
    seed(app_db)
    insert_history_row(app_db, 1, 1, 1, "alice", 7000, 7600, 301, "Early", "movie")
    app_db.action("INSERT INTO sessions (session_key, state, view_offset, stopped, user_id) "
                  "VALUES (42, 'playing', 0, 5000, 1)")

    result = datafactory.DataFactory().get_datatables_history(
        kwargs={"json_data": json.dumps(build_draw(length=-1))},
        custom_where=[["session_history.reference_id IN", [1]]],
        grouping=False, include_activity=True)

    assert result["recordsFiltered"] == 1
    assert len(result["data"]) == 1
