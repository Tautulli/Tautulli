# -*- coding: utf-8 -*-
import json
import threading

from plexapi import log


class AlertListener(threading.Thread):
    """ Creates a websocket connection to the PlexServer to optionally receive alert notifications.
        These often include messages from Plex about media scans as well as updates to currently running
        Transcode Sessions. This class implements threading.Thread, therefore to start monitoring
        alerts you must call .start() on the object once it's created. When calling
        `PlexServer.startAlertListener()`, the thread will be started for you.

        Known `state`-values for timeline entries, with identifier=`com.plexapp.plugins.library`:

            :0: The item was created
            :1: Reporting progress on item processing
            :2: Matching the item
            :3: Downloading the metadata
            :4: Processing downloaded metadata
            :5: The item processed
            :9: The item deleted

        When metadata agent is not set for the library processing ends with state=1.

        Parameters:
            server (:class:`~plexapi.server.PlexServer`): PlexServer this listener is connected to.
            callback (func): Callback function to call on received messages. The callback function
                will be sent a single argument 'data' which will contain a dictionary of data
                received from the server. :samp:`def my_callback(data): ...`
            callbackError (func): Callback function to call on errors. The callback function
                will be sent a single argument 'error' which will contain the Error object.
                :samp:`def my_callback(error): ...`
    """
    key = '/:/websockets/notifications'

    def __init__(self, server, callback=None, callbackError=None):
        super(AlertListener, self).__init__()
        self.daemon = True
        self._server = server
        self._callback = callback
        self._callbackError = callbackError
        self._ws = None

    def run(self):
        try:
            import websocket
        except ImportError:
            log.warning("Can't use the AlertListener without websocket")
            return
        # create the websocket connection
        url = self._server.url(self.key, includeToken=True).replace('http', 'ws')
        log.info('Starting AlertListener: %s', url)
        self._ws = websocket.WebSocketApp(url, on_message=self._onMessage,
                                          on_error=self._onError)
        self._ws.run_forever()

    def stop(self):
        """ Stop the AlertListener thread. Once the notifier is stopped, it cannot be directly
            started again. You must call :func:`~plexapi.server.PlexServer.startAlertListener`
            from a PlexServer instance.
        """
        log.info('Stopping AlertListener.')
        self._ws.close()

    def _onMessage(self, *args):
        """ Called when websocket message is received.
            In earlier releases, websocket-client returned a tuple of two parameters: a websocket.app.WebSocketApp
            object and the message as a STR. Current releases appear to only return the message.
            We are assuming the last argument in the tuple is the message.
            This is to support compatibility with current and previous releases of websocket-client.
        """
        message = args[-1]
        try:
            data = json.loads(message)['NotificationContainer']
            log.debug('Alert: %s %s %s', *data)
            if self._callback:
                self._callback(data)
        except Exception as err:  # pragma: no cover
            log.error('AlertListener Msg Error: %s', err)

    def _onError(self, *args):  # pragma: no cover
        """ Called when websocket error is received.
            In earlier releases, websocket-client returned a tuple of two parameters: a websocket.app.WebSocketApp
            object and the error. Current releases appear to only return the error.
            We are assuming the last argument in the tuple is the message.
            This is to support compatibility with current and previous releases of websocket-client.
        """
        err = args[-1]
        try:
            log.error('AlertListener Error: %s', err)
            if self._callbackError:
                self._callbackError(err)
        except Exception as err:  # pragma: no cover
            log.error('AlertListener Error: Error: %s', err)
