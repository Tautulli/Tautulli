import copy
import hashlib
import html
import os
import threading
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import requests

try:
    import cryptography
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ed25519
except ImportError:  # pragma: no cover
    cryptography = None

try:
    import jwt
except ImportError:  # pragma: no cover
    jwt = None

from plexapi import (BASE_HEADERS, CONFIG, TIMEOUT, X_PLEX_ENABLE_FAST_CONNECT, X_PLEX_IDENTIFIER,
                     log, logfilter, utils)
from plexapi.base import PlexObject, cached_data_property
from plexapi.client import PlexClient
from plexapi.exceptions import BadRequest, NotFound, Unauthorized, TwoFactorRequired
from plexapi.library import LibrarySection
from plexapi.server import PlexServer
from plexapi.sonos import PlexSonosClient
from plexapi.sync import SyncItem, SyncList
from requests.status_codes import _codes as codes


class MyPlexAccount(PlexObject):
    """ MyPlex account and profile information. This object represents the data found Account on
        the myplex.tv servers at the url https://plex.tv/api/v2/user. You may create this object
        directly by passing in your username & password (or token). There is also a convenience
        method provided at :class:`~plexapi.server.PlexServer.myPlexAccount()` which will create
        and return this object.

        Parameters:
            username (str): Plex login username if not using a token.
            password (str): Plex login password if not using a token.
            token (str): Plex authentication token instead of username and password.
            session (requests.Session, optional): Use your own session object if you want to
                cache the http responses from PMS.
            timeout (int): timeout in seconds on initial connect to myplex (default config.TIMEOUT).
            code (str): Two-factor authentication code to use when logging in with username and password.
            remember (bool): Remember the account token for 14 days (Default True).

        Attributes:
            key (str): 'https://plex.tv/api/v2/user'
            adsConsent (str): Unknown.
            adsConsentReminderAt (str): Unknown.
            adsConsentSetAt (str): Unknown.
            anonymous (str): Unknown.
            authToken (str): The account token.
            backupCodesCreated (bool): If the two-factor authentication backup codes have been created.
            confirmed (bool): If the account has been confirmed.
            country (str): The account country.
            email (str): The account email address.
            emailOnlyAuth (bool): If login with email only is enabled.
            experimentalFeatures (bool): If experimental features are enabled.
            friendlyName (str): Your account full name.
            entitlements (List<str>): List of devices your allowed to use with this account.
            guest (bool): If the account is a Plex Home guest user.
            hasPassword (bool): If the account has a password.
            home (bool): If the account is a Plex Home user.
            homeAdmin (bool): If the account is the Plex Home admin.
            homeSize (int): The number of accounts in the Plex Home.
            id (int): The Plex account ID.
            joinedAt (datetime): Date the account joined Plex.
            locale (str): the account locale
            mailingListActive (bool): If you are subscribed to the Plex newsletter.
            mailingListStatus (str): Your current mailing list status.
            maxHomeSize (int): The maximum number of accounts allowed in the Plex Home.
            pin (str): The hashed Plex Home PIN.
            profileAutoSelectAudio (bool): If the account has automatically select audio and subtitle tracks enabled.
            profileDefaultAudioLanguage (str): The preferred audio language for the account.
            profileDefaultSubtitleLanguage (str): The preferred subtitle language for the account.
            profileAutoSelectSubtitle (int): The auto-select subtitle mode
                (0 = Manually selected, 1 = Shown with foreign audio, 2 = Always enabled).
            profileDefaultSubtitleAccessibility (int): The subtitles for the deaf or hard-of-hearing (SDH) searches mode
                (0 = Prefer non-SDH subtitles, 1 = Prefer SDH subtitles, 2 = Only show SDH subtitles,
                3 = Only shown non-SDH subtitles).
            profileDefaultSubtitleForced (int): The forced subtitles searches mode
                (0 = Prefer non-forced subtitles, 1 = Prefer forced subtitles, 2 = Only show forced subtitles,
                3 = Only show non-forced subtitles).
            protected (bool): If the account has a Plex Home PIN enabled.
            rememberExpiresAt (datetime): Date the token expires.
            restricted (bool): If the account is a Plex Home managed user.
            roles: (List<str>) Lit of account roles. Plexpass membership listed here.
            scrobbleTypes (List<int>): Unknown.
            subscriptionActive (bool): If the account's Plex Pass subscription is active.
            subscriptionDescription (str): Description of the Plex Pass subscription.
            subscriptionFeatures: (List<str>) List of features allowed on your Plex Pass subscription.
            subscriptionPaymentService (str): Payment service used for your Plex Pass subscription.
            subscriptionPlan (str): Name of Plex Pass subscription plan.
            subscriptionStatus (str): String representation of ``subscriptionActive``.
            subscriptionSubscribedAt (datetime): Date the account subscribed to Plex Pass.
            thumb (str): URL of the account thumbnail.
            title (str): The title of the account (username or friendly name).
            twoFactorEnabled (bool): If two-factor authentication is enabled.
            username (str): The account username.
            uuid (str): The account UUID.
    """
    FRIENDINVITE = 'https://plex.tv/api/servers/{machineId}/shared_servers'                     # post with data
    HOMEUSERS = 'https://plex.tv/api/home/users'
    HOMEUSERCREATE = 'https://plex.tv/api/home/users?title={title}'                             # post with data
    EXISTINGUSER = 'https://plex.tv/api/home/users?invitedEmail={username}'                     # post with data
    FRIENDSERVERS = 'https://plex.tv/api/servers/{machineId}/shared_servers/{serverId}'         # put with data
    PLEXSERVERS = 'https://plex.tv/api/servers/{machineId}'                                     # get
    FRIENDUPDATE = 'https://plex.tv/api/v2/sharings/{userId}'                                   # put with args, delete
    HOMEUSER = 'https://plex.tv/api/home/users/{userId}'                                        # delete, put
    MANAGEDHOMEUSER = 'https://plex.tv/api/v2/home/users/restricted/{userId}'                   # put
    SIGNIN = 'https://plex.tv/api/v2/users/signin'                                              # post with auth
    SIGNOUT = 'https://plex.tv/api/v2/users/signout'                                            # delete
    WEBHOOKS = 'https://plex.tv/api/v2/user/webhooks'                                           # get, post with data
    OPTOUTS = 'https://plex.tv/api/v2/user/{userUUID}/settings/opt_outs'                        # get
    LINK = 'https://plex.tv/api/v2/pins/link'                                                   # put
    VIEWSTATESYNC = 'https://plex.tv/api/v2/user/view_state_sync'                               # put
    PING = 'https://plex.tv/api/v2/ping'
    # Hub sections
    VOD = 'https://vod.provider.plex.tv'                                                        # get
    MUSIC = 'https://music.provider.plex.tv'                                                    # get
    DISCOVER = 'https://discover.provider.plex.tv'
    METADATA = 'https://metadata.provider.plex.tv'
    key = 'https://plex.tv/api/v2/user'

    def __init__(self, username=None, password=None, token=None, session=None, timeout=None, code=None, remember=True):
        self._token = logfilter.add_secret(token or CONFIG.get('auth.server_token'))
        self._session = session or requests.Session()
        self._timeout = timeout or TIMEOUT
        self._sonos_cache = []
        self._sonos_cache_timestamp = 0
        data, initpath = self._signin(username, password, code, remember, timeout)
        super(MyPlexAccount, self).__init__(self, data, initpath)

    def _signin(self, username, password, code, remember, timeout):
        if self._token:
            return self.query(self.key), self.key
        payload = {
            'login': username or CONFIG.get('auth.myplex_username'),
            'password': password or CONFIG.get('auth.myplex_password'),
            'rememberMe': remember
        }
        if code:
            payload['verificationCode'] = code
        data = self.query(self.SIGNIN, method=self._session.post, data=payload, timeout=timeout)
        return data, self.SIGNIN

    def signout(self):
        """ Sign out of the Plex account. Invalidates the authentication token. """
        return self.query(self.SIGNOUT, method=self._session.delete)

    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        self._token = logfilter.add_secret(data.attrib.get('authToken'))
        self._webhooks = []

        self.adsConsent = data.attrib.get('adsConsent')
        self.adsConsentReminderAt = data.attrib.get('adsConsentReminderAt')
        self.adsConsentSetAt = data.attrib.get('adsConsentSetAt')
        self.anonymous = data.attrib.get('anonymous')
        self.authToken = self._token
        self.backupCodesCreated = utils.cast(bool, data.attrib.get('backupCodesCreated'))
        self.confirmed = utils.cast(bool, data.attrib.get('confirmed'))
        self.country = data.attrib.get('country')
        self.email = data.attrib.get('email')
        self.emailOnlyAuth = utils.cast(bool, data.attrib.get('emailOnlyAuth'))
        self.experimentalFeatures = utils.cast(bool, data.attrib.get('experimentalFeatures'))
        self.friendlyName = data.attrib.get('friendlyName')
        self.guest = utils.cast(bool, data.attrib.get('guest'))
        self.hasPassword = utils.cast(bool, data.attrib.get('hasPassword'))
        self.home = utils.cast(bool, data.attrib.get('home'))
        self.homeAdmin = utils.cast(bool, data.attrib.get('homeAdmin'))
        self.homeSize = utils.cast(int, data.attrib.get('homeSize'))
        self.id = utils.cast(int, data.attrib.get('id'))
        self.joinedAt = utils.toDatetime(data.attrib.get('joinedAt'))
        self.locale = data.attrib.get('locale')
        self.mailingListActive = utils.cast(bool, data.attrib.get('mailingListActive'))
        self.mailingListStatus = data.attrib.get('mailingListStatus')
        self.maxHomeSize = utils.cast(int, data.attrib.get('maxHomeSize'))
        self.pin = data.attrib.get('pin')
        self.protected = utils.cast(bool, data.attrib.get('protected'))
        self.rememberExpiresAt = utils.toDatetime(data.attrib.get('rememberExpiresAt'))
        self.restricted = utils.cast(bool, data.attrib.get('restricted'))
        self.scrobbleTypes = [utils.cast(int, x) for x in data.attrib.get('scrobbleTypes').split(',')]
        self.thumb = data.attrib.get('thumb')
        self.title = data.attrib.get('title')
        self.twoFactorEnabled = utils.cast(bool, data.attrib.get('twoFactorEnabled'))
        self.username = data.attrib.get('username')
        self.uuid = data.attrib.get('uuid')

        subscription = data.find('subscription')
        self.subscriptionActive = utils.cast(bool, subscription.attrib.get('active'))
        self.subscriptionDescription = data.attrib.get('subscriptionDescription')
        self.subscriptionPaymentService = subscription.attrib.get('paymentService')
        self.subscriptionPlan = subscription.attrib.get('plan')
        self.subscriptionStatus = subscription.attrib.get('status')
        self.subscriptionSubscribedAt = utils.toDatetime(
            subscription.attrib.get('subscribedAt') or None, '%Y-%m-%d %H:%M:%S %Z'
        )

        profile = data.find('profile')
        self.profileAutoSelectAudio = utils.cast(bool, profile.attrib.get('autoSelectAudio'))
        self.profileDefaultAudioLanguage = profile.attrib.get('defaultAudioLanguage')
        self.profileDefaultSubtitleLanguage = profile.attrib.get('defaultSubtitleLanguage')
        self.profileAutoSelectSubtitle = utils.cast(int, profile.attrib.get('autoSelectSubtitle'))
        self.profileDefaultSubtitleAccessibility = utils.cast(int, profile.attrib.get('defaultSubtitleAccessibility'))
        self.profileDefaultSubtitleForces = utils.cast(int, profile.attrib.get('defaultSubtitleForces'))

        # TODO: Fetch missing MyPlexAccount services
        self.services = None

    @cached_data_property
    def subscriptionFeatures(self):
        subscription = self._data.find('subscription')
        return self.listAttrs(subscription, 'id', rtag='features', etag='feature')

    @cached_data_property
    def entitlements(self):
        return self.listAttrs(self._data, 'id', rtag='entitlements', etag='entitlement')

    @cached_data_property
    def roles(self):
        return self.listAttrs(self._data, 'id', rtag='roles', etag='role')

    @property
    def authenticationToken(self):
        """ Returns the authentication token for the account. Alias for ``authToken``. """
        return self.authToken

    def _reload(self, **kwargs):
        """ Perform the actual reload. """
        data = self.query(self.key)
        self._invalidateCacheAndLoadData(data)
        return self

    def _headers(self, **kwargs):
        """ Returns dict containing base headers for all requests to the server. """
        headers = BASE_HEADERS.copy()
        if self._token:
            headers['X-Plex-Token'] = self._token
        headers.update(kwargs)
        return headers

    def query(self, url, method=None, headers=None, timeout=None, **kwargs):
        method = method or self._session.get
        timeout = timeout or self._timeout
        log.debug('%s %s %s', method.__name__.upper(), url, kwargs.get('json', ''))
        headers = self._headers(**headers or {})
        response = method(url, headers=headers, timeout=timeout, **kwargs)
        if response.status_code not in (200, 201, 204):  # pragma: no cover
            codename = codes.get(response.status_code)[0]
            errtext = response.text.replace('\n', ' ')
            message = f'({response.status_code}) {codename}; {response.url} {errtext}'
            if response.status_code == 401:
                if "verification code" in response.text:
                    raise TwoFactorRequired(message)
                raise Unauthorized(message)
            elif response.status_code == 404:
                raise NotFound(message)
            elif response.status_code == 422 and "Invalid token" in response.text:
                raise Unauthorized(message)
            else:
                raise BadRequest(message)
        if 'application/json' in response.headers.get('Content-Type', ''):
            return response.json()
        elif 'text/plain' in response.headers.get('Content-Type', ''):
            return response.text.strip()
        return utils.parseXMLString(response.text)

    def ping(self):
        """ Ping the Plex.tv API.
            This will refresh the authentication token to prevent it from expiring.
        """
        pong = self.query(self.PING)
        if pong is not None:
            return utils.cast(bool, pong.text)
        return False

    def device(self, name=None, clientId=None):
        """ Returns the :class:`~plexapi.myplex.MyPlexDevice` that matches the name specified.

            Parameters:
                name (str): Name to match against.
                clientId (str): clientIdentifier to match against.
        """
        for device in self.devices():
            if (name and device.name.lower() == name.lower() or device.clientIdentifier == clientId):
                return device
        raise NotFound(f'Unable to find device {name}')

    def devices(self):
        """ Returns a list of all :class:`~plexapi.myplex.MyPlexDevice` objects connected to the server. """
        data = self.query(MyPlexDevice.key)
        return [MyPlexDevice(self, elem) for elem in data]

    def resource(self, name):
        """ Returns the :class:`~plexapi.myplex.MyPlexResource` that matches the name specified.

            Parameters:
                name (str): Name  or machine identifier to match against.
        """
        for resource in self.resources():
            if resource.name.lower() == name.lower() or resource.clientIdentifier == name:
                return resource
        raise NotFound(f'Unable to find resource {name}')

    def resources(self):
        """ Returns a list of all :class:`~plexapi.myplex.MyPlexResource` objects connected to the server. """
        data = self.query(MyPlexResource.key)
        return [MyPlexResource(self, elem) for elem in data]

    def sonos_speakers(self):
        if 'companions_sonos' not in self.subscriptionFeatures:
            return []

        t = time.time()
        if t - self._sonos_cache_timestamp > 5:
            self._sonos_cache_timestamp = t
            data = self.query('https://sonos.plex.tv/resources')
            self._sonos_cache = [PlexSonosClient(self, elem) for elem in data]

        return self._sonos_cache

    def sonos_speaker(self, name):
        return next((x for x in self.sonos_speakers() if x.title.split("+")[0].strip() == name), None)

    def sonos_speaker_by_id(self, identifier):
        return next((x for x in self.sonos_speakers() if x.machineIdentifier.startswith(identifier)), None)

    def inviteFriend(self, user, server, sections=None, allowSync=False, allowCameraUpload=False,
                     allowChannels=False, filterMovies=None, filterTelevision=None, filterMusic=None):
        """ Share library content with the specified user.

            Parameters:
                user (:class:`~plexapi.myplex.MyPlexUser`): `MyPlexUser` object, username, or email
                    of the user to be added.
                server (:class:`~plexapi.server.PlexServer`): `PlexServer` object, or machineIdentifier
                    containing the library sections to share.
                sections (List<:class:`~plexapi.library.LibrarySection`>): List of `LibrarySection` objects, or names
                    to be shared (default None). `sections` must be defined in order to update shared libraries.
                allowSync (Bool): Set True to allow user to sync content.
                allowCameraUpload (Bool): Set True to allow user to upload photos.
                allowChannels (Bool): Set True to allow user to utilize installed channels.
                filterMovies (Dict): Dict containing key 'contentRating' and/or 'label' each set to a list of
                    values to be filtered. ex: `{'contentRating':['G'], 'label':['foo']}`
                filterTelevision (Dict): Dict containing key 'contentRating' and/or 'label' each set to a list of
                    values to be filtered. ex: `{'contentRating':['G'], 'label':['foo']}`
                filterMusic (Dict): Dict containing key 'label' set to a list of values to be filtered.
                    ex: `{'label':['foo']}`
        """
        username = user.username if isinstance(user, MyPlexUser) else user
        machineId = server.machineIdentifier if isinstance(server, PlexServer) else server
        sectionIds = self._getSectionIds(machineId, sections)
        params = {
            'server_id': machineId,
            'shared_server': {'library_section_ids': sectionIds, 'invited_email': username},
            'sharing_settings': {
                'allowSync': ('1' if allowSync else '0'),
                'allowCameraUpload': ('1' if allowCameraUpload else '0'),
                'allowChannels': ('1' if allowChannels else '0'),
                'filterMovies': self._filterDictToStr(filterMovies or {}),
                'filterTelevision': self._filterDictToStr(filterTelevision or {}),
                'filterMusic': self._filterDictToStr(filterMusic or {}),
            },
        }
        headers = {'Content-Type': 'application/json'}
        url = self.FRIENDINVITE.format(machineId=machineId)
        return self.query(url, self._session.post, json=params, headers=headers)

    def createHomeUser(self, user, server, sections=None, allowSync=False, allowCameraUpload=False,
                       allowChannels=False, filterMovies=None, filterTelevision=None, filterMusic=None):
        """ Share library content with the specified user.

            Parameters:
                user (:class:`~plexapi.myplex.MyPlexUser`): `MyPlexUser` object, username, or email
                    of the user to be added.
                server (:class:`~plexapi.server.PlexServer`): `PlexServer` object, or machineIdentifier
                    containing the library sections to share.
                sections (List<:class:`~plexapi.library.LibrarySection`>): List of `LibrarySection` objects, or names
                    to be shared (default None). `sections` must be defined in order to update shared libraries.
                allowSync (Bool): Set True to allow user to sync content.
                allowCameraUpload (Bool): Set True to allow user to upload photos.
                allowChannels (Bool): Set True to allow user to utilize installed channels.
                filterMovies (Dict): Dict containing key 'contentRating' and/or 'label' each set to a list of
                    values to be filtered. ex: `{'contentRating':['G'], 'label':['foo']}`
                filterTelevision (Dict): Dict containing key 'contentRating' and/or 'label' each set to a list of
                    values to be filtered. ex: `{'contentRating':['G'], 'label':['foo']}`
                filterMusic (Dict): Dict containing key 'label' set to a list of values to be filtered.
                    ex: `{'label':['foo']}`
        """
        machineId = server.machineIdentifier if isinstance(server, PlexServer) else server
        sectionIds = self._getSectionIds(server, sections)

        headers = {'Content-Type': 'application/json'}
        url = self.HOMEUSERCREATE.format(title=user)
        # UserID needs to be created and referenced when adding sections
        user_creation = self.query(url, self._session.post, headers=headers)
        userIds = {}
        for elem in user_creation.findall("."):
            # Find userID
            userIds['id'] = elem.attrib.get('id')
        log.debug(userIds)
        params = {
            'server_id': machineId,
            'shared_server': {'library_section_ids': sectionIds, 'invited_id': userIds['id']},
            'sharing_settings': {
                'allowSync': ('1' if allowSync else '0'),
                'allowCameraUpload': ('1' if allowCameraUpload else '0'),
                'allowChannels': ('1' if allowChannels else '0'),
                'filterMovies': self._filterDictToStr(filterMovies or {}),
                'filterTelevision': self._filterDictToStr(filterTelevision or {}),
                'filterMusic': self._filterDictToStr(filterMusic or {}),
            },
        }
        url = self.FRIENDINVITE.format(machineId=machineId)
        library_assignment = self.query(url, self._session.post, json=params, headers=headers)
        return user_creation, library_assignment

    def createExistingUser(self, user, server, sections=None, allowSync=False, allowCameraUpload=False,
                           allowChannels=False, filterMovies=None, filterTelevision=None, filterMusic=None):
        """ Share library content with the specified user.

            Parameters:
                user (:class:`~plexapi.myplex.MyPlexUser`): `MyPlexUser` object, username, or email
                    of the user to be added.
                server (:class:`~plexapi.server.PlexServer`): `PlexServer` object, or machineIdentifier
                    containing the library sections to share.
                sections (List<:class:`~plexapi.library.LibrarySection`>): List of `LibrarySection` objects, or names
                    to be shared (default None). `sections` must be defined in order to update shared libraries.
                allowSync (Bool): Set True to allow user to sync content.
                allowCameraUpload (Bool): Set True to allow user to upload photos.
                allowChannels (Bool): Set True to allow user to utilize installed channels.
                filterMovies (Dict): Dict containing key 'contentRating' and/or 'label' each set to a list of
                    values to be filtered. ex: `{'contentRating':['G'], 'label':['foo']}`
                filterTelevision (Dict): Dict containing key 'contentRating' and/or 'label' each set to a list of
                    values to be filtered. ex: `{'contentRating':['G'], 'label':['foo']}`
                filterMusic (Dict): Dict containing key 'label' set to a list of values to be filtered.
                    ex: `{'label':['foo']}`
        """
        headers = {'Content-Type': 'application/json'}
        # If user already exists, carry over sections and settings.
        if isinstance(user, MyPlexUser):
            username = user.username
        elif user in [_user.username for _user in self.users()]:
            username = self.user(user).username
        else:
            # If user does not already exists, treat request as new request and include sections and settings.
            newUser = user
            url = self.EXISTINGUSER.format(username=newUser)
            user_creation = self.query(url, self._session.post, headers=headers)
            machineId = server.machineIdentifier if isinstance(server, PlexServer) else server
            sectionIds = self._getSectionIds(server, sections)
            params = {
                'server_id': machineId,
                'shared_server': {'library_section_ids': sectionIds, 'invited_email': newUser},
                'sharing_settings': {
                    'allowSync': ('1' if allowSync else '0'),
                    'allowCameraUpload': ('1' if allowCameraUpload else '0'),
                    'allowChannels': ('1' if allowChannels else '0'),
                    'filterMovies': self._filterDictToStr(filterMovies or {}),
                    'filterTelevision': self._filterDictToStr(filterTelevision or {}),
                    'filterMusic': self._filterDictToStr(filterMusic or {}),
                },
            }
            url = self.FRIENDINVITE.format(machineId=machineId)
            library_assignment = self.query(url, self._session.post, json=params, headers=headers)
            return user_creation, library_assignment

        url = self.EXISTINGUSER.format(username=username)
        return self.query(url, self._session.post, headers=headers)

    def removeFriend(self, user):
        """ Remove the specified user from your friends.

            Parameters:
                user (:class:`~plexapi.myplex.MyPlexUser` or str): :class:`~plexapi.myplex.MyPlexUser`,
                    username, or email of the user to be removed.
        """
        user = user if isinstance(user, MyPlexUser) else self.user(user)
        url = self.FRIENDUPDATE.format(userId=user.id)
        return self.query(url, self._session.delete)

    def removeHomeUser(self, user):
        """ Remove the specified user from your home users.

            Parameters:
                user (:class:`~plexapi.myplex.MyPlexUser` or str): :class:`~plexapi.myplex.MyPlexUser`,
                    username, or email of the user to be removed.
        """
        user = user if isinstance(user, MyPlexUser) else self.user(user)
        url = self.HOMEUSER.format(userId=user.id)
        return self.query(url, self._session.delete)

    def switchHomeUser(self, user, pin=None):
        """ Returns a new :class:`~plexapi.myplex.MyPlexAccount` object switched to the given home user.

            Parameters:
                user (:class:`~plexapi.myplex.MyPlexUser` or str): :class:`~plexapi.myplex.MyPlexUser`,
                    username, or email of the home user to switch to.
                pin (str): PIN for the home user (required if the home user has a PIN set).

            Example:

                .. code-block:: python

                    from plexapi.myplex import MyPlexAccount
                    # Login to a Plex Home account
                    account = MyPlexAccount('<USERNAME>', '<PASSWORD>')
                    # Switch to a different Plex Home user
                    userAccount = account.switchHomeUser('Username')

        """
        user = user if isinstance(user, MyPlexUser) else self.user(user)
        url = f'{self.HOMEUSERS}/{user.id}/switch'
        params = {}
        if pin:
            params['pin'] = pin
        data = self.query(url, self._session.post, params=params)
        userToken = data.attrib.get('authenticationToken')
        return MyPlexAccount(token=userToken, session=self._session)

    def setPin(self, newPin, currentPin=None):
        """ Set a new Plex Home PIN for the account.

            Parameters:
                newPin (str): New PIN to set for the account.
                currentPin (str): Current PIN for the account (required to change the PIN).
        """
        url = self.HOMEUSER.format(userId=self.id)
        params = {'pin': newPin}
        if currentPin:
            params['currentPin'] = currentPin
        return self.query(url, self._session.put, params=params)

    def removePin(self, currentPin):
        """ Remove the Plex Home PIN for the account.

            Parameters:
                currentPin (str): Current PIN for the account (required to remove the PIN).
        """
        return self.setPin('', currentPin)

    def setManagedUserPin(self, user, newPin):
        """ Set a new Plex Home PIN for a managed home user. This must be done from the Plex Home admin account.

            Parameters:
                user (:class:`~plexapi.myplex.MyPlexUser` or str): :class:`~plexapi.myplex.MyPlexUser`
                    or username of the managed home user.
                newPin (str): New PIN to set for the managed home user.
        """
        user = user if isinstance(user, MyPlexUser) else self.user(user)
        url = self.MANAGEDHOMEUSER.format(userId=user.id)
        params = {'pin': newPin}
        return self.query(url, self._session.post, params=params)

    def removeManagedUserPin(self, user):
        """ Remove the Plex Home PIN for a managed home user. This must be done from the Plex Home admin account.

            Parameters:
                user (:class:`~plexapi.myplex.MyPlexUser` or str): :class:`~plexapi.myplex.MyPlexUser`
                    or username of the managed home user.
        """
        user = user if isinstance(user, MyPlexUser) else self.user(user)
        url = self.MANAGEDHOMEUSER.format(userId=user.id)
        params = {'removePin': 1}
        return self.query(url, self._session.post, params=params)

    def acceptInvite(self, user):
        """ Accept a pending friend invite from the specified user.

            Parameters:
                user (:class:`~plexapi.myplex.MyPlexInvite` or str): :class:`~plexapi.myplex.MyPlexInvite`,
                    username, or email of the friend invite to accept.
        """
        invite = user if isinstance(user, MyPlexInvite) else self.pendingInvite(user, includeSent=False)
        params = {
            'friend': int(invite.friend),
            'home': int(invite.home),
            'server': int(invite.server)
        }
        url = MyPlexInvite.REQUESTS + f'/{invite.id}' + utils.joinArgs(params)
        return self.query(url, self._session.put)

    def cancelInvite(self, user):
        """ Cancel a pending firend invite for the specified user.

            Parameters:
                user (:class:`~plexapi.myplex.MyPlexInvite` or str): :class:`~plexapi.myplex.MyPlexInvite`,
                    username, or email of the friend invite to cancel.
        """
        invite = user if isinstance(user, MyPlexInvite) else self.pendingInvite(user, includeReceived=False)
        params = {
            'friend': int(invite.friend),
            'home': int(invite.home),
            'server': int(invite.server)
        }
        url = MyPlexInvite.REQUESTED + f'/{invite.id}' + utils.joinArgs(params)
        return self.query(url, self._session.delete)

    def updateFriend(self, user, server, sections=None, removeSections=False, allowSync=None, allowCameraUpload=None,
                     allowChannels=None, filterMovies=None, filterTelevision=None, filterMusic=None):
        """ Update the specified user's share settings.

            Parameters:
                user (:class:`~plexapi.myplex.MyPlexUser`): `MyPlexUser` object, username, or email
                    of the user to be updated.
                server (:class:`~plexapi.server.PlexServer`): `PlexServer` object, or machineIdentifier
                    containing the library sections to share.
                sections (List<:class:`~plexapi.library.LibrarySection`>): List of `LibrarySection` objects, or names
                    to be shared (default None). `sections` must be defined in order to update shared libraries.
                removeSections (Bool): Set True to remove all shares. Supersedes sections.
                allowSync (Bool): Set True to allow user to sync content.
                allowCameraUpload (Bool): Set True to allow user to upload photos.
                allowChannels (Bool): Set True to allow user to utilize installed channels.
                filterMovies (Dict): Dict containing key 'contentRating' and/or 'label' each set to a list of
                    values to be filtered. ex: `{'contentRating':['G'], 'label':['foo']}`
                filterTelevision (Dict): Dict containing key 'contentRating' and/or 'label' each set to a list of
                    values to be filtered. ex: `{'contentRating':['G'], 'label':['foo']}`
                filterMusic (Dict): Dict containing key 'label' set to a list of values to be filtered.
                    ex: `{'label':['foo']}`
        """
        # Update friend servers
        response_filters = ''
        response_servers = ''
        user = user if isinstance(user, MyPlexUser) else self.user(user)
        machineId = server.machineIdentifier if isinstance(server, PlexServer) else server
        sectionIds = self._getSectionIds(machineId, sections)
        headers = {'Content-Type': 'application/json'}
        # Determine whether user has access to the shared server.
        user_servers = [s for s in user.servers if s.machineIdentifier == machineId]
        if user_servers and sectionIds:
            serverId = user_servers[0].id
            params = {'server_id': machineId, 'shared_server': {'library_section_ids': sectionIds}}
            url = self.FRIENDSERVERS.format(machineId=machineId, serverId=serverId)
        else:
            params = {'server_id': machineId,
                      'shared_server': {'library_section_ids': sectionIds, 'invited_id': user.id}}
            url = self.FRIENDINVITE.format(machineId=machineId)
        # Remove share sections, add shares to user without shares, or update shares
        if not user_servers or sectionIds:
            if removeSections is True:
                response_servers = self.query(url, self._session.delete, json=params, headers=headers)
            elif 'invited_id' in params.get('shared_server', ''):
                response_servers = self.query(url, self._session.post, json=params, headers=headers)
            else:
                response_servers = self.query(url, self._session.put, json=params, headers=headers)
        else:
            log.warning('Section name, number of section object is required changing library sections')
        # Update friend filters
        url = self.FRIENDUPDATE.format(userId=user.id)
        params = {}
        if isinstance(allowSync, bool):
            params['allowSync'] = '1' if allowSync else '0'
        if isinstance(allowCameraUpload, bool):
            params['allowCameraUpload'] = '1' if allowCameraUpload else '0'
        if isinstance(allowChannels, bool):
            params['allowChannels'] = '1' if allowChannels else '0'
        if isinstance(filterMovies, dict):
            params['filterMovies'] = self._filterDictToStr(filterMovies or {})  # '1' if allowChannels else '0'
        if isinstance(filterTelevision, dict):
            params['filterTelevision'] = self._filterDictToStr(filterTelevision or {})
        if isinstance(allowChannels, dict):
            params['filterMusic'] = self._filterDictToStr(filterMusic or {})
        if params:
            url += utils.joinArgs(params)
            response_filters = self.query(url, self._session.put)
        return response_servers, response_filters

    def user(self, username):
        """ Returns the :class:`~plexapi.myplex.MyPlexUser` that matches the specified username or email.

            Parameters:
                username (str): Username, email or id of the user to return.
        """
        username = str(username)
        for user in self.users():
            # Home users don't have email, username etc.
            if username.lower() == user.title.lower():
                return user

            elif (user.username and user.email and user.id and username.lower() in
                    (user.username.lower(), user.email.lower(), str(user.id))):
                return user

        raise NotFound(f'Unable to find user {username}')

    def users(self):
        """ Returns a list of all :class:`~plexapi.myplex.MyPlexUser` objects connected to your account.
        """
        elem = self.query(MyPlexUser.key)
        return self.findItems(elem, cls=MyPlexUser)

    def pendingInvite(self, username, includeSent=True, includeReceived=True):
        """ Returns the :class:`~plexapi.myplex.MyPlexInvite` that matches the specified username or email.
            Note: This can be a pending invite sent from your account or received to your account.

            Parameters:
                username (str): Username, email or id of the user to return.
                includeSent (bool): True to include sent invites.
                includeReceived (bool): True to include received invites.
        """
        username = str(username)
        for invite in self.pendingInvites(includeSent, includeReceived):
            if (invite.username and invite.email and invite.id and username.lower() in
                    (invite.username.lower(), invite.email.lower(), str(invite.id))):
                return invite

        raise NotFound(f'Unable to find invite {username}')

    def pendingInvites(self, includeSent=True, includeReceived=True):
        """ Returns a list of all :class:`~plexapi.myplex.MyPlexInvite` objects connected to your account.
            Note: This includes all pending invites sent from your account and received to your account.

            Parameters:
                includeSent (bool): True to include sent invites.
                includeReceived (bool): True to include received invites.
        """
        invites = []
        if includeSent:
            elem = self.query(MyPlexInvite.REQUESTED)
            invites += self.findItems(elem, cls=MyPlexInvite)
        if includeReceived:
            elem = self.query(MyPlexInvite.REQUESTS)
            invites += self.findItems(elem, cls=MyPlexInvite)
        return invites

    def _getSectionIds(self, server, sections):
        """ Converts a list of section objects or names to sectionIds needed for library sharing. """
        if not sections: return []
        # Get a list of all section ids for looking up each section.
        allSectionIds = {}
        machineIdentifier = server.machineIdentifier if isinstance(server, PlexServer) else server
        url = self.PLEXSERVERS.format(machineId=machineIdentifier)
        data = self.query(url, self._session.get)
        for elem in data[0]:
            _id = utils.cast(int, elem.attrib.get('id'))
            _key = utils.cast(int, elem.attrib.get('key'))
            _title = elem.attrib.get('title', '').lower()
            allSectionIds[_id] = _id
            allSectionIds[_key] = _id
            allSectionIds[_title] = _id
        log.debug(allSectionIds)
        # Convert passed in section items to section ids from above lookup
        sectionIds = []
        for section in sections:
            sectionKey = section.key if isinstance(section, LibrarySection) else section.lower()
            sectionIds.append(allSectionIds[sectionKey])
        return sectionIds

    def _filterDictToStr(self, filterDict):
        """ Converts friend filters to a string representation for transport. """
        values = []
        for key, vals in filterDict.items():
            if key not in ('contentRating', 'label', 'contentRating!', 'label!'):
                raise BadRequest(f'Unknown filter key: {key}')
            values.append(f"{key}={'%2C'.join(vals)}")
        return '|'.join(values)

    def addWebhook(self, url):
        # copy _webhooks and append url
        urls = self._webhooks[:] + [url]
        return self.setWebhooks(urls)

    def deleteWebhook(self, url):
        urls = copy.copy(self._webhooks)
        if url not in urls:
            raise BadRequest(f'Webhook does not exist: {url}')
        urls.remove(url)
        return self.setWebhooks(urls)

    def setWebhooks(self, urls):
        log.info('Setting webhooks: %s', urls)
        data = {'urls[]': urls} if len(urls) else {'urls': ''}
        data = self.query(self.WEBHOOKS, self._session.post, data=data)
        self._webhooks = self.listAttrs(data, 'url', etag='webhook')
        return self._webhooks

    def webhooks(self):
        data = self.query(self.WEBHOOKS)
        self._webhooks = self.listAttrs(data, 'url', etag='webhook')
        return self._webhooks

    def optOut(self, playback=None, library=None):
        """ Opt in or out of sharing stuff with plex.
            See: https://www.plex.tv/about/privacy-legal/
        """
        params = {}
        if playback is not None:
            params['optOutPlayback'] = int(playback)
        if library is not None:
            params['optOutLibraryStats'] = int(library)
        url = 'https://plex.tv/api/v2/user/privacy'
        return self.query(url, method=self._session.put, data=params)

    def syncItems(self, client=None, clientId=None):
        """ Returns an instance of :class:`~plexapi.sync.SyncList` for specified client.

            Parameters:
                client (:class:`~plexapi.myplex.MyPlexDevice`): a client to query SyncItems for.
                clientId (str): an identifier of a client to query SyncItems for.

            If both `client` and `clientId` provided the client would be preferred.
            If neither `client` nor `clientId` provided the clientId would be set to current clients's identifier.
        """
        if client:
            clientId = client.clientIdentifier
        elif clientId is None:
            clientId = X_PLEX_IDENTIFIER

        data = self.query(SyncList.key.format(clientId=clientId))

        return SyncList(self, data)

    def sync(self, sync_item, client=None, clientId=None):
        """ Adds specified sync item for the client. It's always easier to use methods defined directly in the media
            objects, e.g. :func:`~plexapi.video.Video.sync`, :func:`~plexapi.audio.Audio.sync`.

            Parameters:
                client (:class:`~plexapi.myplex.MyPlexDevice`): a client for which you need to add SyncItem to.
                clientId (str): an identifier of a client for which you need to add SyncItem to.
                sync_item (:class:`~plexapi.sync.SyncItem`): prepared SyncItem object with all fields set.

            If both `client` and `clientId` provided the client would be preferred.
            If neither `client` nor `clientId` provided the clientId would be set to current clients's identifier.

            Returns:
                :class:`~plexapi.sync.SyncItem`: an instance of created syncItem.

            Raises:
                :exc:`~plexapi.exceptions.BadRequest`: When client with provided clientId wasn't found.
                :exc:`~plexapi.exceptions.BadRequest`: Provided client doesn't provides `sync-target`.
        """
        if not client and not clientId:
            clientId = X_PLEX_IDENTIFIER

        if not client:
            for device in self.devices():
                if device.clientIdentifier == clientId:
                    client = device
                    break

            if not client:
                raise BadRequest(f'Unable to find client by clientId={clientId}')

        if 'sync-target' not in client.provides:
            raise BadRequest("Received client doesn't provides sync-target")

        params = {
            'SyncItem[title]': sync_item.title,
            'SyncItem[rootTitle]': sync_item.rootTitle,
            'SyncItem[metadataType]': sync_item.metadataType,
            'SyncItem[machineIdentifier]': sync_item.machineIdentifier,
            'SyncItem[contentType]': sync_item.contentType,
            'SyncItem[Policy][scope]': sync_item.policy.scope,
            'SyncItem[Policy][unwatched]': str(int(sync_item.policy.unwatched)),
            'SyncItem[Policy][value]': str(sync_item.policy.value if hasattr(sync_item.policy, 'value') else 0),
            'SyncItem[Location][uri]': sync_item.location,
            'SyncItem[MediaSettings][audioBoost]': str(sync_item.mediaSettings.audioBoost),
            'SyncItem[MediaSettings][maxVideoBitrate]': str(sync_item.mediaSettings.maxVideoBitrate),
            'SyncItem[MediaSettings][musicBitrate]': str(sync_item.mediaSettings.musicBitrate),
            'SyncItem[MediaSettings][photoQuality]': str(sync_item.mediaSettings.photoQuality),
            'SyncItem[MediaSettings][photoResolution]': sync_item.mediaSettings.photoResolution,
            'SyncItem[MediaSettings][subtitleSize]': str(sync_item.mediaSettings.subtitleSize),
            'SyncItem[MediaSettings][videoQuality]': str(sync_item.mediaSettings.videoQuality),
            'SyncItem[MediaSettings][videoResolution]': sync_item.mediaSettings.videoResolution,
        }

        url = SyncList.key.format(clientId=client.clientIdentifier)
        data = self.query(url, method=self._session.post, params=params)

        return SyncItem(self, data, None, clientIdentifier=client.clientIdentifier)

    def claimToken(self):
        """ Returns a str, a new "claim-token", which you can use to register your new Plex Server instance to your
            account.
            See: https://hub.docker.com/r/plexinc/pms-docker/, https://www.plex.tv/claim/
        """
        response = self._session.get('https://plex.tv/api/claim/token.json', headers=self._headers(), timeout=TIMEOUT)
        if response.status_code not in (200, 201, 204):  # pragma: no cover
            codename = codes.get(response.status_code)[0]
            errtext = response.text.replace('\n', ' ')
            raise BadRequest(f'({response.status_code}) {codename} {response.url}; {errtext}')
        return response.json()['token']

    def history(self, maxresults=None, mindate=None):
        """ Get Play History for all library sections on all servers for the owner.

            Parameters:
                maxresults (int): Only return the specified number of results (optional).
                mindate (datetime): Min datetime to return results from.
        """
        servers = [x for x in self.resources() if x.provides == 'server' and x.owned]
        hist = []
        for server in servers:
            conn = server.connect()
            hist.extend(conn.history(maxresults=maxresults, mindate=mindate, accountID=1))
        return hist

    def onlineMediaSources(self):
        """ Returns a list of user account Online Media Sources settings :class:`~plexapi.myplex.AccountOptOut`
        """
        url = self.OPTOUTS.format(userUUID=self.uuid)
        elem = self.query(url)
        return self.findItems(elem, cls=AccountOptOut, etag='optOut')

    def videoOnDemand(self):
        """ Returns a list of VOD Hub items :class:`~plexapi.library.Hub`
        """
        data = self.query(f'{self.VOD}/hubs')
        return self.findItems(data)

    def tidal(self):
        """ Returns a list of tidal Hub items :class:`~plexapi.library.Hub`
        """
        data = self.query(f'{self.MUSIC}/hubs')
        return self.findItems(data)

    def watchlist(self, filter=None, sort=None, libtype=None, maxresults=None, **kwargs):
        """ Returns a list of :class:`~plexapi.video.Movie` and :class:`~plexapi.video.Show` items in the user's watchlist.
            Note: The objects returned are from Plex's online metadata. To get the matching item on a Plex server,
            search for the media using the guid.

            Parameters:
                filter (str, optional): 'available' or 'released' to only return items that are available or released,
                    otherwise return all items.
                sort (str, optional): In the format ``field:dir``. Available fields are ``watchlistedAt`` (Added At),
                    ``titleSort`` (Title), ``originallyAvailableAt`` (Release Date), or ``rating`` (Critic Rating).
                    ``dir`` can be ``asc`` or ``desc``.
                libtype (str, optional): 'movie' or 'show' to only return movies or shows, otherwise return all items.
                maxresults (int, optional): Only return the specified number of results.
                **kwargs (dict): Additional custom filters to apply to the search results.


            Example:

                .. code-block:: python

                    # Watchlist for released movies sorted by critic rating in descending order
                    watchlist = account.watchlist(filter='released', sort='rating:desc', libtype='movie')
                    item = watchlist[0]  # First item in the watchlist

                    # Search for the item on a Plex server
                    result = plex.library.search(guid=item.guid, libtype=item.type)

        """
        params = {
            'includeCollections': 1,
            'includeExternalMedia': 1
        }

        if not filter:
            filter = 'all'
        if sort:
            params['sort'] = sort
        if libtype:
            params['type'] = utils.searchType(libtype)

        params.update(kwargs)

        key = f'{self.DISCOVER}/library/sections/watchlist/{filter}{utils.joinArgs(params)}'
        return self._toOnlineMetadata(self.fetchItems(key, maxresults=maxresults), **kwargs)

    def onWatchlist(self, item):
        """ Returns True if the item is on the user's watchlist.

            Parameters:
                item (:class:`~plexapi.video.Movie` or :class:`~plexapi.video.Show`): Item to check
                    if it is on the user's watchlist.
        """
        return bool(self.userState(item).watchlistedAt)

    def addToWatchlist(self, items):
        """ Add media items to the user's watchlist

            Parameters:
                items (List): List of :class:`~plexapi.video.Movie` or :class:`~plexapi.video.Show`
                    objects to be added to the watchlist.

            Raises:
                :exc:`~plexapi.exceptions.BadRequest`: When trying to add invalid or existing
                    media to the watchlist.
        """
        if not isinstance(items, list):
            items = [items]

        for item in items:
            if self.onWatchlist(item):
                raise BadRequest(f'"{item.title}" is already on the watchlist')
            ratingKey = item.guid.rsplit('/', 1)[-1]
            self.query(f'{self.DISCOVER}/actions/addToWatchlist?ratingKey={ratingKey}', method=self._session.put)
        return self

    def removeFromWatchlist(self, items):
        """ Remove media items from the user's watchlist

            Parameters:
                items (List): List of :class:`~plexapi.video.Movie` or :class:`~plexapi.video.Show`
                    objects to be added to the watchlist.

            Raises:
                :exc:`~plexapi.exceptions.BadRequest`: When trying to remove invalid or non-existing
                    media to the watchlist.
        """
        if not isinstance(items, list):
            items = [items]

        for item in items:
            if not self.onWatchlist(item):
                raise BadRequest(f'"{item.title}" is not on the watchlist')
            ratingKey = item.guid.rsplit('/', 1)[-1]
            self.query(f'{self.DISCOVER}/actions/removeFromWatchlist?ratingKey={ratingKey}', method=self._session.put)
        return self

    def userState(self, item):
        """ Returns a :class:`~plexapi.myplex.UserState` object for the specified item.

            Parameters:
                item (:class:`~plexapi.video.Movie` or :class:`~plexapi.video.Show`): Item to return the user state.
        """
        ratingKey = item.guid.rsplit('/', 1)[-1]
        data = self.query(f"{self.METADATA}/library/metadata/{ratingKey}/userState")
        return self.findItem(data, cls=UserState)

    def isPlayed(self, item):
        """ Return True if the item is played on Discover.

            Parameters:
                item (:class:`~plexapi.video.Movie`,
                :class:`~plexapi.video.Show`, :class:`~plexapi.video.Season` or
                :class:`~plexapi.video.Episode`): Object from searchDiscover().
                Can be also result from Plex Movie or Plex TV Series agent.
        """
        userState = self.userState(item)
        return bool(userState.viewCount > 0) if userState.viewCount else False

    def markPlayed(self, item):
        """ Mark the Plex object as played on Discover.

            Parameters:
                item (:class:`~plexapi.video.Movie`,
                :class:`~plexapi.video.Show`, :class:`~plexapi.video.Season` or
                :class:`~plexapi.video.Episode`): Object from searchDiscover().
                Can be also result from Plex Movie or Plex TV Series agent.
        """
        key = f'{self.METADATA}/actions/scrobble'
        ratingKey = item.guid.rsplit('/', 1)[-1]
        params = {'key': ratingKey, 'identifier': 'com.plexapp.plugins.library'}
        self.query(key, params=params)
        return self

    def markUnplayed(self, item):
        """ Mark the Plex object as unplayed on Discover.

            Parameters:
                item (:class:`~plexapi.video.Movie`,
                :class:`~plexapi.video.Show`, :class:`~plexapi.video.Season` or
                :class:`~plexapi.video.Episode`): Object from searchDiscover().
                Can be also result from Plex Movie or Plex TV Series agent.
        """
        key = f'{self.METADATA}/actions/unscrobble'
        ratingKey = item.guid.rsplit('/', 1)[-1]
        params = {'key': ratingKey, 'identifier': 'com.plexapp.plugins.library'}
        self.query(key, params=params)
        return self

    def searchDiscover(self, query, limit=30, libtype=None, providers='discover'):
        """ Search for movies and TV shows in Discover.
            Returns a list of :class:`~plexapi.video.Movie` and :class:`~plexapi.video.Show` objects.

            Parameters:
                query (str): Search query.
                limit (int, optional): Limit to the specified number of results. Default 30.
                libtype (str, optional): 'movie' or 'show' to only return movies or shows, otherwise return all items.
                providers (str, optional): 'discover' for default behavior
                    or 'discover,PLEXAVOD' to also include the Plex ad-suported video service
                    or 'discover,PLEXAVOD,PLEXTVOD' to also include the Plex video rental service
        """
        libtypes = {'movie': 'movies', 'show': 'tv'}
        libtype = libtypes.get(libtype, 'movies,tv')

        headers = {
            'Accept': 'application/json'
        }
        params = {
            'query': query,
            'limit': limit,
            'searchTypes': libtype,
            'searchProviders': providers,
            'includeMetadata': 1
        }

        data = self.query(f'{self.DISCOVER}/library/search', headers=headers, params=params)
        searchResults = data['MediaContainer'].get('SearchResults', [])
        searchResult = next((s.get('SearchResult', []) for s in searchResults if s.get('id') == 'external'), [])

        results = []
        for result in searchResult:
            metadata = result['Metadata']
            type = metadata['type']
            if type == 'movie':
                tag = 'Video'
            elif type == 'show':
                tag = 'Directory'
            else:
                continue
            attrs = ''.join(f'{k}="{html.escape(str(v))}" ' for k, v in metadata.items())
            xml = f'<{tag} {attrs}/>'
            results.append(self._manuallyLoadXML(xml))

        return self._toOnlineMetadata(results)

    @property
    def viewStateSync(self):
        """ Returns True or False if syncing of watch state and ratings
            is enabled or disabled, respectively, for the account.
        """
        headers = {'Accept': 'application/json'}
        data = self.query(self.VIEWSTATESYNC, headers=headers)
        return data.get('consent')

    def enableViewStateSync(self):
        """ Enable syncing of watch state and ratings for the account. """
        self._updateViewStateSync(True)

    def disableViewStateSync(self):
        """ Disable syncing of watch state and ratings for the account. """
        self._updateViewStateSync(False)

    def _updateViewStateSync(self, consent):
        """ Enable or disable syncing of watch state and ratings for the account.

            Parameters:
                consent (bool): True to enable, False to disable.
        """
        params = {'consent': consent}
        self.query(self.VIEWSTATESYNC, method=self._session.put, params=params)

    def link(self, pin):
        """ Link a device to the account using a pin code.

            Parameters:
                pin (str): The 4 digit link pin code.
        """
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-Plex-Product': 'Plex SSO'
        }
        data = {'code': pin}
        self.query(self.LINK, self._session.put, headers=headers, data=data)

    def _toOnlineMetadata(self, objs, **kwargs):
        """ Convert a list of media objects to online metadata objects. """
        # TODO: Add proper support for metadata.provider.plex.tv
        # Temporary workaround to allow reloading and browsing of online media objects
        server = PlexServer(self.METADATA, self._token, session=self._session)

        includeUserState = int(bool(kwargs.pop('includeUserState', True)))

        if not isinstance(objs, list):
            objs = [objs]

        for obj in objs:
            obj._server = server

            # Parse details key to modify query string
            url = urlsplit(obj._details_key)
            query = dict(parse_qsl(url.query))
            query['includeUserState'] = includeUserState
            query.pop('includeFields', None)
            obj._details_key = urlunsplit((url.scheme, url.netloc, url.path, urlencode(query), url.fragment))

        return objs

    def publicIP(self):
        """ Returns your public IP address. """
        return self.query('https://plex.tv/:/ip')

    def geoip(self, ip_address):
        """ Returns a :class:`~plexapi.myplex.GeoLocation` object with geolocation information
            for an IP address using Plex's GeoIP database.

            Parameters:
                ip_address (str): IP address to lookup.
        """
        params = {'ip_address': ip_address}
        data = self.query('https://plex.tv/api/v2/geoip', params=params)
        return GeoLocation(self, data)


