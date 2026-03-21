# -*- coding: utf-8 -*-

#  This file is part of Tautulli.
#
#  Tautulli is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  Tautulli is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with Tautulli.  If not, see <http://www.gnu.org/licenses/>.

"""Prometheus text-format metrics for the optional /metrics scrape endpoint.

Exposes aggregate statistics aligned with Tautulli graphs, history, libraries,
and common API summaries. Per-user / per-title / per-library-name series are
omitted to avoid Prometheus cardinality blowups; use the HTTP API for those.
"""

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Gauge,
    Info,
    generate_latest,
)

import plexpy
from plexpy import database
from plexpy import helpers
from plexpy import logger
from plexpy import pmsconnect

_REGISTRY = CollectorRegistry()

_BUILD_INFO = Info(
    'tautulli_build_info',
    'Tautulli version and runtime information',
    registry=_REGISTRY,
)

_PLEX_SERVER_UP = Gauge(
    'tautulli_plex_server_up',
    'Whether the Plex server is considered up (1=yes, 0=no or unknown)',
    registry=_REGISTRY,
)

_PLEX_REMOTE_ACCESS_UP = Gauge(
    'tautulli_plex_remote_access_up',
    'Whether Plex remote access appears up (1=yes, 0=no, unknown as 0)',
    registry=_REGISTRY,
)

_WEBSOCKET_CONNECTED = Gauge(
    'tautulli_websocket_connected',
    'Whether the Plex websocket connection is active (1=yes, 0=no)',
    registry=_REGISTRY,
)

_UPDATE_AVAILABLE = Gauge(
    'tautulli_update_available',
    'Whether a Tautulli update is available (1=yes, 0=no)',
    registry=_REGISTRY,
)

_ACTIVE_SESSIONS = Gauge(
    'tautulli_active_sessions',
    'Rows in the Tautulli active sessions table (mirrors DB activity cache)',
    registry=_REGISTRY,
)

_HISTORY_PLAYS = Gauge(
    'tautulli_history_plays_total',
    'Completed history plays by window and media category (see graphs logic)',
    ('window', 'media_category'),
    registry=_REGISTRY,
)

_HISTORY_WATCH_SECONDS = Gauge(
    'tautulli_history_watch_seconds_total',
    'Sum of watch time in seconds by window and media category',
    ('window', 'media_category'),
    registry=_REGISTRY,
)

_SESSION_HISTORY_ROWS = Gauge(
    'tautulli_session_history_rows',
    'Total rows in session_history',
    registry=_REGISTRY,
)

_LIBRARY_SECTIONS = Gauge(
    'tautulli_library_sections',
    'Library section count by Plex section_type (from library_sections)',
    ('section_type',),
    registry=_REGISTRY,
)

_LIBRARY_ITEMS = Gauge(
    'tautulli_library_items_reported',
    'Sum of Plex item counts field by section_type',
    ('section_type',),
    registry=_REGISTRY,
)

_USERS_TOTAL = Gauge(
    'tautulli_users_total',
    'Users rows in Tautulli DB (friends list cache)',
    registry=_REGISTRY,
)

_USERS_ACTIVE = Gauge(
    'tautulli_users_active',
    'Users with is_active=1',
    registry=_REGISTRY,
)

_TABLE_ROWS = Gauge(
    'tautulli_table_rows',
    'Row counts for auxiliary tables',
    ('table',),
    registry=_REGISTRY,
)

_NOTIFY_ENTRIES = Gauge(
    'tautulli_notify_log_entries',
    'Notification log rows in time window',
    ('window',),
    registry=_REGISTRY,
)

_DB_SESSION_TRANSCODE = Gauge(
    'tautulli_db_session_streams_by_decision',
    'Active cached streams by transcode_decision (Tautulli sessions table)',
    ('decision',),
    registry=_REGISTRY,
)

_DB_SESSION_BANDWIDTH = Gauge(
    'tautulli_db_session_bandwidth_bytes_sum',
    'Sum of bandwidth field for active cached sessions',
    registry=_REGISTRY,
)

_DB_SESSION_BUFFER_EVENTS = Gauge(
    'tautulli_db_session_buffer_events_sum',
    'Sum of buffer_count for active cached sessions',
    registry=_REGISTRY,
)

_PMS_STREAM_COUNT = Gauge(
    'tautulli_pms_stream_count',
    'Live streams reported by PMS get_current_activity (API parity)',
    registry=_REGISTRY,
)

_PMS_STREAMS_BY_DECISION = Gauge(
    'tautulli_pms_streams_by_decision',
    'Live streams by transcode_decision from PMS',
    ('decision',),
    registry=_REGISTRY,
)

