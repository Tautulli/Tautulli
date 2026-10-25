import pytest

from plexpy.notification_handler import str_format


def test_basic_substitution(app_config):
    assert str_format("{show_name} - {episode_name}", {"show_name": "Foo", "episode_name": "Bar"}) == "Foo - Bar"


def test_missing_key_is_literal(app_config):
    # A typo'd/unknown parameter name must not raise; it degrades to the literal {key}.
    assert str_format("{unknown_param}", {}) == "{unknown_param}"


@pytest.mark.parametrize("template, params, expected", [
    ("{video_codec!u}", {"video_codec": "hevc"}, "HEVC"),
    ("{content_rating!l}", {"content_rating": "TV-PG"}, "tv-pg"),
    ("{media_type!c}", {"media_type": "movie"}, "Movie"),
    ("{value!r}", {"value": "test"}, "'test'"),
    # !s combined with a width format spec: the conversion and the spec
    # both apply.
    ("{video_codec!s:10}", {"video_codec": 123}, "123       "),
])
def test_conversion_modifiers(app_config, template, params, expected):
    assert str_format(template, params) == expected


@pytest.mark.parametrize("template, expected", [
    ("{actors:[0]}", "Actor0"),
    ("{actors:[:4]}", "Actor0, Actor1, Actor2, Actor3"),
    ("{actors:[2:]}", "Actor2, Actor3, Actor4"),
    ("{actors:[1:5]}", "Actor1, Actor2, Actor3, Actor4"),
    # Trailing text after the closing ] makes the format_spec not match the
    # [...]  slicing pattern at all, so format_field falls through and
    # returns the value unchanged, slicing skipped.
    ("{actors:[0]extra}", "Actor0, Actor1, Actor2, Actor3, Actor4"),
])
def test_list_slicing(app_config, template, expected):
    actors = "Actor0, Actor1, Actor2, Actor3, Actor4"
    assert str_format(template, {"actors": actors}) == expected


def test_list_slicing_falsy_value_is_empty(app_config):
    # format_field's slicing branch only runs "if value and match"; a falsy
    # value (e.g. an unavailable param resolving to None) short-circuits it
    # and yields the empty field, not the literal text "None".
    assert str_format("{actors:[0:2]}", {"actors": None}) == ""


@pytest.mark.parametrize("template, expected", [
    ("{rating}", "8.9"),
    ("{Rating: <rating}", "Rating: 8.9"),
    ("{rating>/10}", "8.9/10"),
    ("{Rating: <rating>/10}", "Rating: 8.9/10"),
])
def test_prefix_suffix(app_config, template, expected):
    assert str_format(template, {"rating": "8.9"}) == expected


@pytest.mark.parametrize("template, expected", [
    # A literal backslash-n in the prefix/suffix text is the user-facing way
    # to put a line break in notification text; parse() turns it into a real
    # newline.
    (r"{Prefix\n <rating}", "Prefix\n 8.9"),
    (r"{rating>\n Suffix}", "8.9\n Suffix"),
])
def test_prefix_suffix_literal_newline(app_config, template, expected):
    assert str_format(template, {"rating": "8.9"}) == expected


@pytest.mark.parametrize("template, expected", [
    # When a notification parameter is available but empty, the field, its
    # prefix, and its suffix are all omitted from the output.
    ("{rating}", ""),
    ("Rating: {rating}/10", "Rating: /10"),
    ("{Rating: <rating>/10}", ""),
])
def test_prefix_suffix_with_unavailable_param(app_config, template, expected):
    assert str_format(template, {"rating": ""}) == expected


# ---------------------------------------------------------------------------
# Backtick eval fields, e.g. {`episode_num00 if season_num00 else 'N/A'`}.
# CustomFormatter.parse()/_vformat() only route a field through str_eval when
# NOTIFY_TEXT_EVAL is on, so each test below sets it explicitly.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("template, params, expected", [
    ("{`1 + 1`}", {}, "2"),
    ("{`episode_num00 if season_num00 else 'N/A'`}",
     {"episode_num00": "05", "season_num00": "01"}, "05"),
    ("{`episode_num00 if season_num00 else 'N/A'`}",
     {"episode_num00": "05", "season_num00": ""}, "N/A"),
])
def test_eval_field(app_config, template, params, expected):
    app_config.NOTIFY_TEXT_EVAL = 1
    assert str_format(template, params) == expected


