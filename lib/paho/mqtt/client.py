# Copyright (c) 2012-2019 Roger Light and others
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Eclipse Public License v2.0
# and Eclipse Distribution License v1.0 which accompany this distribution.
#
# The Eclipse Public License is available at
#    http://www.eclipse.org/legal/epl-v20.html
# and the Eclipse Distribution License is available at
#   http://www.eclipse.org/org/documents/edl-v10.php.
#
# Contributors:
#    Roger Light - initial API and implementation
#    Ian Craggs - MQTT V5 support
"""
This is an MQTT client module. MQTT is a lightweight pub/sub messaging
protocol that is easy to implement and suitable for low powered devices.
"""
from __future__ import annotations

import base64
import collections
import errno
import hashlib
import logging
import os
import platform
import select
import socket
import string
import struct
import threading
import time
import urllib.parse
import urllib.request
import uuid
import warnings
from typing import TYPE_CHECKING, Any, Callable, Dict, Iterator, List, NamedTuple, Sequence, Tuple, Union, cast

from paho.mqtt.packettypes import PacketTypes

from .enums import CallbackAPIVersion, ConnackCode, LogLevel, MessageState, MessageType, MQTTErrorCode, MQTTProtocolVersion, PahoClientMode, _ConnectionState
from .matcher import MQTTMatcher
from .properties import Properties
from .reasoncodes import ReasonCode, ReasonCodes
from .subscribeoptions import SubscribeOptions

try:
    from typing import Literal
except ImportError:
    from typing_extensions import Literal  # type: ignore

if TYPE_CHECKING:
    try:
        from typing import TypedDict  # type: ignore
    except ImportError:
        from typing_extensions import TypedDict

    try:
        from typing import Protocol  # type: ignore
    except ImportError:
        from typing_extensions import Protocol  # type: ignore

    class _InPacket(TypedDict):
        command: int
        have_remaining: int
        remaining_count: list[int]
        remaining_mult: int
        remaining_length: int
        packet: bytearray
        to_process: int
        pos: int


    class _OutPacket(TypedDict):
        command: int
        mid: int
        qos: int
        pos: int
        to_process: int
        packet: bytes
        info: MQTTMessageInfo | None

    class SocketLike(Protocol):
        def recv(self, buffer_size: int) -> bytes:
            ...
        def send(self, buffer: bytes) -> int:
            ...
        def close(self) -> None:
            ...
        def fileno(self) -> int:
            ...
        def setblocking(self, flag: bool) -> None:
            ...


try:
    import ssl
except ImportError:
    ssl = None  # type: ignore[assignment]


try:
    import socks  # type: ignore[import-untyped]
except ImportError:
    socks = None  # type: ignore[assignment]


try:
    # Use monotonic clock if available
    time_func = time.monotonic
except AttributeError:
    time_func = time.time

try:
    import dns.resolver

    HAVE_DNS = True
except ImportError:
    HAVE_DNS = False


if platform.system() == 'Windows':
    EAGAIN = errno.WSAEWOULDBLOCK  # type: ignore[attr-defined]
else:
    EAGAIN = errno.EAGAIN

# Avoid linter complain. We kept importing it as ReasonCodes (plural) for compatibility
_ = ReasonCodes

# Keep copy of enums values for compatibility.
CONNECT = MessageType.CONNECT
CONNACK = MessageType.CONNACK
PUBLISH = MessageType.PUBLISH
PUBACK = MessageType.PUBACK
PUBREC = MessageType.PUBREC
PUBREL = MessageType.PUBREL
PUBCOMP = MessageType.PUBCOMP
SUBSCRIBE = MessageType.SUBSCRIBE
SUBACK = MessageType.SUBACK
UNSUBSCRIBE = MessageType.UNSUBSCRIBE
UNSUBACK = MessageType.UNSUBACK
PINGREQ = MessageType.PINGREQ
PINGRESP = MessageType.PINGRESP
DISCONNECT = MessageType.DISCONNECT
AUTH = MessageType.AUTH

# Log levels
MQTT_LOG_INFO = LogLevel.MQTT_LOG_INFO
MQTT_LOG_NOTICE = LogLevel.MQTT_LOG_NOTICE
MQTT_LOG_WARNING = LogLevel.MQTT_LOG_WARNING
MQTT_LOG_ERR = LogLevel.MQTT_LOG_ERR
MQTT_LOG_DEBUG = LogLevel.MQTT_LOG_DEBUG
LOGGING_LEVEL = {
    LogLevel.MQTT_LOG_DEBUG: logging.DEBUG,
    LogLevel.MQTT_LOG_INFO: logging.INFO,
    LogLevel.MQTT_LOG_NOTICE: logging.INFO,  # This has no direct equivalent level
    LogLevel.MQTT_LOG_WARNING: logging.WARNING,
    LogLevel.MQTT_LOG_ERR: logging.ERROR,
}

# CONNACK codes
CONNACK_ACCEPTED = ConnackCode.CONNACK_ACCEPTED
CONNACK_REFUSED_PROTOCOL_VERSION = ConnackCode.CONNACK_REFUSED_PROTOCOL_VERSION
CONNACK_REFUSED_IDENTIFIER_REJECTED = ConnackCode.CONNACK_REFUSED_IDENTIFIER_REJECTED
CONNACK_REFUSED_SERVER_UNAVAILABLE = ConnackCode.CONNACK_REFUSED_SERVER_UNAVAILABLE
CONNACK_REFUSED_BAD_USERNAME_PASSWORD = ConnackCode.CONNACK_REFUSED_BAD_USERNAME_PASSWORD
CONNACK_REFUSED_NOT_AUTHORIZED = ConnackCode.CONNACK_REFUSED_NOT_AUTHORIZED

# Message state
mqtt_ms_invalid = MessageState.MQTT_MS_INVALID
mqtt_ms_publish = MessageState.MQTT_MS_PUBLISH
mqtt_ms_wait_for_puback = MessageState.MQTT_MS_WAIT_FOR_PUBACK
mqtt_ms_wait_for_pubrec = MessageState.MQTT_MS_WAIT_FOR_PUBREC
mqtt_ms_resend_pubrel = MessageState.MQTT_MS_RESEND_PUBREL
mqtt_ms_wait_for_pubrel = MessageState.MQTT_MS_WAIT_FOR_PUBREL
mqtt_ms_resend_pubcomp = MessageState.MQTT_MS_RESEND_PUBCOMP
mqtt_ms_wait_for_pubcomp = MessageState.MQTT_MS_WAIT_FOR_PUBCOMP
mqtt_ms_send_pubrec = MessageState.MQTT_MS_SEND_PUBREC
mqtt_ms_queued = MessageState.MQTT_MS_QUEUED

MQTT_ERR_AGAIN = MQTTErrorCode.MQTT_ERR_AGAIN
MQTT_ERR_SUCCESS = MQTTErrorCode.MQTT_ERR_SUCCESS
MQTT_ERR_NOMEM = MQTTErrorCode.MQTT_ERR_NOMEM
MQTT_ERR_PROTOCOL = MQTTErrorCode.MQTT_ERR_PROTOCOL
MQTT_ERR_INVAL = MQTTErrorCode.MQTT_ERR_INVAL
MQTT_ERR_NO_CONN = MQTTErrorCode.MQTT_ERR_NO_CONN
MQTT_ERR_CONN_REFUSED = MQTTErrorCode.MQTT_ERR_CONN_REFUSED
MQTT_ERR_NOT_FOUND = MQTTErrorCode.MQTT_ERR_NOT_FOUND
MQTT_ERR_CONN_LOST = MQTTErrorCode.MQTT_ERR_CONN_LOST
MQTT_ERR_TLS = MQTTErrorCode.MQTT_ERR_TLS
MQTT_ERR_PAYLOAD_SIZE = MQTTErrorCode.MQTT_ERR_PAYLOAD_SIZE
MQTT_ERR_NOT_SUPPORTED = MQTTErrorCode.MQTT_ERR_NOT_SUPPORTED
MQTT_ERR_AUTH = MQTTErrorCode.MQTT_ERR_AUTH
MQTT_ERR_ACL_DENIED = MQTTErrorCode.MQTT_ERR_ACL_DENIED
MQTT_ERR_UNKNOWN = MQTTErrorCode.MQTT_ERR_UNKNOWN
MQTT_ERR_ERRNO = MQTTErrorCode.MQTT_ERR_ERRNO
MQTT_ERR_QUEUE_SIZE = MQTTErrorCode.MQTT_ERR_QUEUE_SIZE
MQTT_ERR_KEEPALIVE = MQTTErrorCode.MQTT_ERR_KEEPALIVE

MQTTv31 = MQTTProtocolVersion.MQTTv31
MQTTv311 = MQTTProtocolVersion.MQTTv311
MQTTv5 = MQTTProtocolVersion.MQTTv5

MQTT_CLIENT = PahoClientMode.MQTT_CLIENT
MQTT_BRIDGE = PahoClientMode.MQTT_BRIDGE

# For MQTT V5, use the clean start flag only on the first successful connect
MQTT_CLEAN_START_FIRST_ONLY: CleanStartOption = 3

sockpair_data = b"0"

# Payload support all those type and will be converted to bytes:
# * str are utf8 encoded
# * int/float are converted to string and utf8 encoded (e.g. 1 is converted to b"1")
# * None is converted to a zero-length payload (i.e. b"")
PayloadType = Union[str, bytes, bytearray, int, float, None]

HTTPHeader = Dict[str, str]
WebSocketHeaders = Union[Callable[[HTTPHeader], HTTPHeader], HTTPHeader]

CleanStartOption = Union[bool, Literal[3]]


class ConnectFlags(NamedTuple):
    """Contains additional information passed to `on_connect` callback"""

    session_present: bool
    """
    this flag is useful for clients that are
    using clean session set to False only (MQTTv3) or clean_start = False (MQTTv5).
    In that case, if client  that reconnects to a broker that it has previously
    connected to, this flag indicates whether the broker still has the
    session information for the client. If true, the session still exists.
    """


class DisconnectFlags(NamedTuple):
    """Contains additional information passed to `on_disconnect` callback"""

    is_disconnect_packet_from_server: bool
    """
    tells whether this on_disconnect call is the result
    of receiving an DISCONNECT packet from the broker or if the on_disconnect is only
    generated by the client library.
    When true, the reason code is generated by the broker.
    """


CallbackOnConnect_v1_mqtt3 = Callable[["Client", Any, Dict[str, Any], MQTTErrorCode], None]
CallbackOnConnect_v1_mqtt5 = Callable[["Client", Any, Dict[str, Any], ReasonCode, Union[Properties, None]], None]
CallbackOnConnect_v1 = Union[CallbackOnConnect_v1_mqtt5, CallbackOnConnect_v1_mqtt3]
CallbackOnConnect_v2 = Callable[["Client", Any, ConnectFlags, ReasonCode, Union[Properties, None]], None]
CallbackOnConnect = Union[CallbackOnConnect_v1, CallbackOnConnect_v2]
CallbackOnConnectFail = Callable[["Client", Any], None]
CallbackOnDisconnect_v1_mqtt3 = Callable[["Client", Any, MQTTErrorCode], None]
CallbackOnDisconnect_v1_mqtt5 = Callable[["Client", Any, Union[ReasonCode, int, None], Union[Properties, None]], None]
CallbackOnDisconnect_v1 = Union[CallbackOnDisconnect_v1_mqtt3, CallbackOnDisconnect_v1_mqtt5]
CallbackOnDisconnect_v2 = Callable[["Client", Any, DisconnectFlags, ReasonCode, Union[Properties, None]], None]
CallbackOnDisconnect = Union[CallbackOnDisconnect_v1, CallbackOnDisconnect_v2]
CallbackOnLog = Callable[["Client", Any, int, str], None]
CallbackOnMessage = Callable[["Client", Any, "MQTTMessage"], None]
CallbackOnPreConnect = Callable[["Client", Any], None]
CallbackOnPublish_v1 = Callable[["Client", Any, int], None]
CallbackOnPublish_v2 = Callable[["Client", Any, int, ReasonCode, Properties], None]
CallbackOnPublish = Union[CallbackOnPublish_v1, CallbackOnPublish_v2]
CallbackOnSocket = Callable[["Client", Any, "SocketLike"], None]
CallbackOnSubscribe_v1_mqtt3 = Callable[["Client", Any, int, Tuple[int, ...]], None]
CallbackOnSubscribe_v1_mqtt5 = Callable[["Client", Any, int, List[ReasonCode], Properties], None]
CallbackOnSubscribe_v1 = Union[CallbackOnSubscribe_v1_mqtt3, CallbackOnSubscribe_v1_mqtt5]
CallbackOnSubscribe_v2 = Callable[["Client", Any, int, List[ReasonCode], Union[Properties, None]], None]
CallbackOnSubscribe = Union[CallbackOnSubscribe_v1, CallbackOnSubscribe_v2]
CallbackOnUnsubscribe_v1_mqtt3 = Callable[["Client", Any, int], None]
CallbackOnUnsubscribe_v1_mqtt5 = Callable[["Client", Any, int, Properties, Union[ReasonCode, List[ReasonCode]]], None]
CallbackOnUnsubscribe_v1 = Union[CallbackOnUnsubscribe_v1_mqtt3, CallbackOnUnsubscribe_v1_mqtt5]
CallbackOnUnsubscribe_v2 = Callable[["Client", Any, int, List[ReasonCode], Union[Properties, None]], None]
CallbackOnUnsubscribe = Union[CallbackOnUnsubscribe_v1, CallbackOnUnsubscribe_v2]

# This is needed for typing because class Client redefined the name "socket"
_socket = socket


class WebsocketConnectionError(ConnectionError):
    """ WebsocketConnectionError is a subclass of ConnectionError.

        It's raised when unable to perform the Websocket handshake.
    """
    pass


def error_string(mqtt_errno: MQTTErrorCode | int) -> str:
    """Return the error string associated with an mqtt error number."""
    if mqtt_errno == MQTT_ERR_SUCCESS:
        return "No error."
    elif mqtt_errno == MQTT_ERR_NOMEM:
        return "Out of memory."
    elif mqtt_errno == MQTT_ERR_PROTOCOL:
        return "A network protocol error occurred when communicating with the broker."
    elif mqtt_errno == MQTT_ERR_INVAL:
        return "Invalid function arguments provided."
    elif mqtt_errno == MQTT_ERR_NO_CONN:
        return "The client is not currently connected."
    elif mqtt_errno == MQTT_ERR_CONN_REFUSED:
        return "The connection was refused."
    elif mqtt_errno == MQTT_ERR_NOT_FOUND:
        return "Message not found (internal error)."
    elif mqtt_errno == MQTT_ERR_CONN_LOST:
        return "The connection was lost."
    elif mqtt_errno == MQTT_ERR_TLS:
        return "A TLS error occurred."
    elif mqtt_errno == MQTT_ERR_PAYLOAD_SIZE:
        return "Payload too large."
    elif mqtt_errno == MQTT_ERR_NOT_SUPPORTED:
        return "This feature is not supported."
    elif mqtt_errno == MQTT_ERR_AUTH:
        return "Authorisation failed."
    elif mqtt_errno == MQTT_ERR_ACL_DENIED:
        return "Access denied by ACL."
    elif mqtt_errno == MQTT_ERR_UNKNOWN:
        return "Unknown error."
    elif mqtt_errno == MQTT_ERR_ERRNO:
        return "Error defined by errno."
    elif mqtt_errno == MQTT_ERR_QUEUE_SIZE:
        return "Message queue full."
    elif mqtt_errno == MQTT_ERR_KEEPALIVE:
        return "Client or broker did not communicate in the keepalive interval."
    else:
        return "Unknown error."


def connack_string(connack_code: int|ReasonCode) -> str:
    """Return the string associated with a CONNACK result or CONNACK reason code."""
    if isinstance(connack_code, ReasonCode):
        return str(connack_code)

    if connack_code == CONNACK_ACCEPTED:
        return "Connection Accepted."
    elif connack_code == CONNACK_REFUSED_PROTOCOL_VERSION:
        return "Connection Refused: unacceptable protocol version."
    elif connack_code == CONNACK_REFUSED_IDENTIFIER_REJECTED:
        return "Connection Refused: identifier rejected."
    elif connack_code == CONNACK_REFUSED_SERVER_UNAVAILABLE:
        return "Connection Refused: broker unavailable."
    elif connack_code == CONNACK_REFUSED_BAD_USERNAME_PASSWORD:
        return "Connection Refused: bad user name or password."
    elif connack_code == CONNACK_REFUSED_NOT_AUTHORIZED:
        return "Connection Refused: not authorised."
    else:
        return "Connection Refused: unknown reason."


def convert_connack_rc_to_reason_code(connack_code: ConnackCode) -> ReasonCode:
    """Convert a MQTTv3 / MQTTv3.1.1 connack result to `ReasonCode`.

    This is used in `on_connect` callback to have a consistent API.

    Be careful that the numeric value isn't the same, for example:

    >>> ConnackCode.CONNACK_REFUSED_SERVER_UNAVAILABLE == 3
    >>> convert_connack_rc_to_reason_code(ConnackCode.CONNACK_REFUSED_SERVER_UNAVAILABLE) == 136

    It's recommended to compare by names

    >>> code_to_test = ReasonCode(PacketTypes.CONNACK, "Server unavailable")
    >>> convert_connack_rc_to_reason_code(ConnackCode.CONNACK_REFUSED_SERVER_UNAVAILABLE) == code_to_test
    """
    if connack_code == ConnackCode.CONNACK_ACCEPTED:
        return ReasonCode(PacketTypes.CONNACK, "Success")
    if connack_code == ConnackCode.CONNACK_REFUSED_PROTOCOL_VERSION:
        return ReasonCode(PacketTypes.CONNACK, "Unsupported protocol version")
    if connack_code == ConnackCode.CONNACK_REFUSED_IDENTIFIER_REJECTED:
        return ReasonCode(PacketTypes.CONNACK, "Client identifier not valid")
    if connack_code == ConnackCode.CONNACK_REFUSED_SERVER_UNAVAILABLE:
        return ReasonCode(PacketTypes.CONNACK, "Server unavailable")
    if connack_code == ConnackCode.CONNACK_REFUSED_BAD_USERNAME_PASSWORD:
        return ReasonCode(PacketTypes.CONNACK, "Bad user name or password")
    if connack_code == ConnackCode.CONNACK_REFUSED_NOT_AUTHORIZED:
        return ReasonCode(PacketTypes.CONNACK, "Not authorized")

    return ReasonCode(PacketTypes.CONNACK, "Unspecified error")


def convert_disconnect_error_code_to_reason_code(rc: MQTTErrorCode) -> ReasonCode:
    """Convert an MQTTErrorCode to Reason code.

    This is used in `on_disconnect` callback to have a consistent API.

    Be careful that the numeric value isn't the same, for example:

    >>> MQTTErrorCode.MQTT_ERR_PROTOCOL == 2
    >>> convert_disconnect_error_code_to_reason_code(MQTTErrorCode.MQTT_ERR_PROTOCOL) == 130

    It's recommended to compare by names

    >>> code_to_test = ReasonCode(PacketTypes.DISCONNECT, "Protocol error")
    >>> convert_disconnect_error_code_to_reason_code(MQTTErrorCode.MQTT_ERR_PROTOCOL) == code_to_test
    """
    if rc == MQTTErrorCode.MQTT_ERR_SUCCESS:
        return ReasonCode(PacketTypes.DISCONNECT, "Success")
    if rc == MQTTErrorCode.MQTT_ERR_KEEPALIVE:
        return ReasonCode(PacketTypes.DISCONNECT, "Keep alive timeout")
    if rc == MQTTErrorCode.MQTT_ERR_CONN_LOST:
        return ReasonCode(PacketTypes.DISCONNECT, "Unspecified error")
    return ReasonCode(PacketTypes.DISCONNECT, "Unspecified error")


def _base62(
    num: int,
    base: str = string.digits + string.ascii_letters,
    padding: int = 1,
) -> str:
    """Convert a number to base-62 representation."""
    if num < 0:
        raise ValueError("Number must be positive or zero")
    digits = []
    while num:
        num, rest = divmod(num, 62)
        digits.append(base[rest])
    digits.extend(base[0] for _ in range(len(digits), padding))
    return ''.join(reversed(digits))


def topic_matches_sub(sub: str, topic: str) -> bool:
    """Check whether a topic matches a subscription.

    For example:

    * Topic "foo/bar" would match the subscription "foo/#" or "+/bar"
    * Topic "non/matching" would not match the subscription "non/+/+"
    """
    matcher = MQTTMatcher()
    matcher[sub] = True
    try:
        next(matcher.iter_match(topic))
        return True
    except StopIteration:
        return False


def _socketpair_compat() -> tuple[socket.socket, socket.socket]:
    """TCP/IP socketpair including Windows support"""
    listensock = socket.socket(
        socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_IP)
    listensock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listensock.bind(("127.0.0.1", 0))
    listensock.listen(1)

    iface, port = listensock.getsockname()
    sock1 = socket.socket(
        socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_IP)
    sock1.setblocking(False)
    try:
        sock1.connect(("127.0.0.1", port))
    except BlockingIOError:
        pass
    sock2, address = listensock.accept()
    sock2.setblocking(False)
    listensock.close()
    return (sock1, sock2)


def _force_bytes(s: str | bytes) -> bytes:
    if isinstance(s, str):
        return s.encode("utf-8")
    return s


def _encode_payload(payload: str | bytes | bytearray | int | float | None) -> bytes|bytearray:
    if isinstance(payload, str):
        return payload.encode("utf-8")

    if isinstance(payload, (int, float)):
        return str(payload).encode("ascii")

    if payload is None:
        return b""

    if not isinstance(payload, (bytes, bytearray)):
        raise TypeError(
            "payload must be a string, bytearray, int, float or None."
        )

    return payload


