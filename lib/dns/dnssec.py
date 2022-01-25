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

"""Common DNSSEC-related functions and constants."""

import hashlib
import struct
import time
import base64

import dns.enum
import dns.exception
import dns.name
import dns.node
import dns.rdataset
import dns.rdata
import dns.rdatatype
import dns.rdataclass


class UnsupportedAlgorithm(dns.exception.DNSException):
    """The DNSSEC algorithm is not supported."""


class ValidationFailure(dns.exception.DNSException):
    """The DNSSEC signature is invalid."""


class Algorithm(dns.enum.IntEnum):
    RSAMD5 = 1
    DH = 2
    DSA = 3
    ECC = 4
    RSASHA1 = 5
    DSANSEC3SHA1 = 6
    RSASHA1NSEC3SHA1 = 7
    RSASHA256 = 8
    RSASHA512 = 10
    ECCGOST = 12
    ECDSAP256SHA256 = 13
    ECDSAP384SHA384 = 14
    ED25519 = 15
    ED448 = 16
    INDIRECT = 252
    PRIVATEDNS = 253
    PRIVATEOID = 254

    @classmethod
    def _maximum(cls):
        return 255


def algorithm_from_text(text):
    """Convert text into a DNSSEC algorithm value.

    *text*, a ``str``, the text to convert to into an algorithm value.

    Returns an ``int``.
    """

    return Algorithm.from_text(text)


def algorithm_to_text(value):
    """Convert a DNSSEC algorithm value to text

    *value*, an ``int`` a DNSSEC algorithm.

    Returns a ``str``, the name of a DNSSEC algorithm.
    """

    return Algorithm.to_text(value)


