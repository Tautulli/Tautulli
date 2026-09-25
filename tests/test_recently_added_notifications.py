"""Regression tests for episode details in grouped Recently Added notifications.

Run with: PYTHONPATH=lib python3 -m unittest discover -s tests -v
"""

import json
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, call, patch

import plexpy
from plexpy import activity_handler, config, notification_handler, notifiers


def show():
    return {'rating_key': 'show', 'media_type': 'show', 'title': 'Lanterns',
            'full_title': 'Lanterns', 'year': 2026}


def season(number=1):
    return {'rating_key': 'season-%s' % number, 'media_type': 'season',
            'media_index': str(number), 'title': 'Season %s' % number,
            'full_title': 'Lanterns - Season %s' % number,
            'parent_title': 'Lanterns', 'parent_rating_key': 'show',
            'parent_year': 2026, 'year': 2026}


def episode(number, season_number=1):
    return {'rating_key': 'episode-%s-%s' % (season_number, number),
            'media_type': 'episode', 'media_index': str(number),
            'title': 'Episode title %s' % number,
            'full_title': 'Lanterns - Episode title %s' % number,
            'parent_title': 'Season %s' % season_number,
            'parent_rating_key': 'season-%s' % season_number,
            'parent_media_index': str(season_number),
            'grandparent_title': 'Lanterns', 'grandparent_rating_key': 'show',
            'grandparent_year': 2026, 'year': 2026}


