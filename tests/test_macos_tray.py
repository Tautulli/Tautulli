import signal

import plexpy
from plexpy import macos


def test_tray_routes_sigterm_through_the_run_loop(monkeypatch):
    calls = []

    class FakeMachSignals:
        @staticmethod
        def signal(signum, handler):
            calls.append(("signal", signum, handler))

    class FakeTrayIcon:
        def run(self):
            calls.append(("run",))

    monkeypatch.setattr(macos, "MachSignals", FakeMachSignals, raising=False)
    tray = object.__new__(macos.MacOSSystemTray)
    tray.tray_icon = FakeTrayIcon()

    tray.start()

    assert calls == [("signal", signal.SIGTERM, tray.tray_quit), ("run",)]


def test_sigterm_handler_quits_like_the_menu_item(monkeypatch):
    monkeypatch.setattr(plexpy, "SIGNAL", None)
    tray = object.__new__(macos.MacOSSystemTray)

    tray.tray_quit(signal.SIGTERM)

    assert plexpy.SIGNAL == "shutdown"
