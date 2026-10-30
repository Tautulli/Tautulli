"""Newsletter cron triggers use the resolved system timezone.

CronTrigger without a timezone asks tzlocal for the local zone itself, which
raised ZoneInfoNotFoundError for unknown zone names and aborted startup.
"""

import zoneinfo

from apscheduler.schedulers.background import BackgroundScheduler

import plexpy
from plexpy import newsletter_handler


def _scheduler(monkeypatch):
    sched = BackgroundScheduler(timezone=zoneinfo.ZoneInfo("UTC"))
    sched.start(paused=True)
    monkeypatch.setattr(newsletter_handler, "NEWSLETTER_SCHED", sched)
    return sched


def _boom(*args, **kwargs):
    raise AssertionError("get_localzone must not be called")


def test_add_job_uses_sys_timezone(monkeypatch):
    sched = _scheduler(monkeypatch)
    monkeypatch.setattr(plexpy, "SYS_TIMEZONE", zoneinfo.ZoneInfo("America/Edmonton"))
    monkeypatch.setattr("apscheduler.triggers.cron.get_localzone", _boom)
    try:
        newsletter_handler.schedule_newsletter_job(
            "newsletter-1", name="t", func=print, args=[1, "on_cron"], cron="0 8 * * 1")
        job = sched.get_job("newsletter-1")
        assert job is not None
        assert str(job.trigger.timezone) == "America/Edmonton"
    finally:
        sched.shutdown(wait=False)


def test_reschedule_job_uses_sys_timezone(monkeypatch):
    sched = _scheduler(monkeypatch)
    monkeypatch.setattr(plexpy, "SYS_TIMEZONE", zoneinfo.ZoneInfo("UTC"))
    monkeypatch.setattr("apscheduler.triggers.cron.get_localzone", _boom)
    try:
        newsletter_handler.schedule_newsletter_job(
            "newsletter-2", name="t", func=print, args=[2, "on_cron"], cron="0 8 * * 1")
        monkeypatch.setattr(plexpy, "SYS_TIMEZONE", zoneinfo.ZoneInfo("Europe/Paris"))
        newsletter_handler.schedule_newsletter_job(
            "newsletter-2", name="t", func=print, args=[2, "on_cron"], cron="30 9 * * 2")
        assert str(sched.get_job("newsletter-2").trigger.timezone) == "Europe/Paris"
    finally:
        sched.shutdown(wait=False)
