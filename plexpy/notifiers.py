#  This file is part of PlexPy.
#
#  PlexPy is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  PlexPy is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with PlexPy.  If not, see <http://www.gnu.org/licenses/>.

from plexpy import logger, helpers, common, request
from plexpy.helpers import checked, radio

from xml.dom import minidom
from httplib import HTTPSConnection
from urlparse import parse_qsl
from urllib import urlencode
from pynma import pynma

import base64
import cherrypy
import urllib
import urllib2
import plexpy
import os.path
import subprocess
import gntp.notifier
import json

import oauth2 as oauth
import pythontwitter as twitter

from email.mime.text import MIMEText
import smtplib
import email.utils

AGENT_IDS = {"Growl": 0,
             "Prowl": 1,
             "XBMC": 2,
             "Plex": 3,
             "NMA": 4,
             "Pushalot": 5,
             "Pushbullet": 6,
             "Pushover": 7,
             "OSX Notify": 8,
             "Boxcar2": 9,
             "Email": 10,
             "Twitter": 11,
             "IFTTT": 12,
             "Telegram": 13}

def available_notification_agents():
    agents = [{'name': 'Growl',
               'id': AGENT_IDS['Growl'],
               'config_prefix': 'growl',
               'has_config': True,
               'state': checked(plexpy.CONFIG.GROWL_ENABLED),
               'on_play': plexpy.CONFIG.GROWL_ON_PLAY,
               'on_stop': plexpy.CONFIG.GROWL_ON_STOP,
               'on_pause': plexpy.CONFIG.GROWL_ON_PAUSE,
               'on_resume': plexpy.CONFIG.GROWL_ON_RESUME,
               'on_buffer': plexpy.CONFIG.GROWL_ON_BUFFER,
               'on_watched': plexpy.CONFIG.GROWL_ON_WATCHED,
               'on_created': plexpy.CONFIG.GROWL_ON_CREATED,
               'on_extdown': plexpy.CONFIG.GROWL_ON_EXTDOWN,
               'on_intdown': plexpy.CONFIG.GROWL_ON_INTDOWN
               },
              {'name': 'Prowl',
               'id': AGENT_IDS['Prowl'],
               'config_prefix': 'prowl',
               'has_config': True,
               'state': checked(plexpy.CONFIG.PROWL_ENABLED),
               'on_play': plexpy.CONFIG.PROWL_ON_PLAY,
               'on_stop': plexpy.CONFIG.PROWL_ON_STOP,
               'on_pause': plexpy.CONFIG.PROWL_ON_PAUSE,
               'on_resume': plexpy.CONFIG.PROWL_ON_RESUME,
               'on_buffer': plexpy.CONFIG.PROWL_ON_BUFFER,
               'on_watched': plexpy.CONFIG.PROWL_ON_WATCHED,
               'on_created': plexpy.CONFIG.PROWL_ON_CREATED,
               'on_extdown': plexpy.CONFIG.PROWL_ON_EXTDOWN,
               'on_intdown': plexpy.CONFIG.PROWL_ON_INTDOWN
               },
              {'name': 'XBMC',
               'id': AGENT_IDS['XBMC'],
               'config_prefix': 'xbmc',
               'has_config': True,
               'state': checked(plexpy.CONFIG.XBMC_ENABLED),
               'on_play': plexpy.CONFIG.XBMC_ON_PLAY,
               'on_stop': plexpy.CONFIG.XBMC_ON_STOP,
               'on_pause': plexpy.CONFIG.XBMC_ON_PAUSE,
               'on_resume': plexpy.CONFIG.XBMC_ON_RESUME,
               'on_buffer': plexpy.CONFIG.XBMC_ON_BUFFER,
               'on_watched': plexpy.CONFIG.XBMC_ON_WATCHED,
               'on_created': plexpy.CONFIG.XBMC_ON_CREATED,
               'on_extdown': plexpy.CONFIG.XBMC_ON_EXTDOWN,
               'on_intdown': plexpy.CONFIG.XBMC_ON_INTDOWN
               },
              {'name': 'Plex',
               'id': AGENT_IDS['Plex'],
               'config_prefix': 'plex',
               'has_config': True,
               'state': checked(plexpy.CONFIG.PLEX_ENABLED),
               'on_play': plexpy.CONFIG.PLEX_ON_PLAY,
               'on_stop': plexpy.CONFIG.PLEX_ON_STOP,
               'on_pause': plexpy.CONFIG.PLEX_ON_PAUSE,
               'on_resume': plexpy.CONFIG.PLEX_ON_RESUME,
               'on_buffer': plexpy.CONFIG.PLEX_ON_BUFFER,
               'on_watched': plexpy.CONFIG.PLEX_ON_WATCHED,
               'on_created': plexpy.CONFIG.PLEX_ON_CREATED,
               'on_extdown': plexpy.CONFIG.PLEX_ON_EXTDOWN,
               'on_intdown': plexpy.CONFIG.PLEX_ON_INTDOWN
               },
              {'name': 'NotifyMyAndroid',
               'id': AGENT_IDS['NMA'],
               'config_prefix': 'nma',
               'has_config': True,
               'state': checked(plexpy.CONFIG.NMA_ENABLED),
               'on_play': plexpy.CONFIG.NMA_ON_PLAY,
               'on_stop': plexpy.CONFIG.NMA_ON_STOP,
               'on_pause': plexpy.CONFIG.NMA_ON_PAUSE,
               'on_resume': plexpy.CONFIG.NMA_ON_RESUME,
               'on_buffer': plexpy.CONFIG.NMA_ON_BUFFER,
               'on_watched': plexpy.CONFIG.NMA_ON_WATCHED,
               'on_created': plexpy.CONFIG.NMA_ON_CREATED,
               'on_extdown': plexpy.CONFIG.NMA_ON_EXTDOWN,
               'on_intdown': plexpy.CONFIG.NMA_ON_INTDOWN
               },
              {'name': 'Pushalot',
               'id': AGENT_IDS['Pushalot'],
               'config_prefix': 'pushalot',
               'has_config': True,
               'state': checked(plexpy.CONFIG.PUSHALOT_ENABLED),
               'on_play': plexpy.CONFIG.PUSHALOT_ON_PLAY,
               'on_stop': plexpy.CONFIG.PUSHALOT_ON_STOP,
               'on_pause': plexpy.CONFIG.PUSHALOT_ON_PAUSE,
               'on_resume': plexpy.CONFIG.PUSHALOT_ON_RESUME,
               'on_buffer': plexpy.CONFIG.PUSHALOT_ON_BUFFER,
               'on_watched': plexpy.CONFIG.PUSHALOT_ON_WATCHED,
               'on_created': plexpy.CONFIG.PUSHALOT_ON_CREATED,
               'on_extdown': plexpy.CONFIG.PUSHALOT_ON_EXTDOWN,
               'on_intdown': plexpy.CONFIG.PUSHALOT_ON_INTDOWN
               },
              {'name': 'Pushbullet',
               'id': AGENT_IDS['Pushbullet'],
               'config_prefix': 'pushbullet',
               'has_config': True,
               'state': checked(plexpy.CONFIG.PUSHBULLET_ENABLED),
               'on_play': plexpy.CONFIG.PUSHBULLET_ON_PLAY,
               'on_stop': plexpy.CONFIG.PUSHBULLET_ON_STOP,
               'on_pause': plexpy.CONFIG.PUSHBULLET_ON_PAUSE,
               'on_resume': plexpy.CONFIG.PUSHBULLET_ON_RESUME,
               'on_buffer': plexpy.CONFIG.PUSHBULLET_ON_BUFFER,
               'on_watched': plexpy.CONFIG.PUSHBULLET_ON_WATCHED,
               'on_created': plexpy.CONFIG.PUSHBULLET_ON_CREATED,
               'on_extdown': plexpy.CONFIG.PUSHBULLET_ON_EXTDOWN,
               'on_intdown': plexpy.CONFIG.PUSHBULLET_ON_INTDOWN
               },
              {'name': 'Pushover',
               'id': AGENT_IDS['Pushover'],
               'config_prefix': 'pushover',
               'has_config': True,
               'state': checked(plexpy.CONFIG.PUSHOVER_ENABLED),
               'on_play': plexpy.CONFIG.PUSHOVER_ON_PLAY,
               'on_stop': plexpy.CONFIG.PUSHOVER_ON_STOP,
               'on_pause': plexpy.CONFIG.PUSHOVER_ON_PAUSE,
               'on_resume': plexpy.CONFIG.PUSHOVER_ON_RESUME,
               'on_buffer': plexpy.CONFIG.PUSHOVER_ON_BUFFER,
               'on_watched': plexpy.CONFIG.PUSHOVER_ON_WATCHED,
               'on_created': plexpy.CONFIG.PUSHOVER_ON_CREATED,
               'on_extdown': plexpy.CONFIG.PUSHOVER_ON_EXTDOWN,
               'on_intdown': plexpy.CONFIG.PUSHOVER_ON_INTDOWN
               },
              {'name': 'Boxcar2',
               'id': AGENT_IDS['Boxcar2'],
               'config_prefix': 'boxcar',
               'has_config': True,
               'state': checked(plexpy.CONFIG.BOXCAR_ENABLED),
               'on_play': plexpy.CONFIG.BOXCAR_ON_PLAY,
               'on_stop': plexpy.CONFIG.BOXCAR_ON_STOP,
               'on_pause': plexpy.CONFIG.BOXCAR_ON_PAUSE,
               'on_resume': plexpy.CONFIG.BOXCAR_ON_RESUME,
               'on_buffer': plexpy.CONFIG.BOXCAR_ON_BUFFER,
               'on_watched': plexpy.CONFIG.BOXCAR_ON_WATCHED,
               'on_created': plexpy.CONFIG.BOXCAR_ON_CREATED,
               'on_extdown': plexpy.CONFIG.BOXCAR_ON_EXTDOWN,
               'on_intdown': plexpy.CONFIG.BOXCAR_ON_INTDOWN
               },
              {'name': 'E-mail',
               'id': AGENT_IDS['Email'],
               'config_prefix': 'email',
               'has_config': True,
               'state': checked(plexpy.CONFIG.EMAIL_ENABLED),
               'on_play': plexpy.CONFIG.EMAIL_ON_PLAY,
               'on_stop': plexpy.CONFIG.EMAIL_ON_STOP,
               'on_pause': plexpy.CONFIG.EMAIL_ON_PAUSE,
               'on_resume': plexpy.CONFIG.EMAIL_ON_RESUME,
               'on_buffer': plexpy.CONFIG.EMAIL_ON_BUFFER,
               'on_watched': plexpy.CONFIG.EMAIL_ON_WATCHED,
               'on_created': plexpy.CONFIG.EMAIL_ON_CREATED,
               'on_extdown': plexpy.CONFIG.EMAIL_ON_EXTDOWN,
               'on_intdown': plexpy.CONFIG.EMAIL_ON_INTDOWN
               },
              {'name': 'Twitter',
               'id': AGENT_IDS['Twitter'],
               'config_prefix': 'twitter',
               'has_config': True,
               'state': checked(plexpy.CONFIG.TWITTER_ENABLED),
               'on_play': plexpy.CONFIG.TWITTER_ON_PLAY,
               'on_stop': plexpy.CONFIG.TWITTER_ON_STOP,
               'on_pause': plexpy.CONFIG.TWITTER_ON_PAUSE,
               'on_resume': plexpy.CONFIG.TWITTER_ON_RESUME,
               'on_buffer': plexpy.CONFIG.TWITTER_ON_BUFFER,
               'on_watched': plexpy.CONFIG.TWITTER_ON_WATCHED,
               'on_created': plexpy.CONFIG.TWITTER_ON_CREATED,
               'on_extdown': plexpy.CONFIG.TWITTER_ON_EXTDOWN,
               'on_intdown': plexpy.CONFIG.TWITTER_ON_INTDOWN
               },
              {'name': 'IFTTT',
               'id': AGENT_IDS['IFTTT'],
               'config_prefix': 'ifttt',
               'has_config': True,
               'state': checked(plexpy.CONFIG.IFTTT_ENABLED),
               'on_play': plexpy.CONFIG.IFTTT_ON_PLAY,
               'on_stop': plexpy.CONFIG.IFTTT_ON_STOP,
               'on_pause': plexpy.CONFIG.IFTTT_ON_PAUSE,
               'on_resume': plexpy.CONFIG.IFTTT_ON_RESUME,
               'on_buffer': plexpy.CONFIG.IFTTT_ON_BUFFER,
               'on_watched': plexpy.CONFIG.IFTTT_ON_WATCHED,
               'on_created': plexpy.CONFIG.IFTTT_ON_CREATED,
               'on_extdown': plexpy.CONFIG.IFTTT_ON_EXTDOWN,
               'on_intdown': plexpy.CONFIG.IFTTT_ON_INTDOWN
               },
              {'name': 'Telegram',
               'id': AGENT_IDS['Telegram'],
               'config_prefix': 'telegram',
               'has_config': True,
               'state': checked(plexpy.CONFIG.TELEGRAM_ENABLED),
               'on_play': plexpy.CONFIG.TELEGRAM_ON_PLAY,
               'on_stop': plexpy.CONFIG.TELEGRAM_ON_STOP,
               'on_pause': plexpy.CONFIG.TELEGRAM_ON_PAUSE,
               'on_resume': plexpy.CONFIG.TELEGRAM_ON_RESUME,
               'on_buffer': plexpy.CONFIG.TELEGRAM_ON_BUFFER,
               'on_watched': plexpy.CONFIG.TELEGRAM_ON_WATCHED,
               'on_created': plexpy.CONFIG.TELEGRAM_ON_CREATED,
               'on_extdown': plexpy.CONFIG.TELEGRAM_ON_EXTDOWN,
               'on_intdown': plexpy.CONFIG.TELEGRAM_ON_INTDOWN
               }
              ]

    # OSX Notifications should only be visible if it can be used
    osx_notify = OSX_NOTIFY()
    if osx_notify.validate():
        agents.append({'name': 'OSX Notify',
                       'id': AGENT_IDS['OSX Notify'],
                       'config_prefix': 'osx_notify',
                       'has_config': True,
                       'state': checked(plexpy.CONFIG.OSX_NOTIFY_ENABLED),
                       'on_play': plexpy.CONFIG.OSX_NOTIFY_ON_PLAY,
                       'on_stop': plexpy.CONFIG.OSX_NOTIFY_ON_STOP,
                       'on_pause': plexpy.CONFIG.OSX_NOTIFY_ON_PAUSE,
                       'on_resume': plexpy.CONFIG.OSX_NOTIFY_ON_RESUME,
                       'on_buffer': plexpy.CONFIG.OSX_NOTIFY_ON_BUFFER,
                       'on_watched': plexpy.CONFIG.OSX_NOTIFY_ON_WATCHED,
                       'on_created': plexpy.CONFIG.OSX_NOTIFY_ON_CREATED,
                       'on_extdown': plexpy.CONFIG.OSX_NOTIFY_ON_EXTDOWN,
                       'on_intdown': plexpy.CONFIG.OSX_NOTIFY_ON_INTDOWN
                       })

    return agents

