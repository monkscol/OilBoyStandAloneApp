# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['oilboy_standalone_app.py'],
    pathex=[],
    binaries=[],
    datas=[('OilBoy_software logo.png', '.'), ('oilboy_config.json', '.'), ('SBAccess.py', '.'), ('BaseDecoder.py', '.'), ('ByteUtil.py', '.'), ('CMetadataLib.py', '.'), ('CSBPoint.py', '.')],
    hiddenimports=['PIL', 'PIL._imaging', 'PIL._imagingtk', 'PIL.Image', 'PIL.ImageTk', 'bleak', 'bleak.backends', 'bleak.backends.winrt', 'bleak.backends.winrt.scanner', 'bleak.backends.winrt.client', 'bleak.backends.winrt.characteristic', 'bleak.backends.winrt.service', 'bleak.backends.winrt.descriptor', 'asyncio', 'asyncio.windows_events', 'asyncio.windows_utils', 'asyncio.selector_events', 'asyncio.proactor_events', 'asyncio.base_events', 'asyncio.futures', 'asyncio.tasks', 'winrt', 'winrt.windows.devices.bluetooth', 'winrt.windows.devices.bluetooth.genericattributeprofile', 'winrt.windows.devices.enumeration', 'winrt.windows.foundation', 'winrt.windows.storage.streams'],
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
    name='OilBoy_Standalone_Controller',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['oilboy_icon.ico'],
)
