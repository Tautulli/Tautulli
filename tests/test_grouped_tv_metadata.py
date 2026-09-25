"""Exercise grouped TV metadata loading through Plex's children XML parser."""

import unittest
from unittest.mock import Mock, call
from xml.dom.minidom import parseString

from plexpy import notification_handler, pmsconnect


def children_xml(*items):
    """Build a minimal Plex children response without detailed media fields."""
    return parseString('<MediaContainer size="%s">%s</MediaContainer>'
                       % (len(items), ''.join(items)))


class GroupedTVMetadataTest(unittest.TestCase):
    def setUp(self):
        # Keep the production XML parsing path, replacing only HTTP transport.
        self.pms = pmsconnect.PmsConnect.__new__(pmsconnect.PmsConnect)
        self.pms.request_handler = Mock()
        self.responses = {}
        self.pms.request_handler.make_request.side_effect = self.response

    def response(self, uri, request_type, output_format):
        self.assertEqual(request_type, 'GET')
        self.assertEqual(output_format, 'xml')
        return self.responses[uri]

    def add_listing(self, rating_key, *items):
        self.responses['/library/metadata/%s/children' % rating_key] = (
            children_xml(*items))

    def request(self, rating_key):
        return call(uri='/library/metadata/%s/children' % rating_key,
                    request_type='GET', output_format='xml')

    def test_season_loads_only_queued_episodes_in_one_request(self):
        self.add_listing(
            '10',
            '<Video type="episode" ratingKey="102" index="2" '
            'parentRatingKey="10"/>',
            '<Video type="episode" ratingKey="107" index="7"/>',
            '<Video type="episode" ratingKey="199" index="99" '
            'parentRatingKey="10"/>')

        children, grandchildren = notification_handler.get_grouped_tv_metadata(
            self.pms, 10, 'season', [102, '107', '108'], [])

        self.assertEqual(set(children), {'102', '107', '108'})
        self.assertEqual(children['102']['media_index'], '2')
        self.assertEqual(children['107']['media_index'], '7')
        self.assertEqual(children['107']['parent_rating_key'], '10')
        self.assertEqual(children['107']['media_type'], 'episode')
        self.assertEqual(children['108'], {})
        self.assertEqual(grandchildren, {})
        self.assertEqual(self.pms.request_handler.make_request.call_args_list,
                         [self.request('10')])

    def test_conflicting_parent_and_wrong_media_type_stay_missing(self):
        self.add_listing(
            '10',
            '<Video type="episode" ratingKey="101" index="1" '
            'parentRatingKey="wrong-season"/>',
            '<Video type="movie" ratingKey="102" index="2" '
            'parentRatingKey="10"/>',
            '<Video type="episode" ratingKey="103" index="3" '
            'parentRatingKey="10"/>')

        children, _ = notification_handler.get_grouped_tv_metadata(
            self.pms, '10', 'season', ['101', '102', '103'], [])

        self.assertEqual(children['101'], {})
        self.assertEqual(children['102'], {})
        self.assertEqual(children['103']['media_index'], '3')
        self.assertEqual(self.pms.request_handler.make_request.call_count, 1)

    def test_show_queries_queued_season_missing_from_show_listing(self):
        self.add_listing(
            '1',
            '<Directory type="season" ratingKey="10" index="1" '
            'title="Season 1"/>',
            '<Directory type="season" ratingKey="30" index="3" '
            'parentRatingKey="1"/>')
        self.add_listing(
            '10',
            '<Video type="episode" ratingKey="102" index="2"/>',
            '<Video type="episode" ratingKey="109" index="9"/>')
        self.add_listing(
            '20',
            '<Video type="episode" ratingKey="207" index="7" '
            'parentIndex="2" parentTitle="Season 2"/>')

        children, grandchildren = notification_handler.get_grouped_tv_metadata(
            self.pms, '1', 'show', ['20', '10'], ['102', '207', '208'])

        self.assertEqual(set(children), {'10', '20'})
        self.assertEqual(children['10']['media_index'], '1')
        self.assertEqual(children['10']['parent_rating_key'], '1')
        self.assertEqual(children['20'], {})
        self.assertEqual(set(grandchildren), {'102', '207', '208'})
        self.assertEqual(grandchildren['102']['parent_rating_key'], '10')
        self.assertEqual(grandchildren['207']['parent_rating_key'], '20')
        self.assertEqual(grandchildren['207']['parent_media_index'], '2')
        self.assertEqual(grandchildren['207']['parent_title'], 'Season 2')
        self.assertEqual(grandchildren['208'], {})
        self.assertEqual(self.pms.request_handler.make_request.call_args_list,
                         [self.request('1'), self.request('10'),
                          self.request('20')])

    def test_show_rejects_seasons_with_wrong_parent_or_type(self):
        self.add_listing(
            '1',
            '<Directory type="season" ratingKey="10" index="1" '
            'parentRatingKey="another-show"/>',
            '<Video type="episode" ratingKey="20" index="2" '
            'parentRatingKey="1"/>')
        self.add_listing('10')
        self.add_listing('20')

        children, grandchildren = notification_handler.get_grouped_tv_metadata(
            self.pms, '1', 'show', ['10', '20'], ['101'])

        self.assertEqual(children, {'10': {}, '20': {}})
        self.assertEqual(grandchildren, {'101': {}})
        self.assertEqual(self.pms.request_handler.make_request.call_args_list,
                         [self.request('1'), self.request('10'),
                          self.request('20')])

    def test_failed_children_response_preserves_missing_batch_entries(self):
        self.responses['/library/metadata/10/children'] = None

        children, grandchildren = notification_handler.get_grouped_tv_metadata(
            self.pms, '10', 'season', ['101', '102'], [])

        self.assertEqual(children, {'101': {}, '102': {}})
        self.assertEqual(grandchildren, {})
        self.assertEqual(self.pms.request_handler.make_request.call_count, 1)

    def test_large_batch_request_count_depends_on_seasons_not_episodes(self):
        self.add_listing(
            '1',
            '<Directory type="season" ratingKey="10" index="1"/>',
            '<Directory type="season" ratingKey="20" index="2"/>')
        episode_keys = []
        for season_key in ('10', '20'):
            items = []
            for number in range(1, 101):
                key = '%s-%s' % (season_key, number)
                episode_keys.append(key)
                items.append('<Video type="episode" ratingKey="%s" '
                             'index="%s"/>' % (key, number))
            self.add_listing(season_key, *items)

        children, grandchildren = notification_handler.get_grouped_tv_metadata(
            self.pms, '1', 'show', ['10', '20'], episode_keys)

        self.assertEqual(len(children), 2)
        self.assertEqual(len(grandchildren), 200)
        self.assertTrue(all(grandchildren.values()))
        self.assertEqual(grandchildren['10-100']['media_index'], '100')
        self.assertEqual(grandchildren['20-100']['parent_rating_key'], '20')
        self.assertEqual(self.pms.request_handler.make_request.call_args_list,
                         [self.request('1'), self.request('10'),
                          self.request('20')])


if __name__ == '__main__':
    unittest.main()