class MyPlexUser(PlexObject):
    """ This object represents non-signed in users such as friends and linked
        accounts. NOTE: This should not be confused with the :class:`~plexapi.myplex.MyPlexAccount`
        which is your specific account. The raw xml for the data presented here
        can be found at: https://plex.tv/api/users/

        Attributes:
            TAG (str): 'User'
            key (str): 'https://plex.tv/api/users/'
            allowCameraUpload (bool): True if this user can upload images.
            allowChannels (bool): True if this user has access to channels.
            allowSync (bool): True if this user can sync.
            email (str): User's email address (user@gmail.com).
            filterAll (str): Unknown.
            filterMovies (str): Unknown.
            filterMusic (str): Unknown.
            filterPhotos (str): Unknown.
            filterTelevision (str): Unknown.
            home (bool): Unknown.
            id (int): User's Plex account ID.
            protected (False): Unknown (possibly SSL enabled?).
            recommendationsPlaylistId (str): Unknown.
            restricted (str): Unknown.
            servers (List<:class:`~plexapi.myplex.<MyPlexServerShare`>)): Servers shared with the user.
            thumb (str): Link to the users avatar.
            title (str): Seems to be an alias for username.
            username (str): User's username.
    """
    TAG = 'User'
    key = 'https://plex.tv/api/users/'

    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        self.friend = self._initpath == self.key
        self.allowCameraUpload = utils.cast(bool, data.attrib.get('allowCameraUpload'))
        self.allowChannels = utils.cast(bool, data.attrib.get('allowChannels'))
        self.allowSync = utils.cast(bool, data.attrib.get('allowSync'))
        self.email = data.attrib.get('email')
        self.filterAll = data.attrib.get('filterAll')
        self.filterMovies = data.attrib.get('filterMovies')
        self.filterMusic = data.attrib.get('filterMusic')
        self.filterPhotos = data.attrib.get('filterPhotos')
        self.filterTelevision = data.attrib.get('filterTelevision')
        self.home = utils.cast(bool, data.attrib.get('home'))
        self.id = utils.cast(int, data.attrib.get('id'))
        self.protected = utils.cast(bool, data.attrib.get('protected'))
        self.recommendationsPlaylistId = data.attrib.get('recommendationsPlaylistId')
        self.restricted = data.attrib.get('restricted')
        self.thumb = data.attrib.get('thumb')
        self.title = data.attrib.get('title', '')
        self.username = data.attrib.get('username', '')
        for server in self.servers:
            server.accountID = self.id

    @cached_data_property
    def servers(self):
        return self.findItems(self._data, MyPlexServerShare)

    def get_token(self, machineIdentifier):
        try:
            for item in self._server.query(self._server.FRIENDINVITE.format(machineId=machineIdentifier)):
                if utils.cast(int, item.attrib.get('userID')) == self.id:
                    return item.attrib.get('accessToken')
        except Exception:
            log.exception('Failed to get access token for %s', self.title)

    def server(self, name):
        """ Returns the :class:`~plexapi.myplex.MyPlexServerShare` that matches the name specified.

            Parameters:
                name (str): Name of the server to return.
        """
        for server in self.servers:
            if name.lower() == server.name.lower():
                return server

        raise NotFound(f'Unable to find server {name}')

    def history(self, maxresults=None, mindate=None):
        """ Get all Play History for a user in all shared servers.
            Parameters:
                maxresults (int): Only return the specified number of results (optional).
                mindate (datetime): Min datetime to return results from.
        """
        hist = []
        for server in self.servers:
            hist.extend(server.history(maxresults=maxresults, mindate=mindate))
        return hist