class MQTTMessageInfo:
    """This is a class returned from `Client.publish()` and can be used to find
    out the mid of the message that was published, and to determine whether the
    message has been published, and/or wait until it is published.
    """

    __slots__ = 'mid', '_published', '_condition', 'rc', '_iterpos'

    def __init__(self, mid: int):
        self.mid = mid
        """ The message Id (int)"""
        self._published = False
        self._condition = threading.Condition()
        self.rc: MQTTErrorCode = MQTTErrorCode.MQTT_ERR_SUCCESS
        """ The `MQTTErrorCode` that give status for this message.
        This value could change until the message `is_published`"""
        self._iterpos = 0

    def __str__(self) -> str:
        return str((self.rc, self.mid))

    def __iter__(self) -> Iterator[MQTTErrorCode | int]:
        self._iterpos = 0
        return self

    def __next__(self) -> MQTTErrorCode | int:
        return self.next()

    def next(self) -> MQTTErrorCode | int:
        if self._iterpos == 0:
            self._iterpos = 1
            return self.rc
        elif self._iterpos == 1:
            self._iterpos = 2
            return self.mid
        else:
            raise StopIteration

    def __getitem__(self, index: int) -> MQTTErrorCode | int:
        if index == 0:
            return self.rc
        elif index == 1:
            return self.mid
        else:
            raise IndexError("index out of range")

    def _set_as_published(self) -> None:
        with self._condition:
            self._published = True
            self._condition.notify()

    def wait_for_publish(self, timeout: float | None = None) -> None:
        """Block until the message associated with this object is published, or
        until the timeout occurs. If timeout is None, this will never time out.
        Set timeout to a positive number of seconds, e.g. 1.2, to enable the
        timeout.

        :raises ValueError: if the message was not queued due to the outgoing
            queue being full.

        :raises RuntimeError: if the message was not published for another
            reason.
        """
        if self.rc == MQTT_ERR_QUEUE_SIZE:
            raise ValueError('Message is not queued due to ERR_QUEUE_SIZE')
        elif self.rc == MQTT_ERR_AGAIN:
            pass
        elif self.rc > 0:
            raise RuntimeError(f'Message publish failed: {error_string(self.rc)}')

        timeout_time = None if timeout is None else time_func() + timeout
        timeout_tenth = None if timeout is None else timeout / 10.
        def timed_out() -> bool:
            return False if timeout_time is None else time_func() > timeout_time

        with self._condition:
            while not self._published and not timed_out():
                self._condition.wait(timeout_tenth)

        if self.rc > 0:
            raise RuntimeError(f'Message publish failed: {error_string(self.rc)}')

    def is_published(self) -> bool:
        """Returns True if the message associated with this object has been
        published, else returns False.

        To wait for this to become true, look at `wait_for_publish`.
        """
        if self.rc == MQTTErrorCode.MQTT_ERR_QUEUE_SIZE:
            raise ValueError('Message is not queued due to ERR_QUEUE_SIZE')
        elif self.rc == MQTTErrorCode.MQTT_ERR_AGAIN:
            pass
        elif self.rc > 0:
            raise RuntimeError(f'Message publish failed: {error_string(self.rc)}')

        with self._condition:
            return self._published


class MQTTMessage:
    """ This is a class that describes an incoming message. It is
    passed to the `on_message` callback as the message parameter.
    """
    __slots__ = 'timestamp', 'state', 'dup', 'mid', '_topic', 'payload', 'qos', 'retain', 'info', 'properties'

    def __init__(self, mid: int = 0, topic: bytes = b""):
        self.timestamp = 0.0
        self.state = mqtt_ms_invalid
        self.dup = False
        self.mid = mid
        """ The message id (int)."""
        self._topic = topic
        self.payload = b""
        """the message payload (bytes)"""
        self.qos = 0
        """ The message Quality of Service (0, 1 or 2)."""
        self.retain = False
        """ If true, the message is a retained message and not fresh."""
        self.info = MQTTMessageInfo(mid)
        self.properties: Properties | None = None
        """ In MQTT v5.0, the properties associated with the message. (`Properties`)"""

    def __eq__(self, other: object) -> bool:
        """Override the default Equals behavior"""
        if isinstance(other, self.__class__):
            return self.mid == other.mid
        return False

    def __ne__(self, other: object) -> bool:
        """Define a non-equality test"""
        return not self.__eq__(other)

    @property
    def topic(self) -> str:
        """topic that the message was published on.

        This property is read-only.
        """
        return self._topic.decode('utf-8')

    @topic.setter
    def topic(self, value: bytes) -> None:
        self._topic = value


