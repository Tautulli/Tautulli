# This file is part of Tautulli.
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

import sqlite3
from xml.dom import minidom
import os
import plexpy
import database
import libraries
import logger
import json
import servers


def validate_database(database=None):

    try:
        if not os.path.isfile(database):
            logger.error(u"Tautulli Importer :: File Not Found.")
            return 'File Not Found'
        connection = sqlite3.connect(database, timeout=20)
    except sqlite3.OperationalError:
        logger.error(u"Tautulli Importer :: Invalid database specified.")
        return 'Invalid database specified.'
    except ValueError:
        logger.error(u"Tautulli Importer :: Invalid database specified.")
        return 'Invalid database specified.'
    except:
        logger.error(u"Tautulli Importer :: Uncaught exception.")
        return 'Uncaught exception.'

    try:
        connection.execute('SELECT id from servers')
        connection.close()
    except sqlite3.OperationalError as e:
        if e.message == 'no such table: servers':
            logger.error(u"Tautulli Importer :: This database is not a V3.0.00 or higher database.")
            return 'This database is not a V3.0.00 or higher database.'
        else:
            logger.error(u"Tautulli Importer :: %s" % e)
            return e
    except:
        logger.error(u"Tautulli Importer :: Uncaught exception.")
        return 'Uncaught exception.'

    return 'success'


def import_from_tautulli(import_database=None, import_ignore_interval=0):

    try:
        import_db = sqlite3.connect(import_database, timeout=20)
        import_db.row_factory = database.dict_factory
        monitor_db = database.MonitorDatabase()
    except sqlite3.OperationalError:
        logger.error(u"Tautulli Importer :: Invalid filename.")
        return None
    except ValueError:
        logger.error(u"Tautulli Importer :: Invalid filename.")
        return None

    logger.info(u"Tautulli Importer :: Data import from %s in progress..." % import_database)

    try:
        servers_list = import_db.execute('SELECT * FROM servers').fetchall()
        for server in servers_list:
            new_server = False
            old_server_id = server.pop('id')
            logger.info(u"Tautulli Importer :: Importing Server: %s(%s)" % (server['pms_name'], old_server_id))
            query = 'SELECT id FROM servers WHERE pms_identifier = "%s"' % server['pms_identifier']
            existing_server_result = monitor_db.select_single(query)
            if not existing_server_result:
                server['pms_is_enabled'] = 0
                query = (
                    "INSERT INTO servers (" + ", ".join(server.keys()) + ")" +
                    " VALUES (" + ", ".join(["?"] * len(server.keys())) + ")"
                )
                monitor_db.action(query, server.values())
                new_server_id = monitor_db.last_insert_id()
                server['id'] = new_server_id
                new_server = True
            else:
                new_server_id = existing_server_result['id']

            import_library_sections(import_db, monitor_db, old_server_id, new_server_id)
            import_themoviedb_lookup(import_db, monitor_db, old_server_id, new_server_id)
            import_tvmaze_lookup(import_db, monitor_db, old_server_id, new_server_id)
            import_recently_added(import_db, monitor_db, old_server_id, new_server_id)
            import_session_history(import_db, monitor_db, old_server_id, new_server_id, import_ignore_interval)
            if new_server:
                servers.plexServer(server)

        notifier_lookup = import_notifiers(import_db, monitor_db)
        import_newsletters(import_db, monitor_db, notifier_lookup)

        logger.info(u"Tautulli Importer :: Tautulli data import complete successfully.")
        import_db.close()
        plexpy.PMS_SERVERS.refresh()

    except sqlite3.IntegrityError:
        logger.error(u"Tautulli Import_Tautulli :: Queries failed: %s", query)

    except Exception as e:
        logger.error(u"Tautulli Importer :: Failed to import tautulli database: %s" % e)


