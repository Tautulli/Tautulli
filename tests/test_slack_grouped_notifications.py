"""Slack payload limits for grouped Recently Added episode summaries.

Run with: PYTHONPATH=lib python3 -m unittest discover -s tests -p 'test_slack*' -v
"""

from types import SimpleNamespace
import unittest
from unittest.mock import patch

import plexpy
from plexpy import notification_handler, notifiers


class SlackGroupedNotificationsTest(unittest.TestCase):
    def setUp(self):
        config = patch.object(plexpy, 'CONFIG', SimpleNamespace(NOTIFY_TEXT_EVAL=0))
        config.start()
        self.addCleanup(config.stop)

    def parameters(self, episode_count=650):
        season = {'rating_key': 'season-1', 'media_type': 'season',
                  'full_title': 'Lanterns - Season 1', 'title': 'Season 1',
                  'media_index': '1'}
        episodes = {
            str(number): {'parent_rating_key': 'season-1', 'media_index': str(number)}
            for number in range(1, episode_count * 2, 2)
        }
        grouped_title = notification_handler.format_grouped_tv_title(season, episodes, {})
        return {'media_type': 'season', 'action': 'created',
                'title': 'Lanterns - Season 1', 'grouped_title': grouped_title,
                'show_name': 'Lanterns', 'season_name': 'Season 1',
                'poster_url': 'https://example.invalid/poster.png',
                'plex_url': 'https://example.invalid/library/season-1',
                'summary': 'A show about two Green Lanterns.',
                'server_name': 'Example Server'}

    def payload(self, parameters, **config):
        settings = {'hook': 'https://example.invalid/webhook',
                    'incl_card': 1, 'tv_provider': 'plexweb'}
        settings.update(config)
        slack = notifiers.SLACK(settings)
        subject, body, _ = notification_handler.build_notify_text(
            subject='Server: {server_name}', body='{title} was added to Plex.',
            parameters=parameters, notify_action='on_created', agent_id=14)
        with patch.object(slack, 'make_request', return_value=True) as send:
            self.assertTrue(slack.agent_notify(subject, body, 'created', parameters=parameters))
        send.assert_called_once()
        return send.call_args.kwargs['json'], subject + '\n' + body

    def test_large_episode_batches_fit_card_limits_and_keep_full_message(self):
        parameters = self.parameters()
        original = parameters.copy()
        self.assertGreater(len(parameters['grouped_title']), 3000)
        for thumbnail in (0, 1):
            for provider in ('', 'plexweb'):
                for description in (0, 1):
                    with self.subTest(thumbnail=thumbnail, provider=provider, description=description):
                        payload, full_message = self.payload(
                            parameters, incl_thumbnail=thumbnail, tv_provider=provider,
                            incl_description=description)
                        self.assertEqual(payload['text'], full_message)
                        self.assertIn(parameters['grouped_title'], payload['text'])
                        self.assertIn('1295, 1297, 1299 was added to Plex.', payload['text'])
                        self.assertLess(len(payload['text']), 40000)
                        blocks = payload['attachments'][0]['blocks']
                        section = blocks[0]
                        title_text = section['text']['text'].split('\n', 1)[0]
                        self.assertLessEqual(len(section['text']['text']), 3000)
                        if provider:
                            self.assertTrue(title_text.startswith('*<' + parameters['plex_url'] + '|'))
                            self.assertTrue(title_text.endswith('...>*'))
                        else:
                            self.assertTrue(title_text.startswith('*Lanterns - Season 1 - Episodes'))
                            self.assertTrue(title_text.endswith('...*'))
                        image = section['accessory'] if thumbnail else blocks[-1]
                        self.assertEqual(len(image['alt_text']), 2000)
                        self.assertTrue(image['alt_text'].endswith('...'))
                        self.assertEqual(image['image_url'], parameters['poster_url'])
        self.assertEqual(parameters, original)

    def test_long_description_is_shortened_after_the_complete_link_heading(self):
        parameters = self.parameters(3)
        parameters['summary'] = 'Description ' * 1000
        payload, full_message = self.payload(parameters)
        section_text = payload['attachments'][0]['blocks'][0]['text']['text']
        heading = '*<%s|%s>*' % (parameters['plex_url'], parameters['grouped_title'])
        self.assertEqual(len(section_text), 3000)
        self.assertTrue(section_text.startswith(heading + '\nDescription '))
        self.assertTrue(section_text.endswith('...'))
        self.assertEqual(payload['text'], full_message)

    def test_long_provider_link_budget_includes_complete_markup(self):
        parameters = self.parameters()
        parameters['plex_url'] = 'https://example.invalid/' + 'a' * 1500
        payload, full_message = self.payload(parameters)
        blocks = payload['attachments'][0]['blocks']
        section_text = blocks[0]['text']['text']
        self.assertEqual(len(section_text), 3000)
        self.assertTrue(section_text.startswith('*<' + parameters['plex_url'] + '|'))
        self.assertTrue(section_text.endswith('...>*'))
        self.assertNotIn('\n', section_text)
        self.assertEqual(payload['text'], full_message)
        link_field = next(field['text'] for field in blocks[1]['fields']
                          if field['text'].startswith('<'))
        self.assertEqual(link_field, '<%s|Plex Web>' % parameters['plex_url'])
        self.assertLessEqual(len(link_field), 2000)

    def test_provider_link_that_cannot_fit_falls_back_to_plain_heading(self):
        parameters = self.parameters()
        parameters['plex_url'] = 'https://example.invalid/' + 'a' * 3000
        payload, full_message = self.payload(parameters, incl_description=0, incl_pmslink=1)
        blocks = payload['attachments'][0]['blocks']
        section_text = blocks[0]['text']['text']
        self.assertTrue(section_text.startswith('*Lanterns - Season 1 - Episodes'))
        self.assertTrue(section_text.endswith('...*'))
        self.assertLessEqual(len(section_text), 3000)
        self.assertEqual([block['type'] for block in blocks], ['section', 'image'])
        self.assertEqual(payload['text'], full_message)

    def test_small_grouped_card_keeps_original_title_description_and_links(self):
        parameters = self.parameters(3)
        payload, full_message = self.payload(parameters, incl_thumbnail=1)
        section = payload['attachments'][0]['blocks'][0]
        self.assertEqual(section['text']['text'],
                         '*<%s|%s>*\n%s' % (parameters['plex_url'],
                                            parameters['grouped_title'], parameters['summary']))
        self.assertEqual(section['accessory']['alt_text'], parameters['grouped_title'])
        self.assertEqual(payload['text'], full_message)

    def test_title_at_image_limit_is_not_shortened(self):
        parameters = self.parameters(3)
        for length in (2000, 2001):
            with self.subTest(length=length):
                parameters['grouped_title'] = 'x' * length
                payload, _ = self.payload(parameters, incl_thumbnail=1)
                alt_text = payload['attachments'][0]['blocks'][0]['accessory']['alt_text']
                self.assertEqual(len(alt_text), 2000)
                self.assertEqual(alt_text, 'x' * 2000 if length == 2000 else 'x' * 1997 + '...')

    def test_large_message_without_card_retains_all_episode_details(self):
        parameters = self.parameters()
        payload, full_message = self.payload(parameters, incl_card=0)
        self.assertEqual(payload, {'text': full_message})
        self.assertIn(parameters['grouped_title'], payload['text'])

    def test_ordinary_movie_card_keeps_original_format(self):
        parameters = self.parameters(3)
        parameters.update({'media_type': 'movie', 'title': 'A Movie', 'year': 2026,
                           'grouped_title': '', 'summary': 'A short movie summary.'})
        payload, full_message = self.payload(parameters, movie_provider='plexweb')
        blocks = payload['attachments'][0]['blocks']
        self.assertEqual(blocks[0]['text']['text'],
                         '*<%s|A Movie (2026)>*\nA short movie summary.' % parameters['plex_url'])
        self.assertEqual(blocks[-1]['alt_text'], 'A Movie (2026)')
        self.assertEqual(payload['text'], full_message)


if __name__ == '__main__':
    unittest.main()