class Client:
    """MQTT version 3.1/3.1.1/5.0 client class.

    This is the main class for use communicating with an MQTT broker.

    General usage flow:

    * Use `connect()`, `connect_async()` or `connect_srv()` to connect to a broker
    * Use `loop_start()` to set a thread running to call `loop()` for you.
    * Or use `loop_forever()` to handle calling `loop()` for you in a blocking function.
    * Or call `loop()` frequently to maintain network traffic flow with the broker
    * Use `subscribe()` to subscribe to a topic and receive messages
    * Use `publish()` to send messages
    * Use `disconnect()` to disconnect from the broker

    Data returned from the broker is made available with the use of callback
    functions as described below.

    :param CallbackAPIVersion callback_api_version: define the API version for user-callback (on_connect, on_publish,...).
        This field is required and it's recommended to use the latest version (CallbackAPIVersion.API_VERSION2).
        See each callback for description of API for each version. The file docs/migrations.rst contains details on
        how to migrate between version.

    :param str client_id: the unique client id string used when connecting to the
        broker. If client_id is zero length or None, then the behaviour is
        defined by which protocol version is in use. If using MQTT v3.1.1, then
        a zero length client id will be sent to the broker and the broker will
        generate a random for the client. If using MQTT v3.1 then an id will be
        randomly generated. In both cases, clean_session must be True. If this
        is not the case a ValueError will be raised.

    :param bool clean_session: a boolean that determines the client type. If True,
        the broker will remove all information about this client when it
        disconnects. If False, the client is a persistent client and
        subscription information and queued messages will be retained when the
        client disconnects.
        Note that a client will never discard its own outgoing messages on
        disconnect. Calling connect() or reconnect() will cause the messages to
        be resent.  Use reinitialise() to reset a client to its original state.
        The clean_session argument only applies to MQTT versions v3.1.1 and v3.1.
        It is not accepted if the MQTT version is v5.0 - use the clean_start
        argument on connect() instead.

    :param userdata: user defined data of any type that is passed as the "userdata"
        parameter to callbacks. It may be updated at a later point with the
        user_data_set() function.

    :param int protocol: allows explicit setting of the MQTT version to
        use for this client. Can be paho.mqtt.client.MQTTv311 (v3.1.1),
        paho.mqtt.client.MQTTv31 (v3.1) or paho.mqtt.client.MQTTv5 (v5.0),
        with the default being v3.1.1.

    :param transport: use "websockets" to use WebSockets as the transport
        mechanism. Set to "tcp" to use raw TCP, which is the default.
        Use "unix" to use Unix sockets as the transport mechanism; note that
        this option is only available on platforms that support Unix sockets,
        and the "host" argument is interpreted as the path to the Unix socket
        file in this case.

    :param bool manual_ack: normally, when a message is received, the library automatically
        acknowledges after on_message callback returns.  manual_ack=True allows the application to
        acknowledge receipt after it has completed processing of a message
        using a the ack() method. This addresses vulnerability to message loss
        if applications fails while processing a message, or while it pending
        locally.

    Callbacks
    =========

    A number of callback functions are available to receive data back from the
    broker. To use a callback, define a function and then assign it to the
    client::

        def on_connect(client, userdata, flags, reason_code, properties):
            print(f"Connected with result code {reason_code}")

        client.on_connect = on_connect

    Callbacks can also be attached using decorators::

        mqttc = paho.mqtt.Client()

        @mqttc.connect_callback()
        def on_connect(client, userdata, flags, reason_code, properties):
            print(f"Connected with result code {reason_code}")

    All of the callbacks as described below have a "client" and an "userdata"
    argument. "client" is the `Client` instance that is calling the callback.
    userdata" is user data of any type and can be set when creating a new client
    instance or with `user_data_set()`.

    If you wish to suppress exceptions within a callback, you should set
    ``mqttc.suppress_exceptions = True``

    The callbacks are listed below, documentation for each of them can be found
    at the same function name:

    `on_connect`, `on_connect_fail`, `on_disconnect`, `on_message`, `on_publish`,
    `on_subscribe`, `on_unsubscribe`, `on_log`, `on_socket_open`, `on_socket_close`,
    `on_socket_register_write`, `on_socket_unregister_write`
    """

    def __init__(
        self,
        callback_api_version: CallbackAPIVersion = CallbackAPIVersion.VERSION1,
        client_id: str | None = "",
        clean_session: bool | None = None,
        userdata: Any = None,
        protocol: MQTTProtocolVersion = MQTTv311,
        transport: Literal["tcp", "websockets", "unix"] = "tcp",
        reconnect_on_failure: bool = True,
        manual_ack: bool = False,
    ) -> None:
        transport = transport.lower()  # type: ignore
        if transport == "unix" and not hasattr(socket, "AF_UNIX"):
            raise ValueError('"unix" transport not supported')
        elif transport not in ("websockets", "tcp", "unix"):
            raise ValueError(
                f'transport must be "websockets", "tcp" or "unix", not {transport}')

        self._manual_ack = manual_ack
        self._transport = transport
        self._protocol = protocol
        self._userdata = userdata
        self._sock: SocketLike | None = None
        self._sockpairR: socket.socket | None = None
        self._sockpairW: socket.socket | None = None
        self._keepalive = 60
        self._connect_timeout = 5.0
        self._client_mode = MQTT_CLIENT
        self._callback_api_version = callback_api_version

        if self._callback_api_version == CallbackAPIVersion.VERSION1:
            warnings.warn(
                "Callback API version 1 is deprecated, update to latest version",
                category=DeprecationWarning,
                stacklevel=2,
            )
        if isinstance(self._callback_api_version, str):
            # Help user to migrate, it probably provided a client id
            # as first arguments
            raise ValueError(
                "Unsupported callback API version: version 2.0 added a callback_api_version, see docs/migrations.rst for details"
            )
        if self._callback_api_version not in CallbackAPIVersion:
            raise ValueError("Unsupported callback API version")

        self._clean_start: int = MQTT_CLEAN_START_FIRST_ONLY

        if protocol == MQTTv5:
            if clean_session is not None:
                raise ValueError('Clean session is not used for MQTT 5.0')
        else:
            if clean_session is None:
                clean_session = True
            if not clean_session and (client_id == "" or client_id is None):
                raise ValueError(
                    'A client id must be provided if clean session is False.')
            self._clean_session = clean_session

        # [MQTT-3.1.3-4] Client Id must be UTF-8 encoded string.
        if client_id == "" or client_id is None:
            if protocol == MQTTv31:
                self._client_id = _base62(uuid.uuid4().int, padding=22).encode("utf8")
            else:
                self._client_id = b""
        else:
            self._client_id = _force_bytes(client_id)

        self._username: bytes | None = None
        self._password: bytes | None = None
        self._in_packet: _InPacket = {
            "command": 0,
            "have_remaining": 0,
            "remaining_count": [],
            "remaining_mult": 1,
            "remaining_length": 0,
            "packet": bytearray(b""),
            "to_process": 0,
            "pos": 0,
        }
        self._out_packet: collections.deque[_OutPacket] = collections.deque()
        self._last_msg_in = time_func()
        self._last_msg_out = time_func()
        self._reconnect_min_delay = 1
        self._reconnect_max_delay = 120
        self._reconnect_delay: int | None = None
        self._reconnect_on_failure = reconnect_on_failure
        self._ping_t = 0.0
        self._last_mid = 0
        self._state = _ConnectionState.MQTT_CS_NEW
        self._out_messages: collections.OrderedDict[
            int, MQTTMessage
        ] = collections.OrderedDict()
        self._in_messages: collections.OrderedDict[
            int, MQTTMessage
        ] = collections.OrderedDict()
        self._max_inflight_messages = 20
        self._inflight_messages = 0
        self._max_queued_messages = 0
        self._connect_properties: Properties | None = None
        self._will_properties: Properties | None = None
        self._will = False
        self._will_topic = b""
        self._will_payload = b""
        self._will_qos = 0
        self._will_retain = False
        self._on_message_filtered = MQTTMatcher()
        self._host = ""
        self._port = 1883
        self._bind_address = ""
        self._bind_port = 0
        self._proxy: Any = {}
        self._in_callback_mutex = threading.Lock()
        self._callback_mutex = threading.RLock()
        self._msgtime_mutex = threading.Lock()
        self._out_message_mutex = threading.RLock()
        self._in_message_mutex = threading.Lock()
        self._reconnect_delay_mutex = threading.Lock()
        self._mid_generate_mutex = threading.Lock()
        self._thread: threading.Thread | None = None
        self._thread_terminate = False
        self._ssl = False
        self._ssl_context: ssl.SSLContext | None = None
        # Only used when SSL context does not have check_hostname attribute
        self._tls_insecure = False
        self._logger: logging.Logger | None = None
        self._registered_write = False
        # No default callbacks
        self._on_log: CallbackOnLog | None = None
        self._on_pre_connect: CallbackOnPreConnect | None = None
        self._on_connect: CallbackOnConnect | None = None
        self._on_connect_fail: CallbackOnConnectFail | None = None
        self._on_subscribe: CallbackOnSubscribe | None = None
        self._on_message: CallbackOnMessage | None = None
        self._on_publish: CallbackOnPublish | None = None
        self._on_unsubscribe: CallbackOnUnsubscribe | None = None
        self._on_disconnect: CallbackOnDisconnect | None = None
        self._on_socket_open: CallbackOnSocket | None = None
        self._on_socket_close: CallbackOnSocket | None = None
        self._on_socket_register_write: CallbackOnSocket | None = None
        self._on_socket_unregister_write: CallbackOnSocket | None = None
        self._websocket_path = "/mqtt"
        self._websocket_extra_headers: WebSocketHeaders | None = None
        # for clean_start == MQTT_CLEAN_START_FIRST_ONLY
        self._mqttv5_first_connect = True
        self.suppress_exceptions = False # For callbacks

    def __del__(self) -> None:
        self._reset_sockets()

    @property
    def host(self) -> str:
        """
        Host to connect to. If `connect()` hasn't been called yet, returns an empty string.

        This property may not be changed if the connection is already open.
        """
        return self._host

    @host.setter
    def host(self, value: str) -> None:
        if not self._connection_closed():
            raise RuntimeError("updating host on established connection is not supported")

        if not value:
            raise ValueError("Invalid host.")
        self._host = value

    @property
    def port(self) -> int:
        """
        Broker TCP port to connect to.

        This property may not be changed if the connection is already open.
        """
        return self._port

    @port.setter
    def port(self, value: int) -> None:
        if not self._connection_closed():
            raise RuntimeError("updating port on established connection is not supported")

        if value <= 0:
            raise ValueError("Invalid port number.")
        self._port = value

    @property
    def keepalive(self) -> int:
        """
        Client keepalive interval (in seconds).

        This property may not be changed if the connection is already open.
        """
        return self._keepalive

    @keepalive.setter
    def keepalive(self, value: int) -> None:
        if not self._connection_closed():
            # The issue here is that the previous value of keepalive matter to possibly
            # sent ping packet.
            raise RuntimeError("updating keepalive on established connection is not supported")

        if value < 0:
            raise ValueError("Keepalive must be >=0.")

        self._keepalive = value

    @property
    def transport(self) -> Literal["tcp", "websockets", "unix"]:
        """
        Transport method used for the connection ("tcp" or "websockets").

        This property may not be changed if the connection is already open.
        """
        return self._transport

    @transport.setter
    def transport(self, value: Literal["tcp", "websockets"]) -> None:
        if not self._connection_closed():
            raise RuntimeError("updating transport on established connection is not supported")

        self._transport = value

    @property
    def protocol(self) -> MQTTProtocolVersion:
        """
        Protocol version used (MQTT v3, MQTT v3.11, MQTTv5)

        This property is read-only.
        """
        return self._protocol

    @property
    def connect_timeout(self) -> float:
        """
        Connection establishment timeout in seconds.

        This property may not be changed if the connection is already open.
        """
        return self._connect_timeout

    @connect_timeout.setter
    def connect_timeout(self, value: float) -> None:
        if not self._connection_closed():
            raise RuntimeError("updating connect_timeout on established connection is not supported")

        if value <= 0.0:
            raise ValueError("timeout must be a positive number")

        self._connect_timeout = value

    @property
    def username(self) -> str | None:
        """The username used to connect to the MQTT broker, or None if no username is used.

        This property may not be changed if the connection is already open.
        """
        if self._username is None:
            return None
        return self._username.decode("utf-8")

    @username.setter
    def username(self, value: str | None) -> None:
        if not self._connection_closed():
            raise RuntimeError("updating username on established connection is not supported")

        if value is None:
            self._username = None
        else:
            self._username = value.encode("utf-8")

    @property
    def password(self) -> str | None:
        """The password used to connect to the MQTT broker, or None if no password is used.

        This property may not be changed if the connection is already open.
        """
        if self._password is None:
            return None
        return self._password.decode("utf-8")

    @password.setter
    def password(self, value: str | None) -> None:
        if not self._connection_closed():
            raise RuntimeError("updating password on established connection is not supported")

        if value is None:
            self._password = None
        else:
            self._password = value.encode("utf-8")

    @property
    def max_inflight_messages(self) -> int:
        """
        Maximum number of messages with QoS > 0 that can be partway through the network flow at once

        This property may not be changed if the connection is already open.
        """
        return self._max_inflight_messages

    @max_inflight_messages.setter
    def max_inflight_messages(self, value: int) -> None:
        if not self._connection_closed():
            # Not tested. Some doubt that everything is okay when max_inflight change between 0
            # and > 0 value because _update_inflight is skipped when _max_inflight_messages == 0
            raise RuntimeError("updating max_inflight_messages on established connection is not supported")

        if value < 0:
            raise ValueError("Invalid inflight.")

        self._max_inflight_messages = value

    @property
    def max_queued_messages(self) -> int:
        """
        Maximum number of message in the outgoing message queue, 0 means unlimited

        This property may not be changed if the connection is already open.
        """
        return self._max_queued_messages

    @max_queued_messages.setter
    def max_queued_messages(self, value: int) -> None:
        if not self._connection_closed():
            # Not tested.
            raise RuntimeError("updating max_queued_messages on established connection is not supported")

        if value < 0:
            raise ValueError("Invalid queue size.")

        self._max_queued_messages = value

    @property
    def will_topic(self) -> str | None:
        """
        The topic name a will message is sent to when disconnecting unexpectedly. None if a will shall not be sent.

        This property is read-only. Use `will_set()` to change its value.
        """
        if self._will_topic is None:
            return None

        return self._will_topic.decode("utf-8")

    @property
    def will_payload(self) -> bytes | None:
        """
        The payload for the will message that is sent when disconnecting unexpectedly. None if a will shall not be sent.

        This property is read-only. Use `will_set()` to change its value.
        """
        return self._will_payload

    @property
    def logger(self) -> logging.Logger | None:
        return self._logger

    @logger.setter
    def logger(self, value: logging.Logger | None) -> None:
        self._logger = value

    def _sock_recv(self, bufsize: int) -> bytes:
        if self._sock is None:
            raise ConnectionError("self._sock is None")
        try:
            return self._sock.recv(bufsize)
        except ssl.SSLWantReadError as err:
            raise BlockingIOError() from err
        except ssl.SSLWantWriteError as err:
            self._call_socket_register_write()
            raise BlockingIOError() from err
        except AttributeError as err:
            self._easy_log(
                MQTT_LOG_DEBUG, "socket was None: %s", err)
            raise ConnectionError() from err

    def _sock_send(self, buf: bytes) -> int:
        if self._sock is None:
            raise ConnectionError("self._sock is None")

        try:
            return self._sock.send(buf)
        except ssl.SSLWantReadError as err:
            raise BlockingIOError() from err
        except ssl.SSLWantWriteError as err:
            self._call_socket_register_write()
            raise BlockingIOError() from err
        except BlockingIOError as err:
            self._call_socket_register_write()
            raise BlockingIOError() from err

    def _sock_close(self) -> None:
        """Close the connection to the server."""
        if not self._sock:
            return

        try:
            sock = self._sock
            self._sock = None
            self._call_socket_unregister_write(sock)
            self._call_socket_close(sock)
        finally:
            # In case a callback fails, still close the socket to avoid leaking the file descriptor.
            sock.close()

    def _reset_sockets(self, sockpair_only: bool = False) -> None:
        if not sockpair_only:
            self._sock_close()

        if self._sockpairR:
            self._sockpairR.close()
            self._sockpairR = None
        if self._sockpairW:
            self._sockpairW.close()
            self._sockpairW = None

    def reinitialise(
        self,
        client_id: str = "",
        clean_session: bool = True,
        userdata: Any = None,
    ) -> None:
        self._reset_sockets()

        self.__init__(client_id, clean_session, userdata)  # type: ignore[misc]

    def ws_set_options(
        self,
        path: str = "/mqtt",
        headers: WebSocketHeaders | None = None,
    ) -> None:
        """ Set the path and headers for a websocket connection

        :param str path: a string starting with / which should be the endpoint of the
            mqtt connection on the remote server

        :param headers:  can be either a dict or a callable object. If it is a dict then
            the extra items in the dict are added to the websocket headers. If it is
            a callable, then the default websocket headers are passed into this
            function and the result is used as the new headers.
        """
        self._websocket_path = path

        if headers is not None:
            if isinstance(headers, dict) or callable(headers):
                self._websocket_extra_headers = headers
            else:
                raise ValueError(
                    "'headers' option to ws_set_options has to be either a dictionary or callable")

    def tls_set_context(
        self,
        context: ssl.SSLContext | None = None,
    ) -> None:
        """Configure network encryption and authentication context. Enables SSL/TLS support.

        :param context: an ssl.SSLContext object. By default this is given by
            ``ssl.create_default_context()``, if available.

        Must be called before `connect()`, `connect_async()` or `connect_srv()`."""
        if self._ssl_context is not None:
            raise ValueError('SSL/TLS has already been configured.')

        if context is None:
            context = ssl.create_default_context()

        self._ssl = True
        self._ssl_context = context

        # Ensure _tls_insecure is consistent with check_hostname attribute
        if hasattr(context, 'check_hostname'):
            self._tls_insecure = not context.check_hostname

    def tls_set(
        self,
        ca_certs: str | None = None,
        certfile: str | None = None,
        keyfile: str | None = None,
        cert_reqs: ssl.VerifyMode | None = None,
        tls_version: int | None = None,
        ciphers: str | None = None,
        keyfile_password: str | None = None,
        alpn_protocols: list[str] | None = None,
    ) -> None:
        """Configure network encryption and authentication options. Enables SSL/TLS support.

        :param str ca_certs: a string path to the Certificate Authority certificate files
            that are to be treated as trusted by this client. If this is the only
            option given then the client will operate in a similar manner to a web
            browser. That is to say it will require the broker to have a
            certificate signed by the Certificate Authorities in ca_certs and will
            communicate using TLS v1,2, but will not attempt any form of
            authentication. This provides basic network encryption but may not be
            sufficient depending on how the broker is configured.

            By default, on Python 2.7.9+ or 3.4+, the default certification
            authority of the system is used. On older Python version this parameter
            is mandatory.
        :param str certfile: PEM encoded client certificate filename. Used with
            keyfile for client TLS based authentication. Support for this feature is
            broker dependent. Note that if the files in encrypted and needs a password to
            decrypt it, then this can be passed using the keyfile_password argument - you
            should take precautions to ensure that your password is
            not hard coded into your program by loading the password from a file
            for example. If you do not provide keyfile_password, the password will
            be requested to be typed in at a terminal window.
        :param str keyfile: PEM encoded client private keys filename. Used with
            certfile for client TLS based authentication. Support for this feature is
            broker dependent. Note that if the files in encrypted and needs a password to
            decrypt it, then this can be passed using the keyfile_password argument - you
            should take precautions to ensure that your password is
            not hard coded into your program by loading the password from a file
            for example. If you do not provide keyfile_password, the password will
            be requested to be typed in at a terminal window.
        :param cert_reqs: the certificate requirements that the client imposes
            on the broker to be changed. By default this is ssl.CERT_REQUIRED,
            which means that the broker must provide a certificate. See the ssl
            pydoc for more information on this parameter.
        :param tls_version: the version of the SSL/TLS protocol used to be
            specified. By default TLS v1.2 is used. Previous versions are allowed
            but not recommended due to possible security problems.
        :param str ciphers: encryption ciphers that are allowed
            for this connection, or None to use the defaults. See the ssl pydoc for
            more information.

        Must be called before `connect()`, `connect_async()` or `connect_srv()`."""
        if ssl is None:
            raise ValueError('This platform has no SSL/TLS.')

        if not hasattr(ssl, 'SSLContext'):
            # Require Python version that has SSL context support in standard library
            raise ValueError(
                'Python 2.7.9 and 3.2 are the minimum supported versions for TLS.')

        if ca_certs is None and not hasattr(ssl.SSLContext, 'load_default_certs'):
            raise ValueError('ca_certs must not be None.')

        # Create SSLContext object
        if tls_version is None:
            tls_version = ssl.PROTOCOL_TLSv1_2
            # If the python version supports it, use highest TLS version automatically
            if hasattr(ssl, "PROTOCOL_TLS_CLIENT"):
                # This also enables CERT_REQUIRED and check_hostname by default.
                tls_version = ssl.PROTOCOL_TLS_CLIENT
            elif hasattr(ssl, "PROTOCOL_TLS"):
                tls_version = ssl.PROTOCOL_TLS
        context = ssl.SSLContext(tls_version)

        # Configure context
        if ciphers is not None:
            context.set_ciphers(ciphers)

        if certfile is not None:
            context.load_cert_chain(certfile, keyfile, keyfile_password)

        if cert_reqs == ssl.CERT_NONE and hasattr(context, 'check_hostname'):
            context.check_hostname = False

        context.verify_mode = ssl.CERT_REQUIRED if cert_reqs is None else cert_reqs

        if ca_certs is not None:
            context.load_verify_locations(ca_certs)
        else:
            context.load_default_certs()

        if alpn_protocols is not None:
            if not getattr(ssl, "HAS_ALPN", None):
                raise ValueError("SSL library has no support for ALPN")
            context.set_alpn_protocols(alpn_protocols)

        self.tls_set_context(context)

        if cert_reqs != ssl.CERT_NONE:
            # Default to secure, sets context.check_hostname attribute
            # if available
            self.tls_insecure_set(False)
        else:
            # But with ssl.CERT_NONE, we can not check_hostname
            self.tls_insecure_set(True)

    def tls_insecure_set(self, value: bool) -> None:
        """Configure verification of the server hostname in the server certificate.

        If value is set to true, it is impossible to guarantee that the host
        you are connecting to is not impersonating your server. This can be
        useful in initial server testing, but makes it possible for a malicious
        third party to impersonate your server through DNS spoofing, for
        example.

        Do not use this function in a real system. Setting value to true means
        there is no point using encryption.

        Must be called before `connect()` and after either `tls_set()` or
        `tls_set_context()`."""

        if self._ssl_context is None:
            raise ValueError(
                'Must configure SSL context before using tls_insecure_set.')

        self._tls_insecure = value

        # Ensure check_hostname is consistent with _tls_insecure attribute
        if hasattr(self._ssl_context, 'check_hostname'):
            # Rely on SSLContext to check host name
            # If verify_mode is CERT_NONE then the host name will never be checked
            self._ssl_context.check_hostname = not value

    def proxy_set(self, **proxy_args: Any) -> None:
        """Configure proxying of MQTT connection. Enables support for SOCKS or
        HTTP proxies.

        Proxying is done through the PySocks library. Brief descriptions of the
        proxy_args parameters are below; see the PySocks docs for more info.

        (Required)

        :param proxy_type: One of {socks.HTTP, socks.SOCKS4, or socks.SOCKS5}
        :param proxy_addr: IP address or DNS name of proxy server

        (Optional)

        :param proxy_port: (int) port number of the proxy server. If not provided,
            the PySocks package default value will be utilized, which differs by proxy_type.
        :param proxy_rdns: boolean indicating whether proxy lookup should be performed
            remotely (True, default) or locally (False)
        :param proxy_username: username for SOCKS5 proxy, or userid for SOCKS4 proxy
        :param proxy_password: password for SOCKS5 proxy

        Example::

            mqttc.proxy_set(proxy_type=socks.HTTP, proxy_addr='1.2.3.4', proxy_port=4231)
        """
        if socks is None:
            raise ValueError("PySocks must be installed for proxy support.")
        elif not self._proxy_is_valid(proxy_args):
            raise ValueError("proxy_type and/or proxy_addr are invalid.")
        else:
            self._proxy = proxy_args

    def enable_logger(self, logger: logging.Logger | None = None) -> None:
        """
        Enables a logger to send log messages to

        :param logging.Logger logger: if specified, that ``logging.Logger`` object will be used, otherwise
            one will be created automatically.

        See `disable_logger` to undo this action.
        """
        if logger is None:
            if self._logger is not None:
                # Do not replace existing logger
                return
            logger = logging.getLogger(__name__)
        self.logger = logger

    def disable_logger(self) -> None:
        """
        Disable logging using standard python logging package. This has no effect on the `on_log` callback.
        """
        self._logger = None

    def connect(
        self,
        host: str,
        port: int = 1883,
        keepalive: int = 60,
        bind_address: str = "",
        bind_port: int = 0,
        clean_start: CleanStartOption = MQTT_CLEAN_START_FIRST_ONLY,
        properties: Properties | None = None,
    ) -> MQTTErrorCode:
        """Connect to a remote broker. This is a blocking call that establishes
        the underlying connection and transmits a CONNECT packet.
        Note that the connection status will not be updated until a CONNACK is received and
        processed (this requires a running network loop, see `loop_start`, `loop_forever`, `loop`...).

        :param str host: the hostname or IP address of the remote broker.
        :param int port: the network port of the server host to connect to. Defaults to
            1883. Note that the default port for MQTT over SSL/TLS is 8883 so if you
            are using `tls_set()` the port may need providing.
        :param int keepalive: Maximum period in seconds between communications with the
            broker. If no other messages are being exchanged, this controls the
            rate at which the client will send ping messages to the broker.
        :param bool clean_start: (MQTT v5.0 only) True, False or MQTT_CLEAN_START_FIRST_ONLY.
            Sets the MQTT v5.0 clean_start flag always, never or on the first successful connect only,
            respectively.  MQTT session data (such as outstanding messages and subscriptions)
            is cleared on successful connect when the clean_start flag is set.
            For MQTT v3.1.1, the ``clean_session`` argument of `Client` should be used for similar
            result.
        :param Properties properties: (MQTT v5.0 only) the MQTT v5.0 properties to be sent in the
            MQTT connect packet.
        """

        if self._protocol == MQTTv5:
            self._mqttv5_first_connect = True
        else:
            if clean_start != MQTT_CLEAN_START_FIRST_ONLY:
                raise ValueError("Clean start only applies to MQTT V5")
            if properties:
                raise ValueError("Properties only apply to MQTT V5")

        self.connect_async(host, port, keepalive,
                           bind_address, bind_port, clean_start, properties)
        return self.reconnect()

    def connect_srv(
        self,
        domain: str | None = None,
        keepalive: int = 60,
        bind_address: str = "",
        bind_port: int = 0,
        clean_start: CleanStartOption = MQTT_CLEAN_START_FIRST_ONLY,
        properties: Properties | None = None,
    ) -> MQTTErrorCode:
        """Connect to a remote broker.

        :param str domain: the DNS domain to search for SRV records; if None,
            try to determine local domain name.
        :param keepalive, bind_address, clean_start and properties: see `connect()`
        """

        if HAVE_DNS is False:
            raise ValueError(
                'No DNS resolver library found, try "pip install dnspython".')

        if domain is None:
            domain = socket.getfqdn()
            domain = domain[domain.find('.') + 1:]

        try:
            rr = f'_mqtt._tcp.{domain}'
            if self._ssl:
                # IANA specifies secure-mqtt (not mqtts) for port 8883
                rr = f'_secure-mqtt._tcp.{domain}'
            answers = []
            for answer in dns.resolver.query(rr, dns.rdatatype.SRV):
                addr = answer.target.to_text()[:-1]
                answers.append(
                    (addr, answer.port, answer.priority, answer.weight))
        except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.resolver.NoNameservers) as err:
            raise ValueError(f"No answer/NXDOMAIN for SRV in {domain}") from err

        # FIXME: doesn't account for weight
        for answer in answers:
            host, port, prio, weight = answer

            try:
                return self.connect(host, port, keepalive, bind_address, bind_port, clean_start, properties)
            except Exception:  # noqa: S110
                pass

        raise ValueError("No SRV hosts responded")

    def connect_async(
        self,
        host: str,
        port: int = 1883,
        keepalive: int = 60,
        bind_address: str = "",
        bind_port: int = 0,
        clean_start: CleanStartOption = MQTT_CLEAN_START_FIRST_ONLY,
        properties: Properties | None = None,
    ) -> None:
        """Connect to a remote broker asynchronously. This is a non-blocking
        connect call that can be used with `loop_start()` to provide very quick
        start.

        Any already established connection will be terminated immediately.

        :param str host: the hostname or IP address of the remote broker.
        :param int port: the network port of the server host to connect to. Defaults to
            1883. Note that the default port for MQTT over SSL/TLS is 8883 so if you
            are using `tls_set()` the port may need providing.
        :param int keepalive: Maximum period in seconds between communications with the
            broker. If no other messages are being exchanged, this controls the
            rate at which the client will send ping messages to the broker.
        :param bool clean_start: (MQTT v5.0 only) True, False or MQTT_CLEAN_START_FIRST_ONLY.
            Sets the MQTT v5.0 clean_start flag always, never or on the first successful connect only,
            respectively.  MQTT session data (such as outstanding messages and subscriptions)
            is cleared on successful connect when the clean_start flag is set.
            For MQTT v3.1.1, the ``clean_session`` argument of `Client` should be used for similar
            result.
        :param Properties properties: (MQTT v5.0 only) the MQTT v5.0 properties to be sent in the
            MQTT connect packet.
        """
        if bind_port < 0:
            raise ValueError('Invalid bind port number.')

        # Switch to state NEW to allow update of host, port & co.
        self._sock_close()
        self._state = _ConnectionState.MQTT_CS_NEW

        self.host = host
        self.port = port
        self.keepalive = keepalive
        self._bind_address = bind_address
        self._bind_port = bind_port
        self._clean_start = clean_start
        self._connect_properties = properties
        self._state = _ConnectionState.MQTT_CS_CONNECT_ASYNC

    def reconnect_delay_set(self, min_delay: int = 1, max_delay: int = 120) -> None:
        """ Configure the exponential reconnect delay

            When connection is lost, wait initially min_delay seconds and
            double this time every attempt. The wait is capped at max_delay.
            Once the client is fully connected (e.g. not only TCP socket, but
            received a success CONNACK), the wait timer is reset to min_delay.
        """
        with self._reconnect_delay_mutex:
            self._reconnect_min_delay = min_delay
            self._reconnect_max_delay = max_delay
            self._reconnect_delay = None

    def reconnect(self) -> MQTTErrorCode:
        """Reconnect the client after a disconnect. Can only be called after
        connect()/connect_async()."""
        if len(self._host) == 0:
            raise ValueError('Invalid host.')
        if self._port <= 0:
            raise ValueError('Invalid port number.')

        self._in_packet = {
            "command": 0,
            "have_remaining": 0,
            "remaining_count": [],
            "remaining_mult": 1,
            "remaining_length": 0,
            "packet": bytearray(b""),
            "to_process": 0,
            "pos": 0,
        }

        self._ping_t = 0.0
        self._state = _ConnectionState.MQTT_CS_CONNECTING

        self._sock_close()

        # Mark all currently outgoing QoS = 0 packets as lost,
        # or `wait_for_publish()` could hang forever
        for pkt in self._out_packet:
            if pkt["command"] & 0xF0 == PUBLISH and pkt["qos"] == 0 and pkt["info"] is not None:
                pkt["info"].rc = MQTT_ERR_CONN_LOST
                pkt["info"]._set_as_published()

        self._out_packet.clear()

        with self._msgtime_mutex:
            self._last_msg_in = time_func()
            self._last_msg_out = time_func()

        # Put messages in progress in a valid state.
        self._messages_reconnect_reset()

        with self._callback_mutex:
            on_pre_connect = self.on_pre_connect

        if on_pre_connect:
            try:
                on_pre_connect(self, self._userdata)
            except Exception as err:
                self._easy_log(
                    MQTT_LOG_ERR, 'Caught exception in on_pre_connect: %s', err)
                if not self.suppress_exceptions:
                    raise

        self._sock = self._create_socket()

        self._sock.setblocking(False)  # type: ignore[attr-defined]
        self._registered_write = False
        self._call_socket_open(self._sock)

        return self._send_connect(self._keepalive)

    def loop(self, timeout: float = 1.0) -> MQTTErrorCode:
        """Process network events.

        It is strongly recommended that you use `loop_start()`, or
        `loop_forever()`, or if you are using an external event loop using
        `loop_read()`, `loop_write()`, and `loop_misc()`. Using loop() on it's own is
        no longer recommended.

        This function must be called regularly to ensure communication with the
        broker is carried out. It calls select() on the network socket to wait
        for network events. If incoming data is present it will then be
        processed. Outgoing commands, from e.g. `publish()`, are normally sent
        immediately that their function is called, but this is not always
        possible. loop() will also attempt to send any remaining outgoing
        messages, which also includes commands that are part of the flow for
        messages with QoS>0.

        :param int timeout: The time in seconds to wait for incoming/outgoing network
            traffic before timing out and returning.

        Returns MQTT_ERR_SUCCESS on success.
        Returns >0 on error.

        A ValueError will be raised if timeout < 0"""

        if self._sockpairR is None or self._sockpairW is None:
            self._reset_sockets(sockpair_only=True)
            self._sockpairR, self._sockpairW = _socketpair_compat()

        return self._loop(timeout)

    def _loop(self, timeout: float = 1.0) -> MQTTErrorCode:
        if timeout < 0.0:
            raise ValueError('Invalid timeout.')

        if self.want_write():
            wlist = [self._sock]
        else:
            wlist = []

        # used to check if there are any bytes left in the (SSL) socket
        pending_bytes = 0
        if hasattr(self._sock, 'pending'):
            pending_bytes = self._sock.pending()  # type: ignore[union-attr]

        # if bytes are pending do not wait in select
        if pending_bytes > 0:
            timeout = 0.0

        # sockpairR is used to break out of select() before the timeout, on a
        # call to publish() etc.
        if self._sockpairR is None:
            rlist = [self._sock]
        else:
            rlist = [self._sock, self._sockpairR]

        try:
            socklist = select.select(rlist, wlist, [], timeout)
        except TypeError:
            # Socket isn't correct type, in likelihood connection is lost
            # ... or we called disconnect(). In that case the socket will
            # be closed but some loop (like loop_forever) will continue to
            # call _loop(). We still want to break that loop by returning an
            # rc != MQTT_ERR_SUCCESS and we don't want state to change from
            # mqtt_cs_disconnecting.
            if self._state not in (_ConnectionState.MQTT_CS_DISCONNECTING, _ConnectionState.MQTT_CS_DISCONNECTED):
                self._state = _ConnectionState.MQTT_CS_CONNECTION_LOST
            return MQTTErrorCode.MQTT_ERR_CONN_LOST
        except ValueError:
            # Can occur if we just reconnected but rlist/wlist contain a -1 for
            # some reason.
            if self._state not in (_ConnectionState.MQTT_CS_DISCONNECTING, _ConnectionState.MQTT_CS_DISCONNECTED):
                self._state = _ConnectionState.MQTT_CS_CONNECTION_LOST
            return MQTTErrorCode.MQTT_ERR_CONN_LOST
        except Exception:
            # Note that KeyboardInterrupt, etc. can still terminate since they
            # are not derived from Exception
            return MQTTErrorCode.MQTT_ERR_UNKNOWN

        if self._sock in socklist[0] or pending_bytes > 0:
            rc = self.loop_read()
            if rc or self._sock is None:
                return rc

        if self._sockpairR and self._sockpairR in socklist[0]:
            # Stimulate output write even though we didn't ask for it, because
            # at that point the publish or other command wasn't present.
            socklist[1].insert(0, self._sock)
            # Clear sockpairR - only ever a single byte written.
            try:
                # Read many bytes at once - this allows up to 10000 calls to
                # publish() inbetween calls to loop().
                self._sockpairR.recv(10000)
            except BlockingIOError:
                pass

        if self._sock in socklist[1]:
            rc = self.loop_write()
            if rc or self._sock is None:
                return rc

        return self.loop_misc()

    def publish(
        self,
        topic: str,
        payload: PayloadType = None,
        qos: int = 0,
        retain: bool = False,
        properties: Properties | None = None,
    ) -> MQTTMessageInfo:
        """Publish a message on a topic.

        This causes a message to be sent to the broker and subsequently from
        the broker to any clients subscribing to matching topics.

        :param str topic: The topic that the message should be published on.
        :param payload: The actual message to send. If not given, or set to None a
            zero length message will be used. Passing an int or float will result
            in the payload being converted to a string representing that number. If
            you wish to send a true int/float, use struct.pack() to create the
            payload you require.
        :param int qos: The quality of service level to use.
        :param bool retain: If set to true, the message will be set as the "last known
            good"/retained message for the topic.
        :param Properties properties: (MQTT v5.0 only) the MQTT v5.0 properties to be included.

        Returns a `MQTTMessageInfo` class, which can be used to determine whether
        the message has been delivered (using `is_published()`) or to block
        waiting for the message to be delivered (`wait_for_publish()`). The
        message ID and return code of the publish() call can be found at
        :py:attr:`info.mid <MQTTMessage.mid>` and :py:attr:`info.rc <MQTTMessage.rc>`.

        For backwards compatibility, the `MQTTMessageInfo` class is iterable so
        the old construct of ``(rc, mid) = client.publish(...)`` is still valid.

        rc is MQTT_ERR_SUCCESS to indicate success or MQTT_ERR_NO_CONN if the
        client is not currently connected.  mid is the message ID for the
        publish request. The mid value can be used to track the publish request
        by checking against the mid argument in the on_publish() callback if it
        is defined.

        :raises ValueError: if topic is None, has zero length or is
            invalid (contains a wildcard), except if the MQTT version used is v5.0.
            For v5.0, a zero length topic can be used when a Topic Alias has been set.
        :raises ValueError: if qos is not one of 0, 1 or 2
        :raises ValueError: if the length of the payload is greater than 268435455 bytes.
        """
        if self._protocol != MQTTv5:
            if topic is None or len(topic) == 0:
                raise ValueError('Invalid topic.')

        topic_bytes = topic.encode('utf-8')

        self._raise_for_invalid_topic(topic_bytes)

        if qos < 0 or qos > 2:
            raise ValueError('Invalid QoS level.')

        local_payload = _encode_payload(payload)

        if len(local_payload) > 268435455:
            raise ValueError('Payload too large.')

        local_mid = self._mid_generate()

        if qos == 0:
            info = MQTTMessageInfo(local_mid)
            rc = self._send_publish(
                local_mid, topic_bytes, local_payload, qos, retain, False, info, properties)
            info.rc = rc
            return info
        else:
            message = MQTTMessage(local_mid, topic_bytes)
            message.timestamp = time_func()
            message.payload = local_payload
            message.qos = qos
            message.retain = retain
            message.dup = False
            message.properties = properties

            with self._out_message_mutex:
                if self._max_queued_messages > 0 and len(self._out_messages) >= self._max_queued_messages:
                    message.info.rc = MQTTErrorCode.MQTT_ERR_QUEUE_SIZE
                    return message.info

                if local_mid in self._out_messages:
                    message.info.rc = MQTTErrorCode.MQTT_ERR_QUEUE_SIZE
                    return message.info

                self._out_messages[message.mid] = message
                if self._max_inflight_messages == 0 or self._inflight_messages < self._max_inflight_messages:
                    self._inflight_messages += 1
                    if qos == 1:
                        message.state = mqtt_ms_wait_for_puback
                    elif qos == 2:
                        message.state = mqtt_ms_wait_for_pubrec

                    rc = self._send_publish(message.mid, topic_bytes, message.payload, message.qos, message.retain,
                                            message.dup, message.info, message.properties)

                    # remove from inflight messages so it will be send after a connection is made
                    if rc == MQTTErrorCode.MQTT_ERR_NO_CONN:
                        self._inflight_messages -= 1
                        message.state = mqtt_ms_publish

                    message.info.rc = rc
                    return message.info
                else:
                    message.state = mqtt_ms_queued
                    message.info.rc = MQTTErrorCode.MQTT_ERR_SUCCESS
                    return message.info

    def username_pw_set(
        self, username: str | None, password: str | None = None
    ) -> None:
        """Set a username and optionally a password for broker authentication.

        Must be called before connect() to have any effect.
        Requires a broker that supports MQTT v3.1 or more.

        :param str username: The username to authenticate with. Need have no relationship to the client id. Must be str
            [MQTT-3.1.3-11].
            Set to None to reset client back to not using username/password for broker authentication.
        :param str password: The password to authenticate with. Optional, set to None if not required. If it is str, then it
            will be encoded as UTF-8.
        """

        # [MQTT-3.1.3-11] User name must be UTF-8 encoded string
        self._username = None if username is None else username.encode('utf-8')
        if isinstance(password, str):
            self._password = password.encode('utf-8')
        else:
            self._password = password

    def enable_bridge_mode(self) -> None:
        """Sets the client in a bridge mode instead of client mode.

        Must be called before `connect()` to have any effect.
        Requires brokers that support bridge mode.

        Under bridge mode, the broker will identify the client as a bridge and
        not send it's own messages back to it. Hence a subsciption of # is
        possible without message loops. This feature also correctly propagates
        the retain flag on the messages.

        Currently Mosquitto and RSMB support this feature. This feature can
        be used to create a bridge between multiple broker.
        """
        self._client_mode = MQTT_BRIDGE

    def _connection_closed(self) -> bool:
        """
        Return true if the connection is closed (and not trying to be opened).
        """
        return (
            self._state == _ConnectionState.MQTT_CS_NEW
            or (self._state in (_ConnectionState.MQTT_CS_DISCONNECTING, _ConnectionState.MQTT_CS_DISCONNECTED) and self._sock is None))

    def is_connected(self) -> bool:
        """Returns the current status of the connection

        True if connection exists
        False if connection is closed
        """
        return self._state == _ConnectionState.MQTT_CS_CONNECTED

    def disconnect(
        self,
        reasoncode: ReasonCode | None = None,
        properties: Properties | None = None,
    ) -> MQTTErrorCode:
        """Disconnect a connected client from the broker.

        :param ReasonCode reasoncode: (MQTT v5.0 only) a ReasonCode instance setting the MQTT v5.0
            reasoncode to be sent with the disconnect packet. It is optional, the receiver
            then assuming that 0 (success) is the value.
        :param Properties properties: (MQTT v5.0 only) a Properties instance setting the MQTT v5.0 properties
            to be included. Optional - if not set, no properties are sent.
        """
        if self._sock is None:
            self._state = _ConnectionState.MQTT_CS_DISCONNECTED
            return MQTT_ERR_NO_CONN
        else:
            self._state = _ConnectionState.MQTT_CS_DISCONNECTING

        return self._send_disconnect(reasoncode, properties)

    def subscribe(
        self,
        topic: str | tuple[str, int] | tuple[str, SubscribeOptions] | list[tuple[str, int]] | list[tuple[str, SubscribeOptions]],
        qos: int = 0,
        options: SubscribeOptions | None = None,
        properties: Properties | None = None,
    ) -> tuple[MQTTErrorCode, int | None]:
        """Subscribe the client to one or more topics.

        This function may be called in three different ways (and a further three for MQTT v5.0):

        Simple string and integer
        -------------------------
        e.g. subscribe("my/topic", 2)

        :topic: A string specifying the subscription topic to subscribe to.
        :qos: The desired quality of service level for the subscription.
            Defaults to 0.
        :options and properties: Not used.

        Simple string and subscribe options (MQTT v5.0 only)
        ----------------------------------------------------
        e.g. subscribe("my/topic", options=SubscribeOptions(qos=2))

        :topic: A string specifying the subscription topic to subscribe to.
        :qos: Not used.
        :options: The MQTT v5.0 subscribe options.
        :properties: a Properties instance setting the MQTT v5.0 properties
            to be included. Optional - if not set, no properties are sent.

        String and integer tuple
        ------------------------
        e.g. subscribe(("my/topic", 1))

        :topic: A tuple of (topic, qos). Both topic and qos must be present in
               the tuple.
        :qos and options: Not used.
        :properties: Only used for MQTT v5.0.  A Properties instance setting the
            MQTT v5.0 properties. Optional - if not set, no properties are sent.

        String and subscribe options tuple (MQTT v5.0 only)
        ---------------------------------------------------
        e.g. subscribe(("my/topic", SubscribeOptions(qos=1)))

        :topic: A tuple of (topic, SubscribeOptions). Both topic and subscribe
                options must be present in the tuple.
        :qos and options: Not used.
        :properties: a Properties instance setting the MQTT v5.0 properties
            to be included. Optional - if not set, no properties are sent.

        List of string and integer tuples
        ---------------------------------
        e.g. subscribe([("my/topic", 0), ("another/topic", 2)])

        This allows multiple topic subscriptions in a single SUBSCRIPTION
        command, which is more efficient than using multiple calls to
        subscribe().

        :topic: A list of tuple of format (topic, qos). Both topic and qos must
               be present in all of the tuples.
        :qos, options and properties: Not used.

        List of string and subscribe option tuples (MQTT v5.0 only)
        -----------------------------------------------------------
        e.g. subscribe([("my/topic", SubscribeOptions(qos=0), ("another/topic", SubscribeOptions(qos=2)])

        This allows multiple topic subscriptions in a single SUBSCRIPTION
        command, which is more efficient than using multiple calls to
        subscribe().

        :topic: A list of tuple of format (topic, SubscribeOptions). Both topic and subscribe
                options must be present in all of the tuples.
        :qos and options: Not used.
        :properties: a Properties instance setting the MQTT v5.0 properties
            to be included. Optional - if not set, no properties are sent.

        The function returns a tuple (result, mid), where result is
        MQTT_ERR_SUCCESS to indicate success or (MQTT_ERR_NO_CONN, None) if the
        client is not currently connected.  mid is the message ID for the
        subscribe request. The mid value can be used to track the subscribe
        request by checking against the mid argument in the on_subscribe()
        callback if it is defined.

        Raises a ValueError if qos is not 0, 1 or 2, or if topic is None or has
        zero string length, or if topic is not a string, tuple or list.
        """
        topic_qos_list = None

        if isinstance(topic, tuple):
            if self._protocol == MQTTv5:
                topic, options = topic  # type: ignore
                if not isinstance(options, SubscribeOptions):
                    raise ValueError(
                        'Subscribe options must be instance of SubscribeOptions class.')
            else:
                topic, qos = topic  # type: ignore

        if isinstance(topic, (bytes, str)):
            if qos < 0 or qos > 2:
                raise ValueError('Invalid QoS level.')
            if self._protocol == MQTTv5:
                if options is None:
                    # if no options are provided, use the QoS passed instead
                    options = SubscribeOptions(qos=qos)
                elif qos != 0:
                    raise ValueError(
                        'Subscribe options and qos parameters cannot be combined.')
                if not isinstance(options, SubscribeOptions):
                    raise ValueError(
                        'Subscribe options must be instance of SubscribeOptions class.')
                topic_qos_list = [(topic.encode('utf-8'), options)]
            else:
                if topic is None or len(topic) == 0:
                    raise ValueError('Invalid topic.')
                topic_qos_list = [(topic.encode('utf-8'), qos)]  # type: ignore
        elif isinstance(topic, list):
            if len(topic) == 0:
                raise ValueError('Empty topic list')
            topic_qos_list = []
            if self._protocol == MQTTv5:
                for t, o in topic:
                    if not isinstance(o, SubscribeOptions):
                        # then the second value should be QoS
                        if o < 0 or o > 2:
                            raise ValueError('Invalid QoS level.')
                        o = SubscribeOptions(qos=o)
                    topic_qos_list.append((t.encode('utf-8'), o))
            else:
                for t, q in topic:
                    if isinstance(q, SubscribeOptions) or q < 0 or q > 2:
                        raise ValueError('Invalid QoS level.')
                    if t is None or len(t) == 0 or not isinstance(t, (bytes, str)):
                        raise ValueError('Invalid topic.')
                    topic_qos_list.append((t.encode('utf-8'), q))  # type: ignore

        if topic_qos_list is None:
            raise ValueError("No topic specified, or incorrect topic type.")

        if any(self._filter_wildcard_len_check(topic) != MQTT_ERR_SUCCESS for topic, _ in topic_qos_list):
            raise ValueError('Invalid subscription filter.')

        if self._sock is None:
            return (MQTT_ERR_NO_CONN, None)

        return self._send_subscribe(False, topic_qos_list, properties)

    def unsubscribe(
        self, topic: str | list[str], properties: Properties | None = None
    ) -> tuple[MQTTErrorCode, int | None]:
        """Unsubscribe the client from one or more topics.

        :param topic: A single string, or list of strings that are the subscription
            topics to unsubscribe from.
        :param properties: (MQTT v5.0 only) a Properties instance setting the MQTT v5.0 properties
            to be included. Optional - if not set, no properties are sent.

        Returns a tuple (result, mid), where result is MQTT_ERR_SUCCESS
        to indicate success or (MQTT_ERR_NO_CONN, None) if the client is not
        currently connected.
        mid is the message ID for the unsubscribe request. The mid value can be
        used to track the unsubscribe request by checking against the mid
        argument in the on_unsubscribe() callback if it is defined.

        :raises ValueError: if topic is None or has zero string length, or is
            not a string or list.
        """
        topic_list = None
        if topic is None:
            raise ValueError('Invalid topic.')
        if isinstance(topic, (bytes, str)):
            if len(topic) == 0:
                raise ValueError('Invalid topic.')
            topic_list = [topic.encode('utf-8')]
        elif isinstance(topic, list):
            topic_list = []
            for t in topic:
                if len(t) == 0 or not isinstance(t, (bytes, str)):
                    raise ValueError('Invalid topic.')
                topic_list.append(t.encode('utf-8'))

        if topic_list is None:
            raise ValueError("No topic specified, or incorrect topic type.")

        if self._sock is None:
            return (MQTTErrorCode.MQTT_ERR_NO_CONN, None)

        return self._send_unsubscribe(False, topic_list, properties)

    def loop_read(self, max_packets: int = 1) -> MQTTErrorCode:
        """Process read network events. Use in place of calling `loop()` if you
        wish to handle your client reads as part of your own application.

        Use `socket()` to obtain the client socket to call select() or equivalent
        on.

        Do not use if you are using `loop_start()` or `loop_forever()`."""
        if self._sock is None:
            return MQTTErrorCode.MQTT_ERR_NO_CONN

        max_packets = len(self._out_messages) + len(self._in_messages)
        if max_packets < 1:
            max_packets = 1

        for _ in range(0, max_packets):
            if self._sock is None:
                return MQTTErrorCode.MQTT_ERR_NO_CONN
            rc = self._packet_read()
            if rc > 0:
                return self._loop_rc_handle(rc)
            elif rc == MQTTErrorCode.MQTT_ERR_AGAIN:
                return MQTTErrorCode.MQTT_ERR_SUCCESS
        return MQTTErrorCode.MQTT_ERR_SUCCESS

    def loop_write(self) -> MQTTErrorCode:
        """Process write network events. Use in place of calling `loop()` if you
        wish to handle your client writes as part of your own application.

        Use `socket()` to obtain the client socket to call select() or equivalent
        on.

        Use `want_write()` to determine if there is data waiting to be written.

        Do not use if you are using `loop_start()` or `loop_forever()`."""
        if self._sock is None:
            return MQTTErrorCode.MQTT_ERR_NO_CONN

        try:
            rc = self._packet_write()
            if rc == MQTTErrorCode.MQTT_ERR_AGAIN:
                return MQTTErrorCode.MQTT_ERR_SUCCESS
            elif rc > 0:
                return self._loop_rc_handle(rc)
            else:
                return MQTTErrorCode.MQTT_ERR_SUCCESS
        finally:
            if self.want_write():
                self._call_socket_register_write()
            else:
                self._call_socket_unregister_write()

    def want_write(self) -> bool:
        """Call to determine if there is network data waiting to be written.
        Useful if you are calling select() yourself rather than using `loop()`, `loop_start()` or `loop_forever()`.
        """
        return len(self._out_packet) > 0

    def loop_misc(self) -> MQTTErrorCode:
        """Process miscellaneous network events. Use in place of calling `loop()` if you
        wish to call select() or equivalent on.

        Do not use if you are using `loop_start()` or `loop_forever()`."""
        if self._sock is None:
            return MQTTErrorCode.MQTT_ERR_NO_CONN

        now = time_func()
        self._check_keepalive()

        if self._ping_t > 0 and now - self._ping_t >= self._keepalive:
            # client->ping_t != 0 means we are waiting for a pingresp.
            # This hasn't happened in the keepalive time so we should disconnect.
            self._sock_close()

            if self._state in (_ConnectionState.MQTT_CS_DISCONNECTING, _ConnectionState.MQTT_CS_DISCONNECTED):
                self._state = _ConnectionState.MQTT_CS_DISCONNECTED
                rc = MQTTErrorCode.MQTT_ERR_SUCCESS
            else:
                self._state = _ConnectionState.MQTT_CS_CONNECTION_LOST
                rc = MQTTErrorCode.MQTT_ERR_KEEPALIVE

            self._do_on_disconnect(
                packet_from_broker=False,
                v1_rc=rc,
            )

            return MQTTErrorCode.MQTT_ERR_CONN_LOST

        return MQTTErrorCode.MQTT_ERR_SUCCESS

    def max_inflight_messages_set(self, inflight: int) -> None:
        """Set the maximum number of messages with QoS>0 that can be part way
        through their network flow at once. Defaults to 20."""
        self.max_inflight_messages = inflight

    def max_queued_messages_set(self, queue_size: int) -> Client:
        """Set the maximum number of messages in the outgoing message queue.
        0 means unlimited."""
        if not isinstance(queue_size, int):
            raise ValueError('Invalid type of queue size.')
        self.max_queued_messages = queue_size
        return self

    def user_data_set(self, userdata: Any) -> None:
        """Set the user data variable passed to callbacks. May be any data type."""
        self._userdata = userdata

    def user_data_get(self) -> Any:
        """Get the user data variable passed to callbacks. May be any data type."""
        return self._userdata

    def will_set(
        self,
        topic: str,
        payload: PayloadType = None,
        qos: int = 0,
        retain: bool = False,
        properties: Properties | None = None,
    ) -> None:
        """Set a Will to be sent by the broker in case the client disconnects unexpectedly.

        This must be called before connect() to have any effect.

        :param str topic: The topic that the will message should be published on.
        :param payload: The message to send as a will. If not given, or set to None a
            zero length message will be used as the will. Passing an int or float
            will result in the payload being converted to a string representing
            that number. If you wish to send a true int/float, use struct.pack() to
            create the payload you require.
        :param int qos: The quality of service level to use for the will.
        :param bool retain: If set to true, the will message will be set as the "last known
            good"/retained message for the topic.
        :param Properties properties: (MQTT v5.0 only) the MQTT v5.0 properties
            to be included with the will message. Optional - if not set, no properties are sent.

        :raises ValueError: if qos is not 0, 1 or 2, or if topic is None or has
            zero string length.

        See `will_clear` to clear will. Note that will are NOT send if the client disconnect cleanly
        for example by calling `disconnect()`.
        """
        if topic is None or len(topic) == 0:
            raise ValueError('Invalid topic.')

        if qos < 0 or qos > 2:
            raise ValueError('Invalid QoS level.')

        if properties and not isinstance(properties, Properties):
            raise ValueError(
                "The properties argument must be an instance of the Properties class.")

        self._will_payload = _encode_payload(payload)
        self._will = True
        self._will_topic = topic.encode('utf-8')
        self._will_qos = qos
        self._will_retain = retain
        self._will_properties = properties

    def will_clear(self) -> None:
        """ Removes a will that was previously configured with `will_set()`.

        Must be called before connect() to have any effect."""
        self._will = False
        self._will_topic = b""
        self._will_payload = b""
        self._will_qos = 0
        self._will_retain = False

    def socket(self) -> SocketLike | None:
        """Return the socket or ssl object for this client."""
        return self._sock

    def loop_forever(
        self,
        timeout: float = 1.0,
        retry_first_connection: bool = False,
    ) -> MQTTErrorCode:
        """This function calls the network loop functions for you in an
        infinite blocking loop. It is useful for the case where you only want
        to run the MQTT client loop in your program.

        loop_forever() will handle reconnecting for you if reconnect_on_failure is
        true (this is the default behavior). If you call `disconnect()` in a callback
        it will return.

        :param int timeout: The time in seconds to wait for incoming/outgoing network
          traffic before timing out and returning.
        :param bool retry_first_connection: Should the first connection attempt be retried on failure.
          This is independent of the reconnect_on_failure setting.

        :raises OSError: if the first connection fail unless retry_first_connection=True
        """

        run = True

        while run:
            if self._thread_terminate is True:
                break

            if self._state == _ConnectionState.MQTT_CS_CONNECT_ASYNC:
                try:
                    self.reconnect()
                except OSError:
                    self._handle_on_connect_fail()
                    if not retry_first_connection:
                        raise
                    self._easy_log(
                        MQTT_LOG_DEBUG, "Connection failed, retrying")
                    self._reconnect_wait()
            else:
                break

        while run:
            rc = MQTTErrorCode.MQTT_ERR_SUCCESS
            while rc == MQTTErrorCode.MQTT_ERR_SUCCESS:
                rc = self._loop(timeout)
                # We don't need to worry about locking here, because we've
                # either called loop_forever() when in single threaded mode, or
                # in multi threaded mode when loop_stop() has been called and
                # so no other threads can access _out_packet or _messages.
                if (self._thread_terminate is True
                    and len(self._out_packet) == 0
                        and len(self._out_messages) == 0):
                    rc = MQTTErrorCode.MQTT_ERR_NOMEM
                    run = False

            def should_exit() -> bool:
                return (
                    self._state in (_ConnectionState.MQTT_CS_DISCONNECTING, _ConnectionState.MQTT_CS_DISCONNECTED) or
                    run is False or  # noqa: B023 (uses the run variable from the outer scope on purpose)
                    self._thread_terminate is True
                )

            if should_exit() or not self._reconnect_on_failure:
                run = False
            else:
                self._reconnect_wait()

                if should_exit():
                    run = False
                else:
                    try:
                        self.reconnect()
                    except OSError:
                        self._handle_on_connect_fail()
                        self._easy_log(
                            MQTT_LOG_DEBUG, "Connection failed, retrying")

        return rc

    def loop_start(self) -> MQTTErrorCode:
        """This is part of the threaded client interface. Call this once to
        start a new thread to process network traffic. This provides an
        alternative to repeatedly calling `loop()` yourself.

        Under the hood, this will call `loop_forever` in a thread, which means that
        the thread will terminate if you call `disconnect()`
        """
        if self._thread is not None:
            return MQTTErrorCode.MQTT_ERR_INVAL

        self._sockpairR, self._sockpairW = _socketpair_compat()
        self._thread_terminate = False
        self._thread = threading.Thread(target=self._thread_main, name=f"paho-mqtt-client-{self._client_id.decode()}")
        self._thread.daemon = True
        self._thread.start()

        return MQTTErrorCode.MQTT_ERR_SUCCESS

    def loop_stop(self) -> MQTTErrorCode:
        """This is part of the threaded client interface. Call this once to
        stop the network thread previously created with `loop_start()`. This call
        will block until the network thread finishes.

        This don't guarantee that publish packet are sent, use `wait_for_publish` or
        `on_publish` to ensure `publish` are sent.
        """
        if self._thread is None:
            return MQTTErrorCode.MQTT_ERR_INVAL

        self._thread_terminate = True
        if threading.current_thread() != self._thread:
            self._thread.join()

        return MQTTErrorCode.MQTT_ERR_SUCCESS

    @property
    def callback_api_version(self) -> CallbackAPIVersion:
        """
        Return the callback API version used for user-callback. See docstring for
        each user-callback (`on_connect`, `on_publish`, ...) for details.

        This property is read-only.
        """
        return self._callback_api_version

    @property
    def on_log(self) -> CallbackOnLog | None:
        """The callback called when the client has log information.
        Defined to allow debugging.

        Expected signature is::

            log_callback(client, userdata, level, buf)

        :param Client client: the client instance for this callback
        :param userdata: the private user data as set in Client() or user_data_set()
        :param int level: gives the severity of the message and will be one of
                    MQTT_LOG_INFO, MQTT_LOG_NOTICE, MQTT_LOG_WARNING,
                    MQTT_LOG_ERR, and MQTT_LOG_DEBUG.
        :param str buf: the message itself

        Decorator: @client.log_callback() (``client`` is the name of the
            instance which this callback is being attached to)
        """
        return self._on_log

    @on_log.setter
    def on_log(self, func: CallbackOnLog | None) -> None:
        self._on_log = func

    def log_callback(self) -> Callable[[CallbackOnLog], CallbackOnLog]:
        def decorator(func: CallbackOnLog) -> CallbackOnLog:
            self.on_log = func
            return func
        return decorator

    @property
    def on_pre_connect(self) -> CallbackOnPreConnect | None:
        """The callback called immediately prior to the connection is made
        request.

        Expected signature (for all callback API version)::

            connect_callback(client, userdata)

        :parama Client client: the client instance for this callback
        :parama userdata: the private user data as set in Client() or user_data_set()

        Decorator: @client.pre_connect_callback() (``client`` is the name of the
            instance which this callback is being attached to)

        """
        return self._on_pre_connect

    @on_pre_connect.setter
    def on_pre_connect(self, func: CallbackOnPreConnect | None) -> None:
        with self._callback_mutex:
            self._on_pre_connect = func

    def pre_connect_callback(
        self,
    ) -> Callable[[CallbackOnPreConnect], CallbackOnPreConnect]:
        def decorator(func: CallbackOnPreConnect) -> CallbackOnPreConnect:
            self.on_pre_connect = func
            return func
        return decorator

    @property
    def on_connect(self) -> CallbackOnConnect | None:
        """The callback called when the broker reponds to our connection request.

        Expected signature for callback API version 2::

            connect_callback(client, userdata, connect_flags, reason_code, properties)

        Expected signature for callback API version 1 change with MQTT protocol version:
            * For MQTT v3.1 and v3.1.1 it's::

                connect_callback(client, userdata, flags, rc)

            * For MQTT v5.0 it's::

                connect_callback(client, userdata, flags, reason_code, properties)


        :param Client client: the client instance for this callback
        :param userdata: the private user data as set in Client() or user_data_set()
        :param ConnectFlags connect_flags: the flags for this connection
        :param ReasonCode reason_code: the connection reason code received from the broken.
                       In MQTT v5.0 it's the reason code defined by the standard.
                       In MQTT v3, we convert return code to a reason code, see
                       `convert_connack_rc_to_reason_code()`.
                       `ReasonCode` may be compared to integer.
        :param Properties properties: the MQTT v5.0 properties received from the broker.
                       For MQTT v3.1 and v3.1.1 properties is not provided and an empty Properties
                       object is always used.
        :param dict flags: response flags sent by the broker
        :param int rc: the connection result, should have a value of `ConnackCode`

        flags is a dict that contains response flags from the broker:
            flags['session present'] - this flag is useful for clients that are
                using clean session set to 0 only. If a client with clean
                session=0, that reconnects to a broker that it has previously
                connected to, this flag indicates whether the broker still has the
                session information for the client. If 1, the session still exists.

        The value of rc indicates success or not:
            - 0: Connection successful
            - 1: Connection refused - incorrect protocol version
            - 2: Connection refused - invalid client identifier
            - 3: Connection refused - server unavailable
            - 4: Connection refused - bad username or password
            - 5: Connection refused - not authorised
            - 6-255: Currently unused.

        Decorator: @client.connect_callback() (``client`` is the name of the
            instance which this callback is being attached to)
        """
        return self._on_connect

    @on_connect.setter
    def on_connect(self, func: CallbackOnConnect | None) -> None:
        with self._callback_mutex:
            self._on_connect = func

    def connect_callback(
        self,
    ) -> Callable[[CallbackOnConnect], CallbackOnConnect]:
        def decorator(func: CallbackOnConnect) -> CallbackOnConnect:
            self.on_connect = func
            return func
        return decorator

    @property
    def on_connect_fail(self) -> CallbackOnConnectFail | None:
        """The callback called when the client failed to connect
        to the broker.

        Expected signature is (for all callback_api_version)::

            connect_fail_callback(client, userdata)

        :param Client client: the client instance for this callback
        :parama userdata: the private user data as set in Client() or user_data_set()

        Decorator: @client.connect_fail_callback() (``client`` is the name of the
            instance which this callback is being attached to)
        """
        return self._on_connect_fail

    @on_connect_fail.setter
    def on_connect_fail(self, func: CallbackOnConnectFail | None) -> None:
        with self._callback_mutex:
            self._on_connect_fail = func

    def connect_fail_callback(
        self,
    ) -> Callable[[CallbackOnConnectFail], CallbackOnConnectFail]:
        def decorator(func: CallbackOnConnectFail) -> CallbackOnConnectFail:
            self.on_connect_fail = func
            return func
        return decorator

    @property
    def on_subscribe(self) -> CallbackOnSubscribe | None:
        """The callback called when the broker responds to a subscribe
        request.

        Expected signature for callback API version 2::

            subscribe_callback(client, userdata, mid, reason_code_list, properties)

        Expected signature for callback API version 1 change with MQTT protocol version:
            * For MQTT v3.1 and v3.1.1 it's::

                subscribe_callback(client, userdata, mid, granted_qos)

            * For MQTT v5.0 it's::

                subscribe_callback(client, userdata, mid, reason_code_list, properties)

        :param Client client: the client instance for this callback
        :param userdata: the private user data as set in Client() or user_data_set()
        :param int mid: matches the mid variable returned from the corresponding
                          subscribe() call.
        :param list[ReasonCode] reason_code_list: reason codes received from the broker for each subscription.
                          In MQTT v5.0 it's the reason code defined by the standard.
                          In MQTT v3, we convert granted QoS to a reason code.
                          It's a list of ReasonCode instances.
        :param Properties properties: the MQTT v5.0 properties received from the broker.
                          For MQTT v3.1 and v3.1.1 properties is not provided and an empty Properties
                          object is always used.
        :param list[int] granted_qos: list of integers that give the QoS level the broker has
                          granted for each of the different subscription requests.

        Decorator: @client.subscribe_callback() (``client`` is the name of the
            instance which this callback is being attached to)
        """
        return self._on_subscribe

    @on_subscribe.setter
    def on_subscribe(self, func: CallbackOnSubscribe | None) -> None:
        with self._callback_mutex:
            self._on_subscribe = func

    def subscribe_callback(
        self,
    ) -> Callable[[CallbackOnSubscribe], CallbackOnSubscribe]:
        def decorator(func: CallbackOnSubscribe) -> CallbackOnSubscribe:
            self.on_subscribe = func
            return func
        return decorator

    @property
    def on_message(self) -> CallbackOnMessage | None:
        """The callback called when a message has been received on a topic
        that the client subscribes to.

        This callback will be called for every message received unless a
        `message_callback_add()` matched the message.

        Expected signature is (for all callback API version):
            message_callback(client, userdata, message)

        :param Client client: the client instance for this callback
        :param userdata: the private user data as set in Client() or user_data_set()
        :param MQTTMessage message: the received message.
                    This is a class with members topic, payload, qos, retain.

        Decorator: @client.message_callback() (``client`` is the name of the
            instance which this callback is being attached to)
        """
        return self._on_message

    @on_message.setter
    def on_message(self, func: CallbackOnMessage | None) -> None:
        with self._callback_mutex:
            self._on_message = func

    def message_callback(
        self,
    ) -> Callable[[CallbackOnMessage], CallbackOnMessage]:
        def decorator(func: CallbackOnMessage) -> CallbackOnMessage:
            self.on_message = func
            return func
        return decorator

    @property
    def on_publish(self) -> CallbackOnPublish | None:
        """The callback called when a message that was to be sent using the
        `publish()` call has completed transmission to the broker.

        For messages with QoS levels 1 and 2, this means that the appropriate
        handshakes have completed. For QoS 0, this simply means that the message
        has left the client.
        This callback is important because even if the `publish()` call returns
        success, it does not always mean that the message has been sent.

        See also `wait_for_publish` which could be simpler to use.

        Expected signature for callback API version 2::

            publish_callback(client, userdata, mid, reason_code, properties)

        Expected signature for callback API version 1::

            publish_callback(client, userdata, mid)

        :param Client client: the client instance for this callback
        :param userdata: the private user data as set in Client() or user_data_set()
        :param int mid: matches the mid variable returned from the corresponding
                     `publish()` call, to allow outgoing messages to be tracked.
        :param ReasonCode reason_code: the connection reason code received from the broken.
                     In MQTT v5.0 it's the reason code defined by the standard.
                     In MQTT v3 it's always the reason code Success
        :parama Properties properties: the MQTT v5.0 properties received from the broker.
                     For MQTT v3.1 and v3.1.1 properties is not provided and an empty Properties
                     object is always used.

        Note: for QoS = 0, the reason_code and the properties don't really exist, it's the client
        library that generate them. It's always an empty properties and a success reason code.
        Because the (MQTTv5) standard don't have reason code for PUBLISH packet, the library create them
        at PUBACK packet, as if the message was sent with QoS = 1.

        Decorator: @client.publish_callback() (``client`` is the name of the
            instance which this callback is being attached to)

        """
        return self._on_publish

    @on_publish.setter
    def on_publish(self, func: CallbackOnPublish | None) -> None:
        with self._callback_mutex:
            self._on_publish = func

    def publish_callback(
        self,
    ) -> Callable[[CallbackOnPublish], CallbackOnPublish]:
        def decorator(func: CallbackOnPublish) -> CallbackOnPublish:
            self.on_publish = func
            return func
        return decorator

    @property
    def on_unsubscribe(self) -> CallbackOnUnsubscribe | None:
        """The callback called when the broker responds to an unsubscribe
        request.

        Expected signature for callback API version 2::

            unsubscribe_callback(client, userdata, mid, reason_code_list, properties)

        Expected signature for callback API version 1 change with MQTT protocol version:
            * For MQTT v3.1 and v3.1.1 it's::

                unsubscribe_callback(client, userdata, mid)

            * For MQTT v5.0 it's::

                unsubscribe_callback(client, userdata, mid, properties, v1_reason_codes)

        :param Client client: the client instance for this callback
        :param userdata: the private user data as set in Client() or user_data_set()
        :param mid: matches the mid variable returned from the corresponding
                          unsubscribe() call.
        :param list[ReasonCode] reason_code_list: reason codes received from the broker for each unsubscription.
                          In MQTT v5.0 it's the reason code defined by the standard.
                          In MQTT v3, there is not equivalent from broken and empty list
                          is always used.
        :param Properties properties: the MQTT v5.0 properties received from the broker.
                          For MQTT v3.1 and v3.1.1 properties is not provided and an empty Properties
                          object is always used.
        :param v1_reason_codes: the MQTT v5.0 reason codes received from the broker for each
                          unsubscribe topic.  A list of ReasonCode instances OR a single
                          ReasonCode when we unsubscribe from a single topic.

        Decorator: @client.unsubscribe_callback() (``client`` is the name of the
            instance which this callback is being attached to)
        """
        return self._on_unsubscribe

    @on_unsubscribe.setter
    def on_unsubscribe(self, func: CallbackOnUnsubscribe | None) -> None:
        with self._callback_mutex:
            self._on_unsubscribe = func

    def unsubscribe_callback(
        self,
    ) -> Callable[[CallbackOnUnsubscribe], CallbackOnUnsubscribe]:
        def decorator(func: CallbackOnUnsubscribe) -> CallbackOnUnsubscribe:
            self.on_unsubscribe = func
            return func
        return decorator

    @property
    def on_disconnect(self) -> CallbackOnDisconnect | None:
        """The callback called when the client disconnects from the broker.

        Expected signature for callback API version 2::

            disconnect_callback(client, userdata, disconnect_flags, reason_code, properties)

        Expected signature for callback API version 1 change with MQTT protocol version:
            * For MQTT v3.1 and v3.1.1 it's::

                disconnect_callback(client, userdata, rc)

            * For MQTT v5.0 it's::

                disconnect_callback(client, userdata, reason_code, properties)

        :param Client client: the client instance for this callback
        :param userdata:  the private user data as set in Client() or user_data_set()
        :param DisconnectFlag disconnect_flags: the flags for this disconnection.
        :param ReasonCode reason_code:  the disconnection reason code possibly received from the broker (see disconnect_flags).
                          In MQTT v5.0 it's the reason code defined by the standard.
                          In MQTT v3 it's never received from the broker, we convert an MQTTErrorCode,
                          see `convert_disconnect_error_code_to_reason_code()`.
                          `ReasonCode` may be compared to integer.
        :param Properties properties: the MQTT v5.0 properties received from the broker.
                          For MQTT v3.1 and v3.1.1 properties is not provided and an empty Properties
                          object is always used.
        :param int rc: the disconnection result
                          The rc parameter indicates the disconnection state. If
                          MQTT_ERR_SUCCESS (0), the callback was called in response to
                          a disconnect() call. If any other value the disconnection
                          was unexpected, such as might be caused by a network error.

        Decorator: @client.disconnect_callback() (``client`` is the name of the
            instance which this callback is being attached to)

        """
        return self._on_disconnect

    @on_disconnect.setter
    def on_disconnect(self, func: CallbackOnDisconnect | None) -> None:
        with self._callback_mutex:
            self._on_disconnect = func

    def disconnect_callback(
        self,
    ) -> Callable[[CallbackOnDisconnect], CallbackOnDisconnect]:
        def decorator(func: CallbackOnDisconnect) -> CallbackOnDisconnect:
            self.on_disconnect = func
            return func
        return decorator

    @property
    def on_socket_open(self) -> CallbackOnSocket | None:
        """The callback called just after the socket was opend.

        This should be used to register the socket to an external event loop for reading.

        Expected signature is (for all callback API version)::

            socket_open_callback(client, userdata, socket)

        :param Client client:     the client instance for this callback
        :param userdata:   the private user data as set in Client() or user_data_set()
        :param SocketLike sock: the socket which was just opened.

        Decorator: @client.socket_open_callback() (``client`` is the name of the
            instance which this callback is being attached to)
        """
        return self._on_socket_open

    @on_socket_open.setter
    def on_socket_open(self, func: CallbackOnSocket | None) -> None:
        with self._callback_mutex:
            self._on_socket_open = func

    def socket_open_callback(
        self,
    ) -> Callable[[CallbackOnSocket], CallbackOnSocket]:
        def decorator(func: CallbackOnSocket) -> CallbackOnSocket:
            self.on_socket_open = func
            return func
        return decorator

    def _call_socket_open(self, sock: SocketLike) -> None:
        """Call the socket_open callback with the just-opened socket"""
        with self._callback_mutex:
            on_socket_open = self.on_socket_open

        if on_socket_open:
            with self._in_callback_mutex:
                try:
                    on_socket_open(self, self._userdata, sock)
                except Exception as err:
                    self._easy_log(
                        MQTT_LOG_ERR, 'Caught exception in on_socket_open: %s', err)
                    if not self.suppress_exceptions:
                        raise

    @property
    def on_socket_close(self) -> CallbackOnSocket | None:
        """The callback called just before the socket is closed.

        This should be used to unregister the socket from an external event loop for reading.

        Expected signature is (for all callback API version)::

            socket_close_callback(client, userdata, socket)

        :param Client client: the client instance for this callback
        :param userdata: the private user data as set in Client() or user_data_set()
        :param SocketLike sock: the socket which is about to be closed.

        Decorator: @client.socket_close_callback() (``client`` is the name of the
            instance which this callback is being attached to)
        """
        return self._on_socket_close

    @on_socket_close.setter
    def on_socket_close(self, func: CallbackOnSocket | None) -> None:
        with self._callback_mutex:
            self._on_socket_close = func

    def socket_close_callback(
        self,
    ) -> Callable[[CallbackOnSocket], CallbackOnSocket]:
        def decorator(func: CallbackOnSocket) -> CallbackOnSocket:
            self.on_socket_close = func
            return func
        return decorator

    def _call_socket_close(self, sock: SocketLike) -> None:
        """Call the socket_close callback with the about-to-be-closed socket"""
        with self._callback_mutex:
            on_socket_close = self.on_socket_close

        if on_socket_close:
            with self._in_callback_mutex:
                try:
                    on_socket_close(self, self._userdata, sock)
                except Exception as err:
                    self._easy_log(
                        MQTT_LOG_ERR, 'Caught exception in on_socket_close: %s', err)
                    if not self.suppress_exceptions:
                        raise

    @property
    def on_socket_register_write(self) -> CallbackOnSocket | None:
        """The callback called when the socket needs writing but can't.

        This should be used to register the socket with an external event loop for writing.

        Expected signature is (for all callback API version)::

            socket_register_write_callback(client, userdata, socket)

        :param Client client: the client instance for this callback
        :param userdata: the private user data as set in Client() or user_data_set()
        :param SocketLike sock: the socket which should be registered for writing

        Decorator: @client.socket_register_write_callback() (``client`` is the name of the
            instance which this callback is being attached to)
        """
        return self._on_socket_register_write

    @on_socket_register_write.setter
    def on_socket_register_write(self, func: CallbackOnSocket | None) -> None:
        with self._callback_mutex:
            self._on_socket_register_write = func

    def socket_register_write_callback(
        self,
    ) -> Callable[[CallbackOnSocket], CallbackOnSocket]:
        def decorator(func: CallbackOnSocket) -> CallbackOnSocket:
            self._on_socket_register_write = func
            return func
        return decorator

    def _call_socket_register_write(self) -> None:
        """Call the socket_register_write callback with the unwritable socket"""
        if not self._sock or self._registered_write:
            return
        self._registered_write = True
        with self._callback_mutex:
            on_socket_register_write = self.on_socket_register_write

        if on_socket_register_write:
            try:
                on_socket_register_write(
                    self, self._userdata, self._sock)
            except Exception as err:
                self._easy_log(
                    MQTT_LOG_ERR, 'Caught exception in on_socket_register_write: %s', err)
                if not self.suppress_exceptions:
                    raise

    @property
    def on_socket_unregister_write(
        self,
    ) -> CallbackOnSocket | None:
        """The callback called when the socket doesn't need writing anymore.

        This should be used to unregister the socket from an external event loop for writing.

        Expected signature is (for all callback API version)::

            socket_unregister_write_callback(client, userdata, socket)

        :param Client client: the client instance for this callback
        :param userdata: the private user data as set in Client() or user_data_set()
        :param SocketLike sock: the socket which should be unregistered for writing

        Decorator: @client.socket_unregister_write_callback() (``client`` is the name of the
            instance which this callback is being attached to)
        """
        return self._on_socket_unregister_write

    @on_socket_unregister_write.setter
    def on_socket_unregister_write(
        self, func: CallbackOnSocket | None
    ) -> None:
        with self._callback_mutex:
            self._on_socket_unregister_write = func

    def socket_unregister_write_callback(
        self,
    ) -> Callable[[CallbackOnSocket], CallbackOnSocket]:
        def decorator(
            func: CallbackOnSocket,
        ) -> CallbackOnSocket:
            self._on_socket_unregister_write = func
            return func
        return decorator

    def _call_socket_unregister_write(
        self, sock: SocketLike | None = None
    ) -> None:
        """Call the socket_unregister_write callback with the writable socket"""
        sock = sock or self._sock
        if not sock or not self._registered_write:
            return
        self._registered_write = False

        with self._callback_mutex:
            on_socket_unregister_write = self.on_socket_unregister_write

        if on_socket_unregister_write:
            try:
                on_socket_unregister_write(self, self._userdata, sock)
            except Exception as err:
                self._easy_log(
                    MQTT_LOG_ERR, 'Caught exception in on_socket_unregister_write: %s', err)
                if not self.suppress_exceptions:
                    raise

    def message_callback_add(self, sub: str, callback: CallbackOnMessage) -> None:
        """Register a message callback for a specific topic.
        Messages that match 'sub' will be passed to 'callback'. Any
        non-matching messages will be passed to the default `on_message`
        callback.

        Call multiple times with different 'sub' to define multiple topic
        specific callbacks.

        Topic specific callbacks may be removed with
        `message_callback_remove()`.

        See `on_message` for the expected signature of the callback.

        Decorator: @client.topic_callback(sub) (``client`` is the name of the
            instance which this callback is being attached to)

        Example::

            @client.topic_callback("mytopic/#")
            def handle_mytopic(client, userdata, message):
                ...
        """
        if callback is None or sub is None:
            raise ValueError("sub and callback must both be defined.")

        with self._callback_mutex:
            self._on_message_filtered[sub] = callback

    def topic_callback(
        self, sub: str
    ) -> Callable[[CallbackOnMessage], CallbackOnMessage]:
        def decorator(func: CallbackOnMessage) -> CallbackOnMessage:
            self.message_callback_add(sub, func)
            return func
        return decorator

    def message_callback_remove(self, sub: str) -> None:
        """Remove a message callback previously registered with
        `message_callback_add()`."""
        if sub is None:
            raise ValueError("sub must defined.")

        with self._callback_mutex:
            try:
                del self._on_message_filtered[sub]
            except KeyError:  # no such subscription
                pass

    # ============================================================
    # Private functions
    # ============================================================

    def _loop_rc_handle(
        self,
        rc: MQTTErrorCode,
    ) -> MQTTErrorCode:
        if rc:
            self._sock_close()

            if self._state in (_ConnectionState.MQTT_CS_DISCONNECTING, _ConnectionState.MQTT_CS_DISCONNECTED):
                self._state = _ConnectionState.MQTT_CS_DISCONNECTED
                rc = MQTTErrorCode.MQTT_ERR_SUCCESS

            self._do_on_disconnect(packet_from_broker=False, v1_rc=rc)

        if rc == MQTT_ERR_CONN_LOST:
            self._state = _ConnectionState.MQTT_CS_CONNECTION_LOST

        return rc

    def _packet_read(self) -> MQTTErrorCode:
        # This gets called if pselect() indicates that there is network data
        # available - ie. at least one byte.  What we do depends on what data we
        # already have.
        # If we've not got a command, attempt to read one and save it. This should
        # always work because it's only a single byte.
        # Then try to read the remaining length. This may fail because it is may
        # be more than one byte - will need to save data pending next read if it
        # does fail.
        # Then try to read the remaining payload, where 'payload' here means the
        # combined variable header and actual payload. This is the most likely to
        # fail due to longer length, so save current data and current position.
        # After all data is read, send to _mqtt_handle_packet() to deal with.
        # Finally, free the memory and reset everything to starting conditions.
        if self._in_packet['command'] == 0:
            try:
                command = self._sock_recv(1)
            except BlockingIOError:
                return MQTTErrorCode.MQTT_ERR_AGAIN
            except TimeoutError as err:
                self._easy_log(
                    MQTT_LOG_ERR, 'timeout on socket: %s', err)
                return MQTTErrorCode.MQTT_ERR_CONN_LOST
            except OSError as err:
                self._easy_log(
                    MQTT_LOG_ERR, 'failed to receive on socket: %s', err)
                return MQTTErrorCode.MQTT_ERR_CONN_LOST
            else:
                if len(command) == 0:
                    return MQTTErrorCode.MQTT_ERR_CONN_LOST
                self._in_packet['command'] = command[0]

        if self._in_packet['have_remaining'] == 0:
            # Read remaining
            # Algorithm for decoding taken from pseudo code at
            # http://publib.boulder.ibm.com/infocenter/wmbhelp/v6r0m0/topic/com.ibm.etools.mft.doc/ac10870_.htm
            while True:
                try:
                    byte = self._sock_recv(1)
                except BlockingIOError:
                    return MQTTErrorCode.MQTT_ERR_AGAIN
                except OSError as err:
                    self._easy_log(
                        MQTT_LOG_ERR, 'failed to receive on socket: %s', err)
                    return MQTTErrorCode.MQTT_ERR_CONN_LOST
                else:
                    if len(byte) == 0:
                        return MQTTErrorCode.MQTT_ERR_CONN_LOST
                    byte_value = byte[0]
                    self._in_packet['remaining_count'].append(byte_value)
                    # Max 4 bytes length for remaining length as defined by protocol.
                    # Anything more likely means a broken/malicious client.
                    if len(self._in_packet['remaining_count']) > 4:
                        return MQTTErrorCode.MQTT_ERR_PROTOCOL

                    self._in_packet['remaining_length'] += (
                        byte_value & 127) * self._in_packet['remaining_mult']
                    self._in_packet['remaining_mult'] = self._in_packet['remaining_mult'] * 128

                if (byte_value & 128) == 0:
                    break

            self._in_packet['have_remaining'] = 1
            self._in_packet['to_process'] = self._in_packet['remaining_length']

        count = 100 # Don't get stuck in this loop if we have a huge message.
        while self._in_packet['to_process'] > 0:
            try:
                data = self._sock_recv(self._in_packet['to_process'])
            except BlockingIOError:
                return MQTTErrorCode.MQTT_ERR_AGAIN
            except OSError as err:
                self._easy_log(
                    MQTT_LOG_ERR, 'failed to receive on socket: %s', err)
                return MQTTErrorCode.MQTT_ERR_CONN_LOST
            else:
                if len(data) == 0:
                    return MQTTErrorCode.MQTT_ERR_CONN_LOST
                self._in_packet['to_process'] -= len(data)
                self._in_packet['packet'] += data
            count -= 1
            if count == 0:
                with self._msgtime_mutex:
                    self._last_msg_in = time_func()
                return MQTTErrorCode.MQTT_ERR_AGAIN

        # All data for this packet is read.
        self._in_packet['pos'] = 0
        rc = self._packet_handle()

        # Free data and reset values
        self._in_packet = {
            "command": 0,
            "have_remaining": 0,
            "remaining_count": [],
            "remaining_mult": 1,
            "remaining_length": 0,
            "packet": bytearray(b""),
            "to_process": 0,
            "pos": 0,
        }

        with self._msgtime_mutex:
            self._last_msg_in = time_func()
        return rc

    def _packet_write(self) -> MQTTErrorCode:
        while True:
            try:
                packet = self._out_packet.popleft()
            except IndexError:
                return MQTTErrorCode.MQTT_ERR_SUCCESS

            try:
                write_length = self._sock_send(
                    packet['packet'][packet['pos']:])
            except (AttributeError, ValueError):
                self._out_packet.appendleft(packet)
                return MQTTErrorCode.MQTT_ERR_SUCCESS
            except BlockingIOError:
                self._out_packet.appendleft(packet)
                return MQTTErrorCode.MQTT_ERR_AGAIN
            except OSError as err:
                self._out_packet.appendleft(packet)
                self._easy_log(
                    MQTT_LOG_ERR, 'failed to receive on socket: %s', err)
                return MQTTErrorCode.MQTT_ERR_CONN_LOST

            if write_length > 0:
                packet['to_process'] -= write_length
                packet['pos'] += write_length

                if packet['to_process'] == 0:
                    if (packet['command'] & 0xF0) == PUBLISH and packet['qos'] == 0:
                        with self._callback_mutex:
                            on_publish = self.on_publish

                        if on_publish:
                            with self._in_callback_mutex:
                                try:
                                    if self._callback_api_version == CallbackAPIVersion.VERSION1:
                                        on_publish = cast(CallbackOnPublish_v1, on_publish)

                                        on_publish(self, self._userdata, packet["mid"])
                                    elif self._callback_api_version == CallbackAPIVersion.VERSION2:
                                        on_publish = cast(CallbackOnPublish_v2, on_publish)

                                        on_publish(
                                            self,
                                            self._userdata,
                                            packet["mid"],
                                            ReasonCode(PacketTypes.PUBACK),
                                            Properties(PacketTypes.PUBACK),
                                        )
                                    else:
                                        raise RuntimeError("Unsupported callback API version")
                                except Exception as err:
                                    self._easy_log(
                                        MQTT_LOG_ERR, 'Caught exception in on_publish: %s', err)
                                    if not self.suppress_exceptions:
                                        raise

                        # TODO: Something is odd here. I don't see why packet["info"] can't be None.
                        # A packet could be produced by _handle_connack with qos=0 and no info
                        # (around line 3645). Ignore the mypy check for now but I feel there is a bug
                        # somewhere.
                        packet['info']._set_as_published()  # type: ignore

                    if (packet['command'] & 0xF0) == DISCONNECT:
                        with self._msgtime_mutex:
                            self._last_msg_out = time_func()

                        self._do_on_disconnect(
                            packet_from_broker=False,
                            v1_rc=MQTTErrorCode.MQTT_ERR_SUCCESS,
                        )
                        self._sock_close()
                        # Only change to disconnected if the disconnection was wanted
                        # by the client (== state was disconnecting). If the broker disconnected
                        # use unilaterally don't change the state and client may reconnect.
                        if self._state == _ConnectionState.MQTT_CS_DISCONNECTING:
                            self._state = _ConnectionState.MQTT_CS_DISCONNECTED
                        return MQTTErrorCode.MQTT_ERR_SUCCESS

                else:
                    # We haven't finished with this packet
                    self._out_packet.appendleft(packet)
            else:
                break

        with self._msgtime_mutex:
            self._last_msg_out = time_func()

        return MQTTErrorCode.MQTT_ERR_SUCCESS

    def _easy_log(self, level: LogLevel, fmt: str, *args: Any) -> None:
        if self.on_log is not None:
            buf = fmt % args
            try:
                self.on_log(self, self._userdata, level, buf)
            except Exception:  # noqa: S110
                # Can't _easy_log this, as we'll recurse until we break
                pass  # self._logger will pick this up, so we're fine
        if self._logger is not None:
            level_std = LOGGING_LEVEL[level]
            self._logger.log(level_std, fmt, *args)

    def _check_keepalive(self) -> None:
        if self._keepalive == 0:
            return

        now = time_func()

        with self._msgtime_mutex:
            last_msg_out = self._last_msg_out
            last_msg_in = self._last_msg_in

        if self._sock is not None and (now - last_msg_out >= self._keepalive or now - last_msg_in >= self._keepalive):
            if self._state == _ConnectionState.MQTT_CS_CONNECTED and self._ping_t == 0:
                try:
                    self._send_pingreq()
                except Exception:
                    self._sock_close()
                    self._do_on_disconnect(
                        packet_from_broker=False,
                        v1_rc=MQTTErrorCode.MQTT_ERR_CONN_LOST,
                    )
                else:
                    with self._msgtime_mutex:
                        self._last_msg_out = now
                        self._last_msg_in = now
            else:
                self._sock_close()

                if self._state in (_ConnectionState.MQTT_CS_DISCONNECTING, _ConnectionState.MQTT_CS_DISCONNECTED):
                    self._state = _ConnectionState.MQTT_CS_DISCONNECTED
                    rc = MQTTErrorCode.MQTT_ERR_SUCCESS
                else:
                    rc = MQTTErrorCode.MQTT_ERR_KEEPALIVE

                self._do_on_disconnect(
                    packet_from_broker=False,
                    v1_rc=rc,
                )

    def _mid_generate(self) -> int:
        with self._mid_generate_mutex:
            self._last_mid += 1
            if self._last_mid == 65536:
                self._last_mid = 1
            return self._last_mid

    @staticmethod
    def _raise_for_invalid_topic(topic: bytes) -> None:
        """ Check if the topic is a topic without wildcard and valid length.

            Raise ValueError if the topic isn't valid.
        """
        if b'+' in topic or b'#' in topic:
            raise ValueError('Publish topic cannot contain wildcards.')
        if len(topic) > 65535:
            raise ValueError('Publish topic is too long.')

    @staticmethod
    def _filter_wildcard_len_check(sub: bytes) -> MQTTErrorCode:
        if (len(sub) == 0 or len(sub) > 65535
            or any(b'+' in p or b'#' in p for p in sub.split(b'/') if len(p) > 1)
                or b'#/' in sub):
            return MQTTErrorCode.MQTT_ERR_INVAL
        else:
            return MQTTErrorCode.MQTT_ERR_SUCCESS

    def _send_pingreq(self) -> MQTTErrorCode:
        self._easy_log(MQTT_LOG_DEBUG, "Sending PINGREQ")
        rc = self._send_simple_command(PINGREQ)
        if rc == MQTTErrorCode.MQTT_ERR_SUCCESS:
            self._ping_t = time_func()
        return rc

    def _send_pingresp(self) -> MQTTErrorCode:
        self._easy_log(MQTT_LOG_DEBUG, "Sending PINGRESP")
        return self._send_simple_command(PINGRESP)

    def _send_puback(self, mid: int) -> MQTTErrorCode:
        self._easy_log(MQTT_LOG_DEBUG, "Sending PUBACK (Mid: %d)", mid)
        return self._send_command_with_mid(PUBACK, mid, False)

    def _send_pubcomp(self, mid: int) -> MQTTErrorCode:
        self._easy_log(MQTT_LOG_DEBUG, "Sending PUBCOMP (Mid: %d)", mid)
        return self._send_command_with_mid(PUBCOMP, mid, False)

    def _pack_remaining_length(
        self, packet: bytearray, remaining_length: int
    ) -> bytearray:
        remaining_bytes = []
        while True:
            byte = remaining_length % 128
            remaining_length = remaining_length // 128
            # If there are more digits to encode, set the top bit of this digit
            if remaining_length > 0:
                byte |= 0x80

            remaining_bytes.append(byte)
            packet.append(byte)
            if remaining_length == 0:
                # FIXME - this doesn't deal with incorrectly large payloads
                return packet

    def _pack_str16(self, packet: bytearray, data: bytes | str) -> None:
        data = _force_bytes(data)
        packet.extend(struct.pack("!H", len(data)))
        packet.extend(data)

    def _send_publish(
        self,
        mid: int,
        topic: bytes,
        payload: bytes|bytearray = b"",
        qos: int = 0,
        retain: bool = False,
        dup: bool = False,
        info: MQTTMessageInfo | None = None,
        properties: Properties | None = None,
    ) -> MQTTErrorCode:
        # we assume that topic and payload are already properly encoded
        if not isinstance(topic, bytes):
            raise TypeError('topic must be bytes, not str')
        if payload and not isinstance(payload, (bytes, bytearray)):
            raise TypeError('payload must be bytes if set')

        if self._sock is None:
            return MQTTErrorCode.MQTT_ERR_NO_CONN

        command = PUBLISH | ((dup & 0x1) << 3) | (qos << 1) | retain
        packet = bytearray()
        packet.append(command)

        payloadlen = len(payload)
        remaining_length = 2 + len(topic) + payloadlen

        if payloadlen == 0:
            if self._protocol == MQTTv5:
                self._easy_log(
                    MQTT_LOG_DEBUG,
                    "Sending PUBLISH (d%d, q%d, r%d, m%d), '%s', properties=%s (NULL payload)",
                    dup, qos, retain, mid, topic, properties
                )
            else:
                self._easy_log(
                    MQTT_LOG_DEBUG,
                    "Sending PUBLISH (d%d, q%d, r%d, m%d), '%s' (NULL payload)",
                    dup, qos, retain, mid, topic
                )
        else:
            if self._protocol == MQTTv5:
                self._easy_log(
                    MQTT_LOG_DEBUG,
                    "Sending PUBLISH (d%d, q%d, r%d, m%d), '%s', properties=%s, ... (%d bytes)",
                    dup, qos, retain, mid, topic, properties, payloadlen
                )
            else:
                self._easy_log(
                    MQTT_LOG_DEBUG,
                    "Sending PUBLISH (d%d, q%d, r%d, m%d), '%s', ... (%d bytes)",
                    dup, qos, retain, mid, topic, payloadlen
                )

        if qos > 0:
            # For message id
            remaining_length += 2

        if self._protocol == MQTTv5:
            if properties is None:
                packed_properties = b'\x00'
            else:
                packed_properties = properties.pack()
            remaining_length += len(packed_properties)

        self._pack_remaining_length(packet, remaining_length)
        self._pack_str16(packet, topic)

        if qos > 0:
            # For message id
            packet.extend(struct.pack("!H", mid))

        if self._protocol == MQTTv5:
            packet.extend(packed_properties)

        packet.extend(payload)

        return self._packet_queue(PUBLISH, packet, mid, qos, info)

    def _send_pubrec(self, mid: int) -> MQTTErrorCode:
        self._easy_log(MQTT_LOG_DEBUG, "Sending PUBREC (Mid: %d)", mid)
        return self._send_command_with_mid(PUBREC, mid, False)

    def _send_pubrel(self, mid: int) -> MQTTErrorCode:
        self._easy_log(MQTT_LOG_DEBUG, "Sending PUBREL (Mid: %d)", mid)
        return self._send_command_with_mid(PUBREL | 2, mid, False)

    def _send_command_with_mid(self, command: int, mid: int, dup: int) -> MQTTErrorCode:
        # For PUBACK, PUBCOMP, PUBREC, and PUBREL
        if dup:
            command |= 0x8

        remaining_length = 2
        packet = struct.pack('!BBH', command, remaining_length, mid)
        return self._packet_queue(command, packet, mid, 1)

    def _send_simple_command(self, command: int) -> MQTTErrorCode:
        # For DISCONNECT, PINGREQ and PINGRESP
        remaining_length = 0
        packet = struct.pack('!BB', command, remaining_length)
        return self._packet_queue(command, packet, 0, 0)

    def _send_connect(self, keepalive: int) -> MQTTErrorCode:
        proto_ver = int(self._protocol)
        # hard-coded UTF-8 encoded string
        protocol = b"MQTT" if proto_ver >= MQTTv311 else b"MQIsdp"

        remaining_length = 2 + len(protocol) + 1 + \
            1 + 2 + 2 + len(self._client_id)

        connect_flags = 0
        if self._protocol == MQTTv5:
            if self._clean_start is True:
                connect_flags |= 0x02
            elif self._clean_start == MQTT_CLEAN_START_FIRST_ONLY and self._mqttv5_first_connect:
                connect_flags |= 0x02
        elif self._clean_session:
            connect_flags |= 0x02

        if self._will:
            remaining_length += 2 + \
                len(self._will_topic) + 2 + len(self._will_payload)
            connect_flags |= 0x04 | ((self._will_qos & 0x03) << 3) | (
                (self._will_retain & 0x01) << 5)

        if self._username is not None:
            remaining_length += 2 + len(self._username)
            connect_flags |= 0x80
            if self._password is not None:
                connect_flags |= 0x40
                remaining_length += 2 + len(self._password)

        if self._protocol == MQTTv5:
            if self._connect_properties is None:
                packed_connect_properties = b'\x00'
            else:
                packed_connect_properties = self._connect_properties.pack()
            remaining_length += len(packed_connect_properties)
            if self._will:
                if self._will_properties is None:
                    packed_will_properties = b'\x00'
                else:
                    packed_will_properties = self._will_properties.pack()
                remaining_length += len(packed_will_properties)

        command = CONNECT
        packet = bytearray()
        packet.append(command)

        # as per the mosquitto broker, if the MSB of this version is set
        # to 1, then it treats the connection as a bridge
        if self._client_mode == MQTT_BRIDGE:
            proto_ver |= 0x80

        self._pack_remaining_length(packet, remaining_length)
        packet.extend(struct.pack(
            f"!H{len(protocol)}sBBH",
            len(protocol), protocol, proto_ver, connect_flags, keepalive,
        ))

        if self._protocol == MQTTv5:
            packet += packed_connect_properties

        self._pack_str16(packet, self._client_id)

        if self._will:
            if self._protocol == MQTTv5:
                packet += packed_will_properties
            self._pack_str16(packet, self._will_topic)
            self._pack_str16(packet, self._will_payload)

        if self._username is not None:
            self._pack_str16(packet, self._username)

            if self._password is not None:
                self._pack_str16(packet, self._password)

        self._keepalive = keepalive
        if self._protocol == MQTTv5:
            self._easy_log(
                MQTT_LOG_DEBUG,
                "Sending CONNECT (u%d, p%d, wr%d, wq%d, wf%d, c%d, k%d) client_id=%s properties=%s",
                (connect_flags & 0x80) >> 7,
                (connect_flags & 0x40) >> 6,
                (connect_flags & 0x20) >> 5,
                (connect_flags & 0x18) >> 3,
                (connect_flags & 0x4) >> 2,
                (connect_flags & 0x2) >> 1,
                keepalive,
                self._client_id,
                self._connect_properties
            )
        else:
            self._easy_log(
                MQTT_LOG_DEBUG,
                "Sending CONNECT (u%d, p%d, wr%d, wq%d, wf%d, c%d, k%d) client_id=%s",
                (connect_flags & 0x80) >> 7,
                (connect_flags & 0x40) >> 6,
                (connect_flags & 0x20) >> 5,
                (connect_flags & 0x18) >> 3,
                (connect_flags & 0x4) >> 2,
                (connect_flags & 0x2) >> 1,
                keepalive,
                self._client_id
            )
        return self._packet_queue(command, packet, 0, 0)

    def _send_disconnect(
        self,
        reasoncode: ReasonCode | None = None,
        properties: Properties | None = None,
    ) -> MQTTErrorCode:
        if self._protocol == MQTTv5:
            self._easy_log(MQTT_LOG_DEBUG, "Sending DISCONNECT reasonCode=%s properties=%s",
                           reasoncode,
                           properties
                           )
        else:
            self._easy_log(MQTT_LOG_DEBUG, "Sending DISCONNECT")

        remaining_length = 0

        command = DISCONNECT
        packet = bytearray()
        packet.append(command)

        if self._protocol == MQTTv5:
            if properties is not None or reasoncode is not None:
                if reasoncode is None:
                    reasoncode = ReasonCode(DISCONNECT >> 4, identifier=0)
                remaining_length += 1
                if properties is not None:
                    packed_props = properties.pack()
                    remaining_length += len(packed_props)

        self._pack_remaining_length(packet, remaining_length)

        if self._protocol == MQTTv5:
            if reasoncode is not None:
                packet += reasoncode.pack()
                if properties is not None:
                    packet += packed_props

        return self._packet_queue(command, packet, 0, 0)

    def _send_subscribe(
        self,
        dup: int,
        topics: Sequence[tuple[bytes, SubscribeOptions | int]],
        properties: Properties | None = None,
    ) -> tuple[MQTTErrorCode, int]:
        remaining_length = 2
        if self._protocol == MQTTv5:
            if properties is None:
                packed_subscribe_properties = b'\x00'
            else:
                packed_subscribe_properties = properties.pack()
            remaining_length += len(packed_subscribe_properties)
        for t, _ in topics:
            remaining_length += 2 + len(t) + 1

        command = SUBSCRIBE | (dup << 3) | 0x2
        packet = bytearray()
        packet.append(command)
        self._pack_remaining_length(packet, remaining_length)
        local_mid = self._mid_generate()
        packet.extend(struct.pack("!H", local_mid))

        if self._protocol == MQTTv5:
            packet += packed_subscribe_properties

        for t, q in topics:
            self._pack_str16(packet, t)
            if self._protocol == MQTTv5:
                packet += q.pack()  # type: ignore
            else:
                packet.append(q)  # type: ignore

        self._easy_log(
            MQTT_LOG_DEBUG,
            "Sending SUBSCRIBE (d%d, m%d) %s",
            dup,
            local_mid,
            topics,
        )
        return (self._packet_queue(command, packet, local_mid, 1), local_mid)

    def _send_unsubscribe(
        self,
        dup: int,
        topics: list[bytes],
        properties: Properties | None = None,
    ) -> tuple[MQTTErrorCode, int]:
        remaining_length = 2
        if self._protocol == MQTTv5:
            if properties is None:
                packed_unsubscribe_properties = b'\x00'
            else:
                packed_unsubscribe_properties = properties.pack()
            remaining_length += len(packed_unsubscribe_properties)
        for t in topics:
            remaining_length += 2 + len(t)

        command = UNSUBSCRIBE | (dup << 3) | 0x2
        packet = bytearray()
        packet.append(command)
        self._pack_remaining_length(packet, remaining_length)
        local_mid = self._mid_generate()
        packet.extend(struct.pack("!H", local_mid))

        if self._protocol == MQTTv5:
            packet += packed_unsubscribe_properties

        for t in topics:
            self._pack_str16(packet, t)

        # topics_repr = ", ".join("'"+topic.decode('utf8')+"'" for topic in topics)
        if self._protocol == MQTTv5:
            self._easy_log(
                MQTT_LOG_DEBUG,
                "Sending UNSUBSCRIBE (d%d, m%d) %s %s",
                dup,
                local_mid,
                properties,
                topics,
            )
        else:
            self._easy_log(
                MQTT_LOG_DEBUG,
                "Sending UNSUBSCRIBE (d%d, m%d) %s",
                dup,
                local_mid,
                topics,
            )
        return (self._packet_queue(command, packet, local_mid, 1), local_mid)

    def _check_clean_session(self) -> bool:
        if self._protocol == MQTTv5:
            if self._clean_start == MQTT_CLEAN_START_FIRST_ONLY:
                return self._mqttv5_first_connect
            else:
                return self._clean_start  # type: ignore
        else:
            return self._clean_session

    def _messages_reconnect_reset_out(self) -> None:
        with self._out_message_mutex:
            self._inflight_messages = 0
            for m in self._out_messages.values():
                m.timestamp = 0
                if self._max_inflight_messages == 0 or self._inflight_messages < self._max_inflight_messages:
                    if m.qos == 0:
                        m.state = mqtt_ms_publish
                    elif m.qos == 1:
                        # self._inflight_messages = self._inflight_messages + 1
                        if m.state == mqtt_ms_wait_for_puback:
                            m.dup = True
                        m.state = mqtt_ms_publish
                    elif m.qos == 2:
                        # self._inflight_messages = self._inflight_messages + 1
                        if self._check_clean_session():
                            if m.state != mqtt_ms_publish:
                                m.dup = True
                            m.state = mqtt_ms_publish
                        else:
                            if m.state == mqtt_ms_wait_for_pubcomp:
                                m.state = mqtt_ms_resend_pubrel
                            else:
                                if m.state == mqtt_ms_wait_for_pubrec:
                                    m.dup = True
                                m.state = mqtt_ms_publish
                else:
                    m.state = mqtt_ms_queued

    def _messages_reconnect_reset_in(self) -> None:
        with self._in_message_mutex:
            if self._check_clean_session():
                self._in_messages = collections.OrderedDict()
                return
            for m in self._in_messages.values():
                m.timestamp = 0
                if m.qos != 2:
                    self._in_messages.pop(m.mid)
                else:
                    # Preserve current state
                    pass

    def _messages_reconnect_reset(self) -> None:
        self._messages_reconnect_reset_out()
        self._messages_reconnect_reset_in()

    def _packet_queue(
        self,
        command: int,
        packet: bytes,
        mid: int,
        qos: int,
        info: MQTTMessageInfo | None = None,
    ) -> MQTTErrorCode:
        mpkt: _OutPacket = {
            "command": command,
            "mid": mid,
            "qos": qos,
            "pos": 0,
            "to_process": len(packet),
            "packet": packet,
            "info": info,
        }

        self._out_packet.append(mpkt)

        # Write a single byte to sockpairW (connected to sockpairR) to break
        # out of select() if in threaded mode.
        if self._sockpairW is not None:
            try:
                self._sockpairW.send(sockpair_data)
            except BlockingIOError:
                pass

        # If we have an external event loop registered, use that instead
        # of calling loop_write() directly.
        if self._thread is None and self._on_socket_register_write is None:
            if self._in_callback_mutex.acquire(False):
                self._in_callback_mutex.release()
                return self.loop_write()

        self._call_socket_register_write()

        return MQTTErrorCode.MQTT_ERR_SUCCESS

    def _packet_handle(self) -> MQTTErrorCode:
        cmd = self._in_packet['command'] & 0xF0
        if cmd == PINGREQ:
            return self._handle_pingreq()
        elif cmd == PINGRESP:
            return self._handle_pingresp()
        elif cmd == PUBACK:
            return self._handle_pubackcomp("PUBACK")
        elif cmd == PUBCOMP:
            return self._handle_pubackcomp("PUBCOMP")
        elif cmd == PUBLISH:
            return self._handle_publish()
        elif cmd == PUBREC:
            return self._handle_pubrec()
        elif cmd == PUBREL:
            return self._handle_pubrel()
        elif cmd == CONNACK:
            return self._handle_connack()
        elif cmd == SUBACK:
            self._handle_suback()
            return MQTTErrorCode.MQTT_ERR_SUCCESS
        elif cmd == UNSUBACK:
            return self._handle_unsuback()
        elif cmd == DISCONNECT and self._protocol == MQTTv5:  # only allowed in MQTT 5.0
            self._handle_disconnect()
            return MQTTErrorCode.MQTT_ERR_SUCCESS
        else:
            # If we don't recognise the command, return an error straight away.
            self._easy_log(MQTT_LOG_ERR, "Error: Unrecognised command %s", cmd)
            return MQTTErrorCode.MQTT_ERR_PROTOCOL

    def _handle_pingreq(self) -> MQTTErrorCode:
        if self._in_packet['remaining_length'] != 0:
            return MQTTErrorCode.MQTT_ERR_PROTOCOL

        self._easy_log(MQTT_LOG_DEBUG, "Received PINGREQ")
        return self._send_pingresp()

    def _handle_pingresp(self) -> MQTTErrorCode:
        if self._in_packet['remaining_length'] != 0:
            return MQTTErrorCode.MQTT_ERR_PROTOCOL

        # No longer waiting for a PINGRESP.
        self._ping_t = 0
        self._easy_log(MQTT_LOG_DEBUG, "Received PINGRESP")
        return MQTTErrorCode.MQTT_ERR_SUCCESS

    def _handle_connack(self) -> MQTTErrorCode:
        if self._protocol == MQTTv5:
            if self._in_packet['remaining_length'] < 2:
                return MQTTErrorCode.MQTT_ERR_PROTOCOL
        elif self._in_packet['remaining_length'] != 2:
            return MQTTErrorCode.MQTT_ERR_PROTOCOL

        if self._protocol == MQTTv5:
            (flags, result) = struct.unpack(
                "!BB", self._in_packet['packet'][:2])
            if result == 1:
                # This is probably a failure from a broker that doesn't support
                # MQTT v5.
                reason = ReasonCode(CONNACK >> 4, aName="Unsupported protocol version")
                properties = None
            else:
                reason = ReasonCode(CONNACK >> 4, identifier=result)
                properties = Properties(CONNACK >> 4)
                properties.unpack(self._in_packet['packet'][2:])
        else:
            (flags, result) = struct.unpack("!BB", self._in_packet['packet'])
            reason = convert_connack_rc_to_reason_code(result)
            properties = None
        if self._protocol == MQTTv311:
            if result == CONNACK_REFUSED_PROTOCOL_VERSION:
                if not self._reconnect_on_failure:
                    return MQTT_ERR_PROTOCOL
                self._easy_log(
                    MQTT_LOG_DEBUG,
                    "Received CONNACK (%s, %s), attempting downgrade to MQTT v3.1.",
                    flags, result
                )
                # Downgrade to MQTT v3.1
                self._protocol = MQTTv31
                return self.reconnect()
            elif (result == CONNACK_REFUSED_IDENTIFIER_REJECTED
                    and self._client_id == b''):
                if not self._reconnect_on_failure:
                    return MQTT_ERR_PROTOCOL
                self._easy_log(
                    MQTT_LOG_DEBUG,
                    "Received CONNACK (%s, %s), attempting to use non-empty CID",
                    flags, result,
                )
                self._client_id = _base62(uuid.uuid4().int, padding=22).encode("utf8")
                return self.reconnect()

        if result == 0:
            self._state = _ConnectionState.MQTT_CS_CONNECTED
            self._reconnect_delay = None

        if self._protocol == MQTTv5:
            self._easy_log(
                MQTT_LOG_DEBUG, "Received CONNACK (%s, %s) properties=%s", flags, reason, properties)
        else:
            self._easy_log(
                MQTT_LOG_DEBUG, "Received CONNACK (%s, %s)", flags, result)

        # it won't be the first successful connect any more
        self._mqttv5_first_connect = False

        with self._callback_mutex:
            on_connect = self.on_connect

        if on_connect:
            flags_dict = {}
            flags_dict['session present'] = flags & 0x01
            with self._in_callback_mutex:
                try:
                    if self._callback_api_version == CallbackAPIVersion.VERSION1:
                        if self._protocol == MQTTv5:
                            on_connect = cast(CallbackOnConnect_v1_mqtt5, on_connect)

                            on_connect(self, self._userdata,
                                            flags_dict, reason, properties)
                        else:
                            on_connect = cast(CallbackOnConnect_v1_mqtt3, on_connect)

                            on_connect(
                                self, self._userdata, flags_dict, result)
                    elif self._callback_api_version == CallbackAPIVersion.VERSION2:
                        on_connect = cast(CallbackOnConnect_v2, on_connect)

                        connect_flags = ConnectFlags(
                            session_present=flags_dict['session present'] > 0
                        )

                        if properties is None:
                            properties = Properties(PacketTypes.CONNACK)

                        on_connect(
                            self,
                            self._userdata,
                            connect_flags,
                            reason,
                            properties,
                        )
                    else:
                        raise RuntimeError("Unsupported callback API version")
                except Exception as err:
                    self._easy_log(
                        MQTT_LOG_ERR, 'Caught exception in on_connect: %s', err)
                    if not self.suppress_exceptions:
                        raise

        if result == 0:
            rc = MQTTErrorCode.MQTT_ERR_SUCCESS
            with self._out_message_mutex:
                for m in self._out_messages.values():
                    m.timestamp = time_func()
                    if m.state == mqtt_ms_queued:
                        self.loop_write()  # Process outgoing messages that have just been queued up
                        return MQTT_ERR_SUCCESS

                    if m.qos == 0:
                        with self._in_callback_mutex:  # Don't call loop_write after _send_publish()
                            rc = self._send_publish(
                                m.mid,
                                m.topic.encode('utf-8'),
                                m.payload,
                                m.qos,
                                m.retain,
                                m.dup,
                                properties=m.properties
                            )
                        if rc != MQTTErrorCode.MQTT_ERR_SUCCESS:
                            return rc
                    elif m.qos == 1:
                        if m.state == mqtt_ms_publish:
                            self._inflight_messages += 1
                            m.state = mqtt_ms_wait_for_puback
                            with self._in_callback_mutex:  # Don't call loop_write after _send_publish()
                                rc = self._send_publish(
                                    m.mid,
                                    m.topic.encode('utf-8'),
                                    m.payload,
                                    m.qos,
                                    m.retain,
                                    m.dup,
                                    properties=m.properties
                                )
                            if rc != MQTTErrorCode.MQTT_ERR_SUCCESS:
                                return rc
                    elif m.qos == 2:
                        if m.state == mqtt_ms_publish:
                            self._inflight_messages += 1
                            m.state = mqtt_ms_wait_for_pubrec
                            with self._in_callback_mutex:  # Don't call loop_write after _send_publish()
                                rc = self._send_publish(
                                    m.mid,
                                    m.topic.encode('utf-8'),
                                    m.payload,
                                    m.qos,
                                    m.retain,
                                    m.dup,
                                    properties=m.properties
                                )
                            if rc != MQTTErrorCode.MQTT_ERR_SUCCESS:
                                return rc
                        elif m.state == mqtt_ms_resend_pubrel:
                            self._inflight_messages += 1
                            m.state = mqtt_ms_wait_for_pubcomp
                            with self._in_callback_mutex:  # Don't call loop_write after _send_publish()
                                rc = self._send_pubrel(m.mid)
                            if rc != MQTTErrorCode.MQTT_ERR_SUCCESS:
                                return rc
                    self.loop_write()  # Process outgoing messages that have just been queued up

            return rc
        elif result > 0 and result < 6:
            return MQTTErrorCode.MQTT_ERR_CONN_REFUSED
        else:
            return MQTTErrorCode.MQTT_ERR_PROTOCOL

    def _handle_disconnect(self) -> None:
        packet_type = DISCONNECT >> 4
        reasonCode = properties = None
        if self._in_packet['remaining_length'] > 2:
            reasonCode = ReasonCode(packet_type)
            reasonCode.unpack(self._in_packet['packet'])
            if self._in_packet['remaining_length'] > 3:
                properties = Properties(packet_type)
                props, props_len = properties.unpack(
                    self._in_packet['packet'][1:])
        self._easy_log(MQTT_LOG_DEBUG, "Received DISCONNECT %s %s",
                       reasonCode,
                       properties
                       )

        self._sock_close()
        self._do_on_disconnect(
            packet_from_broker=True,
            v1_rc=MQTTErrorCode.MQTT_ERR_SUCCESS,  # If reason is absent (remaining length < 1), it means normal disconnection
            reason=reasonCode,
            properties=properties,
        )

    def _handle_suback(self) -> None:
        self._easy_log(MQTT_LOG_DEBUG, "Received SUBACK")
        pack_format = f"!H{len(self._in_packet['packet']) - 2}s"
        (mid, packet) = struct.unpack(pack_format, self._in_packet['packet'])

        if self._protocol == MQTTv5:
            properties = Properties(SUBACK >> 4)
            props, props_len = properties.unpack(packet)
            reasoncodes = [ReasonCode(SUBACK >> 4, identifier=c) for c in packet[props_len:]]
        else:
            pack_format = f"!{'B' * len(packet)}"
            granted_qos = struct.unpack(pack_format, packet)
            reasoncodes = [ReasonCode(SUBACK >> 4, identifier=c) for c in granted_qos]
            properties = Properties(SUBACK >> 4)

        with self._callback_mutex:
            on_subscribe = self.on_subscribe

        if on_subscribe:
            with self._in_callback_mutex:  # Don't call loop_write after _send_publish()
                try:
                    if self._callback_api_version == CallbackAPIVersion.VERSION1:
                        if self._protocol == MQTTv5:
                            on_subscribe = cast(CallbackOnSubscribe_v1_mqtt5, on_subscribe)

                            on_subscribe(
                                self, self._userdata, mid, reasoncodes, properties)
                        else:
                            on_subscribe = cast(CallbackOnSubscribe_v1_mqtt3, on_subscribe)

                            on_subscribe(
                                self, self._userdata, mid, granted_qos)
                    elif self._callback_api_version == CallbackAPIVersion.VERSION2:
                        on_subscribe = cast(CallbackOnSubscribe_v2, on_subscribe)

                        on_subscribe(
                            self,
                            self._userdata,
                            mid,
                            reasoncodes,
                            properties,
                        )
                    else:
                        raise RuntimeError("Unsupported callback API version")
                except Exception as err:
                    self._easy_log(
                        MQTT_LOG_ERR, 'Caught exception in on_subscribe: %s', err)
                    if not self.suppress_exceptions:
                        raise

    def _handle_publish(self) -> MQTTErrorCode:
        header = self._in_packet['command']
        message = MQTTMessage()
        message.dup = ((header & 0x08) >> 3) != 0
        message.qos = (header & 0x06) >> 1
        message.retain = (header & 0x01) != 0

        pack_format = f"!H{len(self._in_packet['packet']) - 2}s"
        (slen, packet) = struct.unpack(pack_format, self._in_packet['packet'])
        pack_format = f"!{slen}s{len(packet) - slen}s"
        (topic, packet) = struct.unpack(pack_format, packet)

        if self._protocol != MQTTv5 and len(topic) == 0:
            return MQTTErrorCode.MQTT_ERR_PROTOCOL

        # Handle topics with invalid UTF-8
        # This replaces an invalid topic with a message and the hex
        # representation of the topic for logging. When the user attempts to
        # access message.topic in the callback, an exception will be raised.
        try:
            print_topic = topic.decode('utf-8')
        except UnicodeDecodeError:
            print_topic = f"TOPIC WITH INVALID UTF-8: {topic!r}"

        message.topic = topic

        if message.qos > 0:
            pack_format = f"!H{len(packet) - 2}s"
            (message.mid, packet) = struct.unpack(pack_format, packet)

        if self._protocol == MQTTv5:
            message.properties = Properties(PUBLISH >> 4)
            props, props_len = message.properties.unpack(packet)
            packet = packet[props_len:]

        message.payload = packet

        if self._protocol == MQTTv5:
            self._easy_log(
                MQTT_LOG_DEBUG,
                "Received PUBLISH (d%d, q%d, r%d, m%d), '%s', properties=%s, ...  (%d bytes)",
                message.dup, message.qos, message.retain, message.mid,
                print_topic, message.properties, len(message.payload)
            )
        else:
            self._easy_log(
                MQTT_LOG_DEBUG,
                "Received PUBLISH (d%d, q%d, r%d, m%d), '%s', ...  (%d bytes)",
                message.dup, message.qos, message.retain, message.mid,
                print_topic, len(message.payload)
            )

        message.timestamp = time_func()
        if message.qos == 0:
            self._handle_on_message(message)
            return MQTTErrorCode.MQTT_ERR_SUCCESS
        elif message.qos == 1:
            self._handle_on_message(message)
            if self._manual_ack:
                return MQTTErrorCode.MQTT_ERR_SUCCESS
            else:
                return self._send_puback(message.mid)
        elif message.qos == 2:

            rc = self._send_pubrec(message.mid)

            message.state = mqtt_ms_wait_for_pubrel
            with self._in_message_mutex:
                self._in_messages[message.mid] = message

            return rc
        else:
            return MQTTErrorCode.MQTT_ERR_PROTOCOL

    def ack(self, mid: int, qos: int) -> MQTTErrorCode:
        """
           send an acknowledgement for a given message id (stored in :py:attr:`message.mid <MQTTMessage.mid>`).
           only useful in QoS>=1 and ``manual_ack=True`` (option of `Client`)
        """
        if self._manual_ack :
            if qos == 1:
                return self._send_puback(mid)
            elif qos == 2:
                return self._send_pubcomp(mid)

        return MQTTErrorCode.MQTT_ERR_SUCCESS

    def manual_ack_set(self, on: bool) -> None:
        """
           The paho library normally acknowledges messages as soon as they are delivered to the caller.
           If manual_ack is turned on, then the caller MUST manually acknowledge every message once
           application processing is complete using `ack()`
        """
        self._manual_ack = on


    def _handle_pubrel(self) -> MQTTErrorCode:
        if self._protocol == MQTTv5:
            if self._in_packet['remaining_length'] < 2:
                return MQTTErrorCode.MQTT_ERR_PROTOCOL
        elif self._in_packet['remaining_length'] != 2:
            return MQTTErrorCode.MQTT_ERR_PROTOCOL

        mid, = struct.unpack("!H", self._in_packet['packet'][:2])
        if self._protocol == MQTTv5:
            if self._in_packet['remaining_length'] > 2:
                reasonCode = ReasonCode(PUBREL >> 4)
                reasonCode.unpack(self._in_packet['packet'][2:])
                if self._in_packet['remaining_length'] > 3:
                    properties = Properties(PUBREL >> 4)
                    props, props_len = properties.unpack(
                        self._in_packet['packet'][3:])
        self._easy_log(MQTT_LOG_DEBUG, "Received PUBREL (Mid: %d)", mid)

        with self._in_message_mutex:
            if mid in self._in_messages:
                # Only pass the message on if we have removed it from the queue - this
                # prevents multiple callbacks for the same message.
                message = self._in_messages.pop(mid)
                self._handle_on_message(message)
                self._inflight_messages -= 1
                if self._max_inflight_messages > 0:
                    with self._out_message_mutex:
                        rc = self._update_inflight()
                    if rc != MQTTErrorCode.MQTT_ERR_SUCCESS:
                        return rc

        # FIXME: this should only be done if the message is known
        # If unknown it's a protocol error and we should close the connection.
        # But since we don't have (on disk) persistence for the session, it
        # is possible that we must known about this message.
        # Choose to acknowledge this message (thus losing a message) but
        # avoid hanging. See #284.
        if self._manual_ack:
            return MQTTErrorCode.MQTT_ERR_SUCCESS
        else:
            return self._send_pubcomp(mid)

    def _update_inflight(self) -> MQTTErrorCode:
        # Dont lock message_mutex here
        for m in self._out_messages.values():
            if self._inflight_messages < self._max_inflight_messages:
                if m.qos > 0 and m.state == mqtt_ms_queued:
                    self._inflight_messages += 1
                    if m.qos == 1:
                        m.state = mqtt_ms_wait_for_puback
                    elif m.qos == 2:
                        m.state = mqtt_ms_wait_for_pubrec
                    rc = self._send_publish(
                        m.mid,
                        m.topic.encode('utf-8'),
                        m.payload,
                        m.qos,
                        m.retain,
                        m.dup,
                        properties=m.properties,
                    )
                    if rc != MQTTErrorCode.MQTT_ERR_SUCCESS:
                        return rc
            else:
                return MQTTErrorCode.MQTT_ERR_SUCCESS
        return MQTTErrorCode.MQTT_ERR_SUCCESS

    def _handle_pubrec(self) -> MQTTErrorCode:
        if self._protocol == MQTTv5:
            if self._in_packet['remaining_length'] < 2:
                return MQTTErrorCode.MQTT_ERR_PROTOCOL
        elif self._in_packet['remaining_length'] != 2:
            return MQTTErrorCode.MQTT_ERR_PROTOCOL

        mid, = struct.unpack("!H", self._in_packet['packet'][:2])
        if self._protocol == MQTTv5:
            if self._in_packet['remaining_length'] > 2:
                reasonCode = ReasonCode(PUBREC >> 4)
                reasonCode.unpack(self._in_packet['packet'][2:])
                if self._in_packet['remaining_length'] > 3:
                    properties = Properties(PUBREC >> 4)
                    props, props_len = properties.unpack(
                        self._in_packet['packet'][3:])
        self._easy_log(MQTT_LOG_DEBUG, "Received PUBREC (Mid: %d)", mid)

        with self._out_message_mutex:
            if mid in self._out_messages:
                msg = self._out_messages[mid]
                msg.state = mqtt_ms_wait_for_pubcomp
                msg.timestamp = time_func()
                return self._send_pubrel(mid)

        return MQTTErrorCode.MQTT_ERR_SUCCESS

    def _handle_unsuback(self) -> MQTTErrorCode:
        if self._protocol == MQTTv5:
            if self._in_packet['remaining_length'] < 4:
                return MQTTErrorCode.MQTT_ERR_PROTOCOL
        elif self._in_packet['remaining_length'] != 2:
            return MQTTErrorCode.MQTT_ERR_PROTOCOL

        mid, = struct.unpack("!H", self._in_packet['packet'][:2])
        if self._protocol == MQTTv5:
            packet = self._in_packet['packet'][2:]
            properties = Properties(UNSUBACK >> 4)
            props, props_len = properties.unpack(packet)
            reasoncodes_list = [
                ReasonCode(UNSUBACK >> 4, identifier=c)
                for c in packet[props_len:]
            ]
        else:
            reasoncodes_list = []
            properties = Properties(UNSUBACK >> 4)

        self._easy_log(MQTT_LOG_DEBUG, "Received UNSUBACK (Mid: %d)", mid)
        with self._callback_mutex:
            on_unsubscribe = self.on_unsubscribe

        if on_unsubscribe:
            with self._in_callback_mutex:
                try:
                    if self._callback_api_version == CallbackAPIVersion.VERSION1:
                        if self._protocol == MQTTv5:
                            on_unsubscribe = cast(CallbackOnUnsubscribe_v1_mqtt5, on_unsubscribe)

                            reasoncodes: ReasonCode | list[ReasonCode] = reasoncodes_list
                            if len(reasoncodes_list) == 1:
                                reasoncodes = reasoncodes_list[0]

                            on_unsubscribe(
                                self, self._userdata, mid, properties, reasoncodes)
                        else:
                            on_unsubscribe = cast(CallbackOnUnsubscribe_v1_mqtt3, on_unsubscribe)

                            on_unsubscribe(self, self._userdata, mid)
                    elif self._callback_api_version == CallbackAPIVersion.VERSION2:
                        on_unsubscribe = cast(CallbackOnUnsubscribe_v2, on_unsubscribe)

                        if properties is None:
                            properties = Properties(PacketTypes.CONNACK)

                        on_unsubscribe(
                            self,
                            self._userdata,
                            mid,
                            reasoncodes_list,
                            properties,
                        )
                    else:
                        raise RuntimeError("Unsupported callback API version")
                except Exception as err:
                    self._easy_log(
                        MQTT_LOG_ERR, 'Caught exception in on_unsubscribe: %s', err)
                    if not self.suppress_exceptions:
                        raise

        return MQTTErrorCode.MQTT_ERR_SUCCESS

    def _do_on_disconnect(
        self,
        packet_from_broker: bool,
        v1_rc: MQTTErrorCode,
        reason: ReasonCode | None = None,
        properties: Properties | None = None,
    ) -> None:
        with self._callback_mutex:
            on_disconnect = self.on_disconnect

        if on_disconnect:
            with self._in_callback_mutex:
                try:
                    if self._callback_api_version == CallbackAPIVersion.VERSION1:
                        if self._protocol == MQTTv5:
                            on_disconnect = cast(CallbackOnDisconnect_v1_mqtt5, on_disconnect)

                            if packet_from_broker:
                                on_disconnect(self, self._userdata, reason, properties)
                            else:
                                on_disconnect(self, self._userdata, v1_rc, None)
                        else:
                            on_disconnect = cast(CallbackOnDisconnect_v1_mqtt3, on_disconnect)

                            on_disconnect(self, self._userdata, v1_rc)
                    elif self._callback_api_version == CallbackAPIVersion.VERSION2:
                        on_disconnect = cast(CallbackOnDisconnect_v2, on_disconnect)

                        disconnect_flags = DisconnectFlags(
                            is_disconnect_packet_from_server=packet_from_broker
                        )

                        if reason is None:
                            reason = convert_disconnect_error_code_to_reason_code(v1_rc)

                        if properties is None:
                            properties = Properties(PacketTypes.DISCONNECT)

                        on_disconnect(
                            self,
                            self._userdata,
                            disconnect_flags,
                            reason,
                            properties,
                        )
                    else:
                        raise RuntimeError("Unsupported callback API version")
                except Exception as err:
                    self._easy_log(
                        MQTT_LOG_ERR, 'Caught exception in on_disconnect: %s', err)
                    if not self.suppress_exceptions:
                        raise

    def _do_on_publish(self, mid: int, reason_code: ReasonCode, properties: Properties) -> MQTTErrorCode:
        with self._callback_mutex:
            on_publish = self.on_publish

        if on_publish:
            with self._in_callback_mutex:
                try:
                    if self._callback_api_version == CallbackAPIVersion.VERSION1:
                        on_publish = cast(CallbackOnPublish_v1, on_publish)

                        on_publish(self, self._userdata, mid)
                    elif self._callback_api_version == CallbackAPIVersion.VERSION2:
                        on_publish = cast(CallbackOnPublish_v2, on_publish)

                        on_publish(
                            self,
                            self._userdata,
                            mid,
                            reason_code,
                            properties,
                        )
                    else:
                        raise RuntimeError("Unsupported callback API version")
                except Exception as err:
                    self._easy_log(
                        MQTT_LOG_ERR, 'Caught exception in on_publish: %s', err)
                    if not self.suppress_exceptions:
                        raise

        msg = self._out_messages.pop(mid)
        msg.info._set_as_published()
        if msg.qos > 0:
            self._inflight_messages -= 1
            if self._max_inflight_messages > 0:
                rc = self._update_inflight()
                if rc != MQTTErrorCode.MQTT_ERR_SUCCESS:
                    return rc
        return MQTTErrorCode.MQTT_ERR_SUCCESS

    def _handle_pubackcomp(
        self, cmd: Literal['PUBACK'] | Literal['PUBCOMP']
    ) -> MQTTErrorCode:
        if self._protocol == MQTTv5:
            if self._in_packet['remaining_length'] < 2:
                return MQTTErrorCode.MQTT_ERR_PROTOCOL
        elif self._in_packet['remaining_length'] != 2:
            return MQTTErrorCode.MQTT_ERR_PROTOCOL

        packet_type_enum = PUBACK if cmd == "PUBACK" else PUBCOMP
        packet_type = packet_type_enum.value >> 4
        mid, = struct.unpack("!H", self._in_packet['packet'][:2])
        reasonCode = ReasonCode(packet_type)
        properties = Properties(packet_type)
        if self._protocol == MQTTv5:
            if self._in_packet['remaining_length'] > 2:
                reasonCode.unpack(self._in_packet['packet'][2:])
                if self._in_packet['remaining_length'] > 3:
                    props, props_len = properties.unpack(
                        self._in_packet['packet'][3:])
        self._easy_log(MQTT_LOG_DEBUG, "Received %s (Mid: %d)", cmd, mid)

        with self._out_message_mutex:
            if mid in self._out_messages:
                # Only inform the client the message has been sent once.
                rc = self._do_on_publish(mid, reasonCode, properties)
                return rc

        return MQTTErrorCode.MQTT_ERR_SUCCESS

    def _handle_on_message(self, message: MQTTMessage) -> None:

        try:
            topic = message.topic
        except UnicodeDecodeError:
            topic = None

        on_message_callbacks = []
        with self._callback_mutex:
            if topic is not None:
                on_message_callbacks = list(self._on_message_filtered.iter_match(message.topic))

            if len(on_message_callbacks) == 0:
                on_message = self.on_message
            else:
                on_message = None

        for callback in on_message_callbacks:
            with self._in_callback_mutex:
                try:
                    callback(self, self._userdata, message)
                except Exception as err:
                    self._easy_log(
                        MQTT_LOG_ERR,
                        'Caught exception in user defined callback function %s: %s',
                        callback.__name__,
                        err
                    )
                    if not self.suppress_exceptions:
                        raise

        if on_message:
            with self._in_callback_mutex:
                try:
                    on_message(self, self._userdata, message)
                except Exception as err:
                    self._easy_log(
                        MQTT_LOG_ERR, 'Caught exception in on_message: %s', err)
                    if not self.suppress_exceptions:
                        raise


    def _handle_on_connect_fail(self) -> None:
        with self._callback_mutex:
            on_connect_fail = self.on_connect_fail

        if on_connect_fail:
            with self._in_callback_mutex:
                try:
                    on_connect_fail(self, self._userdata)
                except Exception as err:
                    self._easy_log(
                        MQTT_LOG_ERR, 'Caught exception in on_connect_fail: %s', err)

    def _thread_main(self) -> None:
        try:
            self.loop_forever(retry_first_connection=True)
        finally:
            self._thread = None

    def _reconnect_wait(self) -> None:
        # See reconnect_delay_set for details
        now = time_func()
        with self._reconnect_delay_mutex:
            if self._reconnect_delay is None:
                self._reconnect_delay = self._reconnect_min_delay
            else:
                self._reconnect_delay = min(
                    self._reconnect_delay * 2,
                    self._reconnect_max_delay,
                )

            target_time = now + self._reconnect_delay

        remaining = target_time - now
        while (self._state not in (_ConnectionState.MQTT_CS_DISCONNECTING, _ConnectionState.MQTT_CS_DISCONNECTED)
                and not self._thread_terminate
                and remaining > 0):

            time.sleep(min(remaining, 1))
            remaining = target_time - time_func()

    @staticmethod
    def _proxy_is_valid(p) -> bool:  # type: ignore[no-untyped-def]
        def check(t, a) -> bool:  # type: ignore[no-untyped-def]
            return (socks is not None and
                    t in {socks.HTTP, socks.SOCKS4, socks.SOCKS5} and a)

        if isinstance(p, dict):
            return check(p.get("proxy_type"), p.get("proxy_addr"))
        elif isinstance(p, (list, tuple)):
            return len(p) == 6 and check(p[0], p[1])
        else:
            return False

    def _get_proxy(self) -> dict[str, Any] | None:
        if socks is None:
            return None

        # First, check if the user explicitly passed us a proxy to use
        if self._proxy_is_valid(self._proxy):
            return self._proxy

        # Next, check for an mqtt_proxy environment variable as long as the host
        # we're trying to connect to isn't listed under the no_proxy environment
        # variable (matches built-in module urllib's behavior)
        if not (hasattr(urllib.request, "proxy_bypass") and
                urllib.request.proxy_bypass(self._host)):
            env_proxies = urllib.request.getproxies()
            if "mqtt" in env_proxies:
                parts = urllib.parse.urlparse(env_proxies["mqtt"])
                if parts.scheme == "http":
                    proxy = {
                        "proxy_type": socks.HTTP,
                        "proxy_addr": parts.hostname,
                        "proxy_port": parts.port
                    }
                    return proxy
                elif parts.scheme == "socks":
                    proxy = {
                        "proxy_type": socks.SOCKS5,
                        "proxy_addr": parts.hostname,
                        "proxy_port": parts.port
                    }
                    return proxy

        # Finally, check if the user has monkeypatched the PySocks library with
        # a default proxy
        socks_default = socks.get_default_proxy()
        if self._proxy_is_valid(socks_default):
            proxy_keys = ("proxy_type", "proxy_addr", "proxy_port",
                          "proxy_rdns", "proxy_username", "proxy_password")
            return dict(zip(proxy_keys, socks_default))

        # If we didn't find a proxy through any of the above methods, return
        # None to indicate that the connection should be handled normally
        return None

    def _create_socket(self) -> SocketLike:
        if self._transport == "unix":
            sock = self._create_unix_socket_connection()
        else:
            sock = self._create_socket_connection()

        if self._ssl:
            sock = self._ssl_wrap_socket(sock)

        if self._transport == "websockets":
            sock.settimeout(self._keepalive)
            return _WebsocketWrapper(
                socket=sock,
                host=self._host,
                port=self._port,
                is_ssl=self._ssl,
                path=self._websocket_path,
                extra_headers=self._websocket_extra_headers,
            )

        return sock

    def _create_unix_socket_connection(self) -> _socket.socket:
        unix_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        unix_socket.connect(self._host)
        return unix_socket

    def _create_socket_connection(self) -> _socket.socket:
        proxy = self._get_proxy()
        addr = (self._host, self._port)
        source = (self._bind_address, self._bind_port)

        if proxy:
            return socks.create_connection(addr, timeout=self._connect_timeout, source_address=source, **proxy)
        else:
            return socket.create_connection(addr, timeout=self._connect_timeout, source_address=source)

    def _ssl_wrap_socket(self, tcp_sock: _socket.socket) -> ssl.SSLSocket:
        if self._ssl_context is None:
            raise ValueError(
                "Impossible condition. _ssl_context should never be None if _ssl is True"
            )

        verify_host = not self._tls_insecure
        try:
            # Try with server_hostname, even it's not supported in certain scenarios
            ssl_sock = self._ssl_context.wrap_socket(
                tcp_sock,
                server_hostname=self._host,
                do_handshake_on_connect=False,
            )
        except ssl.CertificateError:
            # CertificateError is derived from ValueError
            raise
        except ValueError:
            # Python version requires SNI in order to handle server_hostname, but SNI is not available
            ssl_sock = self._ssl_context.wrap_socket(
                tcp_sock,
                do_handshake_on_connect=False,
            )
        else:
            # If SSL context has already checked hostname, then don't need to do it again
            if getattr(self._ssl_context, 'check_hostname', False):  # type: ignore
                verify_host = False

        ssl_sock.settimeout(self._keepalive)
        ssl_sock.do_handshake()

        if verify_host:
            # TODO: this type error is a true error:
            # error: Module has no attribute "match_hostname"  [attr-defined]
            # Python 3.12 no longer have this method.
            ssl.match_hostname(ssl_sock.getpeercert(), self._host)  # type: ignore

        return ssl_sock

