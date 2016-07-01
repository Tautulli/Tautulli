import sys

import ipaddress

# pylint: skip-file

if sys.version_info[0] == 2:
    def compat_ip_address(address):
        if isinstance(address, bytes):
            address = address.decode()
        return ipaddress.ip_address(address)

    int_from_byte = ord

    FileNotFoundError = IOError

    def int_from_bytes(b):
        if b:
            return int(b.encode("hex"), 16)
        return 0

    byte_from_int = chr
else:
    def compat_ip_address(address):
        return ipaddress.ip_address(address)

    int_from_byte = lambda x: x

    FileNotFoundError = FileNotFoundError

    int_from_bytes = lambda x: int.from_bytes(x, 'big')

    byte_from_int = lambda x: bytes([x])
