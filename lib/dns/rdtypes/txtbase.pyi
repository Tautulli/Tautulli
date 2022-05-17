import typing
from .. import rdata

class TXTBase(rdata.Rdata):
    strings: typing.Tuple[bytes, ...]

    def __init__(self, rdclass: int, rdtype: int, strings: typing.Iterable[bytes]) -> None:
        ...
    def to_text(self, origin: typing.Any, relativize: bool, **kw: typing.Any) -> str:
        ...
class TXT(TXTBase):
    ...
