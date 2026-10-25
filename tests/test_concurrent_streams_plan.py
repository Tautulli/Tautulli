"""The concurrent streams graph reads only the plays in its time range.

With ORDER BY started, SQLite walks the started index to skip a sort. It
then reads every play ever recorded and checks stopped on each one.
"""

from plexpy import database, graphs


def test_concurrent_streams_query_searches_the_stopped_index(app_db, monkeypatch):
    queries = []
    select = database.MonitorDatabase.select

    def record(self, query, args=None):
        queries.append(query)
        return select(self, query, args)

    monkeypatch.setattr(database.MonitorDatabase, "select", record)
    graphs.Graphs().get_total_concurrent_streams_per_stream_type(time_range=30)

    history_query = next(q for q in queries if "FROM session_history " in q)
    # The plan check alone depends on the SQLite version. Another version
    # may search the stopped index without the + on this empty table, and
    # still walk the started index on a real one.
    assert "ORDER BY +session_history.started" in history_query
    plan = [row["detail"] for row in app_db.select("EXPLAIN QUERY PLAN " + history_query)]

    assert any(detail.startswith("SEARCH session_history USING INDEX idx_session_history_stopped ")
               for detail in plan), plan
