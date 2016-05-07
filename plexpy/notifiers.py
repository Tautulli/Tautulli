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

from urlparse import urlparse
import base64
import bleach
import json
import cherrypy
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import email.utils
from httplib import HTTPSConnection
import os
import re
import requests
import shlex
import smtplib
import subprocess
import time

from urllib import urlencode
import urllib
import urllib2
from urlparse import parse_qsl

from pynma import pynma
import gntp.notifier
import oauth2 as oauth
import pythontwitter as twitter
import pythonfacebook as facebook

import plexpy
from plexpy import logger, helpers, request, database
from plexpy.helpers import checked

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
             "Telegram": 13,
             "Slack": 14,
             "Scripts": 15,
             "Facebook": 16,
             "Browser": 17}


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
               'on_intdown': plexpy.CONFIG.GROWL_ON_INTDOWN,
               'on_extup': plexpy.CONFIG.GROWL_ON_EXTUP,
               'on_intup': plexpy.CONFIG.GROWL_ON_INTUP,
               'on_pmsupdate': plexpy.CONFIG.GROWL_ON_PMSUPDATE
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
               'on_intdown': plexpy.CONFIG.PROWL_ON_INTDOWN,
               'on_extup': plexpy.CONFIG.PROWL_ON_EXTUP,
               'on_intup': plexpy.CONFIG.PROWL_ON_INTUP,
               'on_pmsupdate': plexpy.CONFIG.PROWL_ON_PMSUPDATE
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
               'on_intdown': plexpy.CONFIG.XBMC_ON_INTDOWN,
               'on_extup': plexpy.CONFIG.XBMC_ON_EXTUP,
               'on_intup': plexpy.CONFIG.XBMC_ON_INTUP,
               'on_pmsupdate': plexpy.CONFIG.XBMC_ON_PMSUPDATE
               },
              {'name': 'Plex Home Theater',
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
               'on_intdown': plexpy.CONFIG.PLEX_ON_INTDOWN,
               'on_extup': plexpy.CONFIG.PLEX_ON_EXTUP,
               'on_intup': plexpy.CONFIG.PLEX_ON_INTUP,
               'on_pmsupdate': plexpy.CONFIG.PLEX_ON_PMSUPDATE
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
               'on_intdown': plexpy.CONFIG.NMA_ON_INTDOWN,
               'on_extup': plexpy.CONFIG.NMA_ON_EXTUP,
               'on_intup': plexpy.CONFIG.NMA_ON_INTUP,
               'on_pmsupdate': plexpy.CONFIG.NMA_ON_PMSUPDATE
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
               'on_intdown': plexpy.CONFIG.PUSHALOT_ON_INTDOWN,
               'on_extup': plexpy.CONFIG.PUSHALOT_ON_EXTUP,
               'on_intup': plexpy.CONFIG.PUSHALOT_ON_INTUP,
               'on_pmsupdate': plexpy.CONFIG.PUSHALOT_ON_PMSUPDATE
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
               'on_intdown': plexpy.CONFIG.PUSHBULLET_ON_INTDOWN,
               'on_extup': plexpy.CONFIG.PUSHBULLET_ON_EXTUP,
               'on_intup': plexpy.CONFIG.PUSHBULLET_ON_INTUP,
               'on_pmsupdate': plexpy.CONFIG.PUSHBULLET_ON_PMSUPDATE
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
               'on_intdown': plexpy.CONFIG.PUSHOVER_ON_INTDOWN,
               'on_extup': plexpy.CONFIG.PUSHOVER_ON_EXTUP,
               'on_intup': plexpy.CONFIG.PUSHOVER_ON_INTUP,
               'on_pmsupdate': plexpy.CONFIG.PUSHOVER_ON_PMSUPDATE
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
               'on_intdown': plexpy.CONFIG.BOXCAR_ON_INTDOWN,
               'on_extup': plexpy.CONFIG.BOXCAR_ON_EXTUP,
               'on_intup': plexpy.CONFIG.BOXCAR_ON_INTUP,
               'on_pmsupdate': plexpy.CONFIG.BOXCAR_ON_PMSUPDATE
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
               'on_intdown': plexpy.CONFIG.EMAIL_ON_INTDOWN,
               'on_extup': plexpy.CONFIG.EMAIL_ON_EXTUP,
               'on_intup': plexpy.CONFIG.EMAIL_ON_INTUP,
               'on_pmsupdate': plexpy.CONFIG.EMAIL_ON_PMSUPDATE
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
               'on_intdown': plexpy.CONFIG.TWITTER_ON_INTDOWN,
               'on_extup': plexpy.CONFIG.TWITTER_ON_EXTUP,
               'on_intup': plexpy.CONFIG.TWITTER_ON_INTUP,
               'on_pmsupdate': plexpy.CONFIG.TWITTER_ON_PMSUPDATE
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
               'on_intdown': plexpy.CONFIG.IFTTT_ON_INTDOWN,
               'on_extup': plexpy.CONFIG.IFTTT_ON_EXTUP,
               'on_intup': plexpy.CONFIG.IFTTT_ON_INTUP,
               'on_pmsupdate': plexpy.CONFIG.IFTTT_ON_PMSUPDATE
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
               'on_intdown': plexpy.CONFIG.TELEGRAM_ON_INTDOWN,
               'on_extup': plexpy.CONFIG.TELEGRAM_ON_EXTUP,
               'on_intup': plexpy.CONFIG.TELEGRAM_ON_INTUP,
               'on_pmsupdate': plexpy.CONFIG.TELEGRAM_ON_PMSUPDATE
               },
              {'name': 'Slack',
               'id': AGENT_IDS['Slack'],
               'config_prefix': 'slack',
               'has_config': True,
               'state': checked(plexpy.CONFIG.SLACK_ENABLED),
               'on_play': plexpy.CONFIG.SLACK_ON_PLAY,
               'on_stop': plexpy.CONFIG.SLACK_ON_STOP,
               'on_resume': plexpy.CONFIG.SLACK_ON_RESUME,
               'on_pause': plexpy.CONFIG.SLACK_ON_PAUSE,
               'on_buffer': plexpy.CONFIG.SLACK_ON_BUFFER,
               'on_watched': plexpy.CONFIG.SLACK_ON_WATCHED,
               'on_created': plexpy.CONFIG.SLACK_ON_CREATED,
               'on_extdown': plexpy.CONFIG.SLACK_ON_EXTDOWN,
               'on_intdown': plexpy.CONFIG.SLACK_ON_INTDOWN,
               'on_extup': plexpy.CONFIG.SLACK_ON_EXTUP,
               'on_intup': plexpy.CONFIG.SLACK_ON_INTUP,
               'on_pmsupdate': plexpy.CONFIG.SLACK_ON_PMSUPDATE
               },
              {'name': 'Scripts',
               'id': AGENT_IDS['Scripts'],
               'config_prefix': 'scripts',
               'has_config': True,
               'state': checked(plexpy.CONFIG.SCRIPTS_ENABLED),
               'on_play': plexpy.CONFIG.SCRIPTS_ON_PLAY,
               'on_stop': plexpy.CONFIG.SCRIPTS_ON_STOP,
               'on_pause': plexpy.CONFIG.SCRIPTS_ON_PAUSE,
               'on_resume': plexpy.CONFIG.SCRIPTS_ON_RESUME,
               'on_buffer': plexpy.CONFIG.SCRIPTS_ON_BUFFER,
               'on_watched': plexpy.CONFIG.SCRIPTS_ON_WATCHED,
               'on_created': plexpy.CONFIG.SCRIPTS_ON_CREATED,
               'on_extdown': plexpy.CONFIG.SCRIPTS_ON_EXTDOWN,
               'on_extup': plexpy.CONFIG.SCRIPTS_ON_EXTUP,
               'on_intdown': plexpy.CONFIG.SCRIPTS_ON_INTDOWN,
               'on_intup': plexpy.CONFIG.SCRIPTS_ON_INTUP,
               'on_pmsupdate': plexpy.CONFIG.SCRIPTS_ON_PMSUPDATE
              },
              {'name': 'Facebook',
               'id': AGENT_IDS['Facebook'],
               'config_prefix': 'facebook',
               'has_config': True,
               'state': checked(plexpy.CONFIG.FACEBOOK_ENABLED),
               'on_play': plexpy.CONFIG.FACEBOOK_ON_PLAY,
               'on_stop': plexpy.CONFIG.FACEBOOK_ON_STOP,
               'on_pause': plexpy.CONFIG.FACEBOOK_ON_PAUSE,
               'on_resume': plexpy.CONFIG.FACEBOOK_ON_RESUME,
               'on_buffer': plexpy.CONFIG.FACEBOOK_ON_BUFFER,
               'on_watched': plexpy.CONFIG.FACEBOOK_ON_WATCHED,
               'on_created': plexpy.CONFIG.FACEBOOK_ON_CREATED,
               'on_extdown': plexpy.CONFIG.FACEBOOK_ON_EXTDOWN,
               'on_intdown': plexpy.CONFIG.FACEBOOK_ON_INTDOWN,
               'on_extup': plexpy.CONFIG.FACEBOOK_ON_EXTUP,
               'on_intup': plexpy.CONFIG.FACEBOOK_ON_INTUP,
               'on_pmsupdate': plexpy.CONFIG.FACEBOOK_ON_PMSUPDATE
              },
              {'name': 'Browser',
               'id': AGENT_IDS['Browser'],
               'config_prefix': 'browser',
               'has_config': True,
               'state': checked(plexpy.CONFIG.BROWSER_ENABLED),
               'on_play': plexpy.CONFIG.BROWSER_ON_PLAY,
               'on_stop': plexpy.CONFIG.BROWSER_ON_STOP,
               'on_pause': plexpy.CONFIG.BROWSER_ON_PAUSE,
               'on_resume': plexpy.CONFIG.BROWSER_ON_RESUME,
               'on_buffer': plexpy.CONFIG.BROWSER_ON_BUFFER,
               'on_watched': plexpy.CONFIG.BROWSER_ON_WATCHED,
               'on_created': plexpy.CONFIG.BROWSER_ON_CREATED,
               'on_extdown': plexpy.CONFIG.BROWSER_ON_EXTDOWN,
               'on_intdown': plexpy.CONFIG.BROWSER_ON_INTDOWN,
               'on_extup': plexpy.CONFIG.BROWSER_ON_EXTUP,
               'on_intup': plexpy.CONFIG.BROWSER_ON_INTUP,
               'on_pmsupdate': plexpy.CONFIG.BROWSER_ON_PMSUPDATE
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
                       'on_intdown': plexpy.CONFIG.OSX_NOTIFY_ON_INTDOWN,
                       'on_extup': plexpy.CONFIG.OSX_NOTIFY_ON_EXTUP,
                       'on_intup': plexpy.CONFIG.OSX_NOTIFY_ON_INTUP,
                       'on_pmsupdate': plexpy.CONFIG.OSX_NOTIFY_ON_PMSUPDATE
                       })

    return agents


