"""Write the generated doc pages. npm runs this before start and build.

docs/api-reference.md comes from the API docstrings in plexpy/api2.py and
plexpy/webserve.py, through the generator behind the docs_md API command.

docs/exporter-guide.md is docs/_exporter-guide.md with the field tables from
build_export_docs() in plexpy/exporter.py, the generator behind /exporter_docs.
The tables replace the marker line.

Both use the libraries bundled in lib/. Neither needs a running Tautulli,
a config, or a database.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DOCS = os.path.join(HERE, 'docs')
sys.path[:0] = [ROOT, os.path.join(ROOT, 'lib')]
sys.dont_write_bytecode = True

from plexpy import exporter  # noqa: E402
from plexpy.api2 import API2  # noqa: E402

EXPORTER_MARKER = ('<!-- generate-docs.py replaces this line with the field tables '
                   'from build_export_docs() in plexpy/exporter.py. -->')

# Today there are 123 API commands and 24 field tables. A count far below
# that means an import or a generator broke, so fail the build.
MIN_COMMANDS = 100
MIN_FIELD_TABLES = 20


def fail(message):
    sys.exit('generate-docs.py: ' + message)


def write(name, text, count, unit):
    with open(os.path.join(DOCS, name), 'w', encoding='utf-8', newline='\n') as f:
        f.write(text)
    print('generate-docs.py: wrote docs/%s with %d %s.' % (name, count, unit))


api = API2()
commands = len(api._api_docs())
if commands < MIN_COMMANDS:
    fail('found %d API commands, expected at least %d.' % (commands, MIN_COMMANDS))
body = api._api_make_md().removeprefix('<pre>').removesuffix('</pre>')
write('api-reference.md', '---\ntitle: Tautulli API Reference\nsidebar_position: 12\n---\n\n' + body,
      commands, 'API commands')

# build_export_docs() escapes < and > for the <pre> page at /exporter_docs.
fields = exporter.build_export_docs().replace('&lt;', '<').replace('&gt;', '>')
tables = fields.count('<details>')
if tables < MIN_FIELD_TABLES:
    fail('build_export_docs() gave %d field tables, expected at least %d.' % (tables, MIN_FIELD_TABLES))

with open(os.path.join(DOCS, '_exporter-guide.md'), encoding='utf-8') as f:
    prose = f.read()
if prose.split('\n').count(EXPORTER_MARKER) != 1:
    fail('docs/_exporter-guide.md must hold the marker line exactly once: ' + EXPORTER_MARKER)
write('exporter-guide.md', prose.replace(EXPORTER_MARKER, fields), tables, 'field tables')
