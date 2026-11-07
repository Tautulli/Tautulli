"""PMS playlist titles must not reach the browser as raw markup.

The Playlists DataTable writes the title cell with $(td).html() and
get_playlists_list returned the PMS playlist title untouched, so a
title that carries markup executes for any logged-in user who opens
the Playlists tab. The endpoint now applies the same @sanitize_out()
as its sibling DataTable endpoints, which escapes < and > on every
string in the response.
"""

import json

import plexpy.libraries
from plexpy import webserve

PAYLOAD = "PLTITLE <img src=x onerror=\"fetch('/xss-tautulli01')\">"


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
            {"data": "title", "orderable": True, "searchable": True},
            {"data": "leafCount", "orderable": True, "searchable": True},
            {"data": "duration", "orderable": True, "searchable": True},
        ],
        "order": [{"column": 0, "dir": "asc"}],
        "start": 0,
        "length": 25,
        "draw": 1,
    })


def test_playlist_titles_are_escaped(monkeypatch):
    rows = [
        {"title": PAYLOAD, "leafCount": 1, "duration": 3600},
        {"title": "Clean list", "leafCount": 2, "duration": 7200},
    ]
    monkeypatch.setattr(plexpy.libraries, "get_playlists", lambda **kw: rows)

    result = webserve.WebInterface().get_playlists_list(
        section_id="1", json_data=_json_data())

    titles = {row["title"] for row in result["data"]}
    assert PAYLOAD.replace("<", "&lt;").replace(">", "&gt;") in titles
    assert "Clean list" in titles
    _assert_no_raw_markup(result)
