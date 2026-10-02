"""Stream details for a history row (datafactory.get_stream_details).

fd4e13b5 added transcode_decision to session_history, which made the
column ambiguous in the row_id query. a0f42d55 qualified it and gave the
three tables aliases. The guest filter still named
session_history.user_id, and SQLite rejects a table's own name once the
table has an alias, so every guest call raised "no such column". The
guest filter now names the alias.

The guest is simulated by patching session.get_session_user_id, as in
test_guest_history.py. bob (user_id 2) owns rows 3 and 5. alice owns
rows 1, 2, 4 and 6.
"""

import pytest

import plexpy.session
from plexpy import datafactory

from tests.test_history_table import seed_history


def stream_details(row_id):
    return datafactory.DataFactory().get_stream_details(row_id=row_id)


@pytest.fixture
def guest_bob(app_db, monkeypatch):
    seed_history(app_db)
    monkeypatch.setattr(plexpy.session, "get_session_user_id", lambda: "2")
    return app_db


def test_admin_gets_any_row(app_db):
    seed_history(app_db)

    assert stream_details(1)["title"] == "Alpha Show - Episode 1"
    assert stream_details(3)["title"] == "Beta Movie"


def test_guest_gets_their_own_row(guest_bob):
    details = stream_details(3)

    assert details["title"] == "Beta Movie"
    assert details["media_type"] == "movie"


def test_guest_gets_nothing_for_another_users_row(guest_bob):
    assert stream_details(1) == {}
