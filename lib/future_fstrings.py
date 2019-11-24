from __future__ import absolute_import
from __future__ import unicode_literals

import argparse
import codecs
import encodings
import io
import sys


utf_8 = encodings.search_function('utf8')


class TokenSyntaxError(SyntaxError):
    def __init__(self, e, token):
        super(TokenSyntaxError, self).__init__(e)
        self.e = e
        self.token = token


def _find_literal(s, start, level, parts, exprs):
    """Roughly Python/ast.c:fstring_find_literal"""
    i = start
    parse_expr = True

    while i < len(s):
        ch = s[i]

        if ch in ('{', '}'):
            if level == 0:
                if i + 1 < len(s) and s[i + 1] == ch:
                    i += 2
                    parse_expr = False
                    break
                elif ch == '}':
                    raise SyntaxError("f-string: single '}' is not allowed")
            break

        i += 1

    parts.append(s[start:i])
    return i, parse_expr and i < len(s)


def _find_expr(s, start, level, parts, exprs):
    """Roughly Python/ast.c:fstring_find_expr"""
    i = start
    nested_depth = 0
    quote_char = None
    triple_quoted = None

    def _check_end():
        if i == len(s):
            raise SyntaxError("f-string: expecting '}'")

    if level >= 2:
        raise SyntaxError("f-string: expressions nested too deeply")

    parts.append(s[i])
    i += 1

    while i < len(s):
        ch = s[i]

        if ch == '\\':
            raise SyntaxError(
                'f-string expression part cannot include a backslash',
            )
        if quote_char is not None:
            if ch == quote_char:
                if triple_quoted:
                    if i + 2 < len(s) and s[i + 1] == ch and s[i + 2] == ch:
                        i += 2
                        quote_char = None
                        triple_quoted = None
                else:
                    quote_char = None
                    triple_quoted = None
        elif ch in ('"', "'"):
            quote_char = ch
            if i + 2 < len(s) and s[i + 1] == ch and s[i + 2] == ch:
                triple_quoted = True
                i += 2
            else:
                triple_quoted = False
        elif ch in ('[', '{', '('):
            nested_depth += 1
        elif nested_depth and ch in (']', '}', ')'):
            nested_depth -= 1
        elif ch == '#':
            raise SyntaxError("f-string expression cannot include '#'")
        elif nested_depth == 0 and ch in ('!', ':', '}'):
            if ch == '!' and i + 1 < len(s) and s[i + 1] == '=':
                # Allow != at top level as `=` isn't a valid conversion
                pass
            else:
                break
        i += 1

    if quote_char is not None:
        raise SyntaxError('f-string: unterminated string')
    elif nested_depth:
        raise SyntaxError("f-string: mismatched '(', '{', or '['")
    _check_end()

    exprs.append(s[start + 1:i])

    if s[i] == '!':
        parts.append(s[i])
        i += 1
        _check_end()
        parts.append(s[i])
        i += 1

    _check_end()

    if s[i] == ':':
        parts.append(s[i])
        i += 1
        _check_end()
        i = _fstring_parse(s, i, level + 1, parts, exprs)

    _check_end()
    if s[i] != '}':
        raise SyntaxError("f-string: expecting '}'")

    parts.append(s[i])
    i += 1
    return i


def _fstring_parse(s, i, level, parts, exprs):
    """Roughly Python/ast.c:fstring_find_literal_and_expr"""
    while True:
        i, parse_expr = _find_literal(s, i, level, parts, exprs)
        if i == len(s) or s[i] == '}':
            return i
        if parse_expr:
            i = _find_expr(s, i, level, parts, exprs)


def _fstring_parse_outer(s, i, level, parts, exprs):
    for q in ('"' * 3, "'" * 3, '"', "'"):
        if s.startswith(q):
            s = s[len(q):len(s) - len(q)]
            break
    else:
        raise AssertionError('unreachable')
    parts.append(q)
    ret = _fstring_parse(s, i, level, parts, exprs)
    parts.append(q)
    return ret


def _is_f(token):
    import tokenize_rt

    prefix, _ = tokenize_rt.parse_string_literal(token.src)
    return 'f' in prefix.lower()


