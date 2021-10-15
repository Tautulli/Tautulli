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

import contextlib
import errno
import os
import select
import socket
import struct
import time
import base64
import urllib.parse

import dns.exception
import dns.inet
import dns.name
import dns.message
import dns.rcode
import dns.rdataclass
import dns.rdatatype
import dns.serial

try:
    import requests
    from requests_toolbelt.adapters.source import SourceAddressAdapter
    from requests_toolbelt.adapters.host_header_ssl import HostHeaderSSLAdapter
    have_doh = True
except ImportError:  # pragma: no cover
    have_doh = False

try:
    import ssl
except ImportError:  # pragma: no cover
    class ssl:    # type: ignore

        class WantReadException(Exception):
            pass

        class WantWriteException(Exception):
            pass

        class SSLSocket:
            pass

        def create_default_context(self, *args, **kwargs):
            raise Exception('no ssl support')

# Function used to create a socket.  Can be overridden if needed in special
# situations.
socket_factory = socket.socket

class UnexpectedSource(dns.exception.DNSException):
    """A DNS query response came from an unexpected address or port."""


class BadResponse(dns.exception.FormError):
    """A DNS query response does not respond to the question asked."""


class TransferError(dns.exception.DNSException):
    """A zone transfer response got a non-zero rcode."""

    def __init__(self, rcode):
        message = 'Zone transfer error: %s' % dns.rcode.to_text(rcode)
        super().__init__(message)
        self.rcode = rcode


class NoDOH(dns.exception.DNSException):
    """DNS over HTTPS (DOH) was requested but the requests module is not
    available."""


def _compute_times(timeout):
    now = time.time()
    if timeout is None:
        return (now, None)
    else:
        return (now, now + timeout)

# This module can use either poll() or select() as the "polling backend".
#
# A backend function takes an fd, bools for readability, writablity, and
# error detection, and a timeout.

def _poll_for(fd, readable, writable, error, timeout):
    """Poll polling backend."""

    event_mask = 0
    if readable:
        event_mask |= select.POLLIN
    if writable:
        event_mask |= select.POLLOUT
    if error:
        event_mask |= select.POLLERR

    pollable = select.poll()
    pollable.register(fd, event_mask)

    if timeout:
        event_list = pollable.poll(timeout * 1000)
    else:
        event_list = pollable.poll()

    return bool(event_list)


def _select_for(fd, readable, writable, error, timeout):
    """Select polling backend."""

    rset, wset, xset = [], [], []

    if readable:
        rset = [fd]
    if writable:
        wset = [fd]
    if error:
        xset = [fd]

    if timeout is None:
        (rcount, wcount, xcount) = select.select(rset, wset, xset)
    else:
        (rcount, wcount, xcount) = select.select(rset, wset, xset, timeout)

    return bool((rcount or wcount or xcount))


def _wait_for(fd, readable, writable, error, expiration):
    # Use the selected polling backend to wait for any of the specified
    # events.  An "expiration" absolute time is converted into a relative
    # timeout.

    done = False
    while not done:
        if expiration is None:
            timeout = None
        else:
            timeout = expiration - time.time()
            if timeout <= 0.0:
                raise dns.exception.Timeout
        try:
            if isinstance(fd, ssl.SSLSocket) and readable and fd.pending() > 0:
                return True
            if not _polling_backend(fd, readable, writable, error, timeout):
                raise dns.exception.Timeout
        except OSError as e:  # pragma: no cover
            if e.args[0] != errno.EINTR:
                raise e
        done = True


def _set_polling_backend(fn):
    # Internal API. Do not use.

    global _polling_backend

    _polling_backend = fn

if hasattr(select, 'poll'):
    # Prefer poll() on platforms that support it because it has no
    # limits on the maximum value of a file descriptor (plus it will
    # be more efficient for high values).
    _polling_backend = _poll_for
else:
    _polling_backend = _select_for  # pragma: no cover


def _wait_for_readable(s, expiration):
    _wait_for(s, True, False, True, expiration)


def _wait_for_writable(s, expiration):
    _wait_for(s, False, True, True, expiration)


