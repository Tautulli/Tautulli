from __future__ import annotations

import functools
import io
import itertools
import os
import re
import sys
import textwrap
from collections.abc import Callable, Generator, Iterable, Sequence
from importlib.resources import files
from typing import (
    TYPE_CHECKING,
    Literal,
    Protocol,
    SupportsIndex,
    TypeVar,
    Union,
    cast,
    overload,
)

from jaraco.context import ExceptionTrap
from jaraco.functools import compose, method_cache

if sys.version_info >= (3, 11):  # pragma: no cover
    from importlib.resources.abc import Traversable
else:  # pragma: no cover
    from importlib.abc import Traversable

if TYPE_CHECKING:
    from _typeshed import (
        FileDescriptorOrPath,
        SupportsIter,
        SupportsNext,
    )
    from typing_extensions import Self, TypeAlias, TypeGuard, Unpack

    Openable: TypeAlias = FileDescriptorOrPath
else:
    Openable = Union[str, bytes, os.PathLike, int]

_T = TypeVar("_T")


class _SupportsDecode(Protocol):
    def decode(self) -> object: ...


def substitution(old: str, new: str) -> Callable[[str], str]:
    """
    Return a function that will perform a substitution on a string
    """
    return lambda s: s.replace(old, new)


def multi_substitution(*substitutions: str) -> Callable[[str], str]:
    """
    Take a sequence of pairs specifying substitutions, and create
    a function that performs those substitutions.

    >>> multi_substitution(('foo', 'bar'), ('bar', 'baz'))('foo')
    'baz'
    """
    callables: Iterable[Callable[[str], str]] = itertools.starmap(
        substitution, substitutions
    )
    # compose function applies last function first, so reverse the
    #  substitutions to get the expected order.
    reversed_ = reversed(tuple(callables))
    return compose(*reversed_)


class FoldedCase(str):
    """
    A case insensitive string class; behaves just like str
    except compares equal when the only variation is case.

    >>> s = FoldedCase('hello world')

    >>> s == 'Hello World'
    True

    >>> 'Hello World' == s
    True

    >>> s != 'Hello World'
    False

    >>> s.index('O')
    4

    >>> s.split('O')
    ['hell', ' w', 'rld']

    Like ``str``, split accepts None as ''.

    >>> s.split(None)
    ['hello', 'world']

    >>> sorted(map(FoldedCase, ['GAMMA', 'alpha', 'Beta']))
    ['alpha', 'Beta', 'GAMMA']

    Sequence membership is straightforward.

    >>> "Hello World" in [s]
    True
    >>> s in ["Hello World"]
    True

    Allows testing for set inclusion, but candidate and elements
    must both be folded.

    >>> FoldedCase("Hello World") in {s}
    True
    >>> s in {FoldedCase("Hello World")}
    True

    String inclusion works as long as the FoldedCase object
    is on the right.

    >>> "hello" in FoldedCase("Hello World")
    True

    But not if the FoldedCase object is on the left:

    >>> FoldedCase('hello') in 'Hello World'
    False

    In that case, use ``in_``:

    >>> FoldedCase('hello').in_('Hello World')
    True

    >>> FoldedCase('hello') > FoldedCase('Hello')
    False

    >>> FoldedCase('ß') == FoldedCase('ss')
    True

    Also supports string to object comparisons:

    >>> FoldedCase('foo') == object()
    False
    >>> FoldedCase('foo') != object()
    True
    >>> object() in FoldedCase('foo')
    False
    """

    def __lt__(self, other: str) -> bool:
        return self.casefold() < other.casefold()

    def __gt__(self, other: str) -> bool:
        return self.casefold() > other.casefold()

    @functools.singledispatchmethod
    def __eq__(self, other: object) -> bool:
        return False

    @__eq__.register
    def _(self, other: str) -> bool:
        return self.casefold().__eq__(other.casefold())

    @functools.singledispatchmethod
    def __ne__(self, other: object) -> bool:
        return True

    @__ne__.register
    def _(self, other: str) -> bool:
        return self.casefold().__ne__(other.casefold())

    def __hash__(self) -> int:
        return hash(self.casefold())

    @functools.singledispatchmethod
    def __contains__(self, other: object) -> bool:
        return False

    @__contains__.register
    def _(self, other: str) -> bool:
        return super().casefold().__contains__(other.casefold())

    def in_(self, other: str) -> bool:
        """Does self appear in other?"""
        return self in FoldedCase(other)

    # cache casefold since it's likely to be called frequently.
    @method_cache
    def casefold(self) -> str:
        return super().casefold()

    def index(
        self,
        sub: str,
        start: SupportsIndex | None = None,
        end: SupportsIndex | None = None,
    ) -> int:
        return self.casefold().index(sub.casefold(), start, end)

    @functools.singledispatchmethod
    def split(
        self, splitter: str | None = ' ', maxsplit: SupportsIndex = 0
    ) -> list[str]:
        return self.split(' ', maxsplit=maxsplit)

    @split.register
    def _(self, splitter: str, maxsplit: SupportsIndex = 0) -> list[str]:
        pattern = re.compile(re.escape(splitter), re.I)
        return pattern.split(self, int(maxsplit))


