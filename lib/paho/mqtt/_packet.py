""" internal module to (de)serialize packet.
"""

from __future__ import annotations

import functools
import struct
from typing import TYPE_CHECKING, Callable, NamedTuple, TypeVar

from paho.mqtt.enums import ConnackCode, MQTTProtocolVersion
from paho.mqtt.exception import MalformedPacket, MQTTException
from paho.mqtt.packettypes import PacketTypes
from paho.mqtt.properties import Properties
from paho.mqtt.reasoncodes import ReasonCode


class PublishPacket(NamedTuple):
    dup: bool
    qos: int
    retain: bool
    topic: bytes
    mid: int
    properties: Properties|None
    payload: bytes|bytearray


class ConnackPacket(NamedTuple):
    flags: int
    reason: ReasonCode
    properties: Properties|None
    rc: ConnackCode

class DisconnectPacket(NamedTuple):
    reason: ReasonCode|None
    properties: Properties|None


class SubackPacket(NamedTuple):
    mid: int
    reason_codes: list[ReasonCode]
    granted_qos: tuple[int, ...]
    properties: Properties


class UnsubackPacket(NamedTuple):
    mid: int
    reason_codes: list[ReasonCode]
    properties: Properties

class PubrelPacket(NamedTuple):
    mid: int
    reason: ReasonCode
    properties: Properties


class PubrecPacket(NamedTuple):
    mid: int
    reason: ReasonCode
    properties: Properties


class PubackPacket(NamedTuple):
    mid: int
    reason: ReasonCode
    properties: Properties


class PubcompPacket(NamedTuple):
    mid: int
    reason: ReasonCode
    properties: Properties


# Also catch MQTTException, because Properties decoding could yield MQTTException.
# It's expected that such decoding yield MQTTException because it could equally occur
# during decoding (here a MalformedPacket would be better), but also when user try to
# encode a property (here a MalformedPacket wouldn't fit).
DECODE_ERRORS = (struct.error, IndexError, KeyError, ValueError, MQTTException)

if TYPE_CHECKING:
    from typing_extensions import ParamSpec

    P = ParamSpec("P")
    R = TypeVar("R")


def convert_exception(func: Callable[P, R]) -> Callable[P, R]:
    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        try:
            return func(*args, **kwargs)
        except MalformedPacket:
            raise
        except DECODE_ERRORS as err:
            raise MalformedPacket(str(err)) from err
    return wrapper


@convert_exception
def decode_publish(header: int, packet: bytes|bytearray, protocol: MQTTProtocolVersion) -> PublishPacket:
    """ Decode a PUBLISH packet.

        header is the first bytes of fixed header. packet is everything after
        the fixed header (e.g. after the remaining length byte(s)).
    """
    dup = ((header & 0x08) >> 3) != 0
    qos = (header & 0x06) >> 1
    retain = (header & 0x01) != 0

    pack_format = f"!H{len(packet) - 2}s"
    (slen, packet) = struct.unpack(pack_format, packet)
    pack_format = f"!{slen}s{len(packet) - slen}s"
    (topic, packet) = struct.unpack(pack_format, packet)

    if protocol != MQTTProtocolVersion.MQTTv5 and len(topic) == 0:
        raise MalformedPacket("topic can't be empty in MQTTv3")

    mid = 0
    if qos > 0:
        pack_format = f"!H{len(packet) - 2}s"
        (mid, packet) = struct.unpack(pack_format, packet)

    properties = None
    if protocol == MQTTProtocolVersion.MQTTv5:
        properties = Properties(PacketTypes.PUBLISH)
        _props, props_len = properties.unpack(packet)
        packet = packet[props_len:]

    payload = packet

    return PublishPacket(
        dup=dup,
        qos=qos,
        retain=retain,
        topic=topic,
        mid=mid,
        properties=properties,
        payload=payload,
    )


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


@convert_exception
def decode_connack(header: int, packet: bytes|bytearray, protocol: MQTTProtocolVersion) -> ConnackPacket:
    """ Decode a CONNACK packet.

        header is the first bytes of fixed header. packet is everything after
        the fixed header (e.g. after the remaining length byte(s)).
    """
    if protocol == MQTTProtocolVersion.MQTTv5:
        if len(packet) < 2:
            raise MalformedPacket("CONNACK packet is too small")
    elif len(packet) != 2:
        raise MalformedPacket("CONNACK packet size is wrong")

    if protocol == MQTTProtocolVersion.MQTTv5:
        (flags, result) = struct.unpack(
            "!BB", packet[:2])
        if result == 1:
            # This is probably a failure from a broker that doesn't support
            # MQTT v5.
            reason = ReasonCode(PacketTypes.CONNACK, aName="Unsupported protocol version")
            properties = None
        else:
            reason = ReasonCode(PacketTypes.CONNACK, identifier=result)
            properties = Properties(PacketTypes.CONNACK)
            properties.unpack(packet[2:])

    else:
        (flags, result) = struct.unpack("!BB", packet)
        reason = convert_connack_rc_to_reason_code(result)
        properties = None

    return ConnackPacket(
        flags=flags,
        reason=reason,
        properties=properties,
        rc=result,
    )


@convert_exception
def decode_disconnect(header: int, packet: bytes|bytearray, protocol: MQTTProtocolVersion) -> DisconnectPacket:
    """ Decode a DISCONNECT packet.

        header is the first bytes of fixed header. packet is everything after
        the fixed header (e.g. after the remaining length byte(s)).
    """
    packet_type = PacketTypes.DISCONNECT
    reasonCode = properties = None

    if len(packet) > 0:
        reasonCode = ReasonCode(packet_type)
        reasonCode.unpack(packet)
        if len(packet) > 1:
            properties = Properties(packet_type)
            _props, _props_len = properties.unpack(packet[1:])

    return DisconnectPacket(
        reason=reasonCode,
        properties=properties,
    )


