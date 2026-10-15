"""Users.get_details names the missing user in both warnings."""

from plexpy import users


def test_missing_user_warnings_name_the_username(app_config, monkeypatch, caplog):
    monkeypatch.setattr(users, "refresh_users", lambda: None)
    monkeypatch.setattr(users.Users, "get_user_details", lambda self, **kwargs: None)

    with caplog.at_level("WARNING", logger="tautulli"):
        users.Users().get_details(user="someone")

    messages = [record.getMessage() for record in caplog.records]
    assert len(messages) == 2
    for message in messages:
        assert "Unable to retrieve user" in message
        assert "someone" in message


def test_missing_user_warnings_name_the_user_id(app_config, monkeypatch, caplog):
    monkeypatch.setattr(users, "refresh_users", lambda: None)
    monkeypatch.setattr(users.Users, "get_user_details", lambda self, **kwargs: None)

    with caplog.at_level("WARNING", logger="tautulli"):
        users.Users().get_details(user_id=5, user="someone")

    messages = [record.getMessage() for record in caplog.records]
    assert len(messages) == 2
    for message in messages:
        assert "Unable to retrieve user 5 from database" in message
