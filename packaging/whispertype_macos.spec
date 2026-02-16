# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for WhisperType — macOS (.app bundle)."""

import sys
from pathlib import Path

block_cipher = None
ROOT = Path(SPECPATH).parent

a = Analysis(
    [str(ROOT / "voice_app" / "main.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[],
    hiddenimports=[
        "faster_whisper",
        "ctranslate2",
        "huggingface_hub",
        "pynput",
        "pynput.keyboard",
        "pynput.keyboard._darwin",
        "pyperclip",
        "AppKit",
        "Foundation",
        "Quartz",
        "PySide6.QtCore",
        "PySide6.QtGui",
        "PySide6.QtWidgets",
        "sounddevice",
        "numpy",
        "voice_app.services.platform.macos",
    ],
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
    upx=False,
    console=False,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name="WhisperType",
)

app = BUNDLE(
    coll,
    name="WhisperType.app",
    icon=None,
    bundle_identifier="com.whispertype.app",
    info_plist={
        "CFBundleName": "WhisperType",
        "CFBundleDisplayName": "WhisperType",
        "CFBundleVersion": "1.0.0",
        "CFBundleShortVersionString": "1.0.0",
        "NSMicrophoneUsageDescription": "WhisperType needs microphone access to record audio for transcription.",
        "NSAppleEventsUsageDescription": "WhisperType needs Accessibility access to paste text into other applications.",
    },
)
