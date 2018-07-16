#  This file is part of Tautulli.
#
#  Tautulli is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  Tautulli is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with Tautulli.  If not, see <http://www.gnu.org/licenses/>.

import base64
import bleach
import json
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import email.utils
from paho.mqtt.publish import single
import os
import re
import requests
import smtplib
import subprocess
import sys
import threading
import time
from urllib import urlencode
from urlparse import urlparse
import uuid

try:
    from Cryptodome.Protocol.KDF import PBKDF2
    from Cryptodome.Cipher import AES
    from Cryptodome.Random import get_random_bytes
    from Cryptodome.Hash import HMAC, SHA1
    CRYPTODOME = True
except ImportError:
    try:
        from Crypto.Protocol.KDF import PBKDF2
        from Crypto.Cipher import AES
        from Crypto.Random import get_random_bytes
        from Crypto.Hash import HMAC, SHA1
        CRYPTODOME = True
    except ImportError:
        CRYPTODOME = False

import gntp.notifier
import facebook
import twitter
import pynma

import plexpy
import common
import database
import helpers
import logger
import mobile_app
import pmsconnect
import request
import users


BROWSER_NOTIFIERS = {}


AGENT_IDS = {'growl': 0,
             'prowl': 1,
             'xbmc': 2,
             'plex': 3,
             'nma': 4,
             'pushalot': 5,
             'pushbullet': 6,
             'pushover': 7,
             'osx': 8,
             'boxcar': 9,
             'email': 10,
             'twitter': 11,
             'ifttt': 12,
             'telegram': 13,
             'slack': 14,
             'scripts': 15,
             'facebook': 16,
             'browser': 17,
             'join': 18,
             'hipchat': 19,
             'discord': 20,
             'androidapp': 21,
             'groupme': 22,
             'mqtt': 23,
             'zapier': 24
             }

DEFAULT_CUSTOM_CONDITIONS = [{'parameter': '', 'operator': '', 'value': ''}]


def available_notification_agents():
    agents = [{'label': 'Tautulli Remote Android App',
               'name': 'androidapp',
               'id': AGENT_IDS['androidapp']
               },
              {'label': 'Boxcar',
               'name': 'boxcar',
               'id': AGENT_IDS['boxcar']
               },
              {'label': 'Browser',
               'name': 'browser',
               'id': AGENT_IDS['browser']
               },
              {'label': 'Discord',
               'name': 'discord',
               'id': AGENT_IDS['discord'],
               },
              {'label': 'Email',
               'name': 'email',
               'id': AGENT_IDS['email']
               },
              {'label': 'Facebook',
               'name': 'facebook',
               'id': AGENT_IDS['facebook']
               },
              {'label': 'GroupMe',
               'name': 'groupme',
               'id': AGENT_IDS['groupme']
               },
              {'label': 'Growl',
               'name': 'growl',
               'id': AGENT_IDS['growl']
               },
              {'label': 'Hipchat',
               'name': 'hipchat',
               'id': AGENT_IDS['hipchat']
               },
              {'label': 'IFTTT',
               'name': 'ifttt',
               'id': AGENT_IDS['ifttt']
               },
              {'label': 'Join',
               'name': 'join',
               'id': AGENT_IDS['join']
               },
              {'label': 'Kodi',
               'name': 'xbmc',
               'id': AGENT_IDS['xbmc']
               },
              {'label': 'Notify My Android',
               'name': 'nma',
               'id': AGENT_IDS['nma']
               },
              {'label': 'MQTT',
               'name': 'mqtt',
               'id': AGENT_IDS['mqtt']
               },
              {'label': 'Plex Home Theater',
               'name': 'plex',
               'id': AGENT_IDS['plex']
               },
              {'label': 'Prowl',
               'name': 'prowl',
               'id': AGENT_IDS['prowl']
               },
              # {'label': 'Pushalot',
              #  'name': 'pushalot',
              #  'id': AGENT_IDS['pushalot']
              #  },
              {'label': 'Pushbullet',
               'name': 'pushbullet',
               'id': AGENT_IDS['pushbullet']
               },
              {'label': 'Pushover',
               'name': 'pushover',
               'id': AGENT_IDS['pushover']
               },
              {'label': 'Script',
               'name': 'scripts',
               'id': AGENT_IDS['scripts']
               },
              {'label': 'Slack',
               'name': 'slack',
               'id': AGENT_IDS['slack']
               },
              {'label': 'Telegram',
               'name': 'telegram',
               'id': AGENT_IDS['telegram']
               },
              {'label': 'Twitter',
               'name': 'twitter',
               'id': AGENT_IDS['twitter']
               },
              {'label': 'Zapier',
               'name': 'zapier',
               'id': AGENT_IDS['zapier']
               }
              ]

    # OSX Notifications should only be visible if it can be used
    if OSX().validate():
        agents.append({'label': 'macOS Notification Center',
                       'name': 'osx',
                       'id': AGENT_IDS['osx']
                       })

    return agents


def available_notification_actions():
    actions = [{'label': 'Playback Start',
                'name': 'on_play',
                'description': 'Trigger a notification when a stream is started.',
                'subject': 'Tautulli ({server_name})',
                'body': '{user} ({player}) started playing {title}.',
                'icon': 'fa-play',
                'media_types': ('movie', 'episode', 'track')
                },
               {'label': 'Playback Stop',
                'name': 'on_stop',
                'description': 'Trigger a notification when a stream is stopped.',
                'subject': 'Tautulli ({server_name})',
                'body': '{user} ({player}) has stopped {title}.',
                'icon': 'fa-stop',
                'media_types': ('movie', 'episode', 'track')
                },
               {'label': 'Playback Pause',
                'name': 'on_pause',
                'description': 'Trigger a notification when a stream is paused.',
                'subject': 'Tautulli ({server_name})',
                'body': '{user} ({player}) has paused {title}.',
                'icon': 'fa-pause',
                'media_types': ('movie', 'episode', 'track')
                },
               {'label': 'Playback Resume',
                'name': 'on_resume',
                'description': 'Trigger a notification when a stream is resumed.',
                'subject': 'Tautulli ({server_name})',
                'body': '{user} ({player}) has resumed {title}.',
                'icon': 'fa-play',
                'media_types': ('movie', 'episode', 'track')
                },
               {'label': 'Watched',
                'name': 'on_watched',
                'description': 'Trigger a notification when a video stream reaches the specified watch percentage.',
                'subject': 'Tautulli ({server_name})',
                'body': '{user} ({player}) has watched {title}.',
                'icon': 'fa-eye',
                'media_types': ('movie', 'episode', 'track')
                },
               {'label': 'Buffer Warning',
                'name': 'on_buffer',
                'description': 'Trigger a notification when a stream exceeds the specified buffer threshold.',
                'subject': 'Tautulli ({server_name})',
                'body': '{user} ({player}) is buffering {title}.',
                'icon': 'fa-spinner',
                'media_types': ('movie', 'episode', 'track')
                },
               {'label': 'User Concurrent Streams',
                'name': 'on_concurrent',
                'description': 'Trigger a notification when a user exceeds the concurrent stream threshold.',
                'subject': 'Tautulli ({server_name})',
                'body': '{user} has {user_streams} concurrent streams.',
                'icon': 'fa-arrow-circle-o-right',
                'media_types': ('movie', 'episode', 'track')
                },
               {'label': 'User New Device',
                'name': 'on_newdevice',
                'description': 'Trigger a notification when a user streams from a new device.',
                'subject': 'Tautulli ({server_name})',
                'body': '{user} is streaming from a new device: {player}.',
                'icon': 'fa-desktop',
                'media_types': ('movie', 'episode', 'track')
                },
               {'label': 'Recently Added',
                'name': 'on_created',
                'description': 'Trigger a notification when a media item is added to the Plex Media Server.',
                'subject': 'Tautulli ({server_name})',
                'body': '{title} was recently added to Plex.',
                'icon': 'fa-download',
                'media_types': ('movie', 'show', 'season', 'episode', 'artist', 'album', 'track')
                },
               {'label': 'Plex Server Down',
                'name': 'on_intdown',
                'description': 'Trigger a notification when the Plex Media Server cannot be reached internally.',
                'subject': 'Tautulli ({server_name})',
                'body': 'The Plex Media Server is down.',
                'icon': 'fa-server',
                'media_types': ('server',)
                },
               {'label': 'Plex Server Back Up',
                'name': 'on_intup',
                'description': 'Trigger a notification when the Plex Media Server can be reached internally after being down.',
                'subject': 'Tautulli ({server_name})',
                'body': 'The Plex Media Server is back up.',
                'icon': 'fa-server',
                'media_types': ('server',)
                },
               {'label': 'Plex Remote Access Down',
                'name': 'on_extdown',
                'description': 'Trigger a notification when the Plex Media Server cannot be reached externally.',
                'subject': 'Tautulli ({server_name})',
                'body': 'The Plex Media Server remote access is down.',
                'icon': 'fa-server',
                'media_types': ('server',)
                },
               {'label': 'Plex Remote Access Back Up',
                'name': 'on_extup',
                'description': 'Trigger a notification when the Plex Media Server can be reached externally after being down.',
                'subject': 'Tautulli ({server_name})',
                'body': 'The Plex Media Server remote access is back up.',
                'icon': 'fa-server',
                'media_types': ('server',)
                },
               {'label': 'Plex Update Available',
                'name': 'on_pmsupdate',
                'description': 'Trigger a notification when an update for the Plex Media Server is available.',
                'subject': 'Tautulli ({server_name})',
                'body': 'An update is available for the Plex Media Server (version {update_version}).',
                'icon': 'fa-refresh',
                'media_types': ('server',)
                },
               {'label': 'Tautulli Update Available',
                'name': 'on_plexpyupdate',
                'description': 'Trigger a notification when an update for the Tautulli is available.',
                'subject': 'Tautulli ({server_name})',
                'body': 'An update is available for Tautulli (version {tautulli_update_version}).',
                'icon': 'fa-refresh',
                'media_types': ('server',)
                }
               ]

    return actions


def get_agent_class(agent_id=None, config=None):
    if str(agent_id).isdigit():
        agent_id = int(agent_id)

        if agent_id == 0:
            return GROWL(config=config)
        elif agent_id == 1:
            return PROWL(config=config)
        elif agent_id == 2:
            return XBMC(config=config)
        elif agent_id == 3:
            return PLEX(config=config)
        elif agent_id == 4:
            return NMA(config=config)
        elif agent_id == 5:
            return PUSHALOT(config=config)
        elif agent_id == 6:
            return PUSHBULLET(config=config)
        elif agent_id == 7:
            return PUSHOVER(config=config)
        elif agent_id == 8:
            return OSX(config=config)
        elif agent_id == 9:
            return BOXCAR(config=config)
        elif agent_id == 10:
            return EMAIL(config=config)
        elif agent_id == 11:
            return TWITTER(config=config)
        elif agent_id == 12:
            return IFTTT(config=config)
        elif agent_id == 13:
            return TELEGRAM(config=config)
        elif agent_id == 14:
            return SLACK(config=config)
        elif agent_id == 15:
            return SCRIPTS(config=config)
        elif agent_id == 16:
            return FACEBOOK(config=config)
        elif agent_id == 17:
            return BROWSER(config=config)
        elif agent_id == 18:
            return JOIN(config=config)
        elif agent_id == 19:
            return HIPCHAT(config=config)
        elif agent_id == 20:
            return DISCORD(config=config)
        elif agent_id == 21:
            return ANDROIDAPP(config=config)
        elif agent_id == 22:
            return GROUPME(config=config)
        elif agent_id == 23:
            return MQTT(config=config)
        elif agent_id == 24:
            return ZAPIER(config=config)
        else:
            return Notifier(config=config)
    else:
        return None


def get_notify_agents():
    return tuple(a['name'] for a in sorted(available_notification_agents(), key=lambda k: k['label']))


def get_notify_actions():
    return tuple(a['name'] for a in available_notification_actions())


def get_notifiers(notifier_id=None, notify_action=None):
    notify_actions = get_notify_actions()

    where = where_id = where_action = ''
    args = []

    if notifier_id or notify_action:
        where = 'WHERE '
        if notifier_id:
            where_id += 'id = ?'
            args.append(notifier_id)
        if notify_action and notify_action in notify_actions:
            where_action = '%s = ?' % notify_action
            args.append(1)
        where += ' AND '.join([w for w in [where_id, where_action] if w])

    db = database.MonitorDatabase()
    result = db.select('SELECT id, agent_id, agent_name, agent_label, friendly_name, %s FROM notifiers %s'
                       % (', '.join(notify_actions), where), args=args)

    for item in result:
        item['active'] = int(any([item.pop(k) for k in item.keys() if k in notify_actions]))

    return result


def delete_notifier(notifier_id=None):
    db = database.MonitorDatabase()

    if str(notifier_id).isdigit():
        logger.debug(u"Tautulli Notifiers :: Deleting notifier_id %s from the database."
                     % notifier_id)
        result = db.action('DELETE FROM notifiers WHERE id = ?', args=[notifier_id])
        return True
    else:
        return False


def get_notifier_config(notifier_id=None):
    if str(notifier_id).isdigit():
        notifier_id = int(notifier_id)
    else:
        logger.error(u"Tautulli Notifiers :: Unable to retrieve notifier config: invalid notifier_id %s."
                     % notifier_id)
        return None

    db = database.MonitorDatabase()
    result = db.select_single('SELECT * FROM notifiers WHERE id = ?', args=[notifier_id])

    if not result:
        return None

    try:
        config = json.loads(result.pop('notifier_config', '{}'))
        notifier_agent = get_agent_class(agent_id=result['agent_id'], config=config)
        notifier_config = notifier_agent.return_config_options()
    except Exception as e:
        logger.error(u"Tautulli Notifiers :: Failed to get notifier config options: %s." % e)
        return

    notify_actions = get_notify_actions()

    notifier_actions = {}
    notifier_text = {}
    for k in result.keys():
        if k in notify_actions:
            notifier_actions[k] = helpers.cast_to_int(result.pop(k))
            notifier_text[k] = {'subject': result.pop(k + '_subject'),
                                'body': result.pop(k + '_body')}

    try:
        result['custom_conditions'] = json.loads(result['custom_conditions'])
    except (ValueError, TypeError):
        result['custom_conditions'] = DEFAULT_CUSTOM_CONDITIONS

    if not result['custom_conditions_logic']:
        result['custom_conditions_logic'] = ''

    result['config'] = config
    result['config_options'] = notifier_config
    result['actions'] = notifier_actions
    result['notify_text'] = notifier_text

    return result


def add_notifier_config(agent_id=None, **kwargs):
    if str(agent_id).isdigit():
        agent_id = int(agent_id)
    else:
        logger.error(u"Tautulli Notifiers :: Unable to add new notifier: invalid agent_id %s."
                     % agent_id)
        return False

    agent = next((a for a in available_notification_agents() if a['id'] == agent_id), None)

    if not agent:
        logger.error(u"Tautulli Notifiers :: Unable to retrieve new notification agent: invalid agent_id %s."
                     % agent_id)
        return False

    agent_class = get_agent_class(agent_id=agent['id'])

    keys = {'id': None}
    values = {'agent_id': agent['id'],
              'agent_name': agent['name'],
              'agent_label': agent['label'],
              'friendly_name': '',
              'notifier_config': json.dumps(agent_class.config),
              'custom_conditions': json.dumps(DEFAULT_CUSTOM_CONDITIONS),
              'custom_conditions_logic': ''
              }

    if agent['name'] == 'scripts':
        for a in available_notification_actions():
            values[a['name'] + '_subject'] = ''
            values[a['name'] + '_body'] = ''
    else:
        for a in available_notification_actions():
            values[a['name'] + '_subject'] = a['subject']
            values[a['name'] + '_body'] = a['body']

    db = database.MonitorDatabase()
    try:
        db.upsert(table_name='notifiers', key_dict=keys, value_dict=values)
        notifier_id = db.last_insert_id()
        logger.info(u"Tautulli Notifiers :: Added new notification agent: %s (notifier_id %s)."
                    % (agent['label'], notifier_id))
        blacklist_logger()
        return notifier_id
    except Exception as e:
        logger.warn(u"Tautulli Notifiers :: Unable to add notification agent: %s." % e)
        return False


