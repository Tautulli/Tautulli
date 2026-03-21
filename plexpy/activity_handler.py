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

import datetime
import os
import time

from apscheduler.triggers.date import DateTrigger
import pytz

import plexpy
from plexpy import activity_processor
from plexpy import common
from plexpy import datafactory
from plexpy import helpers
from plexpy import logger
from plexpy import notification_handler
from plexpy import pmsconnect


ACTIVITY_SCHED = None

RECENTLY_ADDED_QUEUE = {}


class ActivityHandler(object):

    def __init__(self, timeline):
        self.ap = activity_processor.ActivityProcessor()
        self.timeline = timeline

        self.session_key = None
        self.rating_key = None

        self.is_valid_session = ('sessionKey' in self.timeline and str(self.timeline['sessionKey']).isdigit())
        if self.is_valid_session:
            self.session_key = int(self.timeline['sessionKey'])
            self.rating_key = str(self.timeline['ratingKey'])

        self.key = self.timeline.get('key')
        self.state = self.timeline.get('state')
        self.view_offset = self.timeline.get('viewOffset')
        self.transcode_key = self.timeline.get('transcodeSession', '')

        self.db_session = None
        self.session = None
        self.metadata = None

    def get_db_session(self):
        # Retrieve the session data from our temp table
        self.db_session = self.ap.get_session_by_key(session_key=self.session_key)

    def get_metadata(self, skip_cache=False):
        if self.metadata is None:
            cache_key = None if skip_cache else self.session_key
            pms_connect = pmsconnect.PmsConnect()
            metadata = pms_connect.get_metadata_details(rating_key=self.rating_key, cache_key=cache_key)

            if metadata:
                self.metadata = metadata

    def get_live_session(self, skip_cache=False):
        pms_connect = pmsconnect.PmsConnect()
        session_list = pms_connect.get_current_activity(skip_cache=skip_cache)

        if session_list:
            for session in session_list['sessions']:
                if int(session['session_key']) == self.session_key:
                    # Live sessions don't have rating keys in sessions
                    # Get it from the websocket data
                    if not session['rating_key']:
                        session['rating_key'] = self.rating_key
                    session['rating_key_websocket'] = self.rating_key
                    self.session = session
                    return session

    def update_db_session(self, notify=False):
        if self.session is None:
            self.get_live_session()

        if self.session:
            # Update our session temp table values
            self.ap.write_session(session=self.session, notify=notify)

        self.set_session_state()

    def set_session_state(self, view_offset=None):
        self.ap.set_session_state(
            session_key=self.session_key,
            state=self.state,
            view_offset=view_offset or self.view_offset,
            stopped=helpers.timestamp()
        )
        self.get_db_session()
        
    def put_notification(self, notify_action, **kwargs):
        notification = {'stream_data': self.db_session.copy(), 'notify_action': notify_action}
        notification.update(kwargs)
        plexpy.NOTIFY_QUEUE.put(notification)

    def on_start(self):
        self.get_live_session(skip_cache=True)

        if not self.session:
            return

        # Some DLNA clients create a new session temporarily when browsing the library
        # Wait and get session again to make sure it is an actual session
        if self.session['platform'] == 'DLNA':
            time.sleep(1)
            self.get_live_session()
            if not self.session:
                return

        logger.debug("Tautulli ActivityHandler :: Session %s started by user %s (%s) with ratingKey %s (%s)%s."
                        % (str(self.session['session_key']), str(self.session['user_id']), self.session['username'],
                        str(self.session['rating_key']), self.session['full_title'], ' [Live TV]' if self.session['live'] else ''))

        # Write the new session to our temp session table
        self.update_db_session(notify=True)

        # Schedule a callback to force stop a stale stream 5 minutes later
        schedule_callback('session_key-{}'.format(self.session_key),
                            func=force_stop_stream,
                            args=[self.session_key, self.session['full_title'], self.session['username']],
                            minutes=5)
        
        self.check_markers()

    def on_stop(self, force_stop=False):
        logger.debug("Tautulli ActivityHandler :: Session %s %sstopped."
                        % (str(self.session_key), 'force ' if force_stop else ''))

        # Set the session last_paused timestamp
        self.ap.set_session_last_paused(session_key=self.session_key, timestamp=None)

        # Update the session state and viewOffset
        # Set force_stop to true to disable the state set
        if not force_stop:
            # Set the view offset equal to the duration if it is within the last 10 seconds
            if self.db_session['duration'] > 0 and self.db_session['duration'] - self.view_offset <= 10000:
                view_offset = self.db_session['duration']
            else:
                view_offset = self.view_offset
            self.set_session_state(view_offset=view_offset)

        # Write it to the history table
        row_id = self.ap.write_session_history(session=self.db_session)

        if row_id:
            self.put_notification('on_stop')

            schedule_callback('session_key-{}'.format(self.session_key), remove_job=True)

            # Remove the session from our temp session table
            logger.debug("Tautulli ActivityHandler :: Removing sessionKey %s ratingKey %s from session queue"
                            % (str(self.session_key), str(self.rating_key)))
            self.ap.delete_session(row_id=row_id)
            delete_metadata_cache(self.session_key)
        else:
            schedule_callback('session_key-{}'.format(self.session_key),
                                func=force_stop_stream,
                                args=[self.session_key, self.db_session['full_title'], self.db_session['user']],
                                seconds=30)

    def on_pause(self, still_paused=False):
        if not still_paused:
            logger.debug("Tautulli ActivityHandler :: Session %s paused." % str(self.session_key))

        # Set the session last_paused timestamp
        self.ap.set_session_last_paused(session_key=self.session_key, timestamp=helpers.timestamp())

        self.update_db_session()

        if not still_paused:
            self.put_notification('on_pause')

    def on_resume(self):
        logger.debug("Tautulli ActivityHandler :: Session %s resumed." % str(self.session_key))

        # Set the session last_paused timestamp
        self.ap.set_session_last_paused(session_key=self.session_key, timestamp=None)

        self.update_db_session()

        self.put_notification('on_resume')

    def on_buffer(self):
        logger.debug("Tautulli ActivityHandler :: Session %s is buffering." % self.session_key)

        # Increment our buffer count
        self.ap.increment_session_buffer_count(session_key=self.session_key)

        # Get our current buffer count
        current_buffer_count = self.ap.get_session_buffer_count(self.session_key)
        logger.debug("Tautulli ActivityHandler :: Session %s buffer count is %s." %
                        (self.session_key, current_buffer_count))

        # Get our last triggered time
        buffer_last_triggered = self.ap.get_session_buffer_trigger_time(self.session_key)

        self.update_db_session()

        time_since_last_trigger = 0
        if buffer_last_triggered:
            logger.debug("Tautulli ActivityHandler :: Session %s buffer last triggered at %s." %
                            (self.session_key, buffer_last_triggered))
            time_since_last_trigger = helpers.timestamp() - int(buffer_last_triggered)

        if current_buffer_count >= plexpy.CONFIG.BUFFER_THRESHOLD and time_since_last_trigger == 0 or \
                time_since_last_trigger >= plexpy.CONFIG.BUFFER_WAIT:
            self.ap.set_session_buffer_trigger_time(session_key=self.session_key)

            self.put_notification('on_buffer')

    def on_error(self):
        logger.debug("Tautulli ActivityHandler :: Session %s encountered an error." % str(self.session_key))

        self.update_db_session()

        self.put_notification('on_error')

    def on_change(self):
        logger.debug("Tautulli ActivityHandler :: Session %s has changed transcode decision." % str(self.session_key))

        self.update_db_session()

        self.put_notification('on_change')

    def on_intro(self, marker):
        logger.debug("Tautulli ActivityHandler :: Session %s reached intro marker." % str(self.session_key))

        self.set_session_state(view_offset=marker['start_time_offset'])

        self.put_notification('on_intro', marker=marker)

    def on_commercial(self, marker):
        logger.debug("Tautulli ActivityHandler :: Session %s reached commercial marker." % str(self.session_key))

        self.set_session_state(view_offset=marker['start_time_offset'])

        self.put_notification('on_commercial', marker=marker)

    def on_credits(self, marker):
        logger.debug("Tautulli ActivityHandler :: Session %s reached credits marker." % str(self.session_key))

        self.set_session_state(view_offset=marker['start_time_offset'])

        self.put_notification('on_credits', marker=marker)

    def on_watched(self, marker=None):
        logger.debug("Tautulli ActivityHandler :: Session %s watched." % str(self.session_key))

        if marker:
            self.set_session_state(view_offset=marker['start_time_offset'])
        else:
            self.update_db_session()

        watched_notifiers = notification_handler.get_notify_state_enabled(
            session=self.db_session, notify_action='on_watched', notified=False)

        for d in watched_notifiers:
            self.put_notification('on_watched', notifier_id=d['notifier_id'])

    # This function receives events from our websocket connection
    def process(self):
        if not self.is_valid_session:
            return
        
        self.get_db_session()

        if not self.db_session:
            # We don't have this session in our table yet, start a new one.
            if self.state != 'buffering':
                self.on_start()
            return

        # If we already have this session in the temp table, check for state changes
        # Re-schedule the callback to reset the 5 minutes timer
        schedule_callback('session_key-{}'.format(self.session_key),
                            func=force_stop_stream,
                            args=[self.session_key, self.db_session['full_title'], self.db_session['user']],
                            minutes=5)

        last_state = self.db_session['state']
        last_rating_key = str(self.db_session['rating_key'])
        last_live_uuid = self.db_session['live_uuid']
        last_transcode_key = self.db_session['transcode_key']
        if isinstance(last_transcode_key, str):
            last_transcode_key = last_transcode_key.split('/')[-1]
        last_paused = self.db_session['last_paused']
        last_rating_key_websocket = self.db_session['rating_key_websocket']
        last_guid = self.db_session['guid']

        # Get the live tv session uuid
        this_live_uuid = self.key.split('/')[-1] if self.key.startswith('/livetv/sessions') else None

        this_guid = last_guid
        # Check guid for live TV metadata every 60 seconds
        if self.db_session['live'] and helpers.timestamp() - self.db_session['stopped'] > 60:
            self.get_metadata(skip_cache=True)
            if self.metadata:
                this_guid = self.metadata['guid']

        # Check for stream offset notifications
        self.check_markers()
        self.check_watched()

        # Make sure the same item is being played
        if (self.rating_key == last_rating_key
                or self.rating_key == last_rating_key_websocket
                or this_live_uuid == last_live_uuid) \
                and this_guid == last_guid:
            # Update the session state and viewOffset
            if self.state == 'playing':
                # Update the session in our temp session table
                # if the last set temporary stopped time exceeds 60 seconds
                if helpers.timestamp() - self.db_session['stopped'] > 60:
                    self.update_db_session()

            # Start our state checks
            if self.state != last_state:
                if self.state == 'paused':
                    self.on_pause()
                elif last_paused and self.state == 'playing':
                    self.on_resume()
                elif self.state == 'stopped':
                    self.on_stop()
                elif self.state == 'error':
                    self.on_error()

            elif self.state == 'paused':
                # Update the session last_paused timestamp
                self.on_pause(still_paused=True)

            if self.state == 'buffering':
                self.on_buffer()

            if self.transcode_key != last_transcode_key and self.state != 'stopped':
                self.on_change()

        # If a client doesn't register stop events (I'm looking at you PHT!) check if the ratingKey has changed
        else:
            # Manually stop and start
            # Set force_stop so that we don't overwrite our last viewOffset
            self.on_stop(force_stop=True)
            self.on_start()

    def check_markers(self):
        # Monitor if the stream has reached the intro or credit marker offsets
        self.get_metadata()

        marker_flag = False

        for marker_idx, marker in enumerate(self.metadata['markers'], start=1):
            # Websocket events only fire every 10 seconds
            # Check if the marker is within 10 seconds of the current viewOffset
            if marker['start_time_offset'] - 10000 <= self.view_offset <= marker['end_time_offset']:
                marker_flag = True

                if self.db_session['marker'] != marker_idx:
                    self.ap.set_marker(session_key=self.session_key, marker_idx=marker_idx, marker_type=marker['type'])

                    if self.view_offset < marker['start_time_offset']:
                        # Schedule a callback for the exact offset of the marker
                        schedule_callback(
                            'session_key-{}-marker-{}'.format(self.session_key, marker_idx),
                            func=self._marker_callback,
                            args=[marker],
                            milliseconds=marker['start_time_offset'] - self.view_offset
                        )
                    else:
                        self._marker_callback(marker)

                break

        if not marker_flag:
            self.ap.set_marker(session_key=self.session_key, marker_idx=0)

    def _marker_callback(self, marker):
        if self.get_live_session():
            # Reset ActivityProcessor object for new database thread
            self.ap = activity_processor.ActivityProcessor()

            if marker['type'] == 'intro':
                self.on_intro(marker)
            elif marker['type'] == 'commercial':
                self.on_commercial(marker)
            elif marker['type'] == 'credits':
                self.on_credits(marker)

                if not self.db_session['watched']:
                    if marker['final'] and plexpy.CONFIG.WATCHED_MARKER == 1:
                        self._marker_watched(marker)
                    elif marker['first'] and (plexpy.CONFIG.WATCHED_MARKER in (2, 3)):
                        self._marker_watched(marker)

    def _marker_watched(self, marker):
        if not self.db_session['watched']:
            self._watched_callback(marker)

    def check_watched(self):
        if plexpy.CONFIG.WATCHED_MARKER == 1 or plexpy.CONFIG.WATCHED_MARKER == 2:
            return

        # Monitor if the stream has reached the watch percentage for notifications
        if not self.db_session['watched'] and self.state != 'buffering' and helpers.check_watched(
            self.db_session['media_type'], self.view_offset, self.db_session['duration']
        ):
            self._watched_callback()

    def _watched_callback(self, marker=None):
        self.ap.set_watched(session_key=self.session_key)
        self.on_watched(marker)


