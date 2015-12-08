#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of PlexPy.
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

from plexpy import logger, helpers, users, http_handler, database
import xmltodict
import json
from xml.dom import minidom

import base64
import plexpy


def refresh_users():
    logger.info("Requesting users list refresh...")
    result = PlexTV().get_full_users_list()
    monitor_db = database.MonitorDatabase()

    if len(result) > 0:
        for item in result:
            control_value_dict = {"user_id": item['user_id']}
            new_value_dict = {"username": item['username'],
                              "thumb": item['thumb'],
                              "email": item['email'],
                              "is_home_user": item['is_home_user'],
                              "is_allow_sync": item['is_allow_sync'],
                              "is_restricted": item['is_restricted']
                              }

            # Check if we've set a custom avatar if so don't overwrite it.
            if item['user_id']:
                avatar_urls = monitor_db.select('SELECT thumb, custom_avatar_url '
                                                'FROM users WHERE user_id = ?',
                                                [item['user_id']])
                if avatar_urls:
                    if not avatar_urls[0]['custom_avatar_url'] or \
                            avatar_urls[0]['custom_avatar_url'] == avatar_urls[0]['thumb']:
                        new_value_dict['custom_avatar_url'] = item['thumb']
                else:
                    new_value_dict['custom_avatar_url'] = item['thumb']

            monitor_db.upsert('users', new_value_dict, control_value_dict)

        logger.info("Users list refreshed.")
    else:
        logger.warn("Unable to refresh users list.")


def get_real_pms_url():
    logger.info("Requesting URLs for server...")

    # Reset any current PMS_URL value
    plexpy.CONFIG.__setattr__('PMS_URL', '')
    plexpy.CONFIG.write()

    fallback_url = 'http://' + plexpy.CONFIG.PMS_IP + ':' + str(plexpy.CONFIG.PMS_PORT)

    if plexpy.CONFIG.PMS_SSL:
        result = PlexTV().get_server_urls(include_https=True)
        process_urls = True
    elif plexpy.CONFIG.PMS_IS_REMOTE:
        result = PlexTV().get_server_urls(include_https=False)
        process_urls = True
    else:
        process_urls = False

    if process_urls:
        if len(result) > 0:
            for item in result:
                if plexpy.CONFIG.PMS_IS_REMOTE and item['local'] == '0':
                        plexpy.CONFIG.__setattr__('PMS_URL', item['uri'])
                        plexpy.CONFIG.write()
                        logger.info("Server URL retrieved.")
                if not plexpy.CONFIG.PMS_IS_REMOTE and item['local'] == '1':
                        plexpy.CONFIG.__setattr__('PMS_URL', item['uri'])
                        plexpy.CONFIG.write()
                        logger.info("Server URL retrieved.")
        else:
            plexpy.CONFIG.__setattr__('PMS_URL', fallback_url)
            plexpy.CONFIG.write()
            logger.warn("Unable to retrieve server URLs. Using user-defined value.")
    else:
        plexpy.CONFIG.__setattr__('PMS_URL', fallback_url)
        plexpy.CONFIG.write()


