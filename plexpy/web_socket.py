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

name = 'websocket'
opcode_data = (websocket.ABNF.OPCODE_TEXT, websocket.ABNF.OPCODE_BINARY)
ws_shutdown = False
pong_timer = None
pong_count = 0


def start_thread():
    try:
        # Check for any existing sessions on start up
        activity_pinger.check_active_sessions(ws_request=True)
    except Exception as e:
        logger.error(u"Tautulli WebSocket :: Failed to check for active sessions: %s." % e)
        logger.warn(u"Tautulli WebSocket :: Attempt to fix by flushing temporary sessions...")
        database.delete_sessions()

    # Start the websocket listener on it's own thread
    thread = threading.Thread(target=run)
    thread.daemon = True
    thread.start()


def on_connect():
    if plexpy.PLEX_SERVER_UP is None:
        plexpy.PLEX_SERVER_UP = True

    if not plexpy.PLEX_SERVER_UP:
        logger.info(u"Tautulli WebSocket :: The Plex Media Server is back up.")
        plexpy.NOTIFY_QUEUE.put({'notify_action': 'on_intup'})
        plexpy.PLEX_SERVER_UP = True

    plexpy.initialize_scheduler()
    send_ping()


def on_disconnect():
    if plexpy.PLEX_SERVER_UP is None:
        plexpy.PLEX_SERVER_UP = False

    if plexpy.PLEX_SERVER_UP:
        logger.info(u"Tautulli WebSocket :: Unable to get a response from the server, Plex server is down.")
        plexpy.NOTIFY_QUEUE.put({'notify_action': 'on_intdown'})
        plexpy.PLEX_SERVER_UP = False

    activity_processor.ActivityProcessor().set_temp_stopped()
    plexpy.initialize_scheduler()


def reconnect():
    close()
    logger.info(u"Tautulli WebSocket :: Reconnecting websocket...")
    start_thread()


def shutdown():
    global ws_shutdown
    ws_shutdown = True
    close()


def close():
    logger.info(u"Tautulli WebSocket :: Disconnecting websocket...")
    plexpy.WEBSOCKET.close()
    plexpy.WS_CONNECTED = False


def send_ping():
    if plexpy.WS_CONNECTED:
        # logger.debug(u"Tautulli WebSocket :: Sending ping.")
        plexpy.WEBSOCKET.ping("Hi?")

        global pong_timer
        pong_timer = threading.Timer(5.0, wait_pong)
        pong_timer.daemon = True
        pong_timer.start()


def wait_pong():
    global pong_count
    pong_count += 1

    logger.warning(u"Tautulli WebSocket :: Failed to receive pong from websocket, ping attempt %s." % str(pong_count))

    if pong_count >= plexpy.CONFIG.WEBSOCKET_CONNECTION_ATTEMPTS:
        pong_count = 0
        close()


def receive_pong():
    # logger.debug(u"Tautulli WebSocket :: Received pong.")
    global pong_timer
    global pong_count
    if pong_timer:
        pong_timer = pong_timer.cancel()
        pong_count = 0


