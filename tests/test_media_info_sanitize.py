"""Media info rows must not carry raw PMS markup into the browser.

The Media Info DataTable writes the row cells with $(td).html() and
get_library_media_info returned PMS titles and codec fields
untouched, so a media title that carries markup executes for an
administrator who opens the Media Info tab. The endpoint now applies
the same @sanitize_out() as its sibling DataTable endpoints, which
escapes < and > on every string in the response.
"""

import json

import plexpy.libraries
from plexpy import webserve

PAYLOAD = "MOVIE <img src=x onerror=\"fetch('/xss-tautulli02')\">"


def _assert_no_raw_markup(value):
    if isinstance(value, str):
        assert "<" not in value and ">" not in value
    elif isinstance(value, list):
        for item in value:
            _assert_no_raw_markup(item)
    elif isinstance(value, dict):
        for item in value.values():
            _assert_no_raw_markup(item)


def _json_data():
    return json.dumps({
        "search": {"value": "", "regex": False},
        "columns": [
            {"data": "sort_title", "orderable": True, "searchable": True},
            {"data": "container", "orderable": True, "searchable": True},
        ],
        "order": [{"column": 0, "dir": "asc"}],
        "start": 0,
        "length": 25,
        "draw": 1,
    })


def test_media_info_rows_are_escaped(monkeypatch):
    row = {
        "title": PAYLOAD,
        "sort_title": PAYLOAD,
        "container": "m3u8 <script>",
        "video_codec": "h264",
        "media_type": "movie",
        "rating_key": "1219",
    }

    def fake_media_info(self, **kwargs):
        return {"recordsTotal": 1, "recordsFiltered": 1,
                "data": [row], "draw": 1}

    monkeypatch.setattr(plexpy.libraries.Libraries,
                        "get_datatables_media_info", fake_media_info)

    result = webserve.WebInterface().get_library_media_info(
        section_id="1", json_data=_json_data())

    data = result["data"][0]
    assert data["title"] == PAYLOAD.replace("<", "&lt;").replace(">", "&gt;")
    assert data["container"] == "m3u8 &lt;script&gt;"
    assert data["video_codec"] == "h264"
    _assert_no_raw_markup(result)
