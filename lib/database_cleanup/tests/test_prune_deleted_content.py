import pytest
from unittest.mock import MagicMock, patch
import sqlite3

from lib.database_cleanup.prune_deleted_content import (
    PlexManager,
    HistoryPruner,
    main as pruner_main,
)
import logging


@pytest.fixture
def mock_plex():
    plex = MagicMock()
    section_movie = MagicMock()
    section_movie.type = "movie"
    section_movie.title = "Movies"
    section_movie.all.return_value = [
        MagicMock(ratingKey=1001),
        MagicMock(ratingKey=1002),
    ]

    section_show = MagicMock()
    section_show.type = "show"
    section_show.title = "TV Shows"
    section_show.all.return_value = [
        MagicMock(ratingKey=2001),
        MagicMock(ratingKey=2002),
    ]

    section_music = MagicMock()
    section_music.type = "artist"
    plex.library.sections.return_value = [section_movie, section_show, section_music]
    return plex


@pytest.fixture
def test_db(tmp_path):
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE watch_history (
            id INTEGER PRIMARY KEY,
            rating_key INTEGER NOT NULL,
            timestamp INTEGER
        )
    """
    )
    test_data = [
        (1001, 1625097600),
        (1002, 1625184000),
        (9999, 1625270400),  # Orphan
        (8888, 1625356800),  # Orphan
    ]
    conn.executemany(
        "INSERT INTO watch_history (rating_key, timestamp) VALUES (?, ?)", test_data
    )
    conn.commit()
    conn.close()
    return db_path


@pytest.mark.asyncio
async def test_plex_manager_fetch_ids(mock_plex):
    manager = PlexManager("http://test", "token")
    with patch("pruner.PlexServer", return_value=mock_plex):
        ids = await manager.fetch_all_media_ids()
    assert ids == {1001, 1002, 2001, 2002}


def test_history_pruner_get_history(test_db):
    pruner = HistoryPruner(test_db)
    assert set(pruner.get_watch_history()) == {1001, 1002, 9999, 8888}


def test_delete_orphans(test_db):
    pruner = HistoryPruner(test_db)
    pruner.delete_orphans([9999, 8888])

    conn = sqlite3.connect(test_db)
    remaining = conn.execute("SELECT rating_key FROM watch_history").fetchall()
    assert len(remaining) == 2
    assert {r[0] for r in remaining} == {1001, 1002}


@pytest.mark.asyncio
async def test_main_workflow(test_db, mock_plex, caplog):
    with patch("pruner.PlexManager") as mock_manager:
        mock_instance = mock_manager.return_value
        mock_instance.fetch_all_media_ids.return_value = {1001, 1002, 2001, 2002}

        args = MagicMock(
            db_path=test_db,
            plex_url="http://test",
            plex_token="token",
            plex_server=None,
            loglevel=logging.INFO,
        )

        await pruner_main(args)

        # Verify deletions
        conn = sqlite3.connect(test_db)
        remaining = conn.execute("SELECT rating_key FROM watch_history").fetchall()
        assert len(remaining) == 2

        # Verify logs
        assert "Found 4 watch history entries" in caplog.text
        assert "Identified 2 orphaned entries" in caplog.text
        assert "Deleted 2 orphaned entries" in caplog.text


def test_empty_database(tmp_path):
    db_path = tmp_path / "empty.db"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE watch_history (rating_key INTEGER)")
    conn.close()

    pruner = HistoryPruner(db_path)
    assert pruner.get_watch_history() == []
    pruner.delete_orphans([123])  # Shouldn't error
