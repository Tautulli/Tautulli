import os

import requests

import plexpy


def test_import_plexpy_helpers():
    import plexpy.helpers  # noqa: F401


def test_import_hashing_passwords():
    # This module only exists in lib/, so importing it proves lib/ is on sys.path.
    import hashing_passwords  # noqa: F401


def test_requests_is_the_vendored_copy():
    repo_lib_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lib")
    assert os.path.commonpath([os.path.abspath(requests.__file__), repo_lib_dir]) == repo_lib_dir


def test_app_config_defaults(app_config):
    assert app_config.DATE_FORMAT == "YYYY-MM-DD"
    assert app_config.PMS_PORT == 32400


def test_app_db_builds_schema(app_db):
    tables = app_db.select("SELECT name FROM sqlite_master WHERE type = 'table'")
    table_names = {row["name"] for row in tables}
    assert "session_history" in table_names


def test_dbcheck_twice_does_not_raise(app_db):
    plexpy.dbcheck()