def _addresses_equal(af, a1, a2):
    # Convert the first value of the tuple, which is a textual format
    # address into binary form, so that we are not confused by different
    # textual representations of the same address
    try:
        n1 = dns.inet.inet_pton(af, a1[0])
        n2 = dns.inet.inet_pton(af, a2[0])
    except dns.exception.SyntaxError:
        return False
    return n1 == n2 and a1[1:] == a2[1:]


def _matches_destination(af, from_address, destination, ignore_unexpected):
    # Check that from_address is appropriate for a response to a query
    # sent to destination.
    if not destination:
        return True
    if _addresses_equal(af, from_address, destination) or \
       (dns.inet.is_multicast(destination[0]) and
        from_address[1:] == destination[1:]):
        return True
    elif ignore_unexpected:
        return False
    raise UnexpectedSource(f'got a response from {from_address} instead of '
                           f'{destination}')


def _destination_and_source(where, port, source, source_port,
                            where_must_be_address=True):
    # Apply defaults and compute destination and source tuples
    # suitable for use in connect(), sendto(), or bind().
    af = None
    destination = None
    try:
        af = dns.inet.af_for_address(where)
        destination = where
    except Exception:
        if where_must_be_address:
            raise
        # URLs are ok so eat the exception
    if source:
        saf = dns.inet.af_for_address(source)
        if af:
            # We know the destination af, so source had better agree!
            if saf != af:
                raise ValueError('different address families for source ' +
                                 'and destination')
        else:
            # We didn't know the destination af, but we know the source,
            # so that's our af.
            af = saf
    if source_port and not source:
        # Caller has specified a source_port but not an address, so we
        # need to return a source, and we need to use the appropriate
        # wildcard address as the address.
        if af == socket.AF_INET:
            source = '0.0.0.0'
        elif af == socket.AF_INET6:
            source = '::'
        else:
            raise ValueError('source_port specified but address family is '
                             'unknown')
    # Convert high-level (address, port) tuples into low-level address
    # tuples.
    if destination:
        destination = dns.inet.low_level_address_tuple((destination, port), af)
    if source:
        source = dns.inet.low_level_address_tuple((source, source_port), af)
    return (af, destination, source)

def _make_socket(af, type, source, ssl_context=None, server_hostname=None):
    s = socket_factory(af, type)
    try:
        s.setblocking(False)
        if source is not None:
            s.bind(source)
        if ssl_context:
            return ssl_context.wrap_socket(s, do_handshake_on_connect=False,
                                           server_hostname=server_hostname)
        else:
            return s
    except Exception:
        s.close()
        raise

