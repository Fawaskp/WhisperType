"""macOS platform adapter — PyObjC + pynput."""

import subprocess
import sys
import time

from .base import PlatformFocusManager, PlatformTextInjector, PlatformHotkeyManager


class MacOSFocusManager(PlatformFocusManager):
    """Save/restore the frontmost application on macOS via NSWorkspace."""

    def __init__(self):
        self._saved_app = None  # NSRunningApplication

    def save_focus(self):
        try:
            from AppKit import NSWorkspace
            self._saved_app = NSWorkspace.sharedWorkspace().frontmostApplication()
        except Exception:
            self._saved_app = None

    def restore_focus(self):
        app = self._saved_app
        if app is None:
            return False
        try:
            from AppKit import NSApplicationActivateIgnoringOtherApps
            return app.activateWithOptions_(NSApplicationActivateIgnoringOtherApps)
        except Exception:
            return False

    @property
    def saved_window_id(self):
        if self._saved_app is None:
            return None
        return self._saved_app.processIdentifier()


class MacOSTextInjector(PlatformTextInjector):
    """Paste text via clipboard + Cmd+V on macOS."""

    def inject_text(self, text, target_window_id=None, preserve_clipboard=True):
        import pyperclip

        old_clipboard = None
        if preserve_clipboard:
            try:
                old_clipboard = pyperclip.paste()
            except Exception:
                pass

        pyperclip.copy(text)
        time.sleep(0.05)

        # Simulate Cmd+V via pynput
        from pynput.keyboard import Controller, Key
        kb = Controller()
        kb.press(Key.cmd)
        kb.press("v")
        kb.release("v")
        kb.release(Key.cmd)
        time.sleep(0.05)

        if preserve_clipboard and old_clipboard is not None:
            time.sleep(0.2)
            try:
                pyperclip.copy(old_clipboard)
            except Exception:
                pass


class MacOSHotkeyManager(PlatformHotkeyManager):
    """Global hotkeys via pynput on macOS.

    Notes:
    - Requires Accessibility permissions (System Settings > Privacy).
    - On first run, macOS will prompt the user to grant access.
    - Hotkey suppression is not supported by pynput; keystrokes may
      briefly appear in the focused app.
    """

    def __init__(self):
        self._listeners = []
        self._check_accessibility()

    @staticmethod
    def _check_accessibility():
        """Warn if Accessibility permission has not been granted."""
        try:
            from ApplicationServices import AXIsProcessTrusted
            if not AXIsProcessTrusted():
                print(
                    "[WhisperType] Accessibility permission required.\n"
                    "  Go to: System Settings > Privacy & Security > Accessibility\n"
                    "  and grant access to this application.",
                    file=sys.stderr,
                )
        except ImportError:
            pass

    def register(self, hotkey_str, callback, *, suppress=True):
        from pynput import keyboard

        combo = self._parse_hotkey(hotkey_str)

        def on_activate():
            callback()

        listener = keyboard.GlobalHotKeys({combo: on_activate})
        listener.daemon = True
        listener.start()
        self._listeners.append(listener)

    def unregister_all(self):
        for listener in self._listeners:
            listener.stop()
        self._listeners.clear()

    @staticmethod
    def _parse_hotkey(hotkey_str):
        """Convert WhisperType hotkey string to pynput format.

        e.g. 'ctrl+shift+space' → '<ctrl>+<shift>+<space>'
             'escape' → '<esc>'
        """
        # Map ctrl → cmd on macOS for the primary hotkey
        parts = [p.strip().lower() for p in hotkey_str.split("+")]
        mapped = []
        for p in parts:
            if p == "ctrl":
                mapped.append("<cmd>")
            elif p == "shift":
                mapped.append("<shift>")
            elif p == "alt":
                mapped.append("<alt>")
            elif p == "escape":
                mapped.append("<esc>")
            elif p == "space":
                mapped.append("<space>")
            elif len(p) == 1:
                mapped.append(p)
            else:
                mapped.append(f"<{p}>")
        return "+".join(mapped)
