# *******************************************************************
#   Copyright (c) 2017, 2019 IBM Corp.
#
#   All rights reserved. This program and the accompanying materials
#   are made available under the terms of the Eclipse Public License v2.0
#   and Eclipse Distribution License v1.0 which accompany this distribution.
#
#   The Eclipse Public License is available at
#      http://www.eclipse.org/legal/epl-v20.html
#   and the Eclipse Distribution License is available at
#     http://www.eclipse.org/org/documents/edl-v10.php.
#
#   Contributors:
#      Ian Craggs - initial implementation and/or documentation
# *******************************************************************

import functools
import warnings
from typing import Any

from .packettypes import PacketTypes


@functools.total_ordering
class ReasonCode:
    """MQTT version 5.0 reason codes class.

    See ReasonCode.names for a list of possible numeric values along with their
    names and the packets to which they apply.

    """

    def __init__(self, packetType: int, aName: str ="Success", identifier: int =-1):
        """
        packetType: the type of the packet, such as PacketTypes.CONNECT that
            this reason code will be used with.  Some reason codes have different
            names for the same identifier when used a different packet type.

        aName: the String name of the reason code to be created.  Ignored
            if the identifier is set.

        identifier: an integer value of the reason code to be created.

        """

        self.packetType = packetType
        self.names = {
            0: {"Success": [PacketTypes.CONNACK, PacketTypes.PUBACK,
                            PacketTypes.PUBREC, PacketTypes.PUBREL, PacketTypes.PUBCOMP,
                            PacketTypes.UNSUBACK, PacketTypes.AUTH],
                "Normal disconnection": [PacketTypes.DISCONNECT],
                "Granted QoS 0": [PacketTypes.SUBACK]},
            1: {"Granted QoS 1": [PacketTypes.SUBACK]},
            2: {"Granted QoS 2": [PacketTypes.SUBACK]},
            4: {"Disconnect with will message": [PacketTypes.DISCONNECT]},
            16: {"No matching subscribers":
                 [PacketTypes.PUBACK, PacketTypes.PUBREC]},
            17: {"No subscription found": [PacketTypes.UNSUBACK]},
            24: {"Continue authentication": [PacketTypes.AUTH]},
            25: {"Re-authenticate": [PacketTypes.AUTH]},
            128: {"Unspecified error": [PacketTypes.CONNACK, PacketTypes.PUBACK,
                                        PacketTypes.PUBREC, PacketTypes.SUBACK, PacketTypes.UNSUBACK,
                                        PacketTypes.DISCONNECT], },
            129: {"Malformed packet":
                  [PacketTypes.CONNACK, PacketTypes.DISCONNECT]},
            130: {"Protocol error":
                  [PacketTypes.CONNACK, PacketTypes.DISCONNECT]},
            131: {"Implementation specific error": [PacketTypes.CONNACK,
                                                    PacketTypes.PUBACK, PacketTypes.PUBREC, PacketTypes.SUBACK,
                                                    PacketTypes.UNSUBACK, PacketTypes.DISCONNECT], },
            132: {"Unsupported protocol version": [PacketTypes.CONNACK]},
            133: {"Client identifier not valid": [PacketTypes.CONNACK]},
            134: {"Bad user name or password": [PacketTypes.CONNACK]},
            135: {"Not authorized": [PacketTypes.CONNACK, PacketTypes.PUBACK,
                                     PacketTypes.PUBREC, PacketTypes.SUBACK, PacketTypes.UNSUBACK,
                                     PacketTypes.DISCONNECT], },
            136: {"Server unavailable": [PacketTypes.CONNACK]},
            137: {"Server busy": [PacketTypes.CONNACK, PacketTypes.DISCONNECT]},
            138: {"Banned": [PacketTypes.CONNACK]},
            139: {"Server shutting down": [PacketTypes.DISCONNECT]},
            140: {"Bad authentication method":
                  [PacketTypes.CONNACK, PacketTypes.DISCONNECT]},
            141: {"Keep alive timeout": [PacketTypes.DISCONNECT]},
            142: {"Session taken over": [PacketTypes.DISCONNECT]},
            143: {"Topic filter invalid":
                  [PacketTypes.SUBACK, PacketTypes.UNSUBACK, PacketTypes.DISCONNECT]},
            144: {"Topic name invalid":
                  [PacketTypes.CONNACK, PacketTypes.PUBACK,
                   PacketTypes.PUBREC, PacketTypes.DISCONNECT]},
            145: {"Packet identifier in use":
                  [PacketTypes.PUBACK, PacketTypes.PUBREC,
                   PacketTypes.SUBACK, PacketTypes.UNSUBACK]},
            146: {"Packet identifier not found":
                  [PacketTypes.PUBREL, PacketTypes.PUBCOMP]},
            147: {"Receive maximum exceeded": [PacketTypes.DISCONNECT]},
            148: {"Topic alias invalid": [PacketTypes.DISCONNECT]},
            149: {"Packet too large": [PacketTypes.CONNACK, PacketTypes.DISCONNECT]},
            150: {"Message rate too high": [PacketTypes.DISCONNECT]},
            151: {"Quota exceeded": [PacketTypes.CONNACK, PacketTypes.PUBACK,
                                     PacketTypes.PUBREC, PacketTypes.SUBACK, PacketTypes.DISCONNECT], },
            152: {"Administrative action": [PacketTypes.DISCONNECT]},
            153: {"Payload format invalid":
                  [PacketTypes.PUBACK, PacketTypes.PUBREC, PacketTypes.DISCONNECT]},
            154: {"Retain not supported":
                  [PacketTypes.CONNACK, PacketTypes.DISCONNECT]},
            155: {"QoS not supported":
                  [PacketTypes.CONNACK, PacketTypes.DISCONNECT]},
            156: {"Use another server":
                  [PacketTypes.CONNACK, PacketTypes.DISCONNECT]},
            157: {"Server moved":
                  [PacketTypes.CONNACK, PacketTypes.DISCONNECT]},
            158: {"Shared subscription not supported":
                  [PacketTypes.SUBACK, PacketTypes.DISCONNECT]},
            159: {"Connection rate exceeded":
                  [PacketTypes.CONNACK, PacketTypes.DISCONNECT]},
            160: {"Maximum connect time":
                  [PacketTypes.DISCONNECT]},
            161: {"Subscription identifiers not supported":
                  [PacketTypes.SUBACK, PacketTypes.DISCONNECT]},
            162: {"Wildcard subscription not supported":
                  [PacketTypes.SUBACK, PacketTypes.DISCONNECT]},
        }
        if identifier == -1:
            if packetType == PacketTypes.DISCONNECT and aName == "Success":
                aName = "Normal disconnection"
            self.set(aName)
        else:
            self.value = identifier
            self.getName()  # check it's good

    def __getName__(self, packetType, identifier):
        """
        Get the reason code string name for a specific identifier.
        The name can vary by packet type for the same identifier, which
        is why the packet type is also required.

        Used when displaying the reason code.
        """
        if identifier not in self.names:
            raise KeyError(identifier)
        names = self.names[identifier]
        namelist = [name for name in names.keys() if packetType in names[name]]
        if len(namelist) != 1:
            raise ValueError(f"Expected exactly one name, found {namelist!r}")
        return namelist[0]

    def getId(self, name):
        """
        Get the numeric id corresponding to a reason code name.

        Used when setting the reason code for a packetType
        check that only valid codes for the packet are set.
        """
        for code in self.names.keys():
            if name in self.names[code].keys():
                if self.packetType in self.names[code][name]:
                    return code
        raise KeyError(f"Reason code name not found: {name}")

    def set(self, name):
        self.value = self.getId(name)

    def unpack(self, buffer):
        c = buffer[0]
        name = self.__getName__(self.packetType, c)
        self.value = self.getId(name)
        return 1

    def getName(self):
        """Returns the reason code name corresponding to the numeric value which is set.
        """
        return self.__getName__(self.packetType, self.value)

    def __eq__(self, other):
        if isinstance(other, int):
            return self.value == other
        if isinstance(other, str):
            return other == str(self)
        if isinstance(other, ReasonCode):
            return self.value == other.value
        return False

    def __lt__(self, other):
        if isinstance(other, int):
            return self.value < other
        if isinstance(other, ReasonCode):
            return self.value < other.value
        return NotImplemented

    def __repr__(self):
        try:
            packet_name = PacketTypes.Names[self.packetType]
        except IndexError:
            packet_name = "Unknown"

        return f"ReasonCode({packet_name}, {self.getName()!r})"

    def __str__(self):
        return self.getName()

    def json(self):
        return self.getName()

    def pack(self):
        return bytearray([self.value])

    @property
    def is_failure(self) -> bool:
        return self.value >= 0x80


class _CompatibilityIsInstance(type):
    def __instancecheck__(self, other: Any) -> bool:
        return isinstance(other, ReasonCode)


class ReasonCodes(ReasonCode, metaclass=_CompatibilityIsInstance):
    def __init__(self, *args, **kwargs):
        warnings.warn("ReasonCodes is deprecated, use ReasonCode (singular) instead",
            category=DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(*args, **kwargs)
