import os
import time

# Pin timezone before anything else touches it.
os.environ["TZ"] = "UTC"
if hasattr(time, "tzset"):
    time.tzset()

import pytest

import plexpy
import plexpy.config
import plexpy.database
import plexpy.logger
import plexpy.session


@pytest.fixture(scope="session", autouse=True)
def quiet_logger():
    # initLogger() calls initHooks(), which replaces sys.excepthook and wraps
    # threading.Thread.__init__ process-wide. Calling it more than once stacks
    # the wrapper, so this must run exactly once per test session.
    plexpy.logger.initLogger(console=False, log_dir=False, verbose=False)


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    import socket

    def blocked_connect(*args, **kwargs):
        raise RuntimeError("network access blocked in tests")

    monkeypatch.setattr(socket.socket, "connect", blocked_connect)


@pytest.fixture(autouse=True)
def plexpy_globals():
    config = plexpy.CONFIG
    data_dir = plexpy.DATA_DIR
    db_file = plexpy.DB_FILE
    try:
        yield
    finally:
        plexpy.CONFIG = config
        plexpy.DATA_DIR = data_dir
        plexpy.DB_FILE = db_file


@pytest.fixture
def app_config(tmp_path, monkeypatch):
    config = plexpy.config.Config(str(tmp_path / "config.ini"))
    monkeypatch.setattr(plexpy, "CONFIG", config)
    yield config


@pytest.fixture
def app_db(tmp_path, app_config, monkeypatch):
    monkeypatch.setattr(plexpy, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(plexpy, "DB_FILE", str(tmp_path / "tautulli.db"))
    monkeypatch.setattr(plexpy.database, "FILENAME", "tautulli.db")
    monkeypatch.setattr(plexpy.session, "get_session_user_id", lambda: None)
    monkeypatch.setattr(plexpy.session, "friendly_name_to_username", lambda list_of_dicts: list_of_dicts)

    plexpy.dbcheck()

    yield plexpy.database.MonitorDatabase()
