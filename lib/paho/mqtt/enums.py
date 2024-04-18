import enum


class MQTTErrorCode(enum.IntEnum):
    MQTT_ERR_AGAIN = -1
    MQTT_ERR_SUCCESS = 0
    MQTT_ERR_NOMEM = 1
    MQTT_ERR_PROTOCOL = 2
    MQTT_ERR_INVAL = 3
    MQTT_ERR_NO_CONN = 4
    MQTT_ERR_CONN_REFUSED = 5
    MQTT_ERR_NOT_FOUND = 6
    MQTT_ERR_CONN_LOST = 7
    MQTT_ERR_TLS = 8
    MQTT_ERR_PAYLOAD_SIZE = 9
    MQTT_ERR_NOT_SUPPORTED = 10
    MQTT_ERR_AUTH = 11
    MQTT_ERR_ACL_DENIED = 12
    MQTT_ERR_UNKNOWN = 13
    MQTT_ERR_ERRNO = 14
    MQTT_ERR_QUEUE_SIZE = 15
    MQTT_ERR_KEEPALIVE = 16


class MQTTProtocolVersion(enum.IntEnum):
    MQTTv31 = 3
    MQTTv311 = 4
    MQTTv5 = 5


class CallbackAPIVersion(enum.Enum):
    """Defined the arguments passed to all user-callback.

    See each callbacks for details: `on_connect`, `on_connect_fail`, `on_disconnect`, `on_message`, `on_publish`,
    `on_subscribe`, `on_unsubscribe`, `on_log`, `on_socket_open`, `on_socket_close`,
    `on_socket_register_write`, `on_socket_unregister_write`
    """
    VERSION1 = 1
    """The version used with paho-mqtt 1.x before introducing CallbackAPIVersion.

    This version had different arguments depending if MQTTv5 or MQTTv3 was used. `Properties` & `ReasonCode` were missing
    on some callback (apply only to MQTTv5).

    This version is deprecated and will be removed in version 3.0.
    """
    VERSION2 = 2
    """ This version fix some of the shortcoming of previous version.

    Callback have the same signature if using MQTTv5 or MQTTv3. `ReasonCode` are used in MQTTv3.
    """


class MessageType(enum.IntEnum):
    CONNECT = 0x10
    CONNACK = 0x20
    PUBLISH = 0x30
    PUBACK = 0x40
    PUBREC = 0x50
    PUBREL = 0x60
    PUBCOMP = 0x70
    SUBSCRIBE = 0x80
    SUBACK = 0x90
    UNSUBSCRIBE = 0xA0
    UNSUBACK = 0xB0
    PINGREQ = 0xC0
    PINGRESP = 0xD0
    DISCONNECT = 0xE0
    AUTH = 0xF0


class LogLevel(enum.IntEnum):
    MQTT_LOG_INFO = 0x01
    MQTT_LOG_NOTICE = 0x02
    MQTT_LOG_WARNING = 0x04
    MQTT_LOG_ERR = 0x08
    MQTT_LOG_DEBUG = 0x10


class ConnackCode(enum.IntEnum):
    CONNACK_ACCEPTED = 0
    CONNACK_REFUSED_PROTOCOL_VERSION = 1
    CONNACK_REFUSED_IDENTIFIER_REJECTED = 2
    CONNACK_REFUSED_SERVER_UNAVAILABLE = 3
    CONNACK_REFUSED_BAD_USERNAME_PASSWORD = 4
    CONNACK_REFUSED_NOT_AUTHORIZED = 5


class _ConnectionState(enum.Enum):
    MQTT_CS_NEW = enum.auto()
    MQTT_CS_CONNECT_ASYNC = enum.auto()
    MQTT_CS_CONNECTING = enum.auto()
    MQTT_CS_CONNECTED = enum.auto()
    MQTT_CS_CONNECTION_LOST = enum.auto()
    MQTT_CS_DISCONNECTING = enum.auto()
    MQTT_CS_DISCONNECTED = enum.auto()


class MessageState(enum.IntEnum):
    MQTT_MS_INVALID = 0
    MQTT_MS_PUBLISH = 1
    MQTT_MS_WAIT_FOR_PUBACK = 2
    MQTT_MS_WAIT_FOR_PUBREC = 3
    MQTT_MS_RESEND_PUBREL = 4
    MQTT_MS_WAIT_FOR_PUBREL = 5
    MQTT_MS_RESEND_PUBCOMP = 6
    MQTT_MS_WAIT_FOR_PUBCOMP = 7
    MQTT_MS_SEND_PUBREC = 8
    MQTT_MS_QUEUED = 9


class PahoClientMode(enum.IntEnum):
    MQTT_CLIENT = 0
    MQTT_BRIDGE = 1
