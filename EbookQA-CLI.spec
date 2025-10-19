# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main_cli.py'],
    pathex=['.', '.\\api', '.\\agents', '.\\models', '.\\utils'],
    binaries=[],
    datas=[],
    hiddenimports=['jiter', 'jiter.jiter', 'pydantic_core', 'pydantic_core._pydantic_core'],
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
    name='EbookQA-CLI',
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
