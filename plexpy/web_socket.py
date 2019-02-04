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

import json
import threading
import time

import websocket

import plexpy
import activity_handler
import activity_pinger
import activity_processor
import database
import logger


class ServerWebSocketThread(threading.Thread):

    def __init__(self, server, name=None, target=None):
        threading.Thread.__init__(self, name=name, target=target)
        self.server = server


class ServerWebSocket(object):

    WS_CONNECTION = None
    WS_THREAD = None
    server = None

    opcode_data = (websocket.ABNF.OPCODE_TEXT, websocket.ABNF.OPCODE_BINARY)
    ws_shutdown = False
    pong_timer = None
    pong_count = 0

    def __init__(self, server, ready=None):
        self.server = server
        self.ready = ready

    def start(self):
        self.WS_THREAD = ServerWebSocketThread(self.server, name="WebSocket-" + self.server.CONFIG.PMS_NAME, target=self.connect)
        self.WS_THREAD.daemon = True
        if not self.WS_THREAD.isAlive():
            self.WS_THREAD.start()

    def shutdown(self):
        logger.info("Tautulli WebSocket :: %s: Shutting Down Websocket..." % self.server.CONFIG.PMS_NAME)
        self.ws_shutdown = True
        self.close()
        self.WS_THREAD.join(timeout=30)

    def close(self):
        logger.info("Tautulli WebSocket :: %s: Disconnecting websocket..." % self.server.CONFIG.PMS_NAME)
        self.server.WS_CONNECTED = False
        if self.WS_CONNECTION:
            self.WS_CONNECTION.close()

    def reconnect(self):
        self.close()
        logger.info("Tautulli WebSocket :: %s: Reconnecting websocket..." % self.server.CONFIG.PMS_NAME)
        self.connect()

    def connect(self):
        from websocket import create_connection
        if self.server.CONFIG.PMS_SSL and self.server.CONFIG.PMS_URL[:5] == 'https':
            uri = self.server.CONFIG.PMS_URL.replace('https://', 'wss://') + '/:/websockets/notifications'
            secure = 'secure '
        else:
            uri = 'ws://%s:%s/:/websockets/notifications' % (
                self.server.CONFIG.PMS_IP,
                self.server.CONFIG.PMS_PORT
            )
            secure = ''

        # Set authentication token (if one is available)
        if plexpy.CONFIG.PMS_TOKEN:
            header = ["X-Plex-Token: %s" % plexpy.CONFIG.PMS_TOKEN]
        else:
            header = []

        self.ws_shutdown = False
        reconnects = 0

        # Try an open the websocket connection
        logger.info("Tautulli WebSocket :: %s: Opening %s websocket." % (self.server.CONFIG.PMS_NAME, secure))
        try:
            self.WS_CONNECTION = create_connection(uri, header=header)
            logger.info("Tautulli WebSocket :: %s: Ready" % self.server.CONFIG.PMS_NAME)
            self.server.WS_CONNECTED = True
        except (websocket.WebSocketException, IOError, Exception) as e:
            logger.error("Tautulli WebSocket :: %s: %s." % (self.server.CONFIG.PMS_NAME, e))

        if self.server.WS_CONNECTED:
            self.on_connect()

        self.ready.set()

        while self.server.WS_CONNECTED:
            try:
                self.process(*self.receive(self.WS_CONNECTION))

                # successfully received data, reset reconnects counter
                reconnects = 0

            except websocket.WebSocketConnectionClosedException:
                if self.ws_shutdown:
                    break

                if reconnects == 0:
                    logger.warn("Tautulli WebSocket :: %s: Connection has closed." % self.server.CONFIG.PMS_NAME)

                if not self.server.CONFIG.PMS_IS_CLOUD and reconnects < plexpy.CONFIG.WEBSOCKET_CONNECTION_ATTEMPTS:
                    reconnects += 1

                    # Sleep 5 between connection attempts
                    if reconnects > 1:
                        time.sleep(plexpy.CONFIG.WEBSOCKET_CONNECTION_TIMEOUT)

                    logger.warn("Tautulli WebSocket :: %s: Reconnection attempt %s." % (self.server.CONFIG.PMS_NAME, str(reconnects)))

                    try:
                        self.WS_CONNECTION = create_connection(uri, header=header)
                        logger.info("Tautulli WebSocket :: %s: Ready" % self.server.CONFIG.PMS_NAME)
                        self.server.WS_CONNECTED = True
                    except (websocket.WebSocketException, IOError, Exception) as e:
                        logger.error("Tautulli WebSocket :: %s: %s." % (self.server.CONFIG.PMS_NAME, e))

                else:
                    self.close()
                    break

            except (websocket.WebSocketException, Exception) as e:
                if self.ws_shutdown:
                    break

                if e.message == '[Errno 110] Connection timed out.':
                    if reconnects == 0:
                        logger.warn("Tautulli WebSocket :: %s: Connection timed out." % self.server.CONFIG.PMS_NAME)

                    if not self.server.CONFIG.PMS_IS_CLOUD and reconnects < plexpy.CONFIG.WEBSOCKET_CONNECTION_ATTEMPTS:
                        reconnects += 1
                    else:
                        logger.error("Tautulli WebSocket :: %s: %s." % (self.server.CONFIG.PMS_NAME, e))
                        self.close()
                        break
                else:
                    logger.error("Tautulli WebSocket :: %s: %s." % (self.server.CONFIG.PMS_NAME, e))
                    self.close()
                    break

        if not self.server.WS_CONNECTED and not self.ws_shutdown:
            self.on_disconnect()

        logger.debug("Tautulli WebSocket :: %s: Leaving thread." % self.server.CONFIG.PMS_NAME)

    def on_connect(self):
        if self.server.PLEX_SERVER_UP is None:
            self.server.PLEX_SERVER_UP = True

        if not self.server.PLEX_SERVER_UP:
            logger.info("Tautulli WebSocket :: %s: The Plex Media Server is back up." % self.server.CONFIG.PMS_NAME)
            plexpy.NOTIFY_QUEUE.put({'notify_action': 'on_intup', 'server_id': self.server.CONFIG.ID})
            self.server.PLEX_SERVER_UP = True

        if plexpy.CONFIG.WEBSOCKET_MONITOR_PING_PONG:
            self.send_ping()

        self.server.initialize_scheduler()

    def on_disconnect(self):
        if self.server.PLEX_SERVER_UP is None or self.server.PLEX_SERVER_UP:
            logger.info("Tautulli WebSocket :: %s: Unable to get a response from the server, Plex server is down." % self.server.CONFIG.PMS_NAME)
            plexpy.NOTIFY_QUEUE.put({'notify_action': 'on_intdown', 'server_id': self.server.CONFIG.ID})
            self.server.PLEX_SERVER_UP = False

        activity_processor.ActivityProcessor(server=self.server).set_temp_stopped()
        self.server.initialize_scheduler()

    def send_ping(self):
        if self.server.WS_CONNECTED:
            #logger.debug("Tautulli WebSocket :: %s: Sending ping." % self.server.CONFIG.PMS_NAME)
            self.WS_CONNECTION.ping("Hi?")

            self.pong_timer = threading.Timer(5.0, self.wait_pong)
            self.pong_timer.daemon = True
            self.pong_timer.start()

    def wait_pong(self):
        self.pong_count += 1

        logger.warning("Tautulli WebSocket :: %s: Failed to receive pong from websocket, ping attempt %s." % (self.server.CONFIG.PMS_NAME, str(self.pong_count)))

        if self.pong_count >= plexpy.CONFIG.WEBSOCKET_CONNECTION_ATTEMPTS:
            self.pong_count = 0
            self.close()

    def receive_pong(self):
        #logger.debug("Tautulli WebSocket :: %s: Received pong." % self.server.CONFIG.PMS_NAME)
        if self.pong_timer:
            self.pong_timer = self.pong_timer.cancel()
            self.pong_count = 0

    def receive(self, ws):
        frame = ws.recv_frame()

        if not frame:
            raise websocket.WebSocketException("Not a valid frame %s" % frame)
        elif frame.opcode in self.opcode_data:
            return frame.opcode, frame.data
        elif frame.opcode == websocket.ABNF.OPCODE_CLOSE:
            ws.send_close()
            return frame.opcode, None
        elif frame.opcode == websocket.ABNF.OPCODE_PING:
            #logger.debug("Tautulli WebSocket :: %s: Received ping, sending pong." % self.server.CONFIG.PMS_NAME)
            ws.pong("Hi!")
        elif frame.opcode == websocket.ABNF.OPCODE_PONG:
            self.receive_pong()

        return None, None

    def process(self, opcode, data):
        if opcode not in self.opcode_data:
            return False

        try:
            logger.websocket_debug(data)
            info = json.loads(data)
        except Exception as e:
            logger.warn("Tautulli WebSocket :: %s: Error decoding message from websocket: %s" % (self.server.CONFIG.PMS_NAME, e))
            logger.websocket_error(data)
            return False

        info = info.get('NotificationContainer', info)
        type = info.get('type')

        if not type:
            return False

        if type == 'playing':
            time_line = info.get('PlaySessionStateNotification', info.get('_children', {}))

            if not time_line:
                logger.debug("Tautulli WebSocket :: %s: Session found but unable to get timeline data." % self.server.CONFIG.PMS_NAME)
                return False

            try:
                activity = activity_handler.ActivityHandler(self.server, timeline=time_line[0])
                activity.process()
            except Exception as e:
                logger.error("Tautulli WebSocket :: %s: Failed to process session data: %s." % (self.server.CONFIG.PMS_NAME, e))

        if type == 'timeline':
            time_line = info.get('TimelineEntry', info.get('_children', {}))

            if not time_line:
                logger.debug("Tautulli WebSocket :: %s: Timeline event found but unable to get timeline data." % self.server.CONFIG.PMS_NAME)
                return False

            try:
                activity = activity_handler.TimelineHandler(self.server, timeline=time_line[0])
                activity.process()
            except Exception as e:
                logger.error("Tautulli WebSocket :: %s: Failed to process timeline data: %s." % (self.server.CONFIG.PMS_NAME, e))

        return True
