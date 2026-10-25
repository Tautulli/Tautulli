"""Newsletters run on their own queue and worker thread.

A newsletter render can make dozens of PMS calls and image uploads. On
the notification queue it held up every playback notification behind it.
"""

import queue

import plexpy
from plexpy import newsletter_handler


def test_newsletter_skips_the_notification_queue(monkeypatch):
    notify_queue = queue.Queue()
    newsletter_queue = queue.Queue()
    monkeypatch.setattr(plexpy, "NOTIFY_QUEUE", notify_queue)
    monkeypatch.setattr(newsletter_handler, "NEWSLETTER_QUEUE", newsletter_queue)

    newsletter_handler.add_newsletter_each(newsletter_id=7, notify_action="on_cron")

    assert notify_queue.empty()
    assert newsletter_queue.get_nowait() == {
        "newsletter": True, "newsletter_id": 7, "notify_action": "on_cron"}


def test_newsletter_worker_survives_a_failed_send(monkeypatch):
    newsletter_queue = queue.Queue()
    monkeypatch.setattr(newsletter_handler, "NEWSLETTER_QUEUE", newsletter_queue)
    sent = []

    def fake_notify(**kwargs):
        sent.append(kwargs["newsletter_id"])
        if len(sent) == 1:
            raise RuntimeError("render failed")

    monkeypatch.setattr(newsletter_handler, "notify", fake_notify)

    newsletter_queue.put({"newsletter_id": 1, "notify_action": "on_cron"})
    newsletter_queue.put({"newsletter_id": 2, "notify_action": "on_cron"})
    newsletter_queue.put(None)
    newsletter_handler.process_queue()

    assert sent == [1, 2]


def test_start_thread_runs_the_worker_as_a_daemon(monkeypatch):
    started = []

    class FakeThread:
        def __init__(self, target=None, **kwargs):
            self.target = target
            self.daemon = False

        def start(self):
            started.append((self.target, self.daemon))

    monkeypatch.setattr(newsletter_handler.threading, "Thread", FakeThread)

    newsletter_handler.start_thread()

    assert started == [(newsletter_handler.process_queue, True)]
