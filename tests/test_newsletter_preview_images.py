"""The newsletter preview hashes local images and uploads nothing.

Images go to the image hosting service only when the newsletter is sent.
"""

import pytest

from plexpy import newsletters, notification_handler, webserve

MOVIE = {'media_type': 'movie', 'rating_key': '10', 'title': 'Movie', 'thumb': '/thumb/10', 'art': '/art/10'}


@pytest.fixture
def imgur_newsletter(app_db, app_config, monkeypatch):
    app_config.HTTP_HOST = '127.0.0.1'
    app_config.NOTIFY_UPLOAD_POSTERS = 1
    uploads = []
    rendered = {}

    monkeypatch.setattr(newsletters.RecentlyAdded, '_get_sections',
                        lambda self: [{'section_id': 1, 'section_type': 'movie', 'section_name': 'Movies', 'agent': ''}])
    monkeypatch.setattr(newsletters.RecentlyAdded, '_get_recently_added', lambda self, media_type: [dict(MOVIE)])
    monkeypatch.setattr(notification_handler, 'get_img_info', lambda **kwargs: uploads.append(kwargs) or {})
    monkeypatch.setattr(notification_handler, 'set_hash_image_info', lambda **kwargs: 'hash')
    monkeypatch.setattr(newsletters, 'serve_template',
                        lambda template_name, **kwargs: (rendered.update(kwargs) or '', None))

    newsletter_id = newsletters.add_newsletter_config(agent_id=0)
    app_db.action("UPDATE newsletters SET newsletter_config = ? WHERE id = ?",
                  ['{"incl_libraries": ["1"]}', newsletter_id])

    return str(newsletter_id), uploads, rendered


def test_preview_does_not_upload_images(imgur_newsletter):
    newsletter_id, uploads, rendered = imgur_newsletter

    webserve.WebInterface().real_newsletter(newsletter_id=newsletter_id, preview='true')

    assert uploads == []
    assert rendered['preview'] is True
    assert rendered['data']['recently_added']['movie'][0]['thumb_hash'] == 'hash'


def test_full_newsletter_uploads_images(imgur_newsletter):
    newsletter_id, uploads, rendered = imgur_newsletter

    webserve.WebInterface().real_newsletter(newsletter_id=newsletter_id)

    assert uploads
    assert rendered['preview'] is False