def get_notification_agent_config(agent_id):
    if str(agent_id).isdigit():
        agent_id = int(agent_id)

        if agent_id == 0:
            growl = GROWL()
            return growl.return_config_options()
        elif agent_id == 1:
            prowl = PROWL()
            return prowl.return_config_options()
        elif agent_id == 2:
            xbmc = XBMC()
            return xbmc.return_config_options()
        elif agent_id == 3:
            plex = Plex()
            return plex.return_config_options()
        elif agent_id == 4:
            nma = NMA()
            return nma.return_config_options()
        elif agent_id == 5:
            pushalot = PUSHALOT()
            return pushalot.return_config_options()
        elif agent_id == 6:
            pushbullet = PUSHBULLET()
            return pushbullet.return_config_options()
        elif agent_id == 7:
            pushover = PUSHOVER()
            return pushover.return_config_options()
        elif agent_id == 8:
            osx_notify = OSX_NOTIFY()
            return osx_notify.return_config_options()
        elif agent_id == 9:
            boxcar = BOXCAR()
            return boxcar.return_config_options()
        elif agent_id == 10:
            email = Email()
            return email.return_config_options()
        elif agent_id == 11:
            tweet = TwitterNotifier()
            return tweet.return_config_options()
        elif agent_id == 12:
            iftttClient = IFTTT()
            return iftttClient.return_config_options()
        elif agent_id == 13:
            telegramClient = TELEGRAM()
            return telegramClient.return_config_options()
        elif agent_id == 14:
            slackClient = SLACK()
            return slackClient.return_config_options()
        elif agent_id == 15:
            script = Scripts()
            return script.return_config_options()
        elif agent_id == 16:
            facebook = FacebookNotifier()
            return facebook.return_config_options()
        elif agent_id == 17:
            browser = Browser()
            return browser.return_config_options()
        else:
            return []
    else:
        return []


def send_notification(agent_id, subject, body, notify_action, **kwargs):
    if str(agent_id).isdigit():
        agent_id = int(agent_id)

        if agent_id == 0:
            growl = GROWL()
            return growl.notify(message=body, event=subject)
        elif agent_id == 1:
            prowl = PROWL()
            return prowl.notify(message=body, event=subject)
        elif agent_id == 2:
            xbmc = XBMC()
            return xbmc.notify(subject=subject, message=body)
        elif agent_id == 3:
            plex = Plex()
            return plex.notify(subject=subject, message=body)
        elif agent_id == 4:
            nma = NMA()
            return nma.notify(subject=subject, message=body)
        elif agent_id == 5:
            pushalot = PUSHALOT()
            return pushalot.notify(message=body, event=subject)
        elif agent_id == 6:
            pushbullet = PUSHBULLET()
            return pushbullet.notify(message=body, subject=subject)
        elif agent_id == 7:
            pushover = PUSHOVER()
            return pushover.notify(message=body, event=subject)
        elif agent_id == 8:
            osx_notify = OSX_NOTIFY()
            return osx_notify.notify(title=subject, text=body)
        elif agent_id == 9:
            boxcar = BOXCAR()
            return boxcar.notify(title=subject, message=body)
        elif agent_id == 10:
            email = Email()
            return email.notify(subject=subject, message=body)
        elif agent_id == 11:
            tweet = TwitterNotifier()
            return tweet.notify(subject=subject, message=body)
        elif agent_id == 12:
            iftttClient = IFTTT()
            return iftttClient.notify(subject=subject, message=body, action=notify_action)
        elif agent_id == 13:
            telegramClient = TELEGRAM()
            return telegramClient.notify(message=body, event=subject, **kwargs)
        elif agent_id == 14:
            slackClient = SLACK()
            return slackClient.notify(message=body, event=subject)
        elif agent_id == 15:
            scripts = Scripts()
            return scripts.notify(message=body, subject=subject, notify_action=notify_action, **kwargs)
        elif agent_id == 16:
            facebook = FacebookNotifier()
            return facebook.notify(subject=subject, message=body, **kwargs)
        elif agent_id == 17:
            browser = Browser()
            return browser.notify(subject=subject, message=body)
        else:
            logger.debug(u"PlexPy Notifiers :: Unknown agent id received.")
    else:
        logger.debug(u"PlexPy Notifiers :: Notification requested but no agent id received.")


class GROWL(object):
    """
    Growl notifications, for OS X.
    """

    def __init__(self):
        self.enabled = plexpy.CONFIG.GROWL_ENABLED
        self.host = plexpy.CONFIG.GROWL_HOST
        self.password = plexpy.CONFIG.GROWL_PASSWORD

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
            logger.warn(u"PlexPy Notifiers :: Growl notification failed: network error")
            return False
        except gntp.notifier.errors.AuthError:
            logger.warn(u"PlexPy Notifiers :: Growl notification failed: authentication error")
            return False

        # Fix message
        message = message.encode(plexpy.SYS_ENCODING, "replace")

        # Send it, including an image
        image_file = os.path.join(str(plexpy.PROG_DIR),
            "data/interfaces/default/images/favicon.png")

        with open(image_file, 'rb') as f:
            image = f.read()

        try:
            growl.notify(
                noteType='New Event',
                title=event,
                description=message,
                icon=image
            )
            logger.info(u"PlexPy Notifiers :: Growl notification sent.")
            return True
        except gntp.notifier.errors.NetworkError:
            logger.warn(u"PlexPy Notifiers :: Growl notification failed: network error")
            return False


    def updateLibrary(self):
        # For uniformity reasons not removed
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

    def conf(self, options):
        return cherrypy.config['config'].get('Prowl', options)

    def notify(self, message, event):
        if not message or not event:
            return

        http_handler = HTTPSConnection("api.prowlapp.com")

        data = {'apikey': plexpy.CONFIG.PROWL_KEYS,
                'application': 'PlexPy',
                'event': event.encode("utf-8"),
                'description': message.encode("utf-8"),
                'priority': plexpy.CONFIG.PROWL_PRIORITY}

        http_handler.request("POST",
                             "/publicapi/add",
                             headers={'Content-type': "application/x-www-form-urlencoded"},
                             body=urlencode(data))

        response = http_handler.getresponse()
        request_status = response.status

        if request_status == 200:
            logger.info(u"PlexPy Notifiers :: Prowl notification sent.")
            return True
        elif request_status == 401:
            logger.warn(u"PlexPy Notifiers :: Prowl notification failed: [%s] %s" % (request_status, response.reason))
            return False
        else:
            logger.warn(u"PlexPy Notifiers :: Prowl notification failed.")
            return False

    def updateLibrary(self):
        # For uniformity reasons not removed
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
        time = "3000"  # in ms

        for host in hosts:
            logger.info(u"PlexPy Notifiers :: Sending notification command to XMBC @ " + host)
            try:
                version = self._sendjson(host, 'Application.GetProperties', {'properties': ['version']})['version']['major']

                if version < 12:  # Eden
                    notification = header + "," + message + "," + time
                    notifycommand = {'command': 'ExecBuiltIn', 'parameter': 'Notification(' + notification + ')'}
                    request = self._sendhttp(host, notifycommand)

                else:  # Frodo
                    params = {'title': header, 'message': message, 'displaytime': int(time)}
                    request = self._sendjson(host, 'GUI.ShowNotification', params)

                if not request:
                    raise Exception
                else:
                    logger.info(u"PlexPy Notifiers :: XBMC notification sent.")
                    return True

            except Exception:
                logger.warn(u"PlexPy Notifiers :: XBMC notification filed.")
                return False

    def return_config_options(self):
        config_option = [{'label': 'XBMC Host:Port',
                          'value': self.hosts,
                          'name': 'xbmc_host',
                          'description': 'Host running XBMC (e.g. http://localhost:8080). Separate multiple hosts with commas (,).',
                          'input_type': 'text'
                          },
                         {'label': 'XBMC Username',
                          'value': self.username,
                          'name': 'xbmc_username',
                          'description': 'Username of your XBMC client API (blank for none).',
                          'input_type': 'text'
                          },
                         {'label': 'XBMC Password',
                          'value': self.password,
                          'name': 'xbmc_password',
                          'description': 'Password of your XBMC client API (blank for none).',
                          'input_type': 'password'
                          }
                         ]

        return config_option


