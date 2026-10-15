import threading

import pytest

import plexpy
import plexpy.config as config_module


@pytest.fixture
def import_file(app_config, tmp_path, monkeypatch):
    imported = tmp_path / "imported.ini"
    imported.write_text("[General]\nhttp_port = 8282\n")
    monkeypatch.setattr(plexpy, "SIGNAL", None)
    monkeypatch.setattr(config_module, "IS_IMPORTING", False)
    thread = threading.Thread(target=lambda: None)
    monkeypatch.setattr(config_module, "IMPORT_THREAD", thread)
    return str(imported), thread


def test_success_clears_state_and_restarts(import_file, app_config, monkeypatch):
    path, _ = import_file
    seen = []
    monkeypatch.setattr(app_config, "write", lambda: seen.append(config_module.IS_IMPORTING))

    config_module.import_tautulli_config(path)

    assert seen == [True]
    assert config_module.IS_IMPORTING is False
    assert config_module.IMPORT_THREAD is None
    assert plexpy.SIGNAL == "restart"
    assert app_config.HTTP_PORT != 8282


@pytest.mark.parametrize("target", ["merge", "write"])
def test_exception_clears_state(import_file, app_config, monkeypatch, target):
    path, _ = import_file

    def boom(*args, **kwargs):
        raise RuntimeError("boom")

    if target == "merge":
        monkeypatch.setattr(app_config._config, "merge", boom)
    else:
        monkeypatch.setattr(app_config, "write", boom)

    with pytest.raises(RuntimeError):
        config_module.import_tautulli_config(path)

    assert config_module.IS_IMPORTING is False
    assert config_module.IMPORT_THREAD is None
    assert plexpy.SIGNAL is None


def test_backup_failure_clears_thread(import_file, monkeypatch):
    path, _ = import_file
    monkeypatch.setattr(config_module, "make_backup", lambda *args, **kwargs: False)

    assert config_module.import_tautulli_config(path, backup=True) is False

    assert config_module.IS_IMPORTING is False
    assert config_module.IMPORT_THREAD is None
    assert plexpy.SIGNAL is None


def test_unreadable_config_clears_thread(import_file, tmp_path):
    bad = tmp_path / "bad.ini"
    bad.write_text("[General\nbroken")

    assert config_module.import_tautulli_config(str(bad)) is False

    assert config_module.IS_IMPORTING is False
    assert config_module.IMPORT_THREAD is None
    assert plexpy.SIGNAL is None


def test_refused_call_keeps_running_import_state(import_file, monkeypatch):
    path, thread = import_file
    monkeypatch.setattr(config_module, "IS_IMPORTING", True)

    assert config_module.import_tautulli_config(path) is False

    assert config_module.IS_IMPORTING is True
    assert config_module.IMPORT_THREAD is thread
    assert plexpy.SIGNAL is None
