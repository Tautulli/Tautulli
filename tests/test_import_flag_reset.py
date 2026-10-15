import sqlite3

import pytest

import plexpy.database as database


@pytest.fixture(autouse=True)
def reset_flag():
    database.set_is_importing(False)
    yield
    database.set_is_importing(False)


def make_import_file(tmp_path):
    path = str(tmp_path / "import.db")
    connection = sqlite3.connect(path)
    connection.execute("CREATE TABLE history (ratingKey TEXT, xml TEXT)")
    connection.commit()
    connection.close()
    return path


def test_exception_in_tautulli_import_resets_flag(app_db, tmp_path, monkeypatch):
    def fail(self, query, args=None):
        raise RuntimeError("disk error")

    monkeypatch.setattr(database, "validate_database", lambda database=None: "success")
    monkeypatch.setattr(database.MonitorDatabase, "select_single", fail)

    try:
        with pytest.raises(RuntimeError):
            database.import_tautulli_db(database=str(tmp_path / "x.db"), method="merge")
    finally:
        app_db.connection.rollback()

    assert database.IS_IMPORTING is False


def test_flag_is_set_during_the_import_and_cleared_after(tmp_path, monkeypatch):
    seen = []
    monkeypatch.setattr(database, "_import_tautulli_db_rows", lambda *args: seen.append(database.IS_IMPORTING))
    monkeypatch.setattr(database, "validate_database", lambda database=None: "success")

    database.import_tautulli_db(database=make_import_file(tmp_path), method="merge")

    assert seen == [True]
    assert database.IS_IMPORTING is False