def set_notifier_config(notifier_id=None, agent_id=None, **kwargs):
    if str(agent_id).isdigit():
        agent_id = int(agent_id)
    else:
        logger.error(u"Tautulli Notifiers :: Unable to set existing notifier: invalid agent_id %s."
                     % agent_id)
        return False

    agent = next((a for a in available_notification_agents() if a['id'] == agent_id), None)

    if not agent:
        logger.error(u"Tautulli Notifiers :: Unable to retrieve existing notification agent: invalid agent_id %s."
                     % agent_id)
        return False

    notify_actions = get_notify_actions()
    config_prefix = agent['name'] + '_'

    actions = {k: helpers.cast_to_int(kwargs.pop(k))
               for k in kwargs.keys() if k in notify_actions}
    subject_text = {k: kwargs.pop(k)
                    for k in kwargs.keys() if k.startswith(notify_actions) and k.endswith('_subject')}
    body_text = {k: kwargs.pop(k)
                 for k in kwargs.keys() if k.startswith(notify_actions) and k.endswith('_body')}
    notifier_config = {k[len(config_prefix):]: kwargs.pop(k)
                       for k in kwargs.keys() if k.startswith(config_prefix)}

    agent_class = get_agent_class(agent_id=agent['id'], config=notifier_config)

    keys = {'id': notifier_id}
    values = {'agent_id': agent['id'],
              'agent_name': agent['name'],
              'agent_label': agent['label'],
              'friendly_name': kwargs.get('friendly_name', ''),
              'notifier_config': json.dumps(agent_class.config),
              'custom_conditions': kwargs.get('custom_conditions', json.dumps(DEFAULT_CUSTOM_CONDITIONS)),
              'custom_conditions_logic': kwargs.get('custom_conditions_logic', ''),
              }
    values.update(actions)
    values.update(subject_text)
    values.update(body_text)

    db = database.MonitorDatabase()
    try:
        db.upsert(table_name='notifiers', key_dict=keys, value_dict=values)
        logger.info(u"Tautulli Notifiers :: Updated notification agent: %s (notifier_id %s)."
                    % (agent['label'], notifier_id))
        blacklist_logger()

        if agent['name'] == 'browser':
            check_browser_enabled()

        return True
    except Exception as e:
        logger.warn(u"Tautulli Notifiers :: Unable to update notification agent: %s." % e)
        return False


def send_notification(notifier_id=None, subject='', body='', notify_action='', notification_id=None, **kwargs):
    notifier_config = get_notifier_config(notifier_id=notifier_id)
    if notifier_config:
        agent = get_agent_class(agent_id=notifier_config['agent_id'],
                                config=notifier_config['config'])
        return agent.notify(subject=subject,
                            body=body,
                            action=notify_action.split('on_')[-1],
                            notification_id=notification_id,
                            **kwargs)
    else:
        logger.debug(u"Tautulli Notifiers :: Notification requested but no notifier_id received.")


def blacklist_logger():
    db = database.MonitorDatabase()
    notifiers = db.select('SELECT notifier_config FROM notifiers')

    for n in notifiers:
        config = json.loads(n['notifier_config'] or '{}')
        logger.blacklist_config(config)


class PrettyMetadata(object):
    def __init__(self, parameters=None):
        self.parameters = parameters or {}
        self.media_type = self.parameters.get('media_type')

    @staticmethod
    def get_movie_providers():
        return {'': '',
                'plexweb': 'Plex Web',
                'imdb': 'IMDB',
                'themoviedb': 'The Movie Database',
                'trakt': 'Trakt.tv'
                }

    @staticmethod
    def get_tv_providers():
        return {'': '',
                'plexweb': 'Plex Web',
                'imdb': 'IMDB',
                'themoviedb': 'The Movie Database',
                'thetvdb': 'TheTVDB',
                'tvmaze': 'TVmaze',
                'trakt': 'Trakt.tv'
                }

    @staticmethod
    def get_music_providers():
        return {'': '',
                'plexweb': 'Plex Web',
                'lastfm': 'Last.fm'
                }

    def get_poster_url(self):
        poster_url = self.parameters['poster_url']
        if not poster_url:
            if self.media_type in ('artist', 'album', 'track'):
                poster_url = common.ONLINE_COVER_THUMB
            else:
                poster_url = common.ONLINE_POSTER_THUMB
        return poster_url

    def get_provider_name(self, provider):
        provider_name = ''
        if provider == 'plexweb':
            provider_name = 'Plex Web'
        elif provider == 'imdb':
            provider_name = 'IMDb'
        elif provider == 'thetvdb':
            provider_name = 'TheTVDB'
        elif provider == 'themoviedb':
            provider_name = 'The Movie Database'
        elif provider == 'tvmaze':
            provider_name = 'TVmaze'
        elif provider == 'trakt':
            provider_name = 'Trakt.tv'
        elif provider == 'lastfm':
            provider_name = 'Last.fm'
        # else:
        #     if self.media_type == 'movie':
        #         provider_name = 'IMDb'
        #     elif self.media_type in ('show', 'season', 'episode'):
        #         provider_name = 'TheTVDB'
        #     elif self.media_type in ('artist', 'album', 'track'):
        #         provider_name = 'Last.fm'
        return provider_name

    def get_provider_link(self, provider=None):
        provider_link = ''
        if provider == 'plexweb':
            provider_link = self.get_plex_url()
        elif provider:
            provider_link = self.parameters.get(provider + '_url', '')
        # else:
        #     if self.media_type == 'movie':
        #         provider_link = self.parameters.get('imdb_url', '')
        #     elif self.media_type in ('show', 'season', 'episode'):
        #         provider_link = self.parameters.get('thetvdb_url', '')
        #     elif self.media_type in ('artist', 'album', 'track'):
        #         provider_link = self.parameters.get('lastfm_url', '')
        return provider_link

    def get_caption(self, provider):
        provider_name = self.get_provider_name(provider)
        return 'View on ' + provider_name

    def get_title(self, divider='-'):
        title = ''
        if self.media_type == 'movie':
            title = '%s (%s)' % (self.parameters['title'], self.parameters['year'])
        elif self.media_type == 'show':
            title = '%s (%s)' % (self.parameters['show_name'], self.parameters['year'])
        elif self.media_type == 'season':
            title = '%s - Season %s' % (self.parameters['show_name'], self.parameters['season_num'])
        elif self.media_type == 'episode':
            title = '%s - %s (S%s %s E%s)' % (self.parameters['show_name'],
                                              self.parameters['episode_name'],
                                              self.parameters['season_num'],
                                              divider,
                                              self.parameters['episode_num'])
        elif self.media_type == 'artist':
            title = self.parameters['artist_name']
        elif self.media_type == 'album':
            title = '%s - %s' % (self.parameters['artist_name'], self.parameters['album_name'])
        elif self.media_type == 'track':
            title = '%s - %s' % (self.parameters['track_name'], self.parameters['track_artist'])
        return title.encode("utf-8")

    def get_description(self):
        if self.media_type == 'track':
            description = self.parameters['album_name']
        else:
            description = self.parameters['summary']
        return description.encode("utf-8")

    def get_plex_url(self):
        return self.parameters['plex_url']

    @staticmethod
    def get_parameters():
        parameters = {param['value']: param['name']
                for category in common.NOTIFICATION_PARAMETERS for param in category['parameters']}
        parameters[''] = ''
        return parameters


class Notifier(object):
    NAME = ''
    _DEFAULT_CONFIG = {}

    def __init__(self, config=None):
        self.config = self.set_config(config=config, default=self._DEFAULT_CONFIG)

    def set_config(self, config=None, default=None):
        return self._validate_config(config=config, default=default)

    def _validate_config(self, config=None, default=None):
        if config is None:
            return default

        new_config = {}
        for k, v in default.iteritems():
            if isinstance(v, int):
                new_config[k] = helpers.cast_to_int(config.get(k, v))
            elif isinstance(v, list):
                c = config.get(k, v)
                if not isinstance(c, list):
                    new_config[k] = [c]
                else:
                    new_config[k] = c
            else:
                new_config[k] = config.get(k, v)

        return new_config

    def return_default_config(self):
        return self._DEFAULT_CONFIG.copy()

    def notify(self, subject='', body='', action='', **kwargs):
        if self.NAME != 'Script':
            if not subject and self.config.get('incl_subject', True):
                logger.error(u"Tautulli Notifiers :: %s notification subject cannot be blank." % self.NAME)
                return
            elif not body:
                logger.error(u"Tautulli Notifiers :: %s notification body cannot be blank." % self.NAME)
                return

        return self.agent_notify(subject=subject, body=body, action=action, **kwargs)

    def agent_notify(self, subject='', body='', action='', **kwargs):
        pass

    def make_request(self, url, method='POST', **kwargs):
        response, err_msg, req_msg = request.request_response2(url, method, **kwargs)

        if response and not err_msg:
            logger.info(u"Tautulli Notifiers :: {name} notification sent.".format(name=self.NAME))
            return True

        else:
            verify_msg = ""
            if response is not None and response.status_code >= 400 and response.status_code < 500:
                verify_msg = " Verify you notification agent settings are correct."

            logger.error(u"Tautulli Notifiers :: {name} notification failed.{msg}".format(msg=verify_msg, name=self.NAME))

            if err_msg:
                logger.error(u"Tautulli Notifiers :: {}".format(err_msg))

            if req_msg:
                logger.debug(u"Tautulli Notifiers :: Request response: {}".format(req_msg))

            return False

    def return_config_options(self):
        config_options = []
        return config_options


class ANDROIDAPP(Notifier):
    """
    Tautulli Remote Android app notifications
    """
    NAME = 'Tautulli Remote Android App'
    _DEFAULT_CONFIG = {'device_id': '',
                       'priority': 3
                       }

    _ONESIGNAL_APP_ID = '3b4b666a-d557-4b92-acdf-e2c8c4b95357'

    def agent_notify(self, subject='', body='', action='', notification_id=None, **kwargs):
        # Check mobile device is still registered
        device = mobile_app.get_mobile_devices(device_id=self.config['device_id'])
        if not device:
            logger.warn(u"Tautulli Notifiers :: Unable to send Android app notification: device not registered.")
            return
        else:
            device = device[0]

        pretty_metadata = PrettyMetadata(kwargs.get('parameters'))

        plaintext_data = {'notification_id': notification_id,
                          'subject': subject.encode('UTF-8'),
                          'body': body.encode('UTF-8'),
                          'action': action.encode('UTF-8'),
                          'priority': self.config['priority'],
                          'session_key': pretty_metadata.parameters.get('session_key',''),
                          'session_id': pretty_metadata.parameters.get('session_id',''),
                          'user_id': pretty_metadata.parameters.get('user_id',''),
                          'rating_key': pretty_metadata.parameters.get('rating_key',''),
                          'poster_thumb': pretty_metadata.parameters.get('poster_thumb','')}

        #logger.debug("Plaintext data: {}".format(plaintext_data))

        if CRYPTODOME:
            # Key generation
            salt = get_random_bytes(16)
            passphrase = device['device_token']
            key_length = 32  # AES256
            iterations = 1000
            key = PBKDF2(passphrase, salt, dkLen=key_length, count=iterations,
                         prf=lambda p, s: HMAC.new(p, s, SHA1).digest())

            #logger.debug("Encryption key (base64): {}".format(base64.b64encode(key)))

            # Encrypt using AES GCM
            nonce = get_random_bytes(16)
            cipher = AES.new(key, AES.MODE_GCM, nonce)
            encrypted_data, gcm_tag = cipher.encrypt_and_digest(json.dumps(plaintext_data))
            encrypted_data += gcm_tag

            #logger.debug("Encrypted data (base64): {}".format(base64.b64encode(encrypted_data)))
            #logger.debug("GCM tag (base64): {}".format(base64.b64encode(gcm_tag)))
            #logger.debug("Nonce (base64): {}".format(base64.b64encode(nonce)))
            #logger.debug("Salt (base64): {}".format(base64.b64encode(salt)))

            payload = {'app_id': self._ONESIGNAL_APP_ID,
                       'include_player_ids': [self.config['device_id']],
                       'contents': {'en': 'Tautulli Notification'},
                       'data': {'encrypted': True,
                                'cipher_text': base64.b64encode(encrypted_data),
                                'nonce': base64.b64encode(nonce),
                                'salt': base64.b64encode(salt)}
                       }
        else:
            logger.warn(u"Tautulli Notifiers :: PyCryptodome library is missing. "
                        "Android app notifications will be sent unecrypted. "
                        "Install the library to encrypt the notifications.")

            payload = {'app_id': self._ONESIGNAL_APP_ID,
                       'include_player_ids': [self.config['device_id']],
                       'contents': {'en': 'Tautulli Notification'},
                       'data': {'encrypted': False,
                                'plain_text': plaintext_data}
                       }

        #logger.debug("OneSignal payload: {}".format(payload))

        headers = {'Content-Type': 'application/json'}

        return self.make_request("https://onesignal.com/api/v1/notifications", headers=headers, json=payload)

    def get_devices(self):
        db = database.MonitorDatabase()

        try:
            query = 'SELECT * FROM mobile_devices'
            result = db.select(query=query)
        except Exception as e:
            logger.warn(u"Tautulli Notifiers :: Unable to retrieve Android app devices list: %s." % e)
            return {'': ''}

        devices = {}
        for device in result:
            if device['friendly_name']:
                devices[device['device_id']] = device['friendly_name']
            else:
                devices[device['device_id']] = device['device_name']

        return devices

    def return_config_options(self):
        config_option = []

        if not CRYPTODOME:
            config_option.append({
                'label': 'Warning',
                'description': '<strong>The PyCryptodome library is missing. '
                               'The content of your notifications will be sent unencrypted!</strong><br>'
                               'Please install the library to encrypt the notification contents. '
                               'Instructions can be found in the '
                               '<a href="https://github.com/%s/%s-Wiki/wiki/'
                               'Frequently-Asked-Questions#notifications-pycryptodome'
                               '" target="_blank">FAQ</a>.' % (plexpy.CONFIG.GIT_USER, plexpy.CONFIG.GIT_REPO),
                'input_type': 'help'
                })
        else:
            config_option.append({
                'label': 'Note',
                'description': 'The PyCryptodome library was found. '
                               'The content of your notifications will be sent encrypted!',
                'input_type': 'help'
                })

        config_option[-1]['description'] += '<br><br>Notifications are sent using the ' \
            '<a href="' + helpers.anon_url('https://onesignal.com') + '" target="_blank">' \
            'OneSignal</a> API. Some user data is collected and cannot be encrypted. ' \
            'Please read the <a href="' + helpers.anon_url(
                'https://onesignal.com/privacy_policy') + '" target="_blank">' \
            'OneSignal Privacy Policy</a> for more details.'

        devices = self.get_devices()

        if not devices:
            config_option.append({
                'label': 'Device',
                'description': 'No devices registered. '
                               '<a data-tab-destination="tabs-android_app" data-toggle="tab" data-dismiss="modal" '
                               'data-target="#top">Get the Android App</a> and register a device.',
                'input_type': 'help'
                })
        else:
            config_option.append({
                'label': 'Device',
                'value': self.config['device_id'],
                'name': 'androidapp_device_id',
                'description': 'Set your Android app device or '
                               '<a data-tab-destination="tabs-android_app" data-toggle="tab" data-dismiss="modal" '
                               'data-target="#top">register a new device</a> with Tautulli.',
                'input_type': 'select',
                'select_options': devices
                })

        config_option.append({
            'label': 'Priority',
            'value': self.config['priority'],
            'name': 'androidapp_priority',
            'description': 'Set the notification priority.',
            'input_type': 'select',
            'select_options': {1: 'Minimum', 2: 'Low', 3: 'Normal', 4: 'High'}
            })

        return config_option


class BOXCAR(Notifier):
    """
    Boxcar notifications
    """
    NAME = 'Boxcar'
    _DEFAULT_CONFIG = {'token': '',
                       'sound': ''
                       }

    def agent_notify(self, subject='', body='', action='', **kwargs):
        data = {'user_credentials': self.config['token'],
                'notification[title]': subject.encode('utf-8'),
                'notification[long_message]': body.encode('utf-8'),
                'notification[sound]': self.config['sound']
                }

        return self.make_request('https://new.boxcar.io/api/notifications', params=data)

    def get_sounds(self):
        sounds = {'': '',
                  'beep-crisp': 'Beep (Crisp)',
                  'beep-soft': 'Beep (Soft)',
                  'bell-modern': 'Bell (Modern)',
                  'bell-one-tone': 'Bell (One Tone)',
                  'bell-simple': 'Bell (Simple)',
                  'bell-triple': 'Bell (Triple)',
                  'bird-1': 'Bird (1)',
                  'bird-2': 'Bird (2)',
                  'boing': 'Boing',
                  'cash': 'Cash',
                  'clanging': 'Clanging',
                  'detonator-charge': 'Detonator Charge',
                  'digital-alarm': 'Digital Alarm',
                  'done': 'Done',
                  'echo': 'Echo',
                  'flourish': 'Flourish',
                  'harp': 'Harp',
                  'light': 'Light',
                  'magic-chime':'Magic Chime',
                  'magic-coin': 'Magic Coin',
                  'no-sound': 'No Sound',
                  'notifier-1': 'Notifier (1)',
                  'notifier-2': 'Notifier (2)',
                  'notifier-3': 'Notifier (3)',
                  'orchestral-long': 'Orchestral (Long)',
                  'orchestral-short': 'Orchestral (Short)',
                  'score': 'Score',
                  'success': 'Success',
                  'up': 'Up'}

        return sounds

    def return_config_options(self):
        config_option = [{'label': 'Boxcar Access Token',
                          'value': self.config['token'],
                          'name': 'boxcar_token',
                          'description': 'Your Boxcar access token.',
                          'input_type': 'text'
                          },
                         {'label': 'Sound',
                          'value': self.config['sound'],
                          'name': 'boxcar_sound',
                          'description': 'Set the notification sound. Leave blank for the default sound.',
                          'input_type': 'select',
                          'select_options': self.get_sounds()
                          }
                         ]

        return config_option


