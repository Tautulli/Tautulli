from xml.dom import minidom

import pytest

from plexpy import pmsconnect

# get_hub_recently_added gets the Plex type number, plus other_video for Videos.
HUB_TYPES = {('1', False): 'movie', ('2', False): 'show', ('8', False): 'artist', ('1', True): 'other_video'}
ADDED = {'movie': 4, 'show': 3, 'artist': 2, 'other_video': 1}


@pytest.fixture
def hub(app_config, monkeypatch):
    monkeypatch.setattr(pmsconnect.session, "get_session_user_id", lambda: None)

    def get_hub_recently_added(self, start, count, media_type, other_video, output_format):
        name = HUB_TYPES[(media_type, other_video)]
        return minidom.parseString('<MediaContainer size="1"><Video type="%s" title="%s" addedAt="%s"/></MediaContainer>'
                                   % (name, name, ADDED[name]))

    monkeypatch.setattr(pmsconnect.PmsConnect, "get_hub_recently_added", get_hub_recently_added)


def titles(media_type):
    result = pmsconnect.PmsConnect().get_recently_added_details(count='50', media_type=media_type)
    return sorted(item['title'] for item in result['recently_added'])


@pytest.mark.parametrize("media_type, expected", [
    ('movie', ['movie']),
    ('movie,show', ['movie', 'show']),
    ('show, other_video', ['other_video', 'show']),
    ('movie,bogus', ['movie']),
    ('', ['artist', 'movie', 'other_video', 'show']),
    ('all', ['artist', 'movie', 'other_video', 'show']),
])
def test_media_type_list_selects_hubs(hub, media_type, expected):
    assert titles(media_type) == expected


def test_media_type_list_merges_newest_first_then_cuts_to_count(hub):
    result = pmsconnect.PmsConnect().get_recently_added_details(count='2', media_type='artist,movie,show')
    assert [item['title'] for item in result['recently_added']] == ['movie', 'show']
