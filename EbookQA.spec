# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import copy_metadata

datas = [('app.py', '.'), ('agents', 'agents'), ('api', 'api'), ('models', 'models'), ('utils', 'utils')]
datas += copy_metadata('streamlit')
datas += copy_metadata('click')
datas += copy_metadata('protobuf')
datas += copy_metadata('watchdog')
datas += copy_metadata('altair')
datas += copy_metadata('blinker')
datas += copy_metadata('cachetools')
datas += copy_metadata('tornado')
datas += copy_metadata('pandas')
datas += copy_metadata('numpy')


a = Analysis(
    ['launcher.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=['watchdog.observers', 'google.protobuf'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='EbookQA',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
