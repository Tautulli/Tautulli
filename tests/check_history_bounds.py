#!/usr/bin/env python3
"""Check that bounding a history draw does not change what it returns.

get_datatables_history bounds a draw before it joins and groups, so a
page reads the rows it can return rather than the whole table. The bound
has to be invisible. Every draw shape must give the same response with
the bound on and with it off.

This runs each shape both ways and compares the responses. It builds its
own database covering the awkward cases, or takes one with --db.

    python3 tests/check_history_bounds.py
    python3 tests/check_history_bounds.py --db /path/to/tautulli.db --max 40

It exits non-zero when a shape mismatches.
"""

import argparse
import itertools
import json
import os
import sys
import tempfile
import threading
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def bootstrap(db_file, root):
    """Bring up enough of Tautulli to call the data factory."""
    sys.path.insert(0, os.path.join(root, 'lib'))
    sys.path.insert(0, root)

    import plexpy
    from plexpy import config, logger

    plexpy.CONFIG = config.Config(
        tempfile.NamedTemporaryFile(suffix='.ini', delete=False).name)
    plexpy.CONFIG.GROUP_HISTORY_TABLES = 1
    plexpy.CONFIG.HISTORY_TABLE_ACTIVITY = 1
    plexpy.DATA_DIR = os.path.dirname(os.path.abspath(db_file))
    plexpy.DB_FILE = os.path.abspath(db_file)
    plexpy.INIT_LOCK = threading.Lock()

    from plexpy import database
    database.FILENAME = os.path.basename(db_file)

    logger.initLogger(console=False, log_dir=False, verbose=False)

    # Both read the CherryPy request, which nothing serves here
    from plexpy import session
    session.get_session_user_id = lambda: None
    session.friendly_name_to_username = lambda rows: rows


