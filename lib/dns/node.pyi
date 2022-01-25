from typing import List, Optional, Union
from . import rdataset, rdatatype, name
class Node:
    def __init__(self):
        self.rdatasets : List[rdataset.Rdataset]
    def to_text(self, name : Union[str,name.Name], **kw) -> str:
        ...
    def find_rdataset(self, rdclass : int, rdtype : int, covers=rdatatype.NONE,
                      create=False) -> rdataset.Rdataset:
        ...
    def get_rdataset(self, rdclass : int, rdtype : int, covers=rdatatype.NONE,
                     create=False) -> Optional[rdataset.Rdataset]:
        ...
    def delete_rdataset(self, rdclass : int, rdtype : int, covers=rdatatype.NONE):
        ...
    def replace_rdataset(self, replacement : rdataset.Rdataset) -> None:
        ...
