"""The user unique-IPs table keeps the archived filter and rows with no address."""

from plexpy import libraries, users

from tests.test_last_played_row import draw, seed_overlapping_plays


def test_user_ips_skip_an_archived_library(app_db):
    seed_overlapping_plays(app_db)
    app_db.action("INSERT INTO library_sections (server_id, section_id, section_name, section_type) "
                  "VALUES ('server', 2, 'Hidden', 'movie')")
    app_db.action("UPDATE session_history SET section_id = 2 WHERE id = 1")
    libraries.Libraries().set_config(section_id=2, is_archived=1)
    columns = ["last_seen", "first_seen", "ip_address", "play_count", "last_played"]

    row = users.Users().get_datatables_unique_ips(user_id=1, kwargs=draw(columns, 0))["data"][0]

    assert (row["last_seen"], row["play_count"], row["last_played"]) == (7000, 1, "Earlier Movie")


def test_user_ips_with_no_ip_address_still_show(app_db):
    seed_overlapping_plays(app_db)
    app_db.action("UPDATE session_history SET ip_address = NULL")
    columns = ["last_seen", "first_seen", "ip_address", "play_count", "last_played"]

    data = users.Users().get_datatables_unique_ips(user_id=1, kwargs=draw(columns, 0))["data"]

    assert [r["last_played"] for r in data] == ["Later Movie"]
