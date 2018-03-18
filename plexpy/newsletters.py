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

import arrow
import json
from itertools import groupby
from mako.lookup import TemplateLookup
from mako import exceptions
import os

import plexpy
import common
import database
import helpers
import libraries
import logger
import newsletter_handler
import notification_handler
import pmsconnect
from notification_handler import get_poster_info
from notifiers import send_notification, EMAIL


AGENT_IDS = {
    'recently_added': 0
}


def available_newsletter_agents():
    agents = [
        {
            'label': 'Recently Added',
            'name': 'recently_added',
            'id': AGENT_IDS['recently_added']
        }
    ]

    return agents


def available_notification_actions():
    actions = [{'label': 'Schedule',
                'name': 'on_cron',
                'description': 'Trigger a notification on a certain schedule.',
                'subject': 'Tautulli Newsletter',
                'icon': 'fa-calendar',
                'media_types': ('newsletter',)
                }
               ]

    return actions


def get_agent_class(agent_id=None, config=None, email_config=None):
    if str(agent_id).isdigit():
        agent_id = int(agent_id)

        if agent_id == 0:
            return RecentlyAdded(config=config, email_config=email_config)
        else:
            return Newsletter(config=config, email_config=email_config)
    else:
        return None


def get_newsletter_agents():
    return tuple(a['name'] for a in sorted(available_newsletter_agents(), key=lambda k: k['label']))


def get_newsletters(newsletter_id=None):
    where = where_id = ''
    args = []

    if newsletter_id:
        where = 'WHERE '
        if newsletter_id:
            where_id += 'id = ?'
            args.append(newsletter_id)
        where += ' AND '.join([w for w in [where_id] if w])

    db = database.MonitorDatabase()
    result = db.select('SELECT id, agent_id, agent_name, agent_label, '
                       'friendly_name, cron, active FROM newsletters %s' % where, args=args)

    return result


def delete_newsletter(newsletter_id=None):
    db = database.MonitorDatabase()

    if str(newsletter_id).isdigit():
        logger.debug(u"Tautulli Newsletters :: Deleting newsletter_id %s from the database."
                     % newsletter_id)
        result = db.action('DELETE FROM newsletters WHERE id = ?', args=[newsletter_id])
        return True
    else:
        return False


def get_newsletter_config(newsletter_id=None):
    if str(newsletter_id).isdigit():
        newsletter_id = int(newsletter_id)
    else:
        logger.error(u"Tautulli Newsletters :: Unable to retrieve newsletter config: invalid newsletter_id %s."
                     % newsletter_id)
        return None

    db = database.MonitorDatabase()
    result = db.select_single('SELECT * FROM newsletters WHERE id = ?', args=[newsletter_id])

    if not result:
        return None

    try:
        config = json.loads(result.pop('newsletter_config', '{}'))
        email_config = json.loads(result.pop('email_config', '{}'))
        newsletter_agent = get_agent_class(agent_id=result['agent_id'], config=config, email_config=email_config)
        newsletter_config = newsletter_agent.return_config_options()
        newsletter_email_config = newsletter_agent.return_email_config_options()
    except Exception as e:
        logger.error(u"Tautulli Newsletters :: Failed to get newsletter config options: %s." % e)
        return

    result['config'] = config
    result['email_config'] = email_config
    result['config_options'] = newsletter_config
    result['email_config_options'] = newsletter_email_config

    return result


