import pytest

from plexpy.helpers import (
    bool_true,
    cast_to_float,
    cast_to_int,
    eval_logic_groups_to_bool,
    get_percent,
    human_duration,
    human_file_size,
    parse_condition_logic_string,
    sanitize,
    version_to_tuple,
)
from plexpy.notification_handler import format_group_index


# ---------------------------------------------------------------------------
# human_duration
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("ms, expected", [
    (0, "0"),
    (None, "0"),
    ("", "0"),
    ("abc", "0"),
    (-5, "0"),
    (65000, "1 min 5 secs"),
    (3661000, "1 hr 1 min"),
    (90061000, "1 day 1 hr 1 min"),
    (400000000, "4 days 15 hrs 7 mins"),
    (1500, "2 secs"),
    (2 * 86400000, "2 days"),
    (2 * 3600000, "2 hrs"),
    (2 * 60000, "2 mins"),
])
def test_human_duration(ms, expected):
    assert human_duration(ms) == expected


def test_human_duration_sub_second_rounds_to_nothing():
    # 45ms is below the 1-second resolution of the default 'dhm' + return_seconds
    # fallback to 'dhms', so it rounds down to 0 and produces an empty string.
    assert human_duration(45) == ""


@pytest.mark.parametrize("sig, expected", [
    ("d", "1 day"),
    ("dh", "1 day 1 hr"),
    ("dhm", "1 day 1 hr 1 min"),
])
def test_human_duration_significance(sig, expected):
    assert human_duration(90061000, sig=sig) == expected


def test_human_duration_sig_dhms_rounds_up_to_one_second():
    assert human_duration(1001, sig='dhms') == "1 sec"


def test_human_duration_units_seconds():
    assert human_duration(65, units="s") == "1 min 5 secs"


# ---------------------------------------------------------------------------
# human_file_size
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("size, expected", [
    (0, "0.0 B"),
    (500, "500.0 B"),
    (1024, "1.00 kB"),
    (1048576, "1.00 MB"),
    (5 * 1024**3, "5.00 GB"),
    ("abc", "abc"),
    ("", ""),
    (None, None),
])
def test_human_file_size(size, expected):
    assert human_file_size(size) == expected


# ---------------------------------------------------------------------------
# get_percent
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("value1, value2, expected", [
    (50, 100, 50),
    (0, 100, 0),
    (100, 0, 0),
    (33, 100, 33),
    (1, 100, 1),
    (60, 100, 60),
    (2, 3, 67),
    ("a", "b", 0),
    (None, None, 0),
    ("", "", 0),
])
def test_get_percent(value1, value2, expected):
    assert get_percent(value1, value2) == expected


# ---------------------------------------------------------------------------
# cast_to_int / cast_to_float
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("value, expected", [
    ("5", 5),
    ("-5", -5),
    ("abc", 0),
    (None, 0),
    ("", 0),
    (5.7, 5),
    (5, 5),
])
def test_cast_to_int(value, expected):
    assert cast_to_int(value) == expected


@pytest.mark.parametrize("value, expected", [
    ("5.5", 5.5),
    ("-5.5", -5.5),
    ("abc", 0),
    (None, 0),
    ("", 0),
    (5, 5.0),
])
def test_cast_to_float(value, expected):
    assert cast_to_float(value) == expected


# ---------------------------------------------------------------------------
# bool_true
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("value", [
    True, 1, "1", "true", "True", "t", "T", "yes", "Yes", "y", "Y", "on", "On",
])
def test_bool_true_truthy(value):
    assert bool_true(value) is True


@pytest.mark.parametrize("value", [
    False, 0, "0", "false", "False", "f", "no", "n", "off", "", "abc", 2, None, [],
])
def test_bool_true_falsy(value):
    assert bool_true(value) is False


def test_bool_true_none_return_none():
    assert bool_true(None, return_none=True) is None


def test_bool_true_none_return_none_false_by_default():
    assert bool_true(None) is False


# ---------------------------------------------------------------------------
# version_to_tuple
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("version, expected", [
    ("v2.15.2", (2, 15, 2)),
    ("2.15.2", (2, 15, 2)),
    ("2.15.2-beta", (2, 15, 2, 0)),
    ("1.0", (1, 0)),
    ("1.32.5.7349-c6bb3c73d", (1, 32, 5, 7349, 0)),
])
def test_version_to_tuple(version, expected):
    assert version_to_tuple(version) == expected


def test_version_to_tuple_ordering_for_comparison():
    # version_to_tuple exists so two version strings can be compared as tuples.
    assert version_to_tuple("2.15.10") > version_to_tuple("2.15.2")
    assert version_to_tuple("2.15.2") == version_to_tuple("v2.15.2")


# ---------------------------------------------------------------------------
# sanitize
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("value, expected", [
    ("<script>alert(1)</script>", "&lt;script&gt;alert(1)&lt;/script&gt;"),
    ("plain text", "plain text"),
    ("", ""),
    ("a & b", "a & b"),  # ampersand is not escaped by sanitize
])
def test_sanitize_strings(value, expected):
    assert sanitize(value) == expected