@ExceptionTrap(UnicodeDecodeError).passes  # type: ignore[no-untyped-call, untyped-decorator, unused-ignore, misc] # jaraco/jaraco.context#15
def is_decodable(value: _SupportsDecode) -> None:
    r"""
    Return True if the supplied value is decodable (using the default
    encoding).

    >>> is_decodable(b'\xff')
    False
    >>> is_decodable(b'\x32')
    True
    """
    value.decode()


def is_binary(value: _SupportsDecode) -> TypeGuard[bytes]:
    r"""
    Return True if the value appears to be binary (that is, it's a byte
    string and isn't decodable).

    >>> is_binary(b'\xff')
    True
    >>> is_binary('\xff')
    False
    """
    return isinstance(value, bytes) and not is_decodable(value)


def trim(s: str) -> str:
    r"""
    Trim something like a docstring to remove the whitespace that
    is common due to indentation and formatting.

    >>> trim("\n\tfoo = bar\n\t\tbar = baz\n")
    'foo = bar\n\tbar = baz'
    """
    return textwrap.dedent(s).strip()


def wrap(s: str) -> str:
    """
    Wrap lines of text, retaining existing newlines as
    paragraph markers.

    >>> print(wrap(lorem_ipsum))
    Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do
    eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad
    minim veniam, quis nostrud exercitation ullamco laboris nisi ut
    aliquip ex ea commodo consequat. Duis aute irure dolor in
    reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla
    pariatur. Excepteur sint occaecat cupidatat non proident, sunt in
    culpa qui officia deserunt mollit anim id est laborum.
    <BLANKLINE>
    Curabitur pretium tincidunt lacus. Nulla gravida orci a odio. Nullam
    varius, turpis et commodo pharetra, est eros bibendum elit, nec luctus
    magna felis sollicitudin mauris. Integer in mauris eu nibh euismod
    gravida. Duis ac tellus et risus vulputate vehicula. Donec lobortis
    risus a elit. Etiam tempor. Ut ullamcorper, ligula eu tempor congue,
    eros est euismod turpis, id tincidunt sapien risus a quam. Maecenas
    fermentum consequat mi. Donec fermentum. Pellentesque malesuada nulla
    a mi. Duis sapien sem, aliquet nec, commodo eget, consequat quis,
    neque. Aliquam faucibus, elit ut dictum aliquet, felis nisl adipiscing
    sapien, sed malesuada diam lacus eget erat. Cras mollis scelerisque
    nunc. Nullam arcu. Aliquam consequat. Curabitur augue lorem, dapibus
    quis, laoreet et, pretium ac, nisi. Aenean magna nisl, mollis quis,
    molestie eu, feugiat in, orci. In hac habitasse platea dictumst.
    """
    paragraphs = s.splitlines()
    wrapped = ('\n'.join(textwrap.wrap(para)) for para in paragraphs)
    return '\n\n'.join(wrapped)


def unwrap(s: str) -> str:
    r"""
    Given a multi-line string, return an unwrapped version.

    >>> wrapped = wrap(lorem_ipsum)
    >>> wrapped.count('\n')
    20
    >>> unwrapped = unwrap(wrapped)
    >>> unwrapped.count('\n')
    1
    >>> print(unwrapped)
    Lorem ipsum dolor sit amet, consectetur adipiscing ...
    Curabitur pretium tincidunt lacus. Nulla gravida orci ...

    """
    paragraphs = re.split(r'\n\n+', s)
    cleaned = (para.replace('\n', ' ') for para in paragraphs)
    return '\n'.join(cleaned)


lorem_ipsum: str = (
    files(__name__).joinpath('Lorem ipsum.txt').read_text(encoding='utf-8')
)


