"""Page templates list notifiers without the notify_log join.

The join visits every notify_log row. It took about 5 s on a large database.
"""

import re
from pathlib import Path

import pytest

from plexpy import notifiers

TEMPLATES = Path(__file__).resolve().parent.parent / "data/interfaces/default"


@pytest.mark.parametrize("template", ["info.html", "newsletter_config.html"])
def test_template_skips_the_notify_log_join(template):
    source = (TEMPLATES / template).read_text(encoding="utf-8")
    assert re.findall(r"notifiers\.get_notifiers\((.*?)\)", source) == ["include_last_triggered=False"]


def test_query_without_the_join_has_the_fields_the_templates_read(app_db):
    app_db.action("INSERT INTO notifiers (agent_id, agent_name, agent_label, friendly_name) "
                  "VALUES (10, 'email', 'Email', 'Mine')")

    (row,) = notifiers.get_notifiers(include_last_triggered=False)

    assert (row["id"], row["agent_name"], row["agent_label"], row["friendly_name"]) == (1, "email", "Email", "Mine")
