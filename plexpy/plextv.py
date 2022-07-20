#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of Tautulli.
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
import json
import threading

import plexpy
from plexpy import helpers
from plexpy import http_handler
from plexpy import logger
from plexpy import users
from plexpy import session
from plexpy import database
from plexpy.servers import plexServer


class PlexTVaccounts(object):

    def __init__(self):
        self._accounts = []
        db = database.MonitorDatabase()
        result = db.select('SELECT * FROM users WHERE is_plextv = 1')
        for accountValues in result:
            account = PlexTV(account=accountValues)
            self._accounts.append(account)

    @property
    def accounts(self):
        return [account for account in self._accounts]

    def __iter__(self):
        for account in self._accounts:
            yield account

    def get_account(self, token=None, user_id=None):
        for account in self._accounts:
            if token and token == account.token:
                return account
            if user_id and user_id == account.user_id:
                return account
        return None

    def add_account(self, token=None, is_plextv=False, is_admin=False):
        new_account = PlexTV(token=token, is_plextv=is_plextv, is_admin=is_admin)
        existing_account = self.get_account(user_id=new_account.user_id)
        if existing_account:
            logger.info("Updating PlexTV Account %s" % existing_account.username)
            existing_account.reinit()
            existing_account.is_validated = new_account.is_validated
            for server in existing_account.servers:
                server.CONFIG.PMS_TOKEN = existing_account.token
            existing_account.start_servers()
            return existing_account
        else:
            logger.info("Adding PlexTV Account %s" % new_account.username)
            self._accounts.append(new_account)
            new_account.refresh_servers()
            for owned_server in new_account.servers:
                for unowned_server in plexpy.PMS_SERVERS.unowned_servers:
                    if owned_server.CONFIG.PMS_IDENTIFIER == unowned_server.CONFIG.PMS_IDENTIFIER:
                        plexpy.PMS_SERVERS.unowned_servers.remove(unowned_server)
            return new_account

    def reinit_account(self, token=None, user_id=None):
        if token or user_id:
            account = self.get_account(token=token, user_id=user_id)
            if account:
                account.reinit()
            else:
                db = database.MonitorDatabase()
                if token:
                    where = " AND user_token = %s" % token
                elif user_id:
                    where = " AND user_id = %s" % user_id
                else:
                    return None
                query = 'SELECT * FROM users WHERE is_plextv = 1 %s' % where
                result = db.select_single(query)
                account = PlexTV(account=result)
                self._accounts.append(account)
            return account
        return None

    def refresh_users(self):
        for account in self._accounts:
            account.refresh_users()

    def refresh_servers(self):
        for account in self._accounts:
            account.refresh_servers()

    def start_servers(self):
        for account in self._accounts:
            account.start_servers()

    def delete_account(self, token=None, user_id=None, keep_history=True):
        account = self.get_account(token=token, user_id=user_id)

        if account:
            logger.error(u"Tautulli PlexTV :: Deleting PlexTV Account %s" % account.username)
            self._accounts.remove(account)
            db = database.MonitorDatabase()
            db.action('UPDATE users SET is_plextv = 0 WHERE user_id = ?', [account.user_id])

            servers = account.servers
            for server in servers:
                server.delete(keep_history=keep_history)
                if keep_history:
                    plexpy.PMS_SERVERS.unowned_servers.append(server)
                    server.PLEXTV = None

            plexpy.PMS_SERVERS.refresh()

    def get_synced_items(self, machine_id=None, client_id_filter=None, user_id_filter=None,
                         rating_key_filter=None, sync_id_filter=None, server_id_filter=None):
        sync_list = []
        for account in self._accounts:
            if account.plexpass:
                result = account.get_synced_items(machine_id=machine_id, client_id_filter=client_id_filter,
                                                  user_id_filter=user_id_filter, server_id_filter=server_id_filter)
                if result:
                    sync_list.append(result)
        return sync_list

    def delete_sync(self, client_id, sync_id):
        for account in self._accounts:
            account.delete_sync(client_id=client_id, sync_id=sync_id)

    def get_plextv_friends(self, output_format=''):
        results = []
        for account in self._accounts:
            result = account.get_plextv_friends(output_format='dict')
            result['MediaContainer']['@friendlyName'] = account.username
            results.append(result)
        if output_format == 'json':
            results = json.dumps(results)
        return results

    def get_plextv_user_details(self, output_format=''):
        results = []
        for account in self._accounts:
            result = account.get_plextv_user_details(output_format='dict')
            results.append(result)
        if output_format == 'json':
            results = json.dumps(results)
        return results


