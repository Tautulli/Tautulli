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
        if not self.enabled:
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
        if not plexpy.CONFIG.PROWL_ENABLED:
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


class MPC(object):
    """
    MPC library update
    """

    def __init__(self):

        pass

    def notify(self):
        subprocess.call(["mpc", "update"])


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

    def update(self):
        # From what I read you can't update the music library on a per directory or per path basis
        # so need to update the whole thing

        hosts = [x.strip() for x in self.hosts.split(',')]

        for host in hosts:
            logger.info('Sending library update command to XBMC @ ' + host)
            request = self._sendjson(host, 'AudioLibrary.Scan')

            if not request:
                logger.warn('Error sending update request to XBMC')

    def notify(self, artist, album, albumartpath):

        hosts = [x.strip() for x in self.hosts.split(',')]

        header = "PlexPy"
        message = "%s - %s added to your library" % (artist, album)
        time = "3000" # in ms

        for host in hosts:
            logger.info('Sending notification command to XMBC @ ' + host)
            try:
                version = self._sendjson(host, 'Application.GetProperties', {'properties': ['version']})['version']['major']

                if version < 12: #Eden
                    notification = header + "," + message + "," + time + "," + albumartpath
                    notifycommand = {'command': 'ExecBuiltIn', 'parameter': 'Notification(' + notification + ')'}
                    request = self._sendhttp(host, notifycommand)

                else: #Frodo
                    params = {'title': header, 'message': message, 'displaytime': int(time), 'image': albumartpath}
                    request = self._sendjson(host, 'GUI.ShowNotification', params)

                if not request:
                    raise Exception

            except Exception:
                logger.error('Error sending notification request to XBMC')


class LMS(object):
    """
    Class for updating a Logitech Media Server
    """

    def __init__(self):
        self.hosts = plexpy.CONFIG.LMS_HOST

    def _sendjson(self, host):
        data = {'id': 1, 'method': 'slim.request', 'params': ["", ["rescan"]]}
        data = json.JSONEncoder().encode(data)

        content = {'Content-Type': 'application/json'}

        req = urllib2.Request(host + '/jsonrpc.js', data, content)

        try:
            handle = urllib2.urlopen(req)
        except Exception as e:
            logger.warn('Error opening LMS url: %s' % e)
            return

        response = json.JSONDecoder().decode(handle.read())

        try:
            return response['result']
        except:
            logger.warn('LMS returned error: %s' % response['error'])
            return response['error']

    def update(self):

        hosts = [x.strip() for x in self.hosts.split(',')]

        for host in hosts:
            logger.info('Sending library rescan command to LMS @ ' + host)
            request = self._sendjson(host)

            if request:
                logger.warn('Error sending rescan request to LMS')


class Plex(object):
    def __init__(self):

        self.server_hosts = plexpy.CONFIG.PLEX_SERVER_HOST
        self.client_hosts = plexpy.CONFIG.PLEX_CLIENT_HOST
        self.username = plexpy.CONFIG.PLEX_USERNAME
        self.password = plexpy.CONFIG.PLEX_PASSWORD

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

    def update(self):

        # From what I read you can't update the music library on a per directory or per path basis
        # so need to update the whole thing

        hosts = [x.strip() for x in self.server_hosts.split(',')]

        for host in hosts:
            logger.info('Sending library update command to Plex Media Server@ ' + host)
            url = "%s/library/sections" % host
            try:
                xml_sections = minidom.parse(urllib.urlopen(url))
            except IOError, e:
                logger.warn("Error while trying to contact Plex Media Server: %s" % e)
                return False

            sections = xml_sections.getElementsByTagName('Directory')
            if not sections:
                logger.info(u"Plex Media Server not running on: " + host)
                return False

            for s in sections:
                if s.getAttribute('type') == "artist":
                    url = "%s/library/sections/%s/refresh" % (host, s.getAttribute('key'))
                    try:
                        urllib.urlopen(url)
                    except Exception as e:
                        logger.warn("Error updating library section for Plex Media Server: %s" % e)
                        return False

    def notify(self, artist, album, albumartpath):

        hosts = [x.strip() for x in self.client_hosts.split(',')]

        header = "PlexPy"
        message = "%s - %s added to your library" % (artist, album)
        time = "3000" # in ms

        for host in hosts:
            logger.info('Sending notification command to Plex Media Server @ ' + host)
            try:
                notification = header + "," + message + "," + time + "," + albumartpath
                notifycommand = {'command': 'ExecBuiltIn', 'parameter': 'Notification(' + notification + ')'}
                request = self._sendhttp(host, notifycommand)

                if not request:
                    raise Exception

            except:
                logger.warn('Error sending notification request to Plex Media Server')