class Plex(object):
    def __init__(self):
        self.client_hosts = plexpy.CONFIG.PLEX_CLIENT_HOST
        self.username = plexpy.CONFIG.PLEX_USERNAME
        self.password = plexpy.CONFIG.PLEX_PASSWORD

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

        hosts = [x.strip() for x in self.client_hosts.split(',')]

        header = subject
        message = message
        time = "3000"  # in ms

        for host in hosts:
            logger.info(u"PlexPy Notifiers :: Sending notification command to Plex Home Theater @ " + host)
            try:
                version = self._sendjson(host, 'Application.GetProperties', {'properties': ['version']})['version']['major']

                if version < 12:  # Eden
                    notification = header + "," + message + "," + time
                    notifycommand = {'command': 'ExecBuiltIn', 'parameter': 'Notification(' + notification + ')'}
                    request = self._sendhttp(host, notifycommand)

                else:  # Frodo
                    params = {'title': header, 'message': message, 'displaytime': int(time)}
                    request = self._sendjson(host, 'GUI.ShowNotification', params)

                if not request:
                    raise Exception
                else:
                    logger.info(u"PlexPy Notifiers :: Plex Home Theater notification sent.")
                    return True

            except Exception:
                logger.warn(u"PlexPy Notifiers :: Plex Home Theater notification filed.")
                return False

    def return_config_options(self):
        config_option = [{'label': 'Plex Home Theater Host:Port',
                          'value': self.client_hosts,
                          'name': 'plex_client_host',
                          'description': 'Host running Plex Home Theater (eg. http://localhost:3005). Separate multiple hosts with commas (,).',
                          'input_type': 'text'
                          },
                         {'label': 'Plex Home Theater Username',
                          'value': self.username,
                          'name': 'plex_username',
                          'description': 'Username of your Plex Home Theater client API (blank for none).',
                          'input_type': 'text'
                          },
                         {'label': 'Plex Home Theater Password',
                          'value': self.password,
                          'name': 'plex_password',
                          'description': 'Password of your Plex Home Theater client API (blank for none).',
                          'input_type': 'password'
                          }
                         ]

        return config_option


