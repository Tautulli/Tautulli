# Copyright (C) Dnspython Contributors, see LICENSE for text of ISC license

# Copyright (C) 2003-2017 Nominum, Inc.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose with or without fee is hereby granted,
# provided that the above copyright notice and this permission notice
# appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND NOMINUM DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL NOMINUM BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

"""Talk to a DNS server."""

import base64
import socket
import struct
import time

import dns.asyncbackend
import dns.exception
import dns.inet
import dns.name
import dns.message
import dns.rcode
import dns.rdataclass
import dns.rdatatype

from dns.query import _compute_times, _matches_destination, BadResponse, ssl, \
    UDPMode, _have_httpx, _have_http2, NoDOH

if _have_httpx:
    import httpx

# for brevity
_lltuple = dns.inet.low_level_address_tuple


def _source_tuple(af, address, port):
    # Make a high level source tuple, or return None if address and port
    # are both None
    if address or port:
        if address is None:
            if af == socket.AF_INET:
                address = '0.0.0.0'
            elif af == socket.AF_INET6:
                address = '::'
            else:
                raise NotImplementedError(f'unknown address family {af}')
        return (address, port)
    else:
        return None


def _timeout(expiration, now=None):
    if expiration:
        if not now:
            now = time.time()
        return max(expiration - now, 0)
    else:
        return None


async def send_udp(sock, what, destination, expiration=None):
    """Send a DNS message to the specified UDP socket.

    *sock*, a ``dns.asyncbackend.DatagramSocket``.

    *what*, a ``bytes`` or ``dns.message.Message``, the message to send.

    *destination*, a destination tuple appropriate for the address family
    of the socket, specifying where to send the query.

    *expiration*, a ``float`` or ``None``, the absolute time at which
    a timeout exception should be raised.  If ``None``, no timeout will
    occur.

    Returns an ``(int, float)`` tuple of bytes sent and the sent time.
    """

    if isinstance(what, dns.message.Message):
        what = what.to_wire()
    sent_time = time.time()
    n = await sock.sendto(what, destination, _timeout(expiration, sent_time))
    return (n, sent_time)


async def receive_udp(sock, destination=None, expiration=None,
                      ignore_unexpected=False, one_rr_per_rrset=False,
                      keyring=None, request_mac=b'', ignore_trailing=False,
                      raise_on_truncation=False):
    """Read a DNS message from a UDP socket.

    *sock*, a ``dns.asyncbackend.DatagramSocket``.

    See :py:func:`dns.query.receive_udp()` for the documentation of the other
    parameters, exceptions, and return type of this method.
    """

    wire = b''
    while 1:
        (wire, from_address) = await sock.recvfrom(65535, _timeout(expiration))
        if _matches_destination(sock.family, from_address, destination,
                                ignore_unexpected):
            break
    received_time = time.time()
    r = dns.message.from_wire(wire, keyring=keyring, request_mac=request_mac,
                              one_rr_per_rrset=one_rr_per_rrset,
                              ignore_trailing=ignore_trailing,
                              raise_on_truncation=raise_on_truncation)
    return (r, received_time, from_address)

async def udp(q, where, timeout=None, port=53, source=None, source_port=0,
              ignore_unexpected=False, one_rr_per_rrset=False,
              ignore_trailing=False, raise_on_truncation=False, sock=None,
              backend=None):
    """Return the response obtained after sending a query via UDP.

    *sock*, a ``dns.asyncbackend.DatagramSocket``, or ``None``,
    the socket to use for the query.  If ``None``, the default, a
    socket is created.  Note that if a socket is provided, the
    *source*, *source_port*, and *backend* are ignored.

    *backend*, a ``dns.asyncbackend.Backend``, or ``None``.  If ``None``,
    the default, then dnspython will use the default backend.

    See :py:func:`dns.query.udp()` for the documentation of the other
    parameters, exceptions, and return type of this method.
    """
    wire = q.to_wire()
    (begin_time, expiration) = _compute_times(timeout)
    s = None
    # After 3.6 is no longer supported, this can use an AsyncExitStack.
    try:
        af = dns.inet.af_for_address(where)
        destination = _lltuple((where, port), af)
        if sock:
            s = sock
        else:
            if not backend:
                backend = dns.asyncbackend.get_default_backend()
            stuple = _source_tuple(af, source, source_port)
            if backend.datagram_connection_required():
                dtuple = (where, port)
            else:
                dtuple = None
            s = await backend.make_socket(af, socket.SOCK_DGRAM, 0, stuple,
                                          dtuple)
        await send_udp(s, wire, destination, expiration)
        (r, received_time, _) = await receive_udp(s, destination, expiration,
                                                  ignore_unexpected,
                                                  one_rr_per_rrset,
                                                  q.keyring, q.mac,
                                                  ignore_trailing,
                                                  raise_on_truncation)
        r.time = received_time - begin_time
        if not q.is_response(r):
            raise BadResponse
        return r
    finally:
        if not sock and s:
            await s.close()

