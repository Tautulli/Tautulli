from typing import Optional,Dict,Union,Any

from . import message, tsig, rdataclass, name

class Update(message.Message):
    def __init__(self, zone : Union[name.Name, str], rdclass : Union[int,str] = rdataclass.IN, keyring : Optional[Dict[name.Name,bytes]] = None,
                 keyname : Optional[name.Name] = None, keyalgorithm : Optional[name.Name] = tsig.default_algorithm) -> None:
        self.id : int
    def add(self, name : Union[str,name.Name], *args : Any):
        ...
    def delete(self, name, *args : Any):
        ...
    def replace(self, name : Union[str,name.Name], *args : Any):
        ...
    def present(self, name : Union[str,name.Name], *args : Any):
        ...
    def absent(self, name : Union[str,name.Name], rdtype=None):
        """Require that an owner name (and optionally an rdata type) does
        not exist as a prerequisite to the execution of the update."""
    def to_wire(self, origin : Optional[name.Name] = None, max_size=65535, **kw) -> bytes:
        ...
