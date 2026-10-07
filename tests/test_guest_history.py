"""Guest session restrictions on the history table (8c715c5a).

A logged-in guest could read any other user's full history. Two holes,
closed in the same commit:

- datafactory.get_datatables_history merged the session user id into a
  caller's user_id clause, so a guest asking for user_id=1 queried
  user_id IN ('1', '2'), the union of both users. The session clause is
  now appended on its own and ANDed with whatever the caller asked for.
- webserve.get_history had no allow_session_user guard, unlike its
  sibling endpoints, so /api/v2?cmd=get_history&user_id=<other>
  returned the other user's rows.

The guest is simulated by patching session.get_session_user_id, which
returns a string user_id only when the session user_group is guest.
Admin sessions return None (the app_db fixture default).
"""

import pytest

import plexpy.session
from plexpy import webserve

from tests.test_history_table import seed_history, call_history


@pytest.fixture
def guest_bob(app_db, monkeypatch):
    seed_history(app_db)
    monkeypatch.setattr(plexpy.session, "get_session_user_id", lambda: "2")
    return app_db


# ---------------------------------------------------------------------------
# datafactory.get_datatables_history: the session clause narrows, never
# widens. bob (user_id 2) owns rows 3 and 5; alice owns 1, 2, 4, 6.
# ---------------------------------------------------------------------------

def test_guest_sees_only_their_own_rows(guest_bob):
    result = call_history(grouping=False)

    assert {row["row_id"] for row in result["data"]} == {3, 5}
    assert result["recordsFiltered"] == 2


def test_guest_filter_for_another_user_returns_nothing(guest_bob):
    # The caller's clause and the session clause are separate ANDed
    # filters. The old merge turned this into user_id IN ('1', '2') and
    # returned every row of both users.
    result = call_history(grouping=False,
                          custom_where=[["session_history.user_id IN", ["1"]]])

    assert result["data"] == []
    assert result["recordsFiltered"] == 0


def test_guest_filter_for_their_own_id_still_works(guest_bob):
    # The two clauses agree, so ANDing them must not over-restrict.
    result = call_history(grouping=False,
                          custom_where=[["session_history.user_id IN", ["2"]]])

    assert {row["row_id"] for row in result["data"]} == {3, 5}


# ---------------------------------------------------------------------------
# webserve.get_history: the allow_session_user guard. Called directly;
# every decorator on it passes the call through.
# ---------------------------------------------------------------------------

def test_get_history_rejects_another_users_id(guest_bob):
    result = webserve.WebInterface().get_history(user_id="1", grouping=0,
                                                 include_activity=0)

    assert result["data"] == []
    assert result["recordsFiltered"] == 0
    assert result["recordsTotal"] == 0
    assert result["draw"] == 0
    assert result["filter_duration"] == "0"
    assert result["total_duration"] == "0"


def test_get_history_allows_the_session_users_own_id(guest_bob):
    result = webserve.WebInterface().get_history(user_id="2", grouping=0,
                                                 include_activity=0)

    assert {row["row_id"] for row in result["data"]} == {3, 5}


def test_get_history_admin_is_unaffected(app_db):
    seed_history(app_db)

    result = webserve.WebInterface().get_history(user_id="1", grouping=0,
                                                 include_activity=0)

    assert {row["row_id"] for row in result["data"]} == {1, 2, 4, 6}