class PlexTV(object):
    """
    Plex.tv authentication
    """

    def __init__(self, username=None, password=None):
        self.protocol = 'HTTPS'
        self.username = username
        self.password = password
        self.ssl_verify = plexpy.CONFIG.VERIFY_SSL_CERT

        self.request_handler = http_handler.HTTPHandler(host='plex.tv',
                                                        port=443,
                                                        token=plexpy.CONFIG.PMS_TOKEN,
                                                        ssl_verify=self.ssl_verify)

    def get_plex_auth(self, output_format='raw'):
        uri = '/users/sign_in.xml'
        base64string = base64.encodestring('%s:%s' % (self.username, self.password)).replace('\n', '')
        headers = {'Content-Type': 'application/xml; charset=utf-8',
                   'Content-Length': '0',
                   'X-Plex-Device-Name': 'PlexPy',
                   'X-Plex-Product': 'PlexPy',
                   'X-Plex-Version': 'v0.1 dev',
                   'X-Plex-Client-Identifier': plexpy.CONFIG.PMS_UUID,
                   'Authorization': 'Basic %s' % base64string + ":"
                   }

        request = self.request_handler.make_request(uri=uri,
                                                    proto=self.protocol,
                                                    request_type='POST',
                                                    headers=headers,
                                                    output_format=output_format)

        return request

    def get_token(self):
        plextv_response = self.get_plex_auth(output_format='xml')

        if plextv_response:
            xml_head = plextv_response.getElementsByTagName('user')
            if not xml_head:
                logger.warn("Error parsing XML for Plex.tv token")
                return []

            auth_token = xml_head[0].getAttribute('authenticationToken')

            return auth_token
        else:
            return []

    def get_plextv_user_data(self):
        plextv_response = self.get_plex_auth(output_format='dict')

        if plextv_response:
            return plextv_response
        else:
            return []

    def get_plextv_friends(self, output_format=''):
        uri = '/api/users'
        request = self.request_handler.make_request(uri=uri,
                                                    proto=self.protocol,
                                                    request_type='GET',
                                                    output_format=output_format)

        return request

    def get_plextv_user_details(self, output_format=''):
        uri = '/users/account'
        request = self.request_handler.make_request(uri=uri,
                                                    proto=self.protocol,
                                                    request_type='GET',
                                                    output_format=output_format)

        return request

    def get_plextv_server_list(self, output_format=''):
        uri = '/pms/servers.xml'
        request = self.request_handler.make_request(uri=uri,
                                                    proto=self.protocol,
                                                    request_type='GET',
                                                    output_format=output_format)

        return request

    def get_plextv_sync_lists(self, machine_id='', output_format=''):
        uri = '/servers/' + machine_id + '/sync_lists'
        request = self.request_handler.make_request(uri=uri,
                                                    proto=self.protocol,
                                                    request_type='GET',
                                                    output_format=output_format)

        return request

    def get_plextv_resources(self, include_https=False, output_format=''):
        if include_https:
            uri = '/api/resources?includeHttps=1'
        else:
            uri = '/api/resources'
        request = self.request_handler.make_request(uri=uri,
                                                    proto=self.protocol,
                                                    request_type='GET',
                                                    output_format=output_format)

        return request

    def get_full_users_list(self):
        friends_list = self.get_plextv_friends()
        own_account = self.get_plextv_user_details()
        users_list = []

        try:
            xml_parse = minidom.parseString(own_account)
        except Exception, e:
            logger.warn("Error parsing XML for Plex account details: %s" % e)
            return []
        except:
            logger.warn("Error parsing XML for Plex account details.")
            return []

        xml_head = xml_parse.getElementsByTagName('user')
        if not xml_head:
            logger.warn("Error parsing XML for Plex account details.")
        else:
            for a in xml_head:
                own_details = {"user_id": helpers.get_xml_attr(a, 'id'),
                               "username": helpers.get_xml_attr(a, 'username'),
                               "thumb": helpers.get_xml_attr(a, 'thumb'),
                               "email": helpers.get_xml_attr(a, 'email'),
                               "is_home_user": helpers.get_xml_attr(a, 'home'),
                               "is_allow_sync": None,
                               "is_restricted": helpers.get_xml_attr(a, 'restricted')
                               }

                users_list.append(own_details)

        try:
            xml_parse = minidom.parseString(friends_list)
        except Exception, e:
            logger.warn("Error parsing XML for Plex friends list: %s" % e)
        except:
            logger.warn("Error parsing XML for Plex friends list.")

        xml_head = xml_parse.getElementsByTagName('User')
        if not xml_head:
            logger.warn("Error parsing XML for Plex friends list.")
        else:
            for a in xml_head:
                friend = {"user_id": helpers.get_xml_attr(a, 'id'),
                          "username": helpers.get_xml_attr(a, 'title'),
                          "thumb": helpers.get_xml_attr(a, 'thumb'),
                          "email": helpers.get_xml_attr(a, 'email'),
                          "is_home_user": helpers.get_xml_attr(a, 'home'),
                          "is_allow_sync": helpers.get_xml_attr(a, 'allowSync'),
                          "is_restricted": helpers.get_xml_attr(a, 'restricted')
                          }

                users_list.append(friend)

        return users_list

    def get_synced_items(self, machine_id=None, user_id=None):
        sync_list = self.get_plextv_sync_lists(machine_id)
        user_data = users.Users()

        synced_items = []

        try:
            xml_parse = minidom.parseString(sync_list)
        except Exception, e:
            logger.warn("Error parsing XML for Plex sync lists: %s" % e)
            return []
        except:
            logger.warn("Error parsing XML for Plex sync lists.")
            return []

        xml_head = xml_parse.getElementsByTagName('SyncList')

        if not xml_head:
            logger.warn("Error parsing XML for Plex sync lists.")
        else:
            for a in xml_head:
                client_id = helpers.get_xml_attr(a, 'id')
                sync_device = a.getElementsByTagName('Device')
                for device in sync_device:
                    device_user_id = helpers.get_xml_attr(device, 'userID')
                    try:
                        device_username = user_data.get_user_details(user_id=device_user_id)['username']
                        device_friendly_name = user_data.get_user_details(user_id=device_user_id)['friendly_name']
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
                if user_id and user_id != device_user_id:
                    continue

                for synced in a.getElementsByTagName('SyncItems'):
                    sync_item = synced.getElementsByTagName('SyncItem')
                    for item in sync_item:
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

                        if helpers.get_xml_attr(item.getElementsByTagName('Location')[0], 'uri').endswith('%2Fchildren'):
                            clean_uri = helpers.get_xml_attr(item.getElementsByTagName('Location')[0], 'uri')[:-11]
                        else:
                            clean_uri = helpers.get_xml_attr(item.getElementsByTagName('Location')[0], 'uri')

                        rating_key = clean_uri.rpartition('%2F')[-1]

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
                                        "sync_id": sync_id
                                        }

                        synced_items.append(sync_details)

        return synced_items

    def get_server_urls(self, include_https=True):

        if plexpy.CONFIG.PMS_IDENTIFIER:
            server_id = plexpy.CONFIG.PMS_IDENTIFIER
        else:
            logger.error('PlexPy PlexTV connector :: Unable to retrieve server identity.')
            return []

        plextv_resources = self.get_plextv_resources(include_https=include_https)
        server_urls = []

        try:
            xml_parse = minidom.parseString(plextv_resources)
        except Exception, e:
            logger.warn("Error parsing XML for Plex resources: %s" % e)
            return []
        except:
            logger.warn("Error parsing XML for Plex resources.")
            return []

        try:
            xml_head = xml_parse.getElementsByTagName('Device')
        except:
            logger.warn("Error parsing XML for Plex resources.")
            return []

        for a in xml_head:
            if helpers.get_xml_attr(a, 'clientIdentifier') == server_id:
                connections = a.getElementsByTagName('Connection')
                for connection in connections:
                    server_details = {"protocol": helpers.get_xml_attr(connection, 'protocol'),
                                      "address": helpers.get_xml_attr(connection, 'address'),
                                      "port": helpers.get_xml_attr(connection, 'port'),
                                      "uri": helpers.get_xml_attr(connection, 'uri'),
                                      "local": helpers.get_xml_attr(connection, 'local')
                                      }

                    server_urls.append(server_details)

        return server_urls

    def discover(self):
        """ Query plex for all servers online. Returns the ones you own in a selectize format """
        result = self.get_plextv_resources(include_https=True, output_format='raw')
        servers = xmltodict.parse(result, process_namespaces=True, attr_prefix='')
        clean_servers = []

        try:
            if servers:
                # Fix if its only one "device"
                if int(servers['MediaContainer']['size']) == 1:
                    servers['MediaContainer']['Device'] = [servers['MediaContainer']['Device']]

                for server in servers['MediaContainer']['Device']:
                    # Only grab servers online and own
                    if server.get('presence', None) == '1' and server.get('owned', None) == '1' and server.get('provides', None) == 'server':
                        # If someone only has one connection..
                        if isinstance(server['Connection'], dict):
                            server['Connection'] = [server['Connection']]

                        for s in server['Connection']:
                            # to avoid circular ref
                            d = {}
                            d.update(s)
                            d.update(server)
                            d['label'] = d['name']
                            d['value'] = d['address']
                            del d['Connection']
                            clean_servers.append(d)

        except Exception as e:
            logger.warn('Failed to get servers from plex %s' % e)
            return clean_servers

        return json.dumps(clean_servers, indent=4)

    def get_server_times(self):
        servers = self.get_plextv_server_list(output_format='xml')
        server_times = []

        try:
            xml_head = servers.getElementsByTagName('Server')
        except:
            logger.warn("Error parsing XML for Plex servers.")
            return []

        for a in xml_head:
            if helpers.get_xml_attr(a, 'machineIdentifier') == plexpy.CONFIG.PMS_IDENTIFIER:
                server_times.append({"created_at": helpers.get_xml_attr(a, 'createdAt'),
                                     "updated_at": helpers.get_xml_attr(a, 'updatedAt')
                                     })
                break

        return server_times