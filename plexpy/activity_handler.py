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

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger

import plexpy
import activity_processor
import datafactory
import helpers
import logger
import notification_handler
import pmsconnect


ACTIVITY_SCHED = BackgroundScheduler()

RECENTLY_ADDED_QUEUE = {}


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

    def get_rating_key(self):
        if self.is_valid_session():
            return int(self.timeline['ratingKey'])

        return None

    def get_live_session(self):
        pms_connect = pmsconnect.PmsConnect()
        session_list = pms_connect.get_current_activity()

        if session_list:
            for session in session_list['sessions']:
                if int(session['session_key']) == self.get_session_key():
                    return session

        return None

    def update_db_session(self, session=None):
        # Update our session temp table values
        monitor_proc = activity_processor.ActivityProcessor()
        monitor_proc.write_session(session=session, notify=False)

    def on_start(self):
        if self.is_valid_session():
            session = self.get_live_session()

            if not session:
                return

            # Some DLNA clients create a new session temporarily when browsing the library
            # Wait and get session again to make sure it is an actual session
            if session['platform'] == 'DLNA':
                time.sleep(1)
                session = self.get_live_session()
                if not session:
                    return

            logger.debug(u"Tautulli ActivityHandler :: Session %s started by user %s (%s) with ratingKey %s (%s)."
                         % (str(session['session_key']), str(session['user_id']), session['username'],
                            str(session['rating_key']), session['full_title']))

            plexpy.NOTIFY_QUEUE.put({'stream_data': session, 'notify_action': 'on_play'})

            # Write the new session to our temp session table
            self.update_db_session(session=session)

    def on_stop(self, force_stop=False):
        if self.is_valid_session():
            logger.debug(u"Tautulli ActivityHandler :: Session %s stopped." % str(self.get_session_key()))

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

            plexpy.NOTIFY_QUEUE.put({'stream_data': db_session, 'notify_action': 'on_stop'})

            # Write it to the history table
            monitor_proc = activity_processor.ActivityProcessor()
            monitor_proc.write_session_history(session=db_session)

            # Remove the session from our temp session table
            logger.debug(u"Tautulli ActivityHandler :: Removing sessionKey %s ratingKey %s from session queue"
                         % (str(self.get_session_key()), str(self.get_rating_key())))
            ap.delete_session(session_key=self.get_session_key())
            delete_metadata_cache(self.get_session_key())

    def on_pause(self, still_paused=False):
        if self.is_valid_session():
            if not still_paused:
                logger.debug(u"Tautulli ActivityHandler :: Session %s paused." % str(self.get_session_key()))

            # Set the session last_paused timestamp
            ap = activity_processor.ActivityProcessor()
            ap.set_session_last_paused(session_key=self.get_session_key(), timestamp=int(time.time()))

            # Update the session state and viewOffset
            ap.set_session_state(session_key=self.get_session_key(),
                                 state=self.timeline['state'],
                                 view_offset=self.timeline['viewOffset'],
                                 stopped=int(time.time()))

            # Retrieve the session data from our temp table
            db_session = ap.get_session_by_key(session_key=self.get_session_key())

            if not still_paused:
                plexpy.NOTIFY_QUEUE.put({'stream_data': db_session, 'notify_action': 'on_pause'})

    def on_resume(self):
        if self.is_valid_session():
            logger.debug(u"Tautulli ActivityHandler :: Session %s resumed." % str(self.get_session_key()))

            # Set the session last_paused timestamp
            ap = activity_processor.ActivityProcessor()
            ap.set_session_last_paused(session_key=self.get_session_key(), timestamp=None)

            # Update the session state and viewOffset
            ap.set_session_state(session_key=self.get_session_key(),
                                 state=self.timeline['state'],
                                 view_offset=self.timeline['viewOffset'],
                                 stopped=int(time.time()))

            # Retrieve the session data from our temp table
            db_session = ap.get_session_by_key(session_key=self.get_session_key())

            plexpy.NOTIFY_QUEUE.put({'stream_data': db_session, 'notify_action': 'on_resume'})

    def on_buffer(self):
        if self.is_valid_session():
            logger.debug(u"Tautulli ActivityHandler :: Session %s is buffering." % self.get_session_key())
            ap = activity_processor.ActivityProcessor()
            db_stream = ap.get_session_by_key(session_key=self.get_session_key())

            # Increment our buffer count
            ap.increment_session_buffer_count(session_key=self.get_session_key())

            # Get our current buffer count
            current_buffer_count = ap.get_session_buffer_count(self.get_session_key())
            logger.debug(u"Tautulli ActivityHandler :: Session %s buffer count is %s." %
                         (self.get_session_key(), current_buffer_count))

            # Get our last triggered time
            buffer_last_triggered = ap.get_session_buffer_trigger_time(self.get_session_key())

            # Update the session state and viewOffset
            ap.set_session_state(session_key=self.get_session_key(),
                                 state=self.timeline['state'],
                                 view_offset=self.timeline['viewOffset'],
                                 stopped=int(time.time()))

            time_since_last_trigger = 0
            if buffer_last_triggered:
                logger.debug(u"Tautulli ActivityHandler :: Session %s buffer last triggered at %s." %
                             (self.get_session_key(), buffer_last_triggered))
                time_since_last_trigger = int(time.time()) - int(buffer_last_triggered)

            if plexpy.CONFIG.BUFFER_THRESHOLD > 0 and (current_buffer_count >= plexpy.CONFIG.BUFFER_THRESHOLD and \
                time_since_last_trigger == 0 or time_since_last_trigger >= plexpy.CONFIG.BUFFER_WAIT):
                ap.set_session_buffer_trigger_time(session_key=self.get_session_key())

                # Retrieve the session data from our temp table
                db_session = ap.get_session_by_key(session_key=self.get_session_key())

                plexpy.NOTIFY_QUEUE.put({'stream_data': db_session, 'notify_action': 'on_buffer'})

    # This function receives events from our websocket connection
    def process(self):
        if self.is_valid_session():
            ap = activity_processor.ActivityProcessor()
            db_session = ap.get_session_by_key(session_key=self.get_session_key())

            this_state = self.timeline['state']
            this_key = str(self.timeline['ratingKey'])

            # If we already have this session in the temp table, check for state changes
            if db_session:
                # Re-schedule the callback to reset the 5 minutes timer
                schedule_callback('session_key-{}'.format(self.get_session_key()),
                                  function=force_stop_stream, args=[self.get_session_key()], minutes=5)

                last_state = db_session['state']
                last_key = str(db_session['rating_key'])

                # Make sure the same item is being played
                if this_key == last_key:
                    # Update the session state and viewOffset
                    if this_state == 'playing':
                        # Update the session in our temp session table
                        # if the last set temporary stopped time exceeds 15 seconds
                        if int(time.time()) - db_session['stopped'] > 60:
                            session = self.get_live_session()
                            if session:
                                self.update_db_session(session=session)

                    # Start our state checks
                    if this_state != last_state:
                        if this_state == 'paused':
                            self.on_pause()
                        elif last_state == 'paused' and this_state == 'playing':
                            self.on_resume()
                        elif this_state == 'stopped':
                            self.on_stop()

                            # Remove the callback if the stream is stopped
                            schedule_callback('session_key-{}'.format(self.get_session_key()), remove_job=True)

                    elif this_state == 'buffering':
                        self.on_buffer()

                    elif this_state == 'paused':
                        # Update the session last_paused timestamp
                        self.on_pause(still_paused=True)

                # If a client doesn't register stop events (I'm looking at you PHT!) check if the ratingKey has changed
                else:
                    # Manually stop and start
                    # Set force_stop so that we don't overwrite our last viewOffset
                    self.on_stop(force_stop=True)
                    self.on_start()

                # Monitor if the stream has reached the watch percentage for notifications
                # The only purpose of this is for notifications
                if this_state != 'buffering':
                    progress_percent = helpers.get_percent(db_session['view_offset'], db_session['duration'])
                    notify_states = notification_handler.get_notify_state(session=db_session)
                    if (db_session['media_type'] == 'movie' and progress_percent >= plexpy.CONFIG.MOVIE_WATCHED_PERCENT or
                        db_session['media_type'] == 'episode' and progress_percent >= plexpy.CONFIG.TV_WATCHED_PERCENT or
                        db_session['media_type'] == 'track' and progress_percent >= plexpy.CONFIG.MUSIC_WATCHED_PERCENT) \
                        and not any(d['notify_action'] == 'on_watched' for d in notify_states):
                        plexpy.NOTIFY_QUEUE.put({'stream_data': db_session, 'notify_action': 'on_watched'})

            else:
                # We don't have this session in our table yet, start a new one.
                if this_state != 'buffering':
                    self.on_start()

                    # Schedule a callback to force stop a stale stream 5 minutes later
                    schedule_callback('session_key-{}'.format(self.get_session_key()),
                                      function=force_stop_stream, args=[self.get_session_key()], minutes=5)


