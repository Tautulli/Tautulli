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
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import email.utils
from itertools import groupby
from mako.lookup import TemplateLookup
from mako import exceptions
import os
import re
import time

import plexpy
import database
import helpers
import logger
import notification_handler
import pmsconnect
import request


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


def get_agent_class(agent_id=None, config=None):
    if str(agent_id).isdigit():
        agent_id = int(agent_id)

        if agent_id == 0:
            return RecentlyAdded(config=config)
        else:
            return Newsletter(config=config)
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
                       'friendly_name, active FROM newsletters %s' % where, args=args)

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
        config = json.loads(result.pop('newsletter_config') or '{}')
        newsletter_agent = get_agent_class(agent_id=result['agent_id'], config=config)
        newsletter_config = newsletter_agent.return_config_options()
    except Exception as e:
        logger.error(u"Tautulli Newsletters :: Failed to get newsletter config options: %s." % e)
        return

    result['config'] = config
    result['config_options'] = newsletter_config

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

    keys = {'id': None}
    values = {'agent_id': agent['id'],
              'agent_name': agent['name'],
              'agent_label': agent['label'],
              'friendly_name': '',
              'newsletter_config': json.dumps(get_agent_class(agent_id=agent['id']).config)
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

    newsletter_config = {k[len(config_prefix):]: kwargs.pop(k)
                         for k in kwargs.keys() if k.startswith(config_prefix)}
    newsletter_config = get_agent_class(agent['id']).set_config(config=newsletter_config)

    keys = {'id': newsletter_id}
    values = {'agent_id': agent['id'],
              'agent_name': agent['name'],
              'agent_label': agent['label'],
              'friendly_name': kwargs.get('friendly_name', ''),
              'newsletter_config': json.dumps(newsletter_config),
              'cron': kwargs.get('cron'),
              'active': kwargs.get('active')
              }

    db = database.MonitorDatabase()
    try:
        db.upsert(table_name='newsletters', key_dict=keys, value_dict=values)
        logger.info(u"Tautulli Newsletters :: Updated newsletter agent: %s (newsletter_id %s)."
                    % (agent['label'], newsletter_id))
        return True
    except Exception as e:
        logger.warn(u"Tautulli Newsletters :: Unable to update newsletter agent: %s." % e)
        return False


def send_newsletter(newsletter_id=None, newsletter_log_id=None, **kwargs):
    newsletter_config = get_newsletter_config(newsletter_id=newsletter_id)
    if newsletter_config:
        agent = get_agent_class(agent_id=newsletter_config['agent_id'],
                                config=newsletter_config['config'])
        return agent.send(newsletter_log_id=newsletter_log_id, **kwargs)
    else:
        logger.debug(u"Tautulli Newsletters :: Notification requested but no newsletter_id received.")


def serve_template(templatename, **kwargs):
    interface_dir = os.path.join(str(plexpy.PROG_DIR), 'data/interfaces/')
    template_dir = os.path.join(str(interface_dir), 'newsletters')

    _hplookup = TemplateLookup(directories=[template_dir], default_filters=['unicode', 'h'])

    try:
        template = _hplookup.get_template(templatename)
        return template.render(**kwargs)
    except:
        return exceptions.html_error_template().render()


class Newsletter(object):
    NAME = ''
    _DEFAULT_CONFIG = {}

    def __init__(self, config=None):
        self.config = {}
        self.set_config(config)

    def set_config(self, config=None):
        self.config = self._validate_config(config)
        return self.config

    def _validate_config(self, config=None):
        if config is None:
            return self._DEFAULT_CONFIG

        new_config = {}
        for k, v in self._DEFAULT_CONFIG.iteritems():
            if isinstance(v, int):
                new_config[k] = helpers.cast_to_int(config.get(k, v))
            else:
                new_config[k] = config.get(k, v)

        return new_config

    def preview(self, **kwargs):
        pass

    def send(self, **kwargs):
        pass

    def make_request(self, url, method='POST', **kwargs):
        response, err_msg, req_msg = request.request_response2(url, method, **kwargs)

        if response and not err_msg:
            logger.info(u"Tautulli Newsletters :: {name} notification sent.".format(name=self.NAME))
            return True

        else:
            verify_msg = ""
            if response is not None and response.status_code >= 400 and response.status_code < 500:
                verify_msg = " Verify you notification newsletter agent settings are correct."

            logger.error(u"Tautulli Newsletters :: {name} notification failed.{}".format(verify_msg, name=self.NAME))

            if err_msg:
                logger.error(u"Tautulli Newsletters :: {}".format(err_msg))

            if req_msg:
                logger.debug(u"Tautulli Newsletters :: Request response: {}".format(req_msg))

            return False

    def return_config_options(self):
        config_options = []
        return config_options


class RecentlyAdded(Newsletter):
    """
    Recently Added Newsletter
    """
    NAME = 'Recently Added'
    _DEFAULT_CONFIG = {'last_days': 7,
                       'incl_movies': 1,
                       'incl_shows': 1,
                       'incl_artists': 1
                       }
    _TEMPLATE = 'recently_added.html'

    def __init__(self, config=None):
        super(RecentlyAdded, self).__init__(config)

        date_format = helpers.momentjs_to_arrow(plexpy.CONFIG.DATE_FORMAT)

        self.end_time = int(time.time())
        self.start_time = self.end_time - self.config['last_days']*24*60*60
        self.end_date = arrow.get(self.end_time).format(date_format)
        self.start_date = arrow.get(self.start_time).format(date_format)

        self.plexpy_config = {
            'pms_identifier': plexpy.CONFIG.PMS_IDENTIFIER,
            'pms_web_url': plexpy.CONFIG.PMS_WEB_URL
        }

        self.recently_added = {}

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

        if media_type == 'show':
            shows_list = []
            show_rating_keys = []
            for item in recently_added:
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
                filtered_children.sort(key=lambda x: x['parent_media_index'])

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

    def get_recently_added(self):
        if self.config['incl_movies']:
            self.recently_added['movie'] = self._get_recently_added('movie')
        if self.config['incl_shows']:
            self.recently_added['show'] = self._get_recently_added('show')
        if self.config['incl_artists']:
            self.recently_added['artist'] = self._get_recently_added('artist')

        return self.recently_added

    def preview(self, **kwargs):
        self.get_recently_added()

        return serve_template(
            templatename=self._TEMPLATE,
            title=self.NAME,
            recently_added=self.recently_added,
            start_date=self.start_date,
            end_date=self.end_date,
            plexpy_config=self.plexpy_config
        )

    def send(self, **kwargs):
        if not subject or not body:
            return

        if self.config['incl_subject']:
            text = subject.encode('utf-8') + '\r\n' + body.encode("utf-8")
        else:
            text = body.encode("utf-8")

        data = {'content': text}
        if self.config['username']:
            data['username'] = self.config['username']
        if self.config['avatar_url']:
            data['avatar_url'] = self.config['avatar_url']
        if self.config['tts']:
            data['tts'] = True

        if self.config['incl_card'] and kwargs.get('parameters', {}).get('media_type'):
            # Grab formatted metadata
            pretty_metadata = PrettyMetadata(kwargs['parameters'])

            if pretty_metadata.media_type == 'movie':
                provider = self.config['movie_provider']
            elif pretty_metadata.media_type in ('show', 'season', 'episode'):
                provider = self.config['tv_provider']
            elif pretty_metadata.media_type in ('artist', 'album', 'track'):
                provider = self.config['music_provider']
            else:
                provider = None

            poster_url = pretty_metadata.get_poster_url()
            provider_name = pretty_metadata.get_provider_name(provider)
            provider_link = pretty_metadata.get_provider_link(provider)
            title = pretty_metadata.get_title('\xc2\xb7'.decode('utf8'))
            description = pretty_metadata.get_description()
            plex_url = pretty_metadata.get_plex_url()

            # Build Discord post attachment
            attachment = {'title': title
                          }

            if self.config['color']:
                hex_match = re.match(r'^#([0-9a-fA-F]{3}){1,2}$', self.config['color'])
                if hex_match:
                    hex = hex_match.group(0).lstrip('#')
                    hex = ''.join(h * 2 for h in hex) if len(hex) == 3 else hex
                    attachment['color'] = helpers.hex_to_int(hex)

            if self.config['incl_thumbnail']:
                attachment['thumbnail'] = {'url': poster_url}
            else:
                attachment['image'] = {'url': poster_url}

            if self.config['incl_description'] or pretty_metadata.media_type in ('artist', 'album', 'track'):
                attachment['description'] = description

            fields = []
            if provider_link:
                attachment['url'] = provider_link
                fields.append({'name': 'View Details',
                               'value': '[%s](%s)' % (provider_name, provider_link.encode('utf-8')),
                               'inline': True})
            if self.config['incl_pmslink']:
                fields.append({'name': 'View Details',
                               'value': '[Plex Web](%s)' % plex_url.encode('utf-8'),
                               'inline': True})
            if fields:
                attachment['fields'] = fields

            data['embeds'] = [attachment]

        headers = {'Content-type': 'application/json'}
        params = {'wait': True}

        return self.make_request(self.config['hook'], params=params, headers=headers, json=data)

    def return_config_options(self):
        config_option = [{'label': 'Number of Days',
                          'value': self.config['last_days'],
                          'name': 'recently_added_last_days',
                          'description': 'The past number of days to include in the newsletter.',
                          'input_type': 'number'
                          },
                         {'label': 'Include Movies',
                          'value': self.config['incl_movies'],
                          'description': 'Include recently added movies in the newsletter.',
                          'name': 'recently_added_incl_movies',
                          'input_type': 'checkbox'
                          },
                         {'label': 'Include TV Shows',
                          'value': self.config['incl_shows'],
                          'description': 'Include recently added TV shows in the newsletter.',
                          'name': 'recently_added_incl_shows',
                          'input_type': 'checkbox'
                          },
                         {'label': 'Include Music',
                          'value': self.config['incl_artists'],
                          'description': 'Include recently added music in the newsletter.',
                          'name': 'recently_added_incl_artists',
                          'input_type': 'checkbox'
                          }
                         ]

        return config_option
