import json
import socket

import certifi
from urllib3 import PoolManager
from urllib3.exceptions import HTTPError

from cloudinary.exceptions import GeneralError


class HttpClient:
    DEFAULT_HTTP_TIMEOUT = 60

    def __init__(self, **options):
        # Lazy initialization of the client, to improve performance when HttpClient is initialized but not used
        self._http_client_instance = None
        self.timeout = options.get("timeout", self.DEFAULT_HTTP_TIMEOUT)

    @property
    def _http_client(self):
        if self._http_client_instance is None:
            self._http_client_instance = PoolManager(cert_reqs='CERT_REQUIRED', ca_certs=certifi.where())
        return self._http_client_instance

    def get_json(self, url):
        try:
            response = self._http_client.request("GET", url, timeout=self.timeout)
            body = response.data
        except HTTPError as e:
            raise GeneralError("Unexpected error %s" % str(e))
        except socket.error as e:
            raise GeneralError("Socket Error: %s" % str(e))

        if response.status != 200:
            raise GeneralError("Server returned unexpected status code - {} - {}".format(response.status,
                                                                                         response.data))
        try:
            result = json.loads(body.decode('utf-8'))
        except Exception as e:
            # Error is parsing json
            raise GeneralError("Error parsing server response (%d) - %s. Got - %s" % (response.status, body, e))

        return result