class Splitter:
    """object that will split a string with the given arguments for each call

    >>> s = Splitter(',')
    >>> s('hello, world, this is your, master calling')
    ['hello', ' world', ' this is your', ' master calling']
    """

    def __init__(self, *args: Unpack[tuple[str | None, SupportsIndex]]) -> None:
        self.args = args

    def __call__(self, s: str) -> list[str]:
        return s.split(*self.args)


def indent(string: str, prefix: str = ' ' * 4) -> str:
    """
    >>> indent('foo')
    '    foo'
    """
    return prefix + string


class WordSet(tuple[str, ...]):
    """
    Given an identifier, return the words that identifier represents,
    whether in camel case, underscore-separated, etc.

    >>> WordSet.parse("camelCase")
    ('camel', 'Case')

    >>> WordSet.parse("under_sep")
    ('under', 'sep')

    Acronyms should be retained

    >>> WordSet.parse("firstSNL")
    ('first', 'SNL')

    >>> WordSet.parse("you_and_I")
    ('you', 'and', 'I')

    >>> WordSet.parse("A simple test")
    ('A', 'simple', 'test')

    Multiple caps should not interfere with the first cap of another word.

    >>> WordSet.parse("myABCClass")
    ('my', 'ABC', 'Class')

    The result is a WordSet, providing access to other forms.

    >>> WordSet.parse("myABCClass").underscore_separated()
    'my_ABC_Class'

    >>> WordSet.parse('a-command').camel_case()
    'ACommand'

    >>> WordSet.parse('someIdentifier').lowered().space_separated()
    'some identifier'

    Slices of the result should return another WordSet.

    >>> WordSet.parse('taken-out-of-context')[1:].underscore_separated()
    'out_of_context'

    >>> WordSet.from_class_name(WordSet()).lowered().space_separated()
    'word set'

    >>> example = WordSet.parse('figured it out')
    >>> example.headless_camel_case()
    'figuredItOut'
    >>> example.dash_separated()
    'figured-it-out'

    """

    _pattern = re.compile('([A-Z]?[a-z]+)|([A-Z]+(?![a-z]))')

    def capitalized(self) -> WordSet:
        return WordSet(word.capitalize() for word in self)

    def lowered(self) -> WordSet:
        return WordSet(word.lower() for word in self)

    def camel_case(self) -> str:
        return ''.join(self.capitalized())

    def headless_camel_case(self) -> str:
        words = iter(self)
        first = next(words).lower()
        new_words = itertools.chain((first,), WordSet(words).camel_case())
        return ''.join(new_words)

    def underscore_separated(self) -> str:
        return '_'.join(self)

    def dash_separated(self) -> str:
        return '-'.join(self)

    def space_separated(self) -> str:
        return ' '.join(self)

    def trim_right(self, item: str) -> WordSet:
        """
        Remove the item from the end of the set.

        >>> WordSet.parse('foo bar').trim_right('foo')
        ('foo', 'bar')
        >>> WordSet.parse('foo bar').trim_right('bar')
        ('foo',)
        >>> WordSet.parse('').trim_right('bar')
        ()
        """
        return self[:-1] if self and self[-1] == item else self

    def trim_left(self, item: str) -> WordSet:
        """
        Remove the item from the beginning of the set.

        >>> WordSet.parse('foo bar').trim_left('foo')
        ('bar',)
        >>> WordSet.parse('foo bar').trim_left('bar')
        ('foo', 'bar')
        >>> WordSet.parse('').trim_left('bar')
        ()
        """
        return self[1:] if self and self[0] == item else self

    def trim(self, item: str) -> WordSet:
        """
        >>> WordSet.parse('foo bar').trim('foo')
        ('bar',)
        """
        return self.trim_left(item).trim_right(item)

    @overload  # type:ignore[override] # more restricted return type
    def __getitem__(self, item: slice) -> WordSet: ...
    @overload
    def __getitem__(self, item: SupportsIndex) -> str: ...
    def __getitem__(self, item: slice | SupportsIndex) -> WordSet | str:
        result = super().__getitem__(item)
        if isinstance(result, tuple):
            return WordSet(result)
        return result

    @classmethod
    def parse(cls, identifier: str) -> WordSet:
        matches = cls._pattern.finditer(identifier)
        return WordSet(match.group(0) for match in matches)

    @classmethod
    def from_class_name(cls, subject: object) -> WordSet:
        return cls.parse(subject.__class__.__name__)


