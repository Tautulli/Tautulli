from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

import argparse
import collections
import io
import keyword
import re
import tokenize
from typing import Generator
from typing import Iterable
from typing import List
from typing import Optional
from typing import Pattern
from typing import Sequence
from typing import Tuple


ESCAPED_NL = 'ESCAPED_NL'
UNIMPORTANT_WS = 'UNIMPORTANT_WS'
NON_CODING_TOKENS = frozenset(('COMMENT', ESCAPED_NL, 'NL', UNIMPORTANT_WS))


class Offset(collections.namedtuple('Offset', ('line', 'utf8_byte_offset'))):
    __slots__ = ()

    def __new__(cls, line=None, utf8_byte_offset=None):
        # type: (Optional[int], Optional[int]) -> None
        return super(Offset, cls).__new__(cls, line, utf8_byte_offset)


class Token(
    collections.namedtuple(
        'Token', ('name', 'src', 'line', 'utf8_byte_offset'),
    ),
):
    __slots__ = ()

    def __new__(cls, name, src, line=None, utf8_byte_offset=None):
        # type: (str, str, Optional[int], Optional[int]) -> None
        return super(Token, cls).__new__(
            cls, name, src, line, utf8_byte_offset,
        )

    @property
    def offset(self):  # type: () -> Offset
        return Offset(self.line, self.utf8_byte_offset)


_string_re = re.compile('^([^\'"]*)(.*)$', re.DOTALL)
_string_prefixes = frozenset('bfru')
_escaped_nl_re = re.compile(r'\\(\n|\r\n|\r)')


def _re_partition(regex, s):
    # type: (Pattern[str], str) -> Tuple[str, str, str]
    match = regex.search(s)
    if match:
        return s[:match.start()], s[slice(*match.span())], s[match.end():]
    else:
        return (s, '', '')


def src_to_tokens(src):  # type: (str) -> List[Token]
    tokenize_target = io.StringIO(src)
    lines = ('',) + tuple(tokenize_target)

    tokenize_target.seek(0)

    tokens = []
    last_line = 1
    last_col = 0

    for (
            tok_type, tok_text, (sline, scol), (eline, ecol), line,
    ) in tokenize.generate_tokens(tokenize_target.readline):
        if sline > last_line:
            newtok = lines[last_line][last_col:]
            for lineno in range(last_line + 1, sline):
                newtok += lines[lineno]
            if scol > 0:
                newtok += lines[sline][:scol]

            # a multiline unimportant whitespace may contain escaped newlines
            while _escaped_nl_re.search(newtok):
                ws, nl, newtok = _re_partition(_escaped_nl_re, newtok)
                if ws:
                    tokens.append(Token(UNIMPORTANT_WS, ws))
                tokens.append(Token(ESCAPED_NL, nl))
            if newtok:
                tokens.append(Token(UNIMPORTANT_WS, newtok))

        elif scol > last_col:
            tokens.append(Token(UNIMPORTANT_WS, line[last_col:scol]))

        tok_name = tokenize.tok_name[tok_type]
        utf8_byte_offset = len(line[:scol].encode('UTF-8'))
        # when a string prefix is not recognized, the tokenizer produces a
        # NAME token followed by a STRING token
        if (
                tok_name == 'STRING' and
                tokens and
                tokens[-1].name == 'NAME' and
                frozenset(tokens[-1].src.lower()) <= _string_prefixes
        ):
            newsrc = tokens[-1].src + tok_text
            tokens[-1] = tokens[-1]._replace(src=newsrc, name=tok_name)
        # produce octal literals as a single token in python 3 as well
        elif (
                tok_name == 'NUMBER' and
                tokens and
                tokens[-1].name == 'NUMBER'
        ):  # pragma: no cover (PY3)
            tokens[-1] = tokens[-1]._replace(src=tokens[-1].src + tok_text)
        # produce long literals as a single token in python 3 as well
        elif (
                tok_name == 'NAME' and
                tok_text.lower() == 'l' and
                tokens and
                tokens[-1].name == 'NUMBER'
        ):  # pragma: no cover (PY3)
            tokens[-1] = tokens[-1]._replace(src=tokens[-1].src + tok_text)
        else:
            tokens.append(Token(tok_name, tok_text, sline, utf8_byte_offset))
        last_line, last_col = eline, ecol

    return tokens


def tokens_to_src(tokens):  # type: (Iterable[Token]) -> str
    return ''.join(tok.src for tok in tokens)


def reversed_enumerate(tokens):
    # type: (Sequence[Token]) -> Generator[Tuple[int, Token], None, None]
    for i in reversed(range(len(tokens))):
        yield i, tokens[i]


def parse_string_literal(src):  # type: (str) -> Tuple[str, str]
    """parse a string literal's source into (prefix, string)"""
    match = _string_re.match(src)
    assert match is not None
    return match.group(1), match.group(2)


def rfind_string_parts(tokens, i):
    # type: (Sequence[Token], int) -> Tuple[int, ...]
    """find the indicies of the string parts of a (joined) string literal

    - `i` should start at the end of the string literal
    - returns `()` (an empty tuple) for things which are not string literals
    """
    ret = []
    depth = 0
    for i in range(i, -1, -1):
        token = tokens[i]
        if token.name == 'STRING':
            ret.append(i)
        elif token.name in NON_CODING_TOKENS:
            pass
        elif token.src == ')':
            depth += 1
        elif depth and token.src == '(':
            depth -= 1
            # if we closed the paren(s) make sure it was a parenthesized string
            # and not actually a call
            if depth == 0:
                for j in range(i - 1, -1, -1):
                    tok = tokens[j]
                    if tok.name in NON_CODING_TOKENS:
                        pass
                    # this was actually a call and not a parenthesized string
                    elif (
                            tok.src in {']', ')'} or (
                                tok.name == 'NAME' and
                                tok.src not in keyword.kwlist
                            )
                    ):
                        return ()
                    else:
                        break
                break
        elif depth:  # it looked like a string but wasn't
            return ()
        else:
            break
    return tuple(reversed(ret))


def main(argv=None):  # type: (Optional[Sequence[str]]) -> int
    parser = argparse.ArgumentParser()
    parser.add_argument('filename')
    args = parser.parse_args(argv)
    with io.open(args.filename) as f:
        tokens = src_to_tokens(f.read())

    def no_u_repr(s):  # type: (str) -> str
        return repr(s).lstrip('u')

    for token in tokens:
        if token.name == UNIMPORTANT_WS:
            line, col = '?', '?'
        else:
            line, col = token.line, token.utf8_byte_offset
        print(
            '{}:{} {} {}'.format(
                line, col, token.name, no_u_repr(token.src),
            ),
        )

    return 0


if __name__ == '__main__':
    exit(main())