class MyPlexInvite(PlexObject):
    """ This object represents pending friend invites.

        Attributes:
            TAG (str): 'Invite'
            createdAt (datetime): Datetime the user was invited.
            email (str): User's email address (user@gmail.com).
            friend (bool): True or False if the user is invited as a friend.
            friendlyName (str): The user's friendly name.
            home (bool): True or False if the user is invited to a Plex Home.
            id (int): User's Plex account ID.
            server (bool): True or False if the user is invited to any servers.
            servers (List<:class:`~plexapi.myplex.<MyPlexServerShare`>)): Servers shared with the user.
            thumb (str): Link to the users avatar.
            username (str): User's username.
    """
    TAG = 'Invite'
    REQUESTS = 'https://plex.tv/api/invites/requests'
    REQUESTED = 'https://plex.tv/api/invites/requested'

    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        self.createdAt = utils.toDatetime(data.attrib.get('createdAt'))
        self.email = data.attrib.get('email')
        self.friend = utils.cast(bool, data.attrib.get('friend'))
        self.friendlyName = data.attrib.get('friendlyName')
        self.home = utils.cast(bool, data.attrib.get('home'))
        self.id = utils.cast(int, data.attrib.get('id'))
        self.server = utils.cast(bool, data.attrib.get('server'))
        self.thumb = data.attrib.get('thumb')
        self.username = data.attrib.get('username', '')
        for server in self.servers:
            server.accountID = self.id

    @cached_data_property
    def servers(self):
        return self.findItems(self._data, MyPlexServerShare)


