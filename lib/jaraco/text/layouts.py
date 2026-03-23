from __future__ import annotations

from typing import TYPE_CHECKING, Union

if TYPE_CHECKING:
    from _typeshed import SupportsGetItem, SupportsRead
    from typing_extensions import TypeAlias

    # Same as builtins._TranslateTable from typeshed
    _TranslateTable: TypeAlias = SupportsGetItem[int, Union[str, int, None]]

qwerty = "-=qwertyuiop[]asdfghjkl;'zxcvbnm,./_+QWERTYUIOP{}ASDFGHJKL:\"ZXCVBNM<>?"
dvorak = "[]',.pyfgcrl/=aoeuidhtns-;qjkxbmwvz{}\"<>PYFGCRL?+AOEUIDHTNS_:QJKXBMWVZ"


to_dvorak = str.maketrans(qwerty, dvorak)
to_qwerty = str.maketrans(dvorak, qwerty)


def translate(input: str, translation: _TranslateTable) -> str:
    """
    >>> translate('dvorak', to_dvorak)
    'ekrpat'
    >>> translate('qwerty', to_qwerty)
    'x,dokt'
    """
    return input.translate(translation)


def _translate_stream(stream: SupportsRead[str], translation: _TranslateTable) -> None:
    """
    >>> import io
    >>> _translate_stream(io.StringIO('foo'), to_dvorak)
    urr
    """
    print(translate(stream.read(), translation))