class NMA(object):
    def notify(self, artist=None, album=None, snatched=None):
        title = 'PlexPy'
        api = plexpy.CONFIG.NMA_APIKEY
        nma_priority = plexpy.CONFIG.NMA_PRIORITY

        logger.debug(u"NMA title: " + title)
        logger.debug(u"NMA API: " + api)
        logger.debug(u"NMA Priority: " + str(nma_priority))

        if snatched:
            event = snatched + " snatched!"
            message = "PlexPy has snatched: " + snatched
        else:
            event = artist + ' - ' + album + ' complete!'
            message = "PlexPy has downloaded and postprocessed: " + artist + ' [' + album + ']'

        logger.debug(u"NMA event: " + event)
        logger.debug(u"NMA message: " + message)

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


class PUSHBULLET(object):

    def __init__(self):
        self.apikey = plexpy.CONFIG.PUSHBULLET_APIKEY
        self.deviceid = plexpy.CONFIG.PUSHBULLET_DEVICEID

    def conf(self, options):
        return cherrypy.config['config'].get('PUSHBULLET', options)

    def notify(self, message, event):
        if not plexpy.CONFIG.PUSHBULLET_ENABLED:
            return

        http_handler = HTTPSConnection("api.pushbullet.com")

        data = {'type': "note",
                'title': "PlexPy",
                'body': message.encode("utf-8")}

        http_handler.request("POST",
                                "/v2/pushes",
                                headers={'Content-type': "application/json",
                                            'Authorization': 'Basic %s' % base64.b64encode(plexpy.CONFIG.PUSHBULLET_APIKEY + ":")},
                                body=json.dumps(data))
        response = http_handler.getresponse()
        request_status = response.status
        logger.debug(u"PushBullet response status: %r" % request_status)
        logger.debug(u"PushBullet response headers: %r" % response.getheaders())
        logger.debug(u"PushBullet response body: %r" % response.read())

        if request_status == 200:
                logger.info(u"PushBullet notifications sent.")
                return True
        elif request_status >= 400 and request_status < 500:
                logger.info(u"PushBullet request failed: %s" % response.reason)
                return False
        else:
                logger.info(u"PushBullet notification failed serverside.")
                return False

    def updateLibrary(self):
        #For uniformity reasons not removed
        return

    def test(self, apikey, deviceid):

        self.enabled = True
        self.apikey = apikey
        self.deviceid = deviceid

        self.notify('Main Screen Activate', 'Test Message')


class PUSHALOT(object):

    def notify(self, message, event):
        if not plexpy.CONFIG.PUSHALOT_ENABLED:
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


class Synoindex(object):
    def __init__(self, util_loc='/usr/syno/bin/synoindex'):
        self.util_loc = util_loc

    def util_exists(self):
        return os.path.exists(self.util_loc)

    def notify(self, path):
        path = os.path.abspath(path)

        if not self.util_exists():
            logger.warn("Error sending notification: synoindex utility not found at %s" % self.util_loc)
            return

        if os.path.isfile(path):
            cmd_arg = '-a'
        elif os.path.isdir(path):
            cmd_arg = '-A'
        else:
            logger.warn("Error sending notification: Path passed to synoindex was not a file or folder.")
            return

        cmd = [self.util_loc, cmd_arg, path]
        logger.info("Calling synoindex command: %s" % str(cmd))
        try:
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=plexpy.PROG_DIR)
            out, error = p.communicate()
            #synoindex never returns any codes other than '0', highly irritating
        except OSError, e:
            logger.warn("Error sending notification: %s" % str(e))

    def notify_multiple(self, path_list):
        if isinstance(path_list, list):
            for path in path_list:
                self.notify(path)