_PMS_BANDWIDTH = Gauge(
    'tautulli_pms_stream_bandwidth',
    'Live stream bandwidth from PMS (bytes/s style aggregate)',
    ('scope',),
    registry=_REGISTRY,
)

_WINDOWS = (
    ('1d', 86400),
    ('7d', 86400 * 7),
    ('30d', 86400 * 30),
    ('all', None),
)

_MEDIA_KEYS = ('tv', 'movie', 'music', 'live', 'total')

_SECTION_TYPES_KNOWN = (
    'show', 'movie', 'artist', 'photo', 'mixed', 'live', 'home', 'other',
)

_NOTIFY_WINDOWS = (('1d', 86400), ('7d', 86400 * 7))

_TABLES_FOR_ROWS = (
    'recently_added',
    'mobile_devices',
    'notifiers',
    'exports',
    'sessions_continued',
    'newsletter_log',
    'user_login',
)

_PMS_DECISIONS = ('transcode', 'direct_stream', 'direct_play')

_HISTORY_SQL = """
SELECT
 SUM(CASE WHEN sh.media_type = 'episode' AND IFNULL(shm.live, 0) = 0
     THEN 1 ELSE 0 END) AS tv_plays,
 SUM(CASE WHEN sh.media_type = 'movie' AND IFNULL(shm.live, 0) = 0
     THEN 1 ELSE 0 END) AS movie_plays,
 SUM(CASE WHEN sh.media_type = 'track' AND IFNULL(shm.live, 0) = 0
     THEN 1 ELSE 0 END) AS music_plays,
 SUM(CASE WHEN IFNULL(shm.live, 0) = 1 THEN 1 ELSE 0 END) AS live_plays,
 SUM(CASE WHEN sh.media_type = 'episode' AND IFNULL(shm.live, 0) = 0
     AND sh.stopped > 0 THEN (sh.stopped - sh.started) -
     IFNULL(sh.paused_counter, 0) ELSE 0 END) AS tv_sec,
 SUM(CASE WHEN sh.media_type = 'movie' AND IFNULL(shm.live, 0) = 0
     AND sh.stopped > 0 THEN (sh.stopped - sh.started) -
     IFNULL(sh.paused_counter, 0) ELSE 0 END) AS movie_sec,
 SUM(CASE WHEN sh.media_type = 'track' AND IFNULL(shm.live, 0) = 0
     AND sh.stopped > 0 THEN (sh.stopped - sh.started) -
     IFNULL(sh.paused_counter, 0) ELSE 0 END) AS music_sec,
 SUM(CASE WHEN IFNULL(shm.live, 0) = 1 AND sh.stopped > 0
     THEN (sh.stopped - sh.started) -
     IFNULL(sh.paused_counter, 0) ELSE 0 END) AS live_sec
FROM session_history AS sh
LEFT JOIN session_history_metadata AS shm ON shm.id = sh.id
WHERE sh.stopped > 0 %s
"""


def _reset_history_labels():
    for w, _ in _WINDOWS:
        for m in _MEDIA_KEYS:
            _HISTORY_PLAYS.labels(window=w, media_category=m).set(0)
            _HISTORY_WATCH_SECONDS.labels(window=w, media_category=m).set(0)


def _reset_library_labels():
    for st in _SECTION_TYPES_KNOWN:
        _LIBRARY_SECTIONS.labels(section_type=st).set(0)
        _LIBRARY_ITEMS.labels(section_type=st).set(0)


def _reset_notify_labels():
    for w, _ in _NOTIFY_WINDOWS:
        _NOTIFY_ENTRIES.labels(window=w).set(0)


def _reset_db_transcode_labels():
    for d in _PMS_DECISIONS:
        _DB_SESSION_TRANSCODE.labels(decision=d).set(0)


def _reset_pms_labels():
    for d in _PMS_DECISIONS:
        _PMS_STREAMS_BY_DECISION.labels(decision=d).set(0)
    for scope in ('total', 'lan', 'wan'):
        _PMS_BANDWIDTH.labels(scope=scope).set(0)


def _reset_table_labels():
    for t in _TABLES_FOR_ROWS:
        _TABLE_ROWS.labels(table=t).set(0)