class BROWSER(Notifier):
    """
    Browser notifications
    """
    NAME = 'Browser'
    _DEFAULT_CONFIG = {'auto_hide_delay': 5
                       }

    def agent_notify(self, subject='', body='', action='', **kwargs):
        logger.info(u"Tautulli Notifiers :: {name} notification sent.".format(name=self.NAME))
        return True

    def return_config_options(self):
        config_option = [{'label': 'Allow Notifications',
                          'value': 'Allow Notifications',
                          'name': 'browser_allow_browser',
                          'description': 'Click to allow browser notifications. You must click this button for each browser.',
                          'input_type': 'button'
                          },
                         {'label': 'Auto Hide Delay',
                          'value': self.config['auto_hide_delay'],
                          'name': 'browser_auto_hide_delay',
                          'description': 'Set the number of seconds for the notification to remain visible. \
                                          Set 0 to disable auto hiding. (Note: Some browsers have a maximum time limit.)',
                          'input_type': 'number'
                          }
                         ]

        return config_option


class DISCORD(Notifier):
    """
    Discord Notifications
    """
    NAME = 'Discord'
    _DEFAULT_CONFIG = {'hook': '',
                       'username': '',
                       'avatar_url': '',
                       'color': '',
                       'tts': 0,
                       'incl_subject': 1,
                       'incl_card': 0,
                       'incl_description': 1,
                       'incl_thumbnail': 0,
                       'incl_pmslink': 0,
                       'movie_provider': '',
                       'tv_provider': '',
                       'music_provider': ''
                       }

    def agent_notify(self, subject='', body='', action='', **kwargs):
        if self.config['incl_subject']:
            text = subject.encode('utf-8') + '\r\n' + body.encode("utf-8")
        else:
            text = body.encode("utf-8")

        data = {'content': text}
        if self.config['username']:
            data['username'] = self.config['username']
        if self.config['avatar_url']:
            data['avatar_url'] = self.config['avatar_url']
        if self.config['tts']:
            data['tts'] = True

        if self.config['incl_card'] and kwargs.get('parameters', {}).get('media_type'):
            # Grab formatted metadata
            pretty_metadata = PrettyMetadata(kwargs['parameters'])

            if pretty_metadata.media_type == 'movie':
                provider = self.config['movie_provider']
            elif pretty_metadata.media_type in ('show', 'season', 'episode'):
                provider = self.config['tv_provider']
            elif pretty_metadata.media_type in ('artist', 'album', 'track'):
                provider = self.config['music_provider']
            else:
                provider = None

            poster_url = pretty_metadata.get_poster_url()
            provider_name = pretty_metadata.get_provider_name(provider)
            provider_link = pretty_metadata.get_provider_link(provider)
            title = pretty_metadata.get_title('\xc2\xb7'.decode('utf8'))
            description = pretty_metadata.get_description()
            plex_url = pretty_metadata.get_plex_url()

            # Build Discord post attachment
            attachment = {'title': title,
                          'timestamp': helpers.utc_now_iso()
                          }

            if self.config['color']:
                hex_match = re.match(r'^#([0-9a-fA-F]{3}){1,2}$', self.config['color'])
                if hex_match:
                    hex = hex_match.group(0).lstrip('#')
                    hex = ''.join(h * 2 for h in hex) if len(hex) == 3 else hex
                    attachment['color'] = helpers.hex_to_int(hex)

            if self.config['incl_thumbnail']:
                attachment['thumbnail'] = {'url': poster_url}
            else:
                attachment['image'] = {'url': poster_url}

            if self.config['incl_description'] or pretty_metadata.media_type in ('artist', 'album', 'track'):
                attachment['description'] = description

            fields = []
            if provider_link:
                attachment['url'] = provider_link
                fields.append({'name': 'View Details',
                               'value': '[%s](%s)' % (provider_name, provider_link.encode('utf-8')),
                               'inline': True})
            if self.config['incl_pmslink']:
                fields.append({'name': 'View Details',
                               'value': '[Plex Web](%s)' % plex_url.encode('utf-8'),
                               'inline': True})
            if fields:
                attachment['fields'] = fields

            data['embeds'] = [attachment]

        headers = {'Content-type': 'application/json'}
        params = {'wait': True}

        return self.make_request(self.config['hook'], params=params, headers=headers, json=data)

    def return_config_options(self):
        config_option = [{'label': 'Discord Webhook URL',
                          'value': self.config['hook'],
                          'name': 'discord_hook',
                          'description': 'Your Discord incoming webhook URL.',
                          'input_type': 'text'
                          },
                         {'label': 'Discord Username',
                          'value': self.config['username'],
                          'name': 'discord_username',
                          'description': 'The Discord username which will be used. Leave blank for webhook integration default.',
                          'input_type': 'text'
                          },
                         {'label': 'Discord Avatar',
                          'value': self.config['avatar_url'],
                          'description': 'The image url for the avatar which will be used. Leave blank for webhook integration default.',
                          'name': 'discord_avatar_url',
                          'input_type': 'text'
                          },
                         {'label': 'Discord Color',
                          'value': self.config['color'],
                          'description': 'The hex color value (starting with \'#\') for the border along the left side of the message attachment.',
                          'name': 'discord_color',
                          'input_type': 'text'
                          },
                         {'label': 'TTS',
                          'value': self.config['tts'],
                          'name': 'discord_tts',
                          'description': 'Send the notification using text-to-speech.',
                          'input_type': 'checkbox'
                          },
                         {'label': 'Include Subject Line',
                          'value': self.config['incl_subject'],
                          'name': 'discord_incl_subject',
                          'description': 'Include the subject line with the notifications.',
                          'input_type': 'checkbox'
                          },
                         {'label': 'Include Rich Metadata Info',
                          'value': self.config['incl_card'],
                          'name': 'discord_incl_card',
                          'description': 'Include an info card with a poster and metadata with the notifications.<br>'
                                         'Note: <a data-tab-destination="tabs-notifications" data-dismiss="modal" '
                                         'data-target="#notify_upload_posters">Image Hosting</a> '
                                         'must be enabled under the notifications settings tab.',
                          'input_type': 'checkbox'
                          },
                         {'label': 'Include Plot Summaries',
                          'value': self.config['incl_description'],
                          'name': 'discord_incl_description',
                          'description': 'Include a plot summary for movies and TV shows on the info card.',
                          'input_type': 'checkbox'
                          },
                         {'label': 'Include Link to Plex Web',
                          'value': self.config['incl_pmslink'],
                          'name': 'discord_incl_pmslink',
                          'description': 'Include a second link to the media in Plex Web on the info card.',
                          'input_type': 'checkbox'
                          },
                         {'label': 'Use Poster Thumbnail',
                          'value': self.config['incl_thumbnail'],
                          'name': 'discord_incl_thumbnail',
                          'description': 'Use a thumbnail instead of a full sized poster on the info card.',
                          'input_type': 'checkbox'
                          },
                         {'label': 'Movie Link Source',
                          'value': self.config['movie_provider'],
                          'name': 'discord_movie_provider',
                          'description': 'Select the source for movie links on the info cards. Leave blank to disable.<br>'
                                         'Note: 3rd party API lookup may need to be enabled under the notifications settings tab.',
                          'input_type': 'select',
                          'select_options': PrettyMetadata().get_movie_providers()
                          },
                         {'label': 'TV Show Link Source',
                          'value': self.config['tv_provider'],
                          'name': 'discord_tv_provider',
                          'description': 'Select the source for tv show links on the info cards. Leave blank to disable.<br>'
                                         'Note: 3rd party API lookup may need to be enabled under the notifications settings tab.',
                          'input_type': 'select',
                          'select_options': PrettyMetadata().get_tv_providers()
                          },
                         {'label': 'Music Link Source',
                          'value': self.config['music_provider'],
                          'name': 'discord_music_provider',
                          'description': 'Select the source for music links on the info cards. Leave blank to disable.',
                          'input_type': 'select',
                          'select_options': PrettyMetadata().get_music_providers()
                          }
                         ]

        return config_option


class EMAIL(Notifier):
    """
    Email notifications
    """
    NAME = 'Email'
    _DEFAULT_CONFIG = {'from_name': 'Tautulli',
                       'from': '',
                       'to': [],
                       'cc': [],
                       'bcc': [],
                       'smtp_server': '',
                       'smtp_port': 25,
                       'smtp_user': '',
                       'smtp_password': '',
                       'tls': 0,
                       'html_support': 1
                       }

    def agent_notify(self, subject='', body='', action='', **kwargs):
        if self.config['html_support']:
            plain = MIMEText(None, 'plain', 'utf-8')
            plain.replace_header('Content-Transfer-Encoding', 'quoted-printable')
            plain.set_payload(kwargs.get('plaintext', bleach.clean(body, strip=True)), 'utf-8')

            html = MIMEText(body, 'html', 'utf-8')

            msg = MIMEMultipart('alternative')
            msg.attach(plain)
            msg.attach(html)
        else:
            msg = MIMEText(None, 'plain', 'utf-8')
            msg.replace_header('Content-Transfer-Encoding', 'quoted-printable')
            msg.set_payload(body, 'utf-8')

        msg['Message-ID'] = email.utils.make_msgid()
        msg['Date'] = email.utils.formatdate(localtime=True)
        msg['Subject'] = subject
        msg['From'] = email.utils.formataddr((self.config['from_name'], self.config['from']))
        msg['To'] = ','.join(self.config['to'])
        msg['CC'] = ','.join(self.config['cc'])

        recipients = self.config['to'] + self.config['cc'] + self.config['bcc']

        mailserver = None
        success = False

        try:
            mailserver = smtplib.SMTP(self.config['smtp_server'], self.config['smtp_port'])
            mailserver.ehlo()

            if self.config['tls']:
                mailserver.starttls()
                mailserver.ehlo()

            if self.config['smtp_user']:
                mailserver.login(str(self.config['smtp_user']), str(self.config['smtp_password']))

            mailserver.sendmail(self.config['from'], recipients, msg.as_string())
            logger.info(u"Tautulli Notifiers :: {name} notification sent.".format(name=self.NAME))
            success = True

        except Exception as e:
            logger.error(u"Tautulli Notifiers :: {name} notification failed: {e}".format(name=self.NAME, e=e))

        finally:
            if mailserver:
                mailserver.quit()

        return success

    def get_user_emails(self):
        emails = {u['email']: u['friendly_name'] for u in users.Users().get_users() if u['email']}

        user_emails_to = {v: '' for v in self.config['to']}
        user_emails_cc = {v: '' for v in self.config['cc']}
        user_emails_bcc = {v: '' for v in self.config['bcc']}

        user_emails_to.update(emails)
        user_emails_cc.update(emails)
        user_emails_bcc.update(emails)

        user_emails_to = [{'value': k, 'text': v} for k, v in user_emails_to.iteritems()]
        user_emails_cc = [{'value': k, 'text': v} for k, v in user_emails_cc.iteritems()]
        user_emails_bcc = [{'value': k, 'text': v} for k, v in user_emails_bcc.iteritems()]

        return user_emails_to, user_emails_cc, user_emails_bcc

    def return_config_options(self):
        user_emails_to, user_emails_cc, user_emails_bcc = self.get_user_emails()

        config_option = [{'label': 'From Name',
                          'value': self.config['from_name'],
                          'name': 'email_from_name',
                          'description': 'The name of the sender.',
                          'input_type': 'text'
                          },
                         {'label': 'From',
                          'value': self.config['from'],
                          'name': 'email_from',
                          'description': 'The email address of the sender.',
                          'input_type': 'text'
                          },
                         {'label': 'To',
                          'value': self.config['to'],
                          'name': 'email_to',
                          'description': 'The email address(es) of the recipients.',
                          'input_type': 'selectize',
                          'select_options': user_emails_to
                          },
                         {'label': 'CC',
                          'value': self.config['cc'],
                          'name': 'email_cc',
                          'description': 'The email address(es) to CC.',
                          'input_type': 'selectize',
                          'select_options': user_emails_cc
                          },
                         {'label': 'BCC',
                          'value': self.config['bcc'],
                          'name': 'email_bcc',
                          'description': 'The email address(es) to BCC.',
                          'input_type': 'selectize',
                          'select_options': user_emails_bcc
                          },
                         {'label': 'SMTP Server',
                          'value': self.config['smtp_server'],
                          'name': 'email_smtp_server',
                          'description': 'Host for the SMTP server.',
                          'input_type': 'text'
                          },
                         {'label': 'SMTP Port',
                          'value': self.config['smtp_port'],
                          'name': 'email_smtp_port',
                          'description': 'Port for the SMTP server.',
                          'input_type': 'number'
                          },
                         {'label': 'SMTP User',
                          'value': self.config['smtp_user'],
                          'name': 'email_smtp_user',
                          'description': 'User for the SMTP server.',
                          'input_type': 'text'
                          },
                         {'label': 'SMTP Password',
                          'value': self.config['smtp_password'],
                          'name': 'email_smtp_password',
                          'description': 'Password for the SMTP server.',
                          'input_type': 'password'
                          },
                         {'label': 'TLS',
                          'value': self.config['tls'],
                          'name': 'email_tls',
                          'description': 'Does the server use encryption.',
                          'input_type': 'checkbox'
                          },
                         {'label': 'Enable HTML Support',
                          'value': self.config['html_support'],
                          'name': 'email_html_support',
                          'description': 'Style your messages using HTML tags.',
                          'input_type': 'checkbox'
                          }
                         ]

        return config_option


