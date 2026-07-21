# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from PyInstaller.utils.hooks import collect_submodules

# Get project root directory
project_root = os.path.abspath(".")

# Analyze dependencies
a = Analysis(
    ['cli.py'],
    pathex=[project_root],
    binaries=[],
    datas=[
        ('whisper', 'whisper'),
        ('utils', 'utils'),
        ('youtube', 'youtube'),
    ],
    hiddenimports=[
        # Core dependencies
        *collect_submodules('yt_dlp'),
        'deepgram',
        'dotenv',

        # Async related
        'asyncio',
        'logging',
        'tempfile',
        'enum',
        'typing',

        # Network requests
        'requests',
        'urllib3',
        'certifi',

        # File processing
        'zipfile',
        'tarfile',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    macosx_rpath=False,
    cipher=None,
)

# Create executable
pyz = PYZ(a.pure, a.zipped_data, cipher=None)

# Build EXE (onefile mode)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='yt-whisper',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    icon=None  # Optional: add icon file
)