def build_database(groups=120):
    """Fill a database with history the bound has to get right."""
    import plexpy
    plexpy.dbcheck()

    from plexpy import database
    db = database.MonitorDatabase()
    db.action("INSERT INTO users (user_id, username, friendly_name) "
              "VALUES (1, 'alice', 'Alice')")
    db.action("INSERT INTO users (user_id, username, friendly_name) "
              "VALUES (2, 'bob', '')")

    base = 1700000000
    row = 0

    for group in range(groups):
        size = (group % 3) + 1
        reference_id = row + 1

        for member in range(size):
            row += 1
            # Ties every 7th group on started, which the bound breaks by id
            started = base + group * 1000 + (0 if group % 7 == 0 else member)
            # Rows of one group on different players must aggregate whole
            player = 'Roku' if member == 0 else 'Chromecast'
            media_type = ('movie', 'episode', 'track')[group % 3]
            # A resumed play can switch decision, so a group's newest row
            # can fail a transcode filter while an older row passes it.
            transcode = 'transcode' if member == 0 else 'direct play'

            db.action(
                "INSERT INTO session_history (id, reference_id, started, stopped, "
                "rating_key, user_id, user, ip_address, paused_counter, player, product, "
                "platform, machine_id, location, secure, relayed, media_type, section_id, "
                "live, transcode_decision, view_offset) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                [row, reference_id, started, started + 500, 1000 + group,
                 (group % 2) + 1, ('alice', 'bob')[group % 2], '10.0.0.%d' % (group % 5),
                 10 * member, player, 'Plex', ('Roku', 'Android')[group % 2],
                 'mach%d' % group, 'lan', 1, 0, media_type, (group % 3) + 1,
                 1 if group % 11 == 0 else 0, transcode, 400])
            db.action(
                "INSERT INTO session_history_metadata (id, rating_key, parent_rating_key, "
                "grandparent_rating_key, title, full_title, year, duration, guid, live, "
                "media_type) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                [row, 1000 + group, 900 + group, 800 + group, 'Title %d' % group,
                 'Full Title %d' % group, 2000 + (group % 25), 1000,
                 'plex://item/%d' % group, 1 if group % 11 == 0 else 0, media_type])
            db.action(
                "INSERT INTO session_history_media_info (id, rating_key, transcode_decision) "
                "VALUES (?,?,?)", [row, 1000 + group, transcode])

    # Inserted without a group key, the way write_session_history does
    # it. The trigger has to give the row one before it lands.
    row += 1
    db.action(
        "INSERT INTO session_history (id, reference_id, started, stopped, rating_key, "
        "user_id, user, ip_address, paused_counter, player, product, platform, "
        "machine_id, location, secure, relayed, media_type, section_id, "
        "live, transcode_decision, view_offset) "
        "VALUES (?, NULL, ?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        [row, base + 500, base + 900, 9999, 1, 'alice', '10.0.0.9', 0, 'NullRef',
         'Plex', 'Roku', 'machnull', 'lan', 1, 0, 'movie', 1, 0, 'direct play', 400])
    db.action(
        "INSERT INTO session_history_metadata (id, rating_key, parent_rating_key, "
        "grandparent_rating_key, title, full_title, year, duration, guid, live, "
        "media_type) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        [row, 9999, 9998, 9997, 'Ungrouped', 'Ungrouped Title', 2001, 1000,
         'plex://item/9999', 0, 'movie'])
    db.action(
        "INSERT INTO session_history_media_info (id, rating_key, transcode_decision) "
        "VALUES (?,?,?)", [row, 9999, 'direct play'])

    check_reference_id(db, row)

    # write_session_history writes the tables one statement at a time, so
    # a stop between them leaves a row the draw's inner join drops. These
    # sit newest, where a bound reads them first.
    for offset, missing in enumerate(('metadata', 'media_info')):
        row += 1
        started = base + groups * 1000 + 5000 + offset
        db.action(
            "INSERT INTO session_history (id, reference_id, started, stopped, rating_key, "
            "user_id, user, ip_address, paused_counter, player, product, platform, "
            "machine_id, location, secure, relayed, media_type, section_id, "
            "live, transcode_decision, view_offset) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            [row, row, started, started + 500, 8000 + offset, 1, 'alice', '10.0.0.8', 0,
             'Orphan', 'Plex', 'Roku', 'machorphan', 'lan', 1, 0, 'movie', 1,
             0, 'direct play', 400])
        if missing != 'metadata':
            db.action(
                "INSERT INTO session_history_metadata (id, rating_key, parent_rating_key, "
                "grandparent_rating_key, title, full_title, year, duration, guid, live, "
                "media_type) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                [row, 8000 + offset, 7999, 7998, 'Orphan', 'Orphan Title', 2002, 1000,
                 'plex://item/8000', 0, 'movie'])
        if missing != 'media_info':
            db.action(
                "INSERT INTO session_history_media_info (id, rating_key, transcode_decision) "
                "VALUES (?,?,?)", [row, 8000 + offset, 'direct play'])

    return row


def check_reference_id(db, ungrouped_row):
    """Check that a history row cannot lose its group key."""
    import plexpy

    got = db.select_single(
        "SELECT reference_id FROM session_history WHERE id = ?", [ungrouped_row])
    assert got['reference_id'] == ungrouped_row, (
        'the insert trigger left reference_id as %r' % (got['reference_id'],))

    # And that dbcheck repairs a database already carrying one
    db.action("DROP TRIGGER session_history_reference_id")
    db.action("UPDATE session_history SET reference_id = NULL WHERE id = ?", [ungrouped_row])
    plexpy.dbcheck()
    got = db.select_single(
        "SELECT reference_id FROM session_history WHERE id = ?", [ungrouped_row])
    assert got['reference_id'] == ungrouped_row, (
        'dbcheck left reference_id as %r' % (got['reference_id'],))

    assert not db.select("SELECT id FROM session_history WHERE reference_id IS NULL"), \
        'a history row is still without its group key'
    print('reference_id: insert trigger and dbcheck repair both hold')


