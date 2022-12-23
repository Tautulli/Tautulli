# Standard Library
from threading import RLock
from typing import Any
from typing import Callable
from typing import Generic
from typing import Optional
from typing import Type
from typing import TypeVar
from typing import overload

_T = TypeVar("_T")
_S = TypeVar("_S")

# noinspection PyPep8Naming
class cached_property(Generic[_T]):
    func: Callable[[Any], _T]
    attrname: Optional[str]
    lock: RLock
    def __init__(self, func: Callable[[Any], _T]) -> None: ...
    @overload
    def __get__(self, instance: None, owner: Optional[Type[Any]] = ...) -> cached_property[_T]: ...
    @overload
    def __get__(self, instance: _S, owner: Optional[Type[Any]] = ...) -> _T: ...
    def __set_name__(self, owner: Type[Any], name: str) -> None: ...