def https(q, where, timeout=None, port=443, source=None, source_port=0,
          one_rr_per_rrset=False, ignore_trailing=False,
          session=None, path='/dns-query', post=True,
          bootstrap_address=None, verify=True):
    """Return the response obtained after sending a query via DNS-over-HTTPS.

    *q*, a ``dns.message.Message``, the query to send.

    *where*, a ``str``, the nameserver IP address or the full URL. If an IP
    address is given, the URL will be constructed using the following schema:
    https://<IP-address>:<port>/<path>.

    *timeout*, a ``float`` or ``None``, the number of seconds to
    wait before the query times out. If ``None``, the default, wait forever.

    *port*, a ``int``, the port to send the query to. The default is 443.

    *source*, a ``str`` containing an IPv4 or IPv6 address, specifying
    the source address.  The default is the wildcard address.

    *source_port*, an ``int``, the port from which to send the message.
    The default is 0.

    *one_rr_per_rrset*, a ``bool``. If ``True``, put each RR into its own
    RRset.

    *ignore_trailing*, a ``bool``. If ``True``, ignore trailing
    junk at end of the received message.

    *session*, a ``requests.session.Session``.  If provided, the session to use
    to send the queries.

    *path*, a ``str``. If *where* is an IP address, then *path* will be used to
    construct the URL to send the DNS query to.

    *post*, a ``bool``. If ``True``, the default, POST method will be used.

    *bootstrap_address*, a ``str``, the IP address to use to bypass the
    system's DNS resolver.

    *verify*, a ``str``, containing a path to a certificate file or directory.

    Returns a ``dns.message.Message``.
    """

    if not have_doh:
        raise NoDOH  # pragma: no cover

    wire = q.to_wire()
    (af, destination, source) = _destination_and_source(where, port,
                                                        source, source_port,
                                                        False)
    transport_adapter = None
    headers = {
        "accept": "application/dns-message"
    }
    try:
        where_af = dns.inet.af_for_address(where)
        if where_af == socket.AF_INET:
            url = 'https://{}:{}{}'.format(where, port, path)
        elif where_af == socket.AF_INET6:
            url = 'https://[{}]:{}{}'.format(where, port, path)
    except ValueError:
        if bootstrap_address is not None:
            split_url = urllib.parse.urlsplit(where)
            headers['Host'] = split_url.hostname
            url = where.replace(split_url.hostname, bootstrap_address)
            transport_adapter = HostHeaderSSLAdapter()
        else:
            url = where
    if source is not None:
        # set source port and source address
        transport_adapter = SourceAddressAdapter(source)

    with contextlib.ExitStack() as stack:
        if not session:
            session = stack.enter_context(requests.sessions.Session())

        if transport_adapter:
            session.mount(url, transport_adapter)

        # see https://tools.ietf.org/html/rfc8484#section-4.1.1 for DoH
        # GET and POST examples
        if post:
            headers.update({
                "content-type": "application/dns-message",
                "content-length": str(len(wire))
            })
            response = session.post(url, headers=headers, data=wire,
                                    timeout=timeout, verify=verify)
        else:
            wire = base64.urlsafe_b64encode(wire).rstrip(b"=")
            response = session.get(url, headers=headers,
                                   timeout=timeout, verify=verify,
                                   params={"dns": wire})

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