class NMA(object):

    def __init__(self):
        self.api = plexpy.CONFIG.NMA_APIKEY
        self.nma_priority = plexpy.CONFIG.NMA_PRIORITY

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
            logger.warn(u"PlexPy Notifiers :: NotifyMyAndroid notification failed.")
            return False
        else:
            logger.info(u"PlexPy Notifiers :: NotifyMyAndroid notification sent.")
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
            logger.info(u"PlexPy Notifiers :: PushBullet notification sent.")
            return True
        elif request_status >= 400 and request_status < 500:
            logger.warn(u"PlexPy Notifiers :: PushBullet notification failed: [%s] %s" % (request_status, response.reason))
            return False
        else:
            logger.warn(u"PlexPy Notifiers :: PushBullet notification failed.")
            return False

    def test(self, apikey, deviceid):

        self.enabled = True
        self.apikey = apikey
        self.deviceid = deviceid

        self.notify('Main Screen Activate', 'Test Message')

    def get_devices(self):
        if plexpy.CONFIG.PUSHBULLET_APIKEY:
            http_handler = HTTPSConnection("api.pushbullet.com")
            http_handler.request("GET", "/v2/devices",
                                 headers={'Content-type': "application/json",
                                 'Authorization': 'Basic %s' % base64.b64encode(plexpy.CONFIG.PUSHBULLET_APIKEY + ":")})

            response = http_handler.getresponse()
            request_status = response.status

            if request_status == 200:
                data = json.loads(response.read())
                devices = data.get('devices', [])
                devices = {d['iden']: d['nickname'] for d in devices if d['active']}
                devices.update({'': ''})
                return devices
            elif request_status >= 400 and request_status < 500:
                logger.warn(u"PlexPy Notifiers :: Unable to retrieve Pushbullet devices list: %s" % response.reason)
                return {'': ''}
            else:
                logger.warn(u"PlexPy Notifiers :: Unable to retrieve Pushbullet devices list.")
                return {'': ''}

        else:
            return {'': ''}

    def return_config_options(self):
        config_option = [{'label': 'Pushbullet API Key',
                          'value': self.apikey,
                          'name': 'pushbullet_apikey',
                          'description': 'Your Pushbullet API key.',
                          'input_type': 'text'
                          },
                         {'label': 'Device',
                          'value': self.deviceid,
                          'name': 'pushbullet_deviceid',
                          'description': 'Set your Pushbullet device. If set, will override channel tag. ' \
                              'Leave blank to notify on all devices.',
                          'input_type': 'select',
                          'select_options': self.get_devices()
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

    def notify(self, message, event):
        if not message or not event:
            return

        pushalot_authorizationtoken = plexpy.CONFIG.PUSHALOT_APIKEY

        # logger.debug(u"Pushalot event: " + event)
        # logger.debug(u"Pushalot message: " + message)
        # logger.debug(u"Pushalot api: " + pushalot_authorizationtoken)

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

        # logger.debug(u"Pushalot response status: %r" % request_status)
        # logger.debug(u"Pushalot response headers: %r" % response.getheaders())
        # logger.debug(u"Pushalot response body: %r" % response.read())

        if request_status == 200:
            logger.info(u"PlexPy Notifiers :: Pushalot notification sent.")
            return True
        elif request_status == 410:
            logger.warn(u"PlexPy Notifiers :: Pushalot notification failed: [%s] %s" % (request_status, response.reason))
            return False
        else:
            logger.warn(u"PlexPy Notifiers :: Pushalot notification failed.")
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
        self.application_token = plexpy.CONFIG.PUSHOVER_APITOKEN
        self.keys = plexpy.CONFIG.PUSHOVER_KEYS
        self.priority = plexpy.CONFIG.PUSHOVER_PRIORITY
        self.sound = plexpy.CONFIG.PUSHOVER_SOUND
        self.html_support = plexpy.CONFIG.PUSHOVER_HTML_SUPPORT

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
                'html': plexpy.CONFIG.PUSHOVER_HTML_SUPPORT,
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
            logger.info(u"PlexPy Notifiers :: Pushover notification sent.")
            return True
        elif request_status >= 400 and request_status < 500:
            logger.warn(u"PlexPy Notifiers :: Pushover notification failed: [%s] %s" % (request_status, response.reason))
            return False
        else:
            logger.warn(u"PlexPy Notifiers :: Pushover notification failed.")
            return False

    def updateLibrary(self):
        # For uniformity reasons not removed
        return

    def test(self, keys, priority, sound, html_support):
        self.enabled = True
        self.keys = keys
        self.priority = priority
        self.sound = sound
        self.html_support = html_support

        self.notify('Main Screen Activate', 'Test Message')

    def get_sounds(self):
        if plexpy.CONFIG.PUSHOVER_APITOKEN:
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
                logger.warn(u"PlexPy Notifiers :: Unable to retrieve Pushover notification sounds list: %s" % response.reason)
                return {'': ''}
            else:
                logger.warn(u"PlexPy Notifiers :: Unable to retrieve Pushover notification sounds list.")
                return {'': ''}

        else:
            return {'': ''}

    def return_config_options(self):
        config_option = [{'label': 'Pushover API Token',
                          'value': plexpy.CONFIG.PUSHOVER_APITOKEN,
                          'name': 'pushover_apitoken',
                          'description': 'Your Pushover API token.',
                          'input_type': 'text'
                          },
                         {'label': 'Pushover User or Group Key',
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
                         {'label': 'Enable HTML Support',
                          'value': self.html_support,
                          'name': 'pushover_html_support',
                          'description': 'Style your messages using these HTML tags: b, i, u, a[href], font[color]',
                          'input_type': 'checkbox'
                          }
                         ]

        return config_option


class TwitterNotifier(object):

    REQUEST_TOKEN_URL = 'https://api.twitter.com/oauth/request_token'
    ACCESS_TOKEN_URL = 'https://api.twitter.com/oauth/access_token'
    AUTHORIZATION_URL = 'https://api.twitter.com/oauth/authorize'
    SIGNIN_URL = 'https://api.twitter.com/oauth/authenticate'

    def __init__(self):
        self.access_token = plexpy.CONFIG.TWITTER_ACCESS_TOKEN
        self.access_token_secret = plexpy.CONFIG.TWITTER_ACCESS_TOKEN_SECRET
        self.consumer_key = plexpy.CONFIG.TWITTER_CONSUMER_KEY
        self.consumer_secret = plexpy.CONFIG.TWITTER_CONSUMER_SECRET
        self.incl_subject = plexpy.CONFIG.TWITTER_INCL_SUBJECT

    def notify(self, subject, message):
        if not subject or not message:
            return
        else:
            if self.incl_subject:
                self._send_tweet(subject + ': ' + message)
            else:
                self._send_tweet(message)

    def test_notify(self):
        return self._send_tweet("This is a test notification from PlexPy at " + helpers.now())

    def _get_authorization(self):

        oauth_consumer = oauth.Consumer(key=self.consumer_key, secret=self.consumer_secret)
        oauth_client = oauth.Client(oauth_consumer)

        logger.info("PlexPy Notifiers :: Requesting temp token from Twitter")

        resp, content = oauth_client.request(self.REQUEST_TOKEN_URL, 'GET')

        if resp['status'] != '200':
            logger.warn("PlexPy Notifiers :: Invalid respond from Twitter requesting temp token: %s" % resp['status'])
        else:
            request_token = dict(parse_qsl(content))

            plexpy.CONFIG.TWITTER_ACCESS_TOKEN = request_token['oauth_token']
            plexpy.CONFIG.TWITTER_ACCESS_TOKEN_SECRET = request_token['oauth_token_secret']

            return self.AUTHORIZATION_URL + "?oauth_token=" + request_token['oauth_token']

    def _get_credentials(self, key):
        request_token = {}

        request_token['oauth_token'] = plexpy.CONFIG.TWITTER_ACCESS_TOKEN
        request_token['oauth_token_secret'] = plexpy.CONFIG.TWITTER_ACCESS_TOKEN_SECRET
        request_token['oauth_callback_confirmed'] = 'true'

        token = oauth.Token(request_token['oauth_token'], request_token['oauth_token_secret'])
        token.set_verifier(key)

        # logger.debug(u"Generating and signing request for an access token using key " + key)

        oauth_consumer = oauth.Consumer(key=self.consumer_key, secret=self.consumer_secret)
        # logger.debug(u"oauth_consumer: " + str(oauth_consumer))
        oauth_client = oauth.Client(oauth_consumer, token)
        # logger.debug(u"oauth_client: " + str(oauth_client))
        resp, content = oauth_client.request(self.ACCESS_TOKEN_URL, method='POST', body='oauth_verifier=%s' % key)
        # logger.debug(u"resp, content: " + str(resp) + ',' + str(content))

        access_token = dict(parse_qsl(content))
        # logger.debug(u"access_token: " + str(access_token))

        # logger.debug(u"resp[status] = " + str(resp['status']))
        if resp['status'] != '200':
            logger.error(u"PlexPy Notifiers :: The request for a Twitter token did not succeed: " + str(resp['status']), logger.ERROR)
            return False
        else:
            # logger.info(u"PlexPy Notifiers :: Your Twitter Access Token key: %s" % access_token['oauth_token'])
            # logger.info(u"PlexPy Notifiers :: Access Token secret: %s" % access_token['oauth_token_secret'])
            plexpy.CONFIG.TWITTER_ACCESS_TOKEN = access_token['oauth_token']
            plexpy.CONFIG.TWITTER_ACCESS_TOKEN_SECRET = access_token['oauth_token_secret']
            plexpy.CONFIG.write()
            return True

    def _send_tweet(self, message=None):
        consumer_key = self.consumer_key
        consumer_secret = self.consumer_secret
        access_token = self.access_token
        access_token_secret = self.access_token_secret

        # logger.info(u"PlexPy Notifiers :: Sending tweet: " + message)

        api = twitter.Api(consumer_key, consumer_secret, access_token, access_token_secret)

        try:
            api.PostUpdate(message)
            logger.info(u"PlexPy Notifiers :: Twitter notification sent.")
            return True
        except Exception as e:
            logger.warn(u"PlexPy Notifiers :: Twitter notification failed: %s" % e)
            return False

    def return_config_options(self):
        config_option = [{'label': 'Instructions',
                          'description': 'Step 1: Visit <a href="' + helpers.anon_url('https://apps.twitter.com') + '" target="_blank"> \
                                          Twitter Apps</a> to <strong>Create New App</strong>. A vaild "Website" is not required.<br>\
                                          Step 2: Go to <strong>Keys and Access Tokens</strong> and click \
                                          <strong>Create my access token</strong>.<br>\
                                          Step 3: Fill in the <strong>Consumer Key</strong>, <strong>Consumer Secret</strong>, \
                                          <strong>Access Token</strong>, and <strong>Access Token Secret</strong> below.',
                          'input_type': 'help'
                          },
                         {'label': 'Twitter Consumer Key',
                          'value': self.consumer_key,
                          'name': 'twitter_consumer_key',
                          'description': 'Your Twitter consumer key.',
                          'input_type': 'text'
                          },
                         {'label': 'Twitter Consumer Secret',
                          'value': self.consumer_secret,
                          'name': 'twitter_consumer_secret',
                          'description': 'Your Twitter consumer secret.',
                          'input_type': 'text'
                          },
                         {'label': 'Twitter Access Token',
                          'value': self.access_token,
                          'name': 'twitter_access_token',
                          'description': 'Your Twitter access token.',
                          'input_type': 'text'
                          },
                         {'label': 'Twitter Access Token Secret',
                          'value': self.access_token_secret,
                          'name': 'twitter_access_token_secret',
                          'description': 'Your Twitter access token secret.',
                          'input_type': 'text'
                          },
                         {'label': 'Include Subject Line',
                          'value': self.incl_subject,
                          'name': 'twitter_incl_subject',
                          'description': 'Include the subject line with the notifications.',
                          'input_type': 'checkbox'
                          }
                         ]

        return config_option


class OSX_NOTIFY(object):

    def __init__(self):
        try:
            self.objc = __import__("objc")
            self.AppKit = __import__("AppKit")
        except:
            # logger.error(u"PlexPy Notifiers :: Cannot load OSX Notifications agent.")
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
                # notification.set_identityImage_(source_img)
            notification.setHasActionButton_(False)

            notification_center = NSUserNotificationCenter.defaultUserNotificationCenter()
            notification_center.deliverNotification_(notification)
            logger.info(u"PlexPy Notifiers :: OSX Notify notification sent.")

            del pool
            return True

        except Exception as e:
            logger.warn(u"PlexPy Notifiers :: OSX notification failed: %s" % e)
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
            logger.info(u"PlexPy Notifiers :: Boxcar2 notification sent.")
            return True

        except urllib2.URLError as e:
            logger.warn(u"PlexPy Notifiers :: Boxcar2 notification failed: %s" % e)
            return False

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
                          'select_options': self.get_sounds()
                          }
                         ]

        return config_option


class Email(object):

    def __init__(self):
        self.from_name = plexpy.CONFIG.EMAIL_FROM_NAME
        self.email_from = plexpy.CONFIG.EMAIL_FROM
        self.email_to = plexpy.CONFIG.EMAIL_TO
        self.email_cc = plexpy.CONFIG.EMAIL_CC
        self.email_bcc = plexpy.CONFIG.EMAIL_BCC
        self.smtp_server = plexpy.CONFIG.EMAIL_SMTP_SERVER
        self.smtp_port = plexpy.CONFIG.EMAIL_SMTP_PORT
        self.smtp_user = plexpy.CONFIG.EMAIL_SMTP_USER
        self.smtp_password = plexpy.CONFIG.EMAIL_SMTP_PASSWORD
        self.tls = plexpy.CONFIG.EMAIL_TLS
        self.html_support = plexpy.CONFIG.EMAIL_HTML_SUPPORT

    def notify(self, subject, message):
        if not subject or not message:
            return

        if self.html_support:
            msg = MIMEMultipart('alternative')
            msg.attach(MIMEText(bleach.clean(message, strip=True), 'plain', 'utf-8'))
            msg.attach(MIMEText(message, 'html', 'utf-8'))
        else:
            msg = MIMEText(message, 'plain', 'utf-8')

        msg['Subject'] = subject
        msg['From'] = email.utils.formataddr((self.from_name, self.email_from))
        msg['To'] = self.email_to
        msg['CC'] = self.email_cc


        recipients = [x.strip() for x in self.email_to.split(';')] \
                   + [x.strip() for x in self.email_cc.split(';')] \
                   + [x.strip() for x in self.email_bcc.split(';')]
        recipients = filter(None, recipients)

        try:
            mailserver = smtplib.SMTP(self.smtp_server, self.smtp_port)

            if self.tls:
                mailserver.starttls()

            mailserver.ehlo()

            if self.smtp_user:
                mailserver.login(self.smtp_user, self.smtp_password)

            mailserver.sendmail(self.email_from, recipients, msg.as_string())
            mailserver.quit()

            logger.info(u"PlexPy Notifiers :: Email notification sent.")
            return True

        except Exception as e:
            logger.warn(u"PlexPy Notifiers :: Email notification failed: %s" % e)
            return False

    def return_config_options(self):
        config_option = [{'label': 'From Name',
                          'value': self.from_name,
                          'name': 'email_from_name',
                          'description': 'The name of the sender.',
                          'input_type': 'text'
                          },
                         {'label': 'From',
                          'value': self.email_from,
                          'name': 'email_from',
                          'description': 'The email address of the sender.',
                          'input_type': 'text'
                          },
                         {'label': 'To',
                          'value': self.email_to,
                          'name': 'email_to',
                          'description': 'The email address(es) of the recipients, separated by semicolons (;).',
                          'input_type': 'text'
                          },
                         {'label': 'CC',
                          'value': self.email_cc,
                          'name': 'email_cc',
                          'description': 'The email address(es) to CC, separated by semicolons (;).',
                          'input_type': 'text'
                          },
                         {'label': 'BCC',
                          'value': self.email_bcc,
                          'name': 'email_bcc',
                          'description': 'The email address(es) to BCC, separated by semicolons (;).',
                          'input_type': 'text'
                          },
                         {'label': 'SMTP Server',
                          'value': self.smtp_server,
                          'name': 'email_smtp_server',
                          'description': 'Host for the SMTP server.',
                          'input_type': 'text'
                          },
                         {'label': 'SMTP Port',
                          'value': self.smtp_port,
                          'name': 'email_smtp_port',
                          'description': 'Port for the SMTP server.',
                          'input_type': 'number'
                          },
                         {'label': 'SMTP User',
                          'value': self.smtp_user,
                          'name': 'email_smtp_user',
                          'description': 'User for the SMTP server.',
                          'input_type': 'text'
                          },
                         {'label': 'SMTP Password',
                          'value': self.smtp_password,
                          'name': 'email_smtp_password',
                          'description': 'Password for the SMTP server.',
                          'input_type': 'password'
                          },
                         {'label': 'TLS',
                          'value': self.tls,
                          'name': 'email_tls',
                          'description': 'Does the server use encryption.',
                          'input_type': 'checkbox'
                          },
                         {'label': 'Enable HTML Support',
                          'value': self.html_support,
                          'name': 'email_html_support',
                          'description': 'Style your messages using  HTML tags.',
                          'input_type': 'checkbox'
                          }
                         ]

        return config_option

class IFTTT(object):

    def __init__(self):
        self.apikey = plexpy.CONFIG.IFTTT_KEY
        self.event = plexpy.CONFIG.IFTTT_EVENT

    def notify(self, message, subject, action):
        if not message or not subject:
            return

        event = unicode(self.event).format(action=action)
        http_handler = HTTPSConnection("maker.ifttt.com")

        data = {'value1': subject.encode("utf-8"),
                'value2': message.encode("utf-8")}

        # logger.debug(u"Ifttt SENDING: %s" % json.dumps(data))

        http_handler.request("POST",
                             "/trigger/%s/with/key/%s" % (event, self.apikey),
                             headers={'Content-type': "application/json"},
                             body=json.dumps(data))
        response = http_handler.getresponse()
        request_status = response.status
        # logger.debug(u"Ifttt response status: %r" % request_status)
        # logger.debug(u"Ifttt response headers: %r" % response.getheaders())
        # logger.debug(u"Ifttt response body: %r" % response.read())

        if request_status == 200:
            logger.info(u"PlexPy Notifiers :: Ifttt notification sent.")
            return True
        elif request_status >= 400 and request_status < 500:
            logger.warn(u"PlexPy Notifiers :: Ifttt notification failed: [%s] %s" % (request_status, response.reason))
            return False
        else:
            logger.warn(u"PlexPy Notifiers :: Ifttt notification failed.")
            return False

    def test(self):
        return self.notify('PlexPy', 'Test Message')

    def return_config_options(self):
        config_option = [{'label': 'Ifttt Maker Channel Key',
                          'value': self.apikey,
                          'name': 'ifttt_key',
                          'description': 'Your Ifttt  key. You can get a key from'
                                         ' <a href="' + helpers.anon_url('https://ifttt.com/maker') + '" target="_blank">here</a>.',
                          'input_type': 'text'
                          },
                         {'label': 'Ifttt Event',
                          'value': self.event,
                          'name': 'ifttt_event',
                          'description': 'The Ifttt maker event to fire. You can include'
                                         ' the {action} to be substituted with the action name.'
                                         ' The notification subject and body will be sent'
                                         ' as value1 and value2 respectively.',
                          'input_type': 'text'
                          }

                         ]

        return config_option


class TELEGRAM(object):

    def __init__(self):
        self.enabled = plexpy.CONFIG.TELEGRAM_ENABLED
        self.bot_token = plexpy.CONFIG.TELEGRAM_BOT_TOKEN
        self.chat_id = plexpy.CONFIG.TELEGRAM_CHAT_ID
        self.html_support = plexpy.CONFIG.TELEGRAM_HTML_SUPPORT
        self.incl_poster = plexpy.CONFIG.TELEGRAM_INCL_POSTER
        self.incl_subject = plexpy.CONFIG.TELEGRAM_INCL_SUBJECT

    def conf(self, options):
        return cherrypy.config['config'].get('Telegram', options)

    def notify(self, message, event, **kwargs):
        if not message or not event:
            return

        data = {'chat_id': self.chat_id}

        if self.incl_subject:
            text = event.encode('utf-8') + ': ' + message.encode('utf-8')
        else:
            text = message.encode('utf-8')

        if self.incl_poster and 'metadata' in kwargs:
            metadata = kwargs['metadata']
            poster_url = metadata.get('poster_url','')

            if poster_url:
                files = {'photo': (poster_url, urllib.urlopen(poster_url).read())}
                response = requests.post('https://api.telegram.org/bot%s/%s' % (self.bot_token, 'sendPhoto'),
                                         data=data,
                                         files=files)
                request_status = response.status_code
                request_content = json.loads(response.text)

                if request_status == 200:
                    logger.info(u"PlexPy Notifiers :: Telegram poster sent.")
                elif request_status >= 400 and request_status < 500:
                    logger.warn(u"PlexPy Notifiers :: Telegram poster failed: %s" % request_content.get('description'))
                else:
                    logger.warn(u"PlexPy Notifiers :: Telegram poster failed.")

        data['text'] = text
        if self.html_support:
            data['parse_mode'] = 'HTML'

        http_handler = HTTPSConnection("api.telegram.org")
        http_handler.request('POST',
                             '/bot%s/%s' % (self.bot_token, 'sendMessage'),
                             headers={'Content-type': 'application/x-www-form-urlencoded'},
                             body=urlencode(data))

        response = http_handler.getresponse()
        request_status = response.status

        if request_status == 200:
            logger.info(u"PlexPy Notifiers :: Telegram notification sent.")
            return True
        elif request_status >= 400 and request_status < 500:
            logger.warn(u"PlexPy Notifiers :: Telegram notification failed: [%s] %s" % (request_status, response.reason))
            return False
        else:
            logger.warn(u"PlexPy Notifiers :: Telegram notification failed.")
            return False

    def updateLibrary(self):
        # For uniformity reasons not removed
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
                          'description': 'Your Telegram bot token. '
                                         'Contact <a href="' + helpers.anon_url('https://telegram.me/BotFather') + '" target="_blank">@BotFather</a>'
                                         ' on Telegram to get one.',
                          'input_type': 'text'
                          },
                         {'label': 'Telegram Chat ID, Group ID, or Channel Username',
                          'value': self.chat_id,
                          'name': 'telegram_chat_id',
                          'description': 'Your Telegram Chat ID, Group ID, or @channelusername. '
                                         'Contact <a href="' + helpers.anon_url('https://telegram.me/myidbot') + '" target="_blank">@myidbot</a>'
                                         ' on Telegram to get an ID.',
                          'input_type': 'text'
                          },
                         {'label': 'Include Poster Image',
                          'value': self.incl_poster,
                          'name': 'telegram_incl_poster',
                          'description': 'Include a poster with the notifications.',
                          'input_type': 'checkbox'
                          },
                         {'label': 'Include Subject Line',
                          'value': self.incl_subject,
                          'name': 'telegram_incl_subject',
                          'description': 'Include the subject line with the notifications.',
                          'input_type': 'checkbox'
                          },
                         {'label': 'Enable HTML Support',
                          'value': self.html_support,
                          'name': 'telegram_html_support',
                          'description': 'Style your messages using these HTML tags: b, i, a[href], code, pre',
                          'input_type': 'checkbox'
                          }
                         ]

        return config_option


