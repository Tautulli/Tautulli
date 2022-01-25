from typing import Union, Dict, Tuple, Optional
from . import rdataset, rrset, exception, name, rdtypes, rdata, node
import dns.rdtypes.ANY.DS as DS
import dns.rdtypes.ANY.DNSKEY as DNSKEY

_have_pyca : bool

def validate_rrsig(rrset : Union[Tuple[name.Name, rdataset.Rdataset], rrset.RRset], rrsig : rdata.Rdata, keys : Dict[name.Name, Union[node.Node, rdataset.Rdataset]], origin : Optional[name.Name] = None, now : Optional[int] = None) -> None:
    ...

def validate(rrset: Union[Tuple[name.Name, rdataset.Rdataset], rrset.RRset], rrsigset : Union[Tuple[name.Name, rdataset.Rdataset], rrset.RRset], keys : Dict[name.Name, Union[node.Node, rdataset.Rdataset]], origin=None, now=None) -> None:
    ...

class ValidationFailure(exception.DNSException):
    ...

def make_ds(name : name.Name, key : DNSKEY.DNSKEY, algorithm : str, origin : Optional[name.Name] = None) -> DS.DS:
    ...

def nsec3_hash(domain: str, salt: Optional[Union[str, bytes]], iterations: int, algo: int) -> str:
    ...