def _collect_history(db):
    now = helpers.timestamp()
    for window_label, delta in _WINDOWS:
        cond = ''
        if delta is not None:
            ts = now - delta
            cond = ' AND sh.stopped >= %d' % ts
        q = _HISTORY_SQL % cond
        rows = db.select(q)
        if not rows:
            continue
        r = rows[0]
        tv = int(r.get('tv_plays') or 0)
        movie = int(r.get('movie_plays') or 0)
        music = int(r.get('music_plays') or 0)
        live = int(r.get('live_plays') or 0)
        total = tv + movie + music + live
        _HISTORY_PLAYS.labels(window=window_label, media_category='tv').set(
            tv)
        _HISTORY_PLAYS.labels(window=window_label, media_category='movie').set(
            movie)
        _HISTORY_PLAYS.labels(window=window_label, media_category='music').set(
            music)
        _HISTORY_PLAYS.labels(window=window_label, media_category='live').set(
            live)
        _HISTORY_PLAYS.labels(window=window_label, media_category='total').set(
            total)

        tvs = int(r.get('tv_sec') or 0)
        mvs = int(r.get('movie_sec') or 0)
        mus = int(r.get('music_sec') or 0)
        lvs = int(r.get('live_sec') or 0)
        tot_sec = tvs + mvs + mus + lvs
        _HISTORY_WATCH_SECONDS.labels(
            window=window_label, media_category='tv').set(tvs)
        _HISTORY_WATCH_SECONDS.labels(
            window=window_label, media_category='movie').set(mvs)
        _HISTORY_WATCH_SECONDS.labels(
            window=window_label, media_category='music').set(mus)
        _HISTORY_WATCH_SECONDS.labels(
            window=window_label, media_category='live').set(lvs)
        _HISTORY_WATCH_SECONDS.labels(
            window=window_label, media_category='total').set(tot_sec)


def _normalize_section_type(raw):
    if not raw:
        return 'other'
    s = str(raw).strip().lower()
    if s in _SECTION_TYPES_KNOWN:
        return s
    return 'other'


def _collect_libraries(db):
    sid = plexpy.CONFIG.PMS_IDENTIFIER or ''
    q = (
        "SELECT section_type, COUNT(*) AS n, "
        "SUM(CASE WHEN count IS NOT NULL THEN count ELSE 0 END) AS items "
        "FROM library_sections "
        "WHERE deleted_section = 0 AND server_id = ? "
        "GROUP BY section_type"
    )
    rows = db.select(q, args=[sid])
    agg = {st: {'n': 0, 'items': 0} for st in _SECTION_TYPES_KNOWN}
    for row in rows or []:
        st = _normalize_section_type(row.get('section_type'))
        n = int(row.get('n') or 0)
        items = int(row.get('items') or 0)
        if st not in agg:
            st = 'other'
        agg[st]['n'] += n
        agg[st]['items'] += items
    for st in _SECTION_TYPES_KNOWN:
        _LIBRARY_SECTIONS.labels(section_type=st).set(agg[st]['n'])
        _LIBRARY_ITEMS.labels(section_type=st).set(agg[st]['items'])


def _collect_users(db):
    r = db.select_single('SELECT COUNT(*) AS n FROM users')
    if r:
        _USERS_TOTAL.set(int(r.get('n') or 0))
    r2 = db.select_single(
        'SELECT COUNT(*) AS n FROM users WHERE is_active = 1')
    if r2:
        _USERS_ACTIVE.set(int(r2.get('n') or 0))


def _collect_session_history_total(db):
    r = db.select_single('SELECT COUNT(*) AS n FROM session_history')
    if r:
        _SESSION_HISTORY_ROWS.set(int(r.get('n') or 0))


def _collect_aux_tables(db):
    for table in _TABLES_FOR_ROWS:
        try:
            r = db.select_single('SELECT COUNT(*) AS n FROM %s' % table)
            if r:
                _TABLE_ROWS.labels(table=table).set(int(r.get('n') or 0))
        except Exception as e:
            logger.debug(
                'Prometheus metrics :: could not count %s: %s', table, e)


def _collect_notify_windows(db):
    now = helpers.timestamp()
    for window_label, delta in _NOTIFY_WINDOWS:
        ts = now - delta
        r = db.select_single(
            'SELECT COUNT(*) AS n FROM notify_log WHERE timestamp >= ?',
            args=[ts],
        )
        if r:
            _NOTIFY_ENTRIES.labels(window=window_label).set(
                int(r.get('n') or 0))