class TimelineHandler(object):

    def __init__(self, timeline):
        self.timeline = timeline

        self.rating_key = None

        self.is_item = ('itemID' in self.timeline)
        if self.is_item:
            self.rating_key = int(self.timeline['itemID'])

        self.parent_rating_key = helpers.cast_to_int(self.timeline.get('parentItemID')) or None
        self.grandparent_rating_key = helpers.cast_to_int(self.timeline.get('rootItemID')) or None
        self.identifier = self.timeline.get('identifier')
        self.state_type = self.timeline.get('state')
        self.media_type = common.MEDIA_TYPE_VALUES.get(self.timeline.get('type'))
        self.section_id = helpers.cast_to_int(self.timeline.get('sectionID', 0))
        self.title = self.timeline.get('title', 'Unknown')
        self.metadata_state = self.timeline.get('metadataState')
        self.media_state = self.timeline.get('mediaState')
        self.queue_size = self.timeline.get('queueSize')

    # This function receives events from our websocket connection
    def process(self):
        if not self.is_item:
            return
        
        # Return if it is not a library event (i.e. DVR EPG event)
        if self.identifier != 'com.plexapp.plugins.library':
            return

        global RECENTLY_ADDED_QUEUE

        # Add a new media item to the recently added queue
        if self.media_type and self.section_id > 0 and self.state_type == 0 and self.metadata_state == 'created':

            if self.media_type in ('episode', 'track'):
                grandparent_set = RECENTLY_ADDED_QUEUE.get(self.grandparent_rating_key, set())
                grandparent_set.add(self.parent_rating_key)
                RECENTLY_ADDED_QUEUE[self.grandparent_rating_key] = grandparent_set

                parent_set = RECENTLY_ADDED_QUEUE.get(self.parent_rating_key, set())
                parent_set.add(self.rating_key)
                RECENTLY_ADDED_QUEUE[self.parent_rating_key] = parent_set

                RECENTLY_ADDED_QUEUE[self.rating_key] = {self.grandparent_rating_key}

                logger.debug("Tautulli TimelineHandler :: Library item '%s' (%s, grandparent %s) "
                                "added to recently added queue."
                                % (self.title, str(self.rating_key), str(self.grandparent_rating_key)))

                # Schedule a callback to clear the recently added queue
                schedule_callback('rating_key-{}'.format(self.grandparent_rating_key),
                                    func=clear_recently_added_queue,
                                    args=[self.grandparent_rating_key, self.title],
                                    seconds=plexpy.CONFIG.NOTIFY_RECENTLY_ADDED_DELAY)

            elif self.media_type in ('season', 'album'):
                parent_set = RECENTLY_ADDED_QUEUE.get(self.parent_rating_key, set())
                parent_set.add(self.rating_key)
                RECENTLY_ADDED_QUEUE[self.parent_rating_key] = parent_set

                logger.debug("Tautulli TimelineHandler :: Library item '%s' (%s , parent %s) "
                                "added to recently added queue."
                                % (self.title, str(self.rating_key), str(self.parent_rating_key)))

                # Schedule a callback to clear the recently added queue
                schedule_callback('rating_key-{}'.format(self.parent_rating_key),
                                    func=clear_recently_added_queue,
                                    args=[self.parent_rating_key, self.title],
                                    seconds=plexpy.CONFIG.NOTIFY_RECENTLY_ADDED_DELAY)

            elif self.media_type in ('movie', 'show', 'artist'):
                queue_set = RECENTLY_ADDED_QUEUE.get(self.rating_key, set())
                RECENTLY_ADDED_QUEUE[self.rating_key] = queue_set

                logger.debug("Tautulli TimelineHandler :: Library item '%s' (%s) "
                                "added to recently added queue."
                                % (self.title, str(self.rating_key)))

                # Schedule a callback to clear the recently added queue
                schedule_callback('rating_key-{}'.format(self.rating_key),
                                    func=clear_recently_added_queue,
                                    args=[self.rating_key, self.title],
                                    seconds=plexpy.CONFIG.NOTIFY_RECENTLY_ADDED_DELAY)

        # A movie, show, or artist is done processing
        elif self.media_type in ('movie', 'show', 'artist') and self.section_id > 0 and \
                self.state_type == 5 and self.metadata_state is None and self.queue_size is None and \
                self.rating_key in RECENTLY_ADDED_QUEUE:

            logger.debug("Tautulli TimelineHandler :: Library item '%s' (%s) "
                            "done processing metadata."
                            % (self.title, str(self.rating_key)))

        # An item was deleted, make sure it is removed from the queue
        elif self.state_type == 9 and self.metadata_state == 'deleted':
            if self.rating_key in RECENTLY_ADDED_QUEUE and not RECENTLY_ADDED_QUEUE[self.rating_key]:
                logger.debug("Tautulli TimelineHandler :: Library item %s "
                                "removed from recently added queue."
                                % str(self.rating_key))
                del_keys(self.rating_key)

                # Remove the callback if the item is removed
                schedule_callback('rating_key-{}'.format(self.rating_key), remove_job=True)


