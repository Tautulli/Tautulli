from typing import Optional, Iterable
from . import name, resolver
def from_e164(text : str, origin=name.Name(".")) -> name.Name:
    ...

def to_e164(name : name.Name, origin : Optional[name.Name] = None, want_plus_prefix=True) -> str:
    ...

def query(number : str, domains : Iterable[str], resolver : Optional[resolver.Resolver] = None) -> resolver.Answer:
    ...