# for backward compatibility
words = WordSet.parse


def simple_html_strip(s: str) -> str:
    r"""
    Remove HTML from the string `s`.

    >>> str(simple_html_strip(''))
    ''

    >>> print(simple_html_strip('A <bold>stormy</bold> day in paradise'))
    A stormy day in paradise

    >>> print(simple_html_strip('Somebody <!-- do not --> tell the truth.'))
    Somebody  tell the truth.

    >>> print(simple_html_strip('What about<br/>\nmultiple lines?'))
    What about
    multiple lines?
    """
    html_stripper = re.compile('(<!--.*?-->)|(<[^>]*>)|([^<]+)', re.DOTALL)
    texts = (match.group(3) or '' for match in html_stripper.finditer(s))
    return ''.join(texts)


class SeparatedValues(str):
    """
    A string separated by a separator. Overrides __iter__ for getting
    the values.

    >>> list(SeparatedValues('a,b,c'))
    ['a', 'b', 'c']

    Whitespace is stripped and empty values are discarded.

    >>> list(SeparatedValues(' a,   b   , c,  '))
    ['a', 'b', 'c']
    """

    separator = ','

    def __iter__(self) -> filter[str]:
        parts = self.split(self.separator)
        return filter(None, (part.strip() for part in parts))


class Stripper:
    r"""
    Given a series of lines, find the common prefix and strip it from them.

    >>> lines = [
    ...     'abcdefg\n',
    ...     'abc\n',
    ...     'abcde\n',
    ... ]
    >>> res = Stripper.strip_prefix(lines)
    >>> res.prefix
    'abc'
    >>> list(res.lines)
    ['defg\n', '\n', 'de\n']

    If no prefix is common, nothing should be stripped.

    >>> lines = [
    ...     'abcd\n',
    ...     '1234\n',
    ... ]
    >>> res = Stripper.strip_prefix(lines)
    >>> res.prefix = ''
    >>> list(res.lines)
    ['abcd\n', '1234\n']
    """

    def __init__(self, prefix: str | None, lines: Iterable[str]) -> None:
        self.prefix = prefix
        self.lines = map(self, lines)

    @classmethod
    def strip_prefix(cls, lines: Iterable[str]) -> Self:
        prefix_lines, lines = itertools.tee(lines)
        prefix = functools.reduce(cls.common_prefix, prefix_lines)
        return cls(prefix, lines)

    def __call__(self, line: str) -> str:
        if not self.prefix:
            return line
        null, prefix, rest = line.partition(self.prefix)
        return rest

    @overload
    @staticmethod
    def common_prefix(s1: str, s2: str) -> str: ...
    @overload
    @staticmethod
    def common_prefix(s1: Sequence[str], s2: Sequence[str]) -> Sequence[str]: ...
    @staticmethod
    def common_prefix(s1: Sequence[str], s2: Sequence[str]) -> Sequence[str]:
        """
        Return the common prefix of two lines.
        """
        index = min(len(s1), len(s2))
        while s1[:index] != s2[:index]:
            index -= 1
        return s1[:index]


def remove_prefix(text: str, prefix: str) -> str:
    """
    Remove the prefix from the text if it exists.

    >>> remove_prefix('underwhelming performance', 'underwhelming ')
    'performance'

    >>> remove_prefix('something special', 'sample')
    'something special'
    """
    null, prefix, rest = text.rpartition(prefix)
    return rest


def remove_suffix(text: str, suffix: str) -> str:
    """
    Remove the suffix from the text if it exists.

    >>> remove_suffix('name.git', '.git')
    'name'

    >>> remove_suffix('something special', 'sample')
    'something special'
    """
    rest, suffix, null = text.partition(suffix)
    return rest


def normalize_newlines(text: str) -> str:
    r"""
    Replace alternate newlines with the canonical newline.

    >>> normalize_newlines('Lorem Ipsum\u2029')
    'Lorem Ipsum\n'
    >>> normalize_newlines('Lorem Ipsum\r\n')
    'Lorem Ipsum\n'
    >>> normalize_newlines('Lorem Ipsum\x85')
    'Lorem Ipsum\n'
    """
    newlines = ['\r\n', '\r', '\n', '\u0085', '\u2028', '\u2029']
    pattern = '|'.join(newlines)
    return re.sub(pattern, '\n', text)