class TimelineHandler(object):

    def __init__(self, timeline):
        self.timeline = timeline

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
        metadata = pms_connect.get_metadata_details(self.get_rating_key())

        if metadata:
            return metadata

        return None

    # This function receives events from our websocket connection
    def process(self):
        if self.is_item():
            global RECENTLY_ADDED_QUEUE

            rating_key = self.get_rating_key()

            media_types = {1: 'movie',
                           2: 'show',
                           3: 'season',
                           4: 'episode',
                           8: 'artist',
                           9: 'album',
                           10: 'track'}

            state_type = self.timeline.get('state')
            media_type = media_types.get(self.timeline.get('type'))
            section_id = self.timeline.get('sectionID', 0)
            title = self.timeline.get('title', 'Unknown')
            metadata_state = self.timeline.get('metadataState')
            media_state = self.timeline.get('mediaState')
            queue_size = self.timeline.get('queueSize')

            # Add a new media item to the recently added queue
            if media_type and section_id > 0 and \
                ((state_type == 0 and metadata_state == 'created')):  # or \
                #(plexpy.CONFIG.NOTIFY_RECENTLY_ADDED_UPGRADE and state_type in (1, 5) and \
                 #media_state == 'analyzing' and queue_size is None)):

                if media_type in ('episode', 'track'):
                    metadata = self.get_metadata()
                    if metadata:
                        grandparent_rating_key = int(metadata['grandparent_rating_key'])
                        parent_rating_key = int(metadata['parent_rating_key'])
                        
                        grandparent_set = RECENTLY_ADDED_QUEUE.get(grandparent_rating_key, set())
                        grandparent_set.add(parent_rating_key)
                        RECENTLY_ADDED_QUEUE[grandparent_rating_key] = grandparent_set

                        parent_set = RECENTLY_ADDED_QUEUE.get(parent_rating_key, set())
                        parent_set.add(rating_key)
                        RECENTLY_ADDED_QUEUE[parent_rating_key] = parent_set

                        RECENTLY_ADDED_QUEUE[rating_key] = set([grandparent_rating_key])

                        logger.debug(u"Tautulli TimelineHandler :: Library item '%s' (%s, grandparent %s) added to recently added queue."
                                     % (title, str(rating_key), str(grandparent_rating_key)))

                        # Schedule a callback to clear the recently added queue
                        schedule_callback('rating_key-{}'.format(grandparent_rating_key), function=clear_recently_added_queue,
                                          args=[grandparent_rating_key], seconds=plexpy.CONFIG.NOTIFY_RECENTLY_ADDED_DELAY)

                elif media_type in ('season', 'album'):
                    metadata = self.get_metadata()
                    if metadata:
                        parent_rating_key = int(metadata['parent_rating_key'])

                        parent_set = RECENTLY_ADDED_QUEUE.get(parent_rating_key, set())
                        parent_set.add(rating_key)
                        RECENTLY_ADDED_QUEUE[parent_rating_key] = parent_set

                        logger.debug(u"Tautulli TimelineHandler :: Library item '%s' (%s , parent %s) added to recently added queue."
                                     % (title, str(rating_key), str(parent_rating_key)))

                        # Schedule a callback to clear the recently added queue
                        schedule_callback('rating_key-{}'.format(parent_rating_key), function=clear_recently_added_queue,
                                          args=[parent_rating_key], seconds=plexpy.CONFIG.NOTIFY_RECENTLY_ADDED_DELAY)

                else:
                    queue_set = RECENTLY_ADDED_QUEUE.get(rating_key, set())
                    RECENTLY_ADDED_QUEUE[rating_key] = queue_set

                    logger.debug(u"Tautulli TimelineHandler :: Library item '%s' (%s) added to recently added queue."
                                 % (title, str(rating_key)))

                    # Schedule a callback to clear the recently added queue
                    schedule_callback('rating_key-{}'.format(rating_key), function=clear_recently_added_queue,
                                      args=[rating_key], seconds=plexpy.CONFIG.NOTIFY_RECENTLY_ADDED_DELAY)

            # A movie, show, or artist is done processing
            elif media_type in ('movie', 'show', 'artist') and section_id > 0 and \
                state_type == 5 and metadata_state is None and queue_size is None and \
                rating_key in RECENTLY_ADDED_QUEUE:
                
                logger.debug(u"Tautulli TimelineHandler :: Library item '%s' (%s) done processing metadata."
                             % (title, str(rating_key)))

            # An item was deleted, make sure it is removed from the queue
            elif state_type == 9 and metadata_state == 'deleted':
                if rating_key in RECENTLY_ADDED_QUEUE and not RECENTLY_ADDED_QUEUE[rating_key]:
                    logger.debug(u"Tautulli TimelineHandler :: Library item %s removed from recently added queue."
                                 % str(rating_key))
                    del_keys(rating_key)

                    # Remove the callback if the item is removed
                    schedule_callback('rating_key-{}'.format(rating_key), remove_job=True)