def _make_fstring(tokens):
    import tokenize_rt

    new_tokens = []
    exprs = []

    for i, token in enumerate(tokens):
        if token.name == 'STRING' and _is_f(token):
            prefix, s = tokenize_rt.parse_string_literal(token.src)
            parts = []
            try:
                _fstring_parse_outer(s, 0, 0, parts, exprs)
            except SyntaxError as e:
                raise TokenSyntaxError(e, tokens[i - 1])
            if 'r' in prefix.lower():
                parts = [s.replace('\\', '\\\\') for s in parts]
            token = token._replace(src=''.join(parts))
        elif token.name == 'STRING':
            new_src = token.src.replace('{', '{{').replace('}', '}}')
            token = token._replace(src=new_src)
        new_tokens.append(token)

    exprs = ('({})'.format(expr) for expr in exprs)
    format_src = '.format({})'.format(', '.join(exprs))
    new_tokens.append(tokenize_rt.Token('FORMAT', src=format_src))

    return new_tokens


def decode(b, errors='strict'):
    import tokenize_rt  # pip install future-fstrings[rewrite]

    u, length = utf_8.decode(b, errors)
    tokens = tokenize_rt.src_to_tokens(u)

    to_replace = []
    start = end = seen_f = None

    for i, token in enumerate(tokens):
        if start is None:
            if token.name == 'STRING':
                start, end = i, i + 1
                seen_f = _is_f(token)
        elif token.name == 'STRING':
            end = i + 1
            seen_f |= _is_f(token)
        elif token.name not in tokenize_rt.NON_CODING_TOKENS:
            if seen_f:
                to_replace.append((start, end))
            start = end = seen_f = None

    for start, end in reversed(to_replace):
        try:
            tokens[start:end] = _make_fstring(tokens[start:end])
        except TokenSyntaxError as e:
            msg = str(e.e)
            line = u.splitlines()[e.token.line - 1]
            bts = line.encode('UTF-8')[:e.token.utf8_byte_offset]
            indent = len(bts.decode('UTF-8'))
            raise SyntaxError(msg + '\n\n' + line + '\n' + ' ' * indent + '^')
    return tokenize_rt.tokens_to_src(tokens), length


class IncrementalDecoder(codecs.BufferedIncrementalDecoder):
    def _buffer_decode(self, input, errors, final):  # pragma: no cover
        if final:
            return decode(input, errors)
        else:
            return '', 0


class StreamReader(utf_8.streamreader, object):
    """decode is deferred to support better error messages"""
    _stream = None
    _decoded = False

    @property
    def stream(self):
        if not self._decoded:
            text, _ = decode(self._stream.read())
            self._stream = io.BytesIO(text.encode('UTF-8'))
            self._decoded = True
        return self._stream

    @stream.setter
    def stream(self, stream):
        self._stream = stream
        self._decoded = False


def _natively_supports_fstrings():
    try:
        return eval('f"hi"') == 'hi'
    except SyntaxError:
        return False


fstring_decode = decode
SUPPORTS_FSTRINGS = _natively_supports_fstrings()
if SUPPORTS_FSTRINGS:  # pragma: no cover
    decode = utf_8.decode  # noqa
    IncrementalDecoder = utf_8.incrementaldecoder  # noqa
    StreamReader = utf_8.streamreader  # noqa

# codec api

codec_map = {
    name: codecs.CodecInfo(
        name=name,
        encode=utf_8.encode,
        decode=decode,
        incrementalencoder=utf_8.incrementalencoder,
        incrementaldecoder=IncrementalDecoder,
        streamreader=StreamReader,
        streamwriter=utf_8.streamwriter,
    )
    for name in ('future-fstrings', 'future_fstrings')
}


def register():  # pragma: no cover
    codecs.register(codec_map.get)


def main(argv=None):
    parser = argparse.ArgumentParser(description='Prints transformed source.')
    parser.add_argument('filename')
    args = parser.parse_args(argv)

    with open(args.filename, 'rb') as f:
        text, _ = fstring_decode(f.read())
    getattr(sys.stdout, 'buffer', sys.stdout).write(text.encode('UTF-8'))


if __name__ == '__main__':
    exit(main())