def get_notification_agent_config(config_id):
    if config_id:
        config_id = int(config_id)

        if config_id == 0:
            growl = GROWL()
            return growl.return_config_options()
        elif config_id == 1:
            prowl = PROWL()
            return prowl.return_config_options()
        elif config_id == 2:
            xbmc = XBMC()
            return xbmc.return_config_options()
        elif config_id == 3:
            plex = Plex()
            return plex.return_config_options()
        elif config_id == 4:
            nma = NMA()
            return nma.return_config_options()
        elif config_id == 5:
            pushalot = PUSHALOT()
            return pushalot.return_config_options()
        elif config_id == 6:
            pushbullet = PUSHBULLET()
            return pushbullet.return_config_options()
        elif config_id == 7:
            pushover = PUSHOVER()
            return pushover.return_config_options()
        elif config_id == 8:
            osx_notify = OSX_NOTIFY()
            return osx_notify.return_config_options()
        elif config_id == 9:
            boxcar = BOXCAR()
            return boxcar.return_config_options()
        elif config_id == 10:
            email = Email()
            return email.return_config_options()
        elif config_id == 11:
            tweet = TwitterNotifier()
            return tweet.return_config_options()
        elif config_id == 12:
            iftttClient = IFTTT()
            return iftttClient.return_config_options()
        elif config_id == 13:
          telegramClient = TELEGRAM()
          return telegramClient.return_config_options()
        else:
            return []
    else:
        return []

