"""The email agent sets a Reply-To header from its reply_to option.

The header is absent when the option is blank.
"""

import email
import smtplib

import pytest

from plexpy import notifiers


class FakeSMTP:
    sent = []

    def __init__(self, *args, **kwargs):
        pass

    def ehlo(self):
        pass

    def sendmail(self, sender, recipients, message):
        FakeSMTP.sent.append(email.message_from_string(message))

    def quit(self):
        pass


@pytest.fixture
def smtp(monkeypatch):
    FakeSMTP.sent = []
    monkeypatch.setattr(smtplib, "SMTP_SSL", FakeSMTP)
    return FakeSMTP


def send(**config):
    agent = notifiers.EMAIL(config={
        "from": "tautulli@example.com", "to": ["a@example.com"],
        "smtp_server": "mail.example.com", "html_support": 0, **config})
    assert agent.agent_notify(subject="Subject", body="Body") is True


def test_reply_to_header_is_set(smtp):
    send(reply_to="help@example.com")

    assert smtp.sent[0]["Reply-To"] == "help@example.com"


@pytest.mark.parametrize("config", [{}, {"reply_to": ""}])
def test_reply_to_header_is_absent_when_blank(smtp, config):
    send(**config)

    assert "Reply-To" not in smtp.sent[0]


def test_reply_to_is_a_config_option(app_db):
    options = notifiers.EMAIL(config={"reply_to": "help@example.com"}).return_config_options()

    option = next(o for o in options if o["name"] == "email_reply_to")
    assert option["value"] == "help@example.com"