def import_session_history(import_db, monitor_db, old_server_id, new_server_id, import_ignore_interval):
    logger.info(u"Tautulli Importer :: Importing session_history table for ServerID: %s" % old_server_id)

    import_ignore_interval = (int(import_ignore_interval) if import_ignore_interval.isdigit() else 0)

    try:
        session_history_lookup = {}
        query = 'SELECT * FROM session_history WHERE server_id = %s' % old_server_id
        session_history_result = import_db.execute(query).fetchall()
        for session_history in session_history_result:
            old_session_history_id = session_history.pop('id')
            query = 'select sum(stopped - started) as play_time from session_history WHERE reference_id = %s' % old_session_history_id
            result = import_db.execute(query).fetchone()
            if result['play_time'] >= import_ignore_interval:
                session_history['server_id'] = new_server_id
                key_dict = {}
                key_dict['started'] = session_history.pop('started')
                key_dict['server_id'] = session_history.pop('server_id')
                key_dict['rating_key'] = session_history.pop('rating_key')
                key_dict['user_id'] = session_history.pop('user_id')
                result = monitor_db.upsert('session_history', key_dict=key_dict, value_dict=session_history)
                if result == 'insert':
                    new_session_history_id = monitor_db.last_insert_id()
                    session_history_lookup[old_session_history_id] = new_session_history_id

        query = 'SELECT id, reference_id FROM session_history WHERE server_id = %s' % new_server_id
        session_history_result = monitor_db.select(query)
        for session_history in session_history_result:
            key_dict = {'id': session_history.pop('id')}
            if session_history['reference_id'] in session_history_lookup:
                session_history['reference_id'] = session_history_lookup[session_history['reference_id']]
                result = monitor_db.upsert('session_history', key_dict=key_dict, value_dict=session_history)

        import_session_history_media_info(import_db, monitor_db, old_server_id, new_server_id, session_history_lookup)
        import_session_history_metadata(import_db, monitor_db, old_server_id, new_server_id, session_history_lookup)

        logger.info(u"Tautulli Importer :: session_history imported.")

    except sqlite3.IntegrityError:
        logger.error(u"Tautulli Import_Tautulli :: Queries failed: %s", query)

    except Exception as e:
        raise Exception('Session History Import failed: %s' % e)


def import_session_history_media_info(import_db, monitor_db, old_server_id, new_server_id, session_history_lookup):
    logger.info(u"Tautulli Importer :: Importing session_history_media_info table for ServerID: %s" % old_server_id)

    try:
        query = 'SELECT * FROM session_history_media_info WHERE server_id = %s' % old_server_id
        session_history_media_info_result = import_db.execute(query).fetchall()
        for session_history_media_info in session_history_media_info_result:
            if session_history_media_info['id'] in session_history_lookup:
                session_history_media_info['id'] = session_history_lookup[session_history_media_info['id']]
                session_history_media_info['server_id'] = new_server_id
                query = (
                    "INSERT INTO session_history_media_info (" + ", ".join(session_history_media_info.keys()) + ")" +
                    " VALUES (" + ", ".join(["?"] * len(session_history_media_info.keys())) + ")"
                )
                monitor_db.action(query, session_history_media_info.values())

        logger.info(u"Tautulli Importer :: session_history_media_info imported.")

    except sqlite3.IntegrityError:
        logger.error(u"Tautulli Import_Tautulli :: Queries failed: %s", query)

    except Exception as e:
        raise Exception('Session History Media Info Import failed: %s' % e)


def import_session_history_metadata(import_db, monitor_db, old_server_id, new_server_id, session_history_lookup):
    logger.info(u"Tautulli Importer :: Importing session_history_metadata table for ServerID: %s" % old_server_id)

    try:
        query = 'SELECT * FROM session_history_metadata WHERE server_id = %s' % old_server_id
        session_history_metadata_result = import_db.execute(query).fetchall()
        for session_history_metadata in session_history_metadata_result:
            if session_history_metadata['id'] in session_history_lookup:
                session_history_metadata['id'] = session_history_lookup[session_history_metadata['id']]
                session_history_metadata['server_id'] = new_server_id
                session_history_metadata['library_id'] = plexpy.libraries.get_section_index(new_server_id, session_history_metadata['section_id'])
                query = (
                    "INSERT INTO session_history_metadata (" + ", ".join(session_history_metadata.keys()) + ")" +
                    " VALUES (" + ", ".join(["?"] * len(session_history_metadata.keys())) + ")"
                )
                monitor_db.action(query, session_history_metadata.values())

        logger.info(u"Tautulli Importer :: session_history_metadata imported.")

    except sqlite3.IntegrityError:
        logger.error(u"Tautulli Import_Tautulli :: Queries failed: %s", query)

    except Exception as e:
        raise Exception('Session History Metadata Import failed: %s' % e)