def del_keys(key):
    if isinstance(key, set):
        for child_key in key:
            del_keys(child_key)
    elif key in RECENTLY_ADDED_QUEUE:
        del_keys(RECENTLY_ADDED_QUEUE.pop(key))


def schedule_callback(id, function=None, remove_job=False, args=None, **kwargs):
    if ACTIVITY_SCHED.get_job(id):
        if remove_job:
            ACTIVITY_SCHED.remove_job(id)
        else:
            ACTIVITY_SCHED.reschedule_job(
                id, args=args, trigger=DateTrigger(
                    run_date=datetime.datetime.now() + datetime.timedelta(**kwargs)))
    elif not remove_job:
        ACTIVITY_SCHED.add_job(
            function, args=args, id=id, trigger=DateTrigger(
                run_date=datetime.datetime.now() + datetime.timedelta(**kwargs)))
    

def force_stop_stream(session_key):
    ap = activity_processor.ActivityProcessor()
    session = ap.get_session_by_key(session_key=session_key)

    success = ap.write_session_history(session=session)

    if success:
        # If session is written to the databaase successfully, remove the session from the session table
        logger.info(u"Tautulli ActivityHandler :: Removing stale stream with sessionKey %s ratingKey %s from session queue"
                    % (session['session_key'], session['rating_key']))
        ap.delete_session(session_key=session_key)

    else:
        session['write_attempts'] += 1

        if session['write_attempts'] < plexpy.CONFIG.SESSION_DB_WRITE_ATTEMPTS:
            logger.warn(u"Tautulli ActivityHandler :: Failed to write stream with sessionKey %s ratingKey %s to the database. " \
                        "Will try again in 30 seconds. Write attempt %s."
                        % (session['session_key'], session['rating_key'], str(session['write_attempts'])))
            ap.increment_write_attempts(session_key=session_key)

            # Reschedule for 30 seconds later
            schedule_callback('session_key={}'.format(session_key), function=force_stop_stream,
                              args=[session_key], seconds=30)

        else:
            logger.warn(u"Tautulli ActivityHandler :: Failed to write stream with sessionKey %s ratingKey %s to the database. " \
                        "Removing session from the database. Write attempt %s."
                        % (session['session_key'], session['rating_key'], str(session['write_attempts'])))
            logger.info(u"Tautulli ActivityHandler :: Removing stale stream with sessionKey %s ratingKey %s from session queue"
                        % (session['session_key'], session['rating_key']))
            ap.delete_session(session_key=session_key)
            delete_metadata_cache(session_key)