def send_notification(config_id, subject, body):
    if config_id:
        config_id = int(config_id)

        if config_id == 0:
            growl = GROWL()
            growl.notify(message=body, event=subject)
        elif config_id == 1:
            prowl = PROWL()
            prowl.notify(message=body, event=subject)
        elif config_id == 2:
            xbmc = XBMC()
            xbmc.notify(subject=subject, message=body)
        elif config_id == 3:
            plex = Plex()
            plex.notify(subject=subject, message=body)
        elif config_id == 4:
            nma = NMA()
            nma.notify(subject=subject, message=body)
        elif config_id == 5:
            pushalot = PUSHALOT()
            pushalot.notify(message=body, event=subject)
        elif config_id == 6:
            pushbullet = PUSHBULLET()
            pushbullet.notify(message=body, subject=subject)
        elif config_id == 7:
            pushover = PUSHOVER()
            pushover.notify(message=body, event=subject)
        elif config_id == 8:
            osx_notify = OSX_NOTIFY()
            osx_notify.notify(title=subject, text=body)
        elif config_id == 9:
            boxcar = BOXCAR()
            boxcar.notify(title=subject, message=body)
        elif config_id == 10:
            email = Email()
            email.notify(subject=subject, message=body)
        elif config_id == 11:
            tweet = TwitterNotifier()
            tweet.notify(subject=subject, message=body)
        elif config_id == 12:
            iftttClient = IFTTT()
            iftttClient.notify(subject=subject, message=body)
        elif config_id == 13:
          telegramClient = TELEGRAM()
          telegramClient.notify(message=body, event=subject)
        else:
            logger.debug(u"PlexPy Notifier :: Unknown agent id received.")
    else:
        logger.debug(u"PlexPy Notifier :: Notification requested but no agent id received.")


class GROWL(object):
    """
    Growl notifications, for OS X.
    """

    def __init__(self):
        self.enabled = plexpy.CONFIG.GROWL_ENABLED
        self.host = plexpy.CONFIG.GROWL_HOST
        self.password = plexpy.CONFIG.GROWL_PASSWORD
        self.on_play = plexpy.CONFIG.GROWL_ON_PLAY
        self.on_stop = plexpy.CONFIG.GROWL_ON_STOP
        self.on_watched = plexpy.CONFIG.GROWL_ON_WATCHED

    def conf(self, options):
        return cherrypy.config['config'].get('Growl', options)

    def notify(self, message, event):
        if not message or not event:
            return

        # Split host and port
        if self.host == "":
            host, port = "localhost", 23053
        if ":" in self.host:
            host, port = self.host.split(':', 1)
            port = int(port)
        else:
            host, port = self.host, 23053

        # If password is empty, assume none
        if self.password == "":
            password = None
        else:
            password = self.password

        # Register notification
        growl = gntp.notifier.GrowlNotifier(
            applicationName='PlexPy',
            notifications=['New Event'],
            defaultNotifications=['New Event'],
            hostname=host,
            port=port,
            password=password
        )

        try:
            growl.register()
        except gntp.notifier.errors.NetworkError:
            logger.warning(u'Growl notification failed: network error')
            return
        except gntp.notifier.errors.AuthError:
            logger.warning(u'Growl notification failed: authentication error')
            return

        # Fix message
        message = message.encode(plexpy.SYS_ENCODING, "replace")

        # Send it, including an image
        image_file = os.path.join(str(plexpy.PROG_DIR),
            "data/images/plexpylogo.png")

        with open(image_file, 'rb') as f:
            image = f.read()

        try:
            growl.notify(
                noteType='New Event',
                title=event,
                description=message,
                icon=image
            )
        except gntp.notifier.errors.NetworkError:
            logger.warning(u'Growl notification failed: network error')
            return

        logger.info(u"Growl notifications sent.")

    def updateLibrary(self):
        #For uniformity reasons not removed
        return

    def test(self, host, password):
        self.enabled = True
        self.host = host
        self.password = password

        self.notify('ZOMG Lazors Pewpewpew!', 'Test Message')

    def return_config_options(self):
        config_option = [{'label': 'Growl Host',
                          'value': self.host,
                          'name': 'growl_host',
                          'description': 'Your Growl hostname.',
                          'input_type': 'text'
                          },
                         {'label': 'Growl Password',
                          'value': self.password,
                          'name': 'growl_password',
                          'description': 'Your Growl password.',
                          'input_type': 'password'
                          }
                         ]

        return config_option