def import_library_sections(import_db, monitor_db, old_server_id, new_server_id):
    logger.info(u"Tautulli Importer :: Importing library_sections table for ServerID: %s" % old_server_id)

    try:
        query = 'SELECT * FROM library_sections WHERE server_id = %s' % old_server_id
        library_sections = import_db.execute(query).fetchall()
        for library_section in library_sections:
            old_library_section_id = library_section.pop('id')
            library_section['server_id'] = new_server_id
            key_dict = {}
            key_dict['server_id'] = library_section.pop('server_id')
            key_dict['section_id'] = library_section.pop('section_id')
            result = monitor_db.upsert('library_sections', key_dict=key_dict, value_dict=library_section)

        logger.info(u"Tautulli Importer :: library_sections imported.")

    except sqlite3.IntegrityError:
        logger.error(u"Tautulli Import_Tautulli :: Queries failed: %s", query)

    except Exception as e:
        raise Exception('Library Sections Import failed: %s' % e)


def import_recently_added(import_db, monitor_db, old_server_id, new_server_id):
    logger.info(u"Tautulli Importer :: Importing recently_added table for ServerID: %s" % old_server_id)

    try:
        query = 'SELECT * FROM recently_added WHERE server_id = %s' % old_server_id
        recently_added_result = import_db.execute(query).fetchall()
        for recently_added in recently_added_result:
            old_recently_added_id = recently_added.pop('id')
            recently_added['server_id'] = new_server_id
            key_dict = {}
            key_dict['server_id'] = recently_added.pop('server_id')
            key_dict['rating_key'] = recently_added.pop('rating_key')
            key_dict['added_at'] = recently_added.pop('added_at')
            result = monitor_db.upsert('recently_added', key_dict=key_dict, value_dict=recently_added)

        logger.info(u"Tautulli Importer :: recently_added imported.")

    except sqlite3.IntegrityError:
        logger.error(u"Tautulli Import_Tautulli :: Queries failed: %s", query)

    except Exception as e:
        raise Exception('Recently Added Import failed: %s' % e)


def import_themoviedb_lookup(import_db, monitor_db, old_server_id, new_server_id):
    logger.info(u"Tautulli Importer :: Importing recently_added_lookup table for ServerID: %s" % old_server_id)

    try:
        query = 'SELECT * FROM themoviedb_lookup WHERE server_id = %s' % old_server_id
        themoviedb_lookup_result = import_db.execute(query).fetchall()
        for themoviedb_lookup in themoviedb_lookup_result:
            old_themoviedb_lookup_id = themoviedb_lookup.pop('id')
            themoviedb_lookup['server_id'] = new_server_id
            key_dict = {}
            key_dict['server_id'] = themoviedb_lookup.pop('server_id')
            key_dict['rating_key'] = themoviedb_lookup.pop('rating_key')
            result = monitor_db.upsert('themoviedb_lookup', key_dict=key_dict, value_dict=themoviedb_lookup)

        logger.info(u"Tautulli Importer :: themoviedb_lookup imported.")

    except sqlite3.IntegrityError:
        logger.error(u"Tautulli Import_Tautulli :: Queries failed: %s", query)

    except Exception as e:
        raise Exception('TheMovieDB Lookup Import failed: %s' % e)


def import_tvmaze_lookup(import_db, monitor_db, old_server_id, new_server_id):
    logger.info(u"Tautulli Importer :: Importing tvmaze_lookup table for ServerID: %s" % old_server_id)

    try:
        query = 'SELECT * FROM tvmaze_lookup WHERE server_id = %s' % old_server_id
        tvmaze_lookup_result = import_db.execute(query).fetchall()
        for tvmaze_lookup in tvmaze_lookup_result:
            old_tvmaze_lookup_id = tvmaze_lookup.pop('id')
            tvmaze_lookup['server_id'] = new_server_id
            key_dict = {}
            key_dict['server_id'] = tvmaze_lookup.pop('server_id')
            key_dict['rating_key'] = tvmaze_lookup.pop('rating_key')
            result = monitor_db.upsert('tvmaze_lookup', key_dict=key_dict, value_dict=tvmaze_lookup)

        logger.info(u"Tautulli Importer :: tvmaze_lookup imported.")

    except sqlite3.IntegrityError:
        logger.error(u"Tautulli Import_Tautulli :: Queries failed: %s", query)

    except Exception as e:
        raise Exception('TVMaze Lookup Import failed: %s' % e)