def add_newsletter_config(agent_id=None, **kwargs):
    if str(agent_id).isdigit():
        agent_id = int(agent_id)
    else:
        logger.error(u"Tautulli Newsletters :: Unable to add new newsletter: invalid agent_id %s."
                     % agent_id)
        return False

    agent = next((a for a in available_newsletter_agents() if a['id'] == agent_id), None)

    if not agent:
        logger.error(u"Tautulli Newsletters :: Unable to retrieve new newsletter agent: invalid agent_id %s."
                     % agent_id)
        return False

    agent_class = get_agent_class(agent_id=agent['id'])

    keys = {'id': None}
    values = {'agent_id': agent['id'],
              'agent_name': agent['name'],
              'agent_label': agent['label'],
              'friendly_name': '',
              'newsletter_config': json.dumps(agent_class.config),
              'email_config': json.dumps(agent_class.email_config)
              }

    db = database.MonitorDatabase()
    try:
        db.upsert(table_name='newsletters', key_dict=keys, value_dict=values)
        newsletter_id = db.last_insert_id()
        logger.info(u"Tautulli Newsletters :: Added new newsletter agent: %s (newsletter_id %s)."
                    % (agent['label'], newsletter_id))
        return newsletter_id
    except Exception as e:
        logger.warn(u"Tautulli Newsletters :: Unable to add newsletter agent: %s." % e)
        return False


def set_newsletter_config(newsletter_id=None, agent_id=None, **kwargs):
    if str(agent_id).isdigit():
        agent_id = int(agent_id)
    else:
        logger.error(u"Tautulli Newsletters :: Unable to set exisiting newsletter: invalid agent_id %s."
                     % agent_id)
        return False

    agent = next((a for a in available_newsletter_agents() if a['id'] == agent_id), None)

    if not agent:
        logger.error(u"Tautulli Newsletters :: Unable to retrieve existing newsletter agent: invalid agent_id %s."
                     % agent_id)
        return False

    config_prefix = agent['name'] + '_'
    email_config_prefix = 'email_'

    newsletter_config = {k[len(config_prefix):]: kwargs.pop(k)
                         for k in kwargs.keys() if k.startswith(config_prefix)}
    email_config = {k[len(email_config_prefix):]: kwargs.pop(k)
                    for k in kwargs.keys() if k.startswith(email_config_prefix)}

    agent_class = get_agent_class(agent_id=agent['id'], config=newsletter_config, email_config=email_config)

    keys = {'id': newsletter_id}
    values = {'agent_id': agent['id'],
              'agent_name': agent['name'],
              'agent_label': agent['label'],
              'friendly_name': kwargs.get('friendly_name', ''),
              'newsletter_config': json.dumps(agent_class.config),
              'email_config': json.dumps(agent_class.email_config),
              'cron': kwargs.get('cron'),
              'active': kwargs.get('active')
              }

    db = database.MonitorDatabase()
    try:
        db.upsert(table_name='newsletters', key_dict=keys, value_dict=values)
        logger.info(u"Tautulli Newsletters :: Updated newsletter agent: %s (newsletter_id %s)."
                    % (agent['label'], newsletter_id))
        newsletter_handler.schedule_newsletters(newsletter_id=newsletter_id)
        return True
    except Exception as e:
        logger.warn(u"Tautulli Newsletters :: Unable to update newsletter agent: %s." % e)
        return False


def send_newsletter(newsletter_id=None, subject=None, notify_action='', newsletter_log_id=None, **kwargs):
    newsletter_config = get_newsletter_config(newsletter_id=newsletter_id)
    if newsletter_config:
        agent = get_agent_class(agent_id=newsletter_config['agent_id'],
                                config=newsletter_config['config'],
                                email_config=newsletter_config['email_config'])
        return agent.send(subject=subject,
                          action=notify_action.split('on_')[-1],
                          newsletter_log_id=newsletter_log_id,
                          **kwargs)
    else:
        logger.debug(u"Tautulli Newsletters :: Notification requested but no newsletter_id received.")


def serve_template(templatename, **kwargs):
    interface_dir = os.path.join(str(plexpy.PROG_DIR), 'data/interfaces/')
    template_dir = os.path.join(str(interface_dir), plexpy.CONFIG.INTERFACE_NEWSLETTERS)

    _hplookup = TemplateLookup(directories=[template_dir], default_filters=['unicode', 'h'])

    try:
        template = _hplookup.get_template(templatename)
        return template.render(**kwargs)
    except:
        return exceptions.html_error_template().render()


