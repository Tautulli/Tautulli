from typing import Optional, Union, Dict, Generator, Any
from . import tsig, rdatatype, rdataclass, name, message, asyncbackend

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

async def udp(q : message.Message, where : str,
              timeout : Optional[float] = None, port=53,
              source : Optional[str] = None, source_port : Optional[int] = 0,
              ignore_unexpected : Optional[bool] = False,
              one_rr_per_rrset : Optional[bool] = False,
              ignore_trailing : Optional[bool] = False,
              sock : Optional[asyncbackend.DatagramSocket] = None,
              backend : Optional[asyncbackend.Backend] = None) -> message.Message:
    pass

async def tcp(q : message.Message, where : str, timeout : float = None, port=53,
        af : Optional[int] = None, source : Optional[str] = None,
        source_port : Optional[int] = 0,
        one_rr_per_rrset : Optional[bool] = False,
        ignore_trailing : Optional[bool] = False,
        sock : Optional[asyncbackend.StreamSocket] = None,
        backend : Optional[asyncbackend.Backend] = None) -> message.Message:
    pass

async def tls(q : message.Message, where : str,
              timeout : Optional[float] = None, port=53,
              source : Optional[str] = None, source_port : Optional[int] = 0,
              one_rr_per_rrset : Optional[bool] = False,
              ignore_trailing : Optional[bool] = False,
              sock : Optional[asyncbackend.StreamSocket] = None,
              backend : Optional[asyncbackend.Backend] = None,
              ssl_context: Optional[ssl.SSLContext] = None,
              server_hostname: Optional[str] = None) -> message.Message:
    pass
