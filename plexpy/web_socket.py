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

# Mostly borrowed from https://github.com/trakt/Plex-Trakt-Scrobbler

from __future__ import unicode_literals
from future.builtins import str

import json
import ssl
import threading
import time

import certifi
import websocket
from websocket import create_connection

import plexpy
if plexpy.PYTHON2:
    import activity_handler
    import activity_pinger
    import activity_processor
    import database
    import logger
    import plextv
    import server_manager
else:
    from plexpy import activity_handler
    from plexpy import activity_pinger
    from plexpy import activity_processor
    from plexpy import database
    from plexpy import logger
    from plexpy import plextv
    from plexpy import server_manager


name = 'websocket'
opcode_data = (websocket.ABNF.OPCODE_TEXT, websocket.ABNF.OPCODE_BINARY)
ws_shutdown = False
pong_timer = None
pong_count = 0


def isServerUp():
    return True

def start_threads():
    try:
        # Check for any existing sessions on start up
        activity_pinger.check_active_sessions(ws_request=True)
    except Exception as e:
        logger.error("Tautulli WebSocket :: Failed to check for active sessions: %s." % e)
        logger.warn("Tautulli WebSocket :: Attempt to fix by flushing temporary sessions...")
        database.delete_sessions()

    plex_servers = plextv.get_server_resources(return_servers=True)

    owned_servers = server_manager.ServerManger().get_server_list()


    # Start each websocket listener on it's own thread per server
    for owned_server in owned_servers:
        for server in plex_servers:
            if owned_server.server_id == server['pms_identifier']:
                for connection in server['connections']:
                    if connection['local']:
                        wss=WebSocketServer(connection, owned_server.server_id)
                        thread = threading.Thread(target=wss.run)
                        thread.daemon = True
                        thread.start()
                        break
                break


