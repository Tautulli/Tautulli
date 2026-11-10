import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / 'package' / 'flatpak' / 'update-metainfo-releases.py'
spec = importlib.util.spec_from_file_location('update_metainfo_releases', SCRIPT)
script = importlib.util.module_from_spec(spec)
spec.loader.exec_module(script)


def test_parse_skips_betas_and_joins_notes():
    text = (
        '## v2.1.1 (2020-02-02)\n\n'
        '* Notes:\n'
        '  * Fix: A & B <x>.\n'
        '    * Note: More.\n'
        '  * New: &lt;show&gt; tag.\n\n'
        '## v2.1.1-beta (2020-01-02)\n\n'
        '* Other:\n'
        '  * Fix: Beta only.\n\n'
        '## v2.1 (2020-01-01)\n\n'
        '* Other:\n'
        '  * Fix: Old.\n'
    )
    assert script.parse(text) == [
        ('2.1.1', '2020-02-02', [('Notes', ['Fix: A &amp; B &lt;x&gt;. Note: More.',
                                            'New: &lt;show&gt; tag.'])]),
        ('2.1', '2020-01-01', [('Other', ['Fix: Old.'])]),
    ]


def test_metainfo_matches_changelog():
    # A new release in CHANGELOG.md fails this until package/flatpak/update-metainfo-releases.py runs.
    releases = script.parse(script.CHANGELOG.read_text(encoding='utf-8'))[:script.COUNT]
    assert script.render(releases) in script.METAINFO.read_text(encoding='utf-8')
