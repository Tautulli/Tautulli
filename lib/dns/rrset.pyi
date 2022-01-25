from typing import List, Optional
from . import rdataset, rdatatype

class RRset(rdataset.Rdataset):
    def __init__(self, name, rdclass : int , rdtype : int, covers=rdatatype.NONE,
                 deleting : Optional[int] =None) -> None:
        self.name = name
        self.deleting = deleting
def from_text(name : str, ttl : int, rdclass : str, rdtype : str, *text_rdatas : str):
    ...
