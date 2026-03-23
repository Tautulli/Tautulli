"""Test suite for cross-python compatibility helpers."""

import pytest

from cheroot._compat import bton, extract_bytes, ntob, ntou


@pytest.mark.parametrize(
    ('func', 'inp', 'out'),
    (
        (ntob, 'bar', b'bar'),
        (ntou, 'bar', 'bar'),
        (bton, b'bar', 'bar'),
    ),
)
def test_compat_functions_positive(func, inp, out):
    """Check that compatibility functions work with correct input."""
    assert func(inp, encoding='utf-8') == out


@pytest.mark.parametrize(
    'func',
    (
        ntob,
        ntou,
    ),
)
def test_compat_functions_negative_nonnative(func):
    """Check that compatibility functions fail loudly for incorrect input."""
    non_native_test_str = b'bar'
    with pytest.raises(TypeError):
        func(non_native_test_str, encoding='utf-8')


def test_ntou_escape():
    """Check that ``ntou`` supports escape-encoding under Python 2."""
    expected = 'hišřії'  # noqa: RUF001  # This is intended
    actual = ntou('hi\u0161\u0159\u0456\u0457', encoding='escape')
    assert actual == expected


@pytest.mark.parametrize(
    ('input_argument', 'expected_result'),
    (
        (b'qwerty', b'qwerty'),
        (memoryview(b'asdfgh'), b'asdfgh'),
    ),
)
def test_extract_bytes(input_argument, expected_result):
    """Check that legitimate inputs produce bytes."""
    assert extract_bytes(input_argument) == expected_result


def test_extract_bytes_invalid():
    """Ensure that invalid input causes exception to be raised."""
    with pytest.raises(
        ValueError,
        match=r'^extract_bytes\(\) only accepts bytes '
        'and memoryview/buffer$',
    ):
        extract_bytes('some юнікод їїї')
