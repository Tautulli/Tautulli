"""The home library cards of a guest."""

import plexpy
from plexpy import datafactory


def seed(app_db):
    plexpy.CONFIG.PMS_IDENTIFIER = "server"
    app_db.action("INSERT INTO users (user_id, username, friendly_name) VALUES (1, 'alice', 'Alice')")
    for section_id in (1, 2):
        app_db.action("INSERT INTO library_sections (server_id, section_id, section_name, section_type) "
                      "VALUES ('server', ?, ?, 'movie')", [section_id, "Lib%d" % section_id])


def test_home_library_cards_for_a_guest_hide_unshared_libraries(app_db, monkeypatch):
    seed(app_db)
    monkeypatch.setattr(plexpy.session, "get_session_shared_libraries", lambda: ("1",))
    monkeypatch.setattr(plexpy.session, "mask_session_info", lambda rows: rows)

    stats = datafactory.DataFactory().get_library_stats(library_cards=["1", "2"])

    assert [lib["section_id"] for group in stats.values() for lib in group] == [1]