class SLACK(object):
    """
    Slack Notifications
    """
    def __init__(self):
        self.enabled = plexpy.CONFIG.SLACK_ENABLED
        self.slack_hook = plexpy.CONFIG.SLACK_HOOK
        self.channel = plexpy.CONFIG.SLACK_CHANNEL
        self.username = plexpy.CONFIG.SLACK_USERNAME
        self.icon_emoji = plexpy.CONFIG.SLACK_ICON_EMOJI
        self.incl_subject = plexpy.CONFIG.SLACK_INCL_SUBJECT

    def conf(self, options):
        return cherrypy.config['config'].get('Slack', options)

    def notify(self, message, event):
        if not message or not event:
            return
        http_handler = HTTPSConnection("hooks.slack.com")

        if self.incl_subject:
            text = event.encode('utf-8') + ': ' + message.encode("utf-8")
        else:
            text = message.encode("utf-8")

        data = {'text': text}
        if self.channel != '': data['channel'] = self.channel
        if self.username != '': data['username'] = self.username
        if self.icon_emoji != '':
            if urlparse(self.icon_emoji).scheme == '':
                data['icon_emoji'] = self.icon_emoji
            else:
                data['icon_url'] = self.icon_emoji

        url = urlparse(self.slack_hook).path

        http_handler.request("POST",
                                url,
                                headers={'Content-type': "application/x-www-form-urlencoded"},
                                body=json.dumps(data))

        response = http_handler.getresponse()
        request_status = response.status

        if request_status == 200:
            logger.info(u"PlexPy Notifiers :: Slack notification sent.")
            return True
        elif request_status >= 400 and request_status < 500:
            logger.warn(u"PlexPy Notifiers :: Slack notification failed: [%s] %s" % (request_status, response.reason))
            return False
        else:
            logger.warn(u"PlexPy Notifiers :: Slack notification failed.")
            return False

    def updateLibrary(self):
        #For uniformity reasons not removed
        return

    def test(self):
        self.enabled = True
        return self.notify('Main Screen Activate', 'Test Message')

    def return_config_options(self):
        config_option = [{'label': 'Slack Webhook URL',
                          'value': self.slack_hook,
                          'name': 'slack_hook',
                          'description': 'Your Slack incoming webhook URL.',
                          'input_type': 'text'
                          },
                         {'label': 'Slack Channel',
                          'value': self.channel,
                          'name': 'slack_channel',
                          'description': 'Your Slack channel name (begin with \'#\'). Leave blank for webhook integration default.',
                          'input_type': 'text'
                          },
                          {'label': 'Slack Username',
                           'value': self.username,
                           'name': 'slack_username',
                           'description': 'The Slack username which will be shown. Leave blank for webhook integration default.',
                           'input_type': 'text'
                          },
                          {'label': 'Slack Icon',
                           'value': self.icon_emoji,
                           'description': 'The icon you wish to show, use Slack emoji or image url. Leave blank for webhook integration default.',
                           'name': 'slack_icon_emoji',
                           'input_type': 'text'
                          },
                         {'label': 'Include Subject Line',
                          'value': self.incl_subject,
                          'name': 'slack_incl_subject',
                          'description': 'Include the subject line with the notifications.',
                          'input_type': 'checkbox'
                          }
                         ]

        return config_option