def run():
    from websocket import create_connection

    if plexpy.CONFIG.PMS_SSL and plexpy.CONFIG.PMS_URL[:5] == 'https':
        uri = plexpy.CONFIG.PMS_URL.replace('https://', 'wss://') + '/:/websockets/notifications'
        secure = 'secure '
    else:
        uri = 'ws://%s:%s/:/websockets/notifications' % (
            plexpy.CONFIG.PMS_IP,
            plexpy.CONFIG.PMS_PORT
        )
        secure = ''

    # Set authentication token (if one is available)
    if plexpy.CONFIG.PMS_TOKEN:
        header = ["X-Plex-Token: %s" % plexpy.CONFIG.PMS_TOKEN]
    else:
        header = []

    global ws_shutdown
    ws_shutdown = False
    reconnects = 0

    # Try an open the websocket connection
    logger.info(u"Tautulli WebSocket :: Opening %swebsocket." % secure)
    try:
        plexpy.WEBSOCKET = create_connection(uri, header=header)
        logger.info(u"Tautulli WebSocket :: Ready")
        plexpy.WS_CONNECTED = True
    except (websocket.WebSocketException, IOError, Exception) as e:
        logger.error("Tautulli WebSocket :: %s." % e)

    if plexpy.WS_CONNECTED:
        on_connect()

    while plexpy.WS_CONNECTED:
        try:
            process(*receive(plexpy.WEBSOCKET))

            # successfully received data, reset reconnects counter
            reconnects = 0

        except websocket.WebSocketConnectionClosedException:
            if ws_shutdown:
                break

            if reconnects == 0:
                logger.warn(u"Tautulli WebSocket :: Connection has closed.")

            if not plexpy.CONFIG.PMS_IS_CLOUD and reconnects < plexpy.CONFIG.WEBSOCKET_CONNECTION_ATTEMPTS:
                reconnects += 1

                # Sleep 5 between connection attempts
                if reconnects > 1:
                    time.sleep(plexpy.CONFIG.WEBSOCKET_CONNECTION_TIMEOUT)

                logger.warn(u"Tautulli WebSocket :: Reconnection attempt %s." % str(reconnects))

                try:
                    plexpy.WEBSOCKET = create_connection(uri, header=header)
                    logger.info(u"Tautulli WebSocket :: Ready")
                    plexpy.WS_CONNECTED = True
                except (websocket.WebSocketException, IOError, Exception) as e:
                    logger.error("Tautulli WebSocket :: %s." % e)

            else:
                close()
                break

        except (websocket.WebSocketException, Exception) as e:
            if ws_shutdown:
                break

            logger.error("Tautulli WebSocket :: %s." % e)
            close()
            break

    if not plexpy.WS_CONNECTED and not ws_shutdown:
        on_disconnect()

    logger.debug(u"Tautulli WebSocket :: Leaving thread.")


def receive(ws):
    frame = ws.recv_frame()

    if not frame:
        raise websocket.WebSocketException("Not a valid frame %s" % frame)
    elif frame.opcode in opcode_data:
        return frame.opcode, frame.data
    elif frame.opcode == websocket.ABNF.OPCODE_CLOSE:
        ws.send_close()
        return frame.opcode, None
    elif frame.opcode == websocket.ABNF.OPCODE_PING:
        # logger.debug(u"Tautulli WebSocket :: Received ping, sending pong.")
        ws.pong("Hi!")
    elif frame.opcode == websocket.ABNF.OPCODE_PONG:
        receive_pong()

    return None, None


def process(opcode, data):
    if opcode not in opcode_data:
        return False

    try:
        logger.websocket_debug(data)
        info = json.loads(data)
    except Exception as e:
        logger.warn(u"Tautulli WebSocket :: Error decoding message from websocket: %s" % e)
        logger.websocket_error(data)
        return False

    info = info.get('NotificationContainer', info)
    type = info.get('type')

    if not type:
        return False

    if type == 'playing':
        time_line = info.get('PlaySessionStateNotification', info.get('_children', {}))

        if not time_line:
            logger.debug(u"Tautulli WebSocket :: Session found but unable to get timeline data.")
            return False

        try:
            activity = activity_handler.ActivityHandler(timeline=time_line[0])
            activity.process()
        except Exception as e:
            logger.error(u"Tautulli WebSocket :: Failed to process session data: %s." % e)

    if type == 'timeline':
        time_line = info.get('TimelineEntry', info.get('_children', {}))

        if not time_line:
            logger.debug(u"Tautulli WebSocket :: Timeline event found but unable to get timeline data.")
            return False

        try:
            activity = activity_handler.TimelineHandler(timeline=time_line[0])
            activity.process()
        except Exception as e:
            logger.error(u"Tautulli WebSocket :: Failed to process timeline data: %s." % e)

    return True
