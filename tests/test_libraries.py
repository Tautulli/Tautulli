"""Library details."""

import plexpy
from plexpy import libraries, webserve


def test_get_library_refreshes_a_missing_library_with_last_accessed(app_db, monkeypatch):
    # With no GROUP BY, the MAX() for last_accessed returned one row of NULLs
    # for a missing library. get_details took that row and skipped the refresh.
    plexpy.CONFIG.PMS_IDENTIFIER = "server"
    monkeypatch.setattr(libraries, "refresh_libraries", lambda: app_db.action(
        "INSERT INTO library_sections (server_id, section_id, section_name, section_type) "
        "VALUES ('server', 1, 'Movies', 'movie')"))

    result = webserve.WebInterface().get_library(section_id=1, include_last_accessed=1)

    assert (result["section_id"], result["section_name"]) == (1, "Movies")
