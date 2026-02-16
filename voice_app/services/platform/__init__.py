"""Platform detection and factory functions.

Import helpers from here — never import platform adapters directly.
"""

import sys

from .base import (
    PlatformFocusManager,
    PlatformTextInjector,
    PlatformHotkeyManager,
    PlatformSoundPlayer,
)


def _platform():
    if sys.platform == "win32":
        return "windows"
    if sys.platform == "darwin":
        return "macos"
    return "linux"


def get_focus_manager() -> PlatformFocusManager:
    plat = _platform()
    if plat == "windows":
        from .windows import WindowsFocusManager
        return WindowsFocusManager()
    if plat == "macos":
        from .macos import MacOSFocusManager
        return MacOSFocusManager()
    from .linux import LinuxFocusManager
    return LinuxFocusManager()


def get_text_injector() -> PlatformTextInjector:
    plat = _platform()
    if plat == "windows":
        from .windows import WindowsTextInjector
        return WindowsTextInjector()
    if plat == "macos":
        from .macos import MacOSTextInjector
        return MacOSTextInjector()
    from .linux import LinuxTextInjector
    return LinuxTextInjector()


def get_hotkey_manager() -> PlatformHotkeyManager:
    plat = _platform()
    if plat == "windows":
        from .windows import WindowsHotkeyManager
        return WindowsHotkeyManager()
    if plat == "macos":
        from .macos import MacOSHotkeyManager
        return MacOSHotkeyManager()
    from .linux import LinuxHotkeyManager
    return LinuxHotkeyManager()


def get_sound_player() -> PlatformSoundPlayer:
    from ._sound import CrossPlatformSoundPlayer
    return CrossPlatformSoundPlayer()