def send_udp(sock, what, destination, expiration=None):
    """Send a DNS message to the specified UDP socket.

    *sock*, a ``socket``.

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
    _wait_for_writable(sock, expiration)
    sent_time = time.time()
    n = sock.sendto(what, destination)
    return (n, sent_time)


def receive_udp(sock, destination=None, expiration=None,
                ignore_unexpected=False, one_rr_per_rrset=False,
                keyring=None, request_mac=b'', ignore_trailing=False,
                raise_on_truncation=False):
    """Read a DNS message from a UDP socket.

    *sock*, a ``socket``.

    *destination*, a destination tuple appropriate for the address family
    of the socket, specifying where the message is expected to arrive from.
    When receiving a response, this would be where the associated query was
    sent.

    *expiration*, a ``float`` or ``None``, the absolute time at which
    a timeout exception should be raised.  If ``None``, no timeout will
    occur.

    *ignore_unexpected*, a ``bool``.  If ``True``, ignore responses from
    unexpected sources.

    *one_rr_per_rrset*, a ``bool``.  If ``True``, put each RR into its own
    RRset.

    *keyring*, a ``dict``, the keyring to use for TSIG.

    *request_mac*, a ``bytes``, the MAC of the request (for TSIG).

    *ignore_trailing*, a ``bool``.  If ``True``, ignore trailing
    junk at end of the received message.

    *raise_on_truncation*, a ``bool``.  If ``True``, raise an exception if
    the TC bit is set.

    Raises if the message is malformed, if network errors occur, of if
    there is a timeout.

    If *destination* is not ``None``, returns a ``(dns.message.Message, float)``
    tuple of the received message and the received time.

    If *destination* is ``None``, returns a
    ``(dns.message.Message, float, tuple)``
    tuple of the received message, the received time, and the address where
    the message arrived from.
    """

    wire = b''
    while 1:
        _wait_for_readable(sock, expiration)
        (wire, from_address) = sock.recvfrom(65535)
        if _matches_destination(sock.family, from_address, destination,
                                ignore_unexpected):
            break
    received_time = time.time()
    r = dns.message.from_wire(wire, keyring=keyring, request_mac=request_mac,
                              one_rr_per_rrset=one_rr_per_rrset,
                              ignore_trailing=ignore_trailing,
                              raise_on_truncation=raise_on_truncation)
    if destination:
        return (r, received_time)
    else:
        return (r, received_time, from_address)

def udp(q, where, timeout=None, port=53, source=None, source_port=0,
        ignore_unexpected=False, one_rr_per_rrset=False, ignore_trailing=False,
        raise_on_truncation=False, sock=None):
    """Return the response obtained after sending a query via UDP.

    *q*, a ``dns.message.Message``, the query to send

    *where*, a ``str`` containing an IPv4 or IPv6 address,  where
    to send the message.

    *timeout*, a ``float`` or ``None``, the number of seconds to wait before the
    query times out.  If ``None``, the default, wait forever.

    *port*, an ``int``, the port send the message to.  The default is 53.

    *source*, a ``str`` containing an IPv4 or IPv6 address, specifying
    the source address.  The default is the wildcard address.

    *source_port*, an ``int``, the port from which to send the message.
    The default is 0.

    *ignore_unexpected*, a ``bool``.  If ``True``, ignore responses from
    unexpected sources.

    *one_rr_per_rrset*, a ``bool``.  If ``True``, put each RR into its own
    RRset.

    *ignore_trailing*, a ``bool``.  If ``True``, ignore trailing
    junk at end of the received message.

    *raise_on_truncation*, a ``bool``.  If ``True``, raise an exception if
    the TC bit is set.

    *sock*, a ``socket.socket``, or ``None``, the socket to use for the
    query.  If ``None``, the default, a socket is created.  Note that
    if a socket is provided, it must be a nonblocking datagram socket,
    and the *source* and *source_port* are ignored.

    Returns a ``dns.message.Message``.
    """

    wire = q.to_wire()
    (af, destination, source) = _destination_and_source(where, port,
                                                        source, source_port)
    (begin_time, expiration) = _compute_times(timeout)
    with contextlib.ExitStack() as stack:
        if sock:
            s = sock
        else:
            s = stack.enter_context(_make_socket(af, socket.SOCK_DGRAM, source))
        send_udp(s, wire, destination, expiration)
        (r, received_time) = receive_udp(s, destination, expiration,
                                         ignore_unexpected, one_rr_per_rrset,
                                         q.keyring, q.mac, ignore_trailing,
                                         raise_on_truncation)
        r.time = received_time - begin_time
        if not q.is_response(r):
            raise BadResponse
        return r

def udp_with_fallback(q, where, timeout=None, port=53, source=None,
                      source_port=0, ignore_unexpected=False,
                      one_rr_per_rrset=False, ignore_trailing=False,
                      udp_sock=None, tcp_sock=None):
    """Return the response to the query, trying UDP first and falling back
    to TCP if UDP results in a truncated response.

    *q*, a ``dns.message.Message``, the query to send

    *where*, a ``str`` containing an IPv4 or IPv6 address,  where
    to send the message.

    *timeout*, a ``float`` or ``None``, the number of seconds to wait before the
    query times out.  If ``None``, the default, wait forever.

    *port*, an ``int``, the port send the message to.  The default is 53.

    *source*, a ``str`` containing an IPv4 or IPv6 address, specifying
    the source address.  The default is the wildcard address.

    *source_port*, an ``int``, the port from which to send the message.
    The default is 0.

    *ignore_unexpected*, a ``bool``.  If ``True``, ignore responses from
    unexpected sources.

    *one_rr_per_rrset*, a ``bool``.  If ``True``, put each RR into its own
    RRset.

    *ignore_trailing*, a ``bool``.  If ``True``, ignore trailing
    junk at end of the received message.

    *udp_sock*, a ``socket.socket``, or ``None``, the socket to use for the
    UDP query.  If ``None``, the default, a socket is created.  Note that
    if a socket is provided, it must be a nonblocking datagram socket,
    and the *source* and *source_port* are ignored for the UDP query.

    *tcp_sock*, a ``socket.socket``, or ``None``, the socket to use for the
    TCP query.  If ``None``, the default, a socket is created.  Note that
    if a socket is provided, it must be a nonblocking connected stream
    socket, and *where*, *source* and *source_port* are ignored for the TCP
    query.

    Returns a (``dns.message.Message``, tcp) tuple where tcp is ``True``
    if and only if TCP was used.
    """
    try:
        response = udp(q, where, timeout, port, source, source_port,
                       ignore_unexpected, one_rr_per_rrset,
                       ignore_trailing, True, udp_sock)
        return (response, False)
    except dns.message.Truncated:
        response = tcp(q, where, timeout, port, source, source_port,
                       one_rr_per_rrset, ignore_trailing, tcp_sock)
        return (response, True)

def _net_read(sock, count, expiration):
    """Read the specified number of bytes from sock.  Keep trying until we
    either get the desired amount, or we hit EOF.
    A Timeout exception will be raised if the operation is not completed
    by the expiration time.
    """
    s = b''
    while count > 0:
        _wait_for_readable(sock, expiration)
        try:
            n = sock.recv(count)
        except ssl.SSLWantReadError:  # pragma: no cover
            continue
        except ssl.SSLWantWriteError:  # pragma: no cover
            _wait_for_writable(sock, expiration)
            continue
        if n == b'':
            raise EOFError
        count = count - len(n)
        s = s + n
    return s


def _net_write(sock, data, expiration):
    """Write the specified data to the socket.
    A Timeout exception will be raised if the operation is not completed
    by the expiration time.
    """
    current = 0
    l = len(data)
    while current < l:
        _wait_for_writable(sock, expiration)
        try:
            current += sock.send(data[current:])
        except ssl.SSLWantReadError:  # pragma: no cover
            _wait_for_readable(sock, expiration)
            continue
        except ssl.SSLWantWriteError:  # pragma: no cover
            continue


def send_tcp(sock, what, expiration=None):
    """Send a DNS message to the specified TCP socket.

    *sock*, a ``socket``.

    *what*, a ``bytes`` or ``dns.message.Message``, the message to send.

    *expiration*, a ``float`` or ``None``, the absolute time at which
    a timeout exception should be raised.  If ``None``, no timeout will
    occur.

    Returns an ``(int, float)`` tuple of bytes sent and the sent time.
    """

    if isinstance(what, dns.message.Message):
        what = what.to_wire()
    l = len(what)
    # copying the wire into tcpmsg is inefficient, but lets us
    # avoid writev() or doing a short write that would get pushed
    # onto the net
    tcpmsg = struct.pack("!H", l) + what
    _wait_for_writable(sock, expiration)
    sent_time = time.time()
    _net_write(sock, tcpmsg, expiration)
    return (len(tcpmsg), sent_time)

def receive_tcp(sock, expiration=None, one_rr_per_rrset=False,
                keyring=None, request_mac=b'', ignore_trailing=False):
    """Read a DNS message from a TCP socket.

    *sock*, a ``socket``.

    *expiration*, a ``float`` or ``None``, the absolute time at which
    a timeout exception should be raised.  If ``None``, no timeout will
    occur.

    *one_rr_per_rrset*, a ``bool``.  If ``True``, put each RR into its own
    RRset.

    *keyring*, a ``dict``, the keyring to use for TSIG.

    *request_mac*, a ``bytes``, the MAC of the request (for TSIG).

    *ignore_trailing*, a ``bool``.  If ``True``, ignore trailing
    junk at end of the received message.

    Raises if the message is malformed, if network errors occur, of if
    there is a timeout.

    Returns a ``(dns.message.Message, float)`` tuple of the received message
    and the received time.
    """

    ldata = _net_read(sock, 2, expiration)
    (l,) = struct.unpack("!H", ldata)
    wire = _net_read(sock, l, expiration)
    received_time = time.time()
    r = dns.message.from_wire(wire, keyring=keyring, request_mac=request_mac,
                              one_rr_per_rrset=one_rr_per_rrset,
                              ignore_trailing=ignore_trailing)
    return (r, received_time)

def _connect(s, address, expiration):
    err = s.connect_ex(address)
    if err == 0:
        return
    if err in (errno.EINPROGRESS, errno.EWOULDBLOCK, errno.EALREADY):
        _wait_for_writable(s, expiration)
        err = s.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
    if err != 0:
        raise OSError(err, os.strerror(err))


def tcp(q, where, timeout=None, port=53, source=None, source_port=0,
        one_rr_per_rrset=False, ignore_trailing=False, sock=None):
    """Return the response obtained after sending a query via TCP.

    *q*, a ``dns.message.Message``, the query to send

    *where*, a ``str`` containing an IPv4 or IPv6 address, where
    to send the message.

    *timeout*, a ``float`` or ``None``, the number of seconds to wait before the
    query times out.  If ``None``, the default, wait forever.

    *port*, an ``int``, the port send the message to.  The default is 53.

    *source*, a ``str`` containing an IPv4 or IPv6 address, specifying
    the source address.  The default is the wildcard address.

    *source_port*, an ``int``, the port from which to send the message.
    The default is 0.

    *one_rr_per_rrset*, a ``bool``.  If ``True``, put each RR into its own
    RRset.

    *ignore_trailing*, a ``bool``.  If ``True``, ignore trailing
    junk at end of the received message.

    *sock*, a ``socket.socket``, or ``None``, the socket to use for the
    query.  If ``None``, the default, a socket is created.  Note that
    if a socket is provided, it must be a nonblocking connected stream
    socket, and *where*, *port*, *source* and *source_port* are ignored.

    Returns a ``dns.message.Message``.
    """

    wire = q.to_wire()
    (begin_time, expiration) = _compute_times(timeout)
    with contextlib.ExitStack() as stack:
        if sock:
            #
            # Verify that the socket is connected, as if it's not connected,
            # it's not writable, and the polling in send_tcp() will time out or
            # hang forever.
            sock.getpeername()
            s = sock
        else:
            (af, destination, source) = _destination_and_source(where, port,
                                                                source,
                                                                source_port)
            s = stack.enter_context(_make_socket(af, socket.SOCK_STREAM,
                                                 source))
            _connect(s, destination, expiration)
        send_tcp(s, wire, expiration)
        (r, received_time) = receive_tcp(s, expiration, one_rr_per_rrset,
                                         q.keyring, q.mac, ignore_trailing)
        r.time = received_time - begin_time
        if not q.is_response(r):
            raise BadResponse
        return r


def _tls_handshake(s, expiration):
    while True:
        try:
            s.do_handshake()
            return
        except ssl.SSLWantReadError:
            _wait_for_readable(s, expiration)
        except ssl.SSLWantWriteError:  # pragma: no cover
            _wait_for_writable(s, expiration)


def tls(q, where, timeout=None, port=853, source=None, source_port=0,
        one_rr_per_rrset=False, ignore_trailing=False, sock=None,
        ssl_context=None, server_hostname=None):
    """Return the response obtained after sending a query via TLS.

    *q*, a ``dns.message.Message``, the query to send

    *where*, a ``str`` containing an IPv4 or IPv6 address,  where
    to send the message.

    *timeout*, a ``float`` or ``None``, the number of seconds to wait before the
    query times out.  If ``None``, the default, wait forever.

    *port*, an ``int``, the port send the message to.  The default is 853.

    *source*, a ``str`` containing an IPv4 or IPv6 address, specifying
    the source address.  The default is the wildcard address.

    *source_port*, an ``int``, the port from which to send the message.
    The default is 0.

    *one_rr_per_rrset*, a ``bool``.  If ``True``, put each RR into its own
    RRset.

    *ignore_trailing*, a ``bool``.  If ``True``, ignore trailing
    junk at end of the received message.

    *sock*, an ``ssl.SSLSocket``, or ``None``, the socket to use for
    the query.  If ``None``, the default, a socket is created.  Note
    that if a socket is provided, it must be a nonblocking connected
    SSL stream socket, and *where*, *port*, *source*, *source_port*,
    and *ssl_context* are ignored.

    *ssl_context*, an ``ssl.SSLContext``, the context to use when establishing
    a TLS connection. If ``None``, the default, creates one with the default
    configuration.

    *server_hostname*, a ``str`` containing the server's hostname.  The
    default is ``None``, which means that no hostname is known, and if an
    SSL context is created, hostname checking will be disabled.

    Returns a ``dns.message.Message``.

    """

    if sock:
        #
        # If a socket was provided, there's no special TLS handling needed.
        #
        return tcp(q, where, timeout, port, source, source_port,
                   one_rr_per_rrset, ignore_trailing, sock)

    wire = q.to_wire()
    (begin_time, expiration) = _compute_times(timeout)
    (af, destination, source) = _destination_and_source(where, port,
                                                        source, source_port)
    if ssl_context is None and not sock:
        ssl_context = ssl.create_default_context()
        if server_hostname is None:
            ssl_context.check_hostname = False

    with _make_socket(af, socket.SOCK_STREAM, source, ssl_context=ssl_context,
                      server_hostname=server_hostname) as s:
        _connect(s, destination, expiration)
        _tls_handshake(s, expiration)
        send_tcp(s, wire, expiration)
        (r, received_time) = receive_tcp(s, expiration, one_rr_per_rrset,
                                         q.keyring, q.mac, ignore_trailing)
        r.time = received_time - begin_time
        if not q.is_response(r):
            raise BadResponse
        return r


def xfr(where, zone, rdtype=dns.rdatatype.AXFR, rdclass=dns.rdataclass.IN,
        timeout=None, port=53, keyring=None, keyname=None, relativize=True,
        lifetime=None, source=None, source_port=0, serial=0,
        use_udp=False, keyalgorithm=dns.tsig.default_algorithm):
    """Return a generator for the responses to a zone transfer.

    *where*, a ``str`` containing an IPv4 or IPv6 address,  where
    to send the message.

    *zone*, a ``dns.name.Name`` or ``str``, the name of the zone to transfer.

    *rdtype*, an ``int`` or ``str``, the type of zone transfer.  The
    default is ``dns.rdatatype.AXFR``.  ``dns.rdatatype.IXFR`` can be
    used to do an incremental transfer instead.

    *rdclass*, an ``int`` or ``str``, the class of the zone transfer.
    The default is ``dns.rdataclass.IN``.

    *timeout*, a ``float``, the number of seconds to wait for each
    response message.  If None, the default, wait forever.

    *port*, an ``int``, the port send the message to.  The default is 53.

    *keyring*, a ``dict``, the keyring to use for TSIG.

    *keyname*, a ``dns.name.Name`` or ``str``, the name of the TSIG
    key to use.

    *relativize*, a ``bool``.  If ``True``, all names in the zone will be
    relativized to the zone origin.  It is essential that the
    relativize setting matches the one specified to
    ``dns.zone.from_xfr()`` if using this generator to make a zone.

    *lifetime*, a ``float``, the total number of seconds to spend
    doing the transfer.  If ``None``, the default, then there is no
    limit on the time the transfer may take.

    *source*, a ``str`` containing an IPv4 or IPv6 address, specifying
    the source address.  The default is the wildcard address.

    *source_port*, an ``int``, the port from which to send the message.
    The default is 0.

    *serial*, an ``int``, the SOA serial number to use as the base for
    an IXFR diff sequence (only meaningful if *rdtype* is
    ``dns.rdatatype.IXFR``).

    *use_udp*, a ``bool``.  If ``True``, use UDP (only meaningful for IXFR).

    *keyalgorithm*, a ``dns.name.Name`` or ``str``, the TSIG algorithm to use.

    Raises on errors, and so does the generator.

    Returns a generator of ``dns.message.Message`` objects.
    """

    if isinstance(zone, str):
        zone = dns.name.from_text(zone)
    rdtype = dns.rdatatype.RdataType.make(rdtype)
    q = dns.message.make_query(zone, rdtype, rdclass)
    if rdtype == dns.rdatatype.IXFR:
        rrset = dns.rrset.from_text(zone, 0, 'IN', 'SOA',
                                    '. . %u 0 0 0 0' % serial)
        q.authority.append(rrset)
    if keyring is not None:
        q.use_tsig(keyring, keyname, algorithm=keyalgorithm)
    wire = q.to_wire()
    (af, destination, source) = _destination_and_source(where, port,
                                                        source, source_port)
    if use_udp and rdtype != dns.rdatatype.IXFR:
        raise ValueError('cannot do a UDP AXFR')
    sock_type = socket.SOCK_DGRAM if use_udp else socket.SOCK_STREAM
    with _make_socket(af, sock_type, source) as s:
        (_, expiration) = _compute_times(lifetime)
        _connect(s, destination, expiration)
        l = len(wire)
        if use_udp:
            _wait_for_writable(s, expiration)
            s.send(wire)
        else:
            tcpmsg = struct.pack("!H", l) + wire
            _net_write(s, tcpmsg, expiration)
        done = False
        delete_mode = True
        expecting_SOA = False
        soa_rrset = None
        if relativize:
            origin = zone
            oname = dns.name.empty
        else:
            origin = None
            oname = zone
        tsig_ctx = None
        while not done:
            (_, mexpiration) = _compute_times(timeout)
            if mexpiration is None or \
               (expiration is not None and mexpiration > expiration):
                mexpiration = expiration
            if use_udp:
                _wait_for_readable(s, expiration)
                (wire, from_address) = s.recvfrom(65535)
            else:
                ldata = _net_read(s, 2, mexpiration)
                (l,) = struct.unpack("!H", ldata)
                wire = _net_read(s, l, mexpiration)
            is_ixfr = (rdtype == dns.rdatatype.IXFR)
            r = dns.message.from_wire(wire, keyring=q.keyring,
                                      request_mac=q.mac, xfr=True,
                                      origin=origin, tsig_ctx=tsig_ctx,
                                      multi=True, one_rr_per_rrset=is_ixfr)
            rcode = r.rcode()
            if rcode != dns.rcode.NOERROR:
                raise TransferError(rcode)
            tsig_ctx = r.tsig_ctx
            answer_index = 0
            if soa_rrset is None:
                if not r.answer or r.answer[0].name != oname:
                    raise dns.exception.FormError(
                        "No answer or RRset not for qname")
                rrset = r.answer[0]
                if rrset.rdtype != dns.rdatatype.SOA:
                    raise dns.exception.FormError("first RRset is not an SOA")
                answer_index = 1
                soa_rrset = rrset.copy()
                if rdtype == dns.rdatatype.IXFR:
                    if dns.serial.Serial(soa_rrset[0].serial) <= serial:
                        #
                        # We're already up-to-date.
                        #
                        done = True
                    else:
                        expecting_SOA = True
            #
            # Process SOAs in the answer section (other than the initial
            # SOA in the first message).
            #
            for rrset in r.answer[answer_index:]:
                if done:
                    raise dns.exception.FormError("answers after final SOA")
                if rrset.rdtype == dns.rdatatype.SOA and rrset.name == oname:
                    if expecting_SOA:
                        if rrset[0].serial != serial:
                            raise dns.exception.FormError(
                                "IXFR base serial mismatch")
                        expecting_SOA = False
                    elif rdtype == dns.rdatatype.IXFR:
                        delete_mode = not delete_mode
                    #
                    # If this SOA RRset is equal to the first we saw then we're
                    # finished. If this is an IXFR we also check that we're
                    # seeing the record in the expected part of the response.
                    #
                    if rrset == soa_rrset and \
                            (rdtype == dns.rdatatype.AXFR or
                             (rdtype == dns.rdatatype.IXFR and delete_mode)):
                        done = True
                elif expecting_SOA:
                    #
                    # We made an IXFR request and are expecting another
                    # SOA RR, but saw something else, so this must be an
                    # AXFR response.
                    #
                    rdtype = dns.rdatatype.AXFR
                    expecting_SOA = False
            if done and q.keyring and not r.had_tsig:
                raise dns.exception.FormError("missing TSIG")
            yield r