class FACEBOOK(Notifier):
    """
    Facebook notifications
    """
    NAME = 'Facebook'
    _DEFAULT_CONFIG = {'redirect_uri': '',
                       'access_token': '',
                       'app_id': '',
                       'app_secret': '',
                       'group_id': '',
                       'incl_subject': 1,
                       'incl_card': 0,
                       'movie_provider': '',
                       'tv_provider': '',
                       'music_provider': ''
                       }

    def _get_authorization(self, app_id='', app_secret='', redirect_uri=''):
        # Temporarily store settings in the config so we can retrieve them in Facebook step 2.
        # Assume the user won't be requesting authorization for multiple Facebook notifiers at the same time.
        plexpy.CONFIG.FACEBOOK_APP_ID = app_id
        plexpy.CONFIG.FACEBOOK_APP_SECRET = app_secret
        plexpy.CONFIG.FACEBOOK_REDIRECT_URI = redirect_uri
        plexpy.CONFIG.FACEBOOK_TOKEN = 'temp'

        return facebook.auth_url(app_id=app_id,
                                 canvas_url=redirect_uri,
                                 perms=['publish_to_groups'])

    def _get_credentials(self, code=''):
        logger.info(u"Tautulli Notifiers :: Requesting access token from {name}.".format(name=self.NAME))

        app_id = plexpy.CONFIG.FACEBOOK_APP_ID
        app_secret = plexpy.CONFIG.FACEBOOK_APP_SECRET
        redirect_uri = plexpy.CONFIG.FACEBOOK_REDIRECT_URI

        try:
            # Request user access token
            api = facebook.GraphAPI(version='2.12')
            response = api.get_access_token_from_code(code=code,
                                                      redirect_uri=redirect_uri,
                                                      app_id=app_id,
                                                      app_secret=app_secret)
            access_token = response['access_token']

            # Request extended user access token
            api = facebook.GraphAPI(access_token=access_token, version='2.12')
            response = api.extend_access_token(app_id=app_id,
                                               app_secret=app_secret)

            plexpy.CONFIG.FACEBOOK_TOKEN = response['access_token']
        except Exception as e:
            logger.error(u"Tautulli Notifiers :: Error requesting {name} access token: {e}".format(name=self.NAME, e=e))
            plexpy.CONFIG.FACEBOOK_TOKEN = ''

        # Clear out temporary config values
        plexpy.CONFIG.FACEBOOK_APP_ID = ''
        plexpy.CONFIG.FACEBOOK_APP_SECRET = ''
        plexpy.CONFIG.FACEBOOK_REDIRECT_URI = ''

        return plexpy.CONFIG.FACEBOOK_TOKEN

    def _post_facebook(self, **data):
        if self.config['group_id']:
            api = facebook.GraphAPI(access_token=self.config['access_token'], version='2.12')

            try:
                api.put_object(parent_object=self.config['group_id'], connection_name='feed', **data)
                logger.info(u"Tautulli Notifiers :: {name} notification sent.".format(name=self.NAME))
                return True
            except Exception as e:
                logger.error(u"Tautulli Notifiers :: Error sending {name} post: {e}".format(name=self.NAME, e=e))
                return False

        else:
            logger.error(u"Tautulli Notifiers :: Error sending {name} post: No {name} Group ID provided.".format(name=self.NAME))
            return False

    def agent_notify(self, subject='', body='', action='', **kwargs):
        if self.config['incl_subject']:
            text = subject.encode('utf-8') + '\r\n' + body.encode("utf-8")
        else:
            text = body.encode("utf-8")

        data = {'message': text}

        if self.config['incl_card'] and kwargs.get('parameters', {}).get('media_type'):
            # Grab formatted metadata
            pretty_metadata = PrettyMetadata(kwargs['parameters'])

            if pretty_metadata.media_type == 'movie':
                provider = self.config['movie_provider']
            elif pretty_metadata.media_type in ('show', 'season', 'episode'):
                provider = self.config['tv_provider']
            elif pretty_metadata.media_type in ('artist', 'album', 'track'):
                provider = self.config['music_provider']
            else:
                provider = None

            data['link'] = pretty_metadata.get_provider_link(provider)

        return self._post_facebook(**data)

    def return_config_options(self):
        config_option = [{'label': 'OAuth Redirect URI',
                          'value': self.config['redirect_uri'],
                          'name': 'facebook_redirect_uri',
                          'description': 'Fill in this address for the "Valid OAuth redirect URIs" '
                                         'in your Facebook App.',
                          'input_type': 'text'
                          },
                         {'label': 'Facebook App ID',
                          'value': self.config['app_id'],
                          'name': 'facebook_app_id',
                          'description': 'Your Facebook app ID.',
                          'input_type': 'text'
                          },
                         {'label': 'Facebook App Secret',
                          'value': self.config['app_secret'],
                          'name': 'facebook_app_secret',
                          'description': 'Your Facebook app secret.',
                          'input_type': 'text'
                          },
                         {'label': 'Request Authorization',
                          'value': 'Request Authorization',
                          'name': 'facebook_facebook_auth',
                          'description': 'Request Facebook authorization. (Ensure you allow the browser pop-up).',
                          'input_type': 'button'
                          },
                         {'label': 'Facebook Access Token',
                          'value': self.config['access_token'],
                          'name': 'facebook_access_token',
                          'description': 'Your Facebook access token. '
                                         'Automatically filled in after requesting authorization.',
                          'input_type': 'text'
                          },
                         {'label': 'Facebook Group ID',
                          'value': self.config['group_id'],
                          'name': 'facebook_group_id',
                          'description': 'Your Facebook Group ID.',
                          'input_type': 'text'
                          },
                         {'label': 'Include Subject Line',
                          'value': self.config['incl_subject'],
                          'name': 'facebook_incl_subject',
                          'description': 'Include the subject line with the notifications.',
                          'input_type': 'checkbox'
                          },
                         {'label': 'Include Rich Metadata Info',
                          'value': self.config['incl_card'],
                          'name': 'facebook_incl_card',
                          'description': 'Include an info card with a poster and metadata with the notifications.<br>'
                                         'Note: <a data-tab-destination="tabs-notifications" data-dismiss="modal" '
                                         'data-target="#notify_upload_posters">Image Hosting</a> '
                                         'must be enabled under the notifications settings tab.',
                          'input_type': 'checkbox'
                          },
                         {'label': 'Movie Link Source',
                          'value': self.config['movie_provider'],
                          'name': 'facebook_movie_provider',
                          'description': 'Select the source for movie links on the info cards. Leave blank to disable.<br>'
                                         'Note: 3rd party API lookup may need to be enabled under the notifications settings tab.',
                          'input_type': 'select',
                          'select_options': PrettyMetadata().get_movie_providers()
                          },
                         {'label': 'TV Show Link Source',
                          'value': self.config['tv_provider'],
                          'name': 'facebook_tv_provider',
                          'description': 'Select the source for tv show links on the info cards. Leave blank to disable.<br>'
                                         'Note: 3rd party API lookup may need to be enabled under the notifications settings tab.',
                          'input_type': 'select',
                          'select_options': PrettyMetadata().get_tv_providers()
                          },
                         {'label': 'Music Link Source',
                          'value': self.config['music_provider'],
                          'name': 'facebook_music_provider',
                          'description': 'Select the source for music links on the info cards. Leave blank to disable.',
                          'input_type': 'select',
                          'select_options': PrettyMetadata().get_music_providers()
                          }
                         ]

        return config_option


class GROUPME(Notifier):
    """
    GroupMe notifications
    """
    NAME = 'GroupMe'
    _DEFAULT_CONFIG = {'access_token': '',
                       'bot_id': '',
                       'incl_subject': 1,
                       'incl_poster': 0
                       }

    def agent_notify(self, subject='', body='', action='', **kwargs):
        data = {'bot_id': self.config['bot_id']}

        if self.config['incl_subject']:
            data['text'] = subject.encode('utf-8') + '\r\n' + body.encode('utf-8')
        else:
            data['text'] = body.encode('utf-8')

        if self.config['incl_poster'] and kwargs.get('parameters'):
            pretty_metadata = PrettyMetadata(kwargs.get('parameters'))

            # Retrieve the poster from Plex
            result = pmsconnect.PmsConnect().get_image(img=pretty_metadata.parameters.get('poster_thumb',''))
            if result and result[0]:
                poster_content = result[0]
            else:
                poster_content = ''
                logger.error(u"Tautulli Notifiers :: Unable to retrieve image for {name}.".format(name=self.NAME))

            if poster_content:
                headers = {'X-Access-Token': self.config['access_token'],
                           'Content-Type': 'image/png'}

                r = requests.post('https://image.groupme.com/pictures', headers=headers, data=poster_content)

                if r.status_code == 200:
                    logger.info(u"Tautulli Notifiers :: {name} poster sent.".format(name=self.NAME))
                    r_content = r.json()
                    data['attachments'] = [{'type': 'image',
                                            'url': r_content['payload']['picture_url']}]
                else:
                    logger.error(u"Tautulli Notifiers :: {name} poster failed: "
                                 u"[{r.status_code}] {r.reason}".format(name=self.NAME, r=r))
                    logger.debug(u"Tautulli Notifiers :: Request response: {}".format(request.server_message(r, True)))

        return self.make_request('https://api.groupme.com/v3/bots/post', json=data)

    def return_config_options(self):
        config_option = [{'label': 'GroupMe Access Token',
                          'value': self.config['access_token'],
                          'name': 'groupme_access_token',
                          'description': 'Your GroupMe access token.',
                          'input_type': 'text'
                          },
                         {'label': 'GroupMe Bot ID',
                          'value': self.config['bot_id'],
                          'name': 'groupme_bot_id',
                          'description': 'Your GroupMe bot ID.',
                          'input_type': 'text'
                          },
                         {'label': 'Include Subject Line',
                          'value': self.config['incl_subject'],
                          'name': 'groupme_incl_subject',
                          'description': 'Include the subject line with the notifications.',
                          'input_type': 'checkbox'
                          },
                         {'label': 'Include Poster Image',
                          'value': self.config['incl_poster'],
                          'name': 'groupme_incl_poster',
                          'description': 'Include a poster with the notifications.',
                          'input_type': 'checkbox'
                          }
                         ]

        return config_option


class GROWL(Notifier):
    """
    Growl notifications, for OS X.
    """
    NAME = 'Growl'
    _DEFAULT_CONFIG = {'host': '',
                       'password': ''
                       }

    def agent_notify(self, subject='', body='', action='', **kwargs):
        # Split host and port
        if self.config['host'] == "":
            host, port = "localhost", 23053
        if ":" in self.config['host']:
            host, port = self.config['host'].split(':', 1)
            port = int(port)
        else:
            host, port = self.config['host'], 23053

        # If password is empty, assume none
        if self.config['password'] == "":
            password = None
        else:
            password = self.config['password']

        # Register notification
        growl = gntp.notifier.GrowlNotifier(
            applicationName='Tautulli',
            notifications=['New Event'],
            defaultNotifications=['New Event'],
            hostname=host,
            port=port,
            password=password
        )

        try:
            growl.register()
        except gntp.notifier.errors.NetworkError:
            logger.error(u"Tautulli Notifiers :: {name} notification failed: network error".format(name=self.NAME))
            return False
        except gntp.notifier.errors.AuthError:
            logger.error(u"Tautulli Notifiers :: {name} notification failed: authentication error".format(name=self.NAME))
            return False

        # Fix message
        body = body.encode(plexpy.SYS_ENCODING, "replace")

        # Send it, including an image
        image_file = os.path.join(str(plexpy.PROG_DIR),
            "data/interfaces/default/images/logo-circle.png")

        with open(image_file, 'rb') as f:
            image = f.read()

        try:
            growl.notify(
                noteType='New Event',
                title=subject,
                description=body,
                icon=image
            )
            logger.info(u"Tautulli Notifiers :: {name} notification sent.".format(name=self.NAME))
            return True
        except gntp.notifier.errors.NetworkError:
            logger.error(u"Tautulli Notifiers :: {name} notification failed: network error".format(name=self.NAME))
            return False

    def return_config_options(self):
        config_option = [{'label': 'Growl Host',
                          'value': self.config['host'],
                          'name': 'growl_host',
                          'description': 'Your Growl hostname or IP address.',
                          'input_type': 'text'
                          },
                         {'label': 'Growl Password',
                          'value': self.config['password'],
                          'name': 'growl_password',
                          'description': 'Your Growl password.',
                          'input_type': 'password'
                          }
                         ]

        return config_option


class HIPCHAT(Notifier):
    """
    Hipchat notifications
    """
    NAME = 'Hipchat'
    _DEFAULT_CONFIG = {'hook': '',
                       'color': '',
                       'emoticon': '',
                       'incl_subject': 1,
                       'incl_card': 0,
                       'incl_description': 1,
                       'incl_pmslink': 0,
                       'movie_provider': '',
                       'tv_provider': '',
                       'music_provider': ''
                       }

    def agent_notify(self, subject='', body='', action='', **kwargs):
        data = {'notify': 'false'}

        text = body.encode('utf-8')

        if self.config['incl_subject']:
            data['from'] = subject.encode('utf-8')

        if self.config['color']:
            data['color'] = self.config['color']

        if self.config['incl_card'] and kwargs.get('parameters', {}).get('media_type'):
            # Grab formatted metadata
            pretty_metadata = PrettyMetadata(kwargs['parameters'])

            if pretty_metadata.media_type == 'movie':
                provider = self.config['movie_provider']
            elif pretty_metadata.media_type in ('show', 'season', 'episode'):
                provider = self.config['tv_provider']
            elif pretty_metadata.media_type in ('artist', 'album', 'track'):
                provider = self.config['music_provider']
            else:
                provider = None

            poster_url = pretty_metadata.get_poster_url()
            provider_name = pretty_metadata.get_provider_name(provider)
            provider_link = pretty_metadata.get_provider_link(provider)
            title = pretty_metadata.get_title()
            description = pretty_metadata.get_description()
            plex_url = pretty_metadata.get_plex_url()

            attachment = {'title': title,
                          'format': 'medium',
                          'style': 'application',
                          'id': uuid.uuid4().hex,
                          'activity': {'html': text,
                                       'icon': {'url': poster_url}},
                          'thumbnail': {'url': poster_url}
                          }

            if self.config['incl_description'] or pretty_metadata.media_type in ('artist', 'album', 'track'):
                attachment['description'] = {'format': 'text',
                                             'value': description}

            attributes = []
            if provider_link:
                attachment['url'] = provider_link
                attributes.append({'label': 'View Details',
                                   'value': {'label': provider_name,
                                             'url': provider_link}})
            if self.config['incl_pmslink']:
                attributes.append({'label': 'View Details',
                                   'value': {'label': 'Plex Web',
                                             'url': plex_url}})
            if attributes:
                attachment['attributes'] = attributes

            data['message'] = text
            data['card'] = attachment

        else:
            if self.config['emoticon']:
                text = self.config['emoticon'] + ' ' + text
            data['message'] = text
            data['message_format'] = 'text'

        headers = {'Content-type': 'application/json'}

        return self.make_request(self.config['hook'], headers=headers, json=data)

    def return_config_options(self):
        config_option = [{'label': 'Hipchat Custom Integrations URL',
                          'value': self.config['hook'],
                          'name': 'hipchat_hook',
                          'description': 'Your Hipchat BYO integration URL. You can get a key from'
                                         ' <a href="' + helpers.anon_url('https://www.hipchat.com/addons/') + '" target="_blank">here</a>.',
                          'input_type': 'text'
                          },
                         {'label': 'Hipchat Color',
                          'value': self.config['color'],
                          'name': 'hipchat_color',
                          'description': 'Background color for the message.',
                          'input_type': 'select',
                          'select_options': {'': '',
                                             'gray': 'gray',
                                             'green': 'green',
                                             'purple': 'purple',
                                             'random': 'random',
                                             'red': 'red',
                                             'yellow': 'yellow'
                                             }
                          },
                         {'label': 'Hipchat Emoticon',
                          'value': self.config['emoticon'],
                          'name': 'hipchat_emoticon',
                          'description': 'Include an emoticon tag at the beginning of text notifications (e.g. (taco)). Leave blank for none.'
                                         ' Use a stock emoticon or create a custom emoticon'
                                         ' <a href="' + helpers.anon_url('https://www.hipchat.com/emoticons/') + '" target="_blank">here</a>.',
                          'input_type': 'text'
                          },
                         {'label': 'Include Subject Line',
                          'value': self.config['incl_subject'],
                          'name': 'hipchat_incl_subject',
                          'description': 'Includes the subject with the notifications.',
                          'input_type': 'checkbox'
                          },
                         {'label': 'Include Rich Metadata Info',
                          'value': self.config['incl_card'],
                          'name': 'hipchat_incl_card',
                          'description': 'Include an info card with a poster and metadata with the notifications.<br>'
                                         'Note: <a data-tab-destination="tabs-notifications" data-dismiss="modal" '
                                         'data-target="#notify_upload_posters">Image Hosting</a> '
                                         'must be enabled under the notifications settings tab.<br>'
                                         'Note: This will change the notification type to HTML and emoticons will no longer work.',
                          'input_type': 'checkbox'
                          },
                         {'label': 'Include Plot Summaries',
                          'value': self.config['incl_description'],
                          'name': 'hipchat_incl_description',
                          'description': 'Include a plot summary for movies and TV shows on the info card.',
                          'input_type': 'checkbox'
                          },
                         {'label': 'Include Link to Plex Web',
                          'value': self.config['incl_pmslink'],
                          'name': 'hipchat_incl_pmslink',
                          'description': 'Include a second link to the media in Plex Web on the info card.',
                          'input_type': 'checkbox'
                          },
                         {'label': 'Movie Link Source',
                          'value': self.config['movie_provider'],
                          'name': 'hipchat_movie_provider',
                          'description': 'Select the source for movie links on the info cards. Leave blank to disable.<br>'
                                         'Note: 3rd party API lookup may need to be enabled under the notifications settings tab.',
                          'input_type': 'select',
                          'select_options': PrettyMetadata().get_movie_providers()
                          },
                         {'label': 'TV Show Link Source',
                          'value': self.config['tv_provider'],
                          'name': 'hipchat_tv_provider',
                          'description': 'Select the source for tv show links on the info cards. Leave blank to disable.<br>'
                                         'Note: 3rd party API lookup may need to be enabled under the notifications settings tab.',
                          'input_type': 'select',
                          'select_options': PrettyMetadata().get_tv_providers()
                          },
                         {'label': 'Music Link Source',
                          'value': self.config['music_provider'],
                          'name': 'hipchat_music_provider',
                          'description': 'Select the source for music links on the info cards. Leave blank to disable.',
                          'input_type': 'select',
                          'select_options': PrettyMetadata().get_music_providers()
                          }
                         ]

        return config_option