class ReachabilityHandler(object):

    def __init__(self, data):
        self.data = data

        self.is_reachable = self.data.get('reachability', False)

    def remote_access_enabled(self):
        pms_connect = pmsconnect.PmsConnect()
        pref = pms_connect.get_server_pref(pref='PublishServerOnPlexOnlineKey')
        return helpers.bool_true(pref)

    def on_extdown(self, server_response):
        plexpy.NOTIFY_QUEUE.put({'notify_action': 'on_extdown', 'remote_access_info': server_response})

    def on_extup(self, server_response):
        plexpy.NOTIFY_QUEUE.put({'notify_action': 'on_extup', 'remote_access_info': server_response})

    def process(self):
        # Check if remote access is enabled
        if not self.remote_access_enabled():
            return

        # Do nothing if remote access is still up and hasn't changed
        if self.is_reachable and plexpy.PLEX_REMOTE_ACCESS_UP:
            return

        pms_connect = pmsconnect.PmsConnect()
        server_response = pms_connect.get_server_response()

        if not server_response:
            return

        # Waiting for port mapping
        if server_response['mapping_state'] == 'waiting':
            logger.warn("Tautulli ReachabilityHandler :: Remote access waiting for port mapping.")

        elif plexpy.PLEX_REMOTE_ACCESS_UP is not False and server_response['reason']:
            logger.warn("Tautulli ReachabilityHandler :: Remote access failed: %s" % server_response['reason'])
            logger.info("Tautulli ReachabilityHandler :: Plex remote access is down.")

            plexpy.PLEX_REMOTE_ACCESS_UP = False

            if not ACTIVITY_SCHED.get_job('on_extdown'):
                logger.debug("Tautulli ReachabilityHandler :: Scheduling remote access down callback in %d seconds.",
                                plexpy.CONFIG.NOTIFY_REMOTE_ACCESS_THRESHOLD)
                schedule_callback('on_extdown', func=self.on_extdown, args=[server_response],
                                    seconds=plexpy.CONFIG.NOTIFY_REMOTE_ACCESS_THRESHOLD)

        elif plexpy.PLEX_REMOTE_ACCESS_UP is False and not server_response['reason']:
            logger.info("Tautulli ReachabilityHandler :: Plex remote access is back up.")

            plexpy.PLEX_REMOTE_ACCESS_UP = True

            if ACTIVITY_SCHED.get_job('on_extdown'):
                logger.debug("Tautulli ReachabilityHandler :: Cancelling scheduled remote access down callback.")
                schedule_callback('on_extdown', remove_job=True)
            else:
                self.on_extup(server_response)

        elif plexpy.PLEX_REMOTE_ACCESS_UP is None:
            plexpy.PLEX_REMOTE_ACCESS_UP = self.is_reachable