class Scripts(object):

    def __init__(self, **kwargs):
        self.script_exts = ('.bat', '.cmd', '.exe', '.php', '.pl', '.ps1', '.py', '.pyw', '.rb', '.sh')

    def conf(self, options):
        return cherrypy.config['config'].get('Scripts', options)

    def updateLibrary(self):
        # For uniformity reasons not removed
        return

    def test(self, subject, message, *args, **kwargs):
        self.notify(subject, message, *args, **kwargs)
        return

    def list_scripts(self):
        scriptdir = plexpy.CONFIG.SCRIPTS_FOLDER
        scripts = {'': ''}

        if scriptdir and not os.path.exists(scriptdir):
            return scripts

        for root, dirs, files in os.walk(scriptdir):
            for f in files:
                name, ext = os.path.splitext(f)
                if ext in self.script_exts:
                    rfp = os.path.join(os.path.relpath(root, scriptdir), f)
                    fp = os.path.join(root, f)
                    scripts[fp] = rfp

        return scripts

    def notify(self, subject='', message='', notify_action='', script_args=None, *args, **kwargs):
        """
            Args:
                  subject(string, optional): Head text,
                  message(string, optional): Body text,
                  notify_action(string): 'play'
                  script_args(list): ["python2", '-p', '-zomg']
        """
        logger.debug(u"PlexPy Notifiers :: Trying to run notify script, action: %s, arguments: %s" %
                     (notify_action or None, script_args or None))

        if script_args is None:
            script_args = []

        if not plexpy.CONFIG.SCRIPTS_FOLDER:
            return

        # Make sure we use the correct script..
        if notify_action == 'play':
            script = plexpy.CONFIG.SCRIPTS_ON_PLAY_SCRIPT

        elif notify_action == 'stop':
            script = plexpy.CONFIG.SCRIPTS_ON_STOP_SCRIPT

        elif notify_action == 'pause':
            script = plexpy.CONFIG.SCRIPTS_ON_PAUSE_SCRIPT

        elif notify_action == 'resume':
            script = plexpy.CONFIG.SCRIPTS_ON_RESUME_SCRIPT

        elif notify_action == 'watched':
            script = plexpy.CONFIG.SCRIPTS_ON_WATCHED_SCRIPT

        elif notify_action == 'buffer':
            script = plexpy.CONFIG.SCRIPTS_ON_BUFFER_SCRIPT

        elif notify_action == 'created':
            script = plexpy.CONFIG.SCRIPTS_ON_CREATED_SCRIPT

        elif notify_action == 'intdown':
            script = plexpy.CONFIG.SCRIPTS_ON_INTDOWN_SCRIPT

        elif notify_action == 'intup':
            script = plexpy.CONFIG.SCRIPTS_ON_INTUP_SCRIPT

        elif notify_action == 'extdown':
            script = plexpy.CONFIG.SCRIPTS_ON_EXTDOWN_SCRIPT

        elif notify_action == 'extup':
            script = plexpy.CONFIG.SCRIPTS_ON_EXTUP_SCRIPT

        elif notify_action == 'pmsupdate':
            script = plexpy.CONFIG.SCRIPTS_ON_PMSUPDATE_SCRIPT

        else:
            # For manual scripts
            script = kwargs.get('script', '')

        # Don't try to run the script if the action does not have one
        if notify_action and not script:
            logger.debug(u"PlexPy Notifiers :: No script selected for action %s, exiting..." % notify_action)
            return
        elif not script:
            logger.debug(u"PlexPy Notifiers :: No script selected, exiting...")
            return

        name, ext = os.path.splitext(script)

        if ext == '.php':
            prefix = 'php'
        elif ext == '.pl':
            prefix = 'perl'
        elif ext == '.ps1':
            prefix = 'powershell -executionPolicy bypass -file'
        elif ext == '.py':
            prefix = 'python'
        elif ext == '.pyw':
            prefix = 'pythonw'
        elif ext == '.rb':
            prefix = 'ruby'
        else:
            prefix = ''

        if os.name == 'nt':
            script = script.encode(plexpy.SYS_ENCODING, 'ignore')

        if prefix:
            script = prefix.split() + [script]
        else:
            script = [script]

        # For manual notifications
        if script_args and isinstance(script_args, basestring):
            # attemps for format it for the user
            script_args = shlex.split(script_args)

        # Windows handles unicode very badly.
        # https://bugs.python.org/issue19264
        if script_args and os.name == 'nt':
            script_args = [s.encode(plexpy.SYS_ENCODING, 'ignore') for s in script_args]

        # Allow overrides for shitty systems
        if prefix and script_args:
            if script_args[0] in ['python2', 'python', 'pythonw', 'php', 'ruby', 'perl']:
                script[0] = script_args[0]
                del script_args[0]

        script.extend(script_args)

        logger.debug(u"PlexPy Notifiers :: Full script is: %s" % script)

        try:
            p = subprocess.Popen(script, stdin=subprocess.PIPE,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT,
                                 cwd=plexpy.CONFIG.SCRIPTS_FOLDER)

            out, error = p.communicate()
            status = p.returncode

            if out and status:
                out = out.strip()
                logger.debug(u"PlexPy Notifiers :: Script returned: %s" % out)

            if error:
                error = error.strip()
                logger.error(u"PlexPy Notifiers :: Script error: %s" % error)
                return False
            else:
                logger.info(u"PlexPy Notifiers :: Script notification sent.")
                return True

        except OSError as e:
            logger.error(u"PlexPy Notifiers :: Failed to run script: %s" % e)
            return False

    def return_config_options(self):
        config_option = [{'label': 'Supported File Types',
                          'description': ', '.join(self.script_exts),
                          'input_type': 'help'
                          },
                         {'label': 'Script Folder',
                          'value': plexpy.CONFIG.SCRIPTS_FOLDER,
                          'name': 'scripts_folder',
                          'description': 'Add your script folder.',
                          'input_type': 'text',
                          },
                         {'label': 'Playback Start',
                          'value': plexpy.CONFIG.SCRIPTS_ON_PLAY_SCRIPT,
                          'name': 'scripts_on_play_script',
                          'description': 'Choose the script for on play.',
                          'input_type': 'select',
                          'select_options': self.list_scripts()
                          },
                         {'label': 'Playback Stop',
                          'value': plexpy.CONFIG.SCRIPTS_ON_STOP_SCRIPT,
                          'name': 'scripts_on_stop_script',
                          'description': 'Choose the script for on stop.',
                          'input_type': 'select',
                          'select_options': self.list_scripts()
                          },
                         {'label': 'Playback Pause',
                          'value': plexpy.CONFIG.SCRIPTS_ON_PAUSE_SCRIPT,
                          'name': 'scripts_on_pause_script',
                          'description': 'Choose the script for on pause.',
                          'input_type': 'select',
                          'select_options': self.list_scripts()
                          },
                         {'label': 'Playback Resume',
                          'value': plexpy.CONFIG.SCRIPTS_ON_RESUME_SCRIPT,
                          'name': 'scripts_on_resume_script',
                          'description': 'Choose the script for on resume.',
                          'input_type': 'select',
                          'select_options': self.list_scripts()
                          },
                         {'label': 'Watched',
                          'value': plexpy.CONFIG.SCRIPTS_ON_WATCHED_SCRIPT,
                          'name': 'scripts_on_watched_script',
                          'description': 'Choose the script for on watched.',
                          'input_type': 'select',
                          'select_options': self.list_scripts()
                          },
                         {'label': 'Buffer Warnings',
                          'value': plexpy.CONFIG.SCRIPTS_ON_BUFFER_SCRIPT,
                          'name': 'scripts_on_buffer_script',
                          'description': 'Choose the script for buffer warnings.',
                          'input_type': 'select',
                          'select_options': self.list_scripts()
                          },
                         {'label': 'Recently Added',
                          'value': plexpy.CONFIG.SCRIPTS_ON_CREATED_SCRIPT,
                          'name': 'scripts_on_created_script',
                          'description': 'Choose the script for recently added.',
                          'input_type': 'select',
                          'select_options': self.list_scripts()
                          },
                         {'label': 'Plex Server Down',
                          'value': plexpy.CONFIG.SCRIPTS_ON_INTDOWN_SCRIPT,
                          'name': 'scripts_on_intdown_script',
                          'description': 'Choose the script for Plex server down.',
                          'input_type': 'select',
                          'select_options': self.list_scripts()
                          },
                         {'label': 'Plex Server Back Up',
                          'value': plexpy.CONFIG.SCRIPTS_ON_INTUP_SCRIPT,
                          'name': 'scripts_on_intup_script',
                          'description': 'Choose the script for Plex server back up.',
                          'input_type': 'select',
                          'select_options': self.list_scripts()
                          },
                         {'label': 'Plex Remote Access Down',
                          'value': plexpy.CONFIG.SCRIPTS_ON_EXTDOWN_SCRIPT,
                          'name': 'scripts_on_extdown_script',
                          'description': 'Choose the script for Plex remote access down.',
                          'input_type': 'select',
                          'select_options': self.list_scripts()
                          },
                         {'label': 'Plex Remote Access Back Up',
                          'value': plexpy.CONFIG.SCRIPTS_ON_EXTUP_SCRIPT,
                          'name': 'scripts_on_extup_script',
                          'description': 'Choose the script for Plex remote access back up.',
                          'input_type': 'select',
                          'select_options': self.list_scripts()
                          },
                         {'label': 'Plex Update Available',
                          'value': plexpy.CONFIG.SCRIPTS_ON_PMSUPDATE_SCRIPT,
                          'name': 'scripts_on_pmsupdate_script',
                          'description': 'Choose the script for Plex update available.',
                          'input_type': 'select',
                          'select_options': self.list_scripts()
                          }
                         ]

        return config_option


