# -*- mode: python ; coding: utf-8 -*-

import sys
sys.modules['FixTk'] = None

block_cipher = None

analysis = Analysis(
    ['..\\Tautulli.py'],
    pathex=['lib'],
    datas=[
        ('..\\data', 'data'),
        ('..\\CHANGELOG.md', '.'),
        ('..\\LICENSE', '.'),
        ('..\\version.txt', '.'),
        ('..\\lib\\ipwhois\\data', 'data')
    ],
    excludes=['FixTk', 'tcl', 'tk', '_tkinter', 'tkinter', 'Tkinter'],
    hiddenimports=['chroot.ssl'],
    cipher=block_cipher,
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