class Section(PlexObject):
    """ This refers to a shared section. The raw xml for the data presented here
        can be found at: https://plex.tv/api/servers/{machineId}/shared_servers

        Attributes:
            TAG (str): section
            id (int): The shared section ID
            key (int): The shared library section key
            shared (bool): If this section is shared with the user
            title (str): Title of the section
            type (str): movie, tvshow, artist

    """
    TAG = 'Section'

    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        self.id = utils.cast(int, data.attrib.get('id'))
        self.key = utils.cast(int, data.attrib.get('key'))
        self.shared = utils.cast(bool, data.attrib.get('shared', '0'))
        self.title = data.attrib.get('title')
        self.type = data.attrib.get('type')
        self.sectionId = self.id  # For backwards compatibility
        self.sectionKey = self.key  # For backwards compatibility

    def history(self, maxresults=None, mindate=None):
        """ Get all Play History for a user for this section in this shared server.
            Parameters:
                maxresults (int): Only return the specified number of results (optional).
                mindate (datetime): Min datetime to return results from.
        """
        server = self._server._server.resource(self._server.name).connect()
        return server.history(maxresults=maxresults, mindate=mindate,
                              accountID=self._server.accountID, librarySectionID=self.sectionKey)


class MyPlexServerShare(PlexObject):
    """ Represents a single user's server reference. Used for library sharing.

        Attributes:
            id (int): id for this share
            serverId (str): what id plex uses for this.
            machineIdentifier (str): The servers machineIdentifier
            name (str): The servers name
            lastSeenAt (datetime): Last connected to the server?
            numLibraries (int): Total number of libraries
            allLibraries (bool): True if all libraries is shared with this user.
            owned (bool): 1 if the server is owned by the user
            pending (bool): True if the invite is pending.

    """
    TAG = 'Server'

    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        self.id = utils.cast(int, data.attrib.get('id'))
        self.accountID = utils.cast(int, data.attrib.get('accountID'))
        self.serverId = utils.cast(int, data.attrib.get('serverId'))
        self.machineIdentifier = data.attrib.get('machineIdentifier')
        self.name = data.attrib.get('name')
        self.lastSeenAt = utils.toDatetime(data.attrib.get('lastSeenAt'))
        self.numLibraries = utils.cast(int, data.attrib.get('numLibraries'))
        self.allLibraries = utils.cast(bool, data.attrib.get('allLibraries'))
        self.owned = utils.cast(bool, data.attrib.get('owned'))
        self.pending = utils.cast(bool, data.attrib.get('pending'))

    def section(self, name):
        """ Returns the :class:`~plexapi.myplex.Section` that matches the name specified.

            Parameters:
                name (str): Name of the section to return.
        """
        for section in self.sections():
            if name.lower() == section.title.lower():
                return section

        raise NotFound(f'Unable to find section {name}')

    def sections(self):
        """ Returns a list of all :class:`~plexapi.myplex.Section` objects shared with this user.
        """
        url = MyPlexAccount.FRIENDSERVERS.format(machineId=self.machineIdentifier, serverId=self.id)
        data = self._server.query(url)
        return self.findItems(data, Section, rtag='SharedServer')

    def history(self, maxresults=9999999, mindate=None):
        """ Get all Play History for a user in this shared server.
            Parameters:
                maxresults (int): Only return the specified number of results (optional).
                mindate (datetime): Min datetime to return results from.
        """
        server = self._server.resource(self.name).connect()
        return server.history(maxresults=maxresults, mindate=mindate, accountID=self.accountID)


