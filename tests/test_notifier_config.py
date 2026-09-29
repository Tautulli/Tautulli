import pytest

from plexpy import newsletter_handler
from plexpy import newsletters
from plexpy import notifiers


# The settings form posts four spaces in place of a saved password, so the
# real password never reaches the browser. set_notifier_config and
# set_newsletter_config have to read that sentinel off the submitted value.
# They used to read it off the stored value instead, which is the password
# the sentinel is there to protect.

BLANK = '    '


@pytest.fixture
def email_notifier(app_db):
    # Agent 10 is Email, whose config carries smtp_password.
    notifier_id = notifiers.add_notifier_config(agent_id=10)
    notifiers.set_notifier_config(notifier_id=notifier_id, email_smtp_password='hunter2')
    return notifier_id


def test_blank_password_keeps_the_saved_notifier_password(email_notifier):
    assert notifiers.set_notifier_config(notifier_id=email_notifier,
                                         email_smtp_password=BLANK,
                                         email_smtp_server='mail.example.com',
                                         email_html_support='0') is True

    config = notifiers.get_notifier_config(notifier_id=email_notifier)['config']
    assert config['smtp_password'] == 'hunter2'
    # The rest of the form still applies, on both sides of the password. The
    # skipped key is one key, not the end of the loop.
    assert config['smtp_server'] == 'mail.example.com'
    assert config['html_support'] == 0


def test_a_real_password_replaces_the_saved_notifier_password(email_notifier):
    notifiers.set_notifier_config(notifier_id=email_notifier, email_smtp_password='correcthorse')

    assert notifiers.get_notifier_config(notifier_id=email_notifier)['config']['smtp_password'] == 'correcthorse'


def test_an_empty_password_clears_the_saved_notifier_password(email_notifier):
    # Only the four space sentinel is ignored. An empty string is the user
    # actually clearing the field.
    notifiers.set_notifier_config(notifier_id=email_notifier, email_smtp_password='')

    assert notifiers.get_notifier_config(notifier_id=email_notifier)['config']['smtp_password'] == ''


@pytest.fixture
def newsletter(app_db, app_config, monkeypatch):
    monkeypatch.setattr(newsletter_handler, 'schedule_newsletters', lambda **kwargs: None)
    # A newsletter agent builds its parameters on load, which resolves the
    # Tautulli URL. A bound HTTP_HOST keeps that off the network.
    app_config.HTTP_HOST = '127.0.0.1'
    newsletter_id = newsletters.add_newsletter_config(agent_id=0)
    newsletters.set_newsletter_config(newsletter_id=newsletter_id, newsletter_email_smtp_password='hunter2')
    return newsletter_id


def test_blank_password_keeps_the_saved_newsletter_password(newsletter):
    assert newsletters.set_newsletter_config(newsletter_id=newsletter,
                                             newsletter_email_smtp_password=BLANK,
                                             newsletter_email_smtp_server='mail.example.com',
                                             newsletter_email_html_support='0',
                                             newsletter_config_time_frame='14') is True

    config = newsletters.get_newsletter_config(newsletter_id=newsletter)
    assert config['email_config']['smtp_password'] == 'hunter2'
    assert config['email_config']['smtp_server'] == 'mail.example.com'
    assert config['email_config']['html_support'] == 0
    # The newsletter's own config keys go through a second loop of their own.
    assert config['config']['time_frame'] == 14


def test_a_real_password_replaces_the_saved_newsletter_password(newsletter):
    newsletters.set_newsletter_config(newsletter_id=newsletter, newsletter_email_smtp_password='correcthorse')

    email_config = newsletters.get_newsletter_config(newsletter_id=newsletter)['email_config']
    assert email_config['smtp_password'] == 'correcthorse'