class PROWL(object):
    """
    Prowl notifications.
    """

    def __init__(self):
        self.enabled = plexpy.CONFIG.PROWL_ENABLED
        self.keys = plexpy.CONFIG.PROWL_KEYS
        self.priority = plexpy.CONFIG.PROWL_PRIORITY
        self.on_play = plexpy.CONFIG.PROWL_ON_PLAY
        self.on_stop = plexpy.CONFIG.PROWL_ON_STOP
        self.on_watched = plexpy.CONFIG.PROWL_ON_WATCHED

    def conf(self, options):
        return cherrypy.config['config'].get('Prowl', options)

    def notify(self, message, event):
        if not message or not event:
            return

        http_handler = HTTPSConnection("api.prowlapp.com")

        data = {'apikey': plexpy.CONFIG.PROWL_KEYS,
                'application': 'PlexPy',
                'event': event,
                'description': message.encode("utf-8"),
                'priority': plexpy.CONFIG.PROWL_PRIORITY}

        http_handler.request("POST",
                                "/publicapi/add",
                                headers={'Content-type': "application/x-www-form-urlencoded"},
                                body=urlencode(data))
        response = http_handler.getresponse()
        request_status = response.status

        if request_status == 200:
                logger.info(u"Prowl notifications sent.")
                return True
        elif request_status == 401:
                logger.info(u"Prowl auth failed: %s" % response.reason)
                return False
        else:
                logger.info(u"Prowl notification failed.")
                return False

    def updateLibrary(self):
        #For uniformity reasons not removed
        return

    def test(self, keys, priority):
        self.enabled = True
        self.keys = keys
        self.priority = priority

        self.notify('ZOMG Lazors Pewpewpew!', 'Test Message')

    def return_config_options(self):
        config_option = [{'label': 'Prowl API Key',
                          'value': self.keys,
                          'name': 'prowl_keys',
                          'description': 'Your Prowl API key.',
                          'input_type': 'text'
                          },
                         {'label': 'Priority',
                          'value': self.priority,
                          'name': 'prowl_priority',
                          'description': 'Set the priority.',
                          'input_type': 'select',
                          'select_options': {-2: -2, -1: -1, 0: 0, 1: 1, 2: 2}
                          }
                         ]

        return config_option

class XBMC(object):
    """
    XBMC notifications
    """

    def __init__(self):

        self.hosts = plexpy.CONFIG.XBMC_HOST
        self.username = plexpy.CONFIG.XBMC_USERNAME
        self.password = plexpy.CONFIG.XBMC_PASSWORD
        self.on_play = plexpy.CONFIG.XBMC_ON_PLAY
        self.on_stop = plexpy.CONFIG.XBMC_ON_STOP
        self.on_watched = plexpy.CONFIG.XBMC_ON_WATCHED

    def _sendhttp(self, host, command):
        url_command = urllib.urlencode(command)
        url = host + '/xbmcCmds/xbmcHttp/?' + url_command

        if self.password:
            return request.request_content(url, auth=(self.username, self.password))
        else:
            return request.request_content(url)

    def _sendjson(self, host, method, params={}):
        data = [{'id': 0, 'jsonrpc': '2.0', 'method': method, 'params': params}]
        headers = {'Content-Type': 'application/json'}
        url = host + '/jsonrpc'

        if self.password:
            response = request.request_json(url, method="post", data=json.dumps(data), headers=headers, auth=(self.username, self.password))
        else:
            response = request.request_json(url, method="post", data=json.dumps(data), headers=headers)

        if response:
            return response[0]['result']

    def notify(self, subject=None, message=None):

        hosts = [x.strip() for x in self.hosts.split(',')]

        header = subject
        message = message
        time = "3000" # in ms

        for host in hosts:
            logger.info('Sending notification command to XMBC @ ' + host)
            try:
                version = self._sendjson(host, 'Application.GetProperties', {'properties': ['version']})['version']['major']

                if version < 12: #Eden
                    notification = header + "," + message + "," + time
                    notifycommand = {'command': 'ExecBuiltIn', 'parameter': 'Notification(' + notification + ')'}
                    request = self._sendhttp(host, notifycommand)

                else: #Frodo
                    params = {'title': header, 'message': message, 'displaytime': int(time)}
                    request = self._sendjson(host, 'GUI.ShowNotification', params)

                if not request:
                    raise Exception

            except Exception:
                logger.error('Error sending notification request to XBMC')

    def return_config_options(self):
        config_option = [{'label': 'XBMC Host:Port',
                          'value': self.hosts,
                          'name': 'xbmc_host',
                          'description': 'Host running XBMC (e.g. http://localhost:8080). Separate multiple hosts with commas.',
                          'input_type': 'text'
                          },
                         {'label': 'XBMC Username',
                          'value': self.username,
                          'name': 'xbmc_username',
                          'description': 'Your XBMC username.',
                          'input_type': 'text'
                          },
                         {'label': 'XBMC Password',
                          'value': self.password,
                          'name': 'xbmc_password',
                          'description': 'Your XMBC password.',
                          'input_type': 'password'
                          }
                         ]

        return config_option

class Plex(object):
    def __init__(self):

        self.client_hosts = plexpy.CONFIG.PLEX_CLIENT_HOST
        self.username = plexpy.CONFIG.PLEX_USERNAME
        self.password = plexpy.CONFIG.PLEX_PASSWORD
        self.on_play = plexpy.CONFIG.PLEX_ON_PLAY
        self.on_stop = plexpy.CONFIG.PLEX_ON_STOP
        self.on_watched = plexpy.CONFIG.PLEX_ON_WATCHED

    def _sendhttp(self, host, command):

        username = self.username
        password = self.password

        url_command = urllib.urlencode(command)

        url = host + '/xbmcCmds/xbmcHttp/?' + url_command

        req = urllib2.Request(url)

        if password:
            base64string = base64.encodestring('%s:%s' % (username, password)).replace('\n', '')
            req.add_header("Authorization", "Basic %s" % base64string)

        logger.info('Plex url: %s' % url)

        try:
            handle = urllib2.urlopen(req)
        except Exception as e:
            logger.warn('Error opening Plex url: %s' % e)
            return

        response = handle.read().decode(plexpy.SYS_ENCODING)

        return response

    def notify(self, subject=None, message=None):

        hosts = [x.strip() for x in self.client_hosts.split(',')]

        header = subject
        message = message
        time = "3000" # in ms

        for host in hosts:
            logger.info('Sending notification command to Plex Media Server @ ' + host)
            try:
                notification = header + "," + message + "," + time
                notifycommand = {'command': 'ExecBuiltIn', 'parameter': 'Notification(' + notification + ')'}
                request = self._sendhttp(host, notifycommand)

                if not request:
                    raise Exception

            except:
                logger.warn('Error sending notification request to Plex Media Server')

    def return_config_options(self):
        config_option = [{'label': 'Plex Client Host:Port',
                          'value': self.client_hosts,
                          'name': 'plex_client_host',
                          'description': 'Host running Plex Client (eg. http://192.168.1.100:3000).',
                          'input_type': 'text'
                          },
                         {'label': 'Plex Username',
                          'value': self.username,
                          'name': 'plex_username',
                          'description': 'Username of your Plex client API (blank for none).',
                          'input_type': 'text'
                          },
                         {'label': 'Plex Password',
                          'value': self.password,
                          'name': 'plex_password',
                          'description': 'Password of your Plex client API (blank for none).',
                          'input_type': 'password'
                          }
                         ]

        return config_option

