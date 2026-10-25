"""Deleting history invalidates the cached history totals."""

import threading

import plexpy
from plexpy import database, datafactory

from tests.test_history_table import insert_history_row


def seed(app_db):
    plexpy.CONFIG.PMS_IDENTIFIER = "server"
    app_db.action("INSERT INTO users (user_id, username, friendly_name) VALUES (1, 'alice', 'Alice')")
    for section_id in (1, 2):
        app_db.action("INSERT INTO library_sections (server_id, section_id, section_name, section_type) "
                      "VALUES ('server', ?, ?, 'movie')", [section_id, "Lib%d" % section_id])


def test_purge_user_history_bumps_the_history_version(app_db):
    seed(app_db)
    insert_history_row(app_db, 1, 1, 1, "alice", 7000, 7600, 301, "Early", "movie")
    before = database.history_version

    assert database.delete_user_history(user_id=1)

    assert database.history_version > before


def test_total_duration_read_during_a_row_delete_is_not_cached_as_current(app_db, monkeypatch):
    seed(app_db)
    insert_history_row(app_db, 1, 1, 1, "alice", 7000, 7600, 301, "Early", "movie")
    factory = datafactory.DataFactory()
    real = database.delete_rows_from_table

    def delete_then_read_elsewhere(table, row_ids):
        ok = real(table=table, row_ids=row_ids)
        if table == 'session_history':
            # Another thread reads while this transaction is still open.
            t = threading.Thread(target=factory.get_total_duration)
            t.start()
            t.join()
        return ok

    monkeypatch.setattr(database, "delete_rows_from_table", delete_then_read_elsewhere)
    database.delete_session_history_rows(row_ids="1")

    assert not (factory.get_total_duration() or 0)