@convert_exception
def decode_suback(header: int, packet: bytes|bytearray, protocol: MQTTProtocolVersion) -> SubackPacket:
    """ Decode a SUBACK packet.

        header is the first bytes of fixed header. packet is everything after
        the fixed header (e.g. after the remaining length byte(s)).
    """
    pack_format = f"!H{len(packet) - 2}s"
    (mid, packet) = struct.unpack(pack_format, packet)

    if protocol == MQTTProtocolVersion.MQTTv5:
        granted_qos: tuple[int, ...] = ()
        properties = Properties(PacketTypes.SUBACK)
        _props, props_len = properties.unpack(packet)
        reasoncodes = [ReasonCode(PacketTypes.SUBACK, identifier=c) for c in packet[props_len:]]
    else:
        pack_format = f"!{'B' * len(packet)}"
        granted_qos = struct.unpack(pack_format, packet)
        reasoncodes = [ReasonCode(PacketTypes.SUBACK, identifier=c) for c in granted_qos]
        properties = Properties(PacketTypes.SUBACK)

    return SubackPacket(
        mid=mid,
        reason_codes=reasoncodes,
        granted_qos=granted_qos,
        properties=properties,
    )



@convert_exception
def decode_unsuback(header: int, packet: bytes|bytearray, protocol: MQTTProtocolVersion) -> UnsubackPacket:
    """ Decode a UNSUBACK packet.

        header is the first bytes of fixed header. packet is everything after
        the fixed header (e.g. after the remaining length byte(s)).
    """
    if protocol == MQTTProtocolVersion.MQTTv5:
        if len(packet) < 4:
            raise MalformedPacket("wrong size of packet")
    elif len(packet) != 2:
        raise MalformedPacket("wrong size of packet")

    mid, = struct.unpack("!H", packet[:2])
    if protocol == MQTTProtocolVersion.MQTTv5:
        packet = packet[2:]
        properties = Properties(PacketTypes.UNSUBACK)
        _props, props_len = properties.unpack(packet)
        reasoncodes_list = [
            ReasonCode(PacketTypes.UNSUBACK, identifier=c)
            for c in packet[props_len:]
        ]
    else:
        reasoncodes_list = []
        properties = Properties(PacketTypes.UNSUBACK)

    return UnsubackPacket(
        mid=mid,
        reason_codes=reasoncodes_list,
        properties=properties,
    )


def _decode_mid_reason_prop(packet_type: int, packet: bytes|bytearray, protocol: MQTTProtocolVersion) -> tuple[int, ReasonCode, Properties]:
    if protocol == MQTTProtocolVersion.MQTTv5:
        if len(packet) < 2:
            raise MalformedPacket("wrong size of packet")
    elif len(packet) != 2:
        raise MalformedPacket("wrong size of packet")

    mid, = struct.unpack("!H", packet[:2])
    reasonCode = ReasonCode(packet_type)
    properties = Properties(packet_type)
    if protocol == MQTTProtocolVersion.MQTTv5 and len(packet) > 2:
        reasonCode = ReasonCode(packet_type)
        reasonCode.unpack(packet[2:])
        if len(packet) > 3:
            properties = Properties(packet_type)
            _props, _props_len = properties.unpack(
                packet[3:])

    return mid, reasonCode, properties


@convert_exception
def decode_pubrel(header: int, packet: bytes|bytearray, protocol: MQTTProtocolVersion) -> PubrelPacket:
    """ Decode a PUBREL packet.

        header is the first bytes of fixed header. packet is everything after
        the fixed header (e.g. after the remaining length byte(s)).
    """
    (mid, reasonCode, properties) = _decode_mid_reason_prop(PacketTypes.PUBREL, packet, protocol)

    return PubrelPacket(
        mid=mid,
        reason=reasonCode,
        properties=properties,
    )


@convert_exception
def decode_pubrec(header: int, packet: bytes|bytearray, protocol: MQTTProtocolVersion) -> PubrecPacket:
    """ Decode a PUBREC packet.

        header is the first bytes of fixed header. packet is everything after
        the fixed header (e.g. after the remaining length byte(s)).
    """
    (mid, reasonCode, properties) = _decode_mid_reason_prop(PacketTypes.PUBREC, packet, protocol)

    return PubrecPacket(
        mid=mid,
        reason=reasonCode,
        properties=properties,
    )


@convert_exception
def decode_puback(header: int, packet: bytes|bytearray, protocol: MQTTProtocolVersion) -> PubackPacket:
    """ Decode a PUBACK packet.

        header is the first bytes of fixed header. packet is everything after
        the fixed header (e.g. after the remaining length byte(s)).
    """
    (mid, reasonCode, properties) = _decode_mid_reason_prop(PacketTypes.PUBACK, packet, protocol)

    return PubackPacket(
        mid=mid,
        reason=reasonCode,
        properties=properties,
    )


@convert_exception
def decode_pubcomp(header: int, packet: bytes|bytearray, protocol: MQTTProtocolVersion) -> PubcompPacket:
    """ Decode a PUBCOMP packet.

        header is the first bytes of fixed header. packet is everything after
        the fixed header (e.g. after the remaining length byte(s)).
    """
    (mid, reasonCode, properties) = _decode_mid_reason_prop(PacketTypes.PUBCOMP, packet, protocol)

    return PubcompPacket(
        mid=mid,
        reason=reasonCode,
        properties=properties,
    )
