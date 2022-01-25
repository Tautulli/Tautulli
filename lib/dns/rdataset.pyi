from typing import Optional, Dict, List, Union
from io import BytesIO
from . import exception, name, set, rdatatype, rdata, rdataset

class DifferingCovers(exception.DNSException):
    """An attempt was made to add a DNS SIG/RRSIG whose covered type
    is not the same as that of the other rdatas in the rdataset."""


class IncompatibleTypes(exception.DNSException):
    """An attempt was made to add DNS RR data of an incompatible type."""


class Rdataset(set.Set):
    def __init__(self, rdclass, rdtype, covers=rdatatype.NONE, ttl=0):
        self.rdclass : int = rdclass
        self.rdtype : int = rdtype
        self.covers : int = covers
        self.ttl : int = ttl

    def update_ttl(self, ttl : int) -> None:
        ...

    def add(self, rd : rdata.Rdata, ttl : Optional[int] =None):
        ...

    def union_update(self, other : Rdataset):
        ...

    def intersection_update(self, other : Rdataset):
        ...

    def update(self, other : Rdataset):
        ...

    def to_text(self, name : Optional[name.Name] =None, origin : Optional[name.Name] =None, relativize=True,
                override_rdclass : Optional[int] =None, **kw) -> bytes:
        ...

    def to_wire(self, name : Optional[name.Name], file : BytesIO, compress : Optional[Dict[name.Name, int]] = None, origin : Optional[name.Name] = None,
                override_rdclass : Optional[int] = None, want_shuffle=True) -> int:
        ...

    def match(self, rdclass : int, rdtype : int, covers : int) -> bool:
        ...


def from_text_list(rdclass : Union[int,str], rdtype : Union[int,str], ttl : int, text_rdatas : str, idna_codec : Optional[name.IDNACodec] = None) -> rdataset.Rdataset:
    ...

def from_text(rdclass : Union[int,str], rdtype : Union[int,str], ttl : int, *text_rdatas : str) -> rdataset.Rdataset:
    ...

def from_rdata_list(ttl : int, rdatas : List[rdata.Rdata]) -> rdataset.Rdataset:
    ...

def from_rdata(ttl : int, *rdatas : List[rdata.Rdata]) -> rdataset.Rdataset:
    ...
