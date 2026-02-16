"""Thin facade — delegates to the platform-specific text injector."""

from voice_app.services.platform import get_text_injector

_injector = get_text_injector()


def inject_text(text, preserve_clipboard=True, target_hwnd=None):
    """Inject *text* into the focused window.

    On Windows *target_hwnd* is a Win32 HWND used to detect terminal vs GUI.
    On other platforms it is an opaque window identifier (pid, xdotool id, etc.).
    """
    _injector.inject_text(
        text,
        target_window_id=target_hwnd,
        preserve_clipboard=preserve_clipboard,
    )
