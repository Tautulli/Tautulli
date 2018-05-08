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
import pmsconnect
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
                'body': 'Tautulli Newsletter',
                'message': '',
                'icon': 'fa-calendar',
                'media_types': ('newsletter',)
                }
               ]

    return actions


def get_agent_class(newsletter_id=None, agent_id=None, config=None, email_config=None, start_date=None, end_date=None,
                    subject=None, body=None, message=None):
    if str(agent_id).isdigit():
        agent_id = int(agent_id)

        kwargs = {'newsletter_id': newsletter_id,
                  'config': config,
                  'email_config': email_config,
                  'start_date': start_date,
                  'end_date': end_date,
                  'subject': subject,
                  'body': body,
                  'message': message}

        if agent_id == 0:
            return RecentlyAdded(**kwargs)
        else:
            return Newsletter(**kwargs)
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
        subject = result.pop('subject')
        body = result.pop('body')
        message = result.pop('message')
        newsletter_agent = get_agent_class(newsletter_id=newsletter_id, agent_id=result['agent_id'],
                                           config=config, email_config=email_config,
                                           subject=subject, body=body, message=message)
    except Exception as e:
        logger.error(u"Tautulli Newsletters :: Failed to get newsletter config options: %s." % e)
        return

    result['subject'] = newsletter_agent.subject
    result['body'] = newsletter_agent.body
    result['message'] = newsletter_agent.message
    result['config'] = newsletter_agent.config
    result['email_config'] = newsletter_agent.email_config
    result['config_options'] = newsletter_agent.return_config_options()
    result['email_config_options'] = newsletter_agent.return_email_config_options()

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
              'email_config': json.dumps(agent_class.email_config),
              'subject': agent_class.subject,
              'body': agent_class.body,
              'message': agent_class.message
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

    config_prefix = 'newsletter_config_'
    email_config_prefix = 'newsletter_email_'

    newsletter_config = {k[len(config_prefix):]: kwargs.pop(k)
                         for k in kwargs.keys() if k.startswith(config_prefix)}
    email_config = {k[len(email_config_prefix):]: kwargs.pop(k)
                    for k in kwargs.keys() if k.startswith(email_config_prefix)}

    subject = kwargs.pop('subject')
    body = kwargs.pop('body')
    message = kwargs.pop('message')

    agent_class = get_agent_class(newsletter_id=newsletter_id, agent_id=agent['id'],
                                  config=newsletter_config, email_config=email_config,
                                  subject=subject, body=body, message=message)

    keys = {'id': newsletter_id}
    values = {'agent_id': agent['id'],
              'agent_name': agent['name'],
              'agent_label': agent['label'],
              'friendly_name': kwargs.get('friendly_name', ''),
              'newsletter_config': json.dumps(agent_class.config),
              'email_config': json.dumps(agent_class.email_config),
              'subject': agent_class.subject,
              'body': agent_class.body,
              'message': agent_class.message,
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


def send_newsletter(newsletter_id=None, subject=None, body=None, message=None, newsletter_log_id=None, **kwargs):
    newsletter_config = get_newsletter_config(newsletter_id=newsletter_id)
    if newsletter_config:
        agent = get_agent_class(agent_id=newsletter_config['agent_id'],
                                config=newsletter_config['config'],
                                email_config=newsletter_config['email_config'],
                                subject=subject,
                                body=body,
                                messsage=message)
        return agent.send()
    else:
        logger.debug(u"Tautulli Newsletters :: Notification requested but no newsletter_id received.")


def serve_template(templatename, **kwargs):
    if plexpy.CONFIG.NEWSLETTER_CUSTOM_DIR:
        template_dir = plexpy.CONFIG.NEWSLETTER_CUSTOM_DIR
    else:
        interface_dir = os.path.join(str(plexpy.PROG_DIR), 'data/interfaces/')
        template_dir = os.path.join(str(interface_dir), plexpy.CONFIG.NEWSLETTER_TEMPLATES)

    _hplookup = TemplateLookup(directories=[template_dir], default_filters=['unicode', 'h'])

    try:
        template = _hplookup.get_template(templatename)
        return template.render(**kwargs)
    except:
        return exceptions.html_error_template().render()


def generate_newsletter_uuid():
    uuid = ''
    uuid_exists = 0
    db = database.MonitorDatabase()

    while not uuid or uuid_exists:
        uuid = plexpy.generate_uuid()[:8]
        result = db.select_single(
            'SELECT EXISTS(SELECT uuid FROM newsletter_log WHERE uuid = ?) as uuid_exists', [uuid])
        uuid_exists = result['uuid_exists']

    return uuid


class Newsletter(object):
    NAME = ''
    _DEFAULT_CONFIG = {'custom_cron': 0,
                       'time_frame': 7,
                       'time_frame_units': 'days',
                       'formatted': 1,
                       'notifier_id': 0,
                       'filename': ''}
    _DEFAULT_EMAIL_CONFIG = EMAIL().return_default_config()
    _DEFAULT_EMAIL_CONFIG['from_name'] = 'Tautulli Newsletter'
    _DEFAULT_EMAIL_CONFIG['notifier_id'] = 0
    _DEFAULT_SUBJECT = 'Tautulli Newsletter'
    _DEFAULT_BODY = 'View the newsletter here: {newsletter_url}'
    _DEFAULT_MESSAGE = ''
    _DEFAULT_FILENAME = 'newsletter_{newsletter_uuid}.html'
    _TEMPLATE_MASTER = ''
    _TEMPLATE = ''

    def __init__(self, newsletter_id=None, config=None, email_config=None, start_date=None, end_date=None,
                 subject=None, body=None, message=None):
        self.config = self.set_config(config=config, default=self._DEFAULT_CONFIG)
        self.email_config = self.set_config(config=email_config, default=self._DEFAULT_EMAIL_CONFIG)
        self.uuid = generate_newsletter_uuid()

        self.newsletter_id = newsletter_id
        self.start_date = None
        self.end_date = None

        if end_date:
            try:
                self.end_date = arrow.get(end_date, 'YYYY-MM-DD', tzinfo='local').ceil('day')
            except ValueError:
                pass

        if self.end_date is None:
            self.end_date = arrow.now()

        if start_date:
            try:
                self.start_date = arrow.get(start_date, 'YYYY-MM-DD', tzinfo='local').floor('day')
            except ValueError:
                pass

        if self.start_date is None:
            if self.config['time_frame_units'] == 'days':
                self.start_date = self.end_date.shift(days=-self.config['time_frame']+1).floor('day')
            else:
                self.start_date = self.end_date.shift(hours=-self.config['time_frame']).floor('hour')

        self.end_time = self.end_date.timestamp
        self.start_time = self.start_date.timestamp

        self.parameters = self.build_params()
        self.subject = subject or self._DEFAULT_SUBJECT
        self.body = body or self._DEFAULT_BODY
        self.message = message or self._DEFAULT_MESSAGE
        self.filename = self.config['filename'] or self._DEFAULT_FILENAME

        if not self.filename.endswith('.html'):
            self.filename += '.html'

        self.subject_formatted, self.body_formatted, self.message_formatted = self.build_text()
        self.filename_formatted = self.build_filename()

        self.data = {}
        self.newsletter = None

        self.is_preview = False

    def set_config(self, config=None, default=None):
        return self._validate_config(config=config, default=default)

    def _validate_config(self, config=None, default=None):
        if config is None:
            return default

        new_config = {}
        for k, v in default.iteritems():
            if isinstance(v, int):
                new_config[k] = helpers.cast_to_int(config.get(k, v))
            elif isinstance(v, list):
                c = config.get(k, v)
                if not isinstance(c, list):
                    new_config[k] = [c]
                else:
                    new_config[k] = c
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
            uuid=self.uuid,
            subject=self.subject_formatted,
            body=self.body_formatted,
            message=self.message_formatted,
            parameters=self.parameters,
            data=self.data,
            preview=self.is_preview
        )

    def send(self):
        self.newsletter = self.generate_newsletter()

        if not self._has_data():
            logger.warn(u"Tautulli Newsletters :: %s newsletter has no data. Newsletter not sent." % self.NAME)
            return False

        self._save()
        return self._send()

    def _save(self):
        newsletter_file = self.filename_formatted
        newsletter_folder = plexpy.CONFIG.NEWSLETTER_DIR or os.path.join(plexpy.DATA_DIR, 'newsletters')
        newsletter_file_fp = os.path.join(newsletter_folder, newsletter_file)

        # In case the user has deleted it manually
        if not os.path.exists(newsletter_folder):
            os.makedirs(newsletter_folder)

        try:
            with open(newsletter_file_fp, 'wb') as n_file:
                for line in self.newsletter.encode('utf-8').splitlines():
                    if '<!-- IGNORE SAVE -->' not in line:
                        n_file.write(line + '\r\n')

            logger.info(u"Tautulli Newsletters :: %s newsletter saved to %s" % (self.NAME, newsletter_file))
        except OSError as e:
            logger.error(u"Tautulli Newsletters :: Failed to save %s newsletter to %s: %s"
                         % (self.NAME, newsletter_file, e))

    def _send(self):
        if self.config['formatted']:
            if self.email_config['notifier_id']:
                return send_notification(
                    notifier_id=self.email_config['notifier_id'],
                    subject=self.subject_formatted,
                    body=self.newsletter
                )

            else:
                email = EMAIL(config=self.email_config)
                return email.notify(
                    subject=self.subject_formatted,
                    body=self.newsletter
                )
        elif self.config['notifier_id']:
            return send_notification(
                    notifier_id=self.config['notifier_id'],
                    subject=self.subject_formatted,
                    body=self.body_formatted
                )

    def build_params(self):
        parameters = self._build_params()

        return parameters

    def _build_params(self):
        date_format = helpers.momentjs_to_arrow(plexpy.CONFIG.DATE_FORMAT)

        if plexpy.CONFIG.NEWSLETTER_SELF_HOSTED and plexpy.CONFIG.HTTP_BASE_URL:
            base_url = plexpy.CONFIG.HTTP_BASE_URL + plexpy.HTTP_ROOT + 'newsletter/'
        else:
            base_url = helpers.get_plexpy_url() + '/newsletter/'

        parameters = {
            'server_name': plexpy.CONFIG.PMS_NAME,
            'start_date': self.start_date.format(date_format),
            'end_date': self.end_date.format(date_format),
            'week_number': self.start_date.isocalendar()[1],
            'newsletter_time_frame': self.config['time_frame'],
            'newsletter_time_frame_units': self.config['time_frame_units'],
            'newsletter_url': base_url + self.uuid,
            'newsletter_latest_url': base_url + 'id/' + str(self.newsletter_id),
            'newsletter_uuid': self.uuid,
            'newsletter_id': self.newsletter_id
        }

        return parameters

    def build_text(self):
        from notification_handler import CustomFormatter
        custom_formatter = CustomFormatter()

        try:
            subject = custom_formatter.format(unicode(self.subject), **self.parameters)
        except LookupError as e:
            logger.error(
                u"Tautulli Newsletter :: Unable to parse parameter %s in newsletter subject. Using fallback." % e)
            subject = unicode(self._DEFAULT_SUBJECT).format(**self.parameters)
        except Exception as e:
            logger.error(
                u"Tautulli Newsletter :: Unable to parse custom newsletter subject: %s. Using fallback." % e)
            subject = unicode(self._DEFAULT_SUBJECT).format(**self.parameters)

        try:
            body = custom_formatter.format(unicode(self.body), **self.parameters)
        except LookupError as e:
            logger.error(
                u"Tautulli Newsletter :: Unable to parse parameter %s in newsletter body. Using fallback." % e)
            body = unicode(self._DEFAULT_BODY).format(**self.parameters)
        except Exception as e:
            logger.error(
                u"Tautulli Newsletter :: Unable to parse custom newsletter body: %s. Using fallback." % e)
            body = unicode(self._DEFAULT_BODY).format(**self.parameters)

        try:
            message = custom_formatter.format(unicode(self.message), **self.parameters)
        except LookupError as e:
            logger.error(
                u"Tautulli Newsletter :: Unable to parse parameter %s in newsletter message. Using fallback." % e)
            message = unicode(self._DEFAULT_MESSAGE).format(**self.parameters)
        except Exception as e:
            logger.error(
                u"Tautulli Newsletter :: Unable to parse custom newsletter message: %s. Using fallback." % e)
            message = unicode(self._DEFAULT_MESSAGE).format(**self.parameters)

        return subject, body, message

    def build_filename(self):
        from notification_handler import CustomFormatter
        custom_formatter = CustomFormatter()

        try:
            filename = custom_formatter.format(unicode(self.filename), **self.parameters)
        except LookupError as e:
            logger.error(
                u"Tautulli Newsletter :: Unable to parse parameter %s in newsletter filename. Using fallback." % e)
            filename = unicode(self._DEFAULT_FILENAME).format(**self.parameters)
        except Exception as e:
            logger.error(
                u"Tautulli Newsletter :: Unable to parse custom newsletter subject: %s. Using fallback." % e)
            filename = unicode(self._DEFAULT_FILENAME).format(**self.parameters)

        return filename

    def return_config_options(self):
        return self._return_config_options()

    def _return_config_options(self):
        config_options = []

        return config_options

    def return_email_config_options(self):
        config_options = EMAIL(self.email_config).return_config_options()
        for c in config_options:
            c['name'] = 'newsletter_' + c['name']
        return config_options


