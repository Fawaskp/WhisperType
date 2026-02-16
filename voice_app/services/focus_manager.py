"""Thin facade — delegates to the platform-specific focus manager."""

from voice_app.services.platform import get_focus_manager


class FocusManager:
    def __init__(self):
        self._impl = get_focus_manager()

    def save_focus(self):
        self._impl.save_focus()

    def restore_focus(self):
        return self._impl.restore_focus()

    @property
    def saved_hwnd(self):
        """Legacy name kept for compatibility with main.py."""
        return self._impl.saved_window_id