async def udp_with_fallback(q, where, timeout=None, port=53, source=None,
                            source_port=0, ignore_unexpected=False,
                            one_rr_per_rrset=False, ignore_trailing=False,
                            udp_sock=None, tcp_sock=None, backend=None):
    """Return the response to the query, trying UDP first and falling back
    to TCP if UDP results in a truncated response.

    *udp_sock*, a ``dns.asyncbackend.DatagramSocket``, or ``None``,
    the socket to use for the UDP query.  If ``None``, the default, a
    socket is created.  Note that if a socket is provided the *source*,
    *source_port*, and *backend* are ignored for the UDP query.

    *tcp_sock*, a ``dns.asyncbackend.StreamSocket``, or ``None``, the
    socket to use for the TCP query.  If ``None``, the default, a
    socket is created.  Note that if a socket is provided *where*,
    *source*, *source_port*, and *backend*  are ignored for the TCP query.

    *backend*, a ``dns.asyncbackend.Backend``, or ``None``.  If ``None``,
    the default, then dnspython will use the default backend.

    See :py:func:`dns.query.udp_with_fallback()` for the documentation
    of the other parameters, exceptions, and return type of this
    method.
    """
    try:
        response = await udp(q, where, timeout, port, source, source_port,
                             ignore_unexpected, one_rr_per_rrset,
                             ignore_trailing, True, udp_sock, backend)
        return (response, False)
    except dns.message.Truncated:
        response = await tcp(q, where, timeout, port, source, source_port,
                             one_rr_per_rrset, ignore_trailing, tcp_sock,
                             backend)
        return (response, True)


async def send_tcp(sock, what, expiration=None):
    """Send a DNS message to the specified TCP socket.

    *sock*, a ``dns.asyncbackend.StreamSocket``.

    See :py:func:`dns.query.send_tcp()` for the documentation of the other
    parameters, exceptions, and return type of this method.
    """

    if isinstance(what, dns.message.Message):
        what = what.to_wire()
    l = len(what)
    # copying the wire into tcpmsg is inefficient, but lets us
    # avoid writev() or doing a short write that would get pushed
    # onto the net
    tcpmsg = struct.pack("!H", l) + what
    sent_time = time.time()
    await sock.sendall(tcpmsg, _timeout(expiration, sent_time))
    return (len(tcpmsg), sent_time)


async def _read_exactly(sock, count, expiration):
    """Read the specified number of bytes from stream.  Keep trying until we
    either get the desired amount, or we hit EOF.
    """
    s = b''
    while count > 0:
        n = await sock.recv(count, _timeout(expiration))
        if n == b'':
            raise EOFError
        count = count - len(n)
        s = s + n
    return s


async def receive_tcp(sock, expiration=None, one_rr_per_rrset=False,
                      keyring=None, request_mac=b'', ignore_trailing=False):
    """Read a DNS message from a TCP socket.

    *sock*, a ``dns.asyncbackend.StreamSocket``.

    See :py:func:`dns.query.receive_tcp()` for the documentation of the other
    parameters, exceptions, and return type of this method.
    """

    ldata = await _read_exactly(sock, 2, expiration)
    (l,) = struct.unpack("!H", ldata)
    wire = await _read_exactly(sock, l, expiration)
    received_time = time.time()
    r = dns.message.from_wire(wire, keyring=keyring, request_mac=request_mac,
                              one_rr_per_rrset=one_rr_per_rrset,
                              ignore_trailing=ignore_trailing)
    return (r, received_time)


