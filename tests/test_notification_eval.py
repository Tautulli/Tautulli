"""Tests for the eval sandbox used by notification template expressions.

str_eval() / _check_names() (plexpy/notification_handler.py) let a user embed
a Python expression in a notification template, e.g. `` `season_num00 if
episode_num00 else 'N/A'` ``. _check_names() walks the compiled code's
co_names (recursing into any nested code objects, e.g. comprehensions and
lambdas) and raises NameError for any name that is not explicitly
whitelisted. str_eval() then evaluates the expression with __builtins__
stripped out, so the only names available are the whitelist plus whatever
the caller passes in as kwargs.
"""

import pytest

from plexpy.notification_handler import _check_names, str_eval


# ---------------------------------------------------------------------------
# Whitelisted builtins: representative expressions a user could plausibly
# write in a notification template.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("expr, expected", [
    ("`bool(1)`", True),
    ("`bool(0)`", False),
    ("`int('42')`", 42),
    ("`int('not a number')`", 0),  # cast_to_int swallows ValueError
    ("`float('3.5')`", 3.5),
    ("`str(42)`", '42'),
    ("`len('hello')`", 5),
    ("`round(3.14159, 2)`", 3.14),
    ("`divmod(7, 2)`", (3, 1)),
])
def test_str_eval_whitelisted_builtins(expr, expected):
    assert str_eval(expr, {}) == expected


def test_str_eval_uses_caller_supplied_names():
    kwargs = {'season_num00': '01', 'episode_num00': '05'}
    assert str_eval("`season_num00 + episode_num00`", kwargs) == '0105'


def test_str_eval_conditional_expression_with_kwargs():
    kwargs = {'episode_num00': '05', 'season_num00': ''}
    result = str_eval("`episode_num00 if season_num00 else 'N/A'`", kwargs)
    assert result == 'N/A'


def test_str_eval_strips_surrounding_backticks():
    assert str_eval("`1 + 1`", {}) == 2
    assert str_eval("1 + 1", {}) == 2


# ---------------------------------------------------------------------------
# Rejections. str_eval's documented contract for a disallowed name is to
# raise NameError (from _check_names) -- it does not silently fall back.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("expr", [
    "().__class__",
    "[].__class__",
    "'x'.__class__",
    "(1).__class__.__bases__",
])
def test_str_eval_rejects_attribute_access(expr):
    with pytest.raises(NameError):
        str_eval(expr, {})


@pytest.mark.parametrize("expr", [
    "__import__('os')",
    "__import__('os').system('id')",
])
def test_str_eval_rejects_import_expressions(expr):
    with pytest.raises(NameError):
        str_eval(expr, {})


@pytest.mark.parametrize("expr", [
    "__builtins__",
    "().__class__.__mro__",
    "(1).__globals__",
])
def test_str_eval_rejects_dunder_access(expr):
    with pytest.raises(NameError):
        str_eval(expr, {})


@pytest.mark.parametrize("name", [
    "open", "exec", "eval", "getattr", "compile", "input",
])
def test_str_eval_rejects_non_whitelisted_names(name):
    with pytest.raises(NameError):
        str_eval(f"{name}('x')", {})


# ---------------------------------------------------------------------------
# Sandbox-escape attempts that stay within what a user can type into a
# template (attribute-chain walks toward object.__subclasses__() etc).
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("expr", [
    "[c for c in ().__class__.__mro__]",
    "().__class__.__bases__[0].__subclasses__()",
    "(lambda: 1).__globals__",
])
def test_str_eval_rejects_escape_attempts(expr):
    with pytest.raises(NameError):
        str_eval(expr, {})


# ---------------------------------------------------------------------------
# _check_names directly.
# ---------------------------------------------------------------------------

def test_check_names_allows_whitelisted_names():
    code = compile("len(x) + int(y)", '<string>', 'eval')
    assert _check_names(code, {'len': len, 'int': int, 'x': None, 'y': None}) is None


def test_check_names_rejects_unknown_name():
    code = compile("os.system('id')", '<string>', 'eval')
    with pytest.raises(NameError):
        _check_names(code, {})


def test_check_names_recurses_into_nested_code_objects():
    # The comprehension body `x.__class__` compiles into its own nested code
    # object; the disallowed name only shows up when _check_names recurses
    # into code.co_consts.
    code = compile("[x.__class__ for x in items]", '<string>', 'eval')
    with pytest.raises(NameError):
        _check_names(code, {'items': None})


# ---------------------------------------------------------------------------
# str_eval has two independent defense layers: _check_names rejects a
# disallowed name up front, and eval() itself runs with __builtins__
# stripped out. Each is verified on its own below.
# ---------------------------------------------------------------------------

def test_eval_builtins_stripped_independent_of_check_names(monkeypatch):
    # _check_names is the first defense layer. Disable it to prove the
    # second layer holds on its own: eval runs with __builtins__ stripped,
    # so a name _check_names missed still cannot resolve.
    monkeypatch.setattr("plexpy.notification_handler._check_names", lambda *a, **k: None)
    with pytest.raises(NameError):
        str_eval("open('/etc/passwd')", {})


@pytest.mark.parametrize("expr", [
    "`1+1`X",
    "X`1+1`",
])
def test_str_eval_rejects_malformed_backtick_wrapping(expr):
    # strip('`') only trims backticks off the outer ends of the string, so
    # text left outside a single matched pair of backticks is not valid
    # Python and fails to compile.
    with pytest.raises(SyntaxError):
        str_eval(expr, {})
