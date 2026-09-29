import json

import pytest

from plexpy.datafactory import DataFactory
from plexpy.users import Users


# Draw shape reduced from webserve.py's get_user_logins(): the dt_columns it
# builds when the caller sends no json_data.
LOGIN_COLUMNS = [
    ("timestamp", True, False),
    ("ip_address", True, True),
    ("host", True, True),
    ("os", True, True),
    ("browser", True, True),
]


def login_draw():
    return {
        "draw": 1,
        "start": 0,
        "length": 25,
        "search": {"value": "", "regex": False},
        "order": [{"column": 0, "dir": "desc"}],
        "columns": [
            {"data": name, "orderable": orderable, "searchable": searchable,
             "search": {"value": "", "regex": False}}
            for name, orderable, searchable in LOGIN_COLUMNS
        ],
    }


# The Plex "Local" user has user_id 0. Every guard below used to be a plain
# truthiness check, which reads 0 as "no user given" and falls through to the
# no-user branch.

@pytest.fixture
def local_user(app_db):
    # dbcheck seeds the Local user itself, so this only fills in the columns
    # the tests read.
    app_db.action("UPDATE users SET allow_guest = ?, user_token = ?, server_token = ? WHERE user_id = ?",
                  [1, "token0", "server0", 0])
    return app_db


def test_get_tokens_for_user_id_zero(local_user):
    assert Users().get_tokens(user_id=0) == {
        "allow_guest": 1,
        "user_token": "token0",
        "server_token": "server0",
    }


def test_get_tokens_without_a_user_id_returns_the_empty_default(local_user):
    assert Users().get_tokens() == {"allow_guest": 0, "user_token": "", "server_token": ""}


def test_undelete_user_id_zero(local_user):
    local_user.action("UPDATE users SET deleted_user = 1, keep_history = 0 WHERE user_id = ?", [0])

    assert Users().undelete(user_id=0) is True
    assert local_user.select_single(
        "SELECT deleted_user, keep_history FROM users WHERE user_id = ?", [0]
    ) == {"deleted_user": 0, "keep_history": 1}


def test_undelete_falls_through_to_username_for_a_non_numeric_user_id(local_user):
    # A user_id that is not a number takes neither the numeric branch nor a
    # lookup of its own, so the username is what restores the user.
    local_user.action("UPDATE users SET deleted_user = 1, keep_history = 0 WHERE user_id = ?", [0])

    assert Users().undelete(user_id="not-a-number", username="Local") is True
    assert local_user.select_single(
        "SELECT deleted_user FROM users WHERE user_id = ?", [0]
    ) == {"deleted_user": 0}


def test_datatables_user_login_filters_on_user_id_zero(local_user):
    local_user.action("INSERT INTO users (user_id, username) VALUES (?, ?)", [1, "someone"])
    for row_user_id, user in ((0, "Local"), (1, "someone")):
        local_user.action("INSERT INTO user_login (timestamp, user_id, user, user_group, success) "
                          "VALUES (?, ?, ?, ?, ?)", [1700000000, row_user_id, user, "guest", 1])

    result = Users().get_datatables_user_login(user_id=0, kwargs={"json_data": json.dumps(login_draw())})

    assert [row["user_id"] for row in result["data"]] == [0]
    assert result["recordsFiltered"] == 1


def test_datatables_user_login_without_a_user_id_returns_every_row(local_user):
    local_user.action("INSERT INTO users (user_id, username) VALUES (?, ?)", [1, "someone"])
    for row_user_id, user in ((0, "Local"), (1, "someone")):
        local_user.action("INSERT INTO user_login (timestamp, user_id, user, user_group, success) "
                          "VALUES (?, ?, ?, ?, ?)", [1700000000, row_user_id, user, "guest", 1])

    result = Users().get_datatables_user_login(kwargs={"json_data": json.dumps(login_draw())})

    assert sorted(row["user_id"] for row in result["data"]) == [0, 1]


# get_user_devices feeds the new device notification check: an empty list
# reads as "this user has no known devices", so every play by the Local user
# fired a new device notification.

def test_get_user_devices_for_user_id_zero(local_user):
    local_user.action("INSERT INTO session_history (user_id, machine_id) VALUES (?, ?)", [0, "machine-a"])
    local_user.action("INSERT INTO session_history (user_id, machine_id) VALUES (?, ?)", [1, "machine-b"])

    assert DataFactory().get_user_devices(user_id=0) == ["machine-a"]


def test_get_user_devices_includes_continued_sessions_for_user_id_zero(local_user):
    local_user.action("INSERT INTO session_history (user_id, machine_id) VALUES (?, ?)", [0, "machine-a"])
    local_user.action("INSERT INTO sessions_continued (user_id, machine_id) VALUES (?, ?)", [0, "machine-c"])

    assert sorted(DataFactory().get_user_devices(user_id=0, history_only=False)) == ["machine-a", "machine-c"]


@pytest.mark.parametrize("user_id", ["", None])
def test_get_user_devices_without_a_user_id_returns_nothing(local_user, user_id):
    local_user.action("INSERT INTO session_history (user_id, machine_id) VALUES (?, ?)", [0, "machine-a"])

    assert DataFactory().get_user_devices(user_id=user_id) == []
