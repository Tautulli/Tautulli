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

from plexpy import logger, config, notifiers

import plexpy

def notify(stream_data=None, notify_action=None):
    from plexpy import pmsconnect, common
    
    if stream_data and notify_action:
        # Get the server name
        pms_connect = pmsconnect.PmsConnect()
        server_name = pms_connect.get_server_pref(pref='FriendlyName')

        # Build the notification heading
        notify_header = 'PlexPy (%s)' % server_name

        # Build media item title
        if stream_data['media_type'] == 'episode' or stream_data['media_type'] == 'track':
            item_title = '%s - %s' % (stream_data['grandparent_title'], stream_data['title'])
        elif stream_data['media_type'] == 'movie':
            item_title = stream_data['title']
        else:
            item_title = stream_data['title']

        if notify_action == 'play':
            logger.info('PlexPy Monitor :: %s (%s) started playing %s.' % (stream_data['friendly_name'],
                                                                           stream_data['player'], item_title))

        if stream_data['media_type'] == 'movie' or stream_data['media_type'] == 'episode':
            if plexpy.CONFIG.MOVIE_NOTIFY_ENABLE or plexpy.CONFIG.TV_NOTIFY_ENABLE:

                for agent in notifiers.available_notification_agents():
                    if agent['on_play'] and notify_action == 'play':
                        logger.debug("%s agent is configured to notify on playback start." % agent['name'])
                        message = '%s (%s) started playing %s.' % \
                              (stream_data['friendly_name'], stream_data['player'], item_title)
                        notifiers.send_notification(config_id=agent['id'], subject=notify_header, body=message)
                    elif agent['on_stop'] and notify_action == 'stop':
                        logger.debug("%s agent is configured to notify on playback stop." % agent['name'])
                        message = '%s (%s) has stopped %s.' % \
                              (stream_data['friendly_name'], stream_data['player'], item_title)
                        notifiers.send_notification(config_id=agent['id'], subject=notify_header, body=message)

        elif stream_data['media_type'] == 'track':
            if plexpy.CONFIG.MUSIC_NOTIFY_ENABLE:

                for agent in notifiers.available_notification_agents():
                    if agent['on_play'] and notify_action == 'play':
                        logger.debug("%s agent is configured to notify on playback start." % agent['name'])
                        message = '%s (%s) started playing %s.' % \
                              (stream_data['friendly_name'], stream_data['player'], item_title)
                        notifiers.send_notification(config_id=agent['id'], subject=notify_header, body=message)
                    elif agent['on_stop'] and notify_action == 'stop':
                        logger.debug("%s agent is configured to notify on playback stop." % agent['name'])
                        message = '%s (%s) has stopped %s.' % \
                              (stream_data['friendly_name'], stream_data['player'], item_title)
                        notifiers.send_notification(config_id=agent['id'], subject=notify_header, body=message)

        elif stream_data['media_type'] == 'clip':
            pass
        else:
            logger.debug(u"PlexPy Monitor :: Notify called with unsupported media type.")
            pass
    else:
        logger.debug(u"PlexPy Monitor :: Notify called but incomplete data received.")
