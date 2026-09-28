"""clear_user_login_token return value.

Every branch of Users().clear_user_login_token fell through to a shared
`return False`, so a successful token clear reported failure. The
logout_user_session API command trusts that value, so it answered
"Unable to logout user session." after it had cleared the token.
"""

from plexpy.users import Users
from plexpy import webserve


def insert_login(app_db, jwt_token, user_id=0, user="Local"):
    app_db.action(
        "INSERT INTO user_login (timestamp, user_id, user, user_group, success, jwt_token) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        [1700000000, user_id, user, "guest", 1, jwt_token],
    )
    return app_db.select_single(
        "SELECT id FROM user_login WHERE jwt_token = ?", [jwt_token]
    )["id"]


def token_for(app_db, row_id):
    return app_db.select_single(
        "SELECT jwt_token FROM user_login WHERE id = ?", [row_id]
    )["jwt_token"]


def test_logout_user_session_returns_success_and_clears_the_token(app_db):
    row_id = insert_login(app_db, "token-row")

    result = webserve.WebInterface().logout_user_session(row_ids=str(row_id))

    assert result == {'result': 'success', 'message': 'Users session logged out.'}
    assert token_for(app_db, row_id) is None


def test_clear_user_login_token_by_jwt_token_returns_true(app_db):
    row_id = insert_login(app_db, "token-jwt")

    assert Users().clear_user_login_token(jwt_token="token-jwt") is True
    assert token_for(app_db, row_id) is None


def test_clear_user_login_token_without_arguments_returns_false(app_db):
    assert Users().clear_user_login_token() is False
