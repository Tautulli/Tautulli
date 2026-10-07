import pytest

from plexpy import notifiers


class FakePrettyMetadata:
    def __init__(self, parameters):
        self.parameters = parameters

    def get_image(self):
        return b'poster'


@pytest.fixture
def fake_requests(monkeypatch):
    sent = []
    responses = {}

    def make_request(self, url, method='POST', **kwargs):
        endpoint = url.rsplit('/', 1)[-1]
        sent.append(endpoint)
        return responses.get(endpoint, True)

    monkeypatch.setattr(notifiers, 'PrettyMetadata', FakePrettyMetadata)
    monkeypatch.setattr(notifiers.TELEGRAM, 'make_request', make_request)
    return sent, responses


def telegram(**config):
    return notifiers.TELEGRAM(config={'bot_token': 'token', 'chat_id': '123', 'incl_poster': 1, **config})


@pytest.mark.parametrize('photo_result', [True, False])
def test_poster_with_caption_returns_the_photo_result(fake_requests, photo_result):
    sent, responses = fake_requests
    responses['sendPhoto'] = photo_result

    result = telegram().agent_notify(subject='Subject', body='Body', parameters={'media_type': 'movie'})

    assert result is photo_result
    assert sent == ['sendPhoto']


@pytest.mark.parametrize('message_sent', [True, False])
def test_poster_with_long_text_returns_the_message_result(fake_requests, message_sent):
    sent, responses = fake_requests
    responses['sendMessage'] = message_sent

    result = telegram().agent_notify(subject='Subject', body='x' * 1100, parameters={'media_type': 'movie'})

    assert result is message_sent
    assert sent == ['sendPhoto', 'sendMessage']


@pytest.mark.parametrize('message_sent', [True, False])
def test_no_poster_returns_the_message_result(fake_requests, message_sent):
    sent, responses = fake_requests
    responses['sendMessage'] = message_sent

    result = telegram(incl_poster=0).agent_notify(subject='Subject', body='Body', parameters={'media_type': 'movie'})

    assert result is message_sent
    assert sent == ['sendMessage']
