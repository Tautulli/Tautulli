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
import logger

name = 'websocket'
opcode_data = (websocket.ABNF.OPCODE_TEXT, websocket.ABNF.OPCODE_BINARY)
ws_reconnect = False


def start_thread():
    if plexpy.CONFIG.FIRST_RUN_COMPLETE:
        # Check for any existing sessions on start up
        activity_pinger.check_active_sessions(ws_request=True)
        # Start the websocket listener on it's own thread
        threading.Thread(target=run).start()


def on_disconnect():
    activity_processor.ActivityProcessor().set_temp_stopped()
    plexpy.initialize_scheduler()


def reconnect():
    global ws_reconnect
    ws_reconnect = True


def run():
    from websocket import create_connection

    if plexpy.CONFIG.PMS_SSL and plexpy.CONFIG.PMS_URL[:5] == 'https':
        uri = plexpy.CONFIG.PMS_URL.replace('https://', 'wss://') + '/:/websockets/notifications'
        secure = ' secure'
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

    global ws_reconnect
    ws_reconnect = False
    reconnects = 0
    ws_exception = False

    # Try an open the websocket connection
    while not plexpy.WS_CONNECTED and reconnects <= plexpy.CONFIG.WEBSOCKET_CONNECTION_ATTEMPTS:
        try:
            logger.info(u"Tautulli WebSocket :: Opening%s websocket, connection attempt %s." % (secure, str(reconnects + 1)))
            ws = create_connection(uri, header=header)
            reconnects = 0
            logger.info(u"Tautulli WebSocket :: Ready")
            plexpy.WS_CONNECTED = True

            if not plexpy.PLEX_SERVER_UP:
                logger.info(u"Tautulli WebSocket :: The Plex Media Server is back up.")
                plexpy.NOTIFY_QUEUE.put({'notify_action': 'on_intup'})
                plexpy.PLEX_SERVER_UP = True

            plexpy.initialize_scheduler()

        except IOError as e:
            logger.error(u"Tautulli WebSocket :: %s." % e)
            reconnects += 1
            time.sleep(plexpy.CONFIG.WEBSOCKET_CONNECTION_TIMEOUT)

        except (websocket.WebSocketException, Exception) as e:
            logger.error(u"Tautulli WebSocket :: %s." % e)
            plexpy.WS_CONNECTED = False
            ws_exception = True
            break

    while plexpy.WS_CONNECTED:
        try:
            process(*receive(ws))

            # successfully received data, reset reconnects counter
            reconnects = 0

        except websocket.WebSocketConnectionClosedException:
            if reconnects <= plexpy.CONFIG.WEBSOCKET_CONNECTION_ATTEMPTS:
                reconnects += 1

                # Sleep 5 between connection attempts
                if reconnects > 1:
                    time.sleep(plexpy.CONFIG.WEBSOCKET_CONNECTION_TIMEOUT)

                logger.warn(u"Tautulli WebSocket :: Connection has closed, reconnection attempt %s." % reconnects)
                try:
                    ws = create_connection(uri, header=header)
                    logger.info(u"Tautulli WebSocket :: Ready")
                    plexpy.WS_CONNECTED = True
                except IOError as e:
                    logger.info(u"Tautulli WebSocket :: %s." % e)

            else:
                ws.shutdown()
                plexpy.WS_CONNECTED = False
                break

        except (websocket.WebSocketException, Exception) as e:
            logger.error(u"Tautulli WebSocket :: %s." % e)
            plexpy.WS_CONNECTED = False
            ws_exception = True
            break

        # Check if we recieved a restart notification and close websocket connection cleanly
        if ws_reconnect:
            logger.info(u"Tautulli WebSocket :: Reconnecting websocket...")
            ws.shutdown()
            plexpy.WS_CONNECTED = False
            start_thread()
    
    if not plexpy.WS_CONNECTED and not ws_reconnect:
        logger.error(u"Tautulli WebSocket :: Connection unavailable.")

        if not ws_exception and plexpy.PLEX_SERVER_UP:
            logger.info(u"Tautulli WebSocket :: Unable to get an internal response from the server, Plex server is down.")
            plexpy.NOTIFY_QUEUE.put({'notify_action': 'on_intdown'})
            plexpy.PLEX_SERVER_UP = False

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
        ws.pong("Hi!")

    return None, None


def process(opcode, data):
    if opcode not in opcode_data:
        return False

    try:
        logger.websocket_debug(data)
        info = json.loads(data)
    except Exception as e:
        logger.warn(u"Tautulli WebSocket :: Error decoding message from websocket: %s" % e)
        logger.debug(data)
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