class FacebookNotifier(object):

    def __init__(self):
        self.redirect_uri = plexpy.CONFIG.FACEBOOK_REDIRECT_URI
        self.access_token = plexpy.CONFIG.FACEBOOK_TOKEN
        self.app_id = plexpy.CONFIG.FACEBOOK_APP_ID
        self.app_secret = plexpy.CONFIG.FACEBOOK_APP_SECRET
        self.group_id = plexpy.CONFIG.FACEBOOK_GROUP
        self.incl_pmslink = plexpy.CONFIG.FACEBOOK_INCL_PMSLINK
        self.incl_poster = plexpy.CONFIG.FACEBOOK_INCL_POSTER
        self.incl_subject = plexpy.CONFIG.FACEBOOK_INCL_SUBJECT

    def notify(self, subject, message, **kwargs):
        if not subject or not message:
            return
        else:
            if self.incl_subject:
                self._post_facebook(subject + ': ' + message, **kwargs)
            else:
                self._post_facebook(message, **kwargs)

    def test_notify(self):
        return self._post_facebook(u"PlexPy Notifiers :: This is a test notification from PlexPy at " + helpers.now())

    def _get_authorization(self):
        return facebook.auth_url(app_id=self.app_id,
                                 canvas_url=self.redirect_uri + '/facebookStep2',
                                 perms=['user_managed_groups','publish_actions'])

    def _get_credentials(self, code):
        logger.info(u"PlexPy Notifiers :: Requesting access token from Facebook")

        try:
            # Request user access token
            api = facebook.GraphAPI(version='2.5')
            response = api.get_access_token_from_code(code=code,
                                                      redirect_uri=self.redirect_uri + '/facebookStep2',
                                                      app_id=self.app_id,
                                                      app_secret=self.app_secret)
            access_token = response['access_token']

            # Request extended user access token
            api = facebook.GraphAPI(access_token=access_token, version='2.5')
            response = api.extend_access_token(app_id=self.app_id,
                                               app_secret=self.app_secret)
            access_token = response['access_token']

            plexpy.CONFIG.FACEBOOK_TOKEN = access_token
            plexpy.CONFIG.write()
        except Exception as e:
            logger.error(u"PlexPy Notifiers :: Error requesting Facebook access token: %s" % e)
            return False

        return True

    def _post_facebook(self, message=None, **kwargs):
        if self.group_id:
            api = facebook.GraphAPI(access_token=self.access_token, version='2.5')

            attachment = {}

            if self.incl_poster and 'metadata' in kwargs:
                metadata = kwargs['metadata']
                poster_url = metadata.get('poster_url','')
                poster_link = ''
                caption = ''

                # Use default posters if no poster_url
                if not poster_url:
                    if metadata['media_type'] in ['artist', 'track']:
                        poster_url = 'https://raw.githubusercontent.com/drzoidberg33/plexpy/master/data/interfaces/default/images/cover.png'
                    else:
                        poster_url = 'https://raw.githubusercontent.com/drzoidberg33/plexpy/master/data/interfaces/default/images/poster.png'

                if metadata['media_type'] == 'movie':
                    title = '%s (%s)' % (metadata['title'], metadata['year'])
                    subtitle = metadata['summary']
                    rating_key = metadata['rating_key']
                    if metadata.get('imdb_url',''):
                        poster_link = metadata.get('imdb_url', '')
                        caption = 'View on IMDB'
                    elif metadata.get('themoviedb_url',''):
                        poster_link = metadata.get('themoviedb_url', '')
                        caption = 'View on The Movie Database'

                elif metadata['media_type'] == 'show':
                    title = '%s (%s)' % (metadata['title'], metadata['year'])
                    subtitle = metadata['summary']
                    rating_key = metadata['rating_key']
                    if metadata.get('thetvdb_url',''):
                        poster_link = metadata.get('thetvdb_url', '')
                        caption = 'View on TheTVDB'
                    elif metadata.get('themoviedb_url',''):
                        poster_link = metadata.get('themoviedb_url', '')
                        caption = 'View on The Movie Database'

                elif metadata['media_type'] == 'episode':
                    title = '%s - %s (S%s %s E%s)' % (metadata['grandparent_title'],
                                                        metadata['title'],
                                                        metadata['parent_media_index'],
                                                        '\xc2\xb7'.decode('utf8'),
                                                        metadata['media_index'])
                    subtitle = metadata['summary']
                    rating_key = metadata['rating_key']
                    if metadata.get('thetvdb_url',''):
                        poster_link = metadata.get('thetvdb_url', '')
                        caption = 'View on TheTVDB'
                    elif metadata.get('themoviedb_url',''):
                        poster_link = metadata.get('themoviedb_url', '')
                        caption = 'View on The Movie Database'

                elif metadata['media_type'] == 'artist':
                    title = metadata['title']
                    subtitle = metadata['summary']
                    rating_key = metadata['rating_key']
                    if metadata.get('lastfm_url',''):
                        poster_link = metadata.get('lastfm_url', '')
                        caption = 'View on Last.fm'

                elif metadata['media_type'] == 'track':
                    title = '%s - %s' % (metadata['grandparent_title'], metadata['title'])
                    subtitle = metadata['parent_title']
                    rating_key = metadata['parent_rating_key']
                    if metadata.get('lastfm_url',''):
                        poster_link = metadata.get('lastfm_url', '')
                        caption = 'View on Last.fm'

                # Build Facebook post attachment
                if self.incl_pmslink:
                    caption = 'View on Plex Web'
                    attachment['link'] = 'http://app.plex.tv/web/app#!/server/' + plexpy.CONFIG.PMS_IDENTIFIER + \
                                            '/details/%2Flibrary%2Fmetadata%2F' + rating_key
                elif poster_link:
                    attachment['link'] = poster_link
                else:
                    attachment['link'] = poster_url

                attachment['picture'] = poster_url
                attachment['name'] = title
                attachment['description'] = subtitle
                attachment['caption'] = caption

            try:
                api.put_wall_post(profile_id=self.group_id, message=message, attachment=attachment)
                logger.info(u"PlexPy Notifiers :: Facebook notification sent.")
                return True
            except Exception as e:
                logger.warn(u"PlexPy Notifiers :: Error sending Facebook post: %s" % e)
                return False

        else:
            logger.warn(u"PlexPy Notifiers :: Error sending Facebook post: No Facebook Group ID provided.")
            return False

    def return_config_options(self):
        config_option = [{'label': 'Instructions',
                          'description': 'Step 1: Visit <a href="' + helpers.anon_url('https://developers.facebook.com/apps') + '" target="_blank"> \
                                          Facebook Developers</a> to add a new app using <strong>basic setup</strong>.<br>\
                                          Step 2: Go to <strong>Settings > Advanced</strong> and fill in \
                                          <strong>Valid OAuth redirect URIs</strong> with your PlexPy URL (e.g. http://localhost:8181).<br>\
                                          Step 3: Go to <strong>App Review</strong> and toggle public to <strong>Yes</strong>.<br>\
                                          Step 4: Fill in the <strong>PlexPy URL</strong> below with the exact same URL from Step 3.<br>\
                                          Step 5: Fill in the <strong>App ID</strong> and <strong>App Secret</strong> below.<br>\
                                          Step 6: Click the <strong>Request Authorization</strong> button below.<br>\
                                          Step 7: Fill in your <strong>Group ID</strong> below.',
                          'input_type': 'help'
                          },
                         {'label': 'PlexPy URL',
                          'value': self.redirect_uri,
                          'name': 'facebook_redirect_uri',
                          'description': 'Your PlexPy URL. This will tell Facebook where to redirect you after authorization.\
                                          (e.g. http://localhost:8181)',
                          'input_type': 'text'
                          },
                         {'label': 'Facebook App ID',
                          'value': self.app_id,
                          'name': 'facebook_app_id',
                          'description': 'Your Facebook app ID.',
                          'input_type': 'text'
                          },
                         {'label': 'Facebook App Secret',
                          'value': self.app_secret,
                          'name': 'facebook_app_secret',
                          'description': 'Your Facebook app secret.',
                          'input_type': 'text'
                          },
                         {'label': 'Request Authorization',
                          'value': 'Request Authorization',
                          'name': 'facebookStep1',
                          'description': 'Request Facebook authorization. (Ensure you allow the browser pop-up).',
                          'input_type': 'button'
                          },
                         {'label': 'Facebook Group ID',
                          'value': self.group_id,
                          'name': 'facebook_group',
                          'description': 'Your Facebook Group ID.',
                          'input_type': 'text'
                          },
                         {'label': 'Include Poster Image',
                          'value': self.incl_poster,
                          'name': 'facebook_incl_poster',
                          'description': 'Include a poster with the notifications.',
                          'input_type': 'checkbox'
                          },
                         {'label': 'Include Link to Plex Web',
                          'value': self.incl_pmslink,
                          'name': 'facebook_incl_pmslink',
                          'description': 'Include a link to the media in Plex Web with the notifications.<br>'
                                         'If disabled, the link will go to IMDB, TVDB, TMDb, or Last.fm instead, if available.',
                          'input_type': 'checkbox'
                          },
                         {'label': 'Include Subject Line',
                          'value': self.incl_subject,
                          'name': 'facebook_incl_subject',
                          'description': 'Include the subject line with the notifications.',
                          'input_type': 'checkbox'
                          }
                         ]

        return config_option