# Name, orderable, searchable. The history table's own column list.
COLUMNS = [('date', True, False), ('friendly_name', True, True),
           ('ip_address', True, True), ('platform', True, True),
           ('product', True, True), ('player', True, True),
           ('full_title', True, True), ('started', True, False),
           ('paused_counter', True, False), ('stopped', True, False),
           ('duration', True, False), ('watched_status', False, False)]

FILTERS = [
    ('no filter', []),
    ('user_id', [['session_history.user_id IN', ['1']]]),
    ('media type', [['media_type_live IN', ['movie']]]),
    ('media type live', [['media_type_live IN', ['live']]]),
    ('transcode', [['session_history.transcode_decision IN', ['transcode']]]),
    ('guid prefix', [['session_history_metadata.guid LIKE', ['plex://item/1%']]]),
    ('section_id', [['session_history.section_id IN', ['2']]]),
    ('media type and user', [['media_type_live IN', ['episode']],
                             ['session_history.user_id IN', ['2']]]),
    # started splits a group, so these take no page bound
    ('before a date', [['started <', 1700060000]]),
    ('after a date', [['started >', 1700060000]]),
    ('between dates', [['started >', 1700030000], ['started <', 1700090000]]),
    ('transcode and user', [['session_history.transcode_decision IN', ['transcode']],
                            ['session_history.user_id IN', ['1']]]),
]

# Chromecast sits only on a group's second row, so it catches a bound
# that drops the rest of the group
SEARCHES = ['', 'Chromecast', 'Full Title 1', 'alice', '10.0.0.2', 'no-such-row']

ORDERS = [('date', 'desc'), ('date', 'asc'), ('friendly_name', 'desc')]
PAGES = [(0, 25), (50, 25), (100, 25), (0, 100)]

# The bundled table marks these unsearchable, but the API forwards
# json_data verbatim. A bound covering fewer columns than the draw's
# search prunes groups the search would return, so these bound nothing.
CRAFTED_COLUMNS = [
    ('aggregate date', ['date', 'platform']),
    ('aggregate started', ['started', 'platform']),
    ('aggregate stopped', ['stopped', 'platform']),
    ('aggregate play_duration', ['play_duration', 'platform']),
    ('aggregate paused_counter', ['paused_counter', 'platform']),
    ('aggregate percent', ['percent_complete', 'platform']),
    ('aggregate group_count', ['group_count', 'platform']),
    ('aggregate group_ids', ['group_ids', 'platform']),
    ('column with no name', ['', 'platform']),
    ('column not in the draw', ['nosuchcolumn', 'platform']),
    ('null literal', ['state', 'platform']),
    ('every column at once', ['date', 'friendly_name', 'ip_address', 'platform',
                              'product', 'player', 'full_title', 'group_ids',
                              'media_type_live', 'guid', 'transcode_decision',
                              'user_thumb', 'duration', 'row_id', 'reference_id']),
]

CRAFTED_SEARCHES = ['Roku', 'Chromecast', 'NullRef', '1700', '1,2', '0', 'Title 1']