def test_sanitize_list():
    assert sanitize(["<a>", ">b<"]) == ["&lt;a&gt;", "&gt;b&lt;"]


def test_sanitize_dict():
    assert sanitize({"k": "<v>"}) == {"k": "&lt;v&gt;"}


def test_sanitize_tuple():
    assert sanitize(("<a>", "<b>")) == ("&lt;a&gt;", "&lt;b&gt;")


def test_sanitize_nested():
    assert sanitize({"list": ["<a>", {"k": "<v>"}]}) == {"list": ["&lt;a&gt;", {"k": "&lt;v&gt;"}]}


@pytest.mark.parametrize("value", [5, None, True, 3.14])
def test_sanitize_passthrough_non_string(value):
    assert sanitize(value) == value


# ---------------------------------------------------------------------------
# parse_condition_logic_string
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("logic, num_cond, expected", [
    ("{1}", 1, [1]),
    ("{1} and {2}", 2, [[1, "and", 2]]),
    ("{1} or {2}", 2, [1, "or", 2]),
    ("{1} and ({2} or {3})", 3, [[1, "and", [2, "or", 3]]]),
    ("({1} and {2}) or {3}", 3, [[[1, "and", 2]], "or", 3]),
    ("{1} and {2} and {3}", 3, [[[1, "and", 2], "and", 3]]),
    ("{1} and {2} or {3}", 3, [[1, "and", 2], "or", 3]),
    ("", 0, []),
])
def test_parse_condition_logic_string_valid(logic, num_cond, expected):
    assert parse_condition_logic_string(logic, num_cond) == expected


@pytest.mark.parametrize("logic, num_cond, match", [
    ("{1} and", 1, "invalid condition logic"),        # dangling operator
    ("and {1}", 1, "invalid condition logic"),         # leading operator
    ("{1} {2}", 2, "invalid condition logic"),         # missing operator between conditions
    ("({1} and {2}", 2, "closing bracket is missing"), # unbalanced open paren
    ("{1} and {2})", 2, "opening bracket is missing"), # unbalanced close paren
    ("{0}", 1, "invalid condition number in condition logic"),  # condition number too low
    ("{2}", 1, "invalid condition number in condition logic"),  # condition number too high
    ("{1} xor {2}", 2, "invalid condition logic"),     # unsupported operator token
    ("()", 0, "invalid condition logic"),              # empty parens, no condition inside
])
def test_parse_condition_logic_string_malformed(logic, num_cond, match):
    with pytest.raises(ValueError, match=match):
        parse_condition_logic_string(logic, num_cond)


# ---------------------------------------------------------------------------
# eval_logic_groups_to_bool
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("logic, eval_conds, expected", [
    ("{1}", [None, True], True),
    ("{1}", [None, False], False),
    ("{1} and {2}", [None, True, True], True),
    ("{1} and {2}", [None, True, False], False),
    ("{1} or {2}", [None, False, True], True),
    ("{1} or {2}", [None, False, False], False),
    ("{1} and ({2} or {3})", [None, True, False, True], True),
    ("{1} and ({2} or {3})", [None, True, False, False], False),
    ("({1} and {2}) or {3}", [None, False, True, True], True),
    ("({1} and {2}) or {3}", [None, False, True, False], False),
    ("{1} and {2} and {3}", [None, True, True, False], False),
    ("{1} and {2} and {3}", [None, True, True, True], True),
    ("{1} and {2} or {3}", [None, False, True, True], True),
    ("{1} and {2} or {3}", [None, False, True, False], False),
    ("{1} or {2} or {3} or {4}", [None, False, False, False, True], True),
    ("{1} or {2} or {3} or {4}", [None, False, False, False, False], False),
    ("{1} and {2} and {3} and {4}", [None, True, True, True, True], True),
    ("{1} and {2} and {3} and {4}", [None, True, True, True, False], False),
])
def test_eval_logic_groups_to_bool(logic, eval_conds, expected):
    logic_groups = parse_condition_logic_string(logic, len(eval_conds) - 1)
    assert eval_logic_groups_to_bool(logic_groups, eval_conds) is expected


# ---------------------------------------------------------------------------
# format_group_index
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("group_keys, expected", [
    ([1, 2, 3], ("1-3", "01-03")),
    ([1, 3, 5], ("1,3,5", "01,03,05")),
    ([10], ("10", "10")),
    ([5, 3, 1, 2, 4], ("1-5", "01-05")),  # unsorted input is sorted first
    ([1, 2, 3, 7, 8, 10], ("1-3,7-8,10", "01-03,07-08,10")),  # runs + singleton
    ([], ("0", "00")),
])
def test_format_group_index(group_keys, expected):
    assert format_group_index(group_keys) == expected