@pytest.mark.parametrize("template, params, expected", [
    # A colon inside the eval expression must stay part of the expression,
    # not get parsed as a str.format() format-spec separator (regression 05a00e98).
    ("{`'a:b' if 1 else 'c'`}", {}, "a:b"),
    ("{`'a:b' if 0 else 'c'`}", {}, "c"),
    ("{`str(rating)[0:2]`}", {"rating": "8.9"}, "8."),
])
def test_eval_field_with_colon(app_config, template, params, expected):
    app_config.NOTIFY_TEXT_EVAL = 1
    assert str_format(template, params) == expected


@pytest.mark.parametrize("template, expected", [
    ("{Prefix <`1 + 1`> Suffix}", "Prefix 2 Suffix"),
    ("{Prefix <`1 + 1`>}", "Prefix 2"),
    ("{<`1 + 1`> Suffix}", "2 Suffix"),
    # An empty eval result suppresses the prefix and suffix too, same as a
    # plain param (regression 3510224c).
    ("{Prefix <`'' if True else 'x'`> Suffix}", ""),
    # A `<` inside the eval expression must stay part of the expression, not
    # get parsed as the prefix/suffix separator (it is protected by
    # eval_regex matching the whole backtick span before the < / > split).
    ("{Prefix <`1 < 2`> Suffix}", "Prefix True Suffix"),
    # A conversion placed after the closing `>` of a prefix/suffix field is
    # reconstructed into the suffix text along with the literal `!u`, not
    # applied to the eval result -- that is the field's parsed shape once a
    # prefix/suffix is present.
    ("{Prefix <`1 + 1`> Suffix!u}", "Prefix 2 Suffix!u"),
])
def test_eval_field_prefix_suffix(app_config, template, expected):
    app_config.NOTIFY_TEXT_EVAL = 1
    assert str_format(template, {}) == expected


@pytest.mark.parametrize("template, expected", [
    # An exclamation mark inside the eval expression must stay part of the
    # expression, not get parsed as a str.format() conversion (regression 9fddcf30).
    ("{`'it!s' + 'ok'`}", "it!sok"),
    # A real conversion placed after the closing backtick still applies.
    ("{`'a' if True else 'b'`!u}", "A"),
])
def test_eval_field_with_exclamation(app_config, template, expected):
    app_config.NOTIFY_TEXT_EVAL = 1
    assert str_format(template, {}) == expected


def test_eval_field_name_error_degrades_to_literal(app_config):
    # A disallowed name in the eval expression must not crash the whole
    # notification. _vformat catches the NameError from str_eval and falls
    # back to the field's own (backtick-wrapped) source text.
    app_config.NOTIFY_TEXT_EVAL = 1
    assert str_format("{`nonexistent_name`}", {}) == "`nonexistent_name`"


def test_bare_angle_brackets_resolve_to_value(app_config):
    # Empty prefix and suffix text still counts as a prefix/suffix field.
    # parse() must resolve it, not drop the whole field to literal text.
    assert str_format("{<rating>}", {"rating": "8.9"}) == "8.9"


def test_eval_field_disabled_by_notify_text_eval_off(app_config):
    # With NOTIFY_TEXT_EVAL off, a backtick field is never sent to str_eval.
    # It is then treated as an unknown parameter and echoed back literally,
    # same as test_missing_key_is_literal.
    app_config.NOTIFY_TEXT_EVAL = 0
    assert str_format("{`1 + 1`}", {}) == "{`1 + 1`}"


# ---------------------------------------------------------------------------
# Sentinel replacement around backtick eval fields. parse() swaps ':' and '!'
# inside a backtick expression for sentinels so str.format() does not read
# them as a format spec or a conversion, then swaps them back. The swap must
# find the field that holds the eval expression, and only that field.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("template, expected", [
    # Backticks in the literal text between two fields are markdown, not an
    # eval expression. A ':' or '!' inside them must reach the notification
    # unchanged, not as a leftover %%colon%% / %%exclamation%% sentinel.
    ("{title} `a: b` {duration}", "Foo `a: b` 3600"),
    ("{title} `a! b` {duration}", "Foo `a! b` 3600"),
])
def test_backticks_in_literal_text_keep_colons_and_exclamations(app_config, template, expected):
    app_config.NOTIFY_TEXT_EVAL = 1
    assert str_format(template, {"title": "Foo", "duration": "3600"}) == expected


def test_literal_backticks_do_not_shadow_a_later_eval_field(app_config):
    # Literal backticks earlier in the text must not take the place of the
    # real eval field. If they do, the field's ':' keeps its sentinel-free
    # form, str.format() reads it as a format spec, and the field is cut in
    # half.
    app_config.NOTIFY_TEXT_EVAL = 1
    assert str_format("{title} `a: b` {`'c:d'`}", {"title": "Foo"}) == "Foo `a: b` c:d"
