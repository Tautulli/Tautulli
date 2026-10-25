"""A newsletter saves under its configured filename in the newsletter folder.

A filename that resolves outside the folder falls back to the default name.
"""

import pytest

from plexpy import newsletters


@pytest.fixture
def newsletter_dir(app_db, app_config, tmp_path):
    app_config.NEWSLETTER_DIR = str(tmp_path / "newsletters")
    app_config.HTTP_HOST = '127.0.0.1'
    return tmp_path / "newsletters"


def build(filename):
    agent = newsletters.Newsletter(config={'filename': filename})
    agent.retrieve_data_and_build_text()
    return agent


def test_custom_filename_is_kept(newsletter_dir):
    agent = build('weekly.html')

    assert agent.filename_formatted == 'weekly.html'
    assert agent.filepath == str(newsletter_dir / 'weekly.html')


def test_filename_outside_the_folder_uses_the_default(newsletter_dir):
    agent = build('../escape.html')

    assert agent.filename_formatted == f'newsletter_{agent.uuid}.html'
    assert agent.filepath == str(newsletter_dir / agent.filename_formatted)