class MyPlexResource(PlexObject):
    """ This object represents resources connected to your Plex server that can provide
        content such as Plex Media Servers, iPhone or Android clients, etc. The raw xml
        for the data presented here can be found at:
        https://plex.tv/api/v2/resources?includeHttps=1&includeRelay=1

        Attributes:
            TAG (str): 'Device'
            key (str): 'https://plex.tv/api/v2/resources?includeHttps=1&includeRelay=1'
            accessToken (str): This resource's Plex access token.
            clientIdentifier (str): Unique ID for this resource.
            connections (list): List of :class:`~plexapi.myplex.ResourceConnection` objects
                for this resource.
            createdAt (datetime): Timestamp this resource first connected to your server.
            device (str): Best guess on the type of device this is (PS, iPhone, Linux, etc).
            dnsRebindingProtection (bool): True if the server had DNS rebinding protection.
            home (bool): Unknown
            httpsRequired (bool): True if the resource requires https.
            lastSeenAt (datetime): Timestamp this resource last connected.
            name (str): Descriptive name of this resource.
            natLoopbackSupported (bool): True if the resource supports NAT loopback.
            owned (bool): True if this resource is one of your own (you logged into it).
            ownerId (int): ID of the user that owns this resource (shared resources only).
            platform (str): OS the resource is running (Linux, Windows, Chrome, etc.)
            platformVersion (str): Version of the platform.
            presence (bool): True if the resource is online
            product (str): Plex product (Plex Media Server, Plex for iOS, Plex Web, etc.)
            productVersion (str): Version of the product.
            provides (str): List of services this resource provides (client, server,
                player, pubsub-player, etc.)
            publicAddressMatches (bool): True if the public IP address matches the client's public IP address.
            relay (bool): True if this resource has the Plex Relay enabled.
            sourceTitle (str): Username of the user that owns this resource (shared resources only).
            synced (bool): Unknown (possibly True if the resource has synced content?)
    """
    TAG = 'resource'
    key = 'https://plex.tv/api/v2/resources?includeHttps=1&includeRelay=1'

    # Default order to prioritize available resource connections
    DEFAULT_LOCATION_ORDER = ['local', 'remote', 'relay']
    DEFAULT_SCHEME_ORDER = ['https', 'http']

    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        self.accessToken = logfilter.add_secret(data.attrib.get('accessToken'))
        self.clientIdentifier = data.attrib.get('clientIdentifier')
        self.createdAt = utils.toDatetime(data.attrib.get('createdAt'), "%Y-%m-%dT%H:%M:%SZ")
        self.device = data.attrib.get('device')
        self.dnsRebindingProtection = utils.cast(bool, data.attrib.get('dnsRebindingProtection'))
        self.home = utils.cast(bool, data.attrib.get('home'))
        self.httpsRequired = utils.cast(bool, data.attrib.get('httpsRequired'))
        self.lastSeenAt = utils.toDatetime(data.attrib.get('lastSeenAt'), "%Y-%m-%dT%H:%M:%SZ")
        self.name = data.attrib.get('name')
        self.natLoopbackSupported = utils.cast(bool, data.attrib.get('natLoopbackSupported'))
        self.owned = utils.cast(bool, data.attrib.get('owned'))
        self.ownerId = utils.cast(int, data.attrib.get('ownerId', 0))
        self.platform = data.attrib.get('platform')
        self.platformVersion = data.attrib.get('platformVersion')
        self.presence = utils.cast(bool, data.attrib.get('presence'))
        self.product = data.attrib.get('product')
        self.productVersion = data.attrib.get('productVersion')
        self.provides = data.attrib.get('provides')
        self.publicAddressMatches = utils.cast(bool, data.attrib.get('publicAddressMatches'))
        self.relay = utils.cast(bool, data.attrib.get('relay'))
        self.sourceTitle = data.attrib.get('sourceTitle')
        self.synced = utils.cast(bool, data.attrib.get('synced'))

    @cached_data_property
    def connections(self):
        return self.findItems(self._data, ResourceConnection, rtag='connections')

    def preferred_connections(
        self,
        ssl=None,
        locations=None,
        schemes=None,
    ):
        """ Returns a sorted list of the available connection addresses for this resource.
            Often times there is more than one address specified for a server or client.
            Default behavior will prioritize local connections before remote or relay and HTTPS before HTTP.

            Parameters:
                ssl (bool, optional): Set True to only connect to HTTPS connections. Set False to
                    only connect to HTTP connections. Set None (default) to connect to any
                    HTTP or HTTPS connection.
        """
        if locations is None:
            locations = self.DEFAULT_LOCATION_ORDER[:]
        if schemes is None:
            schemes = self.DEFAULT_SCHEME_ORDER[:]

        connections_dict = {location: {scheme: [] for scheme in schemes} for location in locations}
        for connection in self.connections:
            # Only check non-local connections unless we own the resource
            if self.owned or (not self.owned and not connection.local):
                location = 'relay' if connection.relay else ('local' if connection.local else 'remote')
                if location not in locations:
                    continue
                if 'http' in schemes:
                    connections_dict[location]['http'].append(connection.httpuri)
                if 'https' in schemes:
                    connections_dict[location]['https'].append(connection.uri)
        if ssl is True: schemes.remove('http')
        elif ssl is False: schemes.remove('https')
        connections = []
        for location in locations:
            for scheme in schemes:
                connections.extend(connections_dict[location][scheme])
        return connections

    def connect(
        self,
        ssl=None,
        timeout=None,
        locations=None,
        schemes=None,
    ):
        """ Returns a new :class:`~plexapi.server.PlexServer` or :class:`~plexapi.client.PlexClient` object.
            Uses `MyPlexResource.preferred_connections()` to generate the priority order of connection addresses.
            After trying to connect to all available addresses for this resource and
            assuming at least one connection was successful, the PlexServer object is built and returned.

            Parameters:
                ssl (bool, optional): Set True to only connect to HTTPS connections. Set False to
                    only connect to HTTP connections. Set None (default) to connect to any
                    HTTP or HTTPS connection.
                timeout (int, optional): The timeout in seconds to attempt each connection.

            Raises:
                :exc:`~plexapi.exceptions.NotFound`: When unable to connect to any addresses for this resource.
        """
        if locations is None:
            locations = self.DEFAULT_LOCATION_ORDER[:]
        if schemes is None:
            schemes = self.DEFAULT_SCHEME_ORDER[:]

        connections = self.preferred_connections(ssl, locations, schemes)
        # Try connecting to all known resource connections in parallel, but
        # only return the first server (in order) that provides a response.
        cls = PlexServer if 'server' in self.provides else PlexClient
        listargs = [[cls, url, self.accessToken, self._server._session, timeout] for url in connections]
        log.debug('Testing %s resource connections..', len(listargs))
        results = utils.threaded(_connect, listargs)
        return _chooseConnection('Resource', self.name, results)