class NMA(object):

    def __init__(self):
        self.api = plexpy.CONFIG.NMA_APIKEY
        self.nma_priority = plexpy.CONFIG.NMA_PRIORITY
        self.on_play = plexpy.CONFIG.NMA_ON_PLAY
        self.on_stop = plexpy.CONFIG.NMA_ON_STOP
        self.on_watched = plexpy.CONFIG.NMA_ON_WATCHED

    def notify(self, subject=None, message=None):
        if not subject or not message:
            return

        title = 'PlexPy'
        api = plexpy.CONFIG.NMA_APIKEY
        nma_priority = plexpy.CONFIG.NMA_PRIORITY

        # logger.debug(u"NMA title: " + title)
        # logger.debug(u"NMA API: " + api)
        # logger.debug(u"NMA Priority: " + str(nma_priority))

        event = subject

        # logger.debug(u"NMA event: " + event)
        # logger.debug(u"NMA message: " + message)

        batch = False

        p = pynma.PyNMA()
        keys = api.split(',')
        p.addkey(keys)

        if len(keys) > 1:
            batch = True

        response = p.push(title, event, message, priority=nma_priority, batch_mode=batch)

        if not response[api][u'code'] == u'200':
            logger.error(u'Could not send notification to NotifyMyAndroid')
            return False
        else:
            return True

    def return_config_options(self):
        config_option = [{'label': 'NotifyMyAndroid API Key',
                          'value': plexpy.CONFIG.NMA_APIKEY,
                          'name': 'nma_apikey',
                          'description': 'Your NotifyMyAndroid API key. Separate multiple api keys with commas.',
                          'input_type': 'text'
                          },
                         {'label': 'Priority',
                          'value': plexpy.CONFIG.NMA_PRIORITY,
                          'name': 'nma_priority',
                          'description': 'Set the priority.',
                          'input_type': 'select',
                          'select_options': {-2: -2, -1: -1, 0: 0, 1: 1, 2: 2}
                          }
                         ]

        return config_option

class PUSHBULLET(object):

    def __init__(self):
        self.apikey = plexpy.CONFIG.PUSHBULLET_APIKEY
        self.deviceid = plexpy.CONFIG.PUSHBULLET_DEVICEID
        self.channel_tag = plexpy.CONFIG.PUSHBULLET_CHANNEL_TAG
        self.on_play = plexpy.CONFIG.PUSHBULLET_ON_PLAY
        self.on_stop = plexpy.CONFIG.PUSHBULLET_ON_STOP
        self.on_watched = plexpy.CONFIG.PUSHBULLET_ON_WATCHED

    def conf(self, options):
        return cherrypy.config['config'].get('PUSHBULLET', options)

    def notify(self, message, subject):
        if not message or not subject:
            return

        http_handler = HTTPSConnection("api.pushbullet.com")

        data = {'type': "note",
                'title': subject.encode("utf-8"),
                'body': message.encode("utf-8")}

        # Can only send to a device or channel, not both.
        if self.deviceid:
            data['device_iden'] = self.deviceid
        elif self.channel_tag:
            data['channel_tag'] = self.channel_tag

        http_handler.request("POST",
                                "/v2/pushes",
                                headers={'Content-type': "application/json",
                                         'Authorization': 'Basic %s' % base64.b64encode(plexpy.CONFIG.PUSHBULLET_APIKEY + ":")},
                                body=json.dumps(data))
        response = http_handler.getresponse()
        request_status = response.status
        # logger.debug(u"PushBullet response status: %r" % request_status)
        # logger.debug(u"PushBullet response headers: %r" % response.getheaders())
        # logger.debug(u"PushBullet response body: %r" % response.read())

        if request_status == 200:
                logger.info(u"PushBullet notifications sent.")
                return True
        elif request_status >= 400 and request_status < 500:
                logger.info(u"PushBullet request failed: %s" % response.reason)
                return False
        else:
                logger.info(u"PushBullet notification failed serverside.")
                return False

    def test(self, apikey, deviceid):

        self.enabled = True
        self.apikey = apikey
        self.deviceid = deviceid

        self.notify('Main Screen Activate', 'Test Message')

    def return_config_options(self):
        config_option = [{'label': 'Pushbullet API Key',
                          'value': self.apikey,
                          'name': 'pushbullet_apikey',
                          'description': 'Your Pushbullet API key.',
                          'input_type': 'text'
                          },
                         {'label': 'Device ID',
                          'value': self.deviceid,
                          'name': 'pushbullet_deviceid',
                          'description': 'A device ID (optional). If set, will override channel tag.',
                          'input_type': 'text'
                          },
                         {'label': 'Channel',
                          'value': self.channel_tag,
                          'name': 'pushbullet_channel_tag',
                          'description': 'A channel tag (optional).',
                          'input_type': 'text'
                          }
                         ]

        return config_option

class PUSHALOT(object):

    def __init__(self):
        self.api_key = plexpy.CONFIG.PUSHALOT_APIKEY
        self.on_play = plexpy.CONFIG.PUSHALOT_ON_PLAY
        self.on_stop = plexpy.CONFIG.PUSHALOT_ON_STOP
        self.on_watched = plexpy.CONFIG.PUSHALOT_ON_WATCHED

    def notify(self, message, event):
        if not message or not event:
            return

        pushalot_authorizationtoken = plexpy.CONFIG.PUSHALOT_APIKEY

        logger.debug(u"Pushalot event: " + event)
        logger.debug(u"Pushalot message: " + message)
        logger.debug(u"Pushalot api: " + pushalot_authorizationtoken)

        http_handler = HTTPSConnection("pushalot.com")

        data = {'AuthorizationToken': pushalot_authorizationtoken,
                'Title': event.encode('utf-8'),
                'Body': message.encode("utf-8")}

        http_handler.request("POST",
                                "/api/sendmessage",
                                headers={'Content-type': "application/x-www-form-urlencoded"},
                                body=urlencode(data))
        response = http_handler.getresponse()
        request_status = response.status

        logger.debug(u"Pushalot response status: %r" % request_status)
        logger.debug(u"Pushalot response headers: %r" % response.getheaders())
        logger.debug(u"Pushalot response body: %r" % response.read())

        if request_status == 200:
                logger.info(u"Pushalot notifications sent.")
                return True
        elif request_status == 410:
                logger.info(u"Pushalot auth failed: %s" % response.reason)
                return False
        else:
                logger.info(u"Pushalot notification failed.")
                return False

    def return_config_options(self):
        config_option = [{'label': 'Pushalot API Key',
                          'value': plexpy.CONFIG.PUSHALOT_APIKEY,
                          'name': 'pushalot_apikey',
                          'description': 'Your Pushalot API key.',
                          'input_type': 'text'
                          }
                         ]

        return config_option

