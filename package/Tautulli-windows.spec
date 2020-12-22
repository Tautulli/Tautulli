# -*- mode: python ; coding: utf-8 -*-

import sys
sys.modules['FixTk'] = None

excludes = ['FixTk', 'tcl', 'tk', '_tkinter', 'tkinter', 'Tkinter']
block_cipher = None

analysis = Analysis(
    ['..\\Tautulli.py'],
    pathex=['lib'],
    datas=[
        ('..\\data', 'data'),
        ('..\\CHANGELOG.md', '.'),
        ('..\\LICENSE', '.'),
        ('..\\branch.txt', '.'),
        ('..\\version.txt', '.'),
        ('..\\lib\\ipwhois\\data', 'data'),
        ('TautulliUpdateTask.xml', '.')
    ],
    excludes=excludes,
    hiddenimports=['pkg_resources.py2_warn', 'cheroot.ssl', 'cheroot.ssl.builtin'],
    cipher=block_cipher
)
updater_analysis = Analysis(
    ['updater-windows.py'],
    pathex=['lib'],
    excludes=excludes,
    cipher=block_cipher
)

MERGE(
    (analysis, 'Tautulli', 'Tautulli'),
    (updater_analysis, 'updater', 'updater')
)

pyz = PYZ(
    analysis.pure,
    analysis.zipped_data,
    cipher=block_cipher
)
exe = EXE(
    pyz,
    analysis.scripts,
    exclude_binaries=True,
    name='Tautulli',
    console=False,
    icon='..\\data\\interfaces\\default\\images\\logo-circle.ico'
)
coll = COLLECT(
    exe,
    analysis.binaries,
    analysis.zipfiles,
    analysis.datas,
    name='Tautulli'
)

updater_pyz = PYZ(
    updater_analysis.pure,
    updater_analysis.zipped_data,
    cipher=block_cipher
)
updater_exe = EXE(
    updater_pyz,
    updater_analysis.scripts,
    exclude_binaries=True,
    name='updater',
    console=False,
    icon='..\\data\\interfaces\\default\\images\\logo-circle.ico'
)
coll = COLLECT(
    updater_exe,
    updater_analysis.binaries,
    updater_analysis.zipfiles,
    updater_analysis.datas,
    name='updater'
)
