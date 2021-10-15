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

"""Asynchronous DNS stub resolver."""

import time

import dns.asyncbackend
import dns.asyncquery
import dns.exception
import dns.query
import dns.resolver

# import some resolver symbols for brevity
from dns.resolver import NXDOMAIN, NoAnswer, NotAbsolute, NoRootSOA


# for indentation purposes below
_udp = dns.asyncquery.udp
_tcp = dns.asyncquery.tcp


class Resolver(dns.resolver.Resolver):

    async def resolve(self, qname, rdtype=dns.rdatatype.A,
                      rdclass=dns.rdataclass.IN,
                      tcp=False, source=None, raise_on_no_answer=True,
                      source_port=0, lifetime=None, search=None,
                      backend=None):
        """Query nameservers asynchronously to find the answer to the question.

        The *qname*, *rdtype*, and *rdclass* parameters may be objects
        of the appropriate type, or strings that can be converted into objects
        of the appropriate type.

        *qname*, a ``dns.name.Name`` or ``str``, the query name.

        *rdtype*, an ``int`` or ``str``,  the query type.

        *rdclass*, an ``int`` or ``str``,  the query class.

        *tcp*, a ``bool``.  If ``True``, use TCP to make the query.

        *source*, a ``str`` or ``None``.  If not ``None``, bind to this IP
        address when making queries.

        *raise_on_no_answer*, a ``bool``.  If ``True``, raise
        ``dns.resolver.NoAnswer`` if there's no answer to the question.

        *source_port*, an ``int``, the port from which to send the message.

        *lifetime*, a ``float``, how many seconds a query should run
         before timing out.

        *search*, a ``bool`` or ``None``, determines whether the
        search list configured in the system's resolver configuration
        are used for relative names, and whether the resolver's domain
        may be added to relative names.  The default is ``None``,
        which causes the value of the resolver's
        ``use_search_by_default`` attribute to be used.

        *backend*, a ``dns.asyncbackend.Backend``, or ``None``.  If ``None``,
        the default, then dnspython will use the default backend.

        Raises ``dns.resolver.NXDOMAIN`` if the query name does not exist.

        Raises ``dns.resolver.YXDOMAIN`` if the query name is too long after
        DNAME substitution.

        Raises ``dns.resolver.NoAnswer`` if *raise_on_no_answer* is
        ``True`` and the query name exists but has no RRset of the
        desired type and class.

        Raises ``dns.resolver.NoNameservers`` if no non-broken
        nameservers are available to answer the question.

        Returns a ``dns.resolver.Answer`` instance.

        """

        resolution = dns.resolver._Resolution(self, qname, rdtype, rdclass, tcp,
                                              raise_on_no_answer, search)
        if not backend:
            backend = dns.asyncbackend.get_default_backend()
        start = time.time()
        while True:
            (request, answer) = resolution.next_request()
            # Note we need to say "if answer is not None" and not just
            # "if answer" because answer implements __len__, and python
            # will call that.  We want to return if we have an answer
            # object, including in cases where its length is 0.
            if answer is not None:
                # cache hit!
                return answer
            done = False
            while not done:
                (nameserver, port, tcp, backoff) = resolution.next_nameserver()
                if backoff:
                    await backend.sleep(backoff)
                timeout = self._compute_timeout(start, lifetime)
                try:
                    if dns.inet.is_address(nameserver):
                        if tcp:
                            response = await _tcp(request, nameserver,
                                                  timeout, port,
                                                  source, source_port,
                                                  backend=backend)
                        else:
                            response = await _udp(request, nameserver,
                                                  timeout, port,
                                                  source, source_port,
                                                  raise_on_truncation=True,
                                                  backend=backend)
                    else:
                        # We don't do DoH yet.
                        raise NotImplementedError
                except Exception as ex:
                    (_, done) = resolution.query_result(None, ex)
                    continue
                (answer, done) = resolution.query_result(response, None)
                # Note we need to say "if answer is not None" and not just
                # "if answer" because answer implements __len__, and python
                # will call that.  We want to return if we have an answer
                # object, including in cases where its length is 0.
                if answer is not None:
                    return answer

    async def query(self, *args, **kwargs):
        # We have to define something here as we don't want to inherit the
        # parent's query().
        raise NotImplementedError

    async def resolve_address(self, ipaddr, *args, **kwargs):
        """Use an asynchronous resolver to run a reverse query for PTR
        records.

        This utilizes the resolve() method to perform a PTR lookup on the
        specified IP address.

        *ipaddr*, a ``str``, the IPv4 or IPv6 address you want to get
        the PTR record for.

        All other arguments that can be passed to the resolve() function
        except for rdtype and rdclass are also supported by this
        function.

        """

        return await self.resolve(dns.reversename.from_address(ipaddr),
                                  rdtype=dns.rdatatype.PTR,
                                  rdclass=dns.rdataclass.IN,
                                  *args, **kwargs)

