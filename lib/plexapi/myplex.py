# -*- coding: utf-8 -*-
import copy
import threading
import time
from xml.etree import ElementTree

import requests
from plexapi import (BASE_HEADERS, CONFIG, TIMEOUT, X_PLEX_ENABLE_FAST_CONNECT,
                     X_PLEX_IDENTIFIER, log, logfilter, utils)
from plexapi.base import PlexObject
from plexapi.client import PlexClient
from plexapi.exceptions import BadRequest, NotFound, Unauthorized
from plexapi.library import LibrarySection
from plexapi.server import PlexServer
from plexapi.sonos import PlexSonosClient
from plexapi.sync import SyncItem, SyncList
from plexapi.utils import joinArgs
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
            queueEmail (str): Email address to add items to your `Watch Later` queue.
            queueUid (str): Unknown.
            restricted (bool): Unknown.
            roles: (List<str>) Lit of account roles. Plexpass membership listed here.
            scrobbleTypes (str): Description
            secure (bool): Description
            subscriptionActive (bool): True if your subsctiption is active.
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
    HOMEUSERCREATE = 'https://plex.tv/api/home/users?title={title}'                             # post with data
    EXISTINGUSER = 'https://plex.tv/api/home/users?invitedEmail={username}'                     # post with data
    FRIENDSERVERS = 'https://plex.tv/api/servers/{machineId}/shared_servers/{serverId}'         # put with data
    PLEXSERVERS = 'https://plex.tv/api/servers/{machineId}'                                     # get
    FRIENDUPDATE = 'https://plex.tv/api/friends/{userId}'                                       # put with args, delete
    REMOVEHOMEUSER = 'https://plex.tv/api/home/users/{userId}'                                  # delete
    REMOVEINVITE = 'https://plex.tv/api/invites/requested/{userId}?friend=1&server=1&home=1'    # delete
    REQUESTED = 'https://plex.tv/api/invites/requested'                                         # get
    REQUESTS = 'https://plex.tv/api/invites/requests'                                           # get
    SIGNIN = 'https://plex.tv/users/sign_in.xml'                                                # get with auth
    WEBHOOKS = 'https://plex.tv/api/v2/user/webhooks'                                           # get, post with data
    LINK = 'https://plex.tv/api/v2/pins/link'                                                   # put
    # Hub sections
    VOD = 'https://vod.provider.plex.tv/'                                                       # get
    WEBSHOWS = 'https://webshows.provider.plex.tv/'                                             # get
    NEWS = 'https://news.provider.plex.tv/'                                                     # get
    PODCASTS = 'https://podcasts.provider.plex.tv/'                                             # get
    MUSIC = 'https://music.provider.plex.tv/'                                                   # get
    # Key may someday switch to the following url. For now the current value works.
    # https://plex.tv/api/v2/user?X-Plex-Token={token}&X-Plex-Client-Identifier={clientId}
    key = 'https://plex.tv/users/account'

    def __init__(self, username=None, password=None, token=None, session=None, timeout=None):
        self._token = token or CONFIG.get('auth.server_token')
        self._session = session or requests.Session()
        self._sonos_cache = []
        self._sonos_cache_timestamp = 0
        data, initpath = self._signin(username, password, timeout)
        super(MyPlexAccount, self).__init__(self, data, initpath)

    def _signin(self, username, password, timeout):
        if self._token:
            return self.query(self.key), self.key
        username = username or CONFIG.get('auth.myplex_username')
        password = password or CONFIG.get('auth.myplex_password')
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

        self.subscriptionFeatures = []
        for feature in subscription.iter('feature'):
            self.subscriptionFeatures.append(feature.attrib.get('id'))

        roles = data.find('roles')
        self.roles = []
        if roles is not None:
            for role in roles.iter('role'):
                self.roles.append(role.attrib.get('id'))

        entitlements = data.find('entitlements')
        self.entitlements = []
        for entitlement in entitlements.iter('entitlement'):
            self.entitlements.append(entitlement.attrib.get('id'))

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
        raise NotFound('Unable to find device %s' % name)

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
            message = '(%s) %s; %s %s' % (response.status_code, codename, response.url, errtext)
            if response.status_code == 401:
                raise Unauthorized(message)
            elif response.status_code == 404:
                raise NotFound(message)
            else:
                raise BadRequest(message)
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
        raise NotFound('Unable to find resource %s' % name)

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
                user (str): MyPlexUser, username, email of the user to be added.
                server (PlexServer): PlexServer object or machineIdentifier containing the library sections to share.
                sections ([Section]): Library sections, names or ids to be shared (default None).
                    [Section] must be defined in order to update shared sections.
                allowSync (Bool): Set True to allow user to sync content.
                allowCameraUpload (Bool): Set True to allow user to upload photos.
                allowChannels (Bool): Set True to allow user to utilize installed channels.
                filterMovies (Dict): Dict containing key 'contentRating' and/or 'label' each set to a list of
                    values to be filtered. ex: {'contentRating':['G'], 'label':['foo']}
                filterTelevision (Dict): Dict containing key 'contentRating' and/or 'label' each set to a list of
                    values to be filtered. ex: {'contentRating':['G'], 'label':['foo']}
                filterMusic (Dict): Dict containing key 'label' set to a list of values to be filtered.
                    ex: {'label':['foo']}
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
                user (str): MyPlexUser, username, email of the user to be added.
                server (PlexServer): PlexServer object or machineIdentifier containing the library sections to share.
                sections ([Section]): Library sections, names or ids to be shared (default None shares all sections).
                allowSync (Bool): Set True to allow user to sync content.
                allowCameraUpload (Bool): Set True to allow user to upload photos.
                allowChannels (Bool): Set True to allow user to utilize installed channels.
                filterMovies (Dict): Dict containing key 'contentRating' and/or 'label' each set to a list of
                    values to be filtered. ex: {'contentRating':['G'], 'label':['foo']}
                filterTelevision (Dict): Dict containing key 'contentRating' and/or 'label' each set to a list of
                    values to be filtered. ex: {'contentRating':['G'], 'label':['foo']}
                filterMusic (Dict): Dict containing key 'label' set to a list of values to be filtered.
                    ex: {'label':['foo']}
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
                user (str): MyPlexUser, username, email of the user to be added.
                server (PlexServer): PlexServer object or machineIdentifier containing the library sections to share.
                sections ([Section]): Library sections, names or ids to be shared (default None shares all sections).
                allowSync (Bool): Set True to allow user to sync content.
                allowCameraUpload (Bool): Set True to allow user to upload photos.
                allowChannels (Bool): Set True to allow user to utilize installed channels.
                filterMovies (Dict): Dict containing key 'contentRating' and/or 'label' each set to a list of
                    values to be filtered. ex: {'contentRating':['G'], 'label':['foo']}
                filterTelevision (Dict): Dict containing key 'contentRating' and/or 'label' each set to a list of
                    values to be filtered. ex: {'contentRating':['G'], 'label':['foo']}
                filterMusic (Dict): Dict containing key 'label' set to a list of values to be filtered.
                    ex: {'label':['foo']}
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
        """ Remove the specified user from all sharing.

            Parameters:
                user (str): MyPlexUser, username, email of the user to be added.
        """
        user = self.user(user)
        url = self.FRIENDUPDATE if user.friend else self.REMOVEINVITE
        url = url.format(userId=user.id)
        return self.query(url, self._session.delete)

    def removeHomeUser(self, user):
        """ Remove the specified managed user from home.

            Parameters:
                user (str): MyPlexUser, username, email of the user to be removed from home.
        """
        user = self.user(user)
        url = self.REMOVEHOMEUSER.format(userId=user.id)
        return self.query(url, self._session.delete)

    def updateFriend(self, user, server, sections=None, removeSections=False, allowSync=None, allowCameraUpload=None,
                     allowChannels=None, filterMovies=None, filterTelevision=None, filterMusic=None):
        """ Update the specified user's share settings.

            Parameters:
                user (str): MyPlexUser, username, email of the user to be added.
                server (PlexServer): PlexServer object or machineIdentifier containing the library sections to share.
                sections: ([Section]): Library sections, names or ids to be shared (default None).
                    [Section] must be defined in order to update shared sections.
                removeSections (Bool): Set True to remove all shares. Supersedes sections.
                allowSync (Bool): Set True to allow user to sync content.
                allowCameraUpload (Bool): Set True to allow user to upload photos.
                allowChannels (Bool): Set True to allow user to utilize installed channels.
                filterMovies (Dict): Dict containing key 'contentRating' and/or 'label' each set to a list of
                    values to be filtered. ex: {'contentRating':['G'], 'label':['foo']}
                filterTelevision (Dict): Dict containing key 'contentRating' and/or 'label' each set to a list of
                    values to be filtered. ex: {'contentRating':['G'], 'label':['foo']}
                filterMusic (Dict): Dict containing key 'label' set to a list of values to be filtered.
                    ex: {'label':['foo']}
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
            url += joinArgs(params)
            response_filters = self.query(url, self._session.put)
        return response_servers, response_filters

    def user(self, username):
        """ Returns the :class:`~plexapi.myplex.MyPlexUser` that matches the email or username specified.

            Parameters:
                username (str): Username, email or id of the user to return.
        """
        for user in self.users():
            # Home users don't have email, username etc.
            if username.lower() == user.title.lower():
                return user

            elif (user.username and user.email and user.id and username.lower() in
                  (user.username.lower(), user.email.lower(), str(user.id))):
                return user

        raise NotFound('Unable to find user %s' % username)

    def users(self):
        """ Returns a list of all :class:`~plexapi.myplex.MyPlexUser` objects connected to your account.
            This includes both friends and pending invites. You can reference the user.friend to
            distinguish between the two.
        """
        friends = [MyPlexUser(self, elem) for elem in self.query(MyPlexUser.key)]
        requested = [MyPlexUser(self, elem, self.REQUESTED) for elem in self.query(self.REQUESTED)]
        return friends + requested

    def _getSectionIds(self, server, sections):
        """ Converts a list of section objects or names to sectionIds needed for library sharing. """
        if not sections: return []
        # Get a list of all section ids for looking up each section.
        allSectionIds = {}
        machineIdentifier = server.machineIdentifier if isinstance(server, PlexServer) else server
        url = self.PLEXSERVERS.replace('{machineId}', machineIdentifier)
        data = self.query(url, self._session.get)
        for elem in data[0]:
            allSectionIds[elem.attrib.get('id', '').lower()] = elem.attrib.get('id')
            allSectionIds[elem.attrib.get('title', '').lower()] = elem.attrib.get('id')
            allSectionIds[elem.attrib.get('key', '').lower()] = elem.attrib.get('id')
        log.debug(allSectionIds)
        # Convert passed in section items to section ids from above lookup
        sectionIds = []
        for section in sections:
            sectionKey = section.key if isinstance(section, LibrarySection) else section
            sectionIds.append(allSectionIds[sectionKey.lower()])
        return sectionIds

    def _filterDictToStr(self, filterDict):
        """ Converts friend filters to a string representation for transport. """
        values = []
        for key, vals in filterDict.items():
            if key not in ('contentRating', 'label'):
                raise BadRequest('Unknown filter key: %s', key)
            values.append('%s=%s' % (key, '%2C'.join(vals)))
        return '|'.join(values)

    def addWebhook(self, url):
        # copy _webhooks and append url
        urls = self._webhooks[:] + [url]
        return self.setWebhooks(urls)

    def deleteWebhook(self, url):
        urls = copy.copy(self._webhooks)
        if url not in urls:
            raise BadRequest('Webhook does not exist: %s' % url)
        urls.remove(url)
        return self.setWebhooks(urls)

    def setWebhooks(self, urls):
        log.info('Setting webhooks: %s' % urls)
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
            If neither `client` nor `clientId` provided the clientId would be set to current clients`s identifier.
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
            If neither `client` nor `clientId` provided the clientId would be set to current clients`s identifier.

            Returns:
                :class:`~plexapi.sync.SyncItem`: an instance of created syncItem.

            Raises:
                :exc:`~plexapi.exceptions.BadRequest`: When client with provided clientId wasn`t found.
                :exc:`~plexapi.exceptions.BadRequest`: Provided client doesn`t provides `sync-target`.
        """
        if not client and not clientId:
            clientId = X_PLEX_IDENTIFIER

        if not client:
            for device in self.devices():
                if device.clientIdentifier == clientId:
                    client = device
                    break

            if not client:
                raise BadRequest('Unable to find client by clientId=%s', clientId)

        if 'sync-target' not in client.provides:
            raise BadRequest('Received client doesn`t provides sync-target')

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
        data = self.query(url, method=self._session.post, headers={
            'Content-type': 'x-www-form-urlencoded',
        }, params=params)

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
            raise BadRequest('(%s) %s %s; %s' % (response.status_code, codename, response.url, errtext))
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

    def videoOnDemand(self):
        """ Returns a list of VOD Hub items :class:`~plexapi.library.Hub`
        """
        req = requests.get(self.VOD + 'hubs/', headers={'X-Plex-Token': self._token})
        elem = ElementTree.fromstring(req.text)
        return self.findItems(elem)

    def webShows(self):
        """ Returns a list of Webshow Hub items :class:`~plexapi.library.Hub`
        """
        req = requests.get(self.WEBSHOWS + 'hubs/', headers={'X-Plex-Token': self._token})
        elem = ElementTree.fromstring(req.text)
        return self.findItems(elem)

    def news(self):
        """ Returns a list of News Hub items :class:`~plexapi.library.Hub`
        """
        req = requests.get(self.NEWS + 'hubs/sections/all', headers={'X-Plex-Token': self._token})
        elem = ElementTree.fromstring(req.text)
        return self.findItems(elem)

    def podcasts(self):
        """ Returns a list of Podcasts Hub items :class:`~plexapi.library.Hub`
        """
        req = requests.get(self.PODCASTS + 'hubs/', headers={'X-Plex-Token': self._token})
        elem = ElementTree.fromstring(req.text)
        return self.findItems(elem)

    def tidal(self):
        """ Returns a list of tidal Hub items :class:`~plexapi.library.Hub`
        """
        req = requests.get(self.MUSIC + 'hubs/', headers={'X-Plex-Token': self._token})
        elem = ElementTree.fromstring(req.text)
        return self.findItems(elem)

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
            thumb (str): Link to the users avatar.
            title (str): Seems to be an aliad for username.
            username (str): User's username.
            servers: Servers shared between user and friend
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
            log.exception('Failed to get access token for %s' % self.title)

    def server(self, name):
        """ Returns the :class:`~plexapi.myplex.MyPlexServerShare` that matches the name specified.

            Parameters:
                name (str): Name of the server to return.
        """
        for server in self.servers:
            if name.lower() == server.name.lower():
                return server

        raise NotFound('Unable to find server %s' % name)

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


