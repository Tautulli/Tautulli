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
import plexpy

from plexpy import logger, pmsconnect, activity_processor, threading, notification_handler, helpers, notifiers


class ActivityHandler(object):

    def __init__(self, timeline):
        self.timeline = timeline
        # print timeline

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
        monitor_proc = activity_processor.ActivityProcessor()
        monitor_proc.write_session(session=self.get_live_session(), notify=False)

    def on_start(self):
        if self.is_valid_session() and self.get_live_session():
            logger.debug(u"PlexPy ActivityHandler :: Session %s has started." % str(self.get_session_key()))

            # Check if any notification agents have notifications enabled
            if any(d['on_play'] for d in notifiers.available_notification_agents()):
                # Fire off notifications
                threading.Thread(target=notification_handler.notify,
                                 kwargs=dict(stream_data=self.get_live_session(), notify_action='play')).start()

            # Write the new session to our temp session table
            self.update_db_session()

    def on_stop(self, force_stop=False):
        if self.is_valid_session():
            logger.debug(u"PlexPy ActivityHandler :: Session %s has stopped." % str(self.get_session_key()))

            # Set the session last_paused timestamp
            ap = activity_processor.ActivityProcessor()
            ap.set_session_last_paused(session_key=self.get_session_key(), timestamp=None)

            # Update the session state and viewOffset
            # Set force_stop to true to disable the state set
            if not force_stop:
                ap.set_session_state(session_key=self.get_session_key(),
                                     state=self.timeline['state'],
                                     view_offset=self.timeline['viewOffset'],
                                     stopped=int(time.time()))

            # Retrieve the session data from our temp table
            db_session = ap.get_session_by_key(session_key=self.get_session_key())

            # Check if any notification agents have notifications enabled
            if any(d['on_stop'] for d in notifiers.available_notification_agents()):
                # Fire off notifications
                threading.Thread(target=notification_handler.notify,
                                 kwargs=dict(stream_data=db_session, notify_action='stop')).start()

            # Write it to the history table
            monitor_proc = activity_processor.ActivityProcessor()
            monitor_proc.write_session_history(session=db_session)

            # Remove the session from our temp session table
            logger.debug(u"PlexPy ActivityHandler :: Removing session %s from session queue" % str(self.get_session_key()))
            ap.delete_session(session_key=self.get_session_key())

    def on_pause(self):
        if self.is_valid_session():
            logger.debug(u"PlexPy ActivityHandler :: Session %s has been paused." % str(self.get_session_key()))

            # Set the session last_paused timestamp
            ap = activity_processor.ActivityProcessor()
            ap.set_session_last_paused(session_key=self.get_session_key(), timestamp=int(time.time()))

            # Update the session state and viewOffset
            ap.set_session_state(session_key=self.get_session_key(),
                                 state=self.timeline['state'],
                                 view_offset=self.timeline['viewOffset'])

            # Retrieve the session data from our temp table
            db_session = ap.get_session_by_key(session_key=self.get_session_key())

            # Check if any notification agents have notifications enabled
            if any(d['on_pause'] for d in notifiers.available_notification_agents()):
                # Fire off notifications
                threading.Thread(target=notification_handler.notify,
                                 kwargs=dict(stream_data=db_session, notify_action='pause')).start()

    def on_resume(self):
        if self.is_valid_session():
            logger.debug(u"PlexPy ActivityHandler :: Session %s has been resumed." % str(self.get_session_key()))

            # Set the session last_paused timestamp
            ap = activity_processor.ActivityProcessor()
            ap.set_session_last_paused(session_key=self.get_session_key(), timestamp=None)

            # Update the session state and viewOffset
            ap.set_session_state(session_key=self.get_session_key(),
                                 state=self.timeline['state'],
                                 view_offset=self.timeline['viewOffset'])

            # Retrieve the session data from our temp table
            db_session = ap.get_session_by_key(session_key=self.get_session_key())

            # Check if any notification agents have notifications enabled
            if any(d['on_resume'] for d in notifiers.available_notification_agents()):
                # Fire off notifications
                threading.Thread(target=notification_handler.notify,
                                 kwargs=dict(stream_data=db_session, notify_action='resume')).start()

    def on_buffer(self):
        if self.is_valid_session():
            logger.debug(u"PlexPy ActivityHandler :: Session %s is buffering." % self.get_session_key())
            ap = activity_processor.ActivityProcessor()
            db_stream = ap.get_session_by_key(session_key=self.get_session_key())

            # Increment our buffer count
            ap.increment_session_buffer_count(session_key=self.get_session_key())

            # Get our current buffer count
            current_buffer_count = ap.get_session_buffer_count(self.get_session_key())
            logger.debug(u"PlexPy ActivityHandler :: Session %s buffer count is %s." %
                         (self.get_session_key(), current_buffer_count))

            # Get our last triggered time
            buffer_last_triggered = ap.get_session_buffer_trigger_time(self.get_session_key())

            time_since_last_trigger = 0
            if buffer_last_triggered:
                logger.debug(u"PlexPy ActivityHandler :: Session %s buffer last triggered at %s." %
                             (self.get_session_key(), buffer_last_triggered))
                time_since_last_trigger = int(time.time()) - int(buffer_last_triggered)

            if plexpy.CONFIG.BUFFER_THRESHOLD > 0 and (current_buffer_count >= plexpy.CONFIG.BUFFER_THRESHOLD and \
                time_since_last_trigger == 0 or time_since_last_trigger >= plexpy.CONFIG.BUFFER_WAIT):
                ap.set_session_buffer_trigger_time(session_key=self.get_session_key())

                # Check if any notification agents have notifications enabled
                if any(d['on_buffer'] for d in notifiers.available_notification_agents()):
                    threading.Thread(target=notification_handler.notify,
                                     kwargs=dict(stream_data=db_stream, notify_action='buffer')).start()

    # This function receives events from our websocket connection
    def process(self):
        if self.is_valid_session():
            ap = activity_processor.ActivityProcessor()
            db_session = ap.get_session_by_key(session_key=self.get_session_key())

            this_state = self.timeline['state']
            this_key = str(self.timeline['ratingKey'])

            # If we already have this session in the temp table, check for state changes
            if db_session:
                last_state = db_session['state']
                last_key = str(db_session['rating_key'])

                # Make sure the same item is being played
                if this_key == last_key:
                    # Update the session state and viewOffset
                    if this_state == 'playing':
                        ap.set_session_state(session_key=self.get_session_key(),
                                             state=this_state,
                                             view_offset=self.timeline['viewOffset'])
                    # Start our state checks
                    if this_state != last_state:
                        if this_state == 'paused':
                            self.on_pause()
                        elif last_state == 'paused' and this_state == 'playing':
                            self.on_resume()
                        elif this_state == 'stopped':
                            self.on_stop()
                    elif this_state == 'buffering':
                        self.on_buffer()
                # If a client doesn't register stop events (I'm looking at you PHT!) check if the ratingKey has changed
                else:
                    # Manually stop and start
                    # Set force_stop so that we don't overwrite our last viewOffset
                    self.on_stop(force_stop=True)
                    self.on_start()

                # Monitor if the stream has reached the watch percentage for notifications
                # The only purpose of this is for notifications
                # Check if any notification agents have notifications enabled
                notify_agents = [d['id'] for d in notifiers.available_notification_agents() if d['on_watched']]
                # Get the current states for notifications from our db
                notified_agents = [d['agent_id'] for d in notification_handler.get_notify_state(session=db_session)
                                   if d['notify_action'] == 'watched'] if notify_agents else []

                if any(a not in notified_agents for a in notify_agents):
                    progress_percent = helpers.get_percent(self.timeline['viewOffset'], db_session['duration'])
                    if progress_percent >= plexpy.CONFIG.NOTIFY_WATCHED_PERCENT and this_state != 'buffering':
                        # Rather not put this on it's own thread so we know it completes before our next event.
                        notification_handler.notify(stream_data=db_session, notify_action='watched')

            else:
                # We don't have this session in our table yet, start a new one.
                if this_state != 'buffering':
                    self.on_start()

