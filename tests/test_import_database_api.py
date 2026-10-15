"""cmd=import_database through API v2 must reach the database check.

API2 pops the "app" parameter from every call as the mobile app flag.
import_database once required "app", so the API always answered
"No app specified for import".
"""

import json
import threading

from plexpy import webserve  # noqa: F401  (registers import_database on API2)
from plexpy.api2 import API2


def test_api_import_database_reaches_validation(app_config, tmp_path, monkeypatch):
    app_config.API_ENABLED = 1
    app_config.API_KEY = "a" * 32
    app_config.CACHE_DIR = str(tmp_path / "cache")
    (tmp_path / "cache").mkdir()
    not_a_db = tmp_path / "not_a_database.db"
    not_a_db.write_text("this is not a sqlite file")

    def no_thread(*args, **kwargs):
        raise AssertionError("an import thread must not start")

    monkeypatch.setattr(threading.Thread, "start", no_thread)

    out = API2()._api_run(cmd="import_database", apikey=app_config.API_KEY,
                          database_path=str(not_a_db), method="merge")
    response = json.loads(out)["response"]

    assert response["result"] == "error"
    assert response["message"] == "Invalid database specified"


def test_api_import_database_passes_arguments_to_import(app_config, tmp_path, monkeypatch):
    app_config.API_ENABLED = 1
    app_config.API_KEY = "a" * 32
    app_config.CACHE_DIR = str(tmp_path / "cache")
    (tmp_path / "cache").mkdir()
    a_db = tmp_path / "other.db"
    a_db.write_text("stand-in")
    started = []

    class FakeThread:
        def __init__(self, target=None, kwargs=None):
            started.append((target, kwargs))

        def start(self):
            pass

    monkeypatch.setattr(webserve.database, "validate_database", lambda database=None: "success")
    monkeypatch.setattr(webserve.threading, "Thread", FakeThread)

    # table_name is a stale parameter from old clients and must land in kwargs.
    out = API2()._api_run(cmd="import_database", apikey=app_config.API_KEY,
                          database_path=str(a_db), method="overwrite", backup="true",
                          table_name="x")
    response = json.loads(out)["response"]

    assert response["result"] == "success"
    assert len(started) == 1
    target, kwargs = started[0]
    assert target is webserve.database.import_tautulli_db
    assert kwargs["method"] == "overwrite"
    assert kwargs["backup"] is True