class Section(PlexObject):
    """ This refers to a shared section. The raw xml for the data presented here
        can be found at: https://plex.tv/api/servers/{machineId}/shared_servers/{serverId}

        Attributes:
            TAG (str): section
            id (int): shared section id
            sectionKey (str): what key we use for this section
            title (str): Title of the section
            sectionId (str): shared section id
            type (str): movie, tvshow, artist
            shared (bool): If this section is shared with the user

    """
    TAG = 'Section'

    def _loadData(self, data):
        self._data = data
        # self.id = utils.cast(int, data.attrib.get('id'))  # Havnt decided if this should be changed.
        self.sectionKey = data.attrib.get('key')
        self.title = data.attrib.get('title')
        self.sectionId = data.attrib.get('id')
        self.type = data.attrib.get('type')
        self.shared = utils.cast(bool, data.attrib.get('shared'))

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

        raise NotFound('Unable to find section %s' % name)

    def sections(self):
        """ Returns a list of all :class:`~plexapi.myplex.Section` objects shared with this user.
        """
        url = MyPlexAccount.FRIENDSERVERS.format(machineId=self.machineIdentifier, serverId=self.id)
        data = self._server.query(url)
        sections = []

        for section in data.iter('Section'):
            if ElementTree.iselement(section):
                sections.append(Section(self, section, url))

        return sections

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

    def connect(self, ssl=None, timeout=None):
        """ Returns a new :class:`~plexapi.server.PlexServer` or :class:`~plexapi.client.PlexClient` object.
            Often times there is more than one address specified for a server or client.
            This function will prioritize local connections before remote and HTTPS before HTTP.
            After trying to connect to all available addresses for this resource and
            assuming at least one connection was successful, the PlexServer object is built and returned.

            Parameters:
                ssl (optional): Set True to only connect to HTTPS connections. Set False to
                    only connect to HTTP connections. Set None (default) to connect to any
                    HTTP or HTTPS connection.

            Raises:
                :exc:`~plexapi.exceptions.NotFound`: When unable to connect to any addresses for this resource.
        """
        # Sort connections from (https, local) to (http, remote)
        # Only check non-local connections unless we own the resource
        connections = sorted(self.connections, key=lambda c: c.local, reverse=True)
        owned_or_unowned_non_local = lambda x: self.owned or (not self.owned and not x.local)
        https = [c.uri for c in connections if owned_or_unowned_non_local(c)]
        http = [c.httpuri for c in connections if owned_or_unowned_non_local(c)]
        cls = PlexServer if 'server' in self.provides else PlexClient
        # Force ssl, no ssl, or any (default)
        if ssl is True: connections = https
        elif ssl is False: connections = http
        else: connections = https + http
        # Try connecting to all known resource connections in parellel, but
        # only return the first server (in order) that provides a response.
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
        self.httpuri = 'http://%s:%s' % (self.address, self.port)
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
        self.connections = [connection.attrib.get('uri') for connection in data.iter('Connection')]

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
        key = 'https://plex.tv/devices/%s.xml' % self.id
        self._server.query(key, self._server._session.delete)

    def syncItems(self):
        """ Returns an instance of :class:`~plexapi.sync.SyncList` for current device.

            Raises:
                :exc:`~plexapi.exceptions.BadRequest`: when the device doesn`t provides `sync-target`.
        """
        if 'sync-target' not in self.provides:
            raise BadRequest('Requested syncList for device which do not provides sync-target')

        return self._server.syncItems(client=self)


class MyPlexPinLogin(object):
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

        Attributes:
            PINS (str): 'https://plex.tv/api/v2/pins'
            CHECKPINS (str): 'https://plex.tv/api/v2/pins/{pinid}'
            LINK (str): 'https://plex.tv/api/v2/pins/link'
            POLLINTERVAL (int): 1
            finished (bool): Whether the pin login has finished or not.
            expired (bool): Whether the pin login has expired or not.
            token (str): Token retrieved through the pin login.
            pin (str): Pin to use for the login on https://plex.tv/link.
    """
    PINS = 'https://plex.tv/api/v2/pins'               # get
    CHECKPINS = 'https://plex.tv/api/v2/pins/{pinid}'  # get
    POLLINTERVAL = 1

    def __init__(self, session=None, requestTimeout=None, headers=None):
        super(MyPlexPinLogin, self).__init__()
        self._session = session or requests.Session()
        self._requestTimeout = requestTimeout or TIMEOUT
        self.headers = headers

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
        return self._code

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
        response = self._query(url, self._session.post)
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
            raise BadRequest('(%s) %s %s; %s' % (response.status_code, codename, response.url, errtext))
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
    raise NotFound('Unable to connect to %s: %s' % (ctype.lower(), name))
