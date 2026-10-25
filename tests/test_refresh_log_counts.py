"""The refresh summary lines count what Plex returned and what was new.

The loops in refresh_users and refresh_libraries must keep the lists
that the summary lines count.
"""

import plexpy
from plexpy import libraries, plextv, pmsconnect, users

from tests.test_archive_users import FakePlexTV
from tests.test_history_table import seed_history


def info_messages(caplog, prefix):
    return [record.getMessage() for record in caplog.records
            if record.levelname == "INFO" and record.getMessage().startswith(prefix)]


def test_refresh_users_logs_the_returned_and_new_counts(app_db, monkeypatch, caplog):
    seed_history(app_db)
    plexpy.CONFIG.PMS_IDENTIFIER = "server"
    monkeypatch.setattr(plextv, "PlexTV", lambda: FakePlexTV([1, 2, 3, 4]))

    with caplog.at_level("INFO", logger="tautulli"):
        assert users.refresh_users() is True

    assert info_messages(caplog, "Tautulli Users :: Users list refreshed") == [
        "Tautulli Users :: Users list refreshed. 4 users returned, 2 new."]


class FakePmsConnect:
    def get_library_details(self):
        return [{"section_id": section_id, "section_name": "Library %d" % section_id,
                 "section_type": "movie", "agent": "", "thumb": "", "art": "",
                 "count": 0, "is_active": 1}
                for section_id in (1, 2, 3)]


def test_refresh_libraries_logs_the_returned_and_new_counts(app_db, monkeypatch, caplog):
    plexpy.CONFIG.PMS_IDENTIFIER = "server"
    plexpy.CONFIG.HOME_LIBRARY_CARDS = [1]
    app_db.action("INSERT INTO library_sections (server_id, section_id, section_name, section_type) "
                  "VALUES ('server', 1, 'Library 1', 'movie')")
    monkeypatch.setattr(pmsconnect, "PmsConnect", FakePmsConnect)

    with caplog.at_level("INFO", logger="tautulli"):
        assert libraries.refresh_libraries() is True

    assert info_messages(caplog, "Tautulli Libraries :: Libraries list refreshed") == [
        "Tautulli Libraries :: Libraries list refreshed. 3 libraries returned, 2 new."]
    assert plexpy.CONFIG.HOME_LIBRARY_CARDS == [1, 2, 3]
