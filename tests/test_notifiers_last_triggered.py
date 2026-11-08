"""The notifier list reads each notifier's newest notify_log row.

A join with GROUP BY read every notify_log row. It took about 5 s for
875,205 rows, and the settings Notification Agents table waited for it.
"""

from plexpy import notifiers


def add_notifiers(db, count):
    for _ in range(count):
        db.action("INSERT INTO notifiers (agent_id, agent_name, agent_label, friendly_name) "
                  "VALUES (10, 'email', 'Email', '')")


def add_log(db, rows):
    db.connection.executemany(
        "INSERT INTO notify_log (notifier_id, timestamp, success) VALUES (?, ?, ?)", rows)


def last_triggered(**kwargs):
    return [(n["id"], n["last_triggered"], n["last_success"]) for n in notifiers.get_notifiers(**kwargs)]


def test_each_notifier_gets_its_newest_log_row(app_db):
    add_notifiers(app_db, 3)
    add_log(app_db, [
        (1, 100, 1), (1, 300, 0), (1, 200, 1),
        # Two rows in the same second. The row written last wins.
        (2, 500, 0), (2, 500, 1), (2, 400, 0),
    ])

    assert sorted(last_triggered()) == [(1, 300, 0), (2, 500, 1), (3, None, None)]
    assert last_triggered(notifier_id=2) == [(2, 500, 1)]


def test_tie_picks_the_row_written_last_when_sqlite_sorts(app_db):
    # The index scan returns tied rows newest first on its own.
    # Without the indexes SQLite sorts, and only id DESC breaks the tie.
    app_db.action("DROP INDEX idx_notify_log_notifier_id")
    app_db.action("DROP INDEX idx_notify_log_timestamp")
    add_notifiers(app_db, 1)
    add_log(app_db, [(1, 500, 0), (1, 500, 1)])

    assert last_triggered() == [(1, 500, 1)]


def test_query_work_stays_flat_as_the_log_grows(app_db):
    add_notifiers(app_db, 2)
    steps = 0

    def count():
        nonlocal steps
        steps += 1

    def run():
        nonlocal steps
        steps = 0
        app_db.connection.set_progress_handler(count, 1)
        try:
            notifiers.get_notifiers()
        finally:
            app_db.connection.set_progress_handler(None, 1)
        return steps

    add_log(app_db, [(1, 1, 1), (2, 1, 1)])
    few = run()
    add_log(app_db, [(n % 2 + 1, n, 1) for n in range(2, 4000)])

    # The join ran about 1000 times more steps here
    assert run() < few * 2