async def tcp(q, where, timeout=None, port=53, source=None, source_port=0,
              one_rr_per_rrset=False, ignore_trailing=False, sock=None,
              backend=None):
    """Return the response obtained after sending a query via TCP.

    *sock*, a ``dns.asyncbacket.StreamSocket``, or ``None``, the
    socket to use for the query.  If ``None``, the default, a socket
    is created.  Note that if a socket is provided
    *where*, *port*, *source*, *source_port*, and *backend* are ignored.

    *backend*, a ``dns.asyncbackend.Backend``, or ``None``.  If ``None``,
    the default, then dnspython will use the default backend.

    See :py:func:`dns.query.tcp()` for the documentation of the other
    parameters, exceptions, and return type of this method.
    """

    wire = q.to_wire()
    (begin_time, expiration) = _compute_times(timeout)
    s = None
    # After 3.6 is no longer supported, this can use an AsyncExitStack.
    try:
        if sock:
            # Verify that the socket is connected, as if it's not connected,
            # it's not writable, and the polling in send_tcp() will time out or
            # hang forever.
            await sock.getpeername()
            s = sock
        else:
            # These are simple (address, port) pairs, not
            # family-dependent tuples you pass to lowlevel socket
            # code.
            af = dns.inet.af_for_address(where)
            stuple = _source_tuple(af, source, source_port)
            dtuple = (where, port)
            if not backend:
                backend = dns.asyncbackend.get_default_backend()
            s = await backend.make_socket(af, socket.SOCK_STREAM, 0, stuple,
                                          dtuple, timeout)
        await send_tcp(s, wire, expiration)
        (r, received_time) = await receive_tcp(s, expiration, one_rr_per_rrset,
                                               q.keyring, q.mac,
                                               ignore_trailing)
        r.time = received_time - begin_time
        if not q.is_response(r):
            raise BadResponse
        return r
    finally:
        if not sock and s:
            await s.close()

async def tls(q, where, timeout=None, port=853, source=None, source_port=0,
              one_rr_per_rrset=False, ignore_trailing=False, sock=None,
              backend=None, ssl_context=None, server_hostname=None):
    """Return the response obtained after sending a query via TLS.

    *sock*, an ``asyncbackend.StreamSocket``, or ``None``, the socket
    to use for the query.  If ``None``, the default, a socket is
    created.  Note that if a socket is provided, it must be a
    connected SSL stream socket, and *where*, *port*,
    *source*, *source_port*, *backend*, *ssl_context*, and *server_hostname*
    are ignored.

    *backend*, a ``dns.asyncbackend.Backend``, or ``None``.  If ``None``,
    the default, then dnspython will use the default backend.

    See :py:func:`dns.query.tls()` for the documentation of the other
    parameters, exceptions, and return type of this method.
    """
    # After 3.6 is no longer supported, this can use an AsyncExitStack.
    (begin_time, expiration) = _compute_times(timeout)
    if not sock:
        if ssl_context is None:
            ssl_context = ssl.create_default_context()
            if server_hostname is None:
                ssl_context.check_hostname = False
        else:
            ssl_context = None
            server_hostname = None
        af = dns.inet.af_for_address(where)
        stuple = _source_tuple(af, source, source_port)
        dtuple = (where, port)
        if not backend:
            backend = dns.asyncbackend.get_default_backend()
        s = await backend.make_socket(af, socket.SOCK_STREAM, 0, stuple,
                                      dtuple, timeout, ssl_context,
                                      server_hostname)
    else:
        s = sock
    try:
        timeout = _timeout(expiration)
        response = await tcp(q, where, timeout, port, source, source_port,
                             one_rr_per_rrset, ignore_trailing, s, backend)
        end_time = time.time()
        response.time = end_time - begin_time
        return response
    finally:
        if not sock and s:
            await s.close()

async def https(q, where, timeout=None, port=443, source=None, source_port=0,
                one_rr_per_rrset=False, ignore_trailing=False, client=None,
                path='/dns-query', post=True, verify=True):
    """Return the response obtained after sending a query via DNS-over-HTTPS.

    *client*, a ``httpx.AsyncClient``.  If provided, the client to use for
    the query.

    Unlike the other dnspython async functions, a backend cannot be provided
    in this function because httpx always auto-detects the async backend.

    See :py:func:`dns.query.https()` for the documentation of the other
    parameters, exceptions, and return type of this method.
    """

    if not _have_httpx:
        raise NoDOH('httpx is not available.')  # pragma: no cover

    wire = q.to_wire()
    try:
        af = dns.inet.af_for_address(where)
    except ValueError:
        af = None
    transport = None
    headers = {
        "accept": "application/dns-message"
    }
    if af is not None:
        if af == socket.AF_INET:
            url = 'https://{}:{}{}'.format(where, port, path)
        elif af == socket.AF_INET6:
            url = 'https://[{}]:{}{}'.format(where, port, path)
    else:
        url = where
    if source is not None:
        transport = httpx.AsyncHTTPTransport(local_address=source[0])

    # After 3.6 is no longer supported, this can use an AsyncExitStack
    client_to_close = None
    try:
        if not client:
            client = httpx.AsyncClient(http1=True, http2=_have_http2,
                                       verify=verify, transport=transport)
            client_to_close = client

        # see https://tools.ietf.org/html/rfc8484#section-4.1.1 for DoH
        # GET and POST examples
        if post:
            headers.update({
                "content-type": "application/dns-message",
                "content-length": str(len(wire))
            })
            response = await client.post(url, headers=headers, content=wire,
                                         timeout=timeout)
        else:
            wire = base64.urlsafe_b64encode(wire).rstrip(b"=")
            wire = wire.decode()  # httpx does a repr() if we give it bytes
            response = await client.get(url, headers=headers, timeout=timeout,
                                        params={"dns": wire})
    finally:
        if client_to_close:
            await client.aclose()

    # see https://tools.ietf.org/html/rfc8484#section-4.2.1 for info about DoH
    # status codes
    if response.status_code < 200 or response.status_code > 299:
        raise ValueError('{} responded with status code {}'
                         '\nResponse body: {}'.format(where,
                                                      response.status_code,
                                                      response.content))
    r = dns.message.from_wire(response.content,
                              keyring=q.keyring,
                              request_mac=q.request_mac,
                              one_rr_per_rrset=one_rr_per_rrset,
                              ignore_trailing=ignore_trailing)
    r.time = response.elapsed
    if not q.is_response(r):
        raise BadResponse
    return r