def import_newsletters(import_db, monitor_db, notifier_lookup):
    logger.info(u"Tautulli Importer :: Importing Newsletters table...")

    try:
        query = 'SELECT * FROM newsletters'
        newsletters = import_db.execute(query).fetchall()
        for newsletter in newsletters:
            old_newsletters_id = newsletter.pop('id')

            newsletter_config = json.loads(newsletter['newsletter_config'])

            if newsletter_config['notifier_id']:
                newsletter_config['notifier_id'] = notifier_lookup[newsletter_config['notifier_id']]

            incl_servers = []
            for server_id in newsletter_config['incl_servers']:
                result = import_db.execute('SELECT pms_identifier FROM servers WHERE id = %s' % server_id).fetchone()
                incl_servers.append(plexpy.PMS_SERVERS.get_server_by_identifier(result['pms_identifier']).CONFIG.ID)
            newsletter_config['incl_servers'] = incl_servers

            incl_libraries = []
            for library_id in newsletter_config['incl_libraries']:
                query = 'SELECT library_sections.section_id, servers.pms_identifier ' \
                        '  FROM library_sections ' \
                        '  JOIN servers ON library_sections.server_id = servers.id ' \
                        ' WHERE library_sections.id = %s' % library_id
                result = import_db.execute(query).fetchone()
                new_server_id = plexpy.PMS_SERVERS.get_server_by_identifier(result['pms_identifier']).CONFIG.ID
                lib_id = libraries.get_section_index(new_server_id, result['section_id'])
                if lib_id:
                    incl_libraries.append(lib_id)
            newsletter_config['incl_libraries'] = sorted(incl_libraries)

            newsletter['newsletter_config'] = json.dumps(newsletter_config)

            email_config = json.loads(newsletter['email_config'])
            if email_config['notifier_id']:
                email_config['notifier_id'] = notifier_lookup[email_config['notifier_id']]
            newsletter['email_config'] = json.dumps(email_config)

            key_dict = {}
            key_dict['agent_id'] = newsletter.pop('agent_id')
            key_dict['newsletter_config'] = newsletter.pop('newsletter_config')

            result = monitor_db.upsert('newsletters', key_dict=key_dict, value_dict=newsletter)

        logger.info(u"Tautulli Importer :: Newsletters imported.")

    except sqlite3.IntegrityError:
        logger.error(u"Tautulli Import_Tautulli :: Queries failed: %s", query)

    except Exception as e:
        raise Exception('Newsletters Import failed: %s' % e)


def import_notifiers(import_db, monitor_db):
    logger.info(u"Tautulli Importer :: Importing Notifiers table...")

    try:
        notifiers_lookup = {}
        query = 'SELECT * FROM notifiers'
        notifiers_result = import_db.execute(query).fetchall()
        for notifiers in notifiers_result:
            old_notifier_id = notifiers.pop('id')
            key_dict = {}
            key_dict['agent_id'] = notifiers.pop('agent_id')
            key_dict['friendly_name'] = notifiers.pop('friendly_name')
            key_dict['notifier_config'] = notifiers.pop('notifier_config')
            result = monitor_db.upsert('notifiers', key_dict=key_dict, value_dict=notifiers)
            if result == 'insert':
                new_notifier_id = monitor_db.last_insert_id()
                import_notify_log(import_db, monitor_db, old_notifier_id, new_notifier_id)
            else:
                args = []
                query = 'SELECT id FROM notifiers WHERE '
                for key, value in key_dict.items():
                    query += key + ' = ? AND '
                    args.append(value)
                query = query.rstrip(' AND ')
                result = monitor_db.select_single(query, args)
                new_notifier_id = result['id']
            notifiers_lookup[old_notifier_id] = new_notifier_id

        logger.info(u"Tautulli Importer :: Notifiers imported.")
        return notifiers_lookup

    except sqlite3.IntegrityError:
        logger.error(u"Tautulli Import_Tautulli :: Queries failed: %s", query)

    except Exception as e:
        raise Exception('Notifiers Import failed: %s' % e)


def import_notify_log(import_db, monitor_db, old_notifier_id, new_notifier_id):
    logger.info(u"Tautulli Importer :: Importing Notifier_log table entries for notifier ID %s" % old_notifier_id)

    try:
        query = 'SELECT * FROM notify_log WHERE notifier_id = %s' % old_notifier_id
        notify_log_result = import_db.execute(query).fetchall()
        for notify_log in notify_log_result:
            old_notify_log_id = notify_log.pop('id')
            notify_log['notifier_id'] = new_notifier_id
            query = (
                    "INSERT INTO notify_log (" + ", ".join(notify_log.keys()) + ")" +
                    " VALUES (" + ", ".join(["?"] * len(notify_log.keys())) + ")"
            )
            monitor_db.action(query, notify_log.values())

        logger.info(u"Tautulli Importer :: Notify_log imported for notifier ID %s." % old_notifier_id)

    except sqlite3.IntegrityError:
        logger.error(u"Tautulli Import_Tautulli :: Queries failed: %s", query)

    except Exception as e:
        raise Exception('Notify Log Import failed: %s' % e)