def _collect_db_sessions_aggregate(db):
    q = (
        "SELECT "
        "SUM(CASE WHEN LOWER(IFNULL(transcode_decision,'')) = 'transcode' "
        "THEN 1 ELSE 0 END) AS tc, "
        "SUM(CASE WHEN LOWER(IFNULL(transcode_decision,'')) = 'copy' "
        "THEN 1 ELSE 0 END) AS ds, "
        "SUM(CASE WHEN transcode_decision IS NOT NULL "
        "AND TRIM(transcode_decision) != '' "
        "AND LOWER(transcode_decision) NOT IN ('transcode', 'copy') "
        "THEN 1 ELSE 0 END) AS dp, "
        "SUM(IFNULL(bandwidth, 0)) AS bw, "
        "SUM(IFNULL(buffer_count, 0)) AS buf "
        "FROM sessions"
    )
    rows = db.select(q)
    if not rows:
        return
    r = rows[0]
    _DB_SESSION_TRANSCODE.labels(decision='transcode').set(
        int(r.get('tc') or 0))
    _DB_SESSION_TRANSCODE.labels(decision='direct_stream').set(
        int(r.get('ds') or 0))
    _DB_SESSION_TRANSCODE.labels(decision='direct_play').set(
        int(r.get('dp') or 0))
    _DB_SESSION_BANDWIDTH.set(int(r.get('bw') or 0))
    _DB_SESSION_BUFFER_EVENTS.set(int(r.get('buf') or 0))


def _collect_pms_activity():
    _PMS_STREAM_COUNT.set(0)
    try:
        if not plexpy.CONFIG.PMS_TOKEN:
            return
        pms = pmsconnect.PmsConnect(token=plexpy.CONFIG.PMS_TOKEN)
        result = pms.get_current_activity()
        if not result or not isinstance(result, dict):
            return
        sess = result.get('sessions') or []
        _PMS_STREAM_COUNT.set(int(result.get('stream_count') or len(sess)))
        tc = ds = dp = 0
        total_bw = lan_bw = wan_bw = 0
        for s in sess:
            td = (s.get('transcode_decision') or '').lower()
            if td == 'transcode':
                tc += 1
            elif td == 'copy':
                ds += 1
            else:
                dp += 1
            bw = helpers.cast_to_int(s.get('bandwidth'))
            total_bw += bw
            if s.get('location') == 'lan':
                lan_bw += bw
            else:
                wan_bw += bw
        _PMS_STREAMS_BY_DECISION.labels(decision='transcode').set(tc)
        _PMS_STREAMS_BY_DECISION.labels(decision='direct_stream').set(ds)
        _PMS_STREAMS_BY_DECISION.labels(decision='direct_play').set(dp)
        _PMS_BANDWIDTH.labels(scope='total').set(total_bw)
        _PMS_BANDWIDTH.labels(scope='lan').set(lan_bw)
        _PMS_BANDWIDTH.labels(scope='wan').set(wan_bw)
    except Exception as e:
        logger.debug('Prometheus metrics :: PMS activity: %s', e)


def _active_session_count():
    """Return the number of rows in the active ``sessions`` table, or 0."""
    try:
        db = database.MonitorDatabase()
        rows = db.select('SELECT COUNT(*) AS n FROM sessions')
        if rows:
            return int(rows[0]['n'])
    except Exception as e:
        logger.debug('Prometheus metrics :: Could not count sessions: %s', e)
    return 0


def render_metrics():
    """Refresh gauges and return Prometheus/OpenMetrics exposition (bytes).

    Returns:
        bytes: OpenMetrics/Prometheus text for the response body; pair with
            ``metrics_content_type()`` for the ``Content-Type`` header.
    """
    tinfo = plexpy.get_tautulli_info()
    _BUILD_INFO.info({
        'version': str(tinfo.get('tautulli_version') or ''),
        'install_type': str(tinfo.get('tautulli_install_type') or ''),
        'python_version': str(tinfo.get('tautulli_python_version') or ''),
    })

    _PLEX_SERVER_UP.set(1 if plexpy.PLEX_SERVER_UP is True else 0)
    ra = plexpy.PLEX_REMOTE_ACCESS_UP
    _PLEX_REMOTE_ACCESS_UP.set(1 if ra is True else 0)

    _WEBSOCKET_CONNECTED.set(1 if plexpy.WS_CONNECTED else 0)

    ua = plexpy.UPDATE_AVAILABLE
    _UPDATE_AVAILABLE.set(1 if ua not in (None, False) else 0)

    _ACTIVE_SESSIONS.set(_active_session_count())

    _reset_history_labels()
    _reset_library_labels()
    _reset_notify_labels()
    _reset_db_transcode_labels()
    _reset_pms_labels()
    _reset_table_labels()

    try:
        db = database.MonitorDatabase()
        _collect_history(db)
        _collect_libraries(db)
        _collect_users(db)
        _collect_session_history_total(db)
        _collect_aux_tables(db)
        _collect_notify_windows(db)
        _collect_db_sessions_aggregate(db)
    except Exception as e:
        logger.debug('Prometheus metrics :: DB aggregate error: %s', e)

    _collect_pms_activity()

    return generate_latest(_REGISTRY)


def metrics_content_type():
    """Return the Content-Type header string for Prometheus scrape responses."""
    return CONTENT_TYPE_LATEST