class PUSHOVER(object):

    def __init__(self):
        self.enabled = plexpy.CONFIG.PUSHOVER_ENABLED
        self.keys = plexpy.CONFIG.PUSHOVER_KEYS
        self.priority = plexpy.CONFIG.PUSHOVER_PRIORITY
        self.sound = plexpy.CONFIG.PUSHOVER_SOUND
        self.on_play = plexpy.CONFIG.PUSHOVER_ON_PLAY
        self.on_stop = plexpy.CONFIG.PUSHOVER_ON_STOP
        self.on_watched = plexpy.CONFIG.PUSHOVER_ON_WATCHED

        if plexpy.CONFIG.PUSHOVER_APITOKEN:
            self.application_token = plexpy.CONFIG.PUSHOVER_APITOKEN
        else:
            self.application_token = "aVny3NZFwZaXC642c831b4wd7KUhQS"

    def conf(self, options):
        return cherrypy.config['config'].get('Pushover', options)

    def notify(self, message, event):
        if not message or not event:
            return

        http_handler = HTTPSConnection("api.pushover.net")

        data = {'token': self.application_token,
                'user': plexpy.CONFIG.PUSHOVER_KEYS,
                'title': event.encode("utf-8"),
                'message': message.encode("utf-8"),
                'sound': plexpy.CONFIG.PUSHOVER_SOUND,
                'priority': plexpy.CONFIG.PUSHOVER_PRIORITY}

        http_handler.request("POST",
                             "/1/messages.json",
                             headers={'Content-type': "application/x-www-form-urlencoded"},
                             body=urlencode(data))
        response = http_handler.getresponse()
        request_status = response.status
        # logger.debug(u"Pushover response status: %r" % request_status)
        # logger.debug(u"Pushover response headers: %r" % response.getheaders())
        # logger.debug(u"Pushover response body: %r" % response.read())

        if request_status == 200:
                logger.info(u"Pushover notifications sent.")
                return True
        elif request_status >= 400 and request_status < 500:
                logger.info(u"Pushover request failed: %s" % response.reason)
                return False
        else:
                logger.info(u"Pushover notification failed.")
                return False

    def updateLibrary(self):
        #For uniformity reasons not removed
        return

    def test(self, keys, priority, sound):
        self.enabled = True
        self.keys = keys
        self.priority = priority
        self.sound = sound

        self.notify('Main Screen Activate', 'Test Message')

    def get_sounds(self):
        http_handler = HTTPSConnection("api.pushover.net")
        http_handler.request("GET", "/1/sounds.json?token=" + self.application_token)
        response = http_handler.getresponse()
        request_status = response.status
        
        if request_status == 200:
            data = json.loads(response.read())
            sounds = data.get('sounds', {})
            sounds.update({'': ''})
            return sounds
        elif request_status >= 400 and request_status < 500:
            logger.info(u"Unable to retrieve Pushover notification sounds list: %s" % response.reason)
            return {'': ''}
        else:
            logger.info(u"Unable to retrieve Pushover notification sounds list.")
            return {'': ''}

    def return_config_options(self):
        config_option = [{'label': 'Pushover User or Group Key',
                          'value': self.keys,
                          'name': 'pushover_keys',
                          'description': 'Your Pushover user or group key.',
                          'input_type': 'text'
                          },
                         {'label': 'Priority',
                          'value': self.priority,
                          'name': 'pushover_priority',
                          'description': 'Set the priority.',
                          'input_type': 'select',
                          'select_options': {-2: -2, -1: -1, 0: 0, 1: 1, 2: 2}
                          },
                         {'label': 'Sound',
                          'value': self.sound,
                          'name': 'pushover_sound',
                          'description': 'Set the notification sound. Leave blank for the default sound.',
                          'input_type': 'select',
                          'select_options': self.get_sounds()
                          },
                         {'label': 'Pushover API Token',
                          'value': plexpy.CONFIG.PUSHOVER_APITOKEN,
                          'name': 'pushover_apitoken',
                          'description': 'Your Pushover API token. Leave blank to use PlexPy default.',
                          'input_type': 'text'
                          }
                         ]

        return config_option

class TwitterNotifier(object):

    REQUEST_TOKEN_URL = 'https://api.twitter.com/oauth/request_token'
    ACCESS_TOKEN_URL = 'https://api.twitter.com/oauth/access_token'
    AUTHORIZATION_URL = 'https://api.twitter.com/oauth/authorize'
    SIGNIN_URL = 'https://api.twitter.com/oauth/authenticate'

    def __init__(self):
        self.consumer_key = "2LdJKXHDUwJtjYBsdwJisIOsh"
        self.consumer_secret = "QWbUcZzAIiL4zbDCIhy2EdUkV8yEEav3qMdo5y3FugxCFelWrA"

    def notify(self, subject, message):
        if not subject or not message:
            return
        else:
            self._send_tweet(subject + ': ' + message)

    def test_notify(self):
        return self._send_tweet("This is a test notification from PlexPy at " + helpers.now())

    def _get_authorization(self):

        oauth_consumer = oauth.Consumer(key=self.consumer_key, secret=self.consumer_secret)
        oauth_client = oauth.Client(oauth_consumer)

        logger.info('Requesting temp token from Twitter')

        resp, content = oauth_client.request(self.REQUEST_TOKEN_URL, 'GET')

        if resp['status'] != '200':
            logger.info('Invalid respond from Twitter requesting temp token: %s' % resp['status'])
        else:
            request_token = dict(parse_qsl(content))

            plexpy.CONFIG.TWITTER_USERNAME = request_token['oauth_token']
            plexpy.CONFIG.TWITTER_PASSWORD = request_token['oauth_token_secret']

            return self.AUTHORIZATION_URL + "?oauth_token=" + request_token['oauth_token']

    def _get_credentials(self, key):
        request_token = {}

        request_token['oauth_token'] = plexpy.CONFIG.TWITTER_USERNAME
        request_token['oauth_token_secret'] = plexpy.CONFIG.TWITTER_PASSWORD
        request_token['oauth_callback_confirmed'] = 'true'

        token = oauth.Token(request_token['oauth_token'], request_token['oauth_token_secret'])
        token.set_verifier(key)

        logger.info('Generating and signing request for an access token using key ' + key)

        oauth_consumer = oauth.Consumer(key=self.consumer_key, secret=self.consumer_secret)
        # logger.debug('oauth_consumer: ' + str(oauth_consumer))
        oauth_client = oauth.Client(oauth_consumer, token)
        logger.info('oauth_client: ' + str(oauth_client))
        resp, content = oauth_client.request(self.ACCESS_TOKEN_URL, method='POST', body='oauth_verifier=%s' % key)
        logger.info('resp, content: ' + str(resp) + ',' + str(content))

        access_token = dict(parse_qsl(content))
        logger.info('access_token: ' + str(access_token))

        logger.info('resp[status] = ' + str(resp['status']))
        if resp['status'] != '200':
            logger.info('The request for a token with did not succeed: ' + str(resp['status']), logger.ERROR)
            return False
        else:
            logger.info('Your Twitter Access Token key: %s' % access_token['oauth_token'])
            logger.info('Access Token secret: %s' % access_token['oauth_token_secret'])
            plexpy.CONFIG.TWITTER_USERNAME = access_token['oauth_token']
            plexpy.CONFIG.TWITTER_PASSWORD = access_token['oauth_token_secret']
            return True

    def _send_tweet(self, message=None):
        username = self.consumer_key
        password = self.consumer_secret
        access_token_key = plexpy.CONFIG.TWITTER_USERNAME
        access_token_secret = plexpy.CONFIG.TWITTER_PASSWORD

        logger.info(u"Sending tweet: " + message)

        api = twitter.Api(username, password, access_token_key, access_token_secret)

        try:
            api.PostUpdate(message)
        except Exception as e:
            logger.info(u"Error Sending Tweet: %s" % e)
            return False

        return True

    def return_config_options(self):
        config_option = [{'label': 'Request Authorisation',
                          'value': 'Request Authorisation',
                          'name': 'twitterStep1',
                          'description': 'Step 1: Click Request button above. (Ensure you allow the browser pop-up).',
                          'input_type': 'button'
                          },
                          {'label': 'Authorisation Key',
                           'value': '',
                           'name': 'twitter_key',
                           'description': 'Step 2: Input the authorisation key you received from Step 1.',
                           'input_type': 'text'
                          },
                          {'label': 'Verify Key',
                           'value': 'Verify Key',
                           'name': 'twitterStep2',
                           'description': 'Step 3: Verify the key.',
                           'input_type': 'button'
                          },
                          {'label': 'Test Twitter',
                           'value': 'Test Twitter',
                           'name': 'testTwitter',
                           'description': 'Test if Twitter notifications are working. See logs for troubleshooting.',
                           'input_type': 'button'
                          },
                          {'input_type': 'nosave'
                          }
                         ]

        return config_option

