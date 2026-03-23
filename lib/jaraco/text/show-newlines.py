from __future__ import annotations

import inflect
import typer
from more_itertools import always_iterable

import jaraco.text


def report_newlines(input: typer.FileText) -> None:
    r"""
    Report the newlines in the indicated file.

    >>> tmp_path = getfixture('tmp_path')
    >>> filename = tmp_path / 'out.txt'
    >>> _ = filename.write_text('foo\nbar\n', newline='', encoding='utf-8')
    >>> report_newlines(filename)
    newline is '\n'
    >>> filename = tmp_path / 'out.txt'
    >>> _ = filename.write_text('foo\nbar\r\n', newline='', encoding='utf-8')
    >>> report_newlines(filename)
    newlines are ('\n', '\r\n')
    """
    newlines = jaraco.text.read_newlines(input)
    count = len(tuple(always_iterable(newlines)))
    engine = inflect.engine()
    print(
        # Pyright typing issue: jaraco/inflect#210
        engine.plural_noun("newline", count),
        engine.plural_verb("is", count),
        repr(newlines),
    )


__name__ == '__main__' and typer.run(report_newlines)  # type: ignore[func-returns-value]
