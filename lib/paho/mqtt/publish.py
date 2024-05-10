# Copyright (c) 2014 Roger Light <roger@atchoo.org>
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

"""
This module provides some helper functions to allow straightforward publishing
of messages in a one-shot manner. In other words, they are useful for the
situation where you have a single/multiple messages you want to publish to a
broker, then disconnect and nothing else is required.
"""
from __future__ import annotations

import collections
from collections.abc import Iterable
from typing import TYPE_CHECKING, Any, List, Tuple, Union

from paho.mqtt.enums import CallbackAPIVersion, MQTTProtocolVersion
from paho.mqtt.properties import Properties
from paho.mqtt.reasoncodes import ReasonCode

from .. import mqtt
from . import client as paho

if TYPE_CHECKING:
    try:
        from typing import NotRequired, Required, TypedDict  # type: ignore
    except ImportError:
        from typing_extensions import NotRequired, Required, TypedDict

    try:
        from typing import Literal
    except ImportError:
        from typing_extensions import Literal  # type: ignore



    class AuthParameter(TypedDict, total=False):
        username: Required[str]
        password: NotRequired[str]


    class TLSParameter(TypedDict, total=False):
        ca_certs: Required[str]
        certfile: NotRequired[str]
        keyfile: NotRequired[str]
        tls_version: NotRequired[int]
        ciphers: NotRequired[str]
        insecure: NotRequired[bool]


    class MessageDict(TypedDict, total=False):
        topic: Required[str]
        payload: NotRequired[paho.PayloadType]
        qos: NotRequired[int]
        retain: NotRequired[bool]

    MessageTuple = Tuple[str, paho.PayloadType, int, bool]

    MessagesList = List[Union[MessageDict, MessageTuple]]


def _do_publish(client: paho.Client):
    """Internal function"""

    message = client._userdata.popleft()

    if isinstance(message, dict):
        client.publish(**message)
    elif isinstance(message, (tuple, list)):
        client.publish(*message)
    else:
        raise TypeError('message must be a dict, tuple, or list')


def _on_connect(client: paho.Client, userdata: MessagesList, flags, reason_code, properties):
    """Internal v5 callback"""
    if reason_code == 0:
        if len(userdata) > 0:
            _do_publish(client)
    else:
        raise mqtt.MQTTException(paho.connack_string(reason_code))


def _on_publish(
    client: paho.Client, userdata: collections.deque[MessagesList], mid: int, reason_codes: ReasonCode, properties: Properties,
) -> None:
    """Internal callback"""
    #pylint: disable=unused-argument

    if len(userdata) == 0:
        client.disconnect()
    else:
        _do_publish(client)


def multiple(
    msgs: MessagesList,
    hostname: str = "localhost",
    port: int = 1883,
    client_id: str = "",
    keepalive: int = 60,
    will: MessageDict | None = None,
    auth: AuthParameter | None = None,
    tls: TLSParameter | None = None,
    protocol: MQTTProtocolVersion = paho.MQTTv311,
    transport: Literal["tcp", "websockets"] = "tcp",
    proxy_args: Any | None = None,
) -> None:
    """Publish multiple messages to a broker, then disconnect cleanly.

    This function creates an MQTT client, connects to a broker and publishes a
    list of messages. Once the messages have been delivered, it disconnects
    cleanly from the broker.

    :param msgs: a list of messages to publish. Each message is either a dict or a
           tuple.

           If a dict, only the topic must be present. Default values will be
           used for any missing arguments. The dict must be of the form:

           msg = {'topic':"<topic>", 'payload':"<payload>", 'qos':<qos>,
           'retain':<retain>}
           topic must be present and may not be empty.
           If payload is "", None or not present then a zero length payload
           will be published.
           If qos is not present, the default of 0 is used.
           If retain is not present, the default of False is used.

           If a tuple, then it must be of the form:
           ("<topic>", "<payload>", qos, retain)

    :param str hostname: the address of the broker to connect to.
               Defaults to localhost.

    :param int port: the port to connect to the broker on. Defaults to 1883.

    :param str client_id: the MQTT client id to use. If "" or None, the Paho library will
                generate a client id automatically.

    :param int keepalive: the keepalive timeout value for the client. Defaults to 60
                seconds.

    :param will: a dict containing will parameters for the client: will = {'topic':
           "<topic>", 'payload':"<payload">, 'qos':<qos>, 'retain':<retain>}.
           Topic is required, all other parameters are optional and will
           default to None, 0 and False respectively.
           Defaults to None, which indicates no will should be used.

    :param auth: a dict containing authentication parameters for the client:
           auth = {'username':"<username>", 'password':"<password>"}
           Username is required, password is optional and will default to None
           if not provided.
           Defaults to None, which indicates no authentication is to be used.

    :param tls: a dict containing TLS configuration parameters for the client:
          dict = {'ca_certs':"<ca_certs>", 'certfile':"<certfile>",
          'keyfile':"<keyfile>", 'tls_version':"<tls_version>",
          'ciphers':"<ciphers">, 'insecure':"<bool>"}
          ca_certs is required, all other parameters are optional and will
          default to None if not provided, which results in the client using
          the default behaviour - see the paho.mqtt.client documentation.
          Alternatively, tls input can be an SSLContext object, which will be
          processed using the tls_set_context method.
          Defaults to None, which indicates that TLS should not be used.

    :param str transport: set to "tcp" to use the default setting of transport which is
          raw TCP. Set to "websockets" to use WebSockets as the transport.

    :param proxy_args: a dictionary that will be given to the client.
    """

    if not isinstance(msgs, Iterable):
        raise TypeError('msgs must be an iterable')
    if len(msgs) == 0:
        raise ValueError('msgs is empty')

    client = paho.Client(
        CallbackAPIVersion.VERSION2,
        client_id=client_id,
        userdata=collections.deque(msgs),
        protocol=protocol,
        transport=transport,
    )

    client.enable_logger()
    client.on_publish = _on_publish
    client.on_connect = _on_connect  # type: ignore

    if proxy_args is not None:
        client.proxy_set(**proxy_args)

    if auth:
        username = auth.get('username')
        if username:
            password = auth.get('password')
            client.username_pw_set(username, password)
        else:
            raise KeyError("The 'username' key was not found, this is "
                           "required for auth")

    if will is not None:
        client.will_set(**will)

    if tls is not None:
        if isinstance(tls, dict):
            insecure = tls.pop('insecure', False)
            # mypy don't get that tls no longer contains the key insecure
            client.tls_set(**tls)  # type: ignore[misc]
            if insecure:
                # Must be set *after* the `client.tls_set()` call since it sets
                # up the SSL context that `client.tls_insecure_set` alters.
                client.tls_insecure_set(insecure)
        else:
            # Assume input is SSLContext object
            client.tls_set_context(tls)

    client.connect(hostname, port, keepalive)
    client.loop_forever()