class _WebsocketWrapper:
    OPCODE_CONTINUATION = 0x0
    OPCODE_TEXT = 0x1
    OPCODE_BINARY = 0x2
    OPCODE_CONNCLOSE = 0x8
    OPCODE_PING = 0x9
    OPCODE_PONG = 0xa

    def __init__(
        self,
        socket: socket.socket | ssl.SSLSocket,
        host: str,
        port: int,
        is_ssl: bool,
        path: str,
        extra_headers: WebSocketHeaders | None,
    ):
        self.connected = False

        self._ssl = is_ssl
        self._host = host
        self._port = port
        self._socket = socket
        self._path = path

        self._sendbuffer = bytearray()
        self._readbuffer = bytearray()

        self._requested_size = 0
        self._payload_head = 0
        self._readbuffer_head = 0

        self._do_handshake(extra_headers)

    def __del__(self) -> None:
        self._sendbuffer = bytearray()
        self._readbuffer = bytearray()

    def _do_handshake(self, extra_headers: WebSocketHeaders | None) -> None:

        sec_websocket_key = uuid.uuid4().bytes
        sec_websocket_key = base64.b64encode(sec_websocket_key)

        if self._ssl:
            default_port = 443
            http_schema = "https"
        else:
            default_port = 80
            http_schema = "http"

        if default_port == self._port:
            host_port = f"{self._host}"
        else:
            host_port = f"{self._host}:{self._port}"

        websocket_headers = {
            "Host": host_port,
            "Upgrade": "websocket",
            "Connection": "Upgrade",
            "Origin": f"{http_schema}://{host_port}",
            "Sec-WebSocket-Key": sec_websocket_key.decode("utf8"),
            "Sec-Websocket-Version": "13",
            "Sec-Websocket-Protocol": "mqtt",
        }

        # This is checked in ws_set_options so it will either be None, a
        # dictionary, or a callable
        if isinstance(extra_headers, dict):
            websocket_headers.update(extra_headers)
        elif callable(extra_headers):
            websocket_headers = extra_headers(websocket_headers)

        header = "\r\n".join([
            f"GET {self._path} HTTP/1.1",
            "\r\n".join(f"{i}: {j}" for i, j in websocket_headers.items()),
            "\r\n",
        ]).encode("utf8")

        self._socket.send(header)

        has_secret = False
        has_upgrade = False

        while True:
            # read HTTP response header as lines
            try:
                byte = self._socket.recv(1)
            except ConnectionResetError:
                byte = b""

            self._readbuffer.extend(byte)

            # line end
            if byte == b"\n":
                if len(self._readbuffer) > 2:
                    # check upgrade
                    if b"connection" in str(self._readbuffer).lower().encode('utf-8'):
                        if b"upgrade" not in str(self._readbuffer).lower().encode('utf-8'):
                            raise WebsocketConnectionError(
                                "WebSocket handshake error, connection not upgraded")
                        else:
                            has_upgrade = True

                    # check key hash
                    if b"sec-websocket-accept" in str(self._readbuffer).lower().encode('utf-8'):
                        GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

                        server_hash_str = self._readbuffer.decode(
                            'utf-8').split(": ", 1)[1]
                        server_hash = server_hash_str.strip().encode('utf-8')

                        client_hash_key = sec_websocket_key.decode('utf-8') + GUID
                        # Use of SHA-1 is OK here; it's according to the Websocket spec.
                        client_hash_digest = hashlib.sha1(client_hash_key.encode('utf-8'))  # noqa: S324
                        client_hash = base64.b64encode(client_hash_digest.digest())

                        if server_hash != client_hash:
                            raise WebsocketConnectionError(
                                "WebSocket handshake error, invalid secret key")
                        else:
                            has_secret = True
                else:
                    # ending linebreak
                    break

                # reset linebuffer
                self._readbuffer = bytearray()

            # connection reset
            elif not byte:
                raise WebsocketConnectionError("WebSocket handshake error")

        if not has_upgrade or not has_secret:
            raise WebsocketConnectionError("WebSocket handshake error")

        self._readbuffer = bytearray()
        self.connected = True

    def _create_frame(
        self, opcode: int, data: bytearray, do_masking: int = 1
    ) -> bytearray:
        header = bytearray()
        length = len(data)

        mask_key = bytearray(os.urandom(4))
        mask_flag = do_masking

        # 1 << 7 is the final flag, we don't send continuated data
        header.append(1 << 7 | opcode)

        if length < 126:
            header.append(mask_flag << 7 | length)

        elif length < 65536:
            header.append(mask_flag << 7 | 126)
            header += struct.pack("!H", length)

        elif length < 0x8000000000000001:
            header.append(mask_flag << 7 | 127)
            header += struct.pack("!Q", length)

        else:
            raise ValueError("Maximum payload size is 2^63")

        if mask_flag == 1:
            for index in range(length):
                data[index] ^= mask_key[index % 4]
            data = mask_key + data

        return header + data

    def _buffered_read(self, length: int) -> bytearray:

        # try to recv and store needed bytes
        wanted_bytes = length - (len(self._readbuffer) - self._readbuffer_head)
        if wanted_bytes > 0:

            data = self._socket.recv(wanted_bytes)

            if not data:
                raise ConnectionAbortedError
            else:
                self._readbuffer.extend(data)

            if len(data) < wanted_bytes:
                raise BlockingIOError

        self._readbuffer_head += length
        return self._readbuffer[self._readbuffer_head - length:self._readbuffer_head]

    def _recv_impl(self, length: int) -> bytes:

        # try to decode websocket payload part from data
        try:

            self._readbuffer_head = 0

            result = b""

            chunk_startindex = self._payload_head
            chunk_endindex = self._payload_head + length

            header1 = self._buffered_read(1)
            header2 = self._buffered_read(1)

            opcode = (header1[0] & 0x0f)
            maskbit = (header2[0] & 0x80) == 0x80
            lengthbits = (header2[0] & 0x7f)
            payload_length = lengthbits
            mask_key = None

            # read length
            if lengthbits == 0x7e:

                value = self._buffered_read(2)
                payload_length, = struct.unpack("!H", value)

            elif lengthbits == 0x7f:

                value = self._buffered_read(8)
                payload_length, = struct.unpack("!Q", value)

            # read mask
            if maskbit:
                mask_key = self._buffered_read(4)

            # if frame payload is shorter than the requested data, read only the possible part
            readindex = chunk_endindex
            if payload_length < readindex:
                readindex = payload_length

            if readindex > 0:
                # get payload chunk
                payload = self._buffered_read(readindex)

                # unmask only the needed part
                if mask_key is not None:
                    for index in range(chunk_startindex, readindex):
                        payload[index] ^= mask_key[index % 4]

                result = payload[chunk_startindex:readindex]
                self._payload_head = readindex
            else:
                payload = bytearray()

            # check if full frame arrived and reset readbuffer and payloadhead if needed
            if readindex == payload_length:
                self._readbuffer = bytearray()
                self._payload_head = 0

                # respond to non-binary opcodes, their arrival is not guaranteed because of non-blocking sockets
                if opcode == _WebsocketWrapper.OPCODE_CONNCLOSE:
                    frame = self._create_frame(
                        _WebsocketWrapper.OPCODE_CONNCLOSE, payload, 0)
                    self._socket.send(frame)

                if opcode == _WebsocketWrapper.OPCODE_PING:
                    frame = self._create_frame(
                        _WebsocketWrapper.OPCODE_PONG, payload, 0)
                    self._socket.send(frame)

            # This isn't *proper* handling of continuation frames, but given
            # that we only support binary frames, it is *probably* good enough.
            if (opcode == _WebsocketWrapper.OPCODE_BINARY or opcode == _WebsocketWrapper.OPCODE_CONTINUATION) \
                    and payload_length > 0:
                return result
            else:
                raise BlockingIOError

        except ConnectionError:
            self.connected = False
            return b''

    def _send_impl(self, data: bytes) -> int:

        # if previous frame was sent successfully
        if len(self._sendbuffer) == 0:
            # create websocket frame
            frame = self._create_frame(
                _WebsocketWrapper.OPCODE_BINARY, bytearray(data))
            self._sendbuffer.extend(frame)
            self._requested_size = len(data)

        # try to write out as much as possible
        length = self._socket.send(self._sendbuffer)

        self._sendbuffer = self._sendbuffer[length:]

        if len(self._sendbuffer) == 0:
            # buffer sent out completely, return with payload's size
            return self._requested_size
        else:
            # couldn't send whole data, request the same data again with 0 as sent length
            return 0

    def recv(self, length: int) -> bytes:
        return self._recv_impl(length)

    def read(self, length: int) -> bytes:
        return self._recv_impl(length)

    def send(self, data: bytes) -> int:
        return self._send_impl(data)

    def write(self, data: bytes) -> int:
        return self._send_impl(data)

    def close(self) -> None:
        self._socket.close()

    def fileno(self) -> int:
        return self._socket.fileno()

    def pending(self) -> int:
        # Fix for bug #131: a SSL socket may still have data available
        # for reading without select() being aware of it.
        if self._ssl:
            return self._socket.pending()  # type: ignore[union-attr]
        else:
            # normal socket rely only on select()
            return 0

    def setblocking(self, flag: bool) -> None:
        self._socket.setblocking(flag)