def del_keys(key):
    if isinstance(key, set):
        for child_key in key:
            del_keys(child_key)
    elif key in RECENTLY_ADDED_QUEUE:
        del_keys(RECENTLY_ADDED_QUEUE.pop(key))


def schedule_callback(id, func=None, remove_job=False, args=None, **kwargs):
    if ACTIVITY_SCHED.get_job(id):
        if remove_job:
            ACTIVITY_SCHED.remove_job(id)
        else:
            ACTIVITY_SCHED.reschedule_job(
                id, args=args, trigger=DateTrigger(
                    run_date=datetime.datetime.now(pytz.UTC) + datetime.timedelta(**kwargs),
                    timezone=pytz.UTC))
    elif not remove_job:
        ACTIVITY_SCHED.add_job(
            func, args=args, id=id, trigger=DateTrigger(
                run_date=datetime.datetime.now(pytz.UTC) + datetime.timedelta(**kwargs),
                timezone=pytz.UTC),
            misfire_grace_time=None)


def force_stop_stream(session_key, title, user):
    ap = activity_processor.ActivityProcessor()
    session = ap.get_session_by_key(session_key=session_key)

    row_id = ap.write_session_history(session=session)

    if row_id:
        plexpy.NOTIFY_QUEUE.put({'stream_data': session.copy(), 'notify_action': 'on_stop'})

        # If session is written to the database successfully, remove the session from the session table
        logger.info("Tautulli ActivityHandler :: Removing stale stream with sessionKey %s ratingKey %s from session queue"
                    % (session['session_key'], session['rating_key']))
        ap.delete_session(row_id=row_id)
        delete_metadata_cache(session_key)

    else:
        session['write_attempts'] += 1

        if session['write_attempts'] < plexpy.CONFIG.SESSION_DB_WRITE_ATTEMPTS:
            logger.warn("Tautulli ActivityHandler :: Failed to write stream with sessionKey %s ratingKey %s to the database. " \
                        "Will try again in 30 seconds. Write attempt %s."
                        % (session['session_key'], session['rating_key'], str(session['write_attempts'])))
            ap.increment_write_attempts(session_key=session_key)

            # Reschedule for 30 seconds later
            schedule_callback('session_key-{}'.format(session_key), func=force_stop_stream,
                              args=[session_key, session['full_title'], session['user']], seconds=30)

        else:
            logger.warn("Tautulli ActivityHandler :: Failed to write stream with sessionKey %s ratingKey %s to the database. " \
                        "Removing session from the database. Write attempt %s."
                        % (session['session_key'], session['rating_key'], str(session['write_attempts'])))
            logger.info("Tautulli ActivityHandler :: Removing stale stream with sessionKey %s ratingKey %s from session queue"
                        % (session['session_key'], session['rating_key']))
            ap.delete_session(session_key=session_key)
            delete_metadata_cache(session_key)


