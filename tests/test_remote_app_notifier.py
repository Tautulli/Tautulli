import json
import os
import types

import pytest

import plexpy
from plexpy import api2, mobile_app, notifiers, webserve


def device(push_token):
    return {'device_id': 'dev', 'device_name': 'Phone', 'friendly_name': '', 'device_token': 'apikey',
            'platform': 'android', 'push_token': push_token, 'official': 1}


def add_device(db, device_id, push_token, official=1):
    db.action("INSERT INTO mobile_devices (device_id, device_token, device_name, platform, "
              "push_token, official) VALUES (?, ?, ?, 'android', ?, ?)",
              args=[device_id, device_id, device_id, push_token, official])


def official(db, device_id):
    return db.select_single("SELECT official FROM mobile_devices WHERE device_id = ?", args=[device_id])['official']


@pytest.fixture
def relay(monkeypatch):
    sent = []

    def send(self, d, data):
        sent.append(data)
        return True

    monkeypatch.setattr(notifiers.TAUTULLIREMOTEAPP, '_send_via_relay', send)
    return sent


def notify(push_token, monkeypatch, body='B'):
    monkeypatch.setattr(mobile_app, 'get_mobile_devices', lambda device_id=None: [device(push_token)])
    agent = notifiers.TAUTULLIREMOTEAPP(config={'device_id': 'dev'})
    return agent.agent_notify(subject='S', body=body, parameters={})


@pytest.mark.parametrize('push_token', [None, ''])
def test_a_device_without_a_push_token_gets_nothing(relay, monkeypatch, push_token):
    assert notify(push_token, monkeypatch) is False
    assert relay == []


def test_a_long_notification_is_trimmed_and_sent_through_the_relay(app_config, relay, monkeypatch):
    assert notify('fcm-token', monkeypatch, body='x' * 5000) is True

    assert len(relay) == 1
    assert len(json.dumps(relay[0])) <= notifiers.TAUTULLIREMOTEAPP.MAX_DATA_BYTES


def test_get_devices_lists_only_official_relay_devices(app_db):
    add_device(app_db, 'onesignal', None)
    add_device(app_db, 'empty', '')
    add_device(app_db, 'disabled', mobile_app._PUSH_DISABLED)
    add_device(app_db, 'unofficial', 'fcm-token-2', official=0)
    add_device(app_db, 'relay', 'fcm-token')

    assert [d['device_id'] for d in notifiers.TAUTULLIREMOTEAPP().get_devices()] == ['relay']


@pytest.mark.parametrize('push_token, expected', [(None, False), ('', False),
                                                  (mobile_app._PUSH_DISABLED, False), ('fcm-token', True)])
def test_validates_remotely(push_token, expected):
    assert mobile_app.validates_remotely(device(push_token)) is expected


def test_set_official_clears_a_device_without_a_push_token(app_db):
    add_device(app_db, 'dev', None)

    mobile_app.set_official('dev', None)

    assert official(app_db, 'dev') == 0


def test_add_mobile_device_stores_and_validates_the_push_token(app_db, monkeypatch):
    calls = []

    class Thread:
        def __init__(self, target, args):
            self.run = lambda: target(*args)

        def start(self):
            self.run()

    monkeypatch.setattr(mobile_app, 'threading', types.SimpleNamespace(Thread=Thread))
    monkeypatch.setattr(mobile_app, 'set_official', lambda *args: calls.append(args))

    mobile_app.add_mobile_device(device_id='dev', device_name='Phone', device_token='apikey', push_token='fcm-token')

    assert mobile_app.get_mobile_devices(device_id='dev')[0]['push_token'] == 'fcm-token'
    assert calls == [('dev', 'fcm-token')]


def test_revalidate_passes_the_push_token(app_db, monkeypatch):
    calls = []
    add_device(app_db, 'dev', 'fcm-token', official=0)
    monkeypatch.setattr(mobile_app, '_REVALIDATE_INTERVAL', 0)
    monkeypatch.setattr(mobile_app, 'set_official', lambda *args: calls.append(args))

    mobile_app._revalidate_devices()

    assert calls == [('dev', 'fcm-token')]


@pytest.mark.parametrize('kwargs', [{'push_token': 'fcm-token', 'onesignal_id': 'os-id'}, {'onesignal_id': 'os-id'}])
def test_register_device_accepts_old_and_new_apps(app_config, monkeypatch, kwargs):
    calls = []
    monkeypatch.setattr(mobile_app, 'add_mobile_device', lambda **kw: calls.append(kw) or True)
    monkeypatch.setattr(api2.plextv, 'get_server_resources', lambda return_info: {})
    monkeypatch.setattr(plexpy, 'get_tautulli_info', dict)
    api = api2.API2()
    api._api_apikey = 'apikey'

    api.register_device(device_id='dev', device_name='Phone', **kwargs)

    assert api._api_result_type == 'success'
    assert calls[0]['push_token'] == kwargs.get('push_token')
    assert 'onesignal_id' not in calls[0]


@pytest.mark.parametrize('push_token, title', [(None, 'Not Registered for Notifications'),
                                               ('fcm-token', None)])
def test_device_table_flags_a_device_without_a_push_token(app_db, app_config, monkeypatch, push_token, title):
    add_device(app_db, 'dev', push_token)
    monkeypatch.setattr(webserve, 'TEMPLATE_LOOKUP', None)
    monkeypatch.setattr(plexpy, 'PROG_DIR', os.getcwd())
    app_config.INTERFACE = 'default'
    monkeypatch.setattr(webserve, 'get_session_info', dict)
    monkeypatch.setattr(webserve, 'get_session_csrf_token', lambda: '')
    monkeypatch.setattr(webserve.helpers, 'pms_name', lambda: '')
    monkeypatch.setattr(webserve.cherrypy.response, 'headers', {}, raising=False)

    page = webserve.serve_template('mobile_devices_table.html', devices_list=mobile_app.get_mobile_devices())

    assert ('Not Registered for Notifications' in page) is bool(title)
    assert ('fa-android' in page) is not bool(title)


def test_upgrade_drops_the_onesignal_column_and_keeps_the_devices(app_db):
    app_db.action("ALTER TABLE mobile_devices ADD COLUMN onesignal_id TEXT")
    app_db.action("INSERT INTO mobile_devices (device_id, device_token, device_name, platform, version, friendly_name, "
                  "onesignal_id, push_token, last_seen, official) "
                  "VALUES ('dev', 'apikey', 'Phone', 'ios', '3.0', 'Mine', 'os-id', 'fcm-token', 123, 1)")

    plexpy.dbcheck()

    assert app_db.select("SELECT * FROM mobile_devices") == [
        {'id': 1, 'device_id': 'dev', 'device_token': 'apikey', 'device_name': 'Phone', 'platform': 'ios',
         'version': '3.0', 'friendly_name': 'Mine', 'push_token': 'fcm-token', 'last_seen': 123, 'official': 1}]


def test_upgrade_recovers_from_a_leftover_temp_table(app_db):
    app_db.action("ALTER TABLE mobile_devices ADD COLUMN onesignal_id TEXT")
    app_db.action("CREATE TABLE mobile_devices_temp (id INTEGER)")
    add_device(app_db, 'dev', 'fcm-token')

    plexpy.dbcheck()

    tables = {r['name'] for r in app_db.select("SELECT name FROM sqlite_master WHERE name LIKE 'mobile_devices%'")}
    assert tables == {'mobile_devices'}
    assert [d['device_id'] for d in mobile_app.get_mobile_devices()] == ['dev']
    assert 'onesignal_id' not in mobile_app.get_mobile_devices()[0]
