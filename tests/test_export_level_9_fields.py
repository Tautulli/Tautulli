"""The export level map puts a field at Level 9 or lower exactly when a Level 9 export has it.

Level 9 leaves out the *File image fields, and shows and artists have no media
info levels. The map gave those fields Level 9 anyway. With Level 9 selected,
the export modal disabled them as custom fields, and the docs ticked them.
"""

import html

import pytest

from plexpy import exporter, helpers


@pytest.mark.parametrize('media_type', exporter.Export.MEDIA_TYPES)
def test_level_9_exports_exactly_the_fields_mapped_to_level_9(media_type):
    export = exporter.Export(metadata_level=9, media_info_level=9)
    exported = export._get_export_attrs(media_type)
    metadata_map, media_info_map = export.return_attrs_level_map(media_type)

    wrong = []
    for field, level in {**metadata_map, **media_info_map}.items():
        try:
            helpers.get_by_path(exported, field.split('.'))
            in_export = True
        except KeyError:
            in_export = False
        if in_export != (level <= 9):
            wrong.append(field)

    assert wrong == []


def test_level_9_leaves_custom_fields_selectable():
    # The modal disables every field at or below the selected level.
    season = exporter.get_custom_fields('season')['metadata_fields']
    show = exporter.get_custom_fields('show')['media_info_fields']

    assert {'field': 'episodes.thumbFile', 'level': 10} in season
    assert {'field': 'locations', 'level': 10} in show


def test_docs_leave_level_9_unticked_for_fields_it_leaves_out():
    docs = html.unescape(exporter.build_export_docs())
    sections = dict(s.split('\n', 1) for s in docs.split('### ')[1:])

    assert '| `thumbFile` |  |  |  |  |  |' in sections['Episodes']
    assert '| `locations` |  |  |  |  |  |' in sections['Shows']