class ResourceConnection(PlexObject):
    """ Represents a Resource Connection object found within the
        :class:`~plexapi.myplex.MyPlexResource` objects.

        Attributes:
            TAG (str): 'Connection'
            address (str): The connection IP address
            httpuri (str): Full HTTP URL
            ipv6 (bool): True if the address is IPv6
            local (bool): True if the address is local
            port (int): The connection port
            protocol (str): HTTP or HTTPS
            relay (bool): True if the address uses the Plex Relay
            uri (str): Full connetion URL
    """
    TAG = 'connection'

    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        self.address = data.attrib.get('address')
        self.ipv6 = utils.cast(bool, data.attrib.get('IPv6'))
        self.local = utils.cast(bool, data.attrib.get('local'))
        self.port = utils.cast(int, data.attrib.get('port'))
        self.protocol = data.attrib.get('protocol')
        self.relay = utils.cast(bool, data.attrib.get('relay'))
        self.uri = data.attrib.get('uri')
        self.httpuri = f'http://{self.address}:{self.port}'


class MyPlexDevice(PlexObject):
    """ This object represents resources connected to your Plex server that provide
        playback ability from your Plex Server, iPhone or Android clients, Plex Web,
        this API, etc. The raw xml for the data presented here can be found at:
        https://plex.tv/devices.xml

        Attributes:
            TAG (str): 'Device'
            key (str): 'https://plex.tv/devices.xml'
            clientIdentifier (str): Unique ID for this resource.
            connections (list): List of connection URIs for the device.
            device (str): Best guess on the type of device this is (Linux, iPad, AFTB, etc).
            id (str): MyPlex ID of the device.
            model (str): Model of the device (bueller, Linux, x86_64, etc.)
            name (str): Hostname of the device.
            platform (str): OS the resource is running (Linux, Windows, Chrome, etc.)
            platformVersion (str): Version of the platform.
            product (str): Plex product (Plex Media Server, Plex for iOS, Plex Web, etc.)
            productVersion (string): Version of the product.
            provides (str): List of services this resource provides (client, controller,
                sync-target, player, pubsub-player).
            publicAddress (str): Public IP address.
            screenDensity (str): Unknown
            screenResolution (str): Screen resolution (750x1334, 1242x2208, etc.)
            token (str): Plex authentication token for the device.
            vendor (str): Device vendor (ubuntu, etc).
            version (str): Unknown (1, 2, 1.3.3.3148-b38628e, 1.3.15, etc.)
    """
    TAG = 'Device'
    key = 'https://plex.tv/devices.xml'

    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        self.name = data.attrib.get('name')
        self.publicAddress = data.attrib.get('publicAddress')
        self.product = data.attrib.get('product')
        self.productVersion = data.attrib.get('productVersion')
        self.platform = data.attrib.get('platform')
        self.platformVersion = data.attrib.get('platformVersion')
        self.device = data.attrib.get('device')
        self.model = data.attrib.get('model')
        self.vendor = data.attrib.get('vendor')
        self.provides = data.attrib.get('provides')
        self.clientIdentifier = data.attrib.get('clientIdentifier')
        self.version = data.attrib.get('version')
        self.id = data.attrib.get('id')
        self.token = logfilter.add_secret(data.attrib.get('token'))
        self.screenResolution = data.attrib.get('screenResolution')
        self.screenDensity = data.attrib.get('screenDensity')
        self.createdAt = utils.toDatetime(data.attrib.get('createdAt'))
        self.lastSeenAt = utils.toDatetime(data.attrib.get('lastSeenAt'))

    @cached_data_property
    def connections(self):
        return self.listAttrs(self._data, 'uri', etag='Connection')

    def connect(self, timeout=None):
        """ Returns a new :class:`~plexapi.client.PlexClient` or :class:`~plexapi.server.PlexServer`
            Sometimes there is more than one address specified for a server or client.
            After trying to connect to all available addresses for this client and assuming
            at least one connection was successful, the PlexClient object is built and returned.

            Raises:
                :exc:`~plexapi.exceptions.NotFound`: When unable to connect to any addresses for this device.
        """
        cls = PlexServer if 'server' in self.provides else PlexClient
        listargs = [[cls, url, self.token, self._server._session, timeout] for url in self.connections]
        log.debug('Testing %s device connections..', len(listargs))
        results = utils.threaded(_connect, listargs)
        return _chooseConnection('Device', self.name, results)

    def delete(self):
        """ Remove this device from your account. """
        key = f'https://plex.tv/devices/{self.id}.xml'
        self._server.query(key, self._server._session.delete)

    def syncItems(self):
        """ Returns an instance of :class:`~plexapi.sync.SyncList` for current device.

            Raises:
                :exc:`~plexapi.exceptions.BadRequest`: when the device doesn't provides `sync-target`.
        """
        if 'sync-target' not in self.provides:
            raise BadRequest('Requested syncList for device which do not provides sync-target')

        return self._server.syncItems(client=self)


class MyPlexPinLogin:
    """
        MyPlex PIN login class which supports getting a token for authenticating the client and
        providing an access token to create a :class:`~plexapi.myplex.MyPlexAccount` instance.
        The login can be done using the four character PIN which the user must enter at
        https://plex.tv/link or using Plex OAuth.

        This helper class supports a polling, threaded and callback approach.

        - The polling approach expects the developer to periodically check if the PIN login was
          successful using :func:`~plexapi.myplex.MyPlexPinLogin.checkLogin`.
        - The threaded approach expects the developer to call
          :func:`~plexapi.myplex.MyPlexPinLogin.run` and then at a later time call
          :func:`~plexapi.myplex.MyPlexPinLogin.waitForLogin` to wait for and check the result.
        - The callback approach is an extension of the threaded approach and expects the developer
          to pass the ``callback`` parameter to the call to :func:`~plexapi.myplex.MyPlexPinLogin.run`.
          The callback will be called when the thread waiting for the PIN login to succeed either
          finishes or expires. The parameter passed to the callback is the received authentication
          token or ``None`` if the login expired.

        Parameters:
            session (requests.Session, optional): Use your own session object if you want to
                cache the http responses from Plex.
            requestTimeout (int, optional): Timeout in seconds on initial connect to plex.tv (default config.TIMEOUT).
            headers (dict, optional): A dict of X-Plex headers to send with requests.
            oauth (bool, optional): True to use Plex OAuth instead of PIN login.

        Attributes:
            PINS (str): 'https://plex.tv/api/v2/pins'
            POLLINTERVAL (int): 1
            pin (str): Four character PIN to use for the login at https://plex.tv/link.
            finished (bool): Whether the pin login has finished or not.
            expired (bool): Whether the pin login has expired or not.
            token (str): Token retrieved after login.

        Example:

            .. code-block:: python

                from plexapi.myplex import MyPlexAccount, MyPlexPinLogin

                pinlogin = MyPlexPinLogin(oauth=True)
                pinlogin.run()
                print(f'Login to Plex at the following url:\\n{pinlogin.oauthUrl()}')
                pinlogin.waitForLogin()
                token = pinlogin.token

                account = MyPlexAccount(token=token)

    """
    PINS = 'https://plex.tv/api/v2/pins'
    POLLINTERVAL = 1

    def __init__(self, session=None, requestTimeout=None, headers=None, oauth=False):
        super(MyPlexPinLogin, self).__init__()
        self._session = session or requests.Session()
        self._requestTimeout = requestTimeout or TIMEOUT
        self._customHeaders = headers

        self._oauth = oauth
        self._loginTimeout = None
        self._callback = None
        self._thread = None
        self._abort = False
        self._id = None
        self._code = None

        self.finished = False
        self.expired = False
        self.token = None

    @property
    def pin(self):
        """ Return the four character PIN used for linking a device at
            https://plex.tv/link.
        """
        if self._oauth:
            raise BadRequest('Cannot use PIN for Plex OAuth login')
        return self._getCode()

    def oauthUrl(self, forwardUrl=None):
        """ Return the Plex OAuth url for login.

            Parameters:
                forwardUrl (str, optional): The url to redirect the client to after login.
        """
        if not self._oauth:
            raise BadRequest('Must use "MyPlexPinLogin(oauth=True)" for Plex OAuth login.')

        headers = self._headers()
        params = {
            'clientID': headers['X-Plex-Client-Identifier'],
            'context[device][product]': headers['X-Plex-Product'],
            'context[device][version]': headers['X-Plex-Version'],
            'context[device][platform]': headers['X-Plex-Platform'],
            'context[device][platformVersion]': headers['X-Plex-Platform-Version'],
            'context[device][device]': headers['X-Plex-Device'],
            'context[device][deviceName]': headers['X-Plex-Device-Name'],
            'code': self._getCode()
        }
        if forwardUrl:
            params['forwardUrl'] = forwardUrl

        return f'https://app.plex.tv/auth/#!?{urlencode(params)}'

    def run(self, callback=None, timeout=120):
        """ Starts the thread which monitors the PIN login state.

            Parameters:
                callback (Callable[str], optional): Callback called with the received authentication token.
                timeout (int, optional): Timeout in seconds to wait for user login. Default 120 seconds.

            Raises:
                :exc:`RuntimeError`: If the thread is already running.
                :exc:`RuntimeError`: If the PIN login for the current PIN has expired.
        """
        if self._thread and not self._abort:
            raise RuntimeError('MyPlexPinLogin thread is already running')
        if self.expired:
            raise RuntimeError('MyPlexPinLogin has expired')

        self._getCode()

        self._loginTimeout = timeout
        self._callback = callback
        self._abort = False
        self.finished = False
        self._thread = threading.Thread(target=self._pollLogin, name='plexapi.myplex.MyPlexPinLogin')
        self._thread.start()

    def waitForLogin(self):
        """ Waits for the PIN login to succeed or expire.

            Returns:
                bool: ``True`` if the PIN login succeeded or ``False`` otherwise.
        """
        if not self._thread or self._abort:
            return False

        self._thread.join()
        if self.expired or not self.token:
            return False

        return True

    def stop(self):
        """ Stops the thread monitoring the PIN login state. """
        if not self._thread or self._abort:
            return

        self._abort = True
        self._thread.join()

    def checkLogin(self):
        """ Returns ``True`` if the PIN login has succeeded. """
        if self._thread:
            return False

        try:
            return self._checkLogin()
        except Exception:
            self.expired = True
            self.finished = True

        return False

    def _getCode(self):
        if self._code:
            return self._code

        url = self.PINS

        if self._oauth:
            params = {'strong': True}
        else:
            params = None

        response = self._query(url, self._session.post, params=params)
        if response is None:
            return None

        self._id = response.attrib.get('id')
        self._code = response.attrib.get('code')

        return self._code

    def _checkLogin(self):
        if not self._id:
            return False

        if self.token:
            return True

        url = f'{self.PINS}/{self._id}'
        response = self._query(url)
        if response is None:
            return False

        token = response.attrib.get('authToken')
        if not token:
            return False

        self.token = token
        self.finished = True
        return True

    def _pollLogin(self):
        try:
            start = time.time()
            while not self._abort and (not self._loginTimeout or (time.time() - start) < self._loginTimeout):
                try:
                    result = self._checkLogin()
                except Exception:
                    self.expired = True
                    break

                if result:
                    break

                time.sleep(self.POLLINTERVAL)

            if self.token and self._callback:
                self._callback(self.token)
        finally:
            self.finished = True

    def _headers(self, **kwargs):
        """ Returns dict containing base headers for all requests for pin login. """
        headers = BASE_HEADERS.copy()
        if self._customHeaders:
            headers.update(self._customHeaders)
        headers.update(kwargs)
        return headers

    def _query(self, url, method=None, headers=None, **kwargs):
        method = method or self._session.get
        log.debug('%s %s', method.__name__.upper(), url)
        headers = headers or self._headers()
        response = method(url, headers=headers, timeout=self._requestTimeout, **kwargs)
        if not response.ok:  # pragma: no cover
            codename = codes.get(response.status_code)[0]
            errtext = response.text.replace('\n', ' ')
            raise BadRequest(f'({response.status_code}) {codename} {response.url}; {errtext}')
        return utils.parseXMLString(response.text)