class PUSHOVER(object):

    def __init__(self):
        self.enabled = plexpy.CONFIG.PUSHOVER_ENABLED
        self.keys = plexpy.CONFIG.PUSHOVER_KEYS
        self.priority = plexpy.CONFIG.PUSHOVER_PRIORITY

        if plexpy.CONFIG.PUSHOVER_APITOKEN:
            self.application_token = plexpy.CONFIG.PUSHOVER_APITOKEN
        else:
            self.application_token = "LdPCoy0dqC21ktsbEyAVCcwvQiVlsz"

    def conf(self, options):
        return cherrypy.config['config'].get('Pushover', options)

    def notify(self, message, event):
        if not plexpy.CONFIG.PUSHOVER_ENABLED:
            return

        http_handler = HTTPSConnection("api.pushover.net")

        data = {'token': self.application_token,
                'user': plexpy.CONFIG.PUSHOVER_KEYS,
                'title': event,
                'message': message.encode("utf-8"),
                'priority': plexpy.CONFIG.PUSHOVER_PRIORITY}

        http_handler.request("POST",
                                "/1/messages.json",
                                headers={'Content-type': "application/x-www-form-urlencoded"},
                                body=urlencode(data))
        response = http_handler.getresponse()
        request_status = response.status
        logger.debug(u"Pushover response status: %r" % request_status)
        logger.debug(u"Pushover response headers: %r" % response.getheaders())
        logger.debug(u"Pushover response body: %r" % response.read())

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

    def test(self, keys, priority):
        self.enabled = True
        self.keys = keys
        self.priority = priority

        self.notify('Main Screen Activate', 'Test Message')


class TwitterNotifier(object):

    REQUEST_TOKEN_URL = 'https://api.twitter.com/oauth/request_token'
    ACCESS_TOKEN_URL = 'https://api.twitter.com/oauth/access_token'
    AUTHORIZATION_URL = 'https://api.twitter.com/oauth/authorize'
    SIGNIN_URL = 'https://api.twitter.com/oauth/authenticate'

    def __init__(self):
        self.consumer_key = "oYKnp2ddX5gbARjqX8ZAAg"
        self.consumer_secret = "A4Xkw9i5SjHbTk7XT8zzOPqivhj9MmRDR9Qn95YA9sk"

    def notify_snatch(self, title):
        if plexpy.CONFIG.TWITTER_ONSNATCH:
            self._notifyTwitter(common.notifyStrings[common.NOTIFY_SNATCH] + ': ' + title + ' at ' + helpers.now())

    def notify_download(self, title):
        if plexpy.CONFIG.TWITTER_ENABLED:
            self._notifyTwitter(common.notifyStrings[common.NOTIFY_DOWNLOAD] + ': ' + title + ' at ' + helpers.now())

    def test_notify(self):
        return self._notifyTwitter("This is a test notification from PlexPy at " + helpers.now(), force=True)

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
        logger.info('oauth_consumer: ' + str(oauth_consumer))
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

    def _notifyTwitter(self, message='', force=False):
        prefix = plexpy.CONFIG.TWITTER_PREFIX

        if not plexpy.CONFIG.TWITTER_ENABLED and not force:
            return False

        return self._send_tweet(prefix + ": " + message)


class OSX_NOTIFY(object):

    def __init__(self):
        try:
            self.objc = __import__("objc")
            self.AppKit = __import__("AppKit")
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

            del pool
            return True

        except Exception as e:
            logger.warn('Error sending OS X Notification: %s' % e)
            return False

    def swizzled_bundleIdentifier(self, original, swizzled):
        return 'ade.plexpy.osxnotify'


class BOXCAR(object):

    def __init__(self):
        self.url = 'https://new.boxcar.io/api/notifications'

    def notify(self, title, message, rgid=None):
        try:
            if rgid:
                message += '<br></br><a href="http://musicbrainz.org/release-group/%s">MusicBrainz</a>' % rgid

            data = urllib.urlencode({
                'user_credentials': plexpy.CONFIG.BOXCAR_TOKEN,
                'notification[title]': title.encode('utf-8'),
                'notification[long_message]': message.encode('utf-8'),
                'notification[sound]': "done"
                })

            req = urllib2.Request(self.url)
            handle = urllib2.urlopen(req, data)
            handle.close()
            return True

        except urllib2.URLError as e:
            logger.warn('Error sending Boxcar2 Notification: %s' % e)
            return False


class SubSonicNotifier(object):

    def __init__(self):
        self.host = plexpy.CONFIG.SUBSONIC_HOST
        self.username = plexpy.CONFIG.SUBSONIC_USERNAME
        self.password = plexpy.CONFIG.SUBSONIC_PASSWORD

    def notify(self, albumpaths):
        # Correct URL
        if not self.host.lower().startswith("http"):
            self.host = "http://" + self.host

        if not self.host.lower().endswith("/"):
            self.host = self.host + "/"

        # Invoke request
        request.request_response(self.host + "musicFolderSettings.view?scanNow",
            auth=(self.username, self.password))

class Email(object):

    def notify(self, subject, message):

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
            return True

        except Exception, e:
            logger.warn('Error sending Email: %s' % e)
            return False