class WebSocketServer(object):
    def __init__(self, server, server_id):
        self.server=server
        self.WEBSOCKET = None
        self.WS_CONNECTED = False
        self.PLEX_SERVER_UP = None
        self.PLEX_REMOTE_ACCESS_UP = None
        self.server_id = server_id

    def on_connect(self):
        if self.PLEX_SERVER_UP is None:
            self.PLEX_SERVER_UP = True

        if not self.PLEX_SERVER_UP:
            logger.info("Tautulli WebSocket :: The Plex Media Server is back up.")
            self.PLEX_SERVER_UP = True

            if activity_handler.ACTIVITY_SCHED.get_job('on_intdown'):
                logger.debug("Tautulli WebSocket :: Cancelling scheduled Plex server down callback.")
                activity_handler.schedule_callback('on_intdown', remove_job=True)
            else:
                self.on_intup()

        plexpy.initialize_scheduler()
        if plexpy.CONFIG.WEBSOCKET_MONITOR_PING_PONG:
            self.send_ping()


    def on_disconnect(self):
        if self.PLEX_SERVER_UP is None:
            self.PLEX_SERVER_UP = False

        if self.PLEX_SERVER_UP:
            logger.info("Tautulli WebSocket :: Unable to get a response from the server, Plex server is down.")
            self.PLEX_SERVER_UP = False

            logger.debug("Tautulli WebSocket :: Scheduling Plex server down callback in %d seconds.",
                        plexpy.CONFIG.NOTIFY_SERVER_CONNECTION_THRESHOLD)
            activity_handler.schedule_callback('on_intdown', func=self.on_intdown,
                                            seconds=plexpy.CONFIG.NOTIFY_SERVER_CONNECTION_THRESHOLD)

        activity_processor.ActivityProcessor().set_temp_stopped()
        plexpy.initialize_scheduler()


    def on_intdown(self):
        plexpy.NOTIFY_QUEUE.put({'notify_action': 'on_intdown'})


    def on_intup(self):
        plexpy.NOTIFY_QUEUE.put({'notify_action': 'on_intup'})


    def reconnect(self):
        self.close()
        logger.info("Tautulli WebSocket :: Reconnecting websocket...")
        self.run()


    def shutdown(self):
        global ws_shutdown
        ws_shutdown = True
        self.close()


    def close(self):
        logger.info("Tautulli WebSocket :: Disconnecting websocket...")
        self.WEBSOCKET.close()
        self.WS_CONNECTED = False


    def send_ping(self):
        if self.WS_CONNECTED:
            # logger.debug("Tautulli WebSocket :: Sending ping.")
            self.WEBSOCKET.ping("Hi?")

            global pong_timer
            pong_timer = threading.Timer(5.0, self.wait_pong)
            pong_timer.daemon = True
            pong_timer.start()


    def wait_pong(self):
        global pong_count
        pong_count += 1

        logger.warn("Tautulli WebSocket :: Failed to receive pong from websocket, ping attempt %s." % str(pong_count))

        if pong_count >= plexpy.CONFIG.WEBSOCKET_CONNECTION_ATTEMPTS:
            pong_count = 0
            self.close()


    def receive_pong(self):
        # logger.debug("Tautulli WebSocket :: Received pong.")
        global pong_timer
        global pong_count
        if pong_timer:
            pong_timer = pong_timer.cancel()
            pong_count = 0


    def run(self):

        if plexpy.CONFIG.PMS_SSL:
            uri = ""
            if self.server:
                uri = self.server['uri'].replace('https://', 'wss://') + '/:/websockets/notifications'
            else:
                uri = plexpy.CONFIG.PMS_URL.replace('https://', 'wss://') + '/:/websockets/notifications'
            secure = 'secure '
            if plexpy.CONFIG.VERIFY_SSL_CERT:
                sslopt = {'ca_certs': certifi.where()}
            else:
                sslopt = {'cert_reqs': ssl.CERT_NONE}
        else:
            uri = ""
            if self.server:
                uri = 'ws://%s:%s/:/websockets/notifications' % (
                    self.server['address'],
                    self.server['port']
                )
            else:
                uri = 'ws://%s:%s/:/websockets/notifications' % (
                    plexpy.CONFIG.PMS_IP,
                    plexpy.CONFIG.PMS_PORT
                )
            secure = ''
            sslopt = None

        # Set authentication token (if one is available)
        if plexpy.CONFIG.PMS_TOKEN:
            header = {"X-Plex-Token": plexpy.CONFIG.PMS_TOKEN}
        else:
            header = None

        timeout = plexpy.CONFIG.PMS_TIMEOUT

        global ws_shutdown
        ws_shutdown = False
        reconnects = 0

        # Try an open the websocket connection
        logger.info("Tautulli WebSocket :: Opening %swebsocket." % secure)
        try:
            self.WEBSOCKET = create_connection(uri, timeout=timeout, header=header, sslopt=sslopt)
            logger.info("Tautulli WebSocket :: Ready")
            self.WS_CONNECTED = True
        except (websocket.WebSocketException, IOError, Exception) as e:
            logger.error("Tautulli WebSocket :: %s.", e)

        if self.WS_CONNECTED:
            self.on_connect()

        while self.WS_CONNECTED:
            try:
                self.process(*self.receive(self.WEBSOCKET))

                # successfully received data, reset reconnects counter
                reconnects = 0

            except websocket.WebSocketConnectionClosedException:
                if ws_shutdown:
                    break

                if reconnects == 0:
                    logger.warn("Tautulli WebSocket :: Connection has closed.")

                if not plexpy.CONFIG.PMS_IS_CLOUD and reconnects < plexpy.CONFIG.WEBSOCKET_CONNECTION_ATTEMPTS:
                    reconnects += 1

                    # Sleep 5 between connection attempts
                    if reconnects > 1:
                        time.sleep(plexpy.CONFIG.WEBSOCKET_CONNECTION_TIMEOUT)

                    logger.warn("Tautulli WebSocket :: Reconnection attempt %s." % str(reconnects))

                    try:
                        self.WEBSOCKET = create_connection(uri, timeout=timeout, header=header, sslopt=sslopt)
                        logger.info("Tautulli WebSocket :: Ready")
                        self.WS_CONNECTED = True
                    except (websocket.WebSocketException, IOError, Exception) as e:
                        logger.error("Tautulli WebSocket :: %s.", e)

                else:
                    self.close()
                    break

            except (websocket.WebSocketException, Exception) as e:
                if ws_shutdown:
                    break

                logger.error("Tautulli WebSocket :: %s.", e)
                self.close()
                break

        if not self.WS_CONNECTED and not ws_shutdown:
            self.on_disconnect()

        logger.debug("Tautulli WebSocket :: Leaving thread.")


    def receive(self, ws):
        frame = ws.recv_frame()

        if not frame:
            raise websocket.WebSocketException("Not a valid frame %s" % frame)
        elif frame.opcode in opcode_data:
            return frame.opcode, frame.data
        elif frame.opcode == websocket.ABNF.OPCODE_CLOSE:
            ws.send_close()
            return frame.opcode, None
        elif frame.opcode == websocket.ABNF.OPCODE_PING:
            # logger.debug("Tautulli WebSocket :: Received ping, sending pong.")
            ws.pong("Hi!")
        elif frame.opcode == websocket.ABNF.OPCODE_PONG:
            self.receive_pong()

        return None, None


    def process(self, opcode, data):
        if opcode not in opcode_data:
            return False

        try:
            data = data.decode('utf-8')
            logger.websocket_debug(data)
            event = json.loads(data)
        except Exception as e:
            logger.warn("Tautulli WebSocket :: Error decoding message from websocket: %s" % e)
            logger.websocket_error(data)
            return False

        event = event.get('NotificationContainer', event)
        event_type = event.get('type')

        if not event_type:
            return False

        if event_type == 'playing':
            event_data = event.get('PlaySessionStateNotification', event.get('_children', {}))

            if not event_data:
                logger.debug("Tautulli WebSocket :: Session event found but unable to get websocket data.")
                return False

            try:
                activity = activity_handler.ActivityHandler(timeline=event_data[0], server_id=self.server_id)
                activity.process()
            except Exception as e:
                logger.exception("Tautulli WebSocket :: Failed to process session data: %s." % e)

        if event_type == 'timeline':
            event_data = event.get('TimelineEntry', event.get('_children', {}))

            if not event_data:
                logger.debug("Tautulli WebSocket :: Timeline event found but unable to get websocket data.")
                return False

            try:
                activity = activity_handler.TimelineHandler(timeline=event_data[0], server_id=self.server_id)
                activity.process()
            except Exception as e:
                logger.exception("Tautulli WebSocket :: Failed to process timeline data: %s." % e)

        if event_type == 'reachability':
            event_data = event.get('ReachabilityNotification', event.get('_children', {}))

            if not event_data:
                logger.debug("Tautulli WebSocket :: Reachability event found but unable to get websocket data.")
                return False

            try:
                activity = activity_handler.ReachabilityHandler(data=event_data[0], server_id=self.server_id)
                activity.process()
            except Exception as e:
                logger.exception("Tautulli WebSocket :: Failed to process reachability data: %s." % e)

        return True
