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

from plexpy import logger, helpers, plexwatch, db, http_handler, monitor

from xml.dom import minidom

import base64
import plexpy

def refresh_users():
    logger.info("Requesting users list refresh...")
    result = PlexTV().get_full_users_list()
    pw_db = db.DBConnection()
    monitor_db = monitor.MonitorDatabase()

    if len(result) > 0:
        for item in result:
            control_value_dict = {"username": item['username']}
            new_value_dict = {"user_id": item['user_id'],
                              "username": item['username'],
                              "thumb": item['thumb'],
                              "email": item['email'],
                              "is_home_user": item['is_home_user'],
                              "is_allow_sync": item['is_allow_sync'],
                              "is_restricted": item['is_restricted']
                              }

            pw_db.upsert('plexpy_users', new_value_dict, control_value_dict)
            monitor_db.upsert('users', new_value_dict, control_value_dict)

        logger.info("Users list refreshed.")
    else:
        logger.warn("Unable to refresh users list.")


class PlexTV(object):
    """
    Plex.tv authentication
    """

    def __init__(self, username=None, password=None):
        self.protocol = 'HTTPS'
        self.username = username
        self.password = password

        self.request_handler = http_handler.HTTPHandler(host='plex.tv',
                                                        port=443,
                                                        token=plexpy.CONFIG.PMS_TOKEN)

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
                logger.warn("Error parsing XML for Plex.tv token: %s" % e)
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
        plex_watch = plexwatch.PlexWatch()

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
                        device_username = plex_watch.get_user_details(user_id=device_user_id)['username']
                        device_friendly_name = plex_watch.get_user_details(user_id=device_user_id)['friendly_name']
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

                        sync_details = {"device_name": device_name,
                                        "platform": device_platform,
                                        "username": device_username,
                                        "friendly_name": device_friendly_name,
                                        "user_id": device_user_id,
                                        "root_title": sync_root_title,
                                        "title": sync_title,
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