class IFTTT(Notifier):
    """
    IFTTT notifications
    """
    NAME = 'IFTTT'
    _DEFAULT_CONFIG = {'key': '',
                       'event': 'tautulli',
                       'value3': '',
                       }

    def agent_notify(self, subject='', body='', action='', **kwargs):
        event = unicode(self.config['event']).format(action=action)

        data = {'value1': subject.encode("utf-8"),
                'value2': body.encode("utf-8")}

        if self.config['value3']:
            pretty_metadata = PrettyMetadata(kwargs['parameters'])
            data['value3'] = pretty_metadata.parameters.get(self.config['value3'], '')

        headers = {'Content-type': 'application/json'}

        return self.make_request('https://maker.ifttt.com/trigger/{}/with/key/{}'.format(event, self.config['key']),
                                 headers=headers, json=data)

    def return_config_options(self):
        config_option = [{'label': 'IFTTT Webhook Key',
                          'value': self.config['key'],
                          'name': 'ifttt_key',
                          'description': 'Your IFTTT webhook key. You can get a key from'
                                         ' <a href="' + helpers.anon_url('https://ifttt.com/maker_webhooks') + '" target="_blank">here</a>.',
                          'input_type': 'text'
                          },
                         {'label': 'IFTTT Event',
                          'value': self.config['event'],
                          'name': 'ifttt_event',
                          'description': 'The IFTTT maker event to fire. You can include'
                                         ' <span class="inline-pre">{action}</span>'
                                         ' to be substituted with the action name.'
                                         ' The notification subject and body will be sent'
                                         ' as <span class="inline-pre">value1</span>'
                                         ' and <span class="inline-pre">value2</span> respectively.',
                          'input_type': 'text'
                          },
                         {'label': 'Value 3',
                          'value': self.config['value3'],
                          'name': 'ifttt_value3',
                          'description': 'Optional: Select a parameter to send as <span class="inline-pre">value3</span>.',
                          'input_type': 'select',
                          'select_options': PrettyMetadata().get_parameters()
                          }
                         ]

        return config_option


class JOIN(Notifier):
    """
    Join notifications
    """
    NAME = 'Join'
    _DEFAULT_CONFIG = {'api_key': '',
                       'device_names': [],
                       'priority': 2,
                       'incl_subject': 1,
                       'incl_poster': 0,
                       'movie_provider': '',
                       'tv_provider': '',
                       'music_provider': ''
                       }

    def agent_notify(self, subject='', body='', action='', **kwargs):
        data = {'apikey': self.config['api_key'],
                'deviceNames': ','.join(self.config['device_names']),
                'text': body.encode("utf-8")}

        if self.config['incl_subject']:
            data['title'] = subject.encode("utf-8")

        if kwargs.get('parameters', {}).get('media_type'):
            # Grab formatted metadata
            pretty_metadata = PrettyMetadata(kwargs['parameters'])

            poster_url = pretty_metadata.get_poster_url()
            if poster_url and self.config['incl_poster']:
                data['icon'] = poster_url

            if pretty_metadata.media_type == 'movie':
                provider = self.config['movie_provider']
            elif pretty_metadata.media_type in ('show', 'season', 'episode'):
                provider = self.config['tv_provider']
            elif pretty_metadata.media_type in ('artist', 'album', 'track'):
                provider = self.config['music_provider']
            else:
                provider = None

            provider_link = pretty_metadata.get_provider_link(provider)
            if provider_link:
                data['url'] = provider_link

        r = requests.post('https://joinjoaomgcd.appspot.com/_ah/api/messaging/v1/sendPush', params=data)

        if r.status_code == 200:
            response_data = r.json()
            if response_data.get('success'):
                logger.info(u"Tautulli Notifiers :: {name} notification sent.".format(name=self.NAME))
                return True
            else:
                error_msg = response_data.get('errorMessage')
                logger.error(u"Tautulli Notifiers :: {name} notification failed: {msg}".format(name=self.NAME, msg=error_msg))
                return False
        else:
            logger.error(u"Tautulli Notifiers :: {name} notification failed: [{r.status_code}] {r.reason}".format(name=self.NAME, r=r))
            logger.debug(u"Tautulli Notifiers :: Request response: {}".format(request.server_message(r, True)))
            return False

    def get_devices(self):
        devices = {d: d for d in self.config['device_names']}
        devices.update({'': ''})

        if self.config['api_key']:
            params = {'apikey': self.config['api_key']}

            r = requests.get('https://joinjoaomgcd.appspot.com/_ah/api/registration/v1/listDevices', params=params)

            if r.status_code == 200:
                response_data = r.json()
                if response_data.get('success'):
                    response_devices = response_data.get('records', [])
                    devices.update({d['deviceName']: d['deviceName'] for d in response_devices})
                    return devices
                else:
                    error_msg = response_data.get('errorMessage')
                    logger.info(u"Tautulli Notifiers :: Unable to retrieve {name} devices list: {msg}".format(name=self.NAME, msg=error_msg))
                    return devices
            else:
                logger.error(u"Tautulli Notifiers :: Unable to retrieve {name} devices list: [{r.status_code}] {r.reason}".format(name=self.NAME, r=r))
                logger.debug(u"Tautulli Notifiers :: Request response: {}".format(request.server_message(r, True)))
                return devices

        else:
            return devices

    def return_config_options(self):
        config_option = [{'label': 'Join API Key',
                          'value': self.config['api_key'],
                          'name': 'join_api_key',
                          'description': 'Your Join API key. Required for group notifications.',
                          'input_type': 'text',
                          'refresh': True
                          },
                         {'label': 'Device Name(s)',
                          'value': self.config['device_names'],
                          'name': 'join_device_names',
                          'description': 'Select your Join device(s).',
                          'input_type': 'select',
                          'select_options': self.get_devices()
                          },
                         {'label': 'Priority',
                          'value': self.config['priority'],
                          'name': 'join_priority',
                          'description': 'Set the notification priority.',
                          'input_type': 'select',
                          'select_options': {-2: -2, -1: -1, 0: 0, 1: 1, 2: 2}
                          },
                         {'label': 'Include Subject Line',
                          'value': self.config['incl_subject'],
                          'name': 'join_incl_subject',
                          'description': 'Include the subject line with the notifications.',
                          'input_type': 'checkbox'
                          },
                         {'label': 'Include Poster Image',
                          'value': self.config['incl_poster'],
                          'name': 'join_incl_poster',
                          'description': 'Include a poster with the notifications.<br>'
                                         'Note: <a data-tab-destination="tabs-notifications" data-dismiss="modal" '
                                         'data-target="#notify_upload_posters">Image Hosting</a> '
                                         'must be enabled under the notifications settings tab.',
                          'input_type': 'checkbox'
                          },
                         {'label': 'Movie Link Source',
                          'value': self.config['movie_provider'],
                          'name': 'join_movie_provider',
                          'description': 'Select the source for movie links in the notification. Leave blank to disable.<br>'
                                         'Note: 3rd party API lookup may need to be enabled under the notifications settings tab.',
                          'input_type': 'select',
                          'select_options': PrettyMetadata().get_movie_providers()
                          },
                         {'label': 'TV Show Link Source',
                          'value': self.config['tv_provider'],
                          'name': 'join_tv_provider',
                          'description': 'Select the source for tv show links in the notification. Leave blank to disable.<br>'
                                         'Note: 3rd party API lookup may need to be enabled under the notifications settings tab.',
                          'input_type': 'select',
                          'select_options': PrettyMetadata().get_tv_providers()
                          },
                         {'label': 'Music Link Source',
                          'value': self.config['music_provider'],
                          'name': 'join_music_provider',
                          'description': 'Select the source for music links in the notification. Leave blank to disable.',
                          'input_type': 'select',
                          'select_options': PrettyMetadata().get_music_providers()
                          }
                         ]

        return config_option


class MQTT(Notifier):
    """
    MQTT notifications
    """
    _DEFAULT_CONFIG = {'broker': '',
                       'port': 1883,
                       'protocol': 'MQTTv311',
                       'username': '',
                       'password': '',
                       'clientid': 'tautulli',
                       'topic': '',
                       'qos': 1,
                       'retain': 0,
                       'keep_alive': 60
                       }

    def agent_notify(self, subject='', body='', action='', **kwargs):
        if not self.config['topic']:
            logger.error(u"Tautulli Notifiers :: MQTT topic not specified.")
            return

        data = {'subject': subject.encode("utf-8"),
                'body': body.encode("utf-8"),
                'topic': self.config['topic'].encode("utf-8")}

        auth = {}
        if self.config['username']:
            auth['username'] = self.config['username']
        if self.config['password']:
            auth['password'] = self.config['password']

        single(self.config['topic'], payload=json.dumps(data), qos=self.config['qos'], retain=bool(self.config['retain']),
               hostname=self.config['broker'], port=self.config['port'], client_id=self.config['clientid'],
               keepalive=self.config['keep_alive'], auth=auth or None, protocol=self.config['protocol'])

        return True

    def return_config_options(self):
        config_option = [{'label': 'Broker',
                          'value': self.config['broker'],
                          'name': 'mqtt_broker',
                          'description': 'The hostname or IP address of the MQTT broker.',
                          'input_type': 'text'
                          },
                         {'label': 'Port',
                          'value': self.config['port'],
                          'name': 'mqtt_port',
                          'description': 'The network port for connecting to the MQTT broker.',
                          'input_type': 'number'
                          },
                         {'label': 'Protocol',
                          'value': self.config['protocol'],
                          'name': 'mqtt_protocol',
                          'description': 'The MQTT protocol version.',
                          'input_type': 'select',
                          'select_options': {'MQTTv31': '3.1',
                                             'MQTTv311': '3.1.1'
                                             }
                          },
                         {'label': 'Client ID',
                          'value': self.config['clientid'],
                          'name': 'mqtt_clientid',
                          'description': 'The client ID for connecting to the MQTT broker.',
                          'input_type': 'text'
                          },
                         {'label': 'Username',
                          'value': self.config['username'],
                          'name': 'mqtt_username',
                          'description': 'The username to authenticate with the MQTT broker.',
                          'input_type': 'text'
                          },
                         {'label': 'Password',
                          'value': self.config['password'],
                          'name': 'mqtt_password',
                          'description': 'The password to authenticate with the MQTT broker.',
                          'input_type': 'password'
                          },
                         {'label': 'Topic',
                          'value': self.config['topic'],
                          'name': 'mqtt_topic',
                          'description': 'The topic to publish notifications to.',
                          'input_type': 'text'
                          },
                         {'label': 'Quality of Service',
                          'value': self.config['qos'],
                          'name': 'mqtt_qos',
                          'description': 'The quality of service level to use when publishing the notification.',
                          'input_type': 'select',
                          'select_options': {0: 0,
                                             1: 1,
                                             2: 2
                                             }
                          },
                         {'label': 'Retain Message',
                          'value': self.config['retain'],
                          'name': 'mqtt_retain',
                          'description': 'Set the message to be retained on the MQTT broker.',
                          'input_type': 'checkbox'
                          },
                         {'label': 'Keep-Alive',
                          'value': self.config['keep_alive'],
                          'name': 'mqtt_keep_alive',
                          'description': 'Maximum period in seconds before timing out the connection with the broker.',
                          'input_type': 'number'
                          }
                         ]

        return config_option


class NMA(Notifier):
    """
    Notify My Android notifications
    """
    NAME = 'Notify My Android'
    _DEFAULT_CONFIG = {'api_key': '',
                       'priority': 0
                       }

    def agent_notify(self, subject='', body='', action='', **kwargs):
        title = 'Tautulli'
        batch = False

        p = pynma.PyNMA()
        keys = self.config['api_key'].split(',')
        p.addkey(keys)

        if len(keys) > 1:
            batch = True

        response = p.push(title, subject, body, priority=self.config['priority'], batch_mode=batch)

        if response[self.config['api_key']][u'code'] == u'200':
            logger.info(u"Tautulli Notifiers :: {name} notification sent.".format(name=self.NAME))
            return True
        else:
            logger.error(u"Tautulli Notifiers :: {name} notification failed.".format(name=self.NAME))
            return False

    def return_config_options(self):
        config_option = [{'label': 'NotifyMyAndroid API Key',
                          'value': self.config['api_key'],
                          'name': 'nma_api_key',
                          'description': 'Your NotifyMyAndroid API key. Separate multiple api keys with commas.',
                          'input_type': 'text'
                          },
                         {'label': 'Priority',
                          'value': self.config['priority'],
                          'name': 'nma_priority',
                          'description': 'Set the notification priority.',
                          'input_type': 'select',
                          'select_options': {-2: -2, -1: -1, 0: 0, 1: 1, 2: 2}
                          }
                         ]

        return config_option


class OSX(Notifier):
    """
    macOS notifications
    """
    NAME = 'macOS'
    _DEFAULT_CONFIG = {'notify_app': '/Applications/Tautulli'
                       }

    def __init__(self, config=None):
        super(OSX, self).__init__(config=config)

        try:
            self.objc = __import__("objc")
            self.AppKit = __import__("AppKit")
        except:
            # logger.error(u"Tautulli Notifiers :: Cannot load OSX Notifications agent.")
            pass

    def validate(self):
        try:
            self.objc = __import__("objc")
            self.AppKit = __import__("AppKit")
            return True
        except:
            return False

    def _swizzle(self, cls, SEL, func):
        old_IMP = cls.instanceMethodForSelector_(SEL)

        def wrapper(self, *args, **kwargs):
            return func(self, old_IMP, *args, **kwargs)
        new_IMP = self.objc.selector(wrapper, selector=old_IMP.selector,
                                     signature=old_IMP.signature)
        self.objc.classAddMethod(cls, SEL, new_IMP)

    def _swizzled_bundleIdentifier(self, original, swizzled):
        return 'ade.tautulli.osxnotify'

    def agent_notify(self, subject='', body='', action='', **kwargs):

        subtitle = kwargs.get('subtitle', '')
        sound = kwargs.get('sound', '')
        image = kwargs.get('image', '')

        try:
            self._swizzle(self.objc.lookUpClass('NSBundle'),
                b'bundleIdentifier',
                self._swizzled_bundleIdentifier)

            NSUserNotification = self.objc.lookUpClass('NSUserNotification')
            NSUserNotificationCenter = self.objc.lookUpClass('NSUserNotificationCenter')
            NSAutoreleasePool = self.objc.lookUpClass('NSAutoreleasePool')

            if not NSUserNotification or not NSUserNotificationCenter:
                return False

            pool = NSAutoreleasePool.alloc().init()

            notification = NSUserNotification.alloc().init()
            notification.setTitle_(subject)
            if subtitle:
                notification.setSubtitle_(subtitle)
            if body:
                notification.setInformativeText_(body)
            if sound:
                notification.setSoundName_("NSUserNotificationDefaultSoundName")
            if image:
                source_img = self.AppKit.NSImage.alloc().initByReferencingFile_(image)
                notification.setContentImage_(source_img)
                # notification.set_identityImage_(source_img)
            notification.setHasActionButton_(False)

            notification_center = NSUserNotificationCenter.defaultUserNotificationCenter()
            notification_center.deliverNotification_(notification)
            logger.info(u"Tautulli Notifiers :: {name} notification sent.".format(name=self.NAME))

            del pool
            return True

        except Exception as e:
            logger.error(u"Tautulli Notifiers :: {name} failed: {e}".format(name=self.NAME, e=e))
            return False

    def return_config_options(self):
        config_option = [{'label': 'Register Notify App',
                          'value': self.config['notify_app'],
                          'name': 'osx_notify_app',
                          'description': 'Enter the path/application name to be registered with the Notification Center. '
                                         'Default is <span class="inline-pre">/Applications/Tautulli</span>.',
                          'input_type': 'text'
                          },
                         {'label': 'Register App',
                          'value': 'Register App',
                          'name': 'osx_notify_register',
                          'description': 'Register Tautulli with the Notification Center.',
                          'input_type': 'button'
                          }
                         ]

        return config_option


