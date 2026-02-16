"""Linux platform adapter — xdotool + pynput."""

import os
import shutil
import subprocess
import sys
import time

from .base import PlatformFocusManager, PlatformTextInjector, PlatformHotkeyManager


def _is_wayland():
    return os.environ.get("XDG_SESSION_TYPE", "").lower() == "wayland"


def _warn_wayland():
    if _is_wayland():
        print(
            "[WhisperType] WARNING: Wayland session detected.\n"
            "  xdotool and pynput do not fully work under Wayland.\n"
            "  For best results, switch to an X11 session or use XWayland.",
            file=sys.stderr,
        )


def _has_xdotool():
    return shutil.which("xdotool") is not None


class LinuxFocusManager(PlatformFocusManager):
    """Save/restore the active X11 window via xdotool."""

    def __init__(self):
        self._saved_wid = None
        _warn_wayland()
        if not _has_xdotool():
            print(
                "[WhisperType] WARNING: xdotool not found. "
                "Install it with: sudo apt install xdotool",
                file=sys.stderr,
            )

    def save_focus(self):
        try:
            result = subprocess.run(
                ["xdotool", "getactivewindow"],
                capture_output=True, text=True, timeout=2,
            )
            if result.returncode == 0:
                self._saved_wid = result.stdout.strip()
        except Exception:
            self._saved_wid = None

    def restore_focus(self):
        if not self._saved_wid:
            return False
        try:
            result = subprocess.run(
                ["xdotool", "windowactivate", self._saved_wid],
                capture_output=True, timeout=2,
            )
            return result.returncode == 0
        except Exception:
            return False

    @property
    def saved_window_id(self):
        return self._saved_wid


class LinuxTextInjector(PlatformTextInjector):
    """Paste text via clipboard + Ctrl+V on Linux (X11)."""

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

        is_term = self._is_terminal(target_window_id)

        from pynput.keyboard import Controller, Key
        kb = Controller()

        if is_term:
            # Most Linux terminals use Ctrl+Shift+V
            kb.press(Key.ctrl)
            kb.press(Key.shift)
            kb.press("v")
            kb.release("v")
            kb.release(Key.shift)
            kb.release(Key.ctrl)
        else:
            kb.press(Key.ctrl)
            kb.press("v")
            kb.release("v")
            kb.release(Key.ctrl)
        time.sleep(0.05)

        if preserve_clipboard and old_clipboard is not None:
            time.sleep(0.2)
            try:
                pyperclip.copy(old_clipboard)
            except Exception:
                pass

    @staticmethod
    def _is_terminal(window_id):
        """Detect if the window is a terminal by its WM_CLASS."""
        if not window_id or not _has_xdotool():
            return False
        try:
            result = subprocess.run(
                ["xdotool", "getwindowclassname", str(window_id)],
                capture_output=True, text=True, timeout=2,
            )
            if result.returncode != 0:
                return False
            cls = result.stdout.strip().lower()
            terminal_hints = [
                "gnome-terminal", "konsole", "xterm", "urxvt", "alacritty",
                "kitty", "terminator", "tilix", "sakura", "xfce4-terminal",
                "mate-terminal", "lxterminal", "st", "wezterm", "foot",
            ]
            return any(h in cls for h in terminal_hints)
        except Exception:
            return False


class LinuxHotkeyManager(PlatformHotkeyManager):
    """Global hotkeys via pynput on Linux.

    Requires X11.  On Wayland, pynput's global listener may not work.
    """

    def __init__(self):
        self._listeners = []
        _warn_wayland()

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
        """
        parts = [p.strip().lower() for p in hotkey_str.split("+")]
        mapped = []
        for p in parts:
            if p in ("ctrl", "shift", "alt", "cmd"):
                mapped.append(f"<{p}>")
            elif p == "escape":
                mapped.append("<esc>")
            elif p == "space":
                mapped.append("<space>")
            elif len(p) == 1:
                mapped.append(p)
            else:
                mapped.append(f"<{p}>")
        return "+".join(mapped)
