"""Run with: PYTHONPATH=lib python3 -m unittest discover -s tests -v"""

from types import SimpleNamespace
import unittest
from unittest.mock import patch

import plexpy
from plexpy import config, notification_handler
from plexpy.notifiers import PrettyMetadata


class PrettyMetadataTitleTest(unittest.TestCase):
    def parameters(self, media_type, **overrides):
        parameters = {
            'media_type': media_type, 'action': 'created', 'title': 'A Movie',
            'year': 2026, 'show_name': 'Lanterns', 'season_name': 'Season 1',
            'episode_name': '' if media_type in ('show', 'season') else 'Pilot',
            'episode_num': '7', 'episode_count': 1,
            'season_num': '1', 'season_count': 1, 'artist_name': 'An Artist',
            'album_name': 'An Album', 'track_name': 'A Track',
            'track_artist': 'An Artist',
        }
        parameters.update(overrides)
        return parameters

    def assert_title(self, parameters, expected, divider='-'):
        original = parameters.copy()
        self.assertEqual(PrettyMetadata(parameters).get_title(divider),
                         expected)
        self.assertEqual(parameters, original)

    def test_created_group_titles_use_existing_ranges_and_counts(self):
        cases = (
            ('show', '1-3,5', 4, 'Lanterns (2026) - Seasons 1-3,5'),
            ('show', '2', 1, 'Lanterns (2026) - Season 2'),
            ('show', '0', 1, 'Lanterns (2026) - Season 0'),
            ('season', '2-4,7', 4, 'Lanterns - Season 1 - Episodes 2-4,7'),
            ('season', '7', 1, 'Lanterns - Season 1 - Episode 7'),
            ('season', '0', 1, 'Lanterns - Season 1 - Episode 0'),
        )
        for media_type, numbers, count, expected in cases:
            with self.subTest(media_type=media_type, numbers=numbers):
                prefix = 'season' if media_type == 'show' else 'episode'
                parameters = self.parameters(media_type, **{
                    prefix + '_num': numbers, prefix + '_count': count})
                self.assert_title(parameters, expected)

    def test_missing_group_details_do_not_invent_episode_or_season_zero(self):
        for media_type, expected in (('show', 'Lanterns (2026)'),
                                     ('season', 'Lanterns - Season 1')):
            prefix = 'season' if media_type == 'show' else 'episode'
            for numbers, count in (('0', 0), ('1-2', 0), ('', 2),
                                   (None, 2), ('1-2', None)):
                with self.subTest(media_type=media_type,
                                  numbers=numbers, count=count):
                    parameters = self.parameters(media_type)
                    for suffix, value in (('_num', numbers), ('_count', count)):
                        if value is None:
                            parameters.pop(prefix + suffix)
                        else:
                            parameters[prefix + suffix] = value
                    self.assert_title(parameters, expected)
            parameters = self.parameters(media_type)
            parameters.pop('episode_name')
            self.assert_title(parameters, expected)

    def test_other_actions_keep_original_group_titles(self):
        for action in ('play', 'watched', None):
            for media_type, expected in (('show', 'Lanterns (2026)'),
                                         ('season', 'Lanterns - Season 1')):
                with self.subTest(action=action, media_type=media_type):
                    parameters = self.parameters(media_type, action=action)
                    if action is None:
                        parameters.pop('action')
                    self.assert_title(parameters, expected)

    def test_actual_notification_parameters_distinguish_grouping(self):
        settings = SimpleNamespace(**{
            name: definition[2]
            for name, definition in config._CONFIG_DEFINITIONS.items()
        })
        with patch.object(plexpy, 'CONFIG', settings), \
                patch.object(notification_handler.pmsconnect,
                             'PmsConnect') as pms, \
                patch.object(notification_handler.activity_processor,
                             'ActivityProcessor') as activity, \
                patch.object(notification_handler.helpers,
                             'get_img_service', return_value=''), \
                patch.object(notification_handler.helpers,
                             'pms_name', return_value='Example Server'):
            activity.return_value.get_sessions.return_value = []
            for enabled in (False, True):
                settings.NOTIFY_GROUP_RECENTLY_ADDED_PARENT = enabled
                settings.NOTIFY_GROUP_RECENTLY_ADDED_GRANDPARENT = enabled
                for media_type in ('show', 'season'):
                    with self.subTest(grouping=enabled, media_type=media_type):
                        is_show = media_type == 'show'
                        metadata = {
                            'rating_key': 'parent', 'media_type': media_type,
                            'title': 'Lanterns' if is_show else 'Season 1',
                            'full_title': 'Lanterns - Season 1', 'year': 2026,
                            'parent_title': 'Lanterns', 'media_index': '1',
                        }
                        details = {'parent': metadata}
                        children = ['child-2', 'child-4']
                        for key, number in zip(children, ('2', '4')):
                            details[key] = {'rating_key': key,
                                            'parent_rating_key': 'parent',
                                            'media_index': number}
                        pms.return_value.get_metadata_details.side_effect = (
                            lambda rating_key: details.get(rating_key))
                        build = notification_handler.build_media_notify_params
                        parameters = build(
                            notify_action='on_created', timeline=metadata,
                            child_keys=children)
                        if media_type == 'show':
                            expected = '%s (2026)' % parameters['show_name']
                            suffix = ' - Seasons 2,4'
                        else:
                            expected = '%s - %s' % (parameters['show_name'],
                                                   parameters['season_name'])
                            suffix = ' - Episodes 2,4'
                        self.assertEqual(parameters['episode_name'],
                                         '' if enabled else metadata['title'])
                        if enabled:
                            expected += suffix
                        self.assert_title(parameters, expected)

    def test_other_media_titles_and_episode_divider_are_unchanged(self):
        cases = (
            ('movie', 'A Movie (2026)'),
            ('episode', 'Lanterns - Pilot (S1 - E7)'),
            ('artist', 'An Artist'),
            ('album', 'An Artist - An Album'),
            ('track', 'A Track - An Artist'),
        )
        for media_type, expected in cases:
            with self.subTest(media_type=media_type):
                self.assert_title(self.parameters(media_type), expected)
        self.assert_title(self.parameters('episode'),
                          'Lanterns - Pilot (S1 \u00b7 E7)', divider='\u00b7')


if __name__ == '__main__':
    unittest.main()
