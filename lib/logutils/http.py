#
# Copyright (C) 2010-2013 Vinay Sajip. See LICENSE.txt for details.
#
import logging

class HTTPHandler(logging.Handler):
    """
    A class which sends records to a Web server, using either GET or
    POST semantics.

    :param host: The Web server to connect to.
    :param url: The URL to use for the connection.
    :param method: The HTTP method to use. GET and POST are supported.
    :param secure: set to True if HTTPS is to be used.
    :param credentials: Set to a username/password tuple if desired. If
                        set, a Basic authentication header is sent. WARNING:
                        if using credentials, make sure `secure` is `True`
                        to avoid sending usernames and passwords in
                        cleartext over the wire.
    """
    def __init__(self, host, url, method="GET", secure=False, credentials=None):
        """
        Initialize an instance.
        """
        logging.Handler.__init__(self)
        method = method.upper()
        if method not in ["GET", "POST"]:
            raise ValueError("method must be GET or POST")
        self.host = host
        self.url = url
        self.method = method
        self.secure = secure
        self.credentials = credentials

    def mapLogRecord(self, record):
        """
        Default implementation of mapping the log record into a dict
        that is sent as the CGI data. Overwrite in your class.
        Contributed by Franz Glasner.
        
        :param record: The record to be mapped.
        """
        return record.__dict__

    def emit(self, record):
        """
        Emit a record.

        Send the record to the Web server as a percent-encoded dictionary

        :param record: The record to be emitted.
        """
        try:
            import http.client, urllib.parse
            host = self.host
            if self.secure:
                h = http.client.HTTPSConnection(host)
            else:
                h = http.client.HTTPConnection(host)
            url = self.url
            data = urllib.parse.urlencode(self.mapLogRecord(record))
            if self.method == "GET":
                if (url.find('?') >= 0):
                    sep = '&'
                else:
                    sep = '?'
                url = url + "%c%s" % (sep, data)
            h.putrequest(self.method, url)
            # support multiple hosts on one IP address...
            # need to strip optional :port from host, if present
            i = host.find(":")
            if i >= 0:
                host = host[:i]
            h.putheader("Host", host)
            if self.method == "POST":
                h.putheader("Content-type",
                            "application/x-www-form-urlencoded")
                h.putheader("Content-length", str(len(data)))
            if self.credentials:
                import base64
                s = ('u%s:%s' % self.credentials).encode('utf-8')
                s = 'Basic ' + base64.b64encode(s).strip()
                h.putheader('Authorization', s)
            h.endheaders(data if self.method == "POST" else None)
            h.getresponse()    #can't do anything with the result
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)

