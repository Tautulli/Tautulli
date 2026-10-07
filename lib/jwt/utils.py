import base64
import binascii
import re
from typing import Optional, Union

try:
    from cryptography.hazmat.primitives.asymmetric.ec import EllipticCurve
    from cryptography.hazmat.primitives.asymmetric.utils import (
        decode_dss_signature,
        encode_dss_signature,
    )
except ModuleNotFoundError:
    pass


def force_bytes(value: Union[bytes, str]) -> bytes:
    if isinstance(value, str):
        return value.encode("utf-8")
    elif isinstance(value, bytes):
        return value
    else:
        raise TypeError("Expected a string or bytes value")


def base64url_decode(input: Union[bytes, str]) -> bytes:
    input_bytes = force_bytes(input)

    rem = len(input_bytes) % 4

    if rem > 0:
        input_bytes += b"=" * (4 - rem)

    return base64.urlsafe_b64decode(input_bytes)


def base64url_encode(input: bytes) -> bytes:
    return base64.urlsafe_b64encode(input).replace(b"=", b"")


def to_base64url_uint(val: int, *, bit_length: Optional[int] = None) -> bytes:
    if val < 0:
        raise ValueError("Must be a positive integer")

    int_bytes = bytes_from_int(val, bit_length=bit_length)

    if len(int_bytes) == 0:
        int_bytes = b"\x00"

    return base64url_encode(int_bytes)


def from_base64url_uint(val: Union[bytes, str]) -> int:
    data = base64url_decode(force_bytes(val))
    return int.from_bytes(data, byteorder="big")


def number_to_bytes(num: int, num_bytes: int) -> bytes:
    padded_hex = "%0*x" % (2 * num_bytes, num)
    return binascii.a2b_hex(padded_hex.encode("ascii"))


def bytes_to_number(string: bytes) -> int:
    return int(binascii.b2a_hex(string), 16)


def bytes_from_int(val: int, *, bit_length: Optional[int] = None) -> bytes:
    if bit_length is None:
        bit_length = val.bit_length()
    byte_length = (bit_length + 7) // 8

    return val.to_bytes(byte_length, "big", signed=False)


def der_to_raw_signature(der_sig: bytes, curve: "EllipticCurve") -> bytes:
    num_bits = curve.key_size
    num_bytes = (num_bits + 7) // 8

    r, s = decode_dss_signature(der_sig)

    return number_to_bytes(r, num_bytes) + number_to_bytes(s, num_bytes)


def raw_to_der_signature(raw_sig: bytes, curve: "EllipticCurve") -> bytes:
    num_bits = curve.key_size
    num_bytes = (num_bits + 7) // 8

    if len(raw_sig) != 2 * num_bytes:
        raise ValueError("Invalid signature")

    r = bytes_to_number(raw_sig[:num_bytes])
    s = bytes_to_number(raw_sig[num_bytes:])

    return bytes(encode_dss_signature(r, s))


# Based on https://github.com/hynek/pem/blob/7ad94db26b0bc21d10953f5dbad3acfdfacf57aa/src/pem/_core.py#L224-L252
_PEMS = {
    b"CERTIFICATE",
    b"TRUSTED CERTIFICATE",
    b"PRIVATE KEY",
    b"PUBLIC KEY",
    b"ENCRYPTED PRIVATE KEY",
    b"OPENSSH PRIVATE KEY",
    b"DSA PRIVATE KEY",
    b"RSA PRIVATE KEY",
    b"RSA PUBLIC KEY",
    b"EC PRIVATE KEY",
    b"DH PARAMETERS",
    b"NEW CERTIFICATE REQUEST",
    b"CERTIFICATE REQUEST",
    b"SSH2 PUBLIC KEY",
    b"SSH2 ENCRYPTED PRIVATE KEY",
    b"X509 CRL",
}

# Accept PEM formatting variants that the cryptography loader accepts, while
# retaining the explicit asymmetric-key marker check.
_PEM_MARKER_RE = re.compile(
    b"(?=(----[- ](BEGIN|END) (" + b"|".join(_PEMS) + b")[- ]----))"
)


def is_pem_format(key: bytes) -> bool:
    begin_markers: dict[bytes, int] = {}
    for marker in _PEM_MARKER_RE.finditer(key):
        marker_type, label = marker.group(2), marker.group(3)
        if marker_type == b"BEGIN":
            begin_markers[label] = marker.start(1) + len(marker.group(1))
        elif label in begin_markers and begin_markers[label] < marker.start(1):
            return True
    return False


# Based on https://github.com/pyca/cryptography/blob/bcb70852d577b3f490f015378c75cba74986297b/src/cryptography/hazmat/primitives/serialization/ssh.py#L40-L46
_SSH_KEY_FORMATS = (
    b"ssh-ed25519",
    b"ssh-rsa",
    b"ssh-dss",
    b"ecdsa-sha2-nistp256",
    b"ecdsa-sha2-nistp384",
    b"ecdsa-sha2-nistp521",
)


def is_ssh_key(key: bytes) -> bool:
    return key.startswith(_SSH_KEY_FORMATS)
