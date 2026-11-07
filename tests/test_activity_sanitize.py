"""Session fields must not reach the browser as raw markup.

The dashboard update tick builds the subtitle decision from the PMS
subtitle language and writes it with .html(). get_activity returned
the session fields raw, so a session whose subtitle language carries
markup executes for anyone who has the dashboard open. The endpoint
now applies the same @sanitize_out() as its sibling endpoints, which
escapes < and > on every string in the response.
"""

from plexpy import webserve

PAYLOAD = "<img src=x onerror=\"fetch('/xss-tautulli03')\">"


def _assert_no_raw_markup(value):
    if isinstance(value, str):
        assert "<" not in value and ">" not in value
    elif isinstance(value, list):
        for item in value:
            _assert_no_raw_markup(item)
    elif isinstance(value, dict):
        for item in value.values():
            _assert_no_raw_markup(item)


def test_activity_sessions_are_escaped(monkeypatch):
    session = {
        "session_key": 1,
        "transcode_decision": "direct play",
        "bandwidth": "100",
        "location": "lan",
        "title": "Movie <script>alert(1)</script>",
        "subtitle_language": PAYLOAD,
    }

    def fake_cached():
        return {"sessions": [session]}

    monkeypatch.setattr(webserve, "get_current_activity_cached",
                        fake_cached)

    result = webserve.WebInterface().get_activity()

    data = result["sessions"][0]
    assert data["subtitle_language"] == PAYLOAD.replace("<", "&lt;").replace(">", "&gt;")
    assert data["title"] == "Movie &lt;script&gt;alert(1)&lt;/script&gt;"
    _assert_no_raw_markup(result)