class Newsletter(object):
    NAME = ''
    _DEFAULT_CONFIG = {'last_days': 7}
    _DEFAULT_EMAIL_CONFIG = EMAIL().return_default_config()
    _DEFAULT_EMAIL_CONFIG['from_name'] = 'Tautulli Newsletter'
    _DEFAULT_EMAIL_CONFIG['notifier'] = 0
    _DEFAULT_EMAIL_CONFIG['subject'] = 'Tautulli Newsletter'
    _TEMPLATE_MASTER = ''
    _TEMPLATE = ''

    def __init__(self, config=None, email_config=None, start_date=None, end_date=None):
        self.config = self.set_config(config=config, default=self._DEFAULT_CONFIG)
        self.email_config = self.set_config(config=email_config, default=self._DEFAULT_EMAIL_CONFIG)

        date_format = helpers.momentjs_to_arrow(plexpy.CONFIG.DATE_FORMAT)

        self.start_date = None
        self.end_date = None

        if end_date:
            try:
                self.end_date = arrow.get(end_date, 'YYYY-MM-DD', tzinfo='local').ceil('day')
            except ValueError:
                pass

        if self.end_date is None:
            self.end_date = arrow.now().ceil('day')

        if start_date:
            try:
                self.start_date = arrow.get(start_date, 'YYYY-MM-DD', tzinfo='local').floor('day')
            except ValueError:
                pass

        if self.start_date is None:
            self.start_date = self.end_date.shift(days=-self.config['last_days']+1).floor('day')

        self.end_time = self.end_date.timestamp
        self.start_time = self.start_date.timestamp

        self.parameters = {
            'start_date': self.start_date.format(date_format),
            'end_date': self.end_date.format(date_format),
            'server_name': plexpy.CONFIG.PMS_NAME
        }

        self.subject = self.format_subject(self.email_config['subject'])

        self.is_preview = False

        self.data = {}

    def set_config(self, config=None, default=None):
        return self._validate_config(config=config, default=default)

    def _validate_config(self, config=None, default=None):
        if config is None:
            return default

        new_config = {}
        for k, v in default.iteritems():
            if isinstance(v, int):
                new_config[k] = helpers.cast_to_int(config.get(k, v))
            else:
                new_config[k] = config.get(k, v)

        return new_config

    def retrieve_data(self):
        pass

    def _has_data(self):
        return False

    def raw_data(self, preview=False):
        if preview:
            self.is_preview = True

        self.retrieve_data()
        return {'title': self.NAME,
                'parameters': self.parameters,
                'data': self.data}

    def generate_newsletter(self, preview=False, master=False):
        if preview:
            self.is_preview = True

        if master:
            template = self._TEMPLATE_MASTER
        else:
            template = self._TEMPLATE

        self.retrieve_data()

        return serve_template(
            templatename=template,
            title=self.NAME,
            parameters=self.parameters,
            data=self.data,
            preview=self.is_preview
        )

    def send(self):
        newsletter = self.generate_newsletter()

        if not self._has_data():
            logger.warn(u"Tautulli Newsletters :: %s newsletter has no data. Newsletter not sent." % self.NAME)
            return False

        if self.email_config['notifier']:
            return send_notification(
                notifier_id=self.email_config['notifier'],
                subject=self.subject,
                body=newsletter
            )

        else:
            email = EMAIL(config=self.email_config)
            return email.notify(
                subject=self.subject,
                body=newsletter
            )

    def format_subject(self, subject=None):
        subject = subject or self._DEFAULT_EMAIL_CONFIG['subject']

        try:
            subject = unicode(subject).format(**self.parameters)
        except LookupError as e:
            logger.error(
                u"Tautulli Newsletter :: Unable to parse parameter %s in newsletter subject. Using fallback." % e)
            subject = unicode(self._DEFAULT_EMAIL_CONFIG['subject']).format(**self.parameters)
        except Exception as e:
            logger.error(
                u"Tautulli Newsletter :: Unable to parse custom newsletter subject: %s. Using fallback." % e)
            subject = unicode(self._DEFAULT_EMAIL_CONFIG['subject']).format(**self.parameters)

        return subject

    def return_config_options(self):
        config_options = []
        return config_options

    def return_email_config_options(self):
        return EMAIL(self.email_config).return_config_options()