def build_draw(order_column, direction, start, length, search):
    names = [column[0] for column in COLUMNS]
    return {
        'draw': 1,
        'start': start,
        'length': length,
        'search': {'value': search, 'regex': False},
        'order': [{'column': names.index(order_column), 'dir': direction}],
        'columns': [{'data': name, 'orderable': orderable, 'searchable': searchable,
                     'search': {'value': '', 'regex': False}}
                    for name, orderable, searchable in COLUMNS],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', help='database to check, instead of a new one')
    parser.add_argument('--root', default=ROOT, help='Tautulli checkout to import')
    parser.add_argument('--max', type=int, help='stop after this many draw shapes')
    args = parser.parse_args()

    built = None
    if args.db:
        bootstrap(args.db, args.root)
        print('database: %s' % args.db)
    else:
        built = tempfile.NamedTemporaryFile(suffix='.db', delete=False).name
        os.unlink(built)
        bootstrap(built, args.root)
        print('database: %d history rows built in %s' % (build_database(), built))

    from plexpy import datafactory

    factory = datafactory.DataFactory()
    page_bound = datafactory.build_history_page_bound
    search_bound = datafactory.build_history_search_bound

    def run(draw, custom_where, grouping, bounded):
        if bounded:
            datafactory.build_history_page_bound = page_bound
            datafactory.build_history_search_bound = search_bound
        else:
            datafactory.build_history_page_bound = lambda *a, **k: []
            datafactory.build_history_search_bound = lambda *a, **k: []
        started = time.time()
        response = factory.get_datatables_history(
            kwargs={'json_data': json.dumps(draw)},
            custom_where=[list(where) for where in custom_where],
            grouping=grouping, include_activity=True)
        return time.time() - started, response

    shapes = list(itertools.product(FILTERS, SEARCHES, ORDERS, PAGES, [True, False]))
    if args.max:
        shapes = shapes[::max(1, len(shapes) // args.max)][:args.max]

    mismatched = 0
    unbounded_seconds = bounded_seconds = 0.0

    for (name, custom_where), search, (column, direction), (start, length), grouping in shapes:
        draw = build_draw(column, direction, start, length, search)
        label = ('%-20s search=%-14r %s/%s start=%d length=%d grouping=%d'
                 % (name, search, column, direction, start, length, grouping))

        seconds, unbounded = run(draw, custom_where, grouping, bounded=False)
        unbounded_seconds += seconds
        seconds, bounded = run(draw, custom_where, grouping, bounded=True)
        bounded_seconds += seconds

        if unbounded == bounded:
            continue

        mismatched += 1
        print('MISMATCH  %s' % label)
        for key in ('recordsFiltered', 'recordsTotal', 'filter_duration', 'total_duration'):
            if unbounded.get(key) != bounded.get(key):
                print('    %-16s unbounded=%r bounded=%r'
                      % (key, unbounded.get(key), bounded.get(key)))
        unbounded_ids = [row['row_id'] for row in unbounded['data']]
        bounded_ids = [row['row_id'] for row in bounded['data']]
        if unbounded_ids != bounded_ids:
            print('    row_ids unbounded=%s' % unbounded_ids[:10])
            print('    row_ids bounded  =%s' % bounded_ids[:10])
            continue
        for left, right in zip(unbounded['data'], bounded['data']):
            differing = {key: (left[key], right[key])
                         for key in left if left[key] != right[key]}
            if differing:
                print('    row %s differs: %s' % (left['row_id'], differing))
                break

    crafted = 0
    for label, names in CRAFTED_COLUMNS:
        for search in CRAFTED_SEARCHES:
            for grouping in (True, False):
                draw = {
                    'draw': 1, 'start': 0, 'length': 25,
                    'search': {'value': search, 'regex': False},
                    'order': [{'column': 0, 'dir': 'desc'}],
                    'columns': [{'data': name, 'orderable': True, 'searchable': True,
                                 'search': {'value': '', 'regex': False}}
                                for name in names],
                }
                crafted += 1
                _, unbounded = run(draw, [], grouping, bounded=False)
                _, bounded = run(draw, [], grouping, bounded=True)
                if unbounded == bounded:
                    continue
                mismatched += 1
                print('MISMATCH  crafted %-26s search=%-10r grouping=%d'
                      % (label, search, grouping))
                print('    unbounded filtered=%s rows=%s'
                      % (unbounded['recordsFiltered'],
                         [row['row_id'] for row in unbounded['data']][:10]))
                print('    bounded   filtered=%s rows=%s'
                      % (bounded['recordsFiltered'],
                         [row['row_id'] for row in bounded['data']][:10]))

    print('\n%d draw shapes checked, %d mismatched'
          % (len(shapes) + crafted, mismatched))
    print('unbounded %.2fs total, bounded %.2fs total'
          % (unbounded_seconds, bounded_seconds))

    if built and os.path.exists(built):
        os.unlink(built)

    return 1 if mismatched else 0


if __name__ == '__main__':
    sys.exit(main())
