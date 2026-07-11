"""The cached library section types."""

import plexpy
from plexpy import libraries


def seed(app_db):
    plexpy.CONFIG.PMS_IDENTIFIER = "server"
    app_db.action("INSERT INTO users (user_id, username, friendly_name) VALUES (1, 'alice', 'Alice')")
    for section_id in (1, 2):
        app_db.action("INSERT INTO library_sections (server_id, section_id, section_name, section_type) "
                      "VALUES ('server', ?, ?, 'movie')", [section_id, "Lib%d" % section_id])


def test_restoring_a_library_by_section_id_refreshes_the_type_cache(app_db):
    seed(app_db)
    libraries.Libraries().delete(section_id=1, purge_only=False)
    libraries.Libraries().delete(section_id=2, purge_only=False)
    assert not libraries.has_library_type("movie")

    libraries.Libraries().undelete(section_id=1)

    assert libraries.has_library_type("movie")