class TimelineHandler(object):

    def __init__(self, timeline):
        self.timeline = timeline
        #logger.debug(timeline)

    def is_item(self):
        if 'itemID' in self.timeline:
            return True

        return False

    def get_rating_key(self):
        if self.is_item():
            return int(self.timeline['itemID'])

        return None

    def get_metadata(self):
        pms_connect = pmsconnect.PmsConnect()
        metadata_list = pms_connect.get_metadata_details(self.get_rating_key())

        if metadata_list:
            return metadata_list['metadata']

        return None

    def on_created(self):
        if self.is_item():
            logger.debug(u"PlexPy TimelineHandler :: Library item %s has been added to Plex." % str(self.get_rating_key()))

            # Fire off notifications
            threading.Thread(target=notification_handler.notify_timeline,
                             kwargs=dict(timeline_data=self.get_metadata(), notify_action='created')).start()

    # This function receives events from our websocket connection
    def process(self):
        if self.is_item():

            this_state = self.timeline['state']
            this_type = self.timeline['type']
            this_metadataState = self.timeline.get('metadataState', None)
            this_mediaState = self.timeline.get('mediaState', None)

            # state:    5: done processing metadata
            # type:     1: movie, 2: tv show, 4: episode, 8: artist, 10: track
            types = [1, 2, 4, 8, 10]
            if this_state == 5 and this_type in types and this_metadataState == None and this_mediaState == None:
                self.on_created()