class PLEX(Notifier):
    """
    Plex Home Theater notifications
    """
    NAME = 'Plex Home Theater'
    _DEFAULT_CONFIG = {'hosts': '',
                       'username': '',
                       'password': '',
                       'display_time': 5,
                       'image': ''
                       }

    def _sendhttp(self, host, command):
        url_command = urlencode(command)
        url = host + '/xbmcCmds/xbmcHttp/?' + url_command

        if self.config['password']:
            return request.request_content(url, auth=(self.config['username'], self.config['password']))
        else:
            return request.request_content(url)

    def _sendjson(self, host, method, params=None):
        params = params or {}
        data = [{'id': 0, 'jsonrpc': '2.0', 'method': method, 'params': params}]
        headers = {'Content-Type': 'application/json'}
        url = host + '/jsonrpc'

        if self.config['password']:
            response = request.request_json(url, method="post", data=json.dumps(data), headers=headers,
                                            auth=(self.config['username'], self.config['password']))
        else:
            response = request.request_json(url, method="post", data=json.dumps(data), headers=headers)

        if response:
            return response[0]['result']

    def agent_notify(self, subject='', body='', action='', **kwargs):
        hosts = [x.strip() for x in self.config['hosts'].split(',')]

        if self.config['display_time'] > 0:
            display_time = 1000 * self.config['display_time']  # in ms
        else:
            display_time = 5000

        if self.config['image']:
            image = self.config['image']
        else:
            image = os.path.join(plexpy.DATA_DIR, os.path.abspath("data/interfaces/default/images/logo-circle.png"))

        for host in hosts:
            logger.info(u"Tautulli Notifiers :: Sending notification command to {name} @ {host}".format(name=self.NAME, host=host))
            try:
                version = self._sendjson(host, 'Application.GetProperties', {'properties': ['version']})['version']['major']

                if version < 12:  # Eden
                    notification = subject + "," + body + "," + str(display_time)
                    notifycommand = {'command': 'ExecBuiltIn', 'parameter': 'Notification(' + notification + ')'}
                    request = self._sendhttp(host, notifycommand)

                else:  # Frodo
                    params = {'title': subject, 'message': body, 'displaytime': display_time, 'image': image}
                    request = self._sendjson(host, 'GUI.ShowNotification', params)

                if not request:
                    raise Exception
                else:
                    logger.info(u"Tautulli Notifiers :: {name} notification sent.".format(name=self.NAME))

            except Exception as e:
                logger.error(u"Tautulli Notifiers :: {name} notification failed: {e}".format(name=self.NAME, e=e))
                return False

        return True

    def return_config_options(self):
        config_option = [{'label': 'Plex Home Theater Host Address',
                          'value': self.config['hosts'],
                          'name': 'plex_hosts',
                          'description': 'Host running Plex Home Theater (eg. http://localhost:3005). Separate multiple hosts with commas (,).',
                          'input_type': 'text'
                          },
                         {'label': 'Plex Home Theater Username',
                          'value': self.config['username'],
                          'name': 'plex_username',
                          'description': 'Username of your Plex Home Theater client API (blank for none).',
                          'input_type': 'text'
                          },
                         {'label': 'Plex Home Theater Password',
                          'value': self.config['password'],
                          'name': 'plex_password',
                          'description': 'Password of your Plex Home Theater client API (blank for none).',
                          'input_type': 'password'
                          },
                         {'label': 'Notification Duration',
                          'value': self.config['display_time'],
                          'name': 'plex_display_time',
                          'description': 'The duration (in seconds) for the notification to stay on screen.',
                          'input_type': 'number'
                          },
                         {'label': 'Notification Icon',
                          'value': self.config['image'],
                          'name': 'plex_image',
                          'description': 'Full path or URL to an image to display with the notification. Leave blank for the default.',
                          'input_type': 'text'
                          }
                         ]

        return config_option


class PROWL(Notifier):
    """
    Prowl notifications.
    """
    NAME = 'Prowl'
    _DEFAULT_CONFIG = {'key': '',
                       'priority': 0
                       }

    def agent_notify(self, subject='', body='', action='', **kwargs):
        data = {'apikey': self.config['key'],
                'application': 'Tautulli',
                'event': subject.encode("utf-8"),
                'description': body.encode("utf-8"),
                'priority': self.config['priority']}

        headers = {'Content-type': 'application/x-www-form-urlencoded'}

        return self.make_request('https://api.prowlapp.com/publicapi/add', headers=headers, data=data)

    def return_config_options(self):
        config_option = [{'label': 'Prowl API Key',
                          'value': self.config['key'],
                          'name': 'prowl_key',
                          'description': 'Your Prowl API key.',
                          'input_type': 'text'
                          },
                         {'label': 'Priority',
                          'value': self.config['priority'],
                          'name': 'prowl_priority',
                          'description': 'Set the notification priority.',
                          'input_type': 'select',
                          'select_options': {-2: -2, -1: -1, 0: 0, 1: 1, 2: 2}
                          }
                         ]

        return config_option


class PUSHALOT(Notifier):
    """
    Pushalot notifications
    """
    NAME = 'Pushalot'
    _DEFAULT_CONFIG = {'api_key': ''
                       }

    def agent_notify(self, subject='', body='', action='', **kwargs):
        data = {'AuthorizationToken': self.config['api_key'],
                'Title': subject.encode('utf-8'),
                'Body': body.encode("utf-8")}

        headers = {'Content-type': 'application/x-www-form-urlencoded'}

        return self.make_request('https://pushalot.com/api/sendmessage', headers=headers, data=data)

    def return_config_options(self):
        config_option = [{'label': 'Pushalot API Key',
                          'value': self.config['api_key'],
                          'name': 'pushalot_api_key',
                          'description': 'Your Pushalot API key.',
                          'input_type': 'text'
                          }
                         ]

        return config_option


class PUSHBULLET(Notifier):
    """
    Pushbullet notifications
    """
    NAME = 'Pushbullet'
    _DEFAULT_CONFIG = {'api_key': '',
                       'device_id': '',
                       'channel_tag': '',
                       'incl_subject': 1,
                       'incl_poster': 0
                       }

    def agent_notify(self, subject='', body='', action='', **kwargs):
        data = {'type': 'note',
                'body': body.encode("utf-8")}

        headers = {'Content-type': 'application/json',
                   'Access-Token': self.config['api_key']
                   }

        if self.config['incl_subject']:
            data['title'] = subject.encode("utf-8")

        # Can only send to a device or channel, not both.
        if self.config['device_id']:
            data['device_iden'] = self.config['device_id']
        elif self.config['channel_tag']:
            data['channel_tag'] = self.config['channel_tag']

        if self.config['incl_poster'] and kwargs.get('parameters', {}).get('media_type'):
            # Grab formatted metadata
            pretty_metadata = PrettyMetadata(kwargs['parameters'])

            # Retrieve the poster from Plex
            result = pmsconnect.PmsConnect().get_image(img=pretty_metadata.parameters.get('poster_thumb', ''))
            if result and result[0]:
                poster_content = result[0]
            else:
                poster_content = ''
                logger.error(u"Tautulli Notifiers :: Unable to retrieve image for {name}.".format(name=self.NAME))

            if poster_content:
                poster_filename = 'poster_{}.png'.format(pretty_metadata.parameters['rating_key'])
                file_json = {'file_name': poster_filename, 'file_type': 'image/png'}
                files = {'file': (poster_filename, poster_content, 'image/png')}

                r = requests.post('https://api.pushbullet.com/v2/upload-request', headers=headers, json=file_json)

                file_response = r.json()
                upload_url = file_response.pop('upload_url')

                r = requests.post(upload_url, files=files)

                if r.status_code == 204:
                    data['type'] = 'file'
                    file_response.pop('data', None)
                    data.update(file_response)
                else:
                    logger.error(u"Tautulli Notifiers :: Unable to upload image to {name}: "
                                 u"[{r.status_code}] {r.reason}".format(name=self.NAME, r=r))
                    logger.debug(u"Tautulli Notifiers :: Request response: {}".format(request.server_message(r, True)))

        return self.make_request('https://api.pushbullet.com/v2/pushes', headers=headers, json=data)

    def get_devices(self):
        if self.config['api_key']:
            headers = {'Content-type': "application/json",
                       'Access-Token': self.config['api_key']
                       }

            r = requests.get('https://api.pushbullet.com/v2/devices', headers=headers)

            if r.status_code == 200:
                response_data = r.json()
                devices = response_data.get('devices', [])
                devices = {d['iden']: d['nickname'] for d in devices if d['active']}
                devices.update({'': ''})
                return devices
            else:
                logger.error(u"Tautulli Notifiers :: Unable to retrieve {name} devices list: "
                             u"[{r.status_code}] {r.reason}".format(name=self.NAME, r=r))
                logger.debug(u"Tautulli Notifiers :: Request response: {}".format(request.server_message(r, True)))
                return {'': ''}

        else:
            return {'': ''}

    def return_config_options(self):
        config_option = [{'label': 'Pushbullet Access Token',
                          'value': self.config['api_key'],
                          'name': 'pushbullet_api_key',
                          'description': 'Your Pushbullet access token.',
                          'input_type': 'text',
                          'refresh': True
                          },
                         {'label': 'Device',
                          'value': self.config['device_id'],
                          'name': 'pushbullet_device_id',
                          'description': 'Set your Pushbullet device. If set, will override channel tag. '
                                         'Leave blank to notify on all devices.',
                          'input_type': 'select',
                          'select_options': self.get_devices()
                          },
                         {'label': 'Channel',
                          'value': self.config['channel_tag'],
                          'name': 'pushbullet_channel_tag',
                          'description': 'A channel tag (optional).',
                          'input_type': 'text'
                          },
                         {'label': 'Include Subject Line',
                          'value': self.config['incl_subject'],
                          'name': 'pushbullet_incl_subject',
                          'description': 'Include the subject line with the notifications.',
                          'input_type': 'checkbox'
                          },
                         {'label': 'Include Poster Image',
                          'value': self.config['incl_poster'],
                          'name': 'pushbullet_incl_poster',
                          'description': 'Include a poster with the notifications.',
                          'input_type': 'checkbox'
                          }
                         ]

        return config_option


class PUSHOVER(Notifier):
    """
    Pushover notifications
    """
    NAME = 'Pushover'
    _DEFAULT_CONFIG = {'api_token': '',
                       'key': '',
                       'html_support': 1,
                       'sound': '',
                       'priority': 0,
                       'retry': 30,
                       'expire': 3600,
                       'incl_url': 1,
                       'incl_subject': 1,
                       'incl_poster': 0,
                       'movie_provider': '',
                       'tv_provider': '',
                       'music_provider': ''
                       }

    def agent_notify(self, subject='', body='', action='', **kwargs):
        data = {'token': self.config['api_token'],
                'user': self.config['key'],
                'message': body.encode("utf-8"),
                'sound': self.config['sound'],
                'html': self.config['html_support'],
                'priority': self.config['priority'],
                'timestamp': int(time.time())}

        if self.config['incl_subject']:
            data['title'] = subject.encode("utf-8")

        if self.config['priority'] == 2:
            data['retry'] = max(30, self.config['retry'])
            data['expire'] = max(30, self.config['expire'])

        headers = {'Content-type': 'application/x-www-form-urlencoded'}

        files = {}

        if self.config['incl_url'] and kwargs.get('parameters', {}).get('media_type'):
            # Grab formatted metadata
            pretty_metadata = PrettyMetadata(kwargs['parameters'])

            if pretty_metadata.media_type == 'movie':
                provider = self.config['movie_provider']
            elif pretty_metadata.media_type in ('show', 'season', 'episode'):
                provider = self.config['tv_provider']
            elif pretty_metadata.media_type in ('artist', 'album', 'track'):
                provider = self.config['music_provider']
            else:
                provider = None

            provider_link = pretty_metadata.get_provider_link(provider)
            caption = pretty_metadata.get_caption(provider)

            data['url'] = provider_link
            data['url_title'] = caption

        if self.config['incl_poster'] and kwargs.get('parameters', {}).get('media_type'):
            # Grab formatted metadata
            pretty_metadata = PrettyMetadata(kwargs['parameters'])

            # Retrieve the poster from Plex
            result = pmsconnect.PmsConnect().get_image(img=pretty_metadata.parameters.get('poster_thumb', ''))
            if result and result[0]:
                poster_content = result[0]
            else:
                poster_content = ''
                logger.error(u"Tautulli Notifiers :: Unable to retrieve image for {name}.".format(name=self.NAME))

            if poster_content:
                poster_filename = 'poster_{}.png'.format(pretty_metadata.parameters['rating_key'])
                files = {'attachment': (poster_filename, poster_content, 'image/png')}
                headers = {}

        return self.make_request('https://api.pushover.net/1/messages.json', headers=headers, data=data, files=files)

    def get_sounds(self):
        sounds = {
            '': '',
            'alien': 'Alien Alarm (long)',
            'bike': 'Bike',
            'bugle': 'Bugle',
            'cashregister': 'Cash Register',
            'classical': 'Classical',
            'climb': 'Climb (long)',
            'cosmic': 'Cosmic',
            'echo': 'Pushover Echo (long)',
            'falling': 'Falling',
            'gamelan': 'Gamelan',
            'incoming': 'Incoming',
            'intermission': 'Intermission',
            'magic': 'Magic',
            'mechanical': 'Mechanical',
            'none': 'None (silent)',
            'persistent': 'Persistent (long)',
            'pianobar': 'Piano Bar',
            'pushover': 'Pushover (default)',
            'siren': 'Siren',
            'spacealarm': 'Space Alarm',
            'tugboat': 'Tug Boat',
            'updown': 'Up Down (long)'
        }

        return sounds

        # if self.config['api_token']:
        #     params = {'token': self.config['api_token']}
        #
        #     r = requests.get('https://api.pushover.net/1/sounds.json', params=params)
        #
        #     if r.status_code == 200:
        #         response_data = r.json()
        #         sounds = response_data.get('sounds', {})
        #         sounds.update({'': ''})
        #         print sounds
        #         return sounds
        #     else:
        #         logger.error(u"Tautulli Notifiers :: Unable to retrieve {name} sounds list: "
        #                      u"[{r.status_code}] {r.reason}".format(name=self.NAME, r=r))
        #         logger.debug(u"Tautulli Notifiers :: Request response: {}".format(request.server_message(r, True)))
        #         return {'': ''}
        #
        # else:
        #     return {'': ''}

    def return_config_options(self):
        config_option = [{'label': 'Pushover API Token',
                          'value': self.config['api_token'],
                          'name': 'pushover_api_token',
                          'description': 'Your Pushover API token.',
                          'input_type': 'text',
                          'refresh': True
                          },
                         {'label': 'Pushover User or Group Key',
                          'value': self.config['key'],
                          'name': 'pushover_key',
                          'description': 'Your Pushover user or group key.',
                          'input_type': 'text'
                          },
                         {'label': 'Sound',
                          'value': self.config['sound'],
                          'name': 'pushover_sound',
                          'description': 'Set the notification sound. Leave blank for the default sound.',
                          'input_type': 'select',
                          'select_options': self.get_sounds()
                          },
                         {'label': 'Priority',
                          'value': self.config['priority'],
                          'name': 'pushover_priority',
                          'description': 'Set the notification priority.',
                          'input_type': 'select',
                          'select_options': {-2: -2, -1: -1, 0: 0, 1: 1, 2: 2}
                          },
                         {'label': 'Retry Interval',
                          'value': self.config['retry'],
                          'name': 'pushover_retry',
                          'description': 'Set the interval in seconds to keep retrying the notification.<br>'
                                         'Note: For priority 2 only. Minimum 30 seconds.',
                          'input_type': 'number'
                          },
                         {'label': 'Expire Duration',
                          'value': self.config['expire'],
                          'name': 'pushover_expire',
                          'description': 'Set the duration in seconds when the notification will stop retrying.<br>'
                                         'Note: For priority 2 only. Minimum 30 seconds.',
                          'input_type': 'number'
                          },
                         {'label': 'Enable HTML Support',
                          'value': self.config['html_support'],
                          'name': 'pushover_html_support',
                          'description': 'Style your messages using these HTML tags: b, i, u, a[href], font[color]',
                          'input_type': 'checkbox'
                          },
                         {'label': 'Include supplementary URL',
                          'value': self.config['incl_url'],
                          'name': 'pushover_incl_url',
                          'description': 'Include a supplementary URL with the notifications.',
                          'input_type': 'checkbox'
                          },
                         {'label': 'Include Subject Line',
                          'value': self.config['incl_subject'],
                          'name': 'pushover_incl_subject',
                          'description': 'Include the subject line with the notifications.',
                          'input_type': 'checkbox'
                          },
                         {'label': 'Include Poster Image',
                          'value': self.config['incl_poster'],
                          'name': 'pushover_incl_poster',
                          'description': 'Include a poster with the notifications.',
                          'input_type': 'checkbox'
                          },
                         {'label': 'Movie Link Source',
                          'value': self.config['movie_provider'],
                          'name': 'pushover_movie_provider',
                          'description': 'Select the source for movie links in the notification. Leave blank to disable.<br>'
                                         'Note: 3rd party API lookup may need to be enabled under the notifications settings tab.',
                          'input_type': 'select',
                          'select_options': PrettyMetadata().get_movie_providers()
                          },
                         {'label': 'TV Show Link Source',
                          'value': self.config['tv_provider'],
                          'name': 'pushover_tv_provider',
                          'description': 'Select the source for tv show links in the notification. Leave blank to disable.<br>'
                                         'Note: 3rd party API lookup may need to be enabled under the notifications settings tab.',
                          'input_type': 'select',
                          'select_options': PrettyMetadata().get_tv_providers()
                          },
                         {'label': 'Music Link Source',
                          'value': self.config['music_provider'],
                          'name': 'pushover_music_provider',
                          'description': 'Select the source for music links in the notification. Leave blank to disable.',
                          'input_type': 'select',
                          'select_options': PrettyMetadata().get_music_providers()
                          }
                         ]

        return config_option