def clear_recently_added_queue(rating_key, title):
    logger.debug("Tautulli TimelineHandler :: Starting callback for library item '%s' (%s) after delay.",
                 title, str(rating_key))

    child_keys = RECENTLY_ADDED_QUEUE[rating_key]

    if plexpy.CONFIG.NOTIFY_GROUP_RECENTLY_ADDED_GRANDPARENT and len(child_keys) > 1:
        on_created(rating_key, child_keys=child_keys)

    elif child_keys:
        for child_key in child_keys:
            grandchild_keys = RECENTLY_ADDED_QUEUE.get(child_key, [])

            if plexpy.CONFIG.NOTIFY_GROUP_RECENTLY_ADDED_PARENT and len(grandchild_keys) > 1:
                on_created(child_key, child_keys=grandchild_keys)

            elif grandchild_keys:
                for grandchild_key in grandchild_keys:
                    on_created(grandchild_key)

            else:
                on_created(child_key)

    else:
        on_created(rating_key)

    # Remove all keys
    del_keys(rating_key)


def on_created(rating_key, **kwargs):
    pms_connect = pmsconnect.PmsConnect()
    metadata = pms_connect.get_metadata_details(rating_key)

    logger.debug("Tautulli TimelineHandler :: Library item '%s' (%s) added to Plex.",
                 metadata['full_title'], str(rating_key))

    if metadata:
        notify = True
        # now = helpers.timestamp()
        #
        # if helpers.cast_to_int(metadata['added_at']) < now - 86400:  # Updated more than 24 hours ago
        #     logger.debug("Tautulli TimelineHandler :: Library item %s added more than 24 hours ago. Not notifying."
        #                  % str(rating_key))
        #     notify = False

        data_factory = datafactory.DataFactory()
        if 'child_keys' not in kwargs:
            if data_factory.get_recently_added_item(rating_key):
                logger.debug("Tautulli TimelineHandler :: Library item %s added already. Not notifying again."
                             % str(rating_key))
                notify = False

        if notify:
            data = {'timeline_data': metadata, 'notify_action': 'on_created'}
            data.update(kwargs)
            plexpy.NOTIFY_QUEUE.put(data)

        all_keys = [rating_key]
        if 'child_keys' in kwargs:
            all_keys.extend(kwargs['child_keys'])

        for key in all_keys:
            data_factory.set_recently_added_item(key)

        logger.debug("Added %s items to the recently_added database table." % str(len(all_keys)))

    else:
        logger.error("Tautulli TimelineHandler :: Unable to retrieve metadata for rating_key %s" % str(rating_key))


def delete_metadata_cache(session_key):
    try:
        os.remove(os.path.join(plexpy.CONFIG.CACHE_DIR, 'session_metadata', 'metadata-sessionKey-%s.json' % session_key))
    except OSError as e:
        logger.error("Tautulli ActivityHandler :: Failed to remove metadata cache file (sessionKey %s): %s"
                     % (session_key, e))
