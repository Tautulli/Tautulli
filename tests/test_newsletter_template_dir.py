"""A custom template folder that is, or sits inside, the newsletter output folder is refused.

The saved newsletter would otherwise load as a template on the next send.
"""

import pytest

from plexpy import newsletters


@pytest.fixture
def dirs(app_db, app_config, tmp_path):
    out = tmp_path / "out"
    custom = tmp_path / "custom"
    out.mkdir()
    custom.mkdir()
    (custom / "marker.html").write_text("x")
    app_config.NEWSLETTER_DIR = str(out)
    return out, custom


def lookup_dir(monkeypatch, custom):
    seen = []

    class FakeLookup:
        def __init__(self, directories, **kwargs):
            seen.extend(directories)

        def get_template(self, name):
            raise RuntimeError("stop")

    monkeypatch.setattr(newsletters, "TemplateLookup", FakeLookup)
    plexpy_config = newsletters.plexpy.CONFIG
    plexpy_config.NEWSLETTER_CUSTOM_DIR = str(custom)
    newsletters.serve_template("recently_added.html")
    return seen[0]


def test_separate_folder_is_used(dirs, monkeypatch):
    _, custom = dirs

    assert lookup_dir(monkeypatch, custom) == str(custom)


def test_same_folder_is_refused(dirs, monkeypatch):
    out, _ = dirs

    assert lookup_dir(monkeypatch, out) != str(out)


def test_custom_inside_output_is_refused(dirs, monkeypatch):
    out, _ = dirs
    nested = out / "templates"
    nested.mkdir()

    assert lookup_dir(monkeypatch, nested) != str(nested)


def test_output_inside_custom_is_allowed(dirs, monkeypatch, app_config):
    out, custom = dirs
    inner = custom / "output"
    inner.mkdir()
    app_config.NEWSLETTER_DIR = str(inner)

    assert lookup_dir(monkeypatch, custom) == str(custom)


def test_empty_output_dir_uses_the_data_dir_default(dirs, monkeypatch, app_config, tmp_path):
    app_config.NEWSLETTER_DIR = ''
    default = tmp_path / "newsletters"
    default.mkdir()

    assert lookup_dir(monkeypatch, default) != str(default)
    assert lookup_dir(monkeypatch, tmp_path) == str(tmp_path)


def test_refusal_logs_an_error(dirs, monkeypatch):
    out, _ = dirs
    calls = []
    monkeypatch.setattr(newsletters.logger, "error", lambda *a, **k: calls.append(a))

    lookup_dir(monkeypatch, out)

    assert len(calls) == 1 and "overlaps" in calls[0][0]


def test_symlink_and_dotdot_are_refused(dirs, monkeypatch, tmp_path):
    out, _ = dirs
    link = tmp_path / "link"
    link.symlink_to(out)

    assert lookup_dir(monkeypatch, link) != str(link)
    dotdot = str(tmp_path / "custom" / ".." / "out")
    assert lookup_dir(monkeypatch, dotdot) != dotdot


def test_refusal_uses_builtin_templates(dirs, monkeypatch):
    out, _ = dirs

    selected_dir = lookup_dir(monkeypatch, out).replace("\\", "/")
    assert selected_dir.endswith("/data/interfaces/newsletters")