class PlexTV(object):
    """
    Plex.tv authentication
    """

    def __init__(self, account=None, username=None, password=None, token=None, headers=None, is_admin=None, is_plextv=None):
        self.token = token
        self.user_id = None
        self.username = username
        self.password = password
        self.headers = headers
        self.is_validated = None
        self.urls = 'https://plex.tv'
        self.timeout = plexpy.CONFIG.PMS_TIMEOUT
        self.ssl_verify = plexpy.CONFIG.VERIFY_SSL_CERT
        self._servers = []

        db = database.MonitorDatabase()
        if token:
            account_details = self.get_plex_account_details()
            if account_details:
                self.user_id = account_details['user_id']
                self.token = account_details.get('user_token', None)
                self.username = account_details.get('username', None)
                self.is_validated = True

                account = db.select_single('SELECT * FROM users WHERE user_id = ?', args=[self.user_id])
                if account:
                    old_token = account['user_token']
                else:
                    account = {}
                    old_token = None
                account.update(account_details)
                if is_plextv:
                    account['is_plextv'] = 1
                    account['plexpass'] = int(self.get_plexpass_status())
                if is_admin:
                    account['is_admin'] = 1
                    account['is_allow_sync'] = 1
                keys_dict = {"user_id": account.pop('user_id')}
                db.upsert('users', account, keys_dict)
                account.update(keys_dict)

                if old_token and account['is_plextv'] and old_token != token:
                    db.action('UPDATE servers set pms_token = ? WHERE pms_token = ?', args=[token, old_token])

        if account:
            for k, v in account.items():
                vars(self)[k] = v
            self.token = account.get('user_token', None)
            self.username = account.get('username', None)

        if self.username is None and self.password is None:
            if not self.token:
                # Check if we should use the admin token, or the guest server token
                if session.get_session_user_id():
                    user_data = users.Users()
                    user_tokens = user_data.get_tokens(user_id=session.get_session_user_id())
                    self.token = user_tokens['server_token']

            if not self.token:
                logger.error(u"Tautulli PlexTV :: PlexTV called, but no token provided.")
                return

        if self.is_validated is None:
            self.is_validated = self.verify_token()

        result = db.select('SELECT * FROM servers WHERE pms_token = ?', args=[self.token])
        for serverValues in result:
            server = plexServer(serverValues)
            server.PLEXTV = self
            self._servers.append(server)

    def set_admin(self, checked=None):
        self.is_admin = checked
        db = database.MonitorDatabase()
        result = db.action('UPDATE users set is_admin = ? WHERE user_id = ?', args=(checked, self.user_id))
        return True

    @property
    def servers(self):
        return self._servers

    def reinit(self):
        user_details = users.Users().get_details(user_id=self.user_id)
        if user_details:
            for k, v in user_details.items():
                vars(self)[k] = v
            self.token = user_details['user_token']
            self.username = user_details['username']
        self.is_validated = self.verify_token()

    def verify_token(self):
        account = self.get_plex_account_details()
        if account:
            return True
        else:
            logger.warn(u"Tautulli PlexTV :: PlexTV account token may be expired for %s" % self.username)
            return False

    def start_servers(self):
        for server in self._servers:
            server.start()


    def stop_servers(self):
        for server in self._servers:
            server.shutdown()

    def refresh_servers(self):
        logger.info(u"Tautulli PlexTV :: Requesting Servers refresh for account %s" % self.username)
        if self.is_validated:
            thread_list = []
            new_servers = False

            servers = self.get_servers_list(include_cloud=True, all_servers=False)
            if not servers:
                logger.info(u"Tautulli PlexTV :: No Plex Servers Found for account %s" % self.username)
                return

            for server in servers:
                pmsServer = next((s for s in self._servers if s.CONFIG.PMS_IDENTIFIER == server['pms_identifier'] ), None)

                if pmsServer:
                    pmsServer.CONFIG.process_kwargs(server)
                    if not pmsServer.CONFIG.PMS_IS_DELETED:
                        t = threading.Thread(target=pmsServer.refresh)
                        t.start()
                        thread_list.append(t)
                else:
                    new_servers = True
                    pmsServer = plexServer(server)
                    self._servers.append(pmsServer)
                    pmsServer.PLEXTV = self
                    logger.info(u"Tautulli PlexTV :: %s: Server Discovered for account %s..."
                                % (pmsServer.CONFIG.PMS_NAME, self.username))
                    t = threading.Thread(target=pmsServer.refresh)
                    t.start()
                    thread_list.append(t)
            for t in thread_list:
                t.join()
            if new_servers:
                threading.Thread(target=self.refresh_users).start()

    def refresh_users(self):
        result = users.refresh_users(account=self)
        return result

    def get_plex_auth(self, output_format='raw'):
        uri = '/users/sign_in.xml'
        base64string = base64.b64encode(('%s:%s' % (self.username, self.password)).encode('utf-8'))
        headers = {'Content-Type': 'application/xml; charset=utf-8',
                   'Authorization': 'Basic %s' % base64string}

        request_handler = http_handler.HTTPHandler(urls=self.urls,
                                                   token=self.token,
                                                   timeout=self.timeout,
                                                   ssl_verify=self.ssl_verify,
                                                   headers=self.headers)
        request = request_handler.make_request(uri=uri,
                                               request_type='POST',
                                               headers=headers,
                                               output_format=output_format,
                                               no_token=True)

        return request

    def get_token(self):
        plextv_response = self.get_plex_auth(output_format='xml')

        if plextv_response:
            try:
                xml_head = plextv_response.getElementsByTagName('user')
                if xml_head:
                    user = {'auth_token': xml_head[0].getAttribute('authenticationToken'),
                            'user_id': xml_head[0].getAttribute('id')
                            }
                else:
                    logger.warn(u"Tautulli PlexTV :: Could not get Plex authentication token.")
            except Exception as e:
                logger.warn(u"Tautulli PlexTV :: Unable to parse XML for get_token: %s." % e)
                return None

            return user
        else:
            return None

    def get_plexpy_pms_token(self, force=False):
        if force:
            logger.debug(u"Tautulli PlexTV :: Forcing refresh of Plex.tv token.")
            devices_list = self.get_devices_list()
            device_id = next((d for d in devices_list if d['device_identifier'] == plexpy.CONFIG.PMS_UUID), {}).get('device_id', None)

            if device_id:
                logger.debug(u"Tautulli PlexTV :: Removing Tautulli from Plex.tv devices.")
                try:
                    self.delete_plextv_device(device_id=device_id)
                except:
                    logger.error(u"Tautulli PlexTV :: Failed to remove Tautulli from Plex.tv devices.")
                    return None
            else:
                logger.warn(u"Tautulli PlexTV :: No existing Tautulli device found.")
        
        logger.info(u"Tautulli PlexTV :: Fetching a new Plex.tv token for Tautulli.")
        user = self.get_token()
        if user:
            token = user['auth_token']
            plexpy.CONFIG.__setattr__('PMS_TOKEN', token)
            plexpy.CONFIG.write()
            logger.info(u"Tautulli PlexTV :: Updated Plex.tv token for Tautulli.")
            return token

    def get_server_token(self):
        servers = self.get_plextv_resources(output_format='xml')

        try:
            xml_head = servers.getElementsByTagName('Device')
        except Exception as e:
            logger.warn(u"Tautulli PlexTV :: Unable to parse XML for get_server_token: %s." % e)
            return None

        server_tokens = {}
        for a in xml_head:
            if 'server' in helpers.get_xml_attr(a, 'provides'):
                server_identifier = helpers.get_xml_attr(a, 'clientIdentifier')
                server_token = helpers.get_xml_attr(a, 'accessToken')
                server = plexpy.PMS_SERVERS.get_server_by_identifier(server_identifier)
                if server:
                    server_id = server.CONFIG.ID
                    server_tokens[server_id] = server_token

        return server_tokens

    def get_plextv_pin(self, pin='', output_format=''):
        request_handler = http_handler.HTTPHandler(urls=self.urls,
                                                   token=self.token,
                                                   timeout=self.timeout,
                                                   ssl_verify=self.ssl_verify,
                                                   headers=self.headers)
        if pin:
            uri = '/api/v2/pins/' + pin
            request = request_handler.make_request(uri=uri,
                                                   request_type='GET',
                                                   output_format=output_format,
                                                   no_token=True)
        else:
            uri = '/api/v2/pins?strong=true'
            request = request_handler.make_request(uri=uri,
                                                   request_type='POST',
                                                   output_format=output_format,
                                                   no_token=True)
        return request

    def get_pin(self, pin=''):
        plextv_response = self.get_plextv_pin(pin=pin,
                                              output_format='xml')

        if plextv_response:
            try:
                xml_head = plextv_response.getElementsByTagName('pin')
                if xml_head:
                    pin = {'id': xml_head[0].getAttribute('id'),
                           'code': xml_head[0].getAttribute('code'),
                           'token': xml_head[0].getAttribute('authToken')
                           }
                    return pin
                else:
                    logger.warn(u"Tautulli PlexTV :: Could not get Plex authentication pin.")
                    return None

            except Exception as e:
                logger.warn(u"Tautulli PlexTV :: Unable to parse XML for get_pin: %s." % e)
                return None

        else:
            return None

    def get_plextv_user_data(self):
        plextv_response = self.get_plex_auth(output_format='dict')

        if plextv_response:
            return plextv_response
        else:
            return []

    def get_plextv_friends(self, output_format=''):
        request_handler = http_handler.HTTPHandler(urls=self.urls,
                                                   token=self.token,
                                                   timeout=self.timeout,
                                                   ssl_verify=self.ssl_verify,
                                                   headers=self.headers)
        uri = '/api/users'
        request = request_handler.make_request(uri=uri,
                                               request_type='GET',
                                               output_format=output_format)

        return request

    def get_plextv_user_details(self, output_format=''):
        request_handler = http_handler.HTTPHandler(urls=self.urls,
                                                   token=self.token,
                                                   timeout=self.timeout,
                                                   ssl_verify=self.ssl_verify,
                                                   headers=self.headers)
        uri = '/users/account'
        request = request_handler.make_request(uri=uri,
                                               request_type='GET',
                                               output_format=output_format)

        return request

    def get_plextv_devices_list(self, output_format=''):
        request_handler = http_handler.HTTPHandler(urls=self.urls,
                                                   token=self.token,
                                                   timeout=self.timeout,
                                                   ssl_verify=self.ssl_verify,
                                                   headers=self.headers)
        uri = '/devices.xml'
        request = request_handler.make_request(uri=uri,
                                               request_type='GET',
                                               output_format=output_format)

        return request

    def get_plextv_server_list(self, output_format=''):
        request_handler = http_handler.HTTPHandler(urls=self.urls,
                                                   token=self.token,
                                                   timeout=self.timeout,
                                                   ssl_verify=self.ssl_verify,
                                                   headers=self.headers)
        uri = '/pms/servers.xml'
        request = request_handler.make_request(uri=uri,
                                               request_type='GET',
                                               output_format=output_format)

        return request

    def get_plextv_shared_servers(self, machine_id='', output_format=''):
        request_handler = http_handler.HTTPHandler(urls=self.urls,
                                                   token=self.token,
                                                   timeout=self.timeout,
                                                   ssl_verify=self.ssl_verify,
                                                   headers=self.headers)
        uri = '/api/servers/%s/shared_servers' % machine_id
        request = request_handler.make_request(uri=uri,
                                               request_type='GET',
                                               output_format=output_format)

        return request

    def get_plextv_sync_lists(self, machine_id='', output_format=''):
        request_handler = http_handler.HTTPHandler(urls=self.urls,
                                                   token=self.token,
                                                   timeout=self.timeout,
                                                   ssl_verify=self.ssl_verify,
                                                   headers=self.headers)
        uri = '/servers/%s/sync_lists' % machine_id
        request = request_handler.make_request(uri=uri,
                                               request_type='GET',
                                               output_format=output_format)

        return request

    def get_plextv_resources(self, include_https=False, output_format=''):
        request_handler = http_handler.HTTPHandler(urls=self.urls,
                                                   token=self.token,
                                                   timeout=self.timeout,
                                                   ssl_verify=self.ssl_verify,
                                                   headers=self.headers)
        if include_https:
            uri = '/api/resources?includeHttps=1'
        else:
            uri = '/api/resources'
        request = request_handler.make_request(uri=uri,
                                               request_type='GET',
                                               output_format=output_format)

        return request

    def get_plextv_downloads(self, plexpass=False, output_format=''):
        request_handler = http_handler.HTTPHandler(urls=self.urls,
                                                   token=self.token,
                                                   timeout=self.timeout,
                                                   ssl_verify=self.ssl_verify,
                                                   headers=self.headers)
        if plexpass:
            uri = '/api/downloads/5.json?channel=plexpass'
        else:
            uri = '/api/downloads/1.json'
        request = request_handler.make_request(uri=uri,
                                               request_type='GET',
                                               output_format=output_format)

        return request

    def delete_plextv_device(self, device_id='', output_format=''):
        request_handler = http_handler.HTTPHandler(urls=self.urls,
                                                   token=self.token,
                                                   timeout=self.timeout,
                                                   ssl_verify=self.ssl_verify,
                                                   headers=self.headers)
        uri = '/devices/%s.xml' % device_id
        request = request_handler.make_request(uri=uri,
                                               request_type='DELETE',
                                               output_format=output_format)

        return request

    def delete_plextv_device_sync_lists(self, client_id='', output_format=''):
        request_handler = http_handler.HTTPHandler(urls=self.urls,
                                                   token=self.token,
                                                   timeout=self.timeout,
                                                   ssl_verify=self.ssl_verify,
                                                   headers=self.headers)
        uri = '/devices/%s/sync_items' % client_id
        request = request_handler.make_request(uri=uri,
                                               request_type='GET',
                                               output_format=output_format)

        return request

    def delete_plextv_sync(self, client_id='', sync_id='', output_format=''):
        request_handler = http_handler.HTTPHandler(urls=self.urls,
                                                   token=self.token,
                                                   timeout=self.timeout,
                                                   ssl_verify=self.ssl_verify,
                                                   headers=self.headers)
        uri = '/devices/%s/sync_items/%s' % (client_id, sync_id)
        request = request_handler.make_request(uri=uri,
                                               request_type='DELETE',
                                               output_format=output_format)

        return request

    def cloud_server_status(self, output_format=''):
        request_handler = http_handler.HTTPHandler(urls=self.urls,
                                                   token=self.token,
                                                   timeout=self.timeout,
                                                   ssl_verify=self.ssl_verify,
                                                   headers=self.headers)
        uri = '/api/v2/cloud_server'
        request = request_handler.make_request(uri=uri,
                                               request_type='GET',
                                               output_format=output_format)

        return request

    def get_full_users_list(self):

        own_account = self.get_plextv_user_details(output_format='xml')
        friends_list = self.get_plextv_friends(output_format='xml')

        users_list = []

        try:
            xml_head = own_account.getElementsByTagName('user')
        except Exception as e:
            logger.warn(u"Tautulli PlexTV :: Unable to parse own account XML for get_full_users_list: %s." % e)
            return []

        for a in xml_head:
            own_details = {"user_id": helpers.get_xml_attr(a, 'id'),
                           "username": helpers.get_xml_attr(a, 'username'),
                           "thumb": helpers.get_xml_attr(a, 'thumb'),
                           "email": helpers.get_xml_attr(a, 'email'),
                           "is_home_user": helpers.get_xml_attr(a, 'home'),
                           "is_restricted": helpers.get_xml_attr(a, 'restricted'),
                           "filter_all": helpers.get_xml_attr(a, 'filterAll'),
                           "filter_movies": helpers.get_xml_attr(a, 'filterMovies'),
                           "filter_tv": helpers.get_xml_attr(a, 'filterTelevision'),
                           "filter_music": helpers.get_xml_attr(a, 'filterMusic'),
                           "filter_photos": helpers.get_xml_attr(a, 'filterPhotos'),
                           "user_token": helpers.get_xml_attr(a, 'authToken'),
                           "shared_libraries": [],
                           "plexpass": 1 if helpers.get_xml_attr(a.getElementsByTagName('subscription')[0], 'active') == '1' else 0,
            }
            for server in self._servers:
                if server.CONFIG.PMS_TOKEN == self.token:
                    own_details["shared_libraries"].append({"server_id": server.CONFIG.ID,
                                                            "server_token": helpers.get_xml_attr(a, 'authToken'),
                                                            })

            users_list.append(own_details)

        try:
            xml_head = friends_list.getElementsByTagName('User')
        except Exception as e:
            logger.warn(u"Tautulli PlexTV :: Unable to parse friends list XML for get_full_users_list: %s." % e)
            return []

        for a in xml_head:
            friend = {"user_id": helpers.get_xml_attr(a, 'id'),
                      "username": helpers.get_xml_attr(a, 'title'),
                      "thumb": helpers.get_xml_attr(a, 'thumb'),
                      "email": helpers.get_xml_attr(a, 'email'),
                      "is_home_user": helpers.get_xml_attr(a, 'home'),
                      "is_allow_sync": helpers.get_xml_attr(a, 'allowSync'),
                      "is_restricted": helpers.get_xml_attr(a, 'restricted'),
                      "filter_all": helpers.get_xml_attr(a, 'filterAll'),
                      "filter_movies": helpers.get_xml_attr(a, 'filterMovies'),
                      "filter_tv": helpers.get_xml_attr(a, 'filterTelevision'),
                      "filter_music": helpers.get_xml_attr(a, 'filterMusic'),
                      "filter_photos": helpers.get_xml_attr(a, 'filterPhotos')
                      }

            users_list.append(friend)

        user_map = {}
        for server in self._servers:
            if server.CONFIG.PMS_IS_ENABLED == True and server.CONFIG.PMS_TOKEN == self.token:
                shared_servers = self.get_plextv_shared_servers(machine_id=server.CONFIG.PMS_IDENTIFIER,
                                                                output_format='xml')
                try:
                    xml_head = shared_servers.getElementsByTagName('SharedServer')
                except Exception as e:
                    logger.warn(u"Tautulli PlexTV :: %s: Unable to parse shared server list XML for get_full_users_list: %s."
                                % (server.CONFIG.PMS_NAME, e))
                    return []

                for a in xml_head:
                    user_id = helpers.get_xml_attr(a, 'userID')
                    server_token = helpers.get_xml_attr(a, 'accessToken')

                    sections = a.getElementsByTagName('Section')
                    shared_libraries = [helpers.get_xml_attr(s, 'key')
                                        for s in sections if helpers.get_xml_attr(s, 'shared') == '1']
                    if user_id not in user_map:
                        user_map[user_id] = {'shared_libraries': []}
                    user_map[user_id]['shared_libraries'].append({'server_token': server_token,
                                                                  'server_id': server.CONFIG.ID,
                                                                  'shared_libraries': shared_libraries
                                                                  })

        for u in users_list:
            d = user_map.get(u['user_id'], {})
            u.update(d)

        return users_list

    def get_synced_items(self, machine_id=None, client_id_filter=None, user_id_filter=None,
                         rating_key_filter=None, sync_id_filter=None, server_id_filter=None):

        if isinstance(rating_key_filter, list):
            rating_key_filter = [str(k) for k in rating_key_filter]
        elif rating_key_filter:
            rating_key_filter = [str(rating_key_filter)]

        if isinstance(user_id_filter, list):
            user_id_filter = [str(k) for k in user_id_filter]
        elif user_id_filter:
            user_id_filter = [str(user_id_filter)]

        user_data = users.Users()

        synced_items = []

        for server in self._servers:
            if server_id_filter and int(server_id_filter) != server.CONFIG.ID:
                continue
            if not session.allow_session_server(server.CONFIG.ID):
                continue

            machine_id = server.CONFIG.PMS_IDENTIFIER
            sync_list = self.get_plextv_sync_lists(machine_id, output_format='xml')

            try:
                xml_head = sync_list.getElementsByTagName('SyncList')
            except Exception as e:
                logger.warn(u"Tautulli PlexTV :: Unable to parse XML for get_synced_items: %s." % e)
                return {}

            for a in xml_head:
                client_id = helpers.get_xml_attr(a, 'clientIdentifier')

                # Filter by client_id
                if client_id_filter and str(client_id_filter) != client_id:
                    continue

                sync_list_id = helpers.get_xml_attr(a, 'id')
                sync_device = a.getElementsByTagName('Device')

                for device in sync_device:
                    device_user_id = helpers.get_xml_attr(device, 'userID')
                    try:
                        device_username = user_data.get_details(user_id=device_user_id)['username']
                        device_friendly_name = user_data.get_details(user_id=device_user_id)['friendly_name']
                    except:
                        device_username = ''
                        device_friendly_name = ''
                    device_name = helpers.get_xml_attr(device, 'name')
                    device_product = helpers.get_xml_attr(device, 'product')
                    device_product_version = helpers.get_xml_attr(device, 'productVersion')
                    device_platform = helpers.get_xml_attr(device, 'platform')
                    device_platform_version = helpers.get_xml_attr(device, 'platformVersion')
                    device_type = helpers.get_xml_attr(device, 'device')
                    device_model = helpers.get_xml_attr(device, 'model')
                    device_last_seen = helpers.get_xml_attr(device, 'lastSeenAt')

                # Filter by user_id
                if user_id_filter and device_user_id not in user_id_filter:
                    continue

                for synced in a.getElementsByTagName('SyncItems'):
                    sync_item = synced.getElementsByTagName('SyncItem')
                    for item in sync_item:

                        for location in item.getElementsByTagName('Location'):
                            clean_uri = helpers.get_xml_attr(location, 'uri').split('%2F')

                        rating_key = next((clean_uri[(idx + 1) % len(clean_uri)]
                                           for idx, item in enumerate(clean_uri) if item == 'metadata'), None)

                        # Filter by rating_key
                        if rating_key_filter and rating_key not in rating_key_filter:
                            continue

                        sync_id = helpers.get_xml_attr(item, 'id')

                        # Filter by sync_id
                        if sync_id_filter and str(sync_id_filter) != sync_id:
                            continue

                        sync_version = helpers.get_xml_attr(item, 'version')
                        sync_root_title = helpers.get_xml_attr(item, 'rootTitle')
                        sync_title = helpers.get_xml_attr(item, 'title')
                        sync_metadata_type = helpers.get_xml_attr(item, 'metadataType')
                        sync_content_type = helpers.get_xml_attr(item, 'contentType')

                        for status in item.getElementsByTagName('Status'):
                            status_failure_code = helpers.get_xml_attr(status, 'failureCode')
                            status_failure = helpers.get_xml_attr(status, 'failure')
                            status_state = helpers.get_xml_attr(status, 'state')
                            status_item_count = helpers.get_xml_attr(status, 'itemsCount')
                            status_item_complete_count = helpers.get_xml_attr(status, 'itemsCompleteCount')
                            status_item_downloaded_count = helpers.get_xml_attr(status, 'itemsDownloadedCount')
                            status_item_ready_count = helpers.get_xml_attr(status, 'itemsReadyCount')
                            status_item_successful_count = helpers.get_xml_attr(status, 'itemsSuccessfulCount')
                            status_total_size = helpers.get_xml_attr(status, 'totalSize')
                            status_item_download_percent_complete = helpers.get_percent(
                                status_item_downloaded_count, status_item_count)

                        for settings in item.getElementsByTagName('MediaSettings'):
                            settings_video_bitrate = helpers.get_xml_attr(settings, 'maxVideoBitrate')
                            settings_video_quality = helpers.get_xml_attr(settings, 'videoQuality')
                            settings_video_resolution = helpers.get_xml_attr(settings, 'videoResolution')
                            settings_audio_boost = helpers.get_xml_attr(settings, 'audioBoost')
                            settings_audio_bitrate = helpers.get_xml_attr(settings, 'musicBitrate')
                            settings_photo_quality = helpers.get_xml_attr(settings, 'photoQuality')
                            settings_photo_resolution = helpers.get_xml_attr(settings, 'photoResolution')

                        sync_details = {"device_name": helpers.sanitize(device_name),
                                        "server_id": server.CONFIG.ID,
                                        "server_name": server.CONFIG.PMS_NAME,
                                        "platform": helpers.sanitize(device_platform),
                                        "user_id": device_user_id,
                                        "user": helpers.sanitize(device_friendly_name),
                                        "username": helpers.sanitize(device_username),
                                        "root_title": helpers.sanitize(sync_root_title),
                                        "sync_title": helpers.sanitize(sync_title),
                                        "metadata_type": sync_metadata_type,
                                        "content_type": sync_content_type,
                                        "rating_key": rating_key,
                                        "state": status_state,
                                        "item_count": status_item_count,
                                        "item_complete_count": status_item_complete_count,
                                        "item_downloaded_count": status_item_downloaded_count,
                                        "item_downloaded_percent_complete": status_item_download_percent_complete,
                                        "video_bitrate": settings_video_bitrate,
                                        "audio_bitrate": settings_audio_bitrate,
                                        "photo_quality": settings_photo_quality,
                                        "video_quality": settings_video_quality,
                                        "total_size": status_total_size,
                                        "failure": status_failure,
                                        "client_id": client_id,
                                        "sync_id": sync_id
                                        }

                        synced_items.append(sync_details)

        return session.filter_session_info(synced_items, filter_key='user_id')

    def delete_sync(self, client_id, sync_id):
        logger.info(u"Tautulli PlexTV :: Deleting sync item '%s'." % sync_id)
        self.delete_plextv_sync(client_id=client_id, sync_id=sync_id)

    def get_server_connections(self, pms_identifier='', pms_ip='', pms_port=32400, include_https=True):

        if not pms_identifier:
            logger.error(u"Tautulli PlexTV :: Unable to retrieve server connections: no pms_identifier provided.")
            return {}

        plextv_resources = self.get_plextv_resources(include_https=include_https,
                                                     output_format='xml')
        try:
            xml_head = plextv_resources.getElementsByTagName('Device')
        except Exception as e:
            logger.warn(u"Tautulli PlexTV :: Unable to parse XML for get_server_urls: %s." % e)
            return {}

        # Function to get all connections for a device
        def get_connections(device):
            conn = []
            connections = device.getElementsByTagName('Connection')

            server = {'pms_identifier': helpers.get_xml_attr(device, 'clientIdentifier'),
                      'pms_name': helpers.get_xml_attr(device, 'name'),
                      'pms_version': helpers.get_xml_attr(device, 'productVersion'),
                      'pms_platform': helpers.get_xml_attr(device, 'platform'),
                      'pms_presence': helpers.get_xml_attr(device, 'presence'),
                      'pms_is_cloud': 1 if helpers.get_xml_attr(device, 'platform') == 'Cloud' else 0
                      }

            for c in connections:
                server_details = {'protocol': helpers.get_xml_attr(c, 'protocol'),
                                  'address': helpers.get_xml_attr(c, 'address'),
                                  'port': helpers.get_xml_attr(c, 'port'),
                                  'uri': helpers.get_xml_attr(c, 'uri'),
                                  'local': helpers.get_xml_attr(c, 'local')
                                  }
                conn.append(server_details)

            server['connections'] = conn
            return server

        server = {}

        # Try to match the device
        for a in xml_head:
            if helpers.get_xml_attr(a, 'clientIdentifier') == pms_identifier:
                server = get_connections(a)
                break

        # Else no device match found
        if not server:
            # Try to match the PMS_IP and PMS_PORT
            for a in xml_head:
                if helpers.get_xml_attr(a, 'provides') == 'server':
                    connections = a.getElementsByTagName('Connection')

                    for connection in connections:
                        if helpers.get_xml_attr(connection, 'address') == pms_ip and \
                                helpers.get_xml_attr(connection, 'port') == str(pms_port):
                            server = get_connections(a)
                            break

                    if server.get('connections'):
                        break

        return server

    def get_server_times(self):
        servers = self.get_plextv_server_list(output_format='xml')

        try:
            xml_head = servers.getElementsByTagName('Server')
        except Exception as e:
            logger.warn(u"Tautulli PlexTV :: Unable to parse XML for get_server_times: %s." % e)
            return {}

        server_list = {}
        for a in xml_head:
            server_times = {"created_at": helpers.get_xml_attr(a, 'createdAt'),
                            "updated_at": helpers.get_xml_attr(a, 'updatedAt'),
                            "version": helpers.get_xml_attr(a, 'version')
                            }
            pms_identifier = helpers.get_xml_attr(a, 'machineIdentifier')
            pms_name = plexpy.PMS_SERVERS.get_server_by_identifier(pms_identifier=pms_identifier)
            server_list[pms_name] = server_times

        return server_list

    def get_servers_list(self, include_cloud=True, all_servers=False):
        """ Query plex for all servers online. Returns the ones you own in a selectize format """

        # Try to discover localhost server
        local_server = {'pms_ssl': '0',
                        'pms_ip': '127.0.0.1',
                        'pms_port': '32400',
                        'pms_name': 'Local',
                        'pms_url': 'http://127.0.0.1:32400',
                        'pms_is_remote': '0',
                        'pms_is_cloud': '0',
                        'pms_token': self.token,
                        }
        local_machine_identifier = None
        request_handler = http_handler.HTTPHandler(urls='http://127.0.0.1:32400', timeout=1,
                                                   ssl_verify=False, silent=True, token=self.token)
        request = request_handler.make_request(uri='/', request_type='GET', output_format='xml')
        if request:
            xml_head = request.getElementsByTagName('MediaContainer')[0]
            local_machine_identifier = xml_head.getAttribute('machineIdentifier')
            server = self.get_server_connections(pms_identifier=local_machine_identifier)
            if server:
                server.pop('pms_presence')
                conn = server.pop('connections')
                local_server['pms_uri'] = conn[0]['uri']
                local_server.update(server)

        servers = self.get_plextv_resources(include_https=True, output_format='xml')
        clean_servers = []

        try:
            xml_head = servers.getElementsByTagName('MediaContainer')
        except Exception as e:
            logger.warn(u"Tautulli PlexTV :: Failed to get servers from plex: %s." % e)
            return []

        for a in xml_head:
            if a.getAttribute('size'):
                if a.getAttribute('size') == '0':
                    return []

            if a.getElementsByTagName('Device'):
                devices = a.getElementsByTagName('Device')

                for d in devices:
                    if helpers.get_xml_attr(d, 'presence') == '1' and \
                            helpers.get_xml_attr(d, 'owned') == '1' and \
                            helpers.get_xml_attr(d, 'provides') == 'server':

                        is_cloud = (helpers.get_xml_attr(d, 'platform').lower() == 'cloud')
                        if not include_cloud and is_cloud:
                            continue

                        connections = d.getElementsByTagName('Connection')

                        for c in connections:
                            if not all_servers:
                                # If this is a remote server don't show any local IPs.
                                if helpers.get_xml_attr(d, 'publicAddressMatches') == '0' and \
                                        helpers.get_xml_attr(c, 'local') == '1':
                                    continue

                                # If this is a local server don't show any remote IPs.
                                if helpers.get_xml_attr(d, 'publicAddressMatches') == '1' and \
                                        helpers.get_xml_attr(c, 'local') == '0':
                                    continue

                            server = {'pms_ssl': 1 if is_cloud else int(helpers.get_xml_attr(d, 'httpsRequired') or 0),
                                      'pms_identifier': helpers.get_xml_attr(d, 'clientIdentifier'),
                                      'pms_name': helpers.get_xml_attr(d, 'name'),
                                      'pms_ip': helpers.get_xml_attr(c, 'address'),
                                      'pms_port': helpers.get_xml_attr(c, 'port'),
                                      'pms_uri': helpers.get_xml_attr(c, 'uri'),
                                      'pms_is_remote': int(not int(helpers.get_xml_attr(c, 'local') or 0)),
                                      'pms_platform': helpers.get_xml_attr(d, 'platform'),
                                      'pms_version': helpers.get_xml_attr(d, 'productVersion'),
                                      'pms_is_cloud': int(is_cloud or 0),
                                      'pms_token': self.token,
                                      }

                            request_handler = http_handler.HTTPHandler(urls=server['pms_uri'],
                                                                       token=self.token,
                                                                       timeout=self.timeout)
                            prefs = request_handler.make_request(uri='/:/prefs',
                                                                 request_type='GET',
                                                                 output_format='xml')
                            pms_ssl_pref = 0
                            if prefs:
                                xml_head = prefs.getElementsByTagName('Setting')
                                for a in xml_head:
                                    if helpers.get_xml_attr(a, 'id') == 'secureConnections':
                                        pms_ssl_pref = helpers.get_xml_attr(a, 'value')
                                        break

                            if pms_ssl_pref:
                                server['pms_ssl_pref'] = int(pms_ssl_pref)

                            pms_url = 'http://{hostname}:{port}'.format(hostname=helpers.get_xml_attr(c, 'address'),
                                                                        port=helpers.get_xml_attr(c, 'port'))
                            if server['pms_ssl']:
                                server['pms_url'] = server['pms_uri']
                            else:
                                server['pms_url'] = pms_url

                            clean_servers.append(server)

        if local_machine_identifier:
            found = False
            for server in clean_servers:
                if server['pms_identifier'] == local_machine_identifier:
                    local_server.pop('pms_name')
                    server.update(local_server)
                    found = True
                    break
            if not found:
                local_server['pms_identifier'] = local_machine_identifier
                clean_servers.append(local_server)

        clean_servers.sort(key=lambda s: (s['pms_name'], -int(s['pms_is_remote']), s['pms_ip']))

        return clean_servers

    def get_plexpass_status(self):
        account_data = self.get_plextv_user_details(output_format='xml')

        try:
            subscription = account_data.getElementsByTagName('subscription')
        except Exception as e:
            logger.warn(u"Tautulli PlexTV :: Unable to parse XML for get_plexpass_status: %s." % e)
            return False

        if subscription and helpers.get_xml_attr(subscription[0], 'active') == '1':
            return True
        else:
            logger.debug(u"Tautulli PlexTV :: Plex Pass subscription not found for %s" % self.username)
            return False

    def get_devices_list(self):
        devices = self.get_plextv_devices_list(output_format='xml')

        try:
            xml_head = devices.getElementsByTagName('Device')
        except Exception as e:
            logger.warn(u"Tautulli PlexTV :: Unable to parse XML for get_devices_list: %s." % e)
            return []

        devices_list = []
        for a in xml_head:
            device = {"device_name": helpers.get_xml_attr(a, 'name'),
                      "product": helpers.get_xml_attr(a, 'product'),
                      "product_version": helpers.get_xml_attr(a, 'productVersion'),
                      "platform": helpers.get_xml_attr(a, 'platform'),
                      "platform_version": helpers.get_xml_attr(a, 'platformVersion'),
                      "device": helpers.get_xml_attr(a, 'device'),
                      "model": helpers.get_xml_attr(a, 'model'),
                      "vendor": helpers.get_xml_attr(a, 'vendor'),
                      "provides": helpers.get_xml_attr(a, 'provides'),
                      "device_identifier": helpers.get_xml_attr(a, 'clientIdentifier'),
                      "device_id": helpers.get_xml_attr(a, 'id'),
                      "token": helpers.get_xml_attr(a, 'token')
                      }
            devices_list.append(device)

        return devices_list

    def get_cloud_server_status(self, server):
        cloud_status = self.cloud_server_status(output_format='xml')

        try:
            status_info = cloud_status.getElementsByTagName('info')
        except Exception as e:
            logger.warn(u"Tautulli PlexTV :: Unable to parse XML for get_cloud_server_status: %s." % e)
            return False

        for info in status_info:
            servers = info.getElementsByTagName('server')
            for s in servers:
                if helpers.get_xml_attr(s, 'address') == server.CONFIG.PMS_IP:
                    if helpers.get_xml_attr(info, 'running') == '1':
                        return True
                    else:
                        return False

    def get_plex_account_details(self):
        account_data = self.get_plextv_user_details(output_format='xml')

        try:
            xml_head = account_data.getElementsByTagName('user')
        except Exception as e:
            logger.warn(u"Tautulli PlexTV :: Unable to parse XML for get_plex_account_details: %s." % e)
            return None

        for a in xml_head:
            account_details = {"user_id": int(helpers.get_xml_attr(a, 'id')),
                               "username": helpers.get_xml_attr(a, 'username'),
                               "thumb": helpers.get_xml_attr(a, 'thumb'),
                               "email": helpers.get_xml_attr(a, 'email'),
                               "is_home_user": helpers.get_xml_attr(a, 'home'),
                               "is_restricted": helpers.get_xml_attr(a, 'restricted'),
                               "filter_all": helpers.get_xml_attr(a, 'filterAll'),
                               "filter_movies": helpers.get_xml_attr(a, 'filterMovies'),
                               "filter_tv": helpers.get_xml_attr(a, 'filterTelevision'),
                               "filter_music": helpers.get_xml_attr(a, 'filterMusic'),
                               "filter_photos": helpers.get_xml_attr(a, 'filterPhotos'),
                               "user_token": helpers.get_xml_attr(a, 'authToken')
                               }
            return account_details

    def get_server_resources(self, pms_identifier='', pms_ip='', pms_port=32400, include_https=True, **kwargs):
        logger.info(u"Tautulli PlexTV :: Requesting resources for server...")

        server = {'pms_ip': pms_ip,
                  'pms_port': pms_port,
                  }

        result = self.get_server_connections(pms_identifier=pms_identifier,
                                             pms_ip=pms_ip,
                                             pms_port=pms_port,
                                             include_https=True)

        if result:
            connections = result.pop('connections', [])
            presence = result.pop('pms_presence', 0)
            server.update(result)
        else:
            connections = []
            presence = 0

        if connections:
            # Get connection with matching address, otherwise return first connection
            conn = next((c for c in connections if c['address'] == pms_ip
                         and c['port'] == str(pms_port)), connections[0])
            server['pms_is_remote'] = int(not int(conn['local']))
            server['pms_ssl'] = (1 if conn['protocol'] == 'https' else 0)

            request_handler = http_handler.HTTPHandler(urls=conn['uri'],
                                                       token=self.token,
                                                       timeout=self.timeout)
            prefs = request_handler.make_request(uri='/:/prefs',
                                                 request_type='GET',
                                                 output_format='xml')
            pms_ssl_pref = 0
            if prefs:
                xml_head = prefs.getElementsByTagName('Setting')
                for a in xml_head:
                    if helpers.get_xml_attr(a, 'id') == 'secureConnections':
                        pms_ssl_pref = helpers.get_xml_attr(a, 'value')
                        break
            server['pms_ssl_pref'] = pms_ssl_pref

            scheme = ('https' if server['pms_ssl'] else 'http')
            pms_url = '{scheme}://{hostname}:{port}'.format(scheme=scheme,
                                                            hostname=pms_ip,
                                                            port=pms_port)
            server['pms_url'] = pms_url

        server['pms_is_cloud'] = int(server['pms_is_cloud'])

        return server
