"""Write docs/api-reference.md from the API docstrings in plexpy/api2.py and plexpy/webserve.py.

npm runs this before start and build. It uses the generator behind the
docs_md API command and the libraries bundled in lib/, so it needs no
running Tautulli, config, or database.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path[:0] = [ROOT, os.path.join(ROOT, 'lib')]
sys.dont_write_bytecode = True

from plexpy.api2 import API2  # noqa: E402

# The API has 123 commands. A count far below that means the import or
# the docstring scan broke, so fail the build instead of publishing it.
MIN_COMMANDS = 100

api = API2()
commands = len(api._api_docs())
if commands < MIN_COMMANDS:
    sys.exit('api-reference.py: found %d API commands, expected at least %d.' % (commands, MIN_COMMANDS))

body = api._api_make_md().removeprefix('<pre>').removesuffix('</pre>')

with open(os.path.join(HERE, 'docs', 'api-reference.md'), 'w', encoding='utf-8', newline='\n') as f:
    f.write('---\ntitle: Tautulli API Reference\nsidebar_position: 12\n---\n\n' + body)

print('api-reference.py: wrote docs/api-reference.md with %d API commands.' % commands)
