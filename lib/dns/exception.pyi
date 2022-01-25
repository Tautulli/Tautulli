from typing import Set, Optional, Dict

class DNSException(Exception):
    supp_kwargs : Set[str]
    kwargs : Optional[Dict]
    fmt : Optional[str]

class SyntaxError(DNSException): ...
class FormError(DNSException): ...
class Timeout(DNSException): ...