default_resolver = None


def get_default_resolver():
    """Get the default asynchronous resolver, initializing it if necessary."""
    if default_resolver is None:
        reset_default_resolver()
    return default_resolver


def reset_default_resolver():
    """Re-initialize default asynchronous resolver.

    Note that the resolver configuration (i.e. /etc/resolv.conf on UNIX
    systems) will be re-read immediately.
    """

    global default_resolver
    default_resolver = Resolver()


async def resolve(qname, rdtype=dns.rdatatype.A, rdclass=dns.rdataclass.IN,
                  tcp=False, source=None, raise_on_no_answer=True,
                  source_port=0, search=None, backend=None):
    """Query nameservers asynchronously to find the answer to the question.

    This is a convenience function that uses the default resolver
    object to make the query.

    See ``dns.asyncresolver.Resolver.resolve`` for more information on the
    parameters.
    """

    return await get_default_resolver().resolve(qname, rdtype, rdclass, tcp,
                                                source, raise_on_no_answer,
                                                source_port, search, backend)


async def resolve_address(ipaddr, *args, **kwargs):
    """Use a resolver to run a reverse query for PTR records.

    See ``dns.asyncresolver.Resolver.resolve_address`` for more
    information on the parameters.
    """

    return await get_default_resolver().resolve_address(ipaddr, *args, **kwargs)


async def zone_for_name(name, rdclass=dns.rdataclass.IN, tcp=False,
                        resolver=None, backend=None):
    """Find the name of the zone which contains the specified name.

    *name*, an absolute ``dns.name.Name`` or ``str``, the query name.

    *rdclass*, an ``int``, the query class.

    *tcp*, a ``bool``.  If ``True``, use TCP to make the query.

    *resolver*, a ``dns.asyncresolver.Resolver`` or ``None``, the
    resolver to use.  If ``None``, the default resolver is used.

    *backend*, a ``dns.asyncbackend.Backend``, or ``None``.  If ``None``,
    the default, then dnspython will use the default backend.

    Raises ``dns.resolver.NoRootSOA`` if there is no SOA RR at the DNS
    root.  (This is only likely to happen if you're using non-default
    root servers in your network and they are misconfigured.)

    Returns a ``dns.name.Name``.
    """

    if isinstance(name, str):
        name = dns.name.from_text(name, dns.name.root)
    if resolver is None:
        resolver = get_default_resolver()
    if not name.is_absolute():
        raise NotAbsolute(name)
    while True:
        try:
            answer = await resolver.resolve(name, dns.rdatatype.SOA, rdclass,
                                            tcp, backend=backend)
            if answer.rrset.name == name:
                return name
            # otherwise we were CNAMEd or DNAMEd and need to look higher
        except (NXDOMAIN, NoAnswer):
            pass
        try:
            name = name.parent()
        except dns.name.NoParent:  # pragma: no cover
            raise NoRootSOA
