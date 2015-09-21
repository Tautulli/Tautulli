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

import time
from plexpy import logger, datafactory, pmsconnect, monitor, threading, notification_handler


class ActivityHandler(object):

    def __init__(self, timeline):
        self.timeline = timeline

    def is_valid_session(self):
        if 'sessionKey' in self.timeline:
            if str(self.timeline['sessionKey']).isdigit():
                return True

        return False

    def get_session_key(self):
        if self.is_valid_session():
            return int(self.timeline['sessionKey'])

        return None

    def get_live_session(self):
        pms_connect = pmsconnect.PmsConnect()
        session_list = pms_connect.get_current_activity()

        for session in session_list['sessions']:
            if int(session['session_key']) == self.get_session_key():
                return session

        return None

    def update_db_session(self):
        # Update our session temp table values
        monitor_proc = monitor.MonitorProcessing()
        monitor_proc.write_session(self.get_live_session())

    def on_start(self):
        if self.is_valid_session():
            logger.debug(u"PlexPy ActivityHandler :: Session %s has started." % str(self.get_session_key()))

            # Fire off notifications
            threading.Thread(target=notification_handler.notify,
                             kwargs=dict(stream_data=self.get_live_session(), notify_action='play')).start()

            # Write the new session to our temp session table
            self.update_db_session()

    def on_stop(self):
        if self.is_valid_session():
            logger.debug(u"PlexPy ActivityHandler :: Session %s has stopped." % str(self.get_session_key()))

            # Set the session last_paused timestamp
            data_factory = datafactory.DataFactory()
            data_factory.set_session_last_paused(session_key=self.get_session_key(), timestamp=None)

            # Update the session state and viewOffset
            data_factory.set_session_state(session_key=self.get_session_key(),
                                           state=self.timeline['state'],
                                           view_offset=self.timeline['viewOffset'])

            # Retrieve the session data from our temp table
            db_session = data_factory.get_session_by_key(session_key=self.get_session_key())

            # Fire off notifications
            threading.Thread(target=notification_handler.notify,
                             kwargs=dict(stream_data=db_session, notify_action='stop')).start()

            # Write it to the history table
            monitor_proc = monitor.MonitorProcessing()
            monitor_proc.write_session_history(session=db_session)

            # Remove the session from our temp session table
            data_factory.delete_session(session_key=self.get_session_key())

    def on_buffer(self):
        pass

    def on_pause(self):
        if self.is_valid_session():
            logger.debug(u"PlexPy ActivityHandler :: Session %s has been paused." % str(self.get_session_key()))

            # Set the session last_paused timestamp
            data_factory = datafactory.DataFactory()
            data_factory.set_session_last_paused(session_key=self.get_session_key(), timestamp=int(time.time()))

            # Update the session state and viewOffset
            data_factory.set_session_state(session_key=self.get_session_key(),
                                           state=self.timeline['state'],
                                           view_offset=self.timeline['viewOffset'])

            # Retrieve the session data from our temp table
            db_session = data_factory.get_session_by_key(session_key=self.get_session_key())

            # Fire off notifications
            threading.Thread(target=notification_handler.notify,
                             kwargs=dict(stream_data=db_session, notify_action='pause')).start()

    def on_resume(self, time_line=None):
        if self.is_valid_session():
            logger.debug(u"PlexPy ActivityHandler :: Session %s has been resumed." % str(self.get_session_key()))

            # Set the session last_paused timestamp
            data_factory = datafactory.DataFactory()
            data_factory.set_session_last_paused(session_key=self.get_session_key(), timestamp=None)

            # Update the session state and viewOffset
            data_factory.set_session_state(session_key=self.get_session_key(),
                                           state=self.timeline['state'],
                                           view_offset=self.timeline['viewOffset'])

            # Retrieve the session data from our temp table
            db_session = data_factory.get_session_by_key(session_key=self.get_session_key())

            # Fire off notifications
            threading.Thread(target=notification_handler.notify,
                             kwargs=dict(stream_data=db_session, notify_action='resume')).start()

    # This function receives events from our websocket connection
    def process(self):
        if self.is_valid_session():
            data_factory = datafactory.DataFactory()
            db_session = data_factory.get_session_by_key(session_key=self.get_session_key())

            # If we already have this session in the temp table, check for state changes
            if db_session:
                this_state = self.timeline['state']
                last_state = db_session['state']

                if this_state != last_state:
                    # logger.debug(u"PlexPy ActivityHandler :: Last state %s :: Current state %s" %
                    #              (last_state, this_state))
                    if this_state == 'paused':
                        self.on_pause()
                    elif last_state == 'paused' and this_state == 'playing':
                        self.on_resume()
                    elif this_state == 'stopped':
                        self.on_stop()
                # else:
                    # logger.debug(u"PlexPy ActivityHandler :: Session %s state has not changed." %
                    #              self.get_session_key())
            else:
                # We don't have this session in our table yet, start a new one.
                # logger.debug(u"PlexPy ActivityHandler :: Session %s has started." % self.get_session_key())
                self.on_start()