class RecentlyAddedNotificationsTest(unittest.TestCase):
    def setUp(self):
        self.config = SimpleNamespace(**{
            name: definition[2]
            for name, definition in config._CONFIG_DEFINITIONS.items()
        })
        self.config.NOTIFY_GROUP_RECENTLY_ADDED_PARENT = 1
        self.config.NOTIFY_GROUP_RECENTLY_ADDED_GRANDPARENT = 1
        self.metadata = {}
        self.queue = Mock()
        self.patch(plexpy, 'CONFIG', self.config)
        self.patch(plexpy, 'NOTIFY_QUEUE', self.queue)
        self.patch(activity_handler, 'RECENTLY_ADDED_QUEUE', {})
        self.pms = self.patch(notification_handler.pmsconnect, 'PmsConnect').return_value
        self.pms.get_metadata_details.side_effect = lambda rating_key: self.metadata.get(rating_key, {})
        self.pms.get_item_children.side_effect = lambda rating_key: {
            'children_list': [item for item in self.metadata.values()
                              if item.get('parent_rating_key') == rating_key]
        }
        self.patch(notification_handler.activity_processor, 'ActivityProcessor').return_value.get_sessions.return_value = []
        self.patch(notification_handler.helpers, 'get_img_service', return_value='')
        self.patch(notification_handler.helpers, 'pms_name', return_value='Example Server')
        self.database = self.patch(activity_handler.datafactory, 'DataFactory').return_value
        self.database.get_recently_added_item.return_value = None

    def patch(self, obj, name, *args, **kwargs):
        patcher = patch.object(obj, name, *args, **kwargs)
        result = patcher.start()
        self.addCleanup(patcher.stop)
        return result

    def add_metadata(self, *items):
        self.metadata.update({item['rating_key']: item for item in items})

    def parameters(self, item, child_keys=(), grandchild_keys=(), **kwargs):
        self.add_metadata(item)
        return notification_handler.build_media_notify_params(
            notify_action=kwargs.pop('notify_action', 'on_created'),
            timeline=item, child_keys=child_keys, grandchild_keys=grandchild_keys,
            **kwargs)

    def season_parameters(self, numbers=(2, 3, 4, 7)):
        episodes = [episode(number) for number in numbers]
        self.add_metadata(*episodes)
        return self.parameters(season(), [item['rating_key'] for item in episodes])

    def render(self, parameters, **kwargs):
        return notification_handler.build_notify_text(
            subject=kwargs.pop('subject', 'Server: {server_name}'),
            body=kwargs.pop('body', '{title} was added to Plex.'),
            notify_action=kwargs.pop('notify_action', 'on_created'),
            parameters=parameters, **kwargs)

    def enqueue(self, season_episodes):
        self.add_metadata(show())
        additions = activity_handler.RECENTLY_ADDED_QUEUE
        additions['show'] = set()
        for season_number, numbers in season_episodes.items():
            parent = season(season_number)
            self.add_metadata(parent)
            additions['show'].add(parent['rating_key'])
            additions[parent['rating_key']] = set()
            for number in numbers:
                item = episode(number, season_number)
                self.add_metadata(item)
                additions[parent['rating_key']].add(item['rating_key'])
                additions[item['rating_key']] = {'show'}

    def test_season_summary_preserves_ranges_and_gaps(self):
        parameters = self.season_parameters((7, 4, 2, 3))
        self.assertEqual(parameters['grouped_title'],
                         'Lanterns - Season 1 - Episodes 2-4, 7')
        self.assertEqual(parameters['episode_num'], '2-4,7')
        self.assertEqual(parameters['episode_num00'], '02-04,07')
        self.assertEqual(parameters['episode_count'], 4)

    def test_duplicate_episode_indexes_do_not_repeat_in_summary(self):
        second_copy = episode(3)
        second_copy['rating_key'] = 'second-copy'
        self.add_metadata(episode(2), episode(3), second_copy)
        parameters = self.parameters(season(), ['episode-1-2', 'episode-1-3', 'second-copy'])
        self.assertEqual(parameters['grouped_title'], 'Lanterns - Season 1 - Episodes 2-3')

    def test_existing_title_template_works_for_text_notification_services(self):
        parameters = self.season_parameters()
        for agent in notifiers.available_notification_agents():
            if agent['id'] in (12, 15, 23, 24, 25):  # Integrations opt in with {grouped_title}.
                continue
            with self.subTest(agent=agent['name']):
                subject, body, args = self.render(parameters, agent_id=agent['id'])
                self.assertEqual(subject, 'Server: Example Server')
                self.assertEqual(body, 'Lanterns - Season 1 - Episodes 2-4, 7 was added to Plex.')
                self.assertEqual(args, [])
        self.assertEqual(parameters['title'], 'Lanterns - Season 1')

    def test_explicit_episode_template_retains_legacy_parameters(self):
        parameters = self.season_parameters()
        _, body, _ = self.render(parameters, body='{show_name}: S{season_num00} E{episode_num00} ({episode_count})')
        self.assertEqual(body, 'Lanterns: S01 E02-04,07 (4)')

    def test_rendering_does_not_mutate_source_title_parameters(self):
        parameters = self.season_parameters()
        original = parameters.copy()
        _, body, _ = self.render(parameters, body='{full_title} | {title} | {grouped_title}')
        self.assertEqual(body,
                         'Lanterns - Season 1 | Lanterns - Season 1 - Episodes 2-4, 7'
                         ' | Lanterns - Season 1 - Episodes 2-4, 7')
        self.assertEqual(parameters, original)

    def test_title_conditions_still_match_original_metadata_after_rendering(self):
        parameters = self.season_parameters()
        self.render(parameters)
        self.patch(notifiers, 'get_notifier_config', return_value={
            'custom_conditions_logic': '',
            'custom_conditions': [{'parameter': 'title', 'operator': 'is',
                                   'value': ['Lanterns - Season 1'], 'type': 'str'}],
        })
        self.assertTrue(notification_handler.notify_custom_conditions(2, parameters))

    def test_json_templates_preserve_title_and_can_opt_in_to_episode_summary(self):
        parameters = self.season_parameters()
        for kwargs in ({'agent_id': 25}, {'agent_id': 23, 'as_json': True},
                       {'as_json': True}):
            with self.subTest(kwargs=kwargs):
                subject, body, _ = self.render(
                    parameters, subject='{"X-Title": "{title}"}',
                    body='{"nested": {"title": "{title}", "summary": "{grouped_title}", "count": "{episode_count}"}}',
                    **kwargs)
                self.assertEqual(json.loads(subject)['X-Title'], 'Lanterns - Season 1')
                self.assertEqual(json.loads(body)['nested'],
                                 {'title': 'Lanterns - Season 1',
                                  'summary': parameters['grouped_title'], 'count': '4'})

    def test_script_arguments_preserve_title_and_can_opt_in_to_episode_summary(self):
        parameters = self.season_parameters()
        _, _, args = self.render(parameters, agent_id=15,
                                subject='"{title}" "{grouped_title}" {episode_count}')
        self.assertEqual(args, ['Lanterns - Season 1',
                               'Lanterns - Season 1 - Episodes 2-4, 7', '4'])

    def test_automation_templates_preserve_title_and_can_opt_in_to_episode_summary(self):
        parameters = self.season_parameters()
        for agent_id in (12, 23, 24):  # IFTTT, MQTT, and Zapier.
            with self.subTest(agent_id=agent_id):
                subject, body, args = self.render(parameters, agent_id=agent_id, subject='{title}',
                                                  body='{title} | {grouped_title}')
                self.assertEqual(subject, 'Lanterns - Season 1')
                self.assertEqual(body, 'Lanterns - Season 1 | Lanterns - Season 1 - Episodes 2-4, 7')
                self.assertEqual(args, [])

    def test_large_season_batch_uses_one_children_request(self):
        parameters = self.season_parameters(range(1, 601))
        self.assertEqual(parameters['grouped_title'], 'Lanterns - Season 1 - Episodes 1-600')
        self.pms.get_metadata_details.assert_called_once_with(rating_key='season-1')
        self.pms.get_item_children.assert_called_once_with(rating_key='season-1')

    def test_large_show_batch_fetches_only_queued_seasons_in_bulk(self):
        self.add_metadata(season(1), season(2), season(3))
        added = [episode(number, parent) for parent in (1, 2) for number in range(1, 601)]
        self.add_metadata(*added, episode(601), episode(602, 2), episode(1, 3))
        parameters = self.parameters(show(), ['season-1', 'season-2'],
                                     [item['rating_key'] for item in added])
        self.assertEqual(parameters['grouped_title'],
                         'Lanterns - Season 1: Episodes 1-600; Season 2: Episodes 1-600')
        self.pms.get_metadata_details.assert_called_once_with(rating_key='show')
        self.assertEqual(self.pms.get_item_children.call_args_list,
                         [call(rating_key='show'), call(rating_key='season-1'),
                          call(rating_key='season-2')])

    def test_failed_bulk_listing_marks_details_unavailable_without_individual_lookups(self):
        self.pms.get_item_children.return_value = {'children_list': []}
        self.pms.get_item_children.side_effect = None
        parameters = self.season_parameters()
        self.assertEqual(parameters['grouped_title'],
                         'Lanterns - Season 1 - Episodes (details unavailable)')
        self.pms.get_metadata_details.assert_called_once_with(rating_key='season-1')

    def test_discord_body_and_card_describe_the_same_added_episodes(self):
        self.enqueue({1: (2, 3, 4, 7)})
        self.add_metadata(episode(1))  # Already in the library, absent from this batch.
        activity_handler.clear_recently_added_queue('show', 'Lanterns')
        notification = self.queue.put.call_args.args[0]
        parameters = self.parameters(notification['timeline_data'], notification['child_keys'])
        subject, body, _ = self.render(parameters, agent_id=20)
        discord = notifiers.DISCORD({'hook': 'https://example.invalid/webhook', 'incl_card': 1})
        with patch.object(notifiers.PrettyMetadata, 'get_image', return_value=None), \
                patch.object(discord, 'make_request', return_value=True) as send:
            self.assertTrue(discord.agent_notify(subject, body, 'created', parameters=parameters))
        payload = send.call_args.kwargs['json']
        self.assertEqual(payload['content'],
                         'Server: Example Server\r\nLanterns - Season 1 - Episodes 2-4, 7 was added to Plex.')
        self.assertEqual(payload['embeds'][0]['title'], 'Lanterns - Season 1 - Episodes 2-4, 7')
        self.assertNotIn(call(rating_key='episode-1-1'), self.pms.get_metadata_details.call_args_list)
        self.assertEqual(activity_handler.RECENTLY_ADDED_QUEUE, {})

    def test_lunasea_display_title_keeps_episode_details(self):
        parameters = self.season_parameters()
        subject, body, _ = self.render(parameters)
        lunasea = notifiers.LUNASEA({'hook': 'https://example.invalid/webhook'})
        with patch.object(notifiers.PrettyMetadata, 'get_poster_url', return_value=''), \
                patch.object(lunasea, 'make_request', return_value=True) as send:
            self.assertTrue(lunasea.agent_notify(subject, body, 'created', parameters=parameters))
        payload = send.call_args.kwargs['json']['data']
        self.assertEqual(payload['title'], parameters['grouped_title'])
        self.assertIn(parameters['grouped_title'], payload['message'])

    def test_long_discord_card_title_fits_limit_and_body_retains_all_episodes(self):
        parameters = self.season_parameters(range(1, 200, 2))
        subject, body, _ = self.render(parameters, agent_id=20)
        self.assertGreater(len(parameters['grouped_title']), 256)
        discord = notifiers.DISCORD({'hook': 'https://example.invalid/webhook', 'incl_card': 1})
        with patch.object(notifiers.PrettyMetadata, 'get_image', return_value=None), \
                patch.object(discord, 'make_request', return_value=True) as send:
            discord.agent_notify(subject, body, 'created', parameters=parameters)
        payload = send.call_args.kwargs['json']
        self.assertLessEqual(len(payload['embeds'][0]['title']), 256)
        self.assertTrue(payload['embeds'][0]['title'].startswith('Lanterns - Season 1 - Episodes 1, 3, 5'))
        self.assertIn(parameters['grouped_title'], payload['content'])
        self.assertIn('195, 197, 199 was added to Plex.', payload['content'])

    def test_oversized_discord_message_attaches_full_text_and_preserves_poster(self):
        parameters = self.season_parameters(range(1, 1200, 2))
        subject, body, _ = self.render(parameters, agent_id=20, subject='Server: Caf\u00e9')
        full_text = subject + '\r\n' + body
        self.assertGreater(len(full_text), 2000)
        poster = ('poster.png', b'poster content', 'image/png')
        for include_card, image in ((0, None), (1, None), (1, poster)):
            with self.subTest(include_card=include_card, poster=image is not None):
                discord = notifiers.DISCORD({'hook': 'https://example.invalid/webhook',
                                             'incl_card': include_card})
                with patch.object(notifiers.PrettyMetadata, 'get_image', return_value=image), \
                        patch.object(discord, 'make_request', return_value=True) as send:
                    discord.agent_notify(subject, body, 'created', parameters=parameters)
                files = send.call_args.kwargs['files']
                payload = json.loads(files['payload_json'][1])
                self.assertLessEqual(len(payload['content']), 2000)
                self.assertTrue(payload['content'].endswith('\n\nFull notification attached.'))
                file_key = 'files[1]' if image else 'files[0]'
                filename, contents, content_type = files[file_key]
                self.assertEqual(filename, 'recently-added.txt')
                self.assertEqual(content_type, 'text/plain')
                self.assertEqual(contents.decode('utf-8'), full_text)
                self.assertIn('1195, 1197, 1199 was added to Plex.', contents.decode('utf-8'))
                if image:
                    self.assertEqual(files['files[0]'], poster)
                    self.assertEqual(payload['embeds'][0]['image']['url'], 'attachment://poster.png')

    def test_multiple_seasons_keep_episode_associations_and_existing_persistence_scope(self):
        self.enqueue({2: (1,), 1: (2, 3, 4, 7)})
        activity_handler.clear_recently_added_queue('show', 'Lanterns')
        self.queue.put.assert_called_once()
        notification = self.queue.put.call_args.args[0]
        self.assertEqual(notification['child_keys'], {'season-1', 'season-2'})
        self.assertEqual(notification['grandchild_keys'],
                         {'episode-1-2', 'episode-1-3', 'episode-1-4', 'episode-1-7', 'episode-2-1'})
        parameters = self.parameters(notification['timeline_data'], notification['child_keys'],
                                     notification['grandchild_keys'])
        self.assertEqual(parameters['grouped_title'],
                         'Lanterns - Season 1: Episodes 2-4, 7; Season 2: Episode 1')
        self.assertEqual(notifiers.PrettyMetadata(parameters).get_title(), parameters['grouped_title'])
        self.assertEqual(parameters['season_num'], '1-2')
        self.assertEqual(parameters['episode_num'], '')
        recorded = {args.args[0] for args in self.database.set_recently_added_item.call_args_list}
        self.assertEqual(recorded, {'show', 'season-1', 'season-2'})
        self.assertEqual(activity_handler.RECENTLY_ADDED_QUEUE, {})

    def test_parent_grouping_when_show_grouping_is_disabled(self):
        self.config.NOTIFY_GROUP_RECENTLY_ADDED_GRANDPARENT = 0
        self.enqueue({1: (2, 3), 2: (7, 9)})
        activity_handler.clear_recently_added_queue('show', 'Lanterns')
        notifications = [args.args[0] for args in self.queue.put.call_args_list]
        self.assertEqual({n['timeline_data']['rating_key'] for n in notifications}, {'season-1', 'season-2'})
        self.assertTrue(all(len(n['child_keys']) == 2 and 'grandchild_keys' not in n for n in notifications))

    def test_grouping_disabled_keeps_each_episode_separate(self):
        self.config.NOTIFY_GROUP_RECENTLY_ADDED_GRANDPARENT = 0
        self.config.NOTIFY_GROUP_RECENTLY_ADDED_PARENT = 0
        self.enqueue({1: (2, 3), 2: (1,)})
        activity_handler.clear_recently_added_queue('show', 'Lanterns')
        notifications = [args.args[0] for args in self.queue.put.call_args_list]
        self.assertEqual({n['timeline_data']['rating_key'] for n in notifications},
                         {'episode-1-2', 'episode-1-3', 'episode-2-1'})
        for notification in notifications:
            self.assertNotIn('child_keys', notification)
            parameters = self.parameters(notification['timeline_data'])
            self.assertFalse(parameters['grouped_title'])
            self.assertEqual(self.render(parameters)[1], parameters['title'] + ' was added to Plex.')

    def test_single_episode_keeps_existing_title_and_card(self):
        self.enqueue({1: (7,)})
        activity_handler.clear_recently_added_queue('show', 'Lanterns')
        notification = self.queue.put.call_args.args[0]
        self.assertNotIn('child_keys', notification)
        parameters = self.parameters(notification['timeline_data'])
        self.assertFalse(parameters['grouped_title'])
        self.assertEqual(parameters['title'], 'Lanterns - Episode title 7')
        self.assertEqual(notifiers.PrettyMetadata(parameters).get_title(),
                         'Lanterns - Episode title 7 (S1 - E7)')

    def test_manual_season_notification_keeps_existing_behavior(self):
        self.add_metadata(episode(2), episode(3))
        parameters = self.parameters(season(), ['episode-1-2', 'episode-1-3'], manual_trigger=True)
        self.assertFalse(parameters['grouped_title'])
        self.assertEqual(self.render(parameters)[1], 'Lanterns - Season 1 was added to Plex.')
        self.assertEqual(notifiers.PrettyMetadata(parameters).get_title(), 'Lanterns - Season 1')

    def test_unrelated_action_does_not_use_grouped_title(self):
        parameters = self.season_parameters()
        parameters['action'] = 'play'
        _, body, _ = self.render(parameters, notify_action='on_play', body='{title}')
        self.assertEqual(body, 'Lanterns - Season 1')
        self.assertEqual(notifiers.PrettyMetadata(parameters).get_title(), 'Lanterns - Season 1')

    def test_movie_and_music_titles_remain_unchanged(self):
        movie = {'rating_key': 'movie', 'media_type': 'movie', 'title': 'A Movie',
                 'full_title': 'A Movie', 'year': 2026}
        album = {'rating_key': 'album', 'media_type': 'album', 'title': 'An Album',
                 'full_title': 'An Artist - An Album', 'parent_title': 'An Artist',
                 'parent_rating_key': 'artist', 'media_index': '1'}
        track = {'rating_key': 'track', 'media_type': 'track', 'title': 'A Track',
                 'full_title': 'An Artist - A Track', 'parent_rating_key': 'album',
                 'media_index': '2'}
        self.add_metadata(track)
        for item, children, pretty_title in ((movie, [], 'A Movie (2026)'),
                                              (album, ['track'], 'An Artist - An Album')):
            with self.subTest(media_type=item['media_type']):
                parameters = self.parameters(item, children)
                self.assertFalse(parameters['grouped_title'])
                self.assertEqual(self.render(parameters)[1], item['full_title'] + ' was added to Plex.')
                self.assertEqual(notifiers.PrettyMetadata(parameters).get_title(), pretty_title)

    def test_artist_grouping_does_not_fetch_or_record_new_track_details(self):
        artist = {'rating_key': 'artist', 'media_type': 'artist',
                  'title': 'An Artist', 'full_title': 'An Artist'}
        self.add_metadata(artist)
        additions = activity_handler.RECENTLY_ADDED_QUEUE
        additions['artist'] = {'album-1', 'album-2'}
        for number in (1, 2):
            album_key, track_key = 'album-%s' % number, 'track-%s' % number
            self.add_metadata({'rating_key': album_key, 'media_type': 'album',
                               'title': 'Album %s' % number, 'media_index': str(number),
                               'parent_rating_key': 'artist'})
            additions[album_key] = {track_key}
            additions[track_key] = {'artist'}
        activity_handler.clear_recently_added_queue('artist', 'An Artist')
        notification = self.queue.put.call_args.args[0]
        self.assertNotIn('grandchild_keys', notification)
        parameters = self.parameters(notification['timeline_data'], notification['child_keys'])
        self.assertFalse(parameters['grouped_title'])
        self.assertEqual(parameters['album_count'], 2)
        fetched = {args.kwargs.get('rating_key', args.args[0] if args.args else None)
                   for args in self.pms.get_metadata_details.call_args_list}
        self.assertEqual(fetched, {'artist', 'album-1', 'album-2'})
        recorded = {args.args[0] for args in self.database.set_recently_added_item.call_args_list}
        self.assertEqual(recorded, {'artist', 'album-1', 'album-2'})

    def test_missing_episode_lookup_keeps_known_numbers_and_marks_incomplete(self):
        self.add_metadata(episode(2))
        parameters = self.parameters(season(), ['episode-1-2', 'missing-episode'])
        title = parameters['grouped_title']
        self.assertIn('Episode 2', title)
        self.assertIn('details unavailable', title)
        self.assertNotIn('Episode 0', title)

    def test_missing_or_invalid_episode_numbers_do_not_become_zero(self):
        for invalid in (None, '', 'unknown', -1):
            with self.subTest(index=invalid):
                incomplete = episode(9)
                if invalid is None:
                    incomplete.pop('media_index')
                else:
                    incomplete['media_index'] = invalid
                self.add_metadata(episode(2), incomplete)
                parameters = self.parameters(season(), ['episode-1-2', 'episode-1-9'])
                title = parameters['grouped_title']
                self.assertIn('Episode 2', title)
                self.assertIn('details unavailable', title)
                self.assertNotIn('Episode 0', title)

    def test_all_episode_lookups_missing_do_not_claim_entire_season(self):
        parameters = self.parameters(season(), ['missing-one', 'missing-two'])
        title = parameters['grouped_title']
        self.assertIn('Episodes (details unavailable)', title)
        self.assertNotIn('Episode 0', title)

    def test_invalid_and_missing_episodes_do_not_repeat_incomplete_notice(self):
        invalid = episode(9)
        invalid['media_index'] = ''
        self.add_metadata(episode(2), invalid)
        parameters = self.parameters(season(), ['episode-1-2', 'episode-1-9', 'missing'])
        self.assertEqual(parameters['grouped_title'],
                         'Lanterns - Season 1 - Episode 2 (additional episode details unavailable)')

    def test_missing_season_lookup_uses_episode_parent_metadata(self):
        self.add_metadata(season(2), episode(3), episode(1, 2))
        parameters = self.parameters(show(), ['season-1', 'season-2'], ['episode-1-3', 'episode-2-1'])
        self.assertEqual(parameters['grouped_title'],
                         'Lanterns - Season 1: Episode 3; Season 2: Episode 1')

    def test_specials_and_actual_episode_zero_are_preserved(self):
        self.add_metadata(season(0), season(1), episode(0, 0), episode(2))
        parameters = self.parameters(show(), ['season-1', 'season-0'], ['episode-1-2', 'episode-0-0'])
        self.assertEqual(parameters['grouped_title'],
                         'Lanterns - Season 0: Episode 0; Season 1: Episode 2')


if __name__ == '__main__':
    unittest.main()