def clear_recently_added_queue(rating_key):
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
    logger.debug(u"Tautulli TimelineHandler :: Library item %s added to Plex." % str(rating_key))
    pms_connect = pmsconnect.PmsConnect()
    metadata = pms_connect.get_metadata_details(rating_key)

    if metadata:
        notify = True
        now = int(time.time())

        if helpers.cast_to_int(metadata['added_at']) < now - 86400:  # Updated more than 24 hours ago
            logger.debug(u"Tautulli TimelineHandler :: Library item %s added more than 24 hours ago. Not notifying."
                         % str(rating_key))
            notify = False

        data_factory = datafactory.DataFactory()
        if 'child_keys' not in kwargs:
            if data_factory.get_recently_added_item(rating_key):
                logger.debug(u"Tautulli TimelineHandler :: Library item %s added already. Not notifying again."
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

        logger.debug(u"Added %s items to the recently_added database table." % str(len(all_keys)))

    else:
        logger.error(u"Tautulli TimelineHandler :: Unable to retrieve metadata for rating_key %s" % str(rating_key))


def delete_metadata_cache(session_key):
    try:
        os.remove(os.path.join(plexpy.CONFIG.CACHE_DIR, 'metadata-sessionKey-%s.json' % session_key))
    except IOError as e:
        logger.error(u"Tautulli ActivityHandler :: Failed to remove metadata cache file (sessionKey %s): %s"
                     % (session_key, e))
