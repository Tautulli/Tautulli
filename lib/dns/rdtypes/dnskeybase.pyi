from typing import Set, Any

SEP : int
REVOKE : int
ZONE : int

def flags_to_text_set(flags : int) -> Set[str]:
    ...

def flags_from_text_set(texts_set) -> int:
    ...

from .. import rdata

class DNSKEYBase(rdata.Rdata):
    def __init__(self, rdclass, rdtype, flags, protocol, algorithm, key):
        self.flags : int
        self.protocol : int
        self.key : str
        self.algorithm : int

    def to_text(self, origin : Any = None, relativize=True, **kw : Any):
        ...

    @classmethod
    def from_text(cls, rdclass, rdtype, tok, origin=None, relativize=True,
                  relativize_to=None):
        ...

    def _to_wire(self, file, compress=None, origin=None, canonicalize=False):
        ...

    @classmethod
    def from_parser(cls, rdclass, rdtype, parser, origin=None):
        ...

    def flags_to_text_set(self) -> Set[str]:
        ...
