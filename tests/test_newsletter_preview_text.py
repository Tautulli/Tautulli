"""The newsletter preview uses the saved subject, body, message and IDs."""

from plexpy import newsletters, webserve


def test_preview_uses_the_saved_text(app_db, app_config, monkeypatch):
    app_config.HTTP_HOST = '127.0.0.1'
    monkeypatch.setattr(newsletters.RecentlyAdded, '_get_sections', lambda self: [])
    monkeypatch.setattr(newsletters, 'serve_template', lambda template_name, **kwargs: (
        f"{kwargs['subject']}|{kwargs['body']}|{kwargs['message']}", None))

    newsletter_id = newsletters.add_newsletter_config(agent_id=0)
    app_db.action("UPDATE newsletters SET id_name = 'weekly', subject = 'Saved subject', body = 'Saved body', "
                  "message = 'Saved message for {newsletter_id_name} {newsletter_id}' WHERE id = ?",
                  [newsletter_id])

    result = webserve.WebInterface().real_newsletter(newsletter_id=str(newsletter_id), preview='true')

    assert result == f'Saved subject|Saved body|Saved message for weekly {newsletter_id}'
