from typing import Optional, Union, Dict, Generator, Any
from . import tsig, rdatatype, rdataclass, name, message
from requests.sessions import Session

import socket

# If the ssl import works, then
#
#    error: Name 'ssl' already defined (by an import)
#
# is expected and can be ignored.
try:
    import ssl
except ImportError:
    class ssl:    # type: ignore
        SSLContext : Dict = {}

have_doh: bool

def https(q : message.Message, where: str, timeout : Optional[float] = None,
          port : Optional[int] = 443, source : Optional[str] = None,
          source_port : Optional[int] = 0,
          session: Optional[Session] = None,
          path : Optional[str] = '/dns-query', post : Optional[bool] = True,
          bootstrap_address : Optional[str] = None,
          verify : Optional[bool] = True) -> message.Message:
    pass

def tcp(q : message.Message, where : str, timeout : float = None, port=53,
        af : Optional[int] = None, source : Optional[str] = None,
        source_port : Optional[int] = 0,
        one_rr_per_rrset : Optional[bool] = False,
        ignore_trailing : Optional[bool] = False,
        sock : Optional[socket.socket] = None) -> message.Message:
    pass

def xfr(where : None, zone : Union[name.Name,str], rdtype=rdatatype.AXFR,
        rdclass=rdataclass.IN,
        timeout : Optional[float] = None, port=53,
        keyring : Optional[Dict[name.Name, bytes]] = None,
        keyname : Union[str,name.Name]= None, relativize=True,
        lifetime : Optional[float] = None,
        source : Optional[str] = None, source_port=0, serial=0,
        use_udp : Optional[bool] = False,
        keyalgorithm=tsig.default_algorithm) \
        -> Generator[Any,Any,message.Message]:
    pass

def udp(q : message.Message, where : str, timeout : Optional[float] = None,
        port=53, source : Optional[str] = None, source_port : Optional[int] = 0,
        ignore_unexpected : Optional[bool] = False,
        one_rr_per_rrset : Optional[bool] = False,
        ignore_trailing : Optional[bool] = False,
        sock : Optional[socket.socket] = None) -> message.Message:
    pass

def tls(q : message.Message, where : str, timeout : Optional[float] = None,
        port=53, source : Optional[str] = None, source_port : Optional[int] = 0,
        one_rr_per_rrset : Optional[bool] = False,
        ignore_trailing : Optional[bool] = False,
        sock : Optional[socket.socket] = None,
        ssl_context: Optional[ssl.SSLContext] = None,
        server_hostname: Optional[str] = None) -> message.Message:
    pass
