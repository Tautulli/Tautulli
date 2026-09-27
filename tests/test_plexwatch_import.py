"""PlexWatch import (plexpy/plexwatch_import.py), end to end.

import_from_plexwatch reads a PlexWatch database and writes each play
through ActivityProcessor.write_session_history with is_import=True. It
passes an import_metadata dict that it builds from the stored session XML
in place of the Plex metadata a live play would fetch.
"""

import sqlite3

import pytest

from plexpy import database, plexwatch_import, users

XML = (
    '<opt ratingKey="100" type="movie" title="Imported Movie" guid="plex://movie/a" '
    'duration="1000" viewOffset="500" librarySectionID="1">'
    '<Media container="mkv" videoCodec="h264" audioCodec="aac"/>'
    '<Player address="10.0.0.1" machineIdentifier="machine-1" platform="Chrome" title="Chrome"/>'
    '<User id="7" title="alice"/>'
    '</opt>'
)

IMPORT_MARKERS_BUG = (
    "the importers build import_metadata without a 'markers' key, and "
    "write_session_history and group_history read metadata['markers'], so the "
    "import stops with a KeyError"
)


def make_plexwatch_db(path, plays):
    """A PlexWatch 'processed' table with the columns the importer selects,
    holding `plays` plays of the same movie by the same user."""
    connection = sqlite3.connect(path)
    connection.execute(
        "CREATE TABLE processed (id INTEGER PRIMARY KEY, time INTEGER, stopped INTEGER, "
        "ratingKey INTEGER, user TEXT, ip_address TEXT, paused_counter INTEGER, platform TEXT, "
        "parentRatingKey INTEGER, grandparentRatingKey INTEGER, xml TEXT, rating TEXT, "
        "summary TEXT, title TEXT, orig_title TEXT, orig_title_ep TEXT)"
    )
    for play in range(1, plays + 1):
        started = play * 1000000
        connection.execute(
            "INSERT INTO processed VALUES (?, ?, ?, 100, 'alice', '10.0.0.1', 0, 'Chrome', "
            "NULL, NULL, ?, '', '', 'Imported Movie', 'Imported Movie', '')",
            [play, started, started + 900, XML],
        )
    connection.commit()
    connection.close()


# One play goes through write_session_history only. A second play of the
# same item also makes group_history compare it with the first.
@pytest.mark.xfail(reason=IMPORT_MARKERS_BUG)
@pytest.mark.parametrize("plays", [1, 2])
def test_import_writes_every_play_with_metadata(app_db, tmp_path, monkeypatch, plays):
    # refresh_users asks the Plex server for the friends list.
    monkeypatch.setattr(users, "refresh_users", lambda: None)
    # The importer sets this module flag and clears it only at the end.
    monkeypatch.setattr(database, "IS_IMPORTING", False)
    path = str(tmp_path / "plexWatch.db")
    make_plexwatch_db(path, plays)

    plexwatch_import.import_from_plexwatch(path, "processed", import_ignore_interval=0)

    rows = app_db.select(
        "SELECT session_history.user_id, session_history.rating_key, session_history.view_offset, "
        "session_history_metadata.title, session_history_metadata.guid, session_history_metadata.duration "
        "FROM session_history JOIN session_history_metadata ON session_history.id = session_history_metadata.id"
    )
    assert [tuple(row.values()) for row in rows] == [(7, 100, 500, "Imported Movie", "plex://movie/a", 1000)] * plays
    assert database.IS_IMPORTING is False