def single(
    topic: str,
    payload: paho.PayloadType = None,
    qos: int = 0,
    retain: bool = False,
    hostname: str = "localhost",
    port: int = 1883,
    client_id: str = "",
    keepalive: int = 60,
    will: MessageDict | None = None,
    auth: AuthParameter | None = None,
    tls: TLSParameter | None = None,
    protocol: MQTTProtocolVersion = paho.MQTTv311,
    transport: Literal["tcp", "websockets"] = "tcp",
    proxy_args: Any | None = None,
) -> None:
    """Publish a single message to a broker, then disconnect cleanly.

    This function creates an MQTT client, connects to a broker and publishes a
    single message. Once the message has been delivered, it disconnects cleanly
    from the broker.

    :param str topic: the only required argument must be the topic string to which the
            payload will be published.

    :param payload: the payload to be published. If "" or None, a zero length payload
              will be published.

    :param int qos: the qos to use when publishing,  default to 0.

    :param bool retain: set the message to be retained (True) or not (False).

    :param str hostname: the address of the broker to connect to.
               Defaults to localhost.

    :param int port: the port to connect to the broker on. Defaults to 1883.

    :param str client_id: the MQTT client id to use. If "" or None, the Paho library will
                generate a client id automatically.

    :param int keepalive: the keepalive timeout value for the client. Defaults to 60
                seconds.

    :param will: a dict containing will parameters for the client: will = {'topic':
           "<topic>", 'payload':"<payload">, 'qos':<qos>, 'retain':<retain>}.
           Topic is required, all other parameters are optional and will
           default to None, 0 and False respectively.
           Defaults to None, which indicates no will should be used.

    :param auth: a dict containing authentication parameters for the client:
           Username is required, password is optional and will default to None
           auth = {'username':"<username>", 'password':"<password>"}
           if not provided.
           Defaults to None, which indicates no authentication is to be used.

    :param tls: a dict containing TLS configuration parameters for the client:
          dict = {'ca_certs':"<ca_certs>", 'certfile':"<certfile>",
          'keyfile':"<keyfile>", 'tls_version':"<tls_version>",
          'ciphers':"<ciphers">, 'insecure':"<bool>"}
          ca_certs is required, all other parameters are optional and will
          default to None if not provided, which results in the client using
          the default behaviour - see the paho.mqtt.client documentation.
          Defaults to None, which indicates that TLS should not be used.
          Alternatively, tls input can be an SSLContext object, which will be
          processed using the tls_set_context method.

    :param transport: set to "tcp" to use the default setting of transport which is
          raw TCP. Set to "websockets" to use WebSockets as the transport.

    :param proxy_args: a dictionary that will be given to the client.
    """

    msg: MessageDict = {'topic':topic, 'payload':payload, 'qos':qos, 'retain':retain}

    multiple([msg], hostname, port, client_id, keepalive, will, auth, tls,
             protocol, transport, proxy_args)
