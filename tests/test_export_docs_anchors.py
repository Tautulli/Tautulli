"""Every link in the exporter docs points at a heading or an id in the docs.

GitHub makes a heading anchor from the lowercase text with spaces as dashes.
"""

import html
import re

from plexpy import exporter

# The wiki page has this heading above the generated docs.
WIKI_ANCHORS = {'resource-exports'}


def test_every_docs_link_has_a_target():
    docs = html.unescape(exporter.build_export_docs())
    headings = {h.lower().replace(' ', '-') for h in re.findall(r'^### (.+)$', docs, re.M)}
    ids = set(re.findall(r'<a id="([^"]+)">', docs))
    links = set(re.findall(r'\]\(#([^)]+)\)', docs))

    assert links - headings - ids - WIKI_ANCHORS == set()
    assert {'photo-albums', 'collection-item', 'playlist-item'} <= links


def test_child_links_match_their_title_and_section():
    docs = html.unescape(exporter.build_export_docs())
    for section in docs.split('### ')[1:]:
        heading, body = section.split('\n', 1)
        for title, anchor in re.findall(r'Includes \[([^\]]+)\]\(#([^)]+)\)', body):
            if title == 'Items':
                # Items link to the note under their own section.
                assert anchor == heading.lower().rstrip('s') + '-item'
            else:
                assert anchor == title.lower().replace(' ', '-')
