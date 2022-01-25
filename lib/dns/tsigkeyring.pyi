from typing import Dict
from . import name

def from_text(textring : Dict[str,str]) -> Dict[name.Name,bytes]:
    ...
def to_text(keyring : Dict[name.Name,bytes]) -> Dict[str, str]:
    ...
