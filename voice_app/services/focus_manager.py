import ctypes
import ctypes.wintypes as wintypes

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32


class FocusManager:
    def __init__(self):
        self._saved_hwnd = None

    def save_focus(self):
        self._saved_hwnd = user32.GetForegroundWindow()

    def restore_focus(self):
        hwnd = self._saved_hwnd
        if hwnd is None or hwnd == 0:
            return False

        if not user32.IsWindow(hwnd):
            self._saved_hwnd = None
            return False

        current_thread = kernel32.GetCurrentThreadId()
        foreground_thread = user32.GetWindowThreadProcessId(
            user32.GetForegroundWindow(), None
        )

        if current_thread != foreground_thread:
            user32.AttachThreadInput(current_thread, foreground_thread, True)

        user32.SetForegroundWindow(hwnd)

        if current_thread != foreground_thread:
            user32.AttachThreadInput(current_thread, foreground_thread, False)

        return True

    @property
    def saved_hwnd(self):
        return self._saved_hwnd
