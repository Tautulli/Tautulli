"""Regression coverage for queue cleanup through real addition persistence."""

from collections import Counter
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import plexpy
from plexpy import activity_handler, datafactory, pmsconnect


class RecentlyAddedPersistenceTest(unittest.TestCase):
    def setUp(self):
        self.config = SimpleNamespace(
            NOTIFY_GROUP_RECENTLY_ADDED_PARENT=1,
            NOTIFY_GROUP_RECENTLY_ADDED_GRANDPARENT=1)
        self.metadata = {}
        self.queue = Mock()
        self.patch(plexpy, 'CONFIG', self.config)
        self.patch(plexpy, 'NOTIFY_QUEUE', self.queue)
        self.patch(activity_handler, 'RECENTLY_ADDED_QUEUE', {})
        self.pms = self.patch(pmsconnect, 'PmsConnect').return_value
        self.pms.get_metadata_details.side_effect = (
            lambda rating_key: self.metadata.get(rating_key, {}))
        # Keep DataFactory and its persistence logic; replace database I/O.
        self.database = self.patch(
            datafactory.database, 'MonitorDatabase').return_value
        self.database.select.return_value = []

    def patch(self, obj, name, *args):
        patcher = patch.object(obj, name, *args)
        replacement = patcher.start()
        self.addCleanup(patcher.stop)
        return replacement

    def add_metadata(self, key, media_type, parent='', grandparent=''):
        self.metadata[key] = {
            'rating_key': key, 'media_type': media_type,
            'full_title': key, 'added_at': '1700000000', 'section_id': '1',
            'parent_rating_key': parent,
            'grandparent_rating_key': grandparent, 'media_info': []}

    def enqueue(self, episodes_by_season):
        additions = activity_handler.RECENTLY_ADDED_QUEUE
        self.add_metadata('show', 'show')
        additions.setdefault('show', set())
        for number, episodes in episodes_by_season.items():
            season_key = 'season-%s' % number
            self.add_metadata(season_key, 'season', parent='show')
            additions['show'].add(season_key)
            additions.setdefault(season_key, set())
            for episode_number in episodes:
                key = 'episode-%s-%s' % (number, episode_number)
                self.add_metadata(key, 'episode', parent=season_key,
                                  grandparent='show')
                additions[season_key].add(key)
                additions[key] = {'show'}

    def lookup_counts(self):
        return Counter(args.args[0] for args in
                       self.pms.get_metadata_details.call_args_list)

    def persisted_keys(self):
        return {args.kwargs['key_dict']['rating_key']
                for args in self.database.upsert.call_args_list}

    def test_deleted_show_episode_does_not_fetch_or_pollute_next_batch(self):
        self.enqueue({1: range(1, 101), 2: range(1, 101)})
        del self.metadata['episode-1-3']

        activity_handler.clear_recently_added_queue('show', 'Lanterns')

        self.assertEqual(activity_handler.RECENTLY_ADDED_QUEUE, {})
        self.assertEqual(self.lookup_counts(),
                         Counter({'show': 2, 'season-1': 1, 'season-2': 1}))
        self.assertEqual(self.persisted_keys(),
                         {'show', 'season-1', 'season-2'})
        self.queue.put.assert_called_once()
        previous = self.queue.put.call_args.args[0]
        self.assertEqual(len(previous['grandchild_keys']), 200)
        self.assertIn('episode-1-3', previous['grandchild_keys'])

        self.pms.get_metadata_details.reset_mock()
        self.enqueue({1: (101, 102), 2: (101, 102)})
        activity_handler.clear_recently_added_queue('show', 'Lanterns')

        current = self.queue.put.call_args.args[0]
        self.assertEqual(current['grandchild_keys'],
                         {'episode-1-101', 'episode-1-102',
                          'episode-2-101', 'episode-2-102'})
        self.assertTrue(current['grandchild_keys'].isdisjoint(
            previous['grandchild_keys']))
        self.assertEqual(activity_handler.RECENTLY_ADDED_QUEUE, {})
        self.assertEqual(self.lookup_counts(),
                         Counter({'show': 2, 'season-1': 1, 'season-2': 1}))

    def test_missing_show_season_does_not_abort_persistence_or_cleanup(self):
        self.enqueue({1: (2, 3), 2: (7, 8)})
        del self.metadata['season-2']

        activity_handler.clear_recently_added_queue('show', 'Lanterns')

        self.queue.put.assert_called_once()
        notification = self.queue.put.call_args.args[0]
        self.assertEqual(notification['child_keys'],
                         {'season-1', 'season-2'})
        self.assertEqual(self.persisted_keys(), {'show', 'season-1'})
        self.assertEqual(self.lookup_counts(),
                         Counter({'show': 2, 'season-1': 1, 'season-2': 1}))
        self.assertEqual(activity_handler.RECENTLY_ADDED_QUEUE, {})

    def test_missing_season_episode_does_not_abort_valid_item_persistence(self):
        self.config.NOTIFY_GROUP_RECENTLY_ADDED_GRANDPARENT = 0
        self.enqueue({1: (2, 3)})
        del self.metadata['episode-1-2']

        activity_handler.clear_recently_added_queue('show', 'Lanterns')

        self.queue.put.assert_called_once()
        notification = self.queue.put.call_args.args[0]
        self.assertEqual(notification['timeline_data']['rating_key'],
                         'season-1')
        self.assertEqual(notification['child_keys'],
                         {'episode-1-2', 'episode-1-3'})
        self.assertEqual(self.persisted_keys(),
                         {'season-1', 'episode-1-3'})
        self.assertEqual(self.lookup_counts(),
                         Counter({'season-1': 2, 'episode-1-2': 1,
                                  'episode-1-3': 1}))
        self.assertEqual(activity_handler.RECENTLY_ADDED_QUEUE, {})


if __name__ == '__main__':
    unittest.main()
