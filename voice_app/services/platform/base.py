"""Abstract base classes for platform-specific services."""

from abc import ABC, abstractmethod


class PlatformFocusManager(ABC):
    """Save and restore the focused window across recording sessions."""

    @abstractmethod
    def save_focus(self):
        """Capture the currently focused window."""

    @abstractmethod
    def restore_focus(self):
        """Re-activate the previously saved window. Returns True on success."""

    @property
    @abstractmethod
    def saved_window_id(self):
        """Return the opaque window identifier (hwnd, pid, window-id, etc.)."""


class PlatformTextInjector(ABC):
    """Inject transcribed text into the target window."""

    @abstractmethod
    def inject_text(self, text, target_window_id=None, preserve_clipboard=True):
        """Paste *text* into the target window (or current foreground)."""


class PlatformHotkeyManager(ABC):
    """Register and manage global hotkeys."""

    @abstractmethod
    def register(self, hotkey_str, callback, *, suppress=True):
        """Register a global hotkey. *suppress* prevents the keystroke from
        reaching the focused app (best-effort on non-Windows platforms)."""

    @abstractmethod
    def unregister_all(self):
        """Remove every registered hotkey."""

    def start_listener(self):
        """Start listening for hotkeys (no-op if always listening)."""

    def stop_listener(self):
        """Stop listening for hotkeys (no-op if managed automatically)."""


class PlatformSoundPlayer(ABC):
    """Play simple audio feedback tones."""

    @abstractmethod
    def beep(self, frequency, duration_ms):
        """Play a sine-wave beep at *frequency* Hz for *duration_ms* ms."""