async def inbound_xfr(where, txn_manager, query=None,
                      port=53, timeout=None, lifetime=None, source=None,
                      source_port=0, udp_mode=UDPMode.NEVER, backend=None):
    """Conduct an inbound transfer and apply it via a transaction from the
    txn_manager.

    *backend*, a ``dns.asyncbackend.Backend``, or ``None``.  If ``None``,
    the default, then dnspython will use the default backend.

    See :py:func:`dns.query.inbound_xfr()` for the documentation of
    the other parameters, exceptions, and return type of this method.
    """
    if query is None:
        (query, serial) = dns.xfr.make_query(txn_manager)
    else:
        serial = dns.xfr.extract_serial_from_query(query)
    rdtype = query.question[0].rdtype
    is_ixfr = rdtype == dns.rdatatype.IXFR
    origin = txn_manager.from_wire_origin()
    wire = query.to_wire()
    af = dns.inet.af_for_address(where)
    stuple = _source_tuple(af, source, source_port)
    dtuple = (where, port)
    (_, expiration) = _compute_times(lifetime)
    retry = True
    while retry:
        retry = False
        if is_ixfr and udp_mode != UDPMode.NEVER:
            sock_type = socket.SOCK_DGRAM
            is_udp = True
        else:
            sock_type = socket.SOCK_STREAM
            is_udp = False
        if not backend:
            backend = dns.asyncbackend.get_default_backend()
        s = await backend.make_socket(af, sock_type, 0, stuple, dtuple,
                                      _timeout(expiration))
        async with s:
            if is_udp:
                await s.sendto(wire, dtuple, _timeout(expiration))
            else:
                tcpmsg = struct.pack("!H", len(wire)) + wire
                await s.sendall(tcpmsg, expiration)
            with dns.xfr.Inbound(txn_manager, rdtype, serial,
                                 is_udp) as inbound:
                done = False
                tsig_ctx = None
                while not done:
                    (_, mexpiration) = _compute_times(timeout)
                    if mexpiration is None or \
                       (expiration is not None and mexpiration > expiration):
                        mexpiration = expiration
                    if is_udp:
                        destination = _lltuple((where, port), af)
                        while True:
                            timeout = _timeout(mexpiration)
                            (rwire, from_address) = await s.recvfrom(65535,
                                                                     timeout)
                            if _matches_destination(af, from_address,
                                                    destination, True):
                                break
                    else:
                        ldata = await _read_exactly(s, 2, mexpiration)
                        (l,) = struct.unpack("!H", ldata)
                        rwire = await _read_exactly(s, l, mexpiration)
                    is_ixfr = (rdtype == dns.rdatatype.IXFR)
                    r = dns.message.from_wire(rwire, keyring=query.keyring,
                                              request_mac=query.mac, xfr=True,
                                              origin=origin, tsig_ctx=tsig_ctx,
                                              multi=(not is_udp),
                                              one_rr_per_rrset=is_ixfr)
                    try:
                        done = inbound.process_message(r)
                    except dns.xfr.UseTCP:
                        assert is_udp  # should not happen if we used TCP!
                        if udp_mode == UDPMode.ONLY:
                            raise
                        done = True
                        retry = True
                        udp_mode = UDPMode.NEVER
                        continue
                    tsig_ctx = r.tsig_ctx
                if not retry and query.keyring and not r.had_tsig:
                    raise dns.exception.FormError("missing TSIG")
