# -*- coding: utf-8 -*-
import copy
import html
import threading
import time
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from xml.etree import ElementTree

import requests
from plexapi import (BASE_HEADERS, CONFIG, TIMEOUT, X_PLEX_CONTAINER_SIZE,
                     X_PLEX_ENABLE_FAST_CONNECT, X_PLEX_IDENTIFIER, log, logfilter, utils)
from plexapi.base import PlexObject
from plexapi.client import PlexClient
from plexapi.exceptions import BadRequest, NotFound, Unauthorized
from plexapi.library import LibrarySection
from plexapi.server import PlexServer
from plexapi.sonos import PlexSonosClient
from plexapi.sync import SyncItem, SyncList
from requests.status_codes import _codes as codes


class MyPlexAccount(PlexObject):
    """ MyPlex account and profile information. This object represents the data found Account on
        the myplex.tv servers at the url https://plex.tv/users/account. You may create this object
        directly by passing in your username & password (or token). There is also a convenience
        method provided at :class:`~plexapi.server.PlexServer.myPlexAccount()` which will create
        and return this object.

        Parameters:
            username (str): Your MyPlex username.
            password (str): Your MyPlex password.
            session (requests.Session, optional): Use your own session object if you want to
                cache the http responses from PMS
            timeout (int): timeout in seconds on initial connect to myplex (default config.TIMEOUT).
            code (str): Two-factor authentication code to use when logging in.

        Attributes:
            SIGNIN (str): 'https://plex.tv/users/sign_in.xml'
            key (str): 'https://plex.tv/users/account'
            authenticationToken (str): Unknown.
            certificateVersion (str): Unknown.
            cloudSyncDevice (str): Unknown.
            email (str): Your current Plex email address.
            entitlements (List<str>): List of devices your allowed to use with this account.
            guest (bool): Unknown.
            home (bool): Unknown.
            homeSize (int): Unknown.
            id (int): Your Plex account ID.
            locale (str): Your Plex locale
            mailing_list_status (str): Your current mailing list status.
            maxHomeSize (int): Unknown.
            pin (str): The hashed Plex Home PIN.
            queueEmail (str): Email address to add items to your `Watch Later` queue.
            queueUid (str): Unknown.
            restricted (bool): Unknown.
            roles: (List<str>) Lit of account roles. Plexpass membership listed here.
            scrobbleTypes (str): Description
            secure (bool): Description
            subscriptionActive (bool): True if your subscription is active.
            subscriptionFeatures: (List<str>) List of features allowed on your subscription.
            subscriptionPlan (str): Name of subscription plan.
            subscriptionStatus (str): String representation of `subscriptionActive`.
            thumb (str): URL of your account thumbnail.
            title (str): Unknown. - Looks like an alias for `username`.
            username (str): Your account username.
            uuid (str): Unknown.
            _token (str): Token used to access this client.
            _session (obj): Requests session object used to access this client.
    """
    FRIENDINVITE = 'https://plex.tv/api/servers/{machineId}/shared_servers'                     # post with data
    HOMEUSERS = 'https://plex.tv/api/home/users'
    HOMEUSERCREATE = 'https://plex.tv/api/home/users?title={title}'                             # post with data
    EXISTINGUSER = 'https://plex.tv/api/home/users?invitedEmail={username}'                     # post with data
    FRIENDSERVERS = 'https://plex.tv/api/servers/{machineId}/shared_servers/{serverId}'         # put with data
    PLEXSERVERS = 'https://plex.tv/api/servers/{machineId}'                                     # get
    FRIENDUPDATE = 'https://plex.tv/api/friends/{userId}'                                       # put with args, delete
    HOMEUSER = 'https://plex.tv/api/home/users/{userId}'                                        # delete, put
    MANAGEDHOMEUSER = 'https://plex.tv/api/v2/home/users/restricted/{userId}'                   # put
    SIGNIN = 'https://plex.tv/users/sign_in.xml'                                                # get with auth
    WEBHOOKS = 'https://plex.tv/api/v2/user/webhooks'                                           # get, post with data
    OPTOUTS = 'https://plex.tv/api/v2/user/{userUUID}/settings/opt_outs'                        # get
    LINK = 'https://plex.tv/api/v2/pins/link'                                                   # put
    VIEWSTATESYNC = 'https://plex.tv/api/v2/user/view_state_sync'                               # put
    # Hub sections
    VOD = 'https://vod.provider.plex.tv'                                                        # get
    MUSIC = 'https://music.provider.plex.tv'                                                    # get
    METADATA = 'https://metadata.provider.plex.tv'
    # Key may someday switch to the following url. For now the current value works.
    # https://plex.tv/api/v2/user?X-Plex-Token={token}&X-Plex-Client-Identifier={clientId}
    key = 'https://plex.tv/users/account'

    def __init__(self, username=None, password=None, token=None, session=None, timeout=None, code=None):
        self._token = token or CONFIG.get('auth.server_token')
        self._session = session or requests.Session()
        self._sonos_cache = []
        self._sonos_cache_timestamp = 0
        data, initpath = self._signin(username, password, code, timeout)
        super(MyPlexAccount, self).__init__(self, data, initpath)

    def _signin(self, username, password, code, timeout):
        if self._token:
            return self.query(self.key), self.key
        username = username or CONFIG.get('auth.myplex_username')
        password = password or CONFIG.get('auth.myplex_password')
        if code:
            password += code
        data = self.query(self.SIGNIN, method=self._session.post, auth=(username, password), timeout=timeout)
        return data, self.SIGNIN

    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        self._data = data
        self._token = logfilter.add_secret(data.attrib.get('authenticationToken'))
        self._webhooks = []
        self.authenticationToken = self._token
        self.certificateVersion = data.attrib.get('certificateVersion')
        self.cloudSyncDevice = data.attrib.get('cloudSyncDevice')
        self.email = data.attrib.get('email')
        self.guest = utils.cast(bool, data.attrib.get('guest'))
        self.home = utils.cast(bool, data.attrib.get('home'))
        self.homeSize = utils.cast(int, data.attrib.get('homeSize'))
        self.id = utils.cast(int, data.attrib.get('id'))
        self.locale = data.attrib.get('locale')
        self.mailing_list_status = data.attrib.get('mailing_list_status')
        self.maxHomeSize = utils.cast(int, data.attrib.get('maxHomeSize'))
        self.pin = data.attrib.get('pin')
        self.queueEmail = data.attrib.get('queueEmail')
        self.queueUid = data.attrib.get('queueUid')
        self.restricted = utils.cast(bool, data.attrib.get('restricted'))
        self.scrobbleTypes = data.attrib.get('scrobbleTypes')
        self.secure = utils.cast(bool, data.attrib.get('secure'))
        self.thumb = data.attrib.get('thumb')
        self.title = data.attrib.get('title')
        self.username = data.attrib.get('username')
        self.uuid = data.attrib.get('uuid')

        subscription = data.find('subscription')
        self.subscriptionActive = utils.cast(bool, subscription.attrib.get('active'))
        self.subscriptionStatus = subscription.attrib.get('status')
        self.subscriptionPlan = subscription.attrib.get('plan')
        self.subscriptionFeatures = self.listAttrs(subscription, 'id', etag='feature')

        self.roles = self.listAttrs(data, 'id', rtag='roles', etag='role')

        self.entitlements = self.listAttrs(data, 'id', rtag='entitlements', etag='entitlement')

        # TODO: Fetch missing MyPlexAccount attributes
        self.profile_settings = None
        self.services = None
        self.joined_at = None

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

    def _headers(self, **kwargs):
        """ Returns dict containing base headers for all requests to the server. """
        headers = BASE_HEADERS.copy()
        if self._token:
            headers['X-Plex-Token'] = self._token
        headers.update(kwargs)
        return headers

    def query(self, url, method=None, headers=None, timeout=None, **kwargs):
        method = method or self._session.get
        timeout = timeout or TIMEOUT
        log.debug('%s %s %s', method.__name__.upper(), url, kwargs.get('json', ''))
        headers = self._headers(**headers or {})
        response = method(url, headers=headers, timeout=timeout, **kwargs)
        if response.status_code not in (200, 201, 204):  # pragma: no cover
            codename = codes.get(response.status_code)[0]
            errtext = response.text.replace('\n', ' ')
            message = f'({response.status_code}) {codename}; {response.url} {errtext}'
            if response.status_code == 401:
                raise Unauthorized(message)
            elif response.status_code == 404:
                raise NotFound(message)
            else:
                raise BadRequest(message)
        if headers.get('Accept') == 'application/json':
            return response.json()
        data = response.text.encode('utf8')
        return ElementTree.fromstring(data) if data.strip() else None

    def resource(self, name):
        """ Returns the :class:`~plexapi.myplex.MyPlexResource` that matches the name specified.

            Parameters:
                name (str): Name to match against.
        """
        for resource in self.resources():
            if resource.name.lower() == name.lower():
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

    def history(self, maxresults=9999999, mindate=None):
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

    def watchlist(self, filter=None, sort=None, libtype=None, maxresults=9999999, **kwargs):
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

        params['X-Plex-Container-Start'] = 0
        params['X-Plex-Container-Size'] = min(X_PLEX_CONTAINER_SIZE, maxresults)
        params.update(kwargs)

        results, subresults = [], '_init'
        while subresults and maxresults > len(results):
            data = self.query(f'{self.METADATA}/library/sections/watchlist/{filter}', params=params)
            subresults = self.findItems(data)
            results += subresults[:maxresults - len(results)]
            params['X-Plex-Container-Start'] += params['X-Plex-Container-Size']

            # totalSize is available in first response, update maxresults from it
            totalSize = utils.cast(int, data.attrib.get('totalSize'))
            if maxresults > totalSize:
                maxresults = totalSize

        return self._toOnlineMetadata(results, **kwargs)

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
            self.query(f'{self.METADATA}/actions/addToWatchlist?ratingKey={ratingKey}', method=self._session.put)
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
            self.query(f'{self.METADATA}/actions/removeFromWatchlist?ratingKey={ratingKey}', method=self._session.put)
        return self

    def userState(self, item):
        """ Returns a :class:`~plexapi.myplex.UserState` object for the specified item.

            Parameters:
                item (:class:`~plexapi.video.Movie` or :class:`~plexapi.video.Show`): Item to return the user state.
        """
        ratingKey = item.guid.rsplit('/', 1)[-1]
        data = self.query(f"{self.METADATA}/library/metadata/{ratingKey}/userState")
        return self.findItem(data, cls=UserState)

    def searchDiscover(self, query, limit=30, libtype=None):
        """ Search for movies and TV shows in Discover.
            Returns a list of :class:`~plexapi.video.Movie` and :class:`~plexapi.video.Show` objects.

            Parameters:
                query (str): Search query.
                limit (int, optional): Limit to the specified number of results. Default 30.
                libtype (str, optional): 'movie' or 'show' to only return movies or shows, otherwise return all items.
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
            'includeMetadata': 1
        }

        data = self.query(f'{self.METADATA}/library/search', headers=headers, params=params)
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
        self._data = data
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
        self.servers = self.findItems(data, MyPlexServerShare)
        for server in self.servers:
            server.accountID = self.id

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

    def history(self, maxresults=9999999, mindate=None):
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
        self._data = data
        self.createdAt = utils.toDatetime(data.attrib.get('createdAt'))
        self.email = data.attrib.get('email')
        self.friend = utils.cast(bool, data.attrib.get('friend'))
        self.friendlyName = data.attrib.get('friendlyName')
        self.home = utils.cast(bool, data.attrib.get('home'))
        self.id = utils.cast(int, data.attrib.get('id'))
        self.server = utils.cast(bool, data.attrib.get('server'))
        self.servers = self.findItems(data, MyPlexServerShare)
        self.thumb = data.attrib.get('thumb')
        self.username = data.attrib.get('username', '')
        for server in self.servers:
            server.accountID = self.id


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
        self._data = data
        self.id = utils.cast(int, data.attrib.get('id'))
        self.key = utils.cast(int, data.attrib.get('key'))
        self.shared = utils.cast(bool, data.attrib.get('shared', '0'))
        self.title = data.attrib.get('title')
        self.type = data.attrib.get('type')
        self.sectionId = self.id  # For backwards compatibility
        self.sectionKey = self.key  # For backwards compatibility

    def history(self, maxresults=9999999, mindate=None):
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
        self._data = data
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
        https://plex.tv/api/resources?includeHttps=1&includeRelay=1

        Attributes:
            TAG (str): 'Device'
            key (str): 'https://plex.tv/api/resources?includeHttps=1&includeRelay=1'
            accessToken (str): This resources accesstoken.
            clientIdentifier (str): Unique ID for this resource.
            connections (list): List of :class:`~plexapi.myplex.ResourceConnection` objects
                for this resource.
            createdAt (datetime): Timestamp this resource first connected to your server.
            device (str): Best guess on the type of device this is (PS, iPhone, Linux, etc).
            home (bool): Unknown
            lastSeenAt (datetime): Timestamp this resource last connected.
            name (str): Descriptive name of this resource.
            owned (bool): True if this resource is one of your own (you logged into it).
            platform (str): OS the resource is running (Linux, Windows, Chrome, etc.)
            platformVersion (str): Version of the platform.
            presence (bool): True if the resource is online
            product (str): Plex product (Plex Media Server, Plex for iOS, Plex Web, etc.)
            productVersion (str): Version of the product.
            provides (str): List of services this resource provides (client, server,
                player, pubsub-player, etc.)
            synced (bool): Unknown (possibly True if the resource has synced content?)
    """
    TAG = 'Device'
    key = 'https://plex.tv/api/resources?includeHttps=1&includeRelay=1'

    # Default order to prioritize available resource connections
    DEFAULT_LOCATION_ORDER = ['local', 'remote', 'relay']
    DEFAULT_SCHEME_ORDER = ['https', 'http']

    def _loadData(self, data):
        self._data = data
        self.name = data.attrib.get('name')
        self.accessToken = logfilter.add_secret(data.attrib.get('accessToken'))
        self.product = data.attrib.get('product')
        self.productVersion = data.attrib.get('productVersion')
        self.platform = data.attrib.get('platform')
        self.platformVersion = data.attrib.get('platformVersion')
        self.device = data.attrib.get('device')
        self.clientIdentifier = data.attrib.get('clientIdentifier')
        self.createdAt = utils.toDatetime(data.attrib.get('createdAt'))
        self.lastSeenAt = utils.toDatetime(data.attrib.get('lastSeenAt'))
        self.provides = data.attrib.get('provides')
        self.owned = utils.cast(bool, data.attrib.get('owned'))
        self.home = utils.cast(bool, data.attrib.get('home'))
        self.synced = utils.cast(bool, data.attrib.get('synced'))
        self.presence = utils.cast(bool, data.attrib.get('presence'))
        self.connections = self.findItems(data, ResourceConnection)
        self.publicAddressMatches = utils.cast(bool, data.attrib.get('publicAddressMatches'))
        # This seems to only be available if its not your device (say are shared server)
        self.httpsRequired = utils.cast(bool, data.attrib.get('httpsRequired'))
        self.ownerid = utils.cast(int, data.attrib.get('ownerId', 0))
        self.sourceTitle = data.attrib.get('sourceTitle')  # owners plex username.

    def preferred_connections(
        self,
        ssl=None,
        locations=DEFAULT_LOCATION_ORDER,
        schemes=DEFAULT_SCHEME_ORDER,
    ):
        """ Returns a sorted list of the available connection addresses for this resource.
            Often times there is more than one address specified for a server or client.
            Default behavior will prioritize local connections before remote or relay and HTTPS before HTTP.

            Parameters:
                ssl (bool, optional): Set True to only connect to HTTPS connections. Set False to
                    only connect to HTTP connections. Set None (default) to connect to any
                    HTTP or HTTPS connection.
        """
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
        locations=DEFAULT_LOCATION_ORDER,
        schemes=DEFAULT_SCHEME_ORDER,
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
        connections = self.preferred_connections(ssl, locations, schemes)
        # Try connecting to all known resource connections in parallel, but
        # only return the first server (in order) that provides a response.
        cls = PlexServer if 'server' in self.provides else PlexClient
        listargs = [[cls, url, self.accessToken, timeout] for url in connections]
        log.debug('Testing %s resource connections..', len(listargs))
        results = utils.threaded(_connect, listargs)
        return _chooseConnection('Resource', self.name, results)


