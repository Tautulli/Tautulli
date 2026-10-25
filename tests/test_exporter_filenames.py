"""Export names stay inside the 255 byte file name limit (#2777).

A long album title made every name built from it too long, and the
export failed with Errno 36.
"""

from types import SimpleNamespace

import pytest

from plexpy import exporter, helpers

ALBUM = "The Boy Bands Have Won, and All the Copyists \u2019 " * 20


def item(type_, rating_key, title, sync_title):
    obj = SimpleNamespace(type=type_, ratingKey=rating_key, title=title, thumbUrl="http://pms/thumb", fields=[])
    obj._defaultSyncTitle = lambda: sync_title
    return obj


ARTIST = item("artist", 266473, "Chumbawamba", "Chumbawamba")
ALBUM_ITEM = item("album", 266527, ALBUM, "Chumbawamba - " + ALBUM)


class Response:
    status_code = 200

    def __iter__(self):
        return iter([b"image"])


@pytest.fixture
def export_dir(app_config, tmp_path, monkeypatch):
    app_config.EXPORT_DIR = str(tmp_path)
    monkeypatch.setattr(exporter.requests, "get", lambda *args, **kwargs: Response())
    return tmp_path


def make_export(media_type, obj_title, **kwargs):
    export = exporter.Export(thumb_level=9, file_format="json", **kwargs)
    export.media_type = media_type
    export.obj_title = obj_title
    export.directory = export._filename(directory=True)
    export.filename = export._filename()
    export.title = export._filename(extension=False)
    return export


def library_all():
    return exporter.ExportObject(make_export("library", "Music", section_id=2), ARTIST)


def library_albums():
    return exporter.ExportObject(make_export("library", "Music", section_id=2, export_type="albums"), ALBUM_ITEM)


def single_album():
    return make_export("album", ALBUM_ITEM._defaultSyncTitle(), rating_key=266527)


@pytest.mark.parametrize("make", [library_all, library_albums, single_album])
def test_long_title_resource_is_written(export_dir, make):
    make().get_resource(ALBUM_ITEM, "thumb")

    (path,) = export_dir.rglob("*.thumb.jpg")
    assert path.name.endswith(" [266527].thumb.jpg")
    assert all(len(part.encode()) <= 255 for part in path.relative_to(export_dir).parts)


@pytest.mark.parametrize("make", [library_albums, single_album])
def test_long_title_export_file_is_written(export_dir, make):
    export = make()
    export._save_file([{}], obj=export)

    (path,) = export_dir.rglob("*.json")
    assert path.name.endswith(" [266527].json")
    assert len(path.parent.name.encode()) <= 255


@pytest.mark.parametrize("kwargs", [{"user_id": 1}, {"section_id": 2}])
def test_long_user_and_library_names_fit(kwargs):
    assert len(make_export("library", ALBUM, **kwargs).directory.encode()) <= 255


def test_truncate_title_cuts_on_a_character_boundary():
    assert helpers.truncate_title("a" * 200) == "a" * 150
    assert helpers.truncate_title("a" + "\u00e9" * 100) == "a" + "\u00e9" * 74
    assert helpers.truncate_title("Short") == "Short"
    assert helpers.truncate_title(None) == "None"


def test_truncate_title_normalizes_before_the_cut():
    # NFC splits U+FB2C into three code points, which doubles its UTF-8 length
    assert len(helpers.clean_filename(helpers.truncate_title("\ufb2c" * 100)).encode()) <= 150


@pytest.mark.parametrize("filename, expected", [
    ('a/b\\c?d%e*f:g|h"i<j>k\x00l\x1fm\x7fn', "a_b_c_d_e_f_g_h_i_j_k_l_m_n"),
    (" .-_Title_-. ", "Title"),
    ("\u00e9t\u00e9 \u2019", "\u00e9t\u00e9 \u2019"),
    ("e\u0301", "\u00e9"),
    ("\ufb01 \uff21", "\ufb01 \uff21"),
    ("...", "untitled"),
])
def test_clean_filename(filename, expected):
    assert helpers.clean_filename(filename) == expected
