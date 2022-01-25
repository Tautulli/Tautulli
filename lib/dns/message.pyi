from typing import Optional, Dict, List, Tuple, Union
from . import name, rrset, tsig, rdatatype, entropy, edns, rdataclass, rcode
import hmac

class Message:
    def to_wire(self, origin : Optional[name.Name]=None, max_size=0, **kw) -> bytes:
        ...
    def find_rrset(self, section : List[rrset.RRset], name : name.Name, rdclass : int, rdtype : int,
                   covers=rdatatype.NONE, deleting : Optional[int]=None, create=False,
                   force_unique=False) -> rrset.RRset:
        ...
    def __init__(self, id : Optional[int] =None) -> None:
        self.id : int
        self.flags = 0
        self.sections : List[List[rrset.RRset]] = [[], [], [], []]
        self.opt : rrset.RRset = None
        self.request_payload = 0
        self.keyring = None
        self.tsig : rrset.RRset = None
        self.request_mac = b''
        self.xfr = False
        self.origin = None
        self.tsig_ctx = None
        self.index : Dict[Tuple[rrset.RRset, name.Name, int, int, Union[int,str], int], rrset.RRset] = {}

    def is_response(self, other : Message) -> bool:
        ...

    def set_rcode(self, rcode : rcode.Rcode):
        ...

def from_text(a : str, idna_codec : Optional[name.IDNACodec] = None) -> Message:
    ...

def from_wire(wire, keyring : Optional[Dict[name.Name,bytes]] = None, request_mac = b'', xfr=False, origin=None,
              tsig_ctx : Optional[Union[dns.tsig.HMACTSig, dns.tsig.GSSTSig]] = None, multi=False,
              question_only=False, one_rr_per_rrset=False,
              ignore_trailing=False) -> Message:
    ...
def make_response(query : Message, recursion_available=False, our_payload=8192,
                  fudge=300) -> Message:
    ...

def make_query(qname : Union[name.Name,str], rdtype : Union[str,int], rdclass : Union[int,str] =rdataclass.IN, use_edns : Optional[bool] = None,
               want_dnssec=False, ednsflags : Optional[int] = None, payload : Optional[int] = None,
               request_payload : Optional[int] = None, options : Optional[List[edns.Option]] = None) -> Message:
    ...