class MyPlexJWTLogin:
    """
        MyPlex JWT login class which supports getting a JWT for authenticating the client and
        providing an access token to create a :class:`~plexapi.myplex.MyPlexAccount` instance.
        The login can be done using the four character PIN which the user must enter at
        https://plex.tv/link or using Plex OAuth.
        This class can also be used to refresh or verify an existing JWT.

        See: https://developer.plex.tv/pms/#section/API-Info/Authenticating-with-Plex

        Using this class requires the ``PyJWT`` with ``cryptography`` packages to be installed
        (``pyjwt[crypto]``).

        This helper class supports a polling, threaded and callback approach.

        - The polling approach expects the developer to periodically check if the PIN login was
          successful using :func:`~plexapi.myplex.MyPlexJWTLogin.checkLogin`.
        - The threaded approach expects the developer to call
          :func:`~plexapi.myplex.MyPlexJWTLogin.run` and then at a later time call
          :func:`~plexapi.myplex.MyPlexJWTLogin.waitForLogin` to wait for and check the result.
        - The callback approach is an extension of the threaded approach and expects the developer
          to pass the ``callback`` parameter to the call to :func:`~plexapi.myplex.MyPlexJWTLogin.run`.
          The callback will be called when the thread waiting for the PIN login to succeed either
          finishes or expires. The parameter passed to the callback is the received authentication
          token or ``None`` if the login expired.

        Parameters:
            session (requests.Session, optional): Use your own session object if you want to
                cache the http responses from Plex.
            requestTimeout (int, optional): Timeout in seconds on initial connect to plex.tv (default config.TIMEOUT).
            headers (dict, optional): A dict of X-Plex headers to send with requests.
            oauth (bool, optional): True to use Plex OAuth instead of PIN login.
            token (str, optional): Plex token only required to register the device initially if not using OAuth.
            jwtToken (str, optional): Existing Plex JWT to verify or refresh.
            keypair (tuple[str|bytes], optional): A tuple of the full file paths (str) to the ED25519 private and public
                key pair or the raw keys themselves (bytes) to use for signing the JWT.
                Use :func:`~plexapi.myplex.MyPlexJWTLogin.generateKeypair` to generate a new keypair if not provided.
            scope (list[str], optional): List of scopes to request in the new token.
                Default is all available scopes.

        Attributes:
            PINS (str): 'https://plex.tv/api/v2/pins'
            AUTH (str): 'https://clients.plex.tv/api/v2/auth'
            POLLINTERVAL (int): 1
            SCOPES (list): List of all available scopes to request for the JWT.
            pin (str): Four character PIN to use for the login at https://plex.tv/link.
            finished (bool): Whether the JWT login has finished or not.
            expired (bool): Whether the JWT login has expired or not.
            jwtToken (str): The Plex JWT received after login or refreshing.
            decodedJWT (dict): The decoded Plex JWT payload.

        Example:

            .. code-block:: python

                from plexapi.myplex import MyPlexAccount, MyPlexJWTLogin

                # Method 1: Generate a new Plex JWT using Plex OAuth
                jwtlogin = MyPlexJWTLogin(
                    oauth=True,
                    scopes=['username', 'email', 'friendly_name']
                )
                jwtlogin.generateKeypair(keyfiles=('private.key', 'public.key'))
                jwtlogin.run()
                print(f'Login to Plex at the following url:\\n{jwtlogin.oauthUrl()}')
                jwtlogin.waitForLogin()
                jwtToken = jwtlogin.jwtToken

                account = MyPlexAccount(token=jwtToken)

                # Method 2: Generate a new Plex JWT using an existing Plex token and keypair
                jwtlogin = MyPlexJWTLogin(
                    token='2ffLuB84dqLswk9skLos',
                    keypair=('private.key', 'public.key'),
                    scopes=['username', 'email', 'friendly_name']
                )
                jwtlogin.registerDevice()
                jwtToken = jwtlogin.refreshJWT()

                account = MyPlexAccount(token=jwtToken)

                # Refresh an existing Plex JWT
                jwtlogin = MyPlexJWTLogin(
                    jwtToken=jwtToken,
                    keypair=('private.key', 'public.key'),
                    scopes=['username', 'email', 'friendly_name']
                )
                if not jwtlogin.verifyJWT():
                    jwtToken = jwtlogin.refreshJWT()

                account = MyPlexAccount(token=jwtToken)

    """
    PINS = 'https://clients.plex.tv/api/v2/pins'
    AUTH = 'https://clients.plex.tv/api/v2/auth'
    POLLINTERVAL = 1
    SCOPES = ['username', 'email', 'friendly_name', 'restricted', 'anonymous', 'joinedAt']

    def __init__(self, session=None, requestTimeout=None, headers=None, oauth=False,
                 token=None, jwtToken=None, keypair=(None, None), scopes=None):
        super(MyPlexJWTLogin, self).__init__()
        self._session = session or requests.Session()
        self._requestTimeout = requestTimeout or TIMEOUT
        self._customHeaders = headers
        self._token = token
        self._privateKey = utils.openOrRead(keypair[0]) if keypair[0] else None
        self._publicKey = utils.openOrRead(keypair[1]) if keypair[1] else None
        self._scopes = scopes or self.SCOPES
        self._clientJWT = None

        self._oauth = oauth
        self._loginTimeout = None
        self._callback = None
        self._thread = None
        self._abort = False
        self._id = None
        self._code = None

        self.finished = False
        self.expired = False
        self.jwtToken = jwtToken

        if not jwt:
            log.warning('PyJWT package is not installed, cannot use Plex JWT login')
            return

    def generateKeypair(self, keyfiles=(None, None), overwrite=False):
        """ Generates a new ED25519 private/public keypair for signing the JWT and saves them to files.
            Requires the ``cryptography`` package to be installed.

            Parameters:
                keyfiles (tuple[str]): A tuple of the full file paths to write the private and public keypair to.
                overwrite (bool): Set to True to overwrite existing keypair files. Default is False.

            Raises:
                :exc:`FileExistsError`: when keypair files already exist and overwrite is False.
        """
        if not cryptography:
            log.warning('Cryptography package is not installed, cannot generate ED25519 keypair')
            return

        privateKey = ed25519.Ed25519PrivateKey.generate()
        publicKey = privateKey.public_key()
        _privateKey = privateKey.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption()
        )
        _publicKey = publicKey.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )

        if keyfiles[0] and keyfiles[1]:
            if not overwrite and (os.path.exists(keyfiles[0]) or os.path.exists(keyfiles[1])):
                raise FileExistsError('Keypair files already exist, set overwrite=True to overwrite them.')

            with open(keyfiles[0], 'wb') as privateFile, open(keyfiles[1], 'wb') as publicFile:
                privateFile.write(_privateKey)
                publicFile.write(_publicKey)

        self._privateKey = _privateKey
        self._publicKey = _publicKey

    @property
    def _clientIdentifier(self):
        """ Returns the client identifier from the headers. """
        headers = self._headers()
        return headers['X-Plex-Client-Identifier']

    @property
    def _keyID(self):
        """ Returns the key ID (thumbprint) for the ED25519 keypair. """
        if not self._privateKey or not self._publicKey:
            return None
        return hashlib.sha256(self._privateKey + self._publicKey).hexdigest()

    @property
    def _privateJWK(self):
        """ Returns the private JWK (JSON Web Key) for the ED25519 keypair."""
        return jwt.PyJWK.from_dict({
            'kty': 'OKP',
            'crv': 'Ed25519',
            'x': utils.base64urlEncode(self._publicKey),
            'd': utils.base64urlEncode(self._privateKey),
            'use': 'sig',
            'alg': 'EdDSA',
            'kid': self._keyID,
        })

    @property
    def _publicJWK(self):
        """ Returns the public JWK (JSON Web Key) for the ED25519 keypair."""
        return jwt.PyJWK.from_dict({
            'kty': 'OKP',
            'crv': 'Ed25519',
            'x': utils.base64urlEncode(self._publicKey),
            'use': 'sig',
            'alg': 'EdDSA',
            'kid': self._keyID,
        })

    def _encodeClientJWT(self):
        """ Returns the encoded client JWT using the private JWK. """
        payload = {
            'nonce': self._getPlexNonce(),
            'scope': ','.join(self._scopes),
            'aud': 'plex.tv',
            'iss': self._clientIdentifier,
            'iat': int(datetime.now(timezone.utc).timestamp()),
            'exp': int((datetime.now(timezone.utc) + timedelta(minutes=5)).timestamp()),
        }
        headers = {
            'kid': self._keyID
        }
        return jwt.encode(
            payload,
            key=self._privateJWK,
            algorithm='EdDSA',
            headers=headers
        )

    def decodePlexJWT(self, verify_signature=True):
        """ Returns the decoded Plex JWT with optional signature verification using the Plex public JWK.

            Parameters:
                verify_signature (bool): Whether to verify the JWT signature and required claims.
                    Defaults to True. Set to False to skip signature verification and required-claim enforcement.
        """
        kwargs = {
            'jwt': self.jwtToken,
            'algorithms': ['EdDSA'],
            'options': {'verify_signature': verify_signature},
            'audience': ['plex.tv', self._clientIdentifier],
            'issuer': 'plex.tv',
        }

        if not verify_signature:
            return jwt.decode(**kwargs)

        kwargs['options']['require'] = ['aud', 'iss', 'exp', 'iat', 'thumbprint']

        for plexJWK in reversed(self._getPlexPublicJWK()):
            try:
                return jwt.decode(
                    key=jwt.PyJWK.from_dict(plexJWK),
                    **kwargs
                )
            except jwt.InvalidSignatureError:
                continue
            except jwt.InvalidTokenError as e:
                log.warning('Invalid Plex JWT: %s', str(e))
                raise

        log.warning('Plex JWT signature could not be verified with any known Plex JWKs')
        raise jwt.InvalidSignatureError

    @property
    def decodedJWT(self):
        """ Returns the decoded Plex JWT with signature verification and required-claim enforcement. """
        return self.decodePlexJWT()

    def _registerPlexDevice(self):
        """ Registers the public JWK with Plex. """
        url = f'{self.AUTH}/jwk'
        headers = self._headers(**{'X-Plex-Token': self._token})
        body = {'jwk': self._publicJWK._jwk_data}
        self._query(url, method=self._session.post, headers=headers, json=body)

    def _getPlexNonce(self):
        """ Gets a nonce from Plex. """
        url = f'{self.AUTH}/nonce'
        data = self._query(url, method=self._session.get)
        return data['nonce']

    def _exchangePlexJWT(self):
        """ Exchanges the client JWT for a Plex JWT. """
        url = f'{self.AUTH}/token'
        body = {'jwt': self._clientJWT}
        data = self._query(url, method=self._session.post, json=body)
        return data['auth_token']

    def _getPlexPublicJWK(self):
        """ Gets the Plex public JWKs. """
        url = f'{self.AUTH}/keys'
        data = self._query(url, method=self._session.get)
        return data['keys']

    def registerDevice(self):
        """ Registers the device with Plex using the provided token and private/public keypair.
            This must be done once if OAuth was not used before the Plex JWT can be refreshed.

            Raises:
                :exc:`~plexapi.exceptions.BadRequest`: when token or keypair is missing.
        """
        if not self._token:
            raise BadRequest('Plex token is required to register device.')

        if not self._privateKey or not self._publicKey:
            raise BadRequest('ED25519 private and public keys are required to register device. '
                             'Use generateKeypair() to generate a new keypair.')

        self._registerPlexDevice()

    def refreshJWT(self):
        """ Refreshes the Plex JWT using the existing private/public keypair.

            Returns:
                str: The new Plex JWT.

            Raises:
                :exc:`~plexapi.exceptions.BadRequest`: when keypair is missing.
                :exc:`~plexapi.exceptions.BadRequest`: when the newly obtained JWT cannot be verified.
        """
        if not self._privateKey or not self._publicKey:
            raise BadRequest('ED25519 private and public keys are required to refresh JWT.')

        self._clientJWT = self._encodeClientJWT()
        self.jwtToken = self._exchangePlexJWT()
        if self.verifyJWT():
            return self.jwtToken
        raise BadRequest('Failed to verify newly obtained JWT.')

    def verifyJWT(self, refreshWithinDays=1):
        """ Verifies the existing Plex JWT is valid and not expiring within the specified number of days.

            Parameters:
                refreshWithinDays (int): Number of days before expiration to consider
                    the JWT invalid and in need of refresh. Default is 1 day.
        """
        try:
            decodedJWT = self.decodedJWT
        except jwt.InvalidTokenError:
            return False
        else:
            if decodedJWT['thumbprint'] != self._keyID:
                log.warning('Existing JWT was signed with a different key')
                return False
            elif decodedJWT['exp'] < int((datetime.now(timezone.utc) + timedelta(days=refreshWithinDays)).timestamp()):
                log.warning(f'Existing JWT is expiring within {refreshWithinDays} day(s)')
                return False
        return True

    @property
    def pin(self):
        """ Return the four character PIN used for linking a device at
            https://plex.tv/link.
        """
        if self._oauth:
            raise BadRequest('Cannot use PIN for Plex OAuth login')
        return self._code

    def oauthUrl(self, forwardUrl=None):
        """ Return the Plex OAuth url for login.

            Parameters:
                forwardUrl (str, optional): The url to redirect the client to after login.
        """
        if not self._oauth:
            raise BadRequest('Must use "MyPlexJWTLogin(oauth=True)" for Plex OAuth login.')

        headers = self._headers()
        params = {
            'clientID': headers['X-Plex-Client-Identifier'],
            'context[device][product]': headers['X-Plex-Product'],
            'context[device][version]': headers['X-Plex-Version'],
            'context[device][platform]': headers['X-Plex-Platform'],
            'context[device][platformVersion]': headers['X-Plex-Platform-Version'],
            'context[device][device]': headers['X-Plex-Device'],
            'context[device][deviceName]': headers['X-Plex-Device-Name'],
            'code': self._code
        }
        if forwardUrl:
            params['forwardUrl'] = forwardUrl

        return f'https://app.plex.tv/auth/#!?{urlencode(params)}'

    def run(self, callback=None, timeout=120):
        """ Starts the thread which monitors the PIN login state.

            Parameters:
                callback (Callable[str], optional): Callback called with the received authentication token.
                timeout (int, optional): Timeout in seconds to wait for user login. Default 120 seconds.

            Raises:
                :exc:`RuntimeError`: If the thread is already running.
                :exc:`RuntimeError`: If the PIN login for the current PIN has expired.
        """
        if self._thread and not self._abort:
            raise RuntimeError('MyPlexJWTLogin thread is already running')
        if self.expired:
            raise RuntimeError('MyPlexJWTLogin has expired')

        self._getCode()
        self._clientJWT = self._encodeClientJWT()

        self._loginTimeout = timeout
        self._callback = callback
        self._abort = False
        self.finished = False
        self._thread = threading.Thread(target=self._pollLogin, name='plexapi.myplex.MyPlexJWTLogin')
        self._thread.start()

    def waitForLogin(self):
        """ Waits for the user login to succeed or expire.

            Returns:
                bool: ``True`` if the user login succeeded or ``False`` otherwise.
        """
        if not self._thread or self._abort:
            return False

        self._thread.join()
        if self.expired or not self.jwtToken:
            return False

        return True

    def stop(self):
        """ Stops the thread monitoring the user login state. """
        if not self._thread or self._abort:
            return

        self._abort = True
        self._thread.join()

    def checkLogin(self):
        """ Returns ``True`` if the user login has succeeded. """
        if self._thread:
            return False

        try:
            return self._checkLogin()
        except Exception:
            self.expired = True
            self.finished = True

        return False

    def _getCode(self):
        url = self.PINS

        if self._oauth:
            body = {
                'jwk': self._publicJWK._jwk_data,
                'strong': True,
            }
        else:
            body = {
                'jwk': self._publicJWK._jwk_data,
            }

        response = self._query(url, self._session.post, json=body)
        if response is None:
            return None

        self._id = response.get('id')
        self._code = response.get('code')

        return self._code

    def _checkLogin(self):
        if not self._id:
            return False

        if self.jwtToken:
            return True

        url = f'{self.PINS}/{self._id}'
        params = {'deviceJWT': self._clientJWT}
        response = self._query(url, params=params)
        if response is None:
            return False

        token = response.get('authToken')
        if not token:
            return False

        self.jwtToken = token
        self.finished = True
        return True

    def _pollLogin(self):
        try:
            start = time.time()
            while not self._abort and (not self._loginTimeout or (time.time() - start) < self._loginTimeout):
                try:
                    result = self._checkLogin()
                except Exception:
                    self.expired = True
                    break

                if result:
                    break

                time.sleep(self.POLLINTERVAL)

            if self.jwtToken and self._callback:
                self._callback(self.jwtToken)
        finally:
            self.finished = True

    def _headers(self, **kwargs):
        """ Returns dict containing base headers for all requests for Plex JWT login. """
        headers = BASE_HEADERS.copy()
        if self._customHeaders:
            headers.update(self._customHeaders)
        headers.update(kwargs)
        headers['Accept'] = 'application/json'
        return headers

    def _query(self, url, method=None, headers=None, **kwargs):
        method = method or self._session.get
        log.debug('%s %s', method.__name__.upper(), url)
        headers = headers or self._headers()
        response = method(url, headers=headers, timeout=self._requestTimeout, **kwargs)
        if not response.ok:  # pragma: no cover
            codename = codes.get(response.status_code)[0]
            errtext = response.text.replace('\n', ' ')
            raise BadRequest(f'({response.status_code}) {codename} {response.url}; {errtext}')
        if 'application/json' in response.headers.get('Content-Type', '') and len(response.content):
            return response.json()
        return utils.parseXMLString(response.text)


