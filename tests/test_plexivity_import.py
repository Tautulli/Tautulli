"""Plexivity import (plexpy/plexivity_import.py), end to end.

import_from_plexivity reads a Plexivity database and writes each play
through ActivityProcessor.write_session_history with is_import=True. It
passes an import_metadata dict that it builds from the stored session XML
in place of the Plex metadata a live play would fetch.
"""

import sqlite3
import time

import pytest

from plexpy import database, plexivity_import, users

XML = (
    '<MediaContainer><Video ratingKey="200" type="movie" title="Imported Movie" '
    'guid="plex://movie/b" duration="1000" viewOffset="500" librarySectionID="1">'
    '<Media container="mkv" videoCodec="h264" audioCodec="aac"/>'
    '<Player address="10.0.0.1" machineIdentifier="machine-1" platform="Chrome" title="Chrome"/>'
    '<User id="7" title="alice"/>'
    '</Video></MediaContainer>'
)

IMPORT_METADATA_BUG = (
    "the Plexivity importer builds import_metadata without 'section_id' and "
    "'markers', and write_session_history and group_history read both, so the "
    "import stops with a KeyError. Its float stop time also fails the isdigit "
    "check, so the import time replaces it, and a stream with no stop time "
    "makes arrow.get(None) raise and stops the import"
)


def make_plexivity_db(path, plays):
    """A Plexivity 'stream' table with the columns the importer selects,
    holding `plays` plays of the same movie by the same user."""
    connection = sqlite3.connect(path)
    connection.execute(
        "CREATE TABLE stream (id INTEGER PRIMARY KEY, time INTEGER, stopped INTEGER, "
        "user TEXT, ip_address TEXT, paused_counter INTEGER, platform TEXT, xml TEXT, "
        "rating TEXT, summary TEXT, title TEXT, orig_title TEXT, orig_title_ep TEXT)"
    )
    for play in range(1, plays + 1):
        started = play * 1000000
        connection.execute(
            "INSERT INTO stream VALUES (?, ?, ?, 'alice', '10.0.0.1', 0, 'Chrome', ?, "
            "'', '', 'Imported Movie', 'Imported Movie', 'n/a')",
            [play, started, started + 900, XML],
        )
    connection.commit()
    connection.close()


# One play goes through write_session_history only. A second play of the
# same item also makes group_history compare it with the first.
@pytest.mark.xfail(reason=IMPORT_METADATA_BUG)
@pytest.mark.parametrize("plays", [1, 2])
def test_import_writes_every_play_with_metadata(app_db, tmp_path, monkeypatch, plays):
    # refresh_users asks the Plex server for the friends list.
    monkeypatch.setattr(users, "refresh_users", lambda: None)
    # The importer sets this module flag and clears it only at the end.
    monkeypatch.setattr(database, "IS_IMPORTING", False)
    path = str(tmp_path / "plexivity.db")
    make_plexivity_db(path, plays)

    plexivity_import.import_from_plexivity(path, "stream", import_ignore_interval=0)

    rows = app_db.select(
        "SELECT session_history.started, session_history.stopped, "
        "session_history.user_id, session_history.rating_key, session_history.section_id, "
        "session_history_metadata.title, session_history_metadata.guid, session_history_metadata.duration "
        "FROM session_history JOIN session_history_metadata ON session_history.id = session_history_metadata.id"
    )
    expected = [
        (play * 1000000, play * 1000000 + 900, 7, 200, 1, "Imported Movie", "plex://movie/b", 1000)
        for play in range(1, plays + 1)
    ]
    assert [tuple(row.values()) for row in rows] == expected
    assert database.IS_IMPORTING is False


# An interrupted stream can leave Plexivity's stopped column NULL. The import
# must go on past it. write_session_history gives an imported play with no
# stop time the import time, as it does for a PlexWatch play.
@pytest.mark.xfail(reason=IMPORT_METADATA_BUG)
def test_import_continues_past_a_play_without_stop_time(app_db, tmp_path, monkeypatch):
    monkeypatch.setattr(users, "refresh_users", lambda: None)
    monkeypatch.setattr(database, "IS_IMPORTING", False)
    path = str(tmp_path / "plexivity.db")
    make_plexivity_db(path, 2)
    connection = sqlite3.connect(path)
    connection.execute("UPDATE stream SET stopped = NULL WHERE id = 1")
    connection.commit()
    connection.close()
    before = int(time.time())

    plexivity_import.import_from_plexivity(path, "stream", import_ignore_interval=0)

    stops = [row["stopped"] for row in app_db.select("SELECT stopped FROM session_history ORDER BY id")]
    assert len(stops) == 2
    assert stops[0] >= before
    assert stops[1] == 2000900
    assert database.IS_IMPORTING is False