class OSX_NOTIFY(object):

    def __init__(self):
        self.on_play = plexpy.CONFIG.OSX_NOTIFY_ON_PLAY
        self.on_stop = plexpy.CONFIG.OSX_NOTIFY_ON_STOP
        self.on_watched = plexpy.CONFIG.OSX_NOTIFY_ON_WATCHED
        try:
            self.objc = __import__("objc")
            self.AppKit = __import__("AppKit")
        except:
            #logger.error(u"PlexPy Notifier :: Cannot load OSX Notifications agent.")
            pass

    def validate(self):
        try:
            self.objc = __import__("objc")
            self.AppKit = __import__("AppKit")
            return True
        except:
            return False

    def swizzle(self, cls, SEL, func):
        old_IMP = cls.instanceMethodForSelector_(SEL)

        def wrapper(self, *args, **kwargs):
            return func(self, old_IMP, *args, **kwargs)
        new_IMP = self.objc.selector(wrapper, selector=old_IMP.selector,
            signature=old_IMP.signature)
        self.objc.classAddMethod(cls, SEL, new_IMP)

    def notify(self, title, subtitle=None, text=None, sound=True, image=None):

        try:
            self.swizzle(self.objc.lookUpClass('NSBundle'),
                b'bundleIdentifier',
                self.swizzled_bundleIdentifier)

            NSUserNotification = self.objc.lookUpClass('NSUserNotification')
            NSUserNotificationCenter = self.objc.lookUpClass('NSUserNotificationCenter')
            NSAutoreleasePool = self.objc.lookUpClass('NSAutoreleasePool')

            if not NSUserNotification or not NSUserNotificationCenter:
                return False

            pool = NSAutoreleasePool.alloc().init()

            notification = NSUserNotification.alloc().init()
            notification.setTitle_(title)
            if subtitle:
                notification.setSubtitle_(subtitle)
            if text:
                notification.setInformativeText_(text)
            if sound:
                notification.setSoundName_("NSUserNotificationDefaultSoundName")
            if image:
                source_img = self.AppKit.NSImage.alloc().initByReferencingFile_(image)
                notification.setContentImage_(source_img)
                #notification.set_identityImage_(source_img)
            notification.setHasActionButton_(False)

            notification_center = NSUserNotificationCenter.defaultUserNotificationCenter()
            notification_center.deliverNotification_(notification)
            logger.info(u"OSX Notify notifications sent.")

            del pool
            return True

        except Exception as e:
            logger.warn('Error sending OS X Notification: %s' % e)
            return False

    def swizzled_bundleIdentifier(self, original, swizzled):
        return 'ade.plexpy.osxnotify'

    def return_config_options(self):
        config_option = [{'label': 'Register Notify App',
                          'value': plexpy.CONFIG.OSX_NOTIFY_APP,
                          'name': 'osx_notify_app',
                          'description': 'Enter the path/application name to be registered with the '
                                         'Notification Center, default is /Applications/PlexPy.',
                          'input_type': 'text'
                          }
                         ]

        return config_option

