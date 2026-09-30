"""Archived libraries.

An archived library is hidden from the libraries table, the home
library cards, and every statistic. Its session_history
rows stay. The seed is the shared six-row history from test_history_table.
The fixture moves bob's rows 3 and 5 into a second library, section 2,
and the tests archive that library. alice keeps rows 1, 2, 4, 6 in
section 1.
"""

import pytest

import plexpy
from plexpy import datafactory, libraries, webserve

from tests.test_history_table import seed_history


@pytest.fixture
def two_libraries(app_db):
    seed_history(app_db)
    plexpy.CONFIG.PMS_IDENTIFIER = "server"
    for section_id, name in ((1, "Mixed"), (2, "Other")):
        app_db.action("INSERT INTO library_sections (server_id, section_id, section_name, section_type) "
                      "VALUES ('server', ?, ?, 'movie')", [section_id, name])
    app_db.action("UPDATE session_history SET section_id = 2 WHERE id IN (3, 5)")
    return app_db


def archive_other():
    libraries.Libraries().set_config(section_id=2, is_archived=1)


def test_archive_keeps_history_and_unarchive_restores(two_libraries):
    web = webserve.WebInterface()

    web.edit_library(section_id="2", is_archived="1")
    # An edit that leaves out is_archived keeps the library archived.
    web.edit_library(section_id="2", keep_history="1")

    assert two_libraries.select_single(
        "SELECT is_archived, keep_history, deleted_section FROM library_sections WHERE section_id = 2"
    ) == {"is_archived": 1, "keep_history": 1, "deleted_section": 0}
    assert two_libraries.select_single(
        "SELECT COUNT(*) AS plays FROM session_history WHERE section_id = 2") == {"plays": 2}

    web.edit_library(section_id="2", is_archived="0")
    assert two_libraries.select_single(
        "SELECT is_archived FROM library_sections WHERE section_id = 2") == {"is_archived": 0}


def test_get_library_returns_the_archive_flag(two_libraries):
    archive_other()
    web = webserve.WebInterface()

    assert web.get_library(section_id="2")["is_archived"] == 1
    assert web.get_library(section_id="1")["is_archived"] == 0


def test_libraries_table_hides_archived_until_asked(two_libraries):
    archive_other()

    shown = webserve.WebInterface().get_library_list(grouping=0)
    everyone = webserve.WebInterface().get_library_list(grouping=0, include_archived=1)

    assert {row["section_id"] for row in shown["data"]} == {1}
    assert {row["section_id"]: row["is_archived"] for row in everyone["data"]} == {1: 0, 2: 1}


def test_library_names_list_an_archived_library(two_libraries):
    # The settings page picks the home library cards from this list.
    archive_other()

    names = webserve.WebInterface().get_library_sections()

    assert {row["section_id"] for row in names} == {1, 2}


def test_home_library_cards_hide_archived_until_asked(two_libraries):
    archive_other()
    factory = datafactory.DataFactory()

    shown = factory.get_library_stats(library_cards=["1", "2"])
    everyone = factory.get_library_stats(library_cards=["1", "2"], include_archived=True)

    assert [card["section_id"] for card in shown["movie"]] == [1]
    assert {card["section_id"] for card in everyone["movie"]} == {1, 2}


def test_upgrade_adds_the_archive_column(app_db):
    app_db.action("ALTER TABLE library_sections DROP COLUMN is_archived")

    plexpy.dbcheck()

    app_db.action("INSERT INTO library_sections (server_id, section_id) VALUES ('server', 1)")
    assert app_db.select_single("SELECT is_archived FROM library_sections") == {"is_archived": 0}
