"""set_startup writes the launch agent plist when plexpy.ARGS is None.

Tautulli leaves ARGS unset when it starts without command line arguments.
"""

import plistlib
import sys

import pytest

import plexpy
from plexpy import macos


@pytest.fixture
def launch_agent(app_config, tmp_path, monkeypatch):
    monkeypatch.setattr(plexpy, "MAC_SYS_TRAY_ICON", None)
    monkeypatch.setattr(plexpy, "INSTALL_TYPE", "source")
    monkeypatch.setattr(plexpy, "FROZEN", False)
    monkeypatch.setattr(plexpy, "FULL_PATH", "/opt/Tautulli/Tautulli.py")
    monkeypatch.setattr(macos.os.path, "expanduser", lambda path: str(tmp_path))
    app_config.LAUNCH_STARTUP = 1
    return tmp_path / "Library/LaunchAgents/com.Tautulli.Tautulli.plist"


@pytest.mark.parametrize("args, expected", [
    (None, []),
    (["--nolaunch", "--port", "8282"], ["--port", "8282"]),
])
def test_startup_plist_program_arguments(launch_agent, monkeypatch, args, expected):
    monkeypatch.setattr(plexpy, "ARGS", args)

    assert macos.set_startup() is True

    with open(launch_agent, "rb") as f:
        assert plistlib.load(f)["ProgramArguments"] == [sys.executable, "/opt/Tautulli/Tautulli.py"] + expected
