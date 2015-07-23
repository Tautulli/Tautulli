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

from plexpy import logger, config, notifiers, database

import plexpy
import time

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
            logger.info('PlexPy Notifier :: %s (%s) started playing %s.' % (stream_data['friendly_name'],
                                                                           stream_data['player'], item_title))

        if stream_data['media_type'] == 'movie' or stream_data['media_type'] == 'episode':
            if plexpy.CONFIG.MOVIE_NOTIFY_ENABLE or plexpy.CONFIG.TV_NOTIFY_ENABLE:

                for agent in notifiers.available_notification_agents():
                    if agent['on_play'] and notify_action == 'play':
                        logger.debug("PlexPy Notifier :: %s agent is configured to notify on playback start." % agent['name'])
                        message = '%s (%s) started playing %s.' % \
                              (stream_data['friendly_name'], stream_data['player'], item_title)
                        notifiers.send_notification(config_id=agent['id'], subject=notify_header, body=message)
                        set_notify_state(session=stream_data, state='play', agent_info=agent)
                    elif agent['on_stop'] and notify_action == 'stop':
                        logger.debug("PlexPy Notifier :: %s agent is configured to notify on playback stop." % agent['name'])
                        message = '%s (%s) has stopped %s.' % \
                              (stream_data['friendly_name'], stream_data['player'], item_title)
                        notifiers.send_notification(config_id=agent['id'], subject=notify_header, body=message)
                        set_notify_state(session=stream_data, state='stop', agent_info=agent)
                    elif agent['on_watched'] and notify_action == 'watched':
                        notify_states = get_notify_state(session=stream_data)
                        # If there is nothing in the notify_log for our agent id but it is enabled we should notify
                        if not any(d['agent_id'] == agent['id'] for d in notify_states):
                            logger.debug("PlexPy Notifier :: %s agent is configured to notify on watched." % agent['name'])
                            message = '%s (%s) has watched %s.' % \
                                  (stream_data['friendly_name'], stream_data['player'], item_title)
                            notifiers.send_notification(config_id=agent['id'], subject=notify_header, body=message)
                            set_notify_state(session=stream_data, state='watched', agent_info=agent)
                        else:
                            # Check in our notify log if the notification has already been sent
                            for notify_state in notify_states:
                                if not notify_state['on_watched'] and (notify_state['agent_id'] == agent['id']):
                                    logger.debug("PlexPy Notifier :: %s agent is configured to notify on watched." % agent['name'])
                                    message = '%s (%s) has watched %s.' % \
                                          (stream_data['friendly_name'], stream_data['player'], item_title)
                                    notifiers.send_notification(config_id=agent['id'], subject=notify_header, body=message)
                                    set_notify_state(session=stream_data, state='watched', agent_info=agent)

        elif stream_data['media_type'] == 'track':
            if plexpy.CONFIG.MUSIC_NOTIFY_ENABLE:

                for agent in notifiers.available_notification_agents():
                    if agent['on_play'] and notify_action == 'play':
                        logger.debug("PlexPy Notifier :: %s agent is configured to notify on playback start." % agent['name'])
                        message = '%s (%s) started playing %s.' % \
                              (stream_data['friendly_name'], stream_data['player'], item_title)
                        notifiers.send_notification(config_id=agent['id'], subject=notify_header, body=message)
                        set_notify_state(session=stream_data, state='play', agent_info=agent)
                    elif agent['on_stop'] and notify_action == 'stop':
                        logger.debug("PlexPy Notifier :: %s agent is configured to notify on playback stop." % agent['name'])
                        message = '%s (%s) has stopped %s.' % \
                              (stream_data['friendly_name'], stream_data['player'], item_title)
                        notifiers.send_notification(config_id=agent['id'], subject=notify_header, body=message)
                        set_notify_state(session=stream_data, state='stop', agent_info=agent)

        elif stream_data['media_type'] == 'clip':
            pass
        else:
            logger.debug(u"PlexPy Notifier :: Notify called with unsupported media type.")
            pass
    else:
        logger.debug(u"PlexPy Notifier :: Notify called but incomplete data received.")

def get_notify_state(session):
    monitor_db = database.MonitorDatabase()
    result = monitor_db.select('SELECT on_play, on_stop, on_watched, agent_id '
                               'FROM notify_log '
                               'WHERE session_key = ? '
                               'AND rating_key = ? '
                               'AND user = ? '
                               'ORDER BY id DESC',
                               args=[session['session_key'], session['rating_key'], session['user']])
    notify_states = []
    for item in result:
        notify_state = {'on_play': item[0],
                        'on_stop': item[1],
                        'on_watched': item[2],
                        'agent_id': item[3]}
        notify_states.append(notify_state)

    return notify_states

def set_notify_state(session, state, agent_info):

    if session and state and agent_info:
        monitor_db = database.MonitorDatabase()

        if state == 'play':
            values = {'on_play': int(time.time())}
        elif state == 'stop':
            values = {'on_stop': int(time.time())}
        elif state == 'watched':
            values = {'on_watched': int(time.time())}
        else:
            return

        keys = {'session_key': session['session_key'],
                'rating_key': session['rating_key'],
                'user_id': session['user_id'],
                'user': session['user'],
                'agent_id': agent_info['id'],
                'agent_name': agent_info['name']}

        monitor_db.upsert(table_name='notify_log', key_dict=keys, value_dict=values)
    else:
        logger.error('PlexPy Notifier :: Unable to set notify state.')