class RecentlyAdded(Newsletter):
    """
    Recently Added Newsletter
    """
    NAME = 'Recently Added'
    _DEFAULT_CONFIG = Newsletter._DEFAULT_CONFIG.copy()
    _DEFAULT_CONFIG['incl_libraries'] = []
    _DEFAULT_SUBJECT = 'Recently Added to {server_name}! ({end_date})'
    _DEFAULT_BODY = 'View the newsletter here: {newsletter_url}'
    _DEFAULT_MESSAGE = ''
    _TEMPLATE_MASTER = 'recently_added_master.html'
    _TEMPLATE = 'recently_added.html'

    def _get_recently_added(self, media_type=None):
        from notification_handler import format_group_index

        pms_connect = pmsconnect.PmsConnect()

        recently_added = []
        done = False
        start = 0

        while not done:
            recent_items = pms_connect.get_recently_added_details(start=str(start), count='10', type=media_type)
            filtered_items = [i for i in recent_items['recently_added']
                              if self.start_time < helpers.cast_to_int(i['added_at']) < self.end_time]
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
                                     if self.start_time < helpers.cast_to_int(i['added_at']) < self.end_time]
                filtered_children.sort(key=lambda x: int(x['parent_media_index']))

                seasons = []
                for k, v in groupby(filtered_children, key=lambda x: x['parent_media_index']):
                    episodes = list(v)
                    num, num00 = format_group_index([helpers.cast_to_int(d['media_index']) for d in episodes])

                    seasons.append({'media_index': k,
                                    'episode_range': num00,
                                    'episode_count': len(episodes),
                                    'episode': episodes})

                num, num00 = format_group_index([helpers.cast_to_int(d['media_index']) for d in seasons])

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
                                     if self.start_time < helpers.cast_to_int(i['added_at']) < self.end_time]
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
        from notification_handler import get_img_info, set_hash_image_info

        if not self.config['incl_libraries']:
            logger.warn(u"Tautulli Newsletters :: Failed to retrieve %s newsletter data: no libraries selected." % self.NAME)

        media_types = {s['section_type'] for s in self._get_sections()
                       if str(s['section_id']) in self.config['incl_libraries']}

        recently_added = {}
        for media_type in media_types:
            if media_type not in recently_added:
                recently_added[media_type] = self._get_recently_added(media_type)

        movies = recently_added.get('movie', [])
        shows = recently_added.get('show', [])
        artists = recently_added.get('artist', [])
        albums = [a for artist in artists for a in artist['album']]

        if self.is_preview or helpers.get_img_service(include_self=True) == 'self-hosted':
            for item in movies + shows + albums:
                if item['media_type'] == 'album':
                    height = 150
                    fallback = 'cover'
                else:
                    height = 225
                    fallback = 'poster'

                item['thumb_hash'] = set_hash_image_info(
                    img=item['thumb'], width=150, height=height, fallback=fallback)

                if item['art']:
                    item['art_hash'] = set_hash_image_info(
                        img=item['art'], width=500, height=280,
                        opacity=25, background='282828', blur=3, fallback='art')
                else:
                    item['art_hash'] = ''

                item['poster_url'] = ''
                item['art_url'] = ''

        elif helpers.get_img_service():
            # Upload posters and art to image hosting service
            for item in movies + shows + albums:
                if item['media_type'] == 'album':
                    height = 150
                    fallback = 'cover'
                else:
                    height = 225
                    fallback = 'poster'

                img_info = get_img_info(
                    img=item['thumb'], rating_key=item['rating_key'], title=item['title'],
                    width=150, height=height, fallback=fallback)

                item['poster_url'] = img_info.get('img_url') or common.ONLINE_POSTER_THUMB

                img_info = get_img_info(
                    img=item['art'], rating_key=item['rating_key'], title=item['title'],
                    width=500, height=280, opacity=25, background='282828', blur=3, fallback='art')

                item['art_url'] = img_info.get('img_url')

                item['thumb_hash'] = ''
                item['art_hash'] = ''

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

    def build_params(self):
        parameters = self._build_params()

        newsletter_libraries = []
        for s in self._get_sections():
            if str(s['section_id']) in self.config['incl_libraries']:
                newsletter_libraries.append(s['section_name'])

        parameters['newsletter_libraries'] = ', '.join(sorted(newsletter_libraries))
        parameters['pms_identifier'] = plexpy.CONFIG.PMS_IDENTIFIER
        parameters['pms_web_url'] = plexpy.CONFIG.PMS_WEB_URL

        return parameters

    def return_config_options(self):
        config_options = self._return_config_options()

        additional_config = [
            {'label': 'Included Libraries',
             'value': self.config['incl_libraries'],
             'description': 'Select the libraries to include in the newsletter.',
             'name': 'newsletter_config_incl_libraries',
             'input_type': 'selectize',
             'select_options': self._get_sections_options()
             }
        ]

        return additional_config + config_options
