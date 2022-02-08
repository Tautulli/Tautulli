import socket
import sys

from urllib3 import HTTPSConnectionPool, HTTPConnectionPool, PoolManager, ProxyManager

# Inspired by:
# https://github.com/finbourne/lusid-sdk-python/blob/b813882e4f1777ea78670a03a7596486639e6f40/sdk/lusid/tcp/tcp_keep_alive_probes.py

# The content to send on Mac OS in the TCP Keep Alive probe
TCP_KEEPALIVE = 0x10
# The maximum time to keep the connection idle before sending probes
TCP_KEEP_IDLE = 60
# The interval between probes
TCP_KEEPALIVE_INTERVAL = 60
# The maximum number of failed probes before terminating the connection
TCP_KEEP_CNT = 3


class TCPKeepAliveValidationMethods:
    """
    This class contains a single method whose sole purpose is to set up TCP Keep Alive probes on the socket for a
    connection. This is necessary for long-running requests which will be silently terminated by the AWS Network Load
    Balancer which kills a connection if it is idle for more than 350 seconds.
    """

    @staticmethod
    def adjust_connection_socket(conn, protocol="https"):
        """
        Adjusts the socket settings so that the client sends a TCP keep alive probe over the connection. This is only
        applied where possible, if the ability to set the socket options is not available, for example using Anaconda,
        then the settings will be left as is.
        :param conn: The connection to update the socket settings for
        :param str protocol: The protocol of the connection
        :return: None
        """

        if protocol == "http":
            # It isn't clear how to set this up over HTTP, it seems to differ from HTTPs
            return

        # TCP Keep Alive Probes for different platforms
        platform = sys.platform
        # TCP Keep Alive Probes for Linux
        if (platform == 'linux' and hasattr(conn.sock, "setsockopt") and hasattr(socket, "SO_KEEPALIVE") and
                hasattr(socket, "TCP_KEEPIDLE") and hasattr(socket, "TCP_KEEPINTVL") and hasattr(socket,
                                                                                                 "TCP_KEEPCNT")):
            conn.sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            conn.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, TCP_KEEP_IDLE)
            conn.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, TCP_KEEPALIVE_INTERVAL)
            conn.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, TCP_KEEP_CNT)

        # TCP Keep Alive Probes for Windows OS
        elif platform == 'win32' and hasattr(socket, "SIO_KEEPALIVE_VALS") and getattr(conn.sock, "ioctl",
                                                                                       None) is not None:
            conn.sock.ioctl(socket.SIO_KEEPALIVE_VALS, (1, TCP_KEEP_IDLE * 1000, TCP_KEEPALIVE_INTERVAL * 1000))

        # TCP Keep Alive Probes for Mac OS
        elif platform == 'darwin' and getattr(conn.sock, "setsockopt", None) is not None:
            conn.sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            conn.sock.setsockopt(socket.IPPROTO_TCP, TCP_KEEPALIVE, TCP_KEEPALIVE_INTERVAL)


class TCPKeepAliveHTTPSConnectionPool(HTTPSConnectionPool):
    """
    This class overrides the _validate_conn method in the HTTPSConnectionPool class. This is the entry point to use
    for modifying the socket as it is called after the socket is created and before the request is made.
    """

    def _validate_conn(self, conn):
        """
        Called right before a request is made, after the socket is created.
        """
        # Call the method on the base class
        super(TCPKeepAliveHTTPSConnectionPool, self)._validate_conn(conn)

        # Set up TCP Keep Alive probes, this is the only line added to this function
        TCPKeepAliveValidationMethods.adjust_connection_socket(conn, "https")


class TCPKeepAliveHTTPConnectionPool(HTTPConnectionPool):
    """
    This class overrides the _validate_conn method in the HTTPSConnectionPool class. This is the entry point to use
    for modifying the socket as it is called after the socket is created and before the request is made.
    In the base class this method is passed completely.
    """

    def _validate_conn(self, conn):
        """
        Called right before a request is made, after the socket is created.
        """
        # Call the method on the base class
        super(TCPKeepAliveHTTPConnectionPool, self)._validate_conn(conn)

        # Set up TCP Keep Alive probes, this is the only line added to this function
        TCPKeepAliveValidationMethods.adjust_connection_socket(conn, "http")


class TCPKeepAlivePoolManager(PoolManager):
    """
    This Pool Manager has only had the pool_classes_by_scheme variable changed. This now points at the TCPKeepAlive
    connection pools rather than the default connection pools.
    """

    def __init__(self, num_pools=10, headers=None, **connection_pool_kw):
        super(TCPKeepAlivePoolManager, self).__init__(num_pools=num_pools, headers=headers, **connection_pool_kw)
        self.pool_classes_by_scheme = {"http": TCPKeepAliveHTTPConnectionPool, "https": TCPKeepAliveHTTPSConnectionPool}


class TCPKeepAliveProxyManager(ProxyManager):
    """
    This Proxy Manager has only had the pool_classes_by_scheme variable changed. This now points at the TCPKeepAlive
    connection pools rather than the default connection pools.
    """

    def __init__(self, proxy_url, num_pools=10, headers=None, proxy_headers=None, **connection_pool_kw):
        super(TCPKeepAliveProxyManager, self).__init__(proxy_url=proxy_url, num_pools=num_pools, headers=headers,
                                                       proxy_headers=proxy_headers,
                                                       **connection_pool_kw)
        self.pool_classes_by_scheme = {"http": TCPKeepAliveHTTPConnectionPool, "https": TCPKeepAliveHTTPSConnectionPool}