class SCRIPTS(Notifier):
    """
    Script notifications
    """
    NAME = 'Script'
    _DEFAULT_CONFIG = {'script_folder': '',
                       'script': '',
                       'timeout': 30
                       }

    def __init__(self, config=None):
        super(SCRIPTS, self).__init__(config=config)

        self.script_exts = {'.bat': '',
                            '.cmd': '',
                            '.exe': '',
                            '.php': 'php',
                            '.pl': 'perl',
                            '.ps1': 'powershell -executionPolicy bypass -file',
                            '.py': 'python',
                            '.pyw': 'pythonw',
                            '.rb': 'ruby',
                            '.sh': ''
                            }

        self.arg_overrides = ('python2', 'python3', 'python', 'pythonw', 'php', 'ruby', 'perl')
        self.script_killed = False

    def list_scripts(self):
        scriptdir = self.config['script_folder']
        scripts = {'': ''}

        if scriptdir and not os.path.exists(scriptdir):
            return scripts

        for root, dirs, files in os.walk(scriptdir):
            for f in files:
                name, ext = os.path.splitext(f)
                if ext in self.script_exts.keys():
                    rfp = os.path.join(os.path.relpath(root, scriptdir), f)
                    fp = os.path.join(root, f)
                    scripts[fp] = rfp

        return scripts

    def run_script(self, script):
        # Common environment variables
        env = os.environ.copy()
        env.update({
            'PLEX_URL': plexpy.CONFIG.PMS_URL,
            'PLEX_TOKEN': plexpy.CONFIG.PMS_TOKEN,
            'TAUTULLI_URL': helpers.get_plexpy_url(hostname='localhost'),
            'TAUTULLI_APIKEY': plexpy.CONFIG.API_KEY,
            'TAUTULLI_ENCODING': plexpy.SYS_ENCODING,
            'PYTHONPATH': os.pathsep.join(sys.path)
            })

        try:
            process = subprocess.Popen(script,
                                       stdin=subprocess.PIPE,
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE,
                                       cwd=self.config['script_folder'],
                                       env=env)

            if self.config['timeout'] > 0:
                timer = threading.Timer(self.config['timeout'], self.kill_script, (process,))
            else:
                timer = None

            try:
                if timer:
                    timer.start()
                output, error = process.communicate()
                status = process.returncode
            finally:
                if timer:
                    timer.cancel()

        except OSError as e:
            logger.error(u"Tautulli Notifiers :: Failed to run script: %s" % e)
            return False

        if error:
            err = '\n  '.join([l for l in error.splitlines()])
            logger.error("Tautulli Notifiers :: Script error: \n  %s" % err)

        if output:
            out = '\n  '.join([l for l in output.splitlines()])
            logger.debug("Tautulli Notifiers :: Script returned: \n  %s" % out)

        if not self.script_killed:
            logger.info(u"Tautulli Notifiers :: Script notification sent.")
            return True

    def kill_script(self, process):
        process.kill()
        self.script_killed = True
        logger.warn(u"Tautulli Notifiers :: Script exceeded timeout limit of %d seconds. "
                    "Script killed." % self.config['timeout'])

    def agent_notify(self, subject='', body='', action='', **kwargs):
        """
            Args:
                  subject(string, optional): Subject text,
                  body(string, optional): Body text,
                  action(string): 'play'
        """
        if not self.config['script_folder']:
            logger.error(u"Tautulli Notifiers :: No script folder specified.")
            return

        script_args = kwargs.get('script_args', [])

        logger.debug(u"Tautulli Notifiers :: Trying to run notify script, action: %s, arguments: %s"
                     % (action, script_args))

        script = kwargs.get('script', self.config.get('script', ''))

        # Don't try to run the script if the action does not have one
        if action and not script:
            logger.debug(u"Tautulli Notifiers :: No script selected for action %s, exiting..." % action)
            return
        elif not script:
            logger.debug(u"Tautulli Notifiers :: No script selected, exiting...")
            return

        name, ext = os.path.splitext(script)
        prefix = self.script_exts.get(ext, '')

        if os.name == 'nt':
            script = script.encode(plexpy.SYS_ENCODING, 'ignore')

        if prefix:
            script = prefix.split() + [script]
        else:
            script = [script]

        # For manual notifications
        # if script_args and isinstance(script_args, basestring):
        #     # attemps for format it for the user
        #     script_args = [arg for arg in shlex.split(script_args.encode(plexpy.SYS_ENCODING, 'ignore'))]

        # Windows handles unicode very badly.
        # https://bugs.python.org/issue19264
        if script_args:  # and os.name == 'nt':
            script_args = [arg.encode(plexpy.SYS_ENCODING, 'ignore') for arg in script_args]

        # Allow overrides for shitty systems
        if prefix and script_args:
            if script_args[0] in self.arg_overrides:
                script[0] = script_args[0]
                del script_args[0]

        script.extend(script_args)

        logger.debug(u"Tautulli Notifiers :: Full script is: %s" % script)
        logger.debug(u"Tautulli Notifiers :: Executing script in a new thread.")
        thread = threading.Thread(target=self.run_script, args=(script,)).start()

        return True

    def return_config_options(self):
        config_option = [{'label': 'Supported File Types',
                          'description': '<span class="inline-pre">' + \
                              ', '.join(self.script_exts.keys()) + '</span>',
                          'input_type': 'help'
                          },
                         {'label': 'Script Folder',
                          'value': self.config['script_folder'],
                          'name': 'scripts_script_folder',
                          'description': 'Enter the full path to your script folder.',
                          'input_type': 'text',
                          'refresh': True
                          },
                         {'label': 'Script File',
                          'value': self.config['script'],
                          'name': 'scripts_script',
                          'description': 'Select the script file to run.',
                          'input_type': 'select',
                          'select_options': self.list_scripts()
                          },
                         {'label': 'Script Timeout',
                          'value': self.config['timeout'],
                          'name': 'scripts_timeout',
                          'description': 'The number of seconds to wait before killing the script. 0 to disable timeout.',
                          'input_type': 'number'
                          }
                         ]

        return config_option


class SLACK(Notifier):
    """
    Slack Notifications
    """
    NAME = 'Slack'
    _DEFAULT_CONFIG = {'hook': '',
                       'channel': '',
                       'username': '',
                       'icon_emoji': '',
                       'color': '',
                       'incl_subject': 1,
                       'incl_card': 0,
                       'incl_description': 1,
                       'incl_thumbnail': 0,
                       'incl_pmslink': 0,
                       'movie_provider': '',
                       'tv_provider': '',
                       'music_provider': ''
                       }

    def agent_notify(self, subject='', body='', action='', **kwargs):
        if self.config['incl_subject']:
            text = subject.encode('utf-8') + '\r\n' + body.encode("utf-8")
        else:
            text = body.encode("utf-8")

        data = {'text': text}
        if self.config['channel'] and self.config['channel'].startswith('#'):
            data['channel'] = self.config['channel']
        if self.config['username']:
            data['username'] = self.config['username']
        if self.config['icon_emoji']:
            if urlparse(self.config['icon_emoji']).scheme == '':
                data['icon_emoji'] = self.config['icon_emoji']
            else:
                data['icon_url'] = self.config['icon_emoji']

        if self.config['incl_card'] and kwargs.get('parameters', {}).get('media_type'):
            # Grab formatted metadata
            pretty_metadata = PrettyMetadata(kwargs['parameters'])

            if pretty_metadata.media_type == 'movie':
                provider = self.config['movie_provider']
            elif pretty_metadata.media_type in ('show', 'season', 'episode'):
                provider = self.config['tv_provider']
            elif pretty_metadata.media_type in ('artist', 'album', 'track'):
                provider = self.config['music_provider']
            else:
                provider = None

            poster_url = pretty_metadata.get_poster_url()
            provider_name = pretty_metadata.get_provider_name(provider)
            provider_link = pretty_metadata.get_provider_link(provider)
            title = pretty_metadata.get_title()
            description = pretty_metadata.get_description()
            plex_url = pretty_metadata.get_plex_url()

            # Build Slack post attachment
            attachment = {'fallback': 'Image for %s' % title,
                          'title': title
                          }

            if self.config['color'] and re.match(r'^#(?:[0-9a-fA-F]{3}){1,2}$', self.config['color']):
                attachment['color'] = self.config['color']

            if self.config['incl_thumbnail']:
                attachment['thumb_url'] = poster_url
            else:
                attachment['image_url'] = poster_url

            if self.config['incl_description'] or pretty_metadata.media_type in ('artist', 'album', 'track'):
                attachment['text'] = description

            fields = []
            if provider_link:
                attachment['title_link'] = provider_link
                fields.append({'title': 'View Details',
                               'value': '<%s|%s>' % (provider_link, provider_name),
                               'short': True})
            if self.config['incl_pmslink']:
                fields.append({'title': 'View Details',
                               'value': '<%s|%s>' % (plex_url, 'Plex Web'),
                               'short': True})
            if fields:
                attachment['fields'] = fields

            data['attachments'] = [attachment]

        headers = {'Content-type': 'application/json'}

        return self.make_request(self.config['hook'], headers=headers, json=data)

    def return_config_options(self):
        config_option = [{'label': 'Slack Webhook URL',
                          'value': self.config['hook'],
                          'name': 'slack_hook',
                          'description': 'Your Slack incoming webhook URL.',
                          'input_type': 'text'
                          },
                         {'label': 'Slack Channel',
                          'value': self.config['channel'],
                          'name': 'slack_channel',
                          'description': 'The Slack channel name (starting with \'#\') which will be used. Leave blank for webhook integration default.',
                          'input_type': 'text'
                          },
                         {'label': 'Slack Username',
                          'value': self.config['username'],
                          'name': 'slack_username',
                          'description': 'The Slack username which will be used. Leave blank for webhook integration default.',
                          'input_type': 'text'
                          },
                         {'label': 'Slack Icon',
                          'value': self.config['icon_emoji'],
                          'description': 'The Slack emoji or image url for the icon which will be used. Leave blank for webhook integration default.',
                          'name': 'slack_icon_emoji',
                          'input_type': 'text'
                          },
                         {'label': 'Slack Color',
                          'value': self.config['color'],
                          'description': 'The hex color value (starting with \'#\') for the border along the left side of the message attachment.',
                          'name': 'slack_color',
                          'input_type': 'text'
                          },
                         {'label': 'Include Subject Line',
                          'value': self.config['incl_subject'],
                          'name': 'slack_incl_subject',
                          'description': 'Include the subject line with the notifications.',
                          'input_type': 'checkbox'
                          },
                         {'label': 'Include Rich Metadata Info',
                          'value': self.config['incl_card'],
                          'name': 'slack_incl_card',
                          'description': 'Include an info card with a poster and metadata with the notifications.<br>'
                                         'Note: <a data-tab-destination="tabs-notifications" data-dismiss="modal" '
                                         'data-target="#notify_upload_posters">Image Hosting</a> '
                                         'must be enabled under the notifications settings tab.',
                          'input_type': 'checkbox'
                          },
                         {'label': 'Include Plot Summaries',
                          'value': self.config['incl_description'],
                          'name': 'slack_incl_description',
                          'description': 'Include a plot summary for movies and TV shows on the info card.',
                          'input_type': 'checkbox'
                          },
                         {'label': 'Include Link to Plex Web',
                          'value': self.config['incl_pmslink'],
                          'name': 'slack_incl_pmslink',
                          'description': 'Include a second link to the media in Plex Web on the info card.',
                          'input_type': 'checkbox'
                          },
                         {'label': 'Use Poster Thumbnail',
                          'value': self.config['incl_thumbnail'],
                          'name': 'slack_incl_thumbnail',
                          'description': 'Use a thumbnail instead of a full sized poster on the info card.',
                          'input_type': 'checkbox'
                          },
                         {'label': 'Movie Link Source',
                          'value': self.config['movie_provider'],
                          'name': 'slack_movie_provider',
                          'description': 'Select the source for movie links on the info cards. Leave blank to disable.<br>'
                                         'Note: 3rd party API lookup may need to be enabled under the notifications settings tab.',
                          'input_type': 'select',
                          'select_options': PrettyMetadata().get_movie_providers()
                          },
                         {'label': 'TV Show Link Source',
                          'value': self.config['tv_provider'],
                          'name': 'slack_tv_provider',
                          'description': 'Select the source for tv show links on the info cards. Leave blank to disable.<br>'
                                         'Note: 3rd party API lookup may need to be enabled under the notifications settings tab.',
                          'input_type': 'select',
                          'select_options': PrettyMetadata().get_tv_providers()
                          },
                         {'label': 'Music Link Source',
                          'value': self.config['music_provider'],
                          'name': 'slack_music_provider',
                          'description': 'Select the source for music links on the info cards. Leave blank to disable.',
                          'input_type': 'select',
                          'select_options': PrettyMetadata().get_music_providers()
                          }
                         ]

        return config_option


class TELEGRAM(Notifier):
    """
    Telegram notifications
    """
    NAME = 'Telegram'
    _DEFAULT_CONFIG = {'bot_token': '',
                       'chat_id': '',
                       'disable_web_preview': 0,
                       'html_support': 1,
                       'incl_subject': 1,
                       'incl_poster': 0
                       }

    def agent_notify(self, subject='', body='', action='', **kwargs):
        data = {'chat_id': self.config['chat_id']}

        if self.config['incl_subject']:
            text = subject.encode('utf-8') + '\r\n' + body.encode('utf-8')
        else:
            text = body.encode('utf-8')

        if self.config['html_support']:
            data['parse_mode'] = 'HTML'

        if self.config['incl_poster'] and kwargs.get('parameters'):
            # Grab formatted metadata
            pretty_metadata = PrettyMetadata(kwargs['parameters'])

            # Retrieve the poster from Plex
            result = pmsconnect.PmsConnect().get_image(img=pretty_metadata.parameters.get('poster_thumb', ''))
            if result and result[0]:
                poster_content = result[0]
            else:
                poster_content = ''
                logger.error(u"Tautulli Notifiers :: Unable to retrieve image for {name}.".format(name=self.NAME))

            if poster_content:
                poster_filename = 'poster_{}.png'.format(pretty_metadata.parameters['rating_key'])
                files = {'photo': (poster_filename, poster_content, 'image/png')}

                if len(text) > 200:
                    data['disable_notification'] = True
                else:
                    data['caption'] = text

                r = self.make_request('https://api.telegram.org/bot{}/sendPhoto'.format(self.config['bot_token']),
                                      data=data, files=files)

                if not data.pop('disable_notification', None):
                    return r

        data['text'] = text

        if self.config['disable_web_preview']:
            data['disable_web_page_preview'] = True

        headers = {'Content-type': 'application/x-www-form-urlencoded'}

        return self.make_request('https://api.telegram.org/bot{}/sendMessage'.format(self.config['bot_token']),
                                 headers=headers, data=data)

    def return_config_options(self):
        config_option = [{'label': 'Telegram Bot Token',
                          'value': self.config['bot_token'],
                          'name': 'telegram_bot_token',
                          'description': 'Your Telegram bot token. '
                                         'Contact <a href="' + helpers.anon_url('https://telegram.me/BotFather') +
                                         '" target="_blank">@BotFather</a>'
                                         ' on Telegram to get one.',
                          'input_type': 'text'
                          },
                         {'label': 'Telegram Chat ID, Group ID, or Channel Username',
                          'value': self.config['chat_id'],
                          'name': 'telegram_chat_id',
                          'description': 'Your Telegram Chat ID, Group ID, or @channelusername. '
                                         'Contact <a href="' + helpers.anon_url('https://telegram.me/myidbot') +
                                         '" target="_blank">@myidbot</a>'
                                         ' on Telegram to get an ID.',
                          'input_type': 'text'
                          },
                         {'label': 'Include Subject Line',
                          'value': self.config['incl_subject'],
                          'name': 'telegram_incl_subject',
                          'description': 'Include the subject line with the notifications.',
                          'input_type': 'checkbox'
                          },
                         {'label': 'Include Poster Image',
                          'value': self.config['incl_poster'],
                          'name': 'telegram_incl_poster',
                          'description': 'Include a poster with the notifications.',
                          'input_type': 'checkbox'
                          },
                         {'label': 'Enable HTML Support',
                          'value': self.config['html_support'],
                          'name': 'telegram_html_support',
                          'description': 'Style your messages using these HTML tags: b, i, a[href], code, pre.',
                          'input_type': 'checkbox'
                          },
                         {'label': 'Disable Web Page Previews',
                          'value': self.config['disable_web_preview'],
                          'name': 'telegram_disable_web_preview',
                          'description': 'Disables automatic link previews for links in the message',
                          'input_type': 'checkbox'
                          }
                         ]

        return config_option


