def match_hostname(cert, hostname):
    """Verify that *cert* (in decoded format as returned by
    SSLSocket.getpeercert()) matches the *hostname*.  RFC 2818 and RFC 6125
    rules are followed, but IP addresses are not accepted for *hostname*.
    CertificateError is raised on failure. On success, the function
    returns nothing.
    """
    if not cert:
        raise ValueError(
            "empty or no certificate, match_hostname needs a "
            "SSL socket or SSL context with either "
            "CERT_OPTIONAL or CERT_REQUIRED"
        )
    try:
        # Divergence from upstream: ipaddress can't handle byte str
        host_ip = ipaddress.ip_address(hostname)
    except ValueError:
        # Not an IP address (common case)
        host_ip = None
    except AttributeError:
        # Divergence from upstream: Make ipaddress library optional
        if ipaddress is None:
            host_ip = None
        else:
            raise
    dnsnames = []
    san = cert.get("subjectAltName", ())
    for key, value in san:
        if key == "DNS":
            if host_ip is None and _dnsname_match(value, hostname):
                return
            dnsnames.append(value)
        elif key == "IP Address":
            if host_ip is not None and _ipaddress_match(value, host_ip):
                return
            dnsnames.append(value)
    if not dnsnames:
        # The subject is only checked when there is no dNSName entry
        # in subjectAltName
        for sub in cert.get("subject", ()):
            for key, value in sub:
                # XXX according to RFC 2818, the most specific Common Name
                # must be used.
                if key == "commonName":
                    if _dnsname_match(value, hostname):
                        return
                    dnsnames.append(value)
    if len(dnsnames) > 1:
        raise CertificateError(
            "hostname %r "
            "doesn't match either of %s" % (hostname, ", ".join(map(repr, dnsnames)))
        )
    elif len(dnsnames) == 1:
        raise CertificateError(f"hostname {hostname!r} doesn't match {dnsnames[0]!r}")
    else:
        raise CertificateError(
            "no appropriate commonName or subjectAltName fields were found"
        )
