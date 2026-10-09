#!/usr/bin/env python3
"""Write python3-requirements.json for cryptography and pyopenssl.

Tautulli vendors its other dependencies in lib/. The two versions come from
package/requirements-package.txt, the same pins the installers use.
Change them there, then run this script.
It resolves one wheel set per architecture with pip, looks up each file URL on PyPI,
and writes sha256-pinned sources for every resolved package. Requires network access.
"""
import json
import re
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

ARCHES = ('x86_64', 'aarch64')
HERE = Path(__file__).resolve().parent
PACKAGE_REQS = HERE.parent / 'requirements-package.txt'
NAMES = ('cryptography', 'pyopenssl')
REQS = [line.strip() for line in PACKAGE_REQS.read_text().splitlines()
        if line.strip().split('==')[0].lower() in NAMES]


def resolve(arch, reqs, dest):
    cmd = [sys.executable, '-m', 'pip', 'download', '-q', '--python-version', '3.13',
           '--implementation', 'cp', '--only-binary=:all:', '-d', dest]
    for tag in ('manylinux_2_28', 'manylinux2014', 'manylinux_2_17'):
        cmd += ['--platform', f'{tag}_{arch}']
    subprocess.run(cmd + reqs, check=True)
    return sorted(Path(dest).iterdir())


def source(filename, only_arch=None):
    name, version = re.match(r'([^-]+)-([^-]+)', filename.removesuffix('.tar.gz')).groups()
    with urllib.request.urlopen(f'https://pypi.org/pypi/{name.replace("_", "-")}/{version}/json') as r:
        files = json.load(r)['urls']
    f = next(f for f in files if f['filename'] == filename)
    src = {'type': 'file', 'url': f['url'], 'sha256': f['digests']['sha256']}
    if only_arch:
        src['only-arches'] = [only_arch]
    return src


def main():
    assert len(REQS) == len(NAMES), f'Pin {NAMES} in {PACKAGE_REQS}'
    seen = {}
    for arch in ARCHES:
        with tempfile.TemporaryDirectory() as tmp:
            for path in resolve(arch, REQS, tmp):
                seen.setdefault(path.name, []).append(arch)
    sources = [source(name, None if len(arches) == len(ARCHES) else arches[0])
               for name, arches in sorted(seen.items())]
    pins = sorted({'==' .join(re.match(r'([^-]+)-([^-]+)', n).groups()) for n in seen})
    module = {
        'name': 'python3-requirements',
        'buildsystem': 'simple',
        'build-commands': [
            'pip3 install --exists-action=i --no-index --find-links="file://${PWD}" '
            '--prefix=${FLATPAK_DEST} ' + ' '.join(pins),
        ],
        'sources': sources,
    }
    (HERE / 'python3-requirements.json').write_text(json.dumps(module, indent=4) + '\n')


if __name__ == '__main__':
    main()
