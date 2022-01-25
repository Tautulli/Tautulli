from typing import Union, Optional, List, Any, Dict
from . import exception, rdataclass, name, rdatatype, asyncbackend

async def resolve(qname : str, rdtype : Union[int,str] = 0,
                  rdclass : Union[int,str] = 0,
                  tcp=False, source=None, raise_on_no_answer=True,
                  source_port=0, lifetime : Optional[float]=None,
                  search : Optional[bool]=None,
                  backend : Optional[asyncbackend.Backend]=None):
    ...
async def resolve_address(self, ipaddr: str,
                          *args: Any, **kwargs: Optional[Dict]):
    ...

class Resolver:
    def __init__(self, filename : Optional[str] = '/etc/resolv.conf',
                 configure : Optional[bool] = True):
        self.nameservers : List[str]
    async def resolve(self, qname : str, rdtype : Union[int,str] = rdatatype.A,
                      rdclass : Union[int,str] = rdataclass.IN,
                      tcp : bool = False, source : Optional[str] = None,
                      raise_on_no_answer=True, source_port : int = 0,
                      lifetime : Optional[float]=None,
                      search : Optional[bool]=None,
                      backend : Optional[asyncbackend.Backend]=None):
        ...
