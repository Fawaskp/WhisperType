# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for WhisperType — Linux."""

import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_all

block_cipher = None
ROOT = Path(SPECPATH).parent

pyside6_datas, pyside6_binaries, pyside6_hiddenimports = collect_all("PySide6")

a = Analysis(
    [str(ROOT / "voice_app" / "main.py")],
    pathex=[str(ROOT)],
    binaries=pyside6_binaries,
    datas=pyside6_datas + [(str(ROOT / "packaging" / "icon.png"), ".")],
    hiddenimports=[
        "faster_whisper",
        "ctranslate2",
        "huggingface_hub",
        "pynput",
        "pynput.keyboard",
        "pynput.keyboard._xorg",
        "pyperclip",
        "sounddevice",
        "numpy",
        "voice_app.services.platform.linux",
    ] + pyside6_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["torch", "torchvision", "torchaudio", "tkinter"],
    noarchive=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="WhisperType",
    debug=False,
    strip=False,
    upx=True,
    console=False,
    icon=str(ROOT / "packaging" / "icon.png"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="WhisperType",
)
