#!/usr/bin/env python3
"""Write the latest releases from CHANGELOG.md into the Flatpak metainfo.

Run it after adding a release to CHANGELOG.md and commit the metainfo with the release.
Beta releases are left out.
"""
import html
import re
import sys
from pathlib import Path
from xml.sax.saxutils import escape

HERE = Path(__file__).resolve().parent
CHANGELOG = HERE.parents[1] / 'CHANGELOG.md'
METAINFO = HERE / 'com.tautulli.Tautulli.metainfo.xml'
COUNT = 10
URL = 'https://github.com/Tautulli/Tautulli/releases/tag/v{}'


def parse(text):
    """Return [(version, date, [(section, [items])])] for stable releases, newest first."""
    releases, sections = [], None
    for line in text.splitlines():
        if line.startswith('## '):
            m = re.match(r'## v([\d.]+) \((\d{4}-\d{2}-\d{2})\)$', line)
            sections = [] if m else None
            if m:
                releases.append((m[1], m[2], sections))
            continue
        if sections is None or not line.strip():
            continue
        indent = len(line) - len(line.lstrip())
        entry = escape(html.unescape(line.strip().removeprefix('* ')))
        if indent == 0:
            sections.append((entry.rstrip(':'), []))
        elif indent == 2:
            sections[-1][1].append(entry)
        else:
            sections[-1][1][-1] += ' ' + entry
    return releases


def render(releases):
    out = ['  <releases>']
    for version, date, sections in releases:
        out += [f'    <release version="{version}" date="{date}">',
                f'      <url type="details">{URL.format(version)}</url>',
                '      <description>']
        for title, items in sections:
            out += [f'        <p>{title}</p>', '        <ul>']
            out += [f'          <li>{item}</li>' for item in items]
            out += ['        </ul>']
        out += ['      </description>', '    </release>']
    out += ['  </releases>']
    return '\n'.join(out)


def main():
    releases = parse(CHANGELOG.read_text(encoding='utf-8'))[:COUNT]
    xml, found = re.subn(r'  <releases>.*</releases>', lambda m: render(releases),
                         METAINFO.read_text(encoding='utf-8'), flags=re.S)
    if not found:
        sys.exit(f'No <releases> block in {METAINFO}')
    METAINFO.write_text(xml, encoding='utf-8')


if __name__ == '__main__':
    main()
