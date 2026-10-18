"""Recently Added newsletters count the added items for the template.

build_params counts movies, shows, seasons, episodes, artists, albums,
tracks and other videos. get_agent_class picks the agent class by id.
"""

import json

import pytest

from plexpy import helpers, newsletter_handler, newsletters


@pytest.fixture
def agent(app_db, monkeypatch):
    monkeypatch.setattr(helpers, "get_plexpy_url", lambda: "http://localhost:8181")
    agent = newsletters.RecentlyAdded(config={"incl_libraries": ["1"]})
    monkeypatch.setattr(agent, "_get_sections", lambda: [{"section_id": 1, "section_name": "Films"}])
    return agent


def test_build_params_counts_each_media_type(agent):
    agent.data = {"recently_added": {
        "movie": [{}, {}, {}, {}],
        "show": [
            {"season_count": 2, "season": [{"episode_count": 3}, {"episode_count": 4}]},
            {"season_count": 1, "season": [{"episode_count": 5}]},
        ],
        "artist": [
            {"album_count": 2, "album": [{"track_count": 10}, {"track_count": 8}]},
        ],
        "other_video": [{}, {}, {}, {}, {}],
    }}

    params = agent.build_params()

    assert params["movie_count"] == 4
    assert params["show_count"] == 2
    assert params["season_count"] == 3
    assert params["episode_count"] == 12
    assert params["artist_count"] == 1
    assert params["album_count"] == 2
    assert params["track_count"] == 18
    assert params["other_video_count"] == 5


def test_empty_result_has_no_data_after_build_params(agent, monkeypatch):
    # A library with no new items. retrieve_data builds the real result.
    monkeypatch.setattr(agent, "_get_sections", lambda: [
        {"section_id": 1, "section_name": "Films", "section_type": "movie", "agent": "tv.plex.agents.movie"}])
    monkeypatch.setattr(agent, "_get_recently_added", lambda media_type: [])
    agent.retrieve_data()

    params = agent.build_params()

    assert params["movie_count"] == 0
    assert params["track_count"] == 0
    # build_params reads empty keys into the defaultdict.
    assert agent._has_data() is False


@pytest.mark.parametrize("agent_id, expected", [
    (0, newsletters.RecentlyAdded),
    ("0", newsletters.RecentlyAdded),
    (7, newsletters.Newsletter),
    ("abc", None),
])
def test_get_agent_class_picks_class_by_id(app_db, agent_id, expected):
    result = newsletters.get_agent_class(agent_id=agent_id, email_config={"from_name": "Sender"})

    if expected is None:
        assert result is None
    else:
        assert type(result) is expected
        assert result.email_config["from_name"] == "Sender"


def test_notify_formats_the_subject_before_it_logs(app_db, app_config, tmp_path, monkeypatch):
    app_config.HTTP_HOST = "127.0.0.1"
    app_config.NEWSLETTER_DIR = str(tmp_path / "newsletters")
    newsletter_id = newsletters.add_newsletter_config(agent_id=0)
    app_db.action("UPDATE newsletters SET subject = ? WHERE id = ?", ["Weekly {movie_count}", newsletter_id])
    monkeypatch.setattr(newsletters.RecentlyAdded, "_get_sections", lambda self: [
        {"section_id": 1, "section_name": "Films", "section_type": "movie", "agent": "tv.plex.agents.movie"}])
    monkeypatch.setattr(newsletters.RecentlyAdded, "_get_recently_added", lambda self, media_type: [])
    monkeypatch.setattr(newsletters.RecentlyAdded, "send", lambda self: True)
    config = newsletters.get_newsletter_config(newsletter_id)["config"]
    config["incl_libraries"] = ["1"]
    app_db.action("UPDATE newsletters SET newsletter_config = ? WHERE id = ?",
                  [json.dumps(config), newsletter_id])

    assert newsletter_handler.notify(newsletter_id=newsletter_id, notify_action="test") is True

    row = app_db.select_single("SELECT subject_text, success FROM newsletter_log")
    assert row == {"subject_text": "Weekly 0", "success": 1}