class Browser(object):

    def __init__(self):
        self.enabled = plexpy.CONFIG.BROWSER_ENABLED
        self.auto_hide_delay = plexpy.CONFIG.BROWSER_AUTO_HIDE_DELAY

    def notify(self, subject, message):
        if not subject or not message:
            return

        logger.info(u"PlexPy Notifiers :: Browser notification sent.")
        return True

    def get_notifications(self):
        if not self.enabled:
            return

        monitor_db = database.MonitorDatabase()
        result = monitor_db.select('SELECT subject_text, body_text FROM notify_log '
                                   'WHERE agent_id = 17 AND timestamp >= ? ',
                                   args=[time.time() - 3])

        notifications = []
        for item in result:
            notification = {'subject_text': item['subject_text'],
                            'body_text': item['body_text'],
                            'delay': self.auto_hide_delay}
            notifications.append(notification)

        return {'notifications': notifications}

    def test(self, bot_token, chat_id):
        self.enabled = True
        self.notify('PlexPy', 'Test Notification')

    def return_config_options(self):
        config_option = [{'label': 'Enable Browser Notifications',
                          'value': self.enabled,
                          'name': 'browser_enabled',
                          'description': 'Enable to display desktop notifications from your browser.',
                          'input_type': 'checkbox'
                          },
                         {'label': 'Allow Notifications',
                          'value': 'Allow Notifications',
                          'name': 'allow_browser',
                          'description': 'Click to allow browser notifications. You must click this button for each browser.',
                          'input_type': 'button'
                          },
                         {'label': 'Auto Hide Delay',
                          'value': self.auto_hide_delay,
                          'name': 'browser_auto_hide_delay',
                          'description': 'Set the number of seconds for the notification to remain visible. \
                                          Set 0 to disable auto hiding. (Note: Some browsers have a maximum time limit.)',
                          'input_type': 'number'
                          }
                         ]

        return config_option