class ResourceConnection(PlexObject):
    """ Represents a Resource Connection object found within the
        :class:`~plexapi.myplex.MyPlexResource` objects.

        Attributes:
            TAG (str): 'Connection'
            address (str): Local IP address
            httpuri (str): Full local address
            local (bool): True if local
            port (int): 32400
            protocol (str): HTTP or HTTPS
            uri (str): External address
    """
    TAG = 'Connection'

    def _loadData(self, data):
        self._data = data
        self.protocol = data.attrib.get('protocol')
        self.address = data.attrib.get('address')
        self.port = utils.cast(int, data.attrib.get('port'))
        self.uri = data.attrib.get('uri')
        self.local = utils.cast(bool, data.attrib.get('local'))
        self.httpuri = f'http://{self.address}:{self.port}'
        self.relay = utils.cast(bool, data.attrib.get('relay'))


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
        self._data = data
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
        self.connections = self.listAttrs(data, 'uri', etag='Connection')

    def connect(self, timeout=None):
        """ Returns a new :class:`~plexapi.client.PlexClient` or :class:`~plexapi.server.PlexServer`
            Sometimes there is more than one address specified for a server or client.
            After trying to connect to all available addresses for this client and assuming
            at least one connection was successful, the PlexClient object is built and returned.

            Raises:
                :exc:`~plexapi.exceptions.NotFound`: When unable to connect to any addresses for this device.
        """
        cls = PlexServer if 'server' in self.provides else PlexClient
        listargs = [[cls, url, self.token, timeout] for url in self.connections]
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
        MyPlex PIN login class which supports getting the four character PIN which the user must
        enter on https://plex.tv/link to authenticate the client and provide an access token to
        create a :class:`~plexapi.myplex.MyPlexAccount` instance.
        This helper class supports a polling, threaded and callback approach.

        - The polling approach expects the developer to periodically check if the PIN login was
          successful using :func:`~plexapi.myplex.MyPlexPinLogin.checkLogin`.
        - The threaded approach expects the developer to call
          :func:`~plexapi.myplex.MyPlexPinLogin.run` and then at a later time call
          :func:`~plexapi.myplex.MyPlexPinLogin.waitForLogin` to wait for and check the result.
        - The callback approach is an extension of the threaded approach and expects the developer
          to pass the `callback` parameter to the call to :func:`~plexapi.myplex.MyPlexPinLogin.run`.
          The callback will be called when the thread waiting for the PIN login to succeed either
          finishes or expires. The parameter passed to the callback is the received authentication
          token or `None` if the login expired.

        Parameters:
            session (requests.Session, optional): Use your own session object if you want to
                cache the http responses from PMS
            requestTimeout (int): timeout in seconds on initial connect to plex.tv (default config.TIMEOUT).
            headers (dict): A dict of X-Plex headers to send with requests.
            oauth (bool): True to use Plex OAuth instead of PIN login.

        Attributes:
            PINS (str): 'https://plex.tv/api/v2/pins'
            CHECKPINS (str): 'https://plex.tv/api/v2/pins/{pinid}'
            POLLINTERVAL (int): 1
            finished (bool): Whether the pin login has finished or not.
            expired (bool): Whether the pin login has expired or not.
            token (str): Token retrieved through the pin login.
            pin (str): Pin to use for the login on https://plex.tv/link.
    """
    PINS = 'https://plex.tv/api/v2/pins'               # get
    CHECKPINS = 'https://plex.tv/api/v2/pins/{pinid}'  # get
    POLLINTERVAL = 1

    def __init__(self, session=None, requestTimeout=None, headers=None, oauth=False):
        super(MyPlexPinLogin, self).__init__()
        self._session = session or requests.Session()
        self._requestTimeout = requestTimeout or TIMEOUT
        self.headers = headers

        self._oauth = oauth
        self._loginTimeout = None
        self._callback = None
        self._thread = None
        self._abort = False
        self._id = None
        self._code = None
        self._getCode()

        self.finished = False
        self.expired = False
        self.token = None

    @property
    def pin(self):
        """ Return the 4 character PIN used for linking a device at https://plex.tv/link. """
        if self._oauth:
            raise BadRequest('Cannot use PIN for Plex OAuth login')
        return self._code

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
            'code': self._code
        }
        if forwardUrl:
            params['forwardUrl'] = forwardUrl

        return f'https://app.plex.tv/auth/#!?{urlencode(params)}'

    def run(self, callback=None, timeout=None):
        """ Starts the thread which monitors the PIN login state.
            Parameters:
                callback (Callable[str]): Callback called with the received authentication token (optional).
                timeout (int): Timeout in seconds waiting for the PIN login to succeed (optional).

            Raises:
                :class:`RuntimeError`: If the thread is already running.
                :class:`RuntimeError`: If the PIN login for the current PIN has expired.
        """
        if self._thread and not self._abort:
            raise RuntimeError('MyPlexPinLogin thread is already running')
        if self.expired:
            raise RuntimeError('MyPlexPinLogin has expired')

        self._loginTimeout = timeout
        self._callback = callback
        self._abort = False
        self.finished = False
        self._thread = threading.Thread(target=self._pollLogin, name='plexapi.myplex.MyPlexPinLogin')
        self._thread.start()

    def waitForLogin(self):
        """ Waits for the PIN login to succeed or expire.
            Parameters:
                callback (Callable[str]): Callback called with the received authentication token (optional).
                timeout (int): Timeout in seconds waiting for the PIN login to succeed (optional).

            Returns:
                `True` if the PIN login succeeded or `False` otherwise.
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
        """ Returns `True` if the PIN login has succeeded. """
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
            params = {'strong': True}
        else:
            params = None

        response = self._query(url, self._session.post, params=params)
        if not response:
            return None

        self._id = response.attrib.get('id')
        self._code = response.attrib.get('code')

        return self._code

    def _checkLogin(self):
        if not self._id:
            return False

        if self.token:
            return True

        url = self.CHECKPINS.format(pinid=self._id)
        response = self._query(url)
        if not response:
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
        if self.headers:
            headers.update(self.headers)
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
        data = response.text.encode('utf8')
        return ElementTree.fromstring(data) if data.strip() else None


def _connect(cls, url, token, timeout, results, i, job_is_done_event=None):
    """ Connects to the specified cls with url and token. Stores the connection
        information to results[i] in a threadsafe way.

        Arguments:
            cls: the class which is responsible for establishing connection, basically it's
                 :class:`~plexapi.client.PlexClient` or :class:`~plexapi.server.PlexServer`
            url (str): url which should be passed as `baseurl` argument to cls.__init__()
            token (str): authentication token which should be passed as `baseurl` argument to cls.__init__()
            timeout (int): timeout which should be passed as `baseurl` argument to cls.__init__()
            results (list): pre-filled list for results
            i (int): index of current job, should be less than len(results)
            job_is_done_event (:class:`~threading.Event`): is X_PLEX_ENABLE_FAST_CONNECT is True then the
                  event would be set as soon the connection is established
    """
    starttime = time.time()
    try:
        device = cls(baseurl=url, token=token, timeout=timeout)
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
        self.lastViewedAt = utils.toDatetime(data.attrib.get('lastViewedAt'))
        self.ratingKey = data.attrib.get('ratingKey')
        self.type = data.attrib.get('type')
        self.viewCount = utils.cast(int, data.attrib.get('viewCount', 0))
        self.viewedLeafCount = utils.cast(int, data.attrib.get('viewedLeafCount', 0))
        self.viewOffset = utils.cast(int, data.attrib.get('viewOffset', 0))
        self.viewState = data.attrib.get('viewState') == 'complete'
        self.watchlistedAt = utils.toDatetime(data.attrib.get('watchlistedAt'))
