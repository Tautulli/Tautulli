"""Dolby Vision profile and level are blank when the stream has none.

get_metadata_details and get_session_each read DOVIProfile and DOVILevel
from the video stream. A missing or zero value gives an empty string. A
present value gives an int. A session with no video stream gives an empty
string.
"""

from xml.dom import minidom

import pytest

from plexpy import pmsconnect

XML = ('<MediaContainer size="1"><Video ratingKey="1" type="movie" title="A Movie">'
       '<Media><Part><Stream streamType="1" codec="hevc" %s/></Part></Media>'
       '</Video></MediaContainer>')


def video_stream(monkeypatch, attributes):
    monkeypatch.setattr(pmsconnect.session, "get_session_user_id", lambda: None)
    metadata = pmsconnect.PmsConnect().get_metadata_details(
        rating_key="1", metadata_xml=minidom.parseString(XML % attributes))
    return metadata["media_info"][0]["parts"][0]["streams"][0]


@pytest.mark.parametrize("attributes, profile, level", [
    ('DOVIPresent="1" DOVIProfile="8" DOVILevel="6"', 8, 6),
    ('DOVIPresent="1" DOVIProfile="5"', 5, ""),
    ('', "", ""),
])
def test_dovi_profile_and_level(app_config, monkeypatch, attributes, profile, level):
    stream = video_stream(monkeypatch, attributes)

    assert stream["video_dovi_profile"] == profile
    assert stream["video_dovi_level"] == level


SESSION = ('<Video ratingKey="1" sessionKey="1" type="movie" title="A"><Media><Part>%s</Part></Media>'
           '<User id="2" title="u"/><Player address="1.1.1.1" state="playing"/></Video>')


def session_stream(monkeypatch, streams):
    monkeypatch.setattr(pmsconnect.session, "get_session_user_id", lambda: None)
    monkeypatch.setattr(pmsconnect.users.Users, "get_details", lambda self, **kw: {
        "user_id": 2, "username": "u", "friendly_name": "u", "user_thumb": "", "email": "",
        "is_active": 1, "is_admin": 0, "is_home_user": 0, "is_allow_sync": 0, "is_restricted": 0,
        "do_notify": 0, "keep_history": 1, "deleted_user": 0, "allow_guest": 0, "shared_libraries": []})
    monkeypatch.setattr(pmsconnect.PmsConnect, "get_metadata_details", lambda self, **kw: {})
    doc = minidom.parseString(SESSION % streams).documentElement
    return pmsconnect.PmsConnect().get_session_each(session=doc)


@pytest.mark.parametrize("streams, profile, level", [
    ('<Stream streamType="1" codec="hevc" selected="1" DOVIPresent="1" DOVIProfile="8" DOVILevel="6"/>', 8, 6),
    ('<Stream streamType="1" codec="hevc" selected="1"/>', "", ""),
    ('<Stream streamType="2" selected="1"/>', "", ""),
])
def test_session_dovi_profile_and_level(app_config, monkeypatch, streams, profile, level):
    result = session_stream(monkeypatch, streams)

    assert result["stream_video_dovi_profile"] == profile
    assert result["stream_video_dovi_level"] == level
