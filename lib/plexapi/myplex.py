# -*- coding: utf-8 -*-
import copy
import requests
import time
from requests.status_codes import _codes as codes
from plexapi import BASE_HEADERS, CONFIG, TIMEOUT
from plexapi import log, logfilter, utils
from plexapi.base import PlexObject
from plexapi.exceptions import BadRequest, NotFound
from plexapi.client import PlexClient
from plexapi.compat import ElementTree
from plexapi.library import LibrarySection
from plexapi.server import PlexServer
from plexapi.utils import joinArgs


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
            id (str): Your Plex account ID.
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
    FRIENDSERVERS = 'https://plex.tv/api/servers/{machineId}/shared_servers/{serverId}'         # put with data
    PLEXSERVERS = 'https://plex.tv/api/servers/{machineId}'                                     # get
    FRIENDUPDATE = 'https://plex.tv/api/friends/{userId}'                                       # put with args, delete
    REMOVEINVITE = 'https://plex.tv/api/invites/requested/{userId}?friend=0&server=1&home=0'    # delete
    REQUESTED = 'https://plex.tv/api/invites/requested'                                         # get
    REQUESTS = 'https://plex.tv/api/invites/requests'                                           # get
    SIGNIN = 'https://plex.tv/users/sign_in.xml'                                                # get with auth
    WEBHOOKS = 'https://plex.tv/api/v2/user/webhooks'                                           # get, post with data
    # Key may someday switch to the following url. For now the current value works.
    # https://plex.tv/api/v2/user?X-Plex-Token={token}&X-Plex-Client-Identifier={clientId}
    key = 'https://plex.tv/users/account'

    def __init__(self, username=None, password=None, token=None, session=None, timeout=None):
        self._token = token
        self._session = session or requests.Session()
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
        self.id = data.attrib.get('id')
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
        # TODO: Fetch missing MyPlexAccount attributes
        self.subscriptionActive = None      # renamed on server
        self.subscriptionStatus = None      # renamed on server
        self.subscriptionPlan = None        # renmaed on server
        self.subscriptionFeatures = None    # renamed on server
        self.roles = None
        self.entitlements = None

    def device(self, name):
        """ Returns the :class:`~plexapi.myplex.MyPlexDevice` that matches the name specified.

            Parameters:
                name (str): Name to match against.
        """
        for device in self.devices():
            if device.name.lower() == name.lower():
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
            log.warning('BadRequest (%s) %s %s; %s' % (response.status_code, codename, response.url, errtext))
            raise BadRequest('(%s) %s %s; %s' % (response.status_code, codename, response.url, errtext))
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

    def inviteFriend(self, user, server, sections=None, allowSync=False, allowCameraUpload=False,
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

    def removeFriend(self, user):
        """ Remove the specified user from all sharing.

            Parameters:
                user (str): MyPlexUser, username, email of the user to be added.
        """
        user = self.user(user)
        url = self.FRIENDUPDATE if user.friend else self.REMOVEINVITE
        url = url.format(userId=user.id)
        return self.query(url, self._session.delete)

    def updateFriend(self, user, server, sections=None, removeSections=False, allowSync=None, allowCameraUpload=None,
                     allowChannels=None, filterMovies=None, filterTelevision=None, filterMusic=None):
        """ Update the specified user's share settings.

            Parameters:
                user (str): MyPlexUser, username, email of the user to be added.
                server (PlexServer): PlexServer object or machineIdentifier containing the library sections to share.
                sections: ([Section]): Library sections, names or ids to be shared (default None shares all sections).
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
        user = self.user(user.username if isinstance(user, MyPlexUser) else user)
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
            params = {'server_id': machineId, 'shared_server': {'library_section_ids': sectionIds,
                "invited_id": user.id}}
            url = self.FRIENDINVITE.format(machineId=machineId)
        # Remove share sections, add shares to user without shares, or update shares
        if sectionIds:
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
        """ Returns the :class:`~myplex.MyPlexUser` that matches the email or username specified.

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
        data = self.query(self.WEBHOOKS, self._session.post, data={'urls[]': urls})
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
        return self.query(url, method=self._session.put, params=params)


class MyPlexUser(PlexObject):
    """ This object represents non-signed in users such as friends and linked
        accounts. NOTE: This should not be confused with the :class:`~myplex.MyPlexAccount`
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

    def get_token(self, machineIdentifier):
        try:
            for item in self._server.query(self._server.FRIENDINVITE.format(machineId=machineIdentifier)):
                if utils.cast(int, item.attrib.get('userID')) == self.id:
                    return item.attrib.get('accessToken')
        except Exception:
            log.exception('Failed to get access token for %s' % self.title)


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
        self.serverId = utils.cast(int, data.attrib.get('serverId'))
        self.machineIdentifier = data.attrib.get('machineIdentifier')
        self.name = data.attrib.get('name')
        self.lastSeenAt = utils.toDatetime(data.attrib.get('lastSeenAt'))
        self.numLibraries = utils.cast(int, data.attrib.get('numLibraries'))
        self.allLibraries = utils.cast(bool, data.attrib.get('allLibraries'))
        self.owned = utils.cast(bool, data.attrib.get('owned'))
        self.pending = utils.cast(bool, data.attrib.get('pending'))

    def sections(self):
        url = MyPlexAccount.FRIENDSERVERS.format(machineId=self.machineIdentifier, serverId=self.id)
        data = self._server.query(url)
        sections = []

        for section in data.iter('Section'):
            if ElementTree.iselement(section):
                sections.append(Section(self, section, url))

        return sections


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
            connections (list): List of :class:`~myplex.ResourceConnection` objects
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
        """ Returns a new :class:`~server.PlexServer` or :class:`~client.PlexClient` object.
            Often times there is more than one address specified for a server or client.
            This function will prioritize local connections before remote and HTTPS before HTTP.
            After trying to connect to all available addresses for this resource and
            assuming at least one connection was successful, the PlexServer object is built and returned.

            Parameters:
                ssl (optional): Set True to only connect to HTTPS connections. Set False to
                    only connect to HTTP connections. Set None (default) to connect to any
                    HTTP or HTTPS connection.

            Raises:
                :class:`~plexapi.exceptions.NotFound`: When unable to connect to any addresses for this resource.
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
        log.info('Testing %s resource connections..', len(listargs))
        results = utils.threaded(_connect, listargs)
        return _chooseConnection('Resource', self.name, results)


class ResourceConnection(PlexObject):
    """ Represents a Resource Connection object found within the
        :class:`~myplex.MyPlexResource` objects.

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
                :class:`~plexapi.exceptions.NotFound`: When unable to connect to any addresses for this device.
        """
        cls = PlexServer if 'server' in self.provides else PlexClient
        listargs = [[cls, url, self.token, timeout] for url in self.connections]
        log.info('Testing %s device connections..', len(listargs))
        results = utils.threaded(_connect, listargs)
        return _chooseConnection('Device', self.name, results)

    def delete(self):
        """ Remove this device from your account. """
        key = 'https://plex.tv/devices/%s.xml' % self.id
        self._server.query(key, self._server._session.delete)


def _connect(cls, url, token, timeout, results, i):
    """ Connects to the specified cls with url and token. Stores the connection
        information to results[i] in a threadsafe way.
    """
    starttime = time.time()
    try:
        device = cls(baseurl=url, token=token, timeout=timeout)
        runtime = int(time.time() - starttime)
        results[i] = (url, token, device, runtime)
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
        log.info('%s connection %s (%ss): %s?X-Plex-Token=%s', ctype, okerr, runtime, url, token)
    results = [r[2] for r in results if r and r[2] is not None]
    if results:
        log.info('Connecting to %s: %s?X-Plex-Token=%s', ctype, results[0]._baseurl, results[0]._token)
        return results[0]
    raise NotFound('Unable to connect to %s: %s' % (ctype.lower(), name))