class RecentlyAdded(Newsletter):
    """
    Recently Added Newsletter
    """
    NAME = 'Recently Added'
    _DEFAULT_CONFIG = {'last_days': 7,
                       'incl_libraries': None
                       }
    _TEMPLATE_MASTER = 'recently_added_master.html'
    _TEMPLATE = 'recently_added.html'

    def __init__(self, config=None, email_config=None, start_date=None, end_date=None):
        super(RecentlyAdded, self).__init__(config=config, email_config=email_config)

        if self.config['incl_libraries'] is None:
            self.config['incl_libraries'] = []
        elif not isinstance(self.config['incl_libraries'], list):
            self.config['incl_libraries'] = [self.config['incl_libraries']]

        self._DEFAULT_EMAIL_CONFIG['subject'] = 'Recently Added to Plex ({server_name})! ({end_date})'

        self.parameters['pms_identifier'] = plexpy.CONFIG.PMS_IDENTIFIER
        self.parameters['pms_web_url'] = plexpy.CONFIG.PMS_WEB_URL

    def _get_recently_added(self, media_type=None):
        pms_connect = pmsconnect.PmsConnect()

        recently_added = []
        done = False
        start = 0

        while not done:
            recent_items = pms_connect.get_recently_added_details(start=str(start), count='10', type=media_type)
            filtered_items = [i for i in recent_items['recently_added']
                              if helpers.cast_to_int(i['added_at']) > self.start_time]
            if len(filtered_items) < 10:
                done = True
            else:
                start += 10

            recently_added.extend(filtered_items)

        if media_type == 'movie':
            movie_list = []
            for item in recently_added:
                # Filter included libraries
                if item['section_id'] not in self.config['incl_libraries']:
                    continue

                movie_list.append(item)

            recently_added = movie_list

        if media_type == 'show':
            shows_list = []
            show_rating_keys = []
            for item in recently_added:
                # Filter included libraries
                if item['section_id'] not in self.config['incl_libraries']:
                    continue

                if item['media_type'] == 'show':
                    show_rating_key = item['rating_key']
                elif item['media_type'] == 'season':
                    show_rating_key = item['parent_rating_key']
                elif item['media_type'] == 'episode':
                    show_rating_key = item['grandparent_rating_key']

                if show_rating_key in show_rating_keys:
                    continue

                show_metadata = pms_connect.get_metadata_details(show_rating_key, media_info=False)
                children = pms_connect.get_item_children(show_rating_key, get_grandchildren=True)
                filtered_children = [i for i in children['children_list']
                                     if helpers.cast_to_int(i['added_at']) > self.start_time]
                filtered_children.sort(key=lambda x: int(x['parent_media_index']))

                seasons = []
                for k, v in groupby(filtered_children, key=lambda x: x['parent_media_index']):
                    episodes = list(v)
                    num, num00 = notification_handler.format_group_index(
                        [helpers.cast_to_int(d['media_index']) for d in episodes])

                    seasons.append({'media_index': k,
                                    'episode_range': num00,
                                    'episode_count': len(episodes),
                                    'episode': episodes})

                num, num00 = notification_handler.format_group_index(
                    [helpers.cast_to_int(d['media_index']) for d in seasons])

                show_metadata['season_range'] = num00
                show_metadata['season_count'] = len(seasons)
                show_metadata['season'] = seasons

                shows_list.append(show_metadata)
                show_rating_keys.append(show_rating_key)

            recently_added = shows_list

        if media_type == 'artist':
            artists_list = []
            artist_rating_keys = []
            for item in recently_added:
                # Filter included libraries
                if item['section_id'] not in self.config['incl_libraries']:
                    continue

                if item['media_type'] == 'artist':
                    artist_rating_key = item['rating_key']
                elif item['media_type'] == 'album':
                    artist_rating_key = item['parent_rating_key']
                elif item['media_type'] == 'track':
                    artist_rating_key = item['grandparent_rating_key']

                if artist_rating_key in artist_rating_keys:
                    continue

                artist_metadata = pms_connect.get_metadata_details(artist_rating_key, media_info=False)
                children = pms_connect.get_item_children(artist_rating_key)
                filtered_children = [i for i in children['children_list']
                                     if helpers.cast_to_int(i['added_at']) > self.start_time]
                filtered_children.sort(key=lambda x: x['added_at'])

                albums = []
                for a in filtered_children:
                    album_metadata = pms_connect.get_metadata_details(a['rating_key'], media_info=False)
                    album_metadata['track_count'] = helpers.cast_to_int(album_metadata['children_count'])
                    albums.append(album_metadata)

                artist_metadata['album_count'] = len(albums)
                artist_metadata['album'] = albums

                artists_list.append(artist_metadata)
                artist_rating_keys.append(artist_rating_key)

            recently_added = artists_list

        return recently_added

    def retrieve_data(self):
        media_types = {s['section_type'] for s in self._get_sections()
                       if str(s['section_id']) in self.config['incl_libraries']}

        recently_added = {}
        for media_type in media_types:
            if media_type not in recently_added:
                recently_added[media_type] = self._get_recently_added(media_type)

        if not self.is_preview:
            # Upload posters and art to Imgur
            movies = recently_added.get('movie', [])
            shows = recently_added.get('show', [])
            artists = recently_added.get('artist', [])
            albums = [a for artist in artists for a in artist['album']]

            for item in movies + shows + albums:
                poster_info = get_poster_info(poster_thumb=item['thumb'],
                                              poster_key=item['rating_key'],
                                              poster_title=item['title'])
                if poster_info:
                    item['poster_url'] = poster_info['poster_url'] or common.ONLINE_POSTER_THUMB

                art_info = get_poster_info(poster_thumb=item['art'],
                                           poster_key=item['rating_key'],
                                           poster_title=item['title'],
                                           art=True,
                                           width='500',
                                           height='280',
                                           opacity='25',
                                           background='282828',
                                           blur='3')
                item['art_url'] = art_info.get('art_url', '')

        self.data['recently_added'] = recently_added

        return self.data

    def _has_data(self):
        recently_added = self.data.get('recently_added')
        if recently_added and \
                recently_added.get('movie') or \
                recently_added.get('show') or \
                recently_added.get('artist'):
            return True

        return False

    def _get_sections(self):
        return libraries.Libraries().get_sections()

    def _get_sections_options(self):
        library_types = {'movie': 'Movie Libraries',
                         'show': 'TV Show Libraries',
                         'artist': 'Music Libraries'}
        sections = {}
        for s in self._get_sections():
            if s['section_type'] != 'photo':
                library_type = library_types[s['section_type']]
                group = sections.get(library_type, [])
                group.append({'value': s['section_id'],
                              'text': s['section_name']})
                sections[library_type] = group
        return sections

    def return_config_options(self):
        config_option = [{'label': 'Number of Days',
                          'value': self.config['last_days'],
                          'name': 'recently_added_last_days',
                          'description': 'The past number of days to include in the newsletter.',
                          'input_type': 'number'
                          },
                         {'label': 'Included Libraries',
                          'value': self.config['incl_libraries'],
                          'description': 'Select the libraries to include in the newsletter.',
                          'name': 'recently_added_incl_libraries',
                          'input_type': 'selectize',
                          'select_options': self._get_sections_options()
                          }
                         ]

        return config_option