def _connect(cls, url, token, session, timeout, results, i, job_is_done_event=None):
    """ Connects to the specified cls with url and token. Stores the connection
        information to results[i] in a threadsafe way.

        Arguments:
            cls: the class which is responsible for establishing connection, basically it's
                 :class:`~plexapi.client.PlexClient` or :class:`~plexapi.server.PlexServer`
            url (str): url which should be passed as `baseurl` argument to cls.__init__()
            session (requests.Session): session which sould be passed as `session` argument to cls.__init()
            token (str): authentication token which should be passed as `baseurl` argument to cls.__init__()
            timeout (int): timeout which should be passed as `baseurl` argument to cls.__init__()
            results (list): pre-filled list for results
            i (int): index of current job, should be less than len(results)
            job_is_done_event (:class:`~threading.Event`): is X_PLEX_ENABLE_FAST_CONNECT is True then the
                  event would be set as soon the connection is established
    """
    starttime = time.time()
    try:
        device = cls(baseurl=url, token=token, session=session, timeout=timeout)
        runtime = int(time.time() - starttime)
        results[i] = (url, token, device, runtime)
        if X_PLEX_ENABLE_FAST_CONNECT and job_is_done_event:
            job_is_done_event.set()
    except Exception as err:
        runtime = int(time.time() - starttime)
        log.error('%s: %s', url, err)
        results[i] = (url, token, None, runtime)


def _chooseConnection(ctype, name, results):
    """ Chooses the first (best) connection from the given _connect results. """
    # At this point we have a list of result tuples containing (url, token, PlexServer, runtime)
    # or (url, token, None, runtime) in the case a connection could not be established.
    for url, token, result, runtime in results:
        okerr = 'OK' if result else 'ERR'
        log.debug('%s connection %s (%ss): %s?X-Plex-Token=%s', ctype, okerr, runtime, url, token)
    results = [r[2] for r in results if r and r[2] is not None]
    if results:
        log.debug('Connecting to %s: %s?X-Plex-Token=%s', ctype, results[0]._baseurl, results[0]._token)
        return results[0]
    raise NotFound(f'Unable to connect to {ctype.lower()}: {name}')


class AccountOptOut(PlexObject):
    """ Represents a single AccountOptOut
        'https://plex.tv/api/v2/user/{userUUID}/settings/opt_outs'

        Attributes:
            TAG (str): optOut
            key (str): Online Media Source key
            value (str): Online Media Source opt_in, opt_out, or opt_out_managed
    """
    TAG = 'optOut'
    CHOICES = {'opt_in', 'opt_out', 'opt_out_managed'}

    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        self.key = data.attrib.get('key')
        self.value = data.attrib.get('value')

    def _updateOptOut(self, option):
        """ Sets the Online Media Sources option.

            Parameters:
                option (str): see CHOICES

            Raises:
                :exc:`~plexapi.exceptions.NotFound`: ``option`` str not found in CHOICES.
        """
        if option not in self.CHOICES:
            raise NotFound(f'{option} not found in available choices: {self.CHOICES}')
        url = self._server.OPTOUTS.format(userUUID=self._server.uuid)
        params = {'key': self.key, 'value': option}
        self._server.query(url, method=self._server._session.post, params=params)
        self.value = option  # assume query successful and set the value to option

    def optIn(self):
        """ Sets the Online Media Source to "Enabled". """
        self._updateOptOut('opt_in')

    def optOut(self):
        """ Sets the Online Media Source to "Disabled". """
        self._updateOptOut('opt_out')

    def optOutManaged(self):
        """ Sets the Online Media Source to "Disabled for Managed Users".

            Raises:
                :exc:`~plexapi.exceptions.BadRequest`: When trying to opt out music.
        """
        if self.key == 'tv.plex.provider.music':
            raise BadRequest(f'{self.key} does not have the option to opt out managed users.')
        self._updateOptOut('opt_out_managed')


class UserState(PlexObject):
    """ Represents a single UserState

        Attributes:
            TAG (str): UserState
            lastViewedAt (datetime): Datetime the item was last played.
            ratingKey (str): Unique key identifying the item.
            type (str): The media type of the item.
            viewCount (int): Count of times the item was played.
            viewedLeafCount (int): Number of items marked as played in the show/season.
            viewOffset (int): Time offset in milliseconds from the start of the content
            viewState (bool): True or False if the item has been played.
            watchlistedAt (datetime): Datetime the item was added to the watchlist.
    """
    TAG = 'UserState'

    def __repr__(self):
        return f'<{self.__class__.__name__}:{self.ratingKey}>'

    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        self.lastViewedAt = utils.toDatetime(data.attrib.get('lastViewedAt'))
        self.ratingKey = data.attrib.get('ratingKey')
        self.type = data.attrib.get('type')
        self.viewCount = utils.cast(int, data.attrib.get('viewCount', 0))
        self.viewedLeafCount = utils.cast(int, data.attrib.get('viewedLeafCount', 0))
        self.viewOffset = utils.cast(int, data.attrib.get('viewOffset', 0))
        self.viewState = data.attrib.get('viewState') == 'complete'
        self.watchlistedAt = utils.toDatetime(data.attrib.get('watchlistedAt'))


class GeoLocation(PlexObject):
    """ Represents a signle IP address geolocation

        Attributes:
            TAG (str): location
            city (str): City name
            code (str): Country code
            continentCode (str): Continent code
            coordinates (Tuple<float>): Latitude and longitude
            country (str): Country name
            europeanUnionMember (bool): True if the country is a member of the European Union
            inPrivacyRestrictedCountry (bool): True if the country is privacy restricted
            postalCode (str): Postal code
            subdivisions (str): Subdivision name
            timezone (str): Timezone
    """
    TAG = 'location'

    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        self.city = data.attrib.get('city')
        self.code = data.attrib.get('code')
        self.continentCode = data.attrib.get('continent_code')
        self.coordinates = tuple(
            utils.cast(float, coord) for coord in (data.attrib.get('coordinates') or ',').split(','))
        self.country = data.attrib.get('country')
        self.postalCode = data.attrib.get('postal_code')
        self.subdivisions = data.attrib.get('subdivisions')
        self.timezone = data.attrib.get('time_zone')

        europeanUnionMember = data.attrib.get('european_union_member')
        self.europeanUnionMember = (
            False if europeanUnionMember == 'Unknown' else utils.cast(bool, europeanUnionMember))

        inPrivacyRestrictedCountry = data.attrib.get('in_privacy_restricted_country')
        self.inPrivacyRestrictedCountry = (
            False if inPrivacyRestrictedCountry == 'Unknown' else utils.cast(bool, inPrivacyRestrictedCountry))