class TWITTER(Notifier):
    """
    Twitter notifications
    """
    NAME = 'Twitter'
    REQUEST_TOKEN_URL = 'https://api.twitter.com/oauth/request_token'
    ACCESS_TOKEN_URL = 'https://api.twitter.com/oauth/access_token'
    AUTHORIZATION_URL = 'https://api.twitter.com/oauth/authorize'
    SIGNIN_URL = 'https://api.twitter.com/oauth/authenticate'
    _DEFAULT_CONFIG = {'access_token': '',
                       'access_token_secret': '',
                       'consumer_key': '',
                       'consumer_secret': '',
                       'incl_subject': 1,
                       'incl_poster': 0
                       }

    def _send_tweet(self, message=None, attachment=None):
        consumer_key = self.config['consumer_key']
        consumer_secret = self.config['consumer_secret']
        access_token = self.config['access_token']
        access_token_secret = self.config['access_token_secret']

        # logger.info(u"Tautulli Notifiers :: Sending tweet: " + message)

        api = twitter.Api(consumer_key, consumer_secret, access_token, access_token_secret)

        try:
            api.PostUpdate(message, media=attachment)
            logger.info(u"Tautulli Notifiers :: {name} notification sent.".format(name=self.NAME))
            return True
        except Exception as e:
            logger.error(u"Tautulli Notifiers :: {name} notification failed: {e}".format(name=self.NAME, e=e))
            return False

    def agent_notify(self, subject='', body='', action='', **kwargs):
        poster_url = ''
        if self.config['incl_poster'] and kwargs.get('parameters'):
            parameters = kwargs['parameters']
            poster_url = parameters.get('poster_url','')

        # Hack to add media type to attachment
        if poster_url and not helpers.get_img_service():
            poster_url += '.png'

        if self.config['incl_subject']:
            return self._send_tweet(subject + '\r\n' + body, attachment=poster_url)
        else:
            return self._send_tweet(body, attachment=poster_url)

    def return_config_options(self):
        config_option = [{'label': 'Twitter Consumer Key',
                          'value': self.config['consumer_key'],
                          'name': 'twitter_consumer_key',
                          'description': 'Your Twitter consumer key.',
                          'input_type': 'text'
                          },
                         {'label': 'Twitter Consumer Secret',
                          'value': self.config['consumer_secret'],
                          'name': 'twitter_consumer_secret',
                          'description': 'Your Twitter consumer secret.',
                          'input_type': 'text'
                          },
                         {'label': 'Twitter Access Token',
                          'value': self.config['access_token'],
                          'name': 'twitter_access_token',
                          'description': 'Your Twitter access token.',
                          'input_type': 'text'
                          },
                         {'label': 'Twitter Access Token Secret',
                          'value': self.config['access_token_secret'],
                          'name': 'twitter_access_token_secret',
                          'description': 'Your Twitter access token secret.',
                          'input_type': 'text'
                          },
                         {'label': 'Include Subject Line',
                          'value': self.config['incl_subject'],
                          'name': 'twitter_incl_subject',
                          'description': 'Include the subject line with the notifications.',
                          'input_type': 'checkbox'
                          },
                         {'label': 'Include Poster Image',
                          'value': self.config['incl_poster'],
                          'name': 'twitter_incl_poster',
                          'description': 'Include a poster with the notifications.<br>'
                                         'Note: <a data-tab-destination="tabs-notifications" data-dismiss="modal" '
                                         'data-target="#notify_upload_posters">Image Hosting</a> '
                                         'must be enabled under the notifications settings tab.',
                          'input_type': 'checkbox'
                          }
                         ]

        return config_option


class XBMC(Notifier):
    """
    Kodi notifications
    """
    NAME = 'Kodi'
    _DEFAULT_CONFIG = {'hosts': '',
                       'username': '',
                       'password': '',
                       'display_time': 5,
                       'image': ''
                       }

    def _sendhttp(self, host, command):
        url_command = urlencode(command)
        url = host + '/xbmcCmds/xbmcHttp/?' + url_command

        if self.config['password']:
            return request.request_content(url, auth=(self.config['username'], self.config['password']))
        else:
            return request.request_content(url)

    def _sendjson(self, host, method, params=None):
        params = params or {}
        data = [{'id': 0, 'jsonrpc': '2.0', 'method': method, 'params': params}]
        headers = {'Content-Type': 'application/json'}
        url = host + '/jsonrpc'

        if self.config['password']:
            response = request.request_json(url, method="post", data=json.dumps(data), headers=headers,
                                            auth=(self.config['username'], self.config['password']))
        else:
            response = request.request_json(url, method="post", data=json.dumps(data), headers=headers)

        if response:
            return response[0]['result']

    def agent_notify(self, subject='', body='', action='', **kwargs):
        hosts = [x.strip() for x in self.config['hosts'].split(',')]

        if self.config['display_time'] > 0:
            display_time = 1000 * self.config['display_time']  # in ms
        else:
            display_time = 5000

        if self.config['image']:
            image = self.config['image']
        else:
            image = os.path.join(plexpy.DATA_DIR, os.path.abspath("data/interfaces/default/images/logo-circle.png"))

        for host in hosts:
            logger.info(u"Tautulli Notifiers :: Sending notification command to XMBC @ " + host)
            try:
                version = self._sendjson(host, 'Application.GetProperties', {'properties': ['version']})['version']['major']

                if version < 12:  # Eden
                    notification = subject + "," + body + "," + str(display_time)
                    notifycommand = {'command': 'ExecBuiltIn', 'parameter': 'Notification(' + notification + ')'}
                    request = self._sendhttp(host, notifycommand)

                else:  # Frodo
                    params = {'title': subject, 'message': body, 'displaytime': display_time, 'image': image}
                    request = self._sendjson(host, 'GUI.ShowNotification', params)

                if not request:
                    raise Exception
                else:
                    logger.info(u"Tautulli Notifiers :: {name} notification sent.".format(name=self.NAME))

            except Exception as e:
                logger.error(u"Tautulli Notifiers :: {name} notification failed: {e}".format(name=self.NAME, e=e))
                return False

        return True

    def return_config_options(self):
        config_option = [{'label': 'Kodi Host Address',
                          'value': self.config['hosts'],
                          'name': 'xbmc_hosts',
                          'description': 'Host running Kodi (e.g. http://localhost:8080). Separate multiple hosts with commas (,).',
                          'input_type': 'text'
                          },
                         {'label': 'Kodi Username',
                          'value': self.config['username'],
                          'name': 'xbmc_username',
                          'description': 'Username of your Kodi client API (blank for none).',
                          'input_type': 'text'
                          },
                         {'label': 'Kodi Password',
                          'value': self.config['password'],
                          'name': 'xbmc_password',
                          'description': 'Password of your Kodi client API (blank for none).',
                          'input_type': 'password'
                          },
                         {'label': 'Notification Duration',
                          'value': self.config['display_time'],
                          'name': 'xbmc_display_time',
                          'description': 'The duration (in seconds) for the notification to stay on screen.',
                          'input_type': 'number'
                          },
                         {'label': 'Notification Icon',
                          'value': self.config['image'],
                          'name': 'xbmc_image',
                          'description': 'Full path or URL to an image to display with the notification. Leave blank for the default.',
                          'input_type': 'text'
                          }
                         ]

        return config_option


class ZAPIER(Notifier):
    """
    Zapier notifications
    """
    NAME = 'Zapier'
    _DEFAULT_CONFIG = {'hook': '',
                       'movie_provider': '',
                       'tv_provider': '',
                       'music_provider': ''
                       }

    def _test_hook(self):
        _test_data = {'subject': 'Subject',
                      'body': 'Body',
                      'action': 'Action',
                      'poster_url': 'https://i.imgur.com',
                      'provider_name': 'Provider Name',
                      'provider_link': 'http://www.imdb.com',
                      'plex_url': 'https://app.plex.tv/desktop'}

        return self.agent_notify(_test_data=_test_data)

    def agent_notify(self, subject='', body='', action='', **kwargs):
        data = {'subject': subject.encode("utf-8"),
                'body': body.encode("utf-8"),
                'action': action.encode("utf-8")}

        if kwargs.get('parameters', {}).get('media_type'):
            # Grab formatted metadata
            pretty_metadata = PrettyMetadata(kwargs['parameters'])

            if pretty_metadata.media_type == 'movie':
                provider = self.config['movie_provider']
            elif pretty_metadata.media_type in ('show', 'season', 'episode'):
                provider = self.config['tv_provider']
            elif pretty_metadata.media_type in ('artist', 'album', 'track'):
                provider = self.config['music_provider']
            else:
                provider = None

            poster_url = pretty_metadata.get_poster_url()
            provider_name = pretty_metadata.get_provider_name(provider)
            provider_link = pretty_metadata.get_provider_link(provider)
            plex_url = pretty_metadata.get_plex_url()

            data['poster_url'] = poster_url
            data['provider_name'] = provider_name
            data['provider_link'] = provider_link
            data['plex_url'] = plex_url

        if kwargs.get('_test_data'):
            data.update(kwargs['_test_data'])

        headers = {'Content-type': 'application/json'}

        return self.make_request(self.config['hook'], headers=headers, json=data)

    def return_config_options(self):
        config_option = [{'label': 'Zapier Webhook URL',
                          'value': self.config['hook'],
                          'name': 'zapier_hook',
                          'description': 'Your Zapier webhook URL.',
                          'input_type': 'text'
                          },
                         {'label': 'Test Zapier Webhook',
                          'value': 'Send Test Data',
                          'name': 'zapier_test_hook',
                          'description': 'Click this button when prompted on then "Test Webhooks by Zapier" step.',
                          'input_type': 'button'
                          },
                         {'label': 'Movie Link Source',
                          'value': self.config['movie_provider'],
                          'name': 'zapier_movie_provider',
                          'description': 'Select the source for movie links in the notification. Leave blank to disable.<br>'
                                         'Note: 3rd party API lookup may need to be enabled under the notifications settings tab.',
                          'input_type': 'select',
                          'select_options': PrettyMetadata().get_movie_providers()
                          },
                         {'label': 'TV Show Link Source',
                          'value': self.config['tv_provider'],
                          'name': 'zapier_tv_provider',
                          'description': 'Select the source for tv show links in the notification. Leave blank to disable.<br>'
                                         'Note: 3rd party API lookup may need to be enabled under the notifications settings tab.',
                          'input_type': 'select',
                          'select_options': PrettyMetadata().get_tv_providers()
                          },
                         {'label': 'Music Link Source',
                          'value': self.config['music_provider'],
                          'name': 'zapier_music_provider',
                          'description': 'Select the source for music links in the notification. Leave blank to disable.',
                          'input_type': 'select',
                          'select_options': PrettyMetadata().get_music_providers()
                          }
                         ]

        return config_option


def upgrade_config_to_db():
    logger.info(u"Tautulli Notifiers :: Upgrading to new notification system...")

    # Set flag first in case something fails we don't want to keep re-adding the notifiers
    plexpy.CONFIG.__setattr__('UPDATE_NOTIFIERS_DB', 0)
    plexpy.CONFIG.write()

    # Config section names from the {new: old} config
    section_overrides = {'xbmc': 'XBMC',
                         'nma': 'NMA',
                         'pushbullet': 'PushBullet',
                         'osx': 'OSX_Notify',
                         'ifttt': 'IFTTT'
                         }

    # Config keys from the {new: old} config
    config_key_overrides = {'plex': {'hosts': 'client_host'},
                            'facebook': {'access_token': 'token',
                                         'group_id': 'group',
                                         'incl_poster': 'incl_card'},
                            'join': {'api_key': 'apikey',
                                     'device_id': 'deviceid'},
                            'hipchat': {'hook': 'url',
                                        'incl_poster': 'incl_card'},
                            'nma': {'api_key': 'apikey'},
                            'osx': {'notify_app': 'app'},
                            'prowl': {'key': 'keys'},
                            'pushalot': {'api_key': 'apikey'},
                            'pushbullet': {'api_key': 'apikey',
                                           'device_id': 'deviceid'},
                            'pushover': {'api_token': 'apitoken',
                                         'key': 'keys'},
                            'scripts': {'script_folder': 'folder'},
                            'slack': {'incl_poster': 'incl_card'}
                            }

    # Get Monitoring config section
    monitoring = plexpy.CONFIG._config['Monitoring']

    # Get the new default notification subject and body text
    defualt_subject_text = {a['name']: a['subject'] for a in available_notification_actions()}
    defualt_body_text = {a['name']: a['body'] for a in available_notification_actions()}

    # Get the old notification subject and body text
    notify_text = {}
    for action in get_notify_actions():
        subject_key = 'notify_' + action + '_subject_text'
        body_key = 'notify_' + action + '_body_text'
        notify_text[action + '_subject'] = monitoring.get(subject_key, defualt_subject_text[action])
        notify_text[action + '_body'] = monitoring.get(body_key, defualt_body_text[action])

    # Check through each notification agent
    for agent in get_notify_agents():
        agent_id = AGENT_IDS[agent]

        # Get the old config section for the agent
        agent_section = section_overrides.get(agent, agent.capitalize())
        agent_config = plexpy.CONFIG._config.get(agent_section)
        agent_config_key = agent_section.lower()

        # Make sure there is an existing config section (to prevent adding v2 agents)
        if not agent_config:
            continue

        # Get all the actions for the agent
        agent_actions = {}
        for action in get_notify_actions():
            a_key = agent_config_key + '_' + action
            agent_actions[action] = helpers.cast_to_int(agent_config.get(a_key, 0))

        # Check if any of the actions were enabled
        # If so, the agent will be added to the database
        if any(agent_actions.values()):
            # Get the new default config for the agent
            notifier_default_config = get_agent_class(agent_id).config

            # Update the new config with the old config values
            notifier_config = {}
            for conf, val in notifier_default_config.iteritems():
                c_key = agent_config_key + '_' + config_key_overrides.get(agent, {}).get(conf, conf)
                notifier_config[agent + '_' + conf] = agent_config.get(c_key, val)

            # Special handling for scripts - one script with multiple actions
            if agent == 'scripts':
                # Get the old script arguments
                script_args = monitoring.get('notify_scripts_args_text', '')

                # Get the old scripts for each action
                action_scripts = {}
                for action in get_notify_actions():
                    s_key = agent + '_' + action + '_script'
                    action_scripts[action] = agent_config.get(s_key, '')

                # Reverse the dict to {script: [actions]}
                script_actions = {}
                for k, v in action_scripts.items():
                    if v: script_actions.setdefault(v, set()).add(k)

                # Add a new script notifier for each script if the action was enabled
                for script, actions in script_actions.items():
                    if any(agent_actions[a] for a in actions):
                        temp_config = notifier_config
                        temp_config.update({a: 0 for a in agent_actions.keys()})
                        temp_config.update({a + '_subject': '' for a in agent_actions.keys()})
                        for a in actions:
                            if agent_actions[a]:
                                temp_config[a] = agent_actions[a]
                                temp_config[a + '_subject'] = script_args
                                temp_config[agent + '_script'] = script

                        # Add a new notifier and update the config
                        notifier_id = add_notifier_config(agent_id=agent_id)
                        set_notifier_config(notifier_id=notifier_id, agent_id=agent_id, **temp_config)

            else:
                notifier_config.update(agent_actions)
                notifier_config.update(notify_text)

                # Add a new notifier and update the config
                notifier_id = add_notifier_config(agent_id=agent_id)
                set_notifier_config(notifier_id=notifier_id, agent_id=agent_id, **notifier_config)


def check_browser_enabled():
    global BROWSER_NOTIFIERS
    BROWSER_NOTIFIERS = {}
    for n in get_notifiers():
        if n['agent_id'] == 17 and n['active']:
            notifier_config = get_notifier_config(n['id'])
            BROWSER_NOTIFIERS[n['id']] = notifier_config['config']['auto_hide_delay']


def get_browser_notifications():
    db = database.MonitorDatabase()
    result = db.select('SELECT notifier_id, subject_text, body_text FROM notify_log '
                       'WHERE agent_id = 17 AND timestamp >= ? ',
                       args=[time.time() - 5])

    notifications = []
    for item in result:
        notification = {'subject_text': item['subject_text'],
                        'body_text': item['body_text'],
                        'delay': BROWSER_NOTIFIERS.get(item['notifier_id'], 5)}
        notifications.append(notification)

    return {'notifications': notifications}
