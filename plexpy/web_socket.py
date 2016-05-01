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

# Mostly borrowed from https://github.com/trakt/Plex-Trakt-Scrobbler

from plexpy import logger, activity_pinger

import threading
import plexpy
import json
import time
import websocket

name = 'websocket'
opcode_data = (websocket.ABNF.OPCODE_TEXT, websocket.ABNF.OPCODE_BINARY)
ws_reconnect = False


def start_thread():
    # Check for any existing sessions on start up
    activity_pinger.check_active_sessions(ws_request=True)
    # Start the websocket listener on it's own thread
    threading.Thread(target=run).start()


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
        uri += '?X-Plex-Token=' + plexpy.CONFIG.PMS_TOKEN

    global ws_reconnect
    ws_reconnect = False
    ws_connected = False
    reconnects = 0

    # Try an open the websocket connection - if it fails after 15 retries fallback to polling
    while not ws_connected and reconnects <= 15:
        try:
            logger.info(u"PlexPy WebSocket :: Opening%s websocket, connection attempt %s." % (secure, str(reconnects + 1)))
            ws = create_connection(uri)
            reconnects = 0
            ws_connected = True
            logger.info(u"PlexPy WebSocket :: Ready")
        except IOError, e:
            logger.error(u"PlexPy WebSocket :: %s." % e)
            reconnects += 1
            time.sleep(5)

    while ws_connected:
        try:
            process(*receive(ws))

            # successfully received data, reset reconnects counter
            reconnects = 0
        except websocket.WebSocketConnectionClosedException:
            if reconnects <= 15:
                reconnects += 1

                # Sleep 5 between connection attempts
                if reconnects > 1:
                    time.sleep(5)

                logger.warn(u"PlexPy WebSocket :: Connection has closed, reconnecting...")
                try:
                    ws = create_connection(uri)
                except IOError, e:
                    logger.info(u"PlexPy WebSocket :: %s." % e)

            else:
                ws.shutdown()
                ws_connected = False
                break

        # Check if we recieved a restart notification and close websocket connection cleanly
        if ws_reconnect:
            logger.info(u"PlexPy WebSocket :: Reconnecting websocket...")
            ws.shutdown()
            ws_connected = False
            start_thread()
    
    if not ws_connected and not ws_reconnect:
        logger.error(u"PlexPy WebSocket :: Connection unavailable, falling back to polling.")
        plexpy.POLLING_FAILOVER = True
        plexpy.initialize_scheduler()

    logger.debug(u"PlexPy WebSocket :: Leaving thread.")


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
    from plexpy import activity_handler

    if opcode not in opcode_data:
        return False

    try:
        info = json.loads(data)
    except Exception as ex:
        logger.warn(u"PlexPy WebSocket :: Error decoding message from websocket: %s" % ex)
        logger.debug(data)
        return False

    type = info.get('type')

    if not type:
        return False

    if type == 'playing':
        # logger.debug('%s.playing %s' % (name, info))
        try:
            time_line = info.get('_children')
        except:
            logger.debug(u"PlexPy WebSocket :: Session found but unable to get timeline data.")
            return False

        activity = activity_handler.ActivityHandler(timeline=time_line[0])
        activity.process()

    #if type == 'timeline':
    #    try:
    #        time_line = info.get('_children')
    #    except:
    #        logger.debug(u"PlexPy WebSocket :: Timeline event found but unable to get timeline data.")
    #        return False

    #    activity = activity_handler.TimelineHandler(timeline=time_line[0])
    #    activity.process()

    return True
