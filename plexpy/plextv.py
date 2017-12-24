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

import plexpy
import common
import helpers
import http_handler
import logger
import users
import pmsconnect
import session


def get_server_resources(return_presence=False):
    if not return_presence:
        logger.info(u"Tautulli PlexTV :: Requesting resources for server...")

    server = {'pms_name': plexpy.CONFIG.PMS_NAME,
              'pms_version': plexpy.CONFIG.PMS_VERSION,
              'pms_platform': plexpy.CONFIG.PMS_PLATFORM,
              'pms_ip': plexpy.CONFIG.PMS_IP,
              'pms_port': plexpy.CONFIG.PMS_PORT,
              'pms_ssl': plexpy.CONFIG.PMS_SSL,
              'pms_is_remote': plexpy.CONFIG.PMS_IS_REMOTE,
              'pms_is_cloud': plexpy.CONFIG.PMS_IS_CLOUD,
              'pms_url': plexpy.CONFIG.PMS_URL,
              'pms_url_manual': plexpy.CONFIG.PMS_URL_MANUAL
              }

    if server['pms_url_manual'] and server['pms_ssl'] or server['pms_is_cloud']:
        scheme = 'https'
    else:
        scheme = 'http'

    fallback_url = '{scheme}://{hostname}:{port}'.format(scheme=scheme,
                                                         hostname=server['pms_ip'],
                                                         port=server['pms_port'])

    plex_tv = PlexTV()
    result = plex_tv.get_server_connections(pms_identifier=plexpy.CONFIG.PMS_IDENTIFIER,
                                            pms_ip=server['pms_ip'],
                                            pms_port=server['pms_port'],
                                            include_https=server['pms_ssl'])

    if result:
        connections = result.pop('connections', [])
        server.update(result)
        presence = server.pop('server_presence', 0)
    else:
        connections = []
        presence = 0

    if return_presence:
        return presence

    plexpass = plex_tv.get_plexpass_status()
    server['pms_plexpass'] = int(plexpass)

    # Only need to retrieve PMS_URL if using SSL
    if not server['pms_url_manual'] and server['pms_ssl']:
        if connections:
            if server['pms_is_remote']:
                # Get all remote connections
                conns = [c for c in connections if
                         c['local'] == '0' and ('plex.direct' in c['uri'] or 'plex.service' in c['uri'])]
            else:
                # Get all local connections
                conns = [c for c in connections if
                         c['local'] == '1' and ('plex.direct' in c['uri'] or 'plex.service' in c['uri'])]

            if conns:
                # Get connection with matching address, otherwise return first connection
                conn = next((c for c in conns if c['address'] == server['pms_ip']
                             and c['port'] == str(server['pms_port'])), conns[0])
                server['pms_url'] = conn['uri']
                logger.info(u"Tautulli PlexTV :: Server URL retrieved.")

        # get_server_urls() failed or PMS_URL not found, fallback url doesn't use SSL
        if not server['pms_url']:
            server['pms_url'] = fallback_url
            logger.warn(u"Tautulli PlexTV :: Unable to retrieve server URLs. Using user-defined value without SSL.")

        # Not using SSL, remote has no effect
    else:
        server['pms_url'] = fallback_url
        logger.info(u"Tautulli PlexTV :: Using user-defined URL.")

    plexpy.CONFIG.process_kwargs(server)
    plexpy.CONFIG.write()