class BOXCAR(object):

    def __init__(self):
        self.url = 'https://new.boxcar.io/api/notifications'
        self.token = plexpy.CONFIG.BOXCAR_TOKEN
        self.sound = plexpy.CONFIG.BOXCAR_SOUND
        self.on_play = plexpy.CONFIG.BOXCAR_ON_PLAY
        self.on_stop = plexpy.CONFIG.BOXCAR_ON_STOP
        self.on_watched = plexpy.CONFIG.BOXCAR_ON_WATCHED

    def notify(self, title, message):
        if not title or not message:
            return

        try:
            data = urllib.urlencode({
                'user_credentials': plexpy.CONFIG.BOXCAR_TOKEN,
                'notification[title]': title.encode('utf-8'),
                'notification[long_message]': message.encode('utf-8'),
                'notification[sound]': plexpy.CONFIG.BOXCAR_SOUND
                })

            req = urllib2.Request(self.url)
            handle = urllib2.urlopen(req, data)
            handle.close()
            return True

        except urllib2.URLError as e:
            logger.warn('Error sending Boxcar2 Notification: %s' % e)
            return False

    def return_config_options(self):
        config_option = [{'label': 'Boxcar Access Token',
                          'value': plexpy.CONFIG.BOXCAR_TOKEN,
                          'name': 'boxcar_token',
                          'description': 'Your Boxcar access token.',
                          'input_type': 'text'
                          },
                         {'label': 'Sound',
                          'value': self.sound,
                          'name': 'boxcar_sound',
                          'description': 'Set the notification sound. Leave blank for the default sound.',
                          'input_type': 'select',
                          'select_options': {'': '',
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
                          }
                         ]

        return config_option

class Email(object):

    def __init__(self):
        self.on_play = plexpy.CONFIG.EMAIL_ON_PLAY
        self.on_stop = plexpy.CONFIG.EMAIL_ON_STOP
        self.on_watched = plexpy.CONFIG.EMAIL_ON_WATCHED

    def notify(self, subject, message):
        if not subject or not message:
            return

        message = MIMEText(message, 'plain', "utf-8")
        message['Subject'] = subject
        message['From'] = email.utils.formataddr(('PlexPy', plexpy.CONFIG.EMAIL_FROM))
        message['To'] = plexpy.CONFIG.EMAIL_TO

        try:
            mailserver = smtplib.SMTP(plexpy.CONFIG.EMAIL_SMTP_SERVER, plexpy.CONFIG.EMAIL_SMTP_PORT)

            if (plexpy.CONFIG.EMAIL_TLS):
                mailserver.starttls()

            mailserver.ehlo()

            if plexpy.CONFIG.EMAIL_SMTP_USER:
                mailserver.login(plexpy.CONFIG.EMAIL_SMTP_USER, plexpy.CONFIG.EMAIL_SMTP_PASSWORD)

            mailserver.sendmail(plexpy.CONFIG.EMAIL_FROM, plexpy.CONFIG.EMAIL_TO, message.as_string())
            mailserver.quit()

            logger.info(u"Email notifications sent.")
            return True

        except Exception, e:
            logger.warn('Error sending Email: %s' % e)
            return False

    def return_config_options(self):
        config_option = [{'label': 'From',
                          'value': plexpy.CONFIG.EMAIL_FROM,
                          'name': 'email_from',
                          'description': 'Who should the sender be.',
                          'input_type': 'text'
                          },
                         {'label': 'To',
                          'value': plexpy.CONFIG.EMAIL_TO,
                          'name': 'email_to',
                          'description': 'Who should the recipient be.',
                          'input_type': 'text'
                          },
                         {'label': 'SMTP Server',
                          'value': plexpy.CONFIG.EMAIL_SMTP_SERVER,
                          'name': 'email_smtp_server',
                          'description': 'Host for the SMTP server.',
                          'input_type': 'text'
                          },
                         {'label': 'SMTP Port',
                          'value': plexpy.CONFIG.EMAIL_SMTP_PORT,
                          'name': 'email_smtp_port',
                          'description': 'Port for the SMTP server.',
                          'input_type': 'number'
                          },
                         {'label': 'SMTP User',
                          'value': plexpy.CONFIG.EMAIL_SMTP_USER,
                          'name': 'email_smtp_user',
                          'description': 'User for the SMTP server.',
                          'input_type': 'text'
                          },
                         {'label': 'SMTP Password',
                          'value': plexpy.CONFIG.EMAIL_SMTP_PASSWORD,
                          'name': 'email_smtp_password',
                          'description': 'Password for the SMTP server.',
                          'input_type': 'password'
                          },
                         {'label': 'TLS',
                          'value': plexpy.CONFIG.EMAIL_TLS,
                          'name': 'email_tls',
                          'description': 'Does the server use encryption.',
                          'input_type': 'checkbox'
                          }
                         ]

        return config_option


class IFTTT(object):

    def __init__(self):
        self.apikey = plexpy.CONFIG.IFTTT_KEY
        self.event = plexpy.CONFIG.IFTTT_EVENT

    def notify(self, message, subject):
        if not message or not subject:
            return

        http_handler = HTTPSConnection("maker.ifttt.com")

        data = {'value1': subject.encode("utf-8"),
                'value2': message.encode("utf-8")}

        # logger.debug("Ifttt SENDING: %s" % json.dumps(data))

        http_handler.request("POST",
                             "/trigger/%s/with/key/%s" % (self.event, self.apikey),
                             headers={'Content-type': "application/json"},
                             body=json.dumps(data))
        response = http_handler.getresponse()
        request_status = response.status
        # logger.debug(u"Ifttt response status: %r" % request_status)
        # logger.debug(u"Ifttt response headers: %r" % response.getheaders())
        # logger.debug(u"Ifttt response body: %r" % response.read())

        if request_status == 200:
                logger.info(u"Ifttt notifications sent.")
                return True
        elif request_status >= 400 and request_status < 500:
                logger.info(u"Ifttt request failed: %s" % response.reason)
                return False
        else:
                logger.info(u"Ifttt notification failed serverside.")
                return False

    def test(self):
        return self.notify('PlexPy', 'Test Message')

    def return_config_options(self):
        config_option = [{'label': 'Ifttt Maker Channel Key',
                          'value': self.apikey,
                          'name': 'ifttt_key',
                          'description': 'Your Ifttt  key. You can get a key from <a href="https://ifttt.com/maker" target="_blank">here</a>.',
                          'input_type': 'text'
                          },
                         {'label': 'Ifttt Event',
                          'value': self.event,
                          'name': 'ifttt_event',
                          'description': 'The Ifttt maker event to fire. The notification subject and body will be sent'
                                         ' as value1 and value2 respectively.',
                          'input_type': 'text'
                          },
                         {'label': 'Test Event',
                           'value': 'Test Event',
                           'name': 'testIFTTT',
                           'description': 'Test if IFTTT notifications are working. See logs for troubleshooting.',
                           'input_type': 'button'
                          }
                         ]

        return config_option

class TELEGRAM(object):

    def __init__(self):
        self.enabled = plexpy.CONFIG.TELEGRAM_ENABLED
        self.bot_token = plexpy.CONFIG.TELEGRAM_BOT_TOKEN
        self.chat_id = plexpy.CONFIG.TELEGRAM_CHAT_ID

    def conf(self, options):
        return cherrypy.config['config'].get('Telegram', options)

    def notify(self, message, event):
        if not message or not event:
            return

        http_handler = HTTPSConnection("api.telegram.org")

        data = {'chat_id': self.chat_id,
                'text': event.encode('utf-8') + ': ' + message.encode("utf-8")}

        http_handler.request("POST",
                                "/bot%s/%s" % (self.bot_token, "sendMessage"),
                                headers={'Content-type': "application/x-www-form-urlencoded"},
                                body=urlencode(data))

        response = http_handler.getresponse()
        request_status = response.status

        if request_status == 200:
                logger.info(u"Telegram notifications sent.")
                return True
        elif request_status >= 400 and request_status < 500:
                logger.info(u"Telegram request failed: %s" % response.reason)
                return False
        else:
                logger.info(u"Telegram notification failed serverside.")
                return False

    def updateLibrary(self):
        #For uniformity reasons not removed
        return

    def test(self, bot_token, chat_id):
        self.enabled = True
        self.bot_token = bot_token
        self.chat_id = chat_id

        self.notify('Main Screen Activate', 'Test Message')

    def return_config_options(self):
        config_option = [{'label': 'Telegram Bot Token',
                          'value': self.bot_token,
                          'name': 'telegram_bot_token',
                          'description': 'Your Telegram bot token. Contact <a href="http://telegram.me/BotFather" target="_blank">@BotFather</a> on Telegram to get one.',
                          'input_type': 'text'
                          },
                         {'label': 'Telegram Chat ID',
                          'value': self.chat_id,
                          'name': 'telegram_chat_id',
                          'description': 'Your Telegram Chat ID or Group ID. Contact <a href="http://telegram.me/myidbot" target="_blank">@myidbot</a> on Telegram to get an ID.',
                          'input_type': 'text'
                          }
                         ]

        return config_option