def key_id(key):
    """Return the key id (a 16-bit number) for the specified key.

    *key*, a ``dns.rdtypes.ANY.DNSKEY.DNSKEY``

    Returns an ``int`` between 0 and 65535
    """

    rdata = key.to_wire()
    if key.algorithm == Algorithm.RSAMD5:
        return (rdata[-3] << 8) + rdata[-2]
    else:
        total = 0
        for i in range(len(rdata) // 2):
            total += (rdata[2 * i] << 8) + \
                rdata[2 * i + 1]
        if len(rdata) % 2 != 0:
            total += rdata[len(rdata) - 1] << 8
        total += ((total >> 16) & 0xffff)
        return total & 0xffff

class DSDigest(dns.enum.IntEnum):
    """DNSSEC Delgation Signer Digest Algorithm"""

    SHA1 = 1
    SHA256 = 2
    SHA384 = 4

    @classmethod
    def _maximum(cls):
        return 255


def make_ds(name, key, algorithm, origin=None):
    """Create a DS record for a DNSSEC key.

    *name*, a ``dns.name.Name`` or ``str``, the owner name of the DS record.

    *key*, a ``dns.rdtypes.ANY.DNSKEY.DNSKEY``, the key the DS is about.

    *algorithm*, a ``str`` or ``int`` specifying the hash algorithm.
    The currently supported hashes are "SHA1", "SHA256", and "SHA384". Case
    does not matter for these strings.

    *origin*, a ``dns.name.Name`` or ``None``.  If `key` is a relative name,
    then it will be made absolute using the specified origin.

    Raises ``UnsupportedAlgorithm`` if the algorithm is unknown.

    Returns a ``dns.rdtypes.ANY.DS.DS``
    """

    try:
        if isinstance(algorithm, str):
            algorithm = DSDigest[algorithm.upper()]
    except Exception:
        raise UnsupportedAlgorithm('unsupported algorithm "%s"' % algorithm)

    if algorithm == DSDigest.SHA1:
        dshash = hashlib.sha1()
    elif algorithm == DSDigest.SHA256:
        dshash = hashlib.sha256()
    elif algorithm == DSDigest.SHA384:
        dshash = hashlib.sha384()
    else:
        raise UnsupportedAlgorithm('unsupported algorithm "%s"' % algorithm)

    if isinstance(name, str):
        name = dns.name.from_text(name, origin)
    dshash.update(name.canonicalize().to_wire())
    dshash.update(key.to_wire(origin=origin))
    digest = dshash.digest()

    dsrdata = struct.pack("!HBB", key_id(key), key.algorithm, algorithm) + \
        digest
    return dns.rdata.from_wire(dns.rdataclass.IN, dns.rdatatype.DS, dsrdata, 0,
                               len(dsrdata))


def _find_candidate_keys(keys, rrsig):
    value = keys.get(rrsig.signer)
    if isinstance(value, dns.node.Node):
        rdataset = value.get_rdataset(dns.rdataclass.IN, dns.rdatatype.DNSKEY)
    else:
        rdataset = value
    if rdataset is None:
        return None
    return [rd for rd in rdataset if
            rd.algorithm == rrsig.algorithm and key_id(rd) == rrsig.key_tag]


def _is_rsa(algorithm):
    return algorithm in (Algorithm.RSAMD5, Algorithm.RSASHA1,
                         Algorithm.RSASHA1NSEC3SHA1, Algorithm.RSASHA256,
                         Algorithm.RSASHA512)


def _is_dsa(algorithm):
    return algorithm in (Algorithm.DSA, Algorithm.DSANSEC3SHA1)


def _is_ecdsa(algorithm):
    return algorithm in (Algorithm.ECDSAP256SHA256, Algorithm.ECDSAP384SHA384)


def _is_eddsa(algorithm):
    return algorithm in (Algorithm.ED25519, Algorithm.ED448)


def _is_gost(algorithm):
    return algorithm == Algorithm.ECCGOST


def _is_md5(algorithm):
    return algorithm == Algorithm.RSAMD5


def _is_sha1(algorithm):
    return algorithm in (Algorithm.DSA, Algorithm.RSASHA1,
                         Algorithm.DSANSEC3SHA1, Algorithm.RSASHA1NSEC3SHA1)


def _is_sha256(algorithm):
    return algorithm in (Algorithm.RSASHA256, Algorithm.ECDSAP256SHA256)


def _is_sha384(algorithm):
    return algorithm == Algorithm.ECDSAP384SHA384


def _is_sha512(algorithm):
    return algorithm == Algorithm.RSASHA512


def _make_hash(algorithm):
    if _is_md5(algorithm):
        return hashes.MD5()
    if _is_sha1(algorithm):
        return hashes.SHA1()
    if _is_sha256(algorithm):
        return hashes.SHA256()
    if _is_sha384(algorithm):
        return hashes.SHA384()
    if _is_sha512(algorithm):
        return hashes.SHA512()
    if algorithm == Algorithm.ED25519:
        return hashes.SHA512()
    if algorithm == Algorithm.ED448:
        return hashes.SHAKE256(114)

    raise ValidationFailure('unknown hash for algorithm %u' % algorithm)


def _bytes_to_long(b):
    return int.from_bytes(b, 'big')


def _validate_signature(sig, data, key, chosen_hash):
    if _is_rsa(key.algorithm):
        keyptr = key.key
        (bytes_,) = struct.unpack('!B', keyptr[0:1])
        keyptr = keyptr[1:]
        if bytes_ == 0:
            (bytes_,) = struct.unpack('!H', keyptr[0:2])
            keyptr = keyptr[2:]
        rsa_e = keyptr[0:bytes_]
        rsa_n = keyptr[bytes_:]
        try:
            public_key = rsa.RSAPublicNumbers(
                _bytes_to_long(rsa_e),
                _bytes_to_long(rsa_n)).public_key(default_backend())
        except ValueError:
            raise ValidationFailure('invalid public key')
        public_key.verify(sig, data, padding.PKCS1v15(), chosen_hash)
    elif _is_dsa(key.algorithm):
        keyptr = key.key
        (t,) = struct.unpack('!B', keyptr[0:1])
        keyptr = keyptr[1:]
        octets = 64 + t * 8
        dsa_q = keyptr[0:20]
        keyptr = keyptr[20:]
        dsa_p = keyptr[0:octets]
        keyptr = keyptr[octets:]
        dsa_g = keyptr[0:octets]
        keyptr = keyptr[octets:]
        dsa_y = keyptr[0:octets]
        try:
            public_key = dsa.DSAPublicNumbers(
                _bytes_to_long(dsa_y),
                dsa.DSAParameterNumbers(
                    _bytes_to_long(dsa_p),
                    _bytes_to_long(dsa_q),
                    _bytes_to_long(dsa_g))).public_key(default_backend())
        except ValueError:
            raise ValidationFailure('invalid public key')
        public_key.verify(sig, data, chosen_hash)
    elif _is_ecdsa(key.algorithm):
        keyptr = key.key
        if key.algorithm == Algorithm.ECDSAP256SHA256:
            curve = ec.SECP256R1()
            octets = 32
        else:
            curve = ec.SECP384R1()
            octets = 48
        ecdsa_x = keyptr[0:octets]
        ecdsa_y = keyptr[octets:octets * 2]
        try:
            public_key = ec.EllipticCurvePublicNumbers(
                curve=curve,
                x=_bytes_to_long(ecdsa_x),
                y=_bytes_to_long(ecdsa_y)).public_key(default_backend())
        except ValueError:
            raise ValidationFailure('invalid public key')
        public_key.verify(sig, data, ec.ECDSA(chosen_hash))
    elif _is_eddsa(key.algorithm):
        keyptr = key.key
        if key.algorithm == Algorithm.ED25519:
            loader = ed25519.Ed25519PublicKey
        else:
            loader = ed448.Ed448PublicKey
        try:
            public_key = loader.from_public_bytes(keyptr)
        except ValueError:
            raise ValidationFailure('invalid public key')
        public_key.verify(sig, data)
    elif _is_gost(key.algorithm):
        raise UnsupportedAlgorithm(
            'algorithm "%s" not supported by dnspython' %
            algorithm_to_text(key.algorithm))
    else:
        raise ValidationFailure('unknown algorithm %u' % key.algorithm)


def _validate_rrsig(rrset, rrsig, keys, origin=None, now=None):
    """Validate an RRset against a single signature rdata, throwing an
    exception if validation is not successful.

    *rrset*, the RRset to validate.  This can be a
    ``dns.rrset.RRset`` or a (``dns.name.Name``, ``dns.rdataset.Rdataset``)
    tuple.

    *rrsig*, a ``dns.rdata.Rdata``, the signature to validate.

    *keys*, the key dictionary, used to find the DNSKEY associated
    with a given name.  The dictionary is keyed by a
    ``dns.name.Name``, and has ``dns.node.Node`` or
    ``dns.rdataset.Rdataset`` values.

    *origin*, a ``dns.name.Name`` or ``None``, the origin to use for relative
    names.

    *now*, an ``int`` or ``None``, the time, in seconds since the epoch, to
    use as the current time when validating.  If ``None``, the actual current
    time is used.

    Raises ``ValidationFailure`` if the signature is expired, not yet valid,
    the public key is invalid, the algorithm is unknown, the verification
    fails, etc.

    Raises ``UnsupportedAlgorithm`` if the algorithm is recognized by
    dnspython but not implemented.
    """

    if isinstance(origin, str):
        origin = dns.name.from_text(origin, dns.name.root)

    candidate_keys = _find_candidate_keys(keys, rrsig)
    if candidate_keys is None:
        raise ValidationFailure('unknown key')

    # For convenience, allow the rrset to be specified as a (name,
    # rdataset) tuple as well as a proper rrset
    if isinstance(rrset, tuple):
        rrname = rrset[0]
        rdataset = rrset[1]
    else:
        rrname = rrset.name
        rdataset = rrset

    if now is None:
        now = time.time()
    if rrsig.expiration < now:
        raise ValidationFailure('expired')
    if rrsig.inception > now:
        raise ValidationFailure('not yet valid')

    if _is_dsa(rrsig.algorithm):
        sig_r = rrsig.signature[1:21]
        sig_s = rrsig.signature[21:]
        sig = utils.encode_dss_signature(_bytes_to_long(sig_r),
                                         _bytes_to_long(sig_s))
    elif _is_ecdsa(rrsig.algorithm):
        if rrsig.algorithm == Algorithm.ECDSAP256SHA256:
            octets = 32
        else:
            octets = 48
        sig_r = rrsig.signature[0:octets]
        sig_s = rrsig.signature[octets:]
        sig = utils.encode_dss_signature(_bytes_to_long(sig_r),
                                         _bytes_to_long(sig_s))
    else:
        sig = rrsig.signature

    data = b''
    data += rrsig.to_wire(origin=origin)[:18]
    data += rrsig.signer.to_digestable(origin)

    # Derelativize the name before considering labels.
    rrname = rrname.derelativize(origin)

    if len(rrname) - 1 < rrsig.labels:
        raise ValidationFailure('owner name longer than RRSIG labels')
    elif rrsig.labels < len(rrname) - 1:
        suffix = rrname.split(rrsig.labels + 1)[1]
        rrname = dns.name.from_text('*', suffix)
    rrnamebuf = rrname.to_digestable()
    rrfixed = struct.pack('!HHI', rdataset.rdtype, rdataset.rdclass,
                          rrsig.original_ttl)
    rdatas = [rdata.to_digestable(origin) for rdata in rdataset]
    for rdata in sorted(rdatas):
        data += rrnamebuf
        data += rrfixed
        rrlen = struct.pack('!H', len(rdata))
        data += rrlen
        data += rdata

    chosen_hash = _make_hash(rrsig.algorithm)

    for candidate_key in candidate_keys:
        try:
            _validate_signature(sig, data, candidate_key, chosen_hash)
            return
        except (InvalidSignature, ValidationFailure):
            # this happens on an individual validation failure
            continue
    # nothing verified -- raise failure:
    raise ValidationFailure('verify failure')


def _validate(rrset, rrsigset, keys, origin=None, now=None):
    """Validate an RRset against a signature RRset, throwing an exception
    if none of the signatures validate.

    *rrset*, the RRset to validate.  This can be a
    ``dns.rrset.RRset`` or a (``dns.name.Name``, ``dns.rdataset.Rdataset``)
    tuple.

    *rrsigset*, the signature RRset.  This can be a
    ``dns.rrset.RRset`` or a (``dns.name.Name``, ``dns.rdataset.Rdataset``)
    tuple.

    *keys*, the key dictionary, used to find the DNSKEY associated
    with a given name.  The dictionary is keyed by a
    ``dns.name.Name``, and has ``dns.node.Node`` or
    ``dns.rdataset.Rdataset`` values.

    *origin*, a ``dns.name.Name``, the origin to use for relative names;
    defaults to None.

    *now*, an ``int`` or ``None``, the time, in seconds since the epoch, to
    use as the current time when validating.  If ``None``, the actual current
    time is used.

    Raises ``ValidationFailure`` if the signature is expired, not yet valid,
    the public key is invalid, the algorithm is unknown, the verification
    fails, etc.
    """

    if isinstance(origin, str):
        origin = dns.name.from_text(origin, dns.name.root)

    if isinstance(rrset, tuple):
        rrname = rrset[0]
    else:
        rrname = rrset.name

    if isinstance(rrsigset, tuple):
        rrsigname = rrsigset[0]
        rrsigrdataset = rrsigset[1]
    else:
        rrsigname = rrsigset.name
        rrsigrdataset = rrsigset

    rrname = rrname.choose_relativity(origin)
    rrsigname = rrsigname.choose_relativity(origin)
    if rrname != rrsigname:
        raise ValidationFailure("owner names do not match")

    for rrsig in rrsigrdataset:
        try:
            _validate_rrsig(rrset, rrsig, keys, origin, now)
            return
        except (ValidationFailure, UnsupportedAlgorithm):
            pass
    raise ValidationFailure("no RRSIGs validated")


class NSEC3Hash(dns.enum.IntEnum):
    """NSEC3 hash algorithm"""

    SHA1 = 1

    @classmethod
    def _maximum(cls):
        return 255

def nsec3_hash(domain, salt, iterations, algorithm):
    """
    Calculate the NSEC3 hash, according to
    https://tools.ietf.org/html/rfc5155#section-5

    *domain*, a ``dns.name.Name`` or ``str``, the name to hash.

    *salt*, a ``str``, ``bytes``, or ``None``, the hash salt.  If a
    string, it is decoded as a hex string.

    *iterations*, an ``int``, the number of iterations.

    *algorithm*, a ``str`` or ``int``, the hash algorithm.
    The only defined algorithm is SHA1.

    Returns a ``str``, the encoded NSEC3 hash.
    """

    b32_conversion = str.maketrans(
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567", "0123456789ABCDEFGHIJKLMNOPQRSTUV"
    )

    try:
        if isinstance(algorithm, str):
            algorithm = NSEC3Hash[algorithm.upper()]
    except Exception:
        raise ValueError("Wrong hash algorithm (only SHA1 is supported)")

    if algorithm != NSEC3Hash.SHA1:
        raise ValueError("Wrong hash algorithm (only SHA1 is supported)")

    salt_encoded = salt
    if salt is None:
        salt_encoded = b''
    elif isinstance(salt, str):
        if len(salt) % 2 == 0:
            salt_encoded = bytes.fromhex(salt)
        else:
            raise ValueError("Invalid salt length")

    if not isinstance(domain, dns.name.Name):
        domain = dns.name.from_text(domain)
    domain_encoded = domain.canonicalize().to_wire()

    digest = hashlib.sha1(domain_encoded + salt_encoded).digest()
    for _ in range(iterations):
        digest = hashlib.sha1(digest + salt_encoded).digest()

    output = base64.b32encode(digest).decode("utf-8")
    output = output.translate(b32_conversion)

    return output


def _need_pyca(*args, **kwargs):
    raise ImportError("DNSSEC validation requires " +
                      "python cryptography")  # pragma: no cover


try:
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import padding
    from cryptography.hazmat.primitives.asymmetric import utils
    from cryptography.hazmat.primitives.asymmetric import dsa
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.primitives.asymmetric import ed25519
    from cryptography.hazmat.primitives.asymmetric import ed448
    from cryptography.hazmat.primitives.asymmetric import rsa
except ImportError:  # pragma: no cover
    validate = _need_pyca
    validate_rrsig = _need_pyca
    _have_pyca = False
else:
    validate = _validate                # type: ignore
    validate_rrsig = _validate_rrsig    # type: ignore
    _have_pyca = True

### BEGIN generated Algorithm constants

RSAMD5 = Algorithm.RSAMD5
DH = Algorithm.DH
DSA = Algorithm.DSA
ECC = Algorithm.ECC
RSASHA1 = Algorithm.RSASHA1
DSANSEC3SHA1 = Algorithm.DSANSEC3SHA1
RSASHA1NSEC3SHA1 = Algorithm.RSASHA1NSEC3SHA1
RSASHA256 = Algorithm.RSASHA256
RSASHA512 = Algorithm.RSASHA512
ECCGOST = Algorithm.ECCGOST
ECDSAP256SHA256 = Algorithm.ECDSAP256SHA256
ECDSAP384SHA384 = Algorithm.ECDSAP384SHA384
ED25519 = Algorithm.ED25519
ED448 = Algorithm.ED448
INDIRECT = Algorithm.INDIRECT
PRIVATEDNS = Algorithm.PRIVATEDNS
PRIVATEOID = Algorithm.PRIVATEOID

### END generated Algorithm constants