class PlexTV(object):
    """
    Plex.tv authentication
    """

    def __init__(self, username=None, password=None, token=None):
        self.username = username
        self.password = password
        self.token = token

        self.urls = 'https://plex.tv'
        self.timeout = plexpy.CONFIG.PMS_TIMEOUT
        self.ssl_verify = plexpy.CONFIG.VERIFY_SSL_CERT

        if not self.token:
            # Check if we should use the admin token, or the guest server token
            if session.get_session_user_id():
                user_data = users.Users()
                user_tokens = user_data.get_tokens(user_id=session.get_session_user_id())
                self.token = user_tokens['server_token']
            else:
                self.token = plexpy.CONFIG.PMS_TOKEN

        if not self.token:
            logger.error(u"Tautulli PlexTV :: PlexTV called, but no token provided.")
            return

        self.request_handler = http_handler.HTTPHandler(urls=self.urls,
                                                        token=self.token,
                                                        timeout=self.timeout,
                                                        ssl_verify=self.ssl_verify)

    def get_plex_auth(self, output_format='raw'):
        uri = '/users/sign_in.xml'
        base64string = base64.b64encode(('%s:%s' % (self.username, self.password)).encode('utf-8'))
        headers = {'Content-Type': 'application/xml; charset=utf-8',
                   'X-Plex-Device-Name': 'Tautulli',
                   'X-Plex-Product': 'Tautulli',
                   'X-Plex-Version': plexpy.common.VERSION_NUMBER,
                   'X-Plex-Platform': plexpy.common.PLATFORM,
                   'X-Plex-Platform-Version': plexpy.common.PLATFORM_VERSION,
                   'X-Plex-Client-Identifier': plexpy.CONFIG.PMS_UUID,
                   'Authorization': 'Basic %s' % base64string
                   }
        
        request = self.request_handler.make_request(uri=uri,
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
        servers = self.get_plextv_server_list(output_format='xml')
        server_token = ''

        try:
            xml_head = servers.getElementsByTagName('Server')
        except Exception as e:
            logger.warn(u"Tautulli PlexTV :: Unable to parse XML for get_server_token: %s." % e)
            return None

        for a in xml_head:
            if helpers.get_xml_attr(a, 'machineIdentifier') == plexpy.CONFIG.PMS_IDENTIFIER:
                server_token = helpers.get_xml_attr(a, 'accessToken')
                break

        return server_token

    def get_plextv_user_data(self):
        plextv_response = self.get_plex_auth(output_format='dict')

        if plextv_response:
            return plextv_response
        else:
            return []

    def get_plextv_friends(self, output_format=''):
        uri = '/api/users'
        request = self.request_handler.make_request(uri=uri,
                                                    request_type='GET',
                                                    output_format=output_format)

        return request

    def get_plextv_user_details(self, output_format=''):
        uri = '/users/account'
        request = self.request_handler.make_request(uri=uri,
                                                    request_type='GET',
                                                    output_format=output_format)

        return request

    def get_plextv_devices_list(self, output_format=''):
        uri = '/devices.xml'
        request = self.request_handler.make_request(uri=uri,
                                                    request_type='GET',
                                                    output_format=output_format)

        return request

    def get_plextv_server_list(self, output_format=''):
        uri = '/pms/servers.xml'
        request = self.request_handler.make_request(uri=uri,
                                                    request_type='GET',
                                                    output_format=output_format)

        return request

    def get_plextv_sync_lists(self, machine_id='', output_format=''):
        uri = '/servers/%s/sync_lists' % machine_id
        request = self.request_handler.make_request(uri=uri,
                                                    request_type='GET',
                                                    output_format=output_format)

        return request

    def get_plextv_resources(self, include_https=False, output_format=''):
        if include_https:
            uri = '/api/resources?includeHttps=1'
        else:
            uri = '/api/resources'
        request = self.request_handler.make_request(uri=uri,
                                                    request_type='GET',
                                                    output_format=output_format)

        return request

    def get_plextv_downloads(self, plexpass=False, output_format=''):
        if plexpass:
            uri = '/api/downloads/1.json?channel=plexpass'
        else:
            uri = '/api/downloads/1.json'
        request = self.request_handler.make_request(uri=uri,
                                                    request_type='GET',
                                                    output_format=output_format)

        return request

    def delete_plextv_device(self, device_id='', output_format=''):
        uri = '/devices/%s.xml' % device_id
        request = self.request_handler.make_request(uri=uri,
                                                    request_type='DELETE',
                                                    output_format=output_format)

        return request

    def delete_plextv_device_sync_lists(self, client_id='', output_format=''):
        uri = '/devices/%s/sync_items' % client_id
        request = self.request_handler.make_request(uri=uri,
                                                    request_type='GET',
                                                    output_format=output_format)

        return request

    def delete_plextv_sync(self, client_id='', sync_id='', output_format=''):
        uri = '/devices/%s/sync_items/%s' % (client_id, sync_id)
        request = self.request_handler.make_request(uri=uri,
                                                    request_type='DELETE',
                                                    output_format=output_format)

        return request

    def get_full_users_list(self):
        friends_list = self.get_plextv_friends(output_format='xml')
        own_account = self.get_plextv_user_details(output_format='xml')
        users_list = []

        try:
            xml_head = own_account.getElementsByTagName('user')
        except Exception as e:
            logger.warn(u"Tautulli PlexTV :: Unable to parse own account XML for get_full_users_list: %s." % e)
            return {}

        for a in xml_head:
            own_details = {"user_id": helpers.get_xml_attr(a, 'id'),
                            "username": helpers.get_xml_attr(a, 'username'),
                            "thumb": helpers.get_xml_attr(a, 'thumb'),
                            "email": helpers.get_xml_attr(a, 'email'),
                            "is_home_user": helpers.get_xml_attr(a, 'home'),
                            "is_allow_sync": None,
                            "is_restricted": helpers.get_xml_attr(a, 'restricted'),
                            "filter_all": helpers.get_xml_attr(a, 'filterAll'),
                            "filter_movies": helpers.get_xml_attr(a, 'filterMovies'),
                            "filter_tv": helpers.get_xml_attr(a, 'filterTelevision'),
                            "filter_music": helpers.get_xml_attr(a, 'filterMusic'),
                            "filter_photos": helpers.get_xml_attr(a, 'filterPhotos')
                            }

            users_list.append(own_details)

        try:
            xml_head = friends_list.getElementsByTagName('User')
        except Exception as e:
            logger.warn(u"Tautulli PlexTV :: Unable to parse friends list XML for get_full_users_list: %s." % e)
            return {}

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

        return users_list

    def get_synced_items(self, machine_id=None, client_id_filter=None, user_id_filter=None, rating_key_filter=None):
        sync_list = self.get_plextv_sync_lists(machine_id, output_format='xml')
        user_data = users.Users()

        synced_items = []

        try:
            xml_head = sync_list.getElementsByTagName('SyncList')
        except Exception as e:
            logger.warn(u"Tautulli PlexTV :: Unable to parse XML for get_synced_items: %s." % e)
            return {}

        for a in xml_head:
            client_id = helpers.get_xml_attr(a, 'clientIdentifier')

            # Filter by client_id
            if client_id_filter and client_id_filter != client_id:
                continue

            sync_id = helpers.get_xml_attr(a, 'id')
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
            if user_id_filter and user_id_filter != device_user_id:
                continue

            for synced in a.getElementsByTagName('SyncItems'):
                sync_item = synced.getElementsByTagName('SyncItem')
                for item in sync_item:

                    for location in item.getElementsByTagName('Location'):
                        clean_uri = helpers.get_xml_attr(location, 'uri').split('%2F')

                    rating_key = next((clean_uri[(idx + 1) % len(clean_uri)]
                                       for idx, item in enumerate(clean_uri) if item == 'metadata'), None)

                    # Filter by rating_key
                    if rating_key_filter and rating_key_filter != rating_key:
                        continue

                    sync_id = helpers.get_xml_attr(item, 'id')
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
                        settings_audio_boost = helpers.get_xml_attr(settings, 'audioBoost')
                        settings_music_bitrate = helpers.get_xml_attr(settings, 'musicBitrate')
                        settings_photo_quality = helpers.get_xml_attr(settings, 'photoQuality')
                        settings_photo_resolution = helpers.get_xml_attr(settings, 'photoResolution')
                        settings_video_quality = helpers.get_xml_attr(settings, 'videoQuality')
                        settings_video_resolution = helpers.get_xml_attr(settings, 'videoResolution')

                    sync_details = {"device_name": helpers.sanitize(device_name),
                                    "platform": helpers.sanitize(device_platform),
                                    "username": helpers.sanitize(device_username),
                                    "friendly_name": helpers.sanitize(device_friendly_name),
                                    "user_id": device_user_id,
                                    "root_title": helpers.sanitize(sync_root_title),
                                    "title": helpers.sanitize(sync_title),
                                    "metadata_type": sync_metadata_type,
                                    "content_type": sync_content_type,
                                    "rating_key": rating_key,
                                    "state": status_state,
                                    "item_count": status_item_count,
                                    "item_complete_count": status_item_complete_count,
                                    "item_downloaded_count": status_item_downloaded_count,
                                    "item_downloaded_percent_complete": status_item_download_percent_complete,
                                    "music_bitrate": settings_music_bitrate,
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
        server_times = {}

        try:
            xml_head = servers.getElementsByTagName('Server')
        except Exception as e:
            logger.warn(u"Tautulli PlexTV :: Unable to parse XML for get_server_times: %s." % e)
            return {}

        for a in xml_head:
            if helpers.get_xml_attr(a, 'machineIdentifier') == plexpy.CONFIG.PMS_IDENTIFIER:
                server_times = {"created_at": helpers.get_xml_attr(a, 'createdAt'),
                                "updated_at": helpers.get_xml_attr(a, 'updatedAt'),
                                "version": helpers.get_xml_attr(a, 'version')
                                }
                break

        return server_times

    def discover(self, include_cloud=True, all_servers=False):
        """ Query plex for all servers online. Returns the ones you own in a selectize format """
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

                        if not include_cloud and helpers.get_xml_attr(d, 'platform').lower() == 'cloud':
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

                            server = {'httpsRequired': helpers.get_xml_attr(d, 'httpsRequired'),
                                      'clientIdentifier': helpers.get_xml_attr(d, 'clientIdentifier'),
                                      'label': helpers.get_xml_attr(d, 'name'),
                                      'ip': helpers.get_xml_attr(c, 'address'),
                                      'port': helpers.get_xml_attr(c, 'port'),
                                      'local': helpers.get_xml_attr(c, 'local'),
                                      'value': helpers.get_xml_attr(c, 'address')
                                      }
                            clean_servers.append(server)

        return clean_servers

    def get_plex_downloads(self):
        logger.debug(u"Tautulli PlexTV :: Retrieving current server version.")
        pmsconnect.PmsConnect().set_server_version()

        logger.debug(u"Tautulli PlexTV :: Plex update channel is %s." % plexpy.CONFIG.PMS_UPDATE_CHANNEL)
        plex_downloads = self.get_plextv_downloads(plexpass=(plexpy.CONFIG.PMS_UPDATE_CHANNEL == 'plexpass'))

        try:
            available_downloads = json.loads(plex_downloads)
        except Exception as e:
            logger.warn(u"Tautulli PlexTV :: Unable to load JSON for get_plex_updates.")
            return {}

        # Get the updates for the platform
        pms_platform = common.PMS_PLATFORM_NAME_OVERRIDES.get(plexpy.CONFIG.PMS_PLATFORM, plexpy.CONFIG.PMS_PLATFORM)
        platform_downloads = available_downloads.get('computer').get(pms_platform) or \
            available_downloads.get('nas').get(pms_platform)

        if not platform_downloads:
            logger.error(u"Tautulli PlexTV :: Unable to retrieve Plex updates: Could not match server platform: %s."
                         % pms_platform)
            return {}

        v_old = helpers.cast_to_int("".join(v.zfill(4) for v in plexpy.CONFIG.PMS_VERSION.split('-')[0].split('.')[:4]))
        v_new = helpers.cast_to_int("".join(v.zfill(4) for v in platform_downloads.get('version', '').split('-')[0].split('.')[:4]))

        if not v_old:
            logger.error(u"Tautulli PlexTV :: Unable to retrieve Plex updates: Invalid current server version: %s."
                         % plexpy.CONFIG.PMS_VERSION)
            return {}
        if not v_new:
            logger.error(u"Tautulli PlexTV :: Unable to retrieve Plex updates: Invalid new server version: %s."
                         % platform_downloads.get('version'))
            return {}

        # Get proper download
        releases = platform_downloads.get('releases', [{}])
        release = next((r for r in releases if r['distro'] == plexpy.CONFIG.PMS_UPDATE_DISTRO and 
                        r['build'] == plexpy.CONFIG.PMS_UPDATE_DISTRO_BUILD), releases[0])

        download_info = {'update_available': v_new > v_old,
                         'platform': platform_downloads.get('name'),
                         'release_date': platform_downloads.get('release_date'),
                         'version': platform_downloads.get('version'),
                         'requirements': platform_downloads.get('requirements'),
                         'extra_info': platform_downloads.get('extra_info'),
                         'changelog_added': platform_downloads.get('items_added'),
                         'changelog_fixed': platform_downloads.get('items_fixed'),
                         'label': release.get('label'),
                         'distro': release.get('distro'),
                         'distro_build': release.get('build'),
                         'download_url': release.get('url'),
                         }

        return download_info

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
            logger.debug(u"Tautulli PlexTV :: Plex Pass subscription not found.")
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