def _nonblank(str: str) -> bool | Literal['']:
    return str and not str.startswith('#')


@functools.singledispatch
def yield_lines(iterable: Iterable[_T] | str) -> itertools.chain[str]:
    r"""
    Yield valid lines of a string or iterable.

    >>> list(yield_lines(''))
    []
    >>> list(yield_lines(['foo', 'bar']))
    ['foo', 'bar']
    >>> list(yield_lines('foo\nbar'))
    ['foo', 'bar']
    >>> list(yield_lines('\nfoo\n#bar\nbaz #comment'))
    ['foo', 'baz #comment']
    >>> list(yield_lines(['foo\nbar', 'baz', 'bing\n\n\n']))
    ['foo', 'bar', 'baz', 'bing']
    """
    return itertools.chain.from_iterable(map(yield_lines, iterable))


@yield_lines.register(str)
def _(text: str) -> filter[str]:
    return clean(text.splitlines())


def clean(lines: Iterable[str]) -> filter[str]:
    """
    Yield non-blank, non-comment elements from lines.
    """
    return filter(_nonblank, map(str.strip, lines))


def drop_comment(line: str) -> str:
    """
    Drop comments.

    >>> drop_comment('foo # bar')
    'foo'

    A hash without a space may be in a URL.

    >>> drop_comment('http://example.com/foo#bar')
    'http://example.com/foo#bar'
    """
    return line.partition(' #')[0]


def join_continuation(lines: SupportsIter[SupportsNext[str]]) -> Generator[str]:
    r"""
    Join lines continued by a trailing backslash.

    >>> list(join_continuation(['foo \\', 'bar', 'baz']))
    ['foobar', 'baz']
    >>> list(join_continuation(['foo \\', 'bar', 'baz']))
    ['foobar', 'baz']
    >>> list(join_continuation(['foo \\', 'bar \\', 'baz']))
    ['foobarbaz']

    Not sure why, but...
    The character preceding the backslash is also elided.

    >>> list(join_continuation(['goo\\', 'dly']))
    ['godly']

    A terrible idea, but...
    If no line is available to continue, suppress the lines.

    >>> list(join_continuation(['foo', 'bar\\', 'baz\\']))
    ['foo']
    """
    lines_ = iter(lines)
    for item in lines_:  # type: ignore[attr-defined] # A bit of a false positive with iteration dunder fallback
        while item.endswith('\\'):
            try:
                item = item[:-2].strip() + next(lines_)
            except StopIteration:
                return
        yield item


# https://docs.python.org/3/library/io.html#io.TextIOBase.newlines
NewlineSpec: TypeAlias = Union[str, tuple[str, ...], None]


@functools.singledispatch
def read_newlines(
    filename: Union[Openable, io.TextIOWrapper],  # noqa: UP007 # singledispatch uses the annotation at runtime (python 3.9)
    limit: int | None = 1024,
) -> NewlineSpec:
    r"""
    >>> tmp_path = getfixture('tmp_path')
    >>> filename = tmp_path / 'out.txt'
    >>> _ = filename.write_text('foo\n', newline='', encoding='utf-8')
    >>> read_newlines(filename)
    '\n'
    >>> _ = filename.write_text('foo\r\n', newline='', encoding='utf-8')
    >>> read_newlines(filename)
    '\r\n'
    >>> _ = filename.write_text('foo\r\nbar\nbing\r', newline='', encoding='utf-8')
    >>> read_newlines(filename)
    ('\r', '\n', '\r\n')
    """
    if sys.version_info >= (3, 10):
        assert isinstance(filename, Openable)
    else:  # pragma: no cover
        filename = cast(Openable, filename)
    with open(filename, encoding='utf-8') as fp:
        return read_newlines(fp, limit=limit)


@read_newlines.register
def _(
    filename: io.TextIOWrapper,
    limit: Union[int, None] = 1024,  # noqa: UP007 # singledispatch uses the annotation at runtime (python 3.9)
) -> NewlineSpec:
    filename.read(limit)
    return filename.newlines


def lines_from(input: Traversable) -> Generator[str]:
    """
    Generate lines from a :class:`importlib.resources.abc.Traversable` path.

    >>> lines = lines_from(files(__name__).joinpath('Lorem ipsum.txt'))
    >>> next(lines)
    'Lorem ipsum...'
    >>> next(lines)
    'Curabitur pretium...'
    """
    with input.open(encoding='utf-8') as stream:
        yield from stream
