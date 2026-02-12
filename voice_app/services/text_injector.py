import ctypes
import ctypes.wintypes as wintypes
import sys
import time

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

# Set proper argtypes/restype for 64-bit pointer safety
kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
kernel32.GlobalAlloc.restype = ctypes.c_void_p
kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
kernel32.GlobalLock.restype = ctypes.c_void_p
kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
kernel32.GlobalUnlock.restype = wintypes.BOOL

user32.OpenClipboard.argtypes = [wintypes.HWND]
user32.OpenClipboard.restype = wintypes.BOOL
user32.CloseClipboard.argtypes = []
user32.CloseClipboard.restype = wintypes.BOOL
user32.EmptyClipboard.argtypes = []
user32.EmptyClipboard.restype = wintypes.BOOL
user32.GetClipboardData.argtypes = [wintypes.UINT]
user32.GetClipboardData.restype = ctypes.c_void_p
user32.SetClipboardData.argtypes = [wintypes.UINT, ctypes.c_void_p]
user32.SetClipboardData.restype = ctypes.c_void_p
user32.IsClipboardFormatAvailable.argtypes = [wintypes.UINT]
user32.IsClipboardFormatAvailable.restype = wintypes.BOOL
user32.SendInput.argtypes = [wintypes.UINT, ctypes.c_void_p, ctypes.c_int]
user32.SendInput.restype = wintypes.UINT
user32.GetClassNameW.argtypes = [wintypes.HWND, ctypes.c_wchar_p, ctypes.c_int]
user32.GetClassNameW.restype = ctypes.c_int

CF_UNICODETEXT = 13
GMEM_MOVEABLE = 0x0002

INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
VK_SHIFT = 0x10
VK_CONTROL = 0x11
VK_MENU = 0x12  # Alt
VK_LWIN = 0x5B
VK_RWIN = 0x5C
VK_V = 0x56


# --- Win32 INPUT structures (must match real sizes for SendInput) ---

class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(wintypes.ULONG)),
    ]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(wintypes.ULONG)),
    ]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    ]


class _INPUT_UNION(ctypes.Union):
    _fields_ = [
        ("mi", MOUSEINPUT),
        ("ki", KEYBDINPUT),
        ("hi", HARDWAREINPUT),
    ]


class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", wintypes.DWORD),
        ("union", _INPUT_UNION),
    ]


# --- Clipboard ---

def _set_clipboard_text(text):
    if not user32.OpenClipboard(0):
        return False
    try:
        user32.EmptyClipboard()
        data = text.encode("utf-16-le") + b"\x00\x00"
        h = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(data))
        if not h:
            return False
        ptr = kernel32.GlobalLock(h)
        ctypes.memmove(ptr, data, len(data))
        kernel32.GlobalUnlock(h)
        user32.SetClipboardData(CF_UNICODETEXT, h)
        return True
    finally:
        user32.CloseClipboard()


def _get_clipboard_text():
    if not user32.IsClipboardFormatAvailable(CF_UNICODETEXT):
        return None
    if not user32.OpenClipboard(0):
        return None
    try:
        h = user32.GetClipboardData(CF_UNICODETEXT)
        if not h:
            return None
        ptr = kernel32.GlobalLock(h)
        if not ptr:
            return None
        try:
            text = ctypes.wstring_at(ptr)
            return text
        finally:
            kernel32.GlobalUnlock(h)
    finally:
        user32.CloseClipboard()


# --- Window detection ---

def _get_window_class(hwnd):
    buf = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, buf, 256)
    return buf.value


def is_terminal_window(hwnd):
    """Check if a window handle belongs to a terminal/console application."""
    if not hwnd:
        return False
    cls = _get_window_class(hwnd).lower()
    terminal_hints = [
        "cascadia_hosting_window_class",  # Windows Terminal
        "consolewindowclass",             # cmd / PowerShell console host
        "mintty",                          # Git Bash / MSYS2
        "virtualconsoleclass",             # ConEmu
        "putty",                           # PuTTY
        "kitty",                           # KiTTY
    ]
    return any(h in cls for h in terminal_hints)


# --- Release stale modifiers ---

def _release_modifiers():
    """Release any modifier keys that may still be logically held down."""
    modifiers = [VK_SHIFT, VK_CONTROL, VK_MENU, VK_LWIN, VK_RWIN]
    released = []
    for vk in modifiers:
        if user32.GetAsyncKeyState(vk) & 0x8000:
            inp = INPUT()
            inp.type = INPUT_KEYBOARD
            inp.union.ki.wVk = vk
            inp.union.ki.dwFlags = KEYEVENTF_KEYUP
            user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))
            released.append(vk)
    if released:
        time.sleep(0.05)
    return released


# --- SendInput Ctrl+V (for GUI apps) ---

def _send_ctrl_v():
    _release_modifiers()

    inputs = (INPUT * 4)()
    for i in range(4):
        inputs[i].type = INPUT_KEYBOARD

    inputs[0].union.ki.wVk = VK_CONTROL
    inputs[1].union.ki.wVk = VK_V
    inputs[2].union.ki.wVk = VK_V
    inputs[2].union.ki.dwFlags = KEYEVENTF_KEYUP
    inputs[3].union.ki.wVk = VK_CONTROL
    inputs[3].union.ki.dwFlags = KEYEVENTF_KEYUP

    return user32.SendInput(4, ctypes.byref(inputs), ctypes.sizeof(INPUT))


def _send_ctrl_shift_v():
    _release_modifiers()

    inputs = (INPUT * 6)()
    for i in range(6):
        inputs[i].type = INPUT_KEYBOARD

    inputs[0].union.ki.wVk = VK_CONTROL
    inputs[1].union.ki.wVk = VK_SHIFT
    inputs[2].union.ki.wVk = VK_V
    inputs[3].union.ki.wVk = VK_V
    inputs[3].union.ki.dwFlags = KEYEVENTF_KEYUP
    inputs[4].union.ki.wVk = VK_SHIFT
    inputs[4].union.ki.dwFlags = KEYEVENTF_KEYUP
    inputs[5].union.ki.wVk = VK_CONTROL
    inputs[5].union.ki.dwFlags = KEYEVENTF_KEYUP

    return user32.SendInput(6, ctypes.byref(inputs), ctypes.sizeof(INPUT))


# --- KEYEVENTF_UNICODE typing (for terminals) ---

def _type_unicode(text):
    """Type text via KEYEVENTF_UNICODE SendInput events.

    These events carry wVk=0 so the keyboard library's low-level hook
    won't intercept them as potential hotkey prefixes.  Works reliably
    with terminals, consoles, and GUI apps alike.
    """
    _release_modifiers()

    n = len(text)
    if n == 0:
        return 0
    # 2 INPUT events per character (key-down + key-up)
    inputs = (INPUT * (n * 2))()
    for i, char in enumerate(text):
        code = ord(char)
        # key down
        inputs[i * 2].type = INPUT_KEYBOARD
        inputs[i * 2].union.ki.wVk = 0
        inputs[i * 2].union.ki.wScan = code
        inputs[i * 2].union.ki.dwFlags = KEYEVENTF_UNICODE
        # key up
        inputs[i * 2 + 1].type = INPUT_KEYBOARD
        inputs[i * 2 + 1].union.ki.wVk = 0
        inputs[i * 2 + 1].union.ki.wScan = code
        inputs[i * 2 + 1].union.ki.dwFlags = KEYEVENTF_UNICODE | KEYEVENTF_KEYUP
    return user32.SendInput(n * 2, ctypes.byref(inputs), ctypes.sizeof(INPUT))


# --- Public API ---

def _dbg(msg):
    print(f"[inject] {msg}", file=sys.stderr, flush=True)


def inject_text(text, preserve_clipboard=True, target_hwnd=None):
    """Inject text into the focused window.

    For terminal/console windows (detected via *target_hwnd*), characters
    are typed directly using KEYEVENTF_UNICODE which bypasses low-level
    keyboard hooks.  For regular GUI windows the clipboard + Ctrl+V
    approach is used.
    """
    # Debug: show what we're working with
    fg = user32.GetForegroundWindow()
    fg_cls = _get_window_class(fg) if fg else "N/A"
    tgt_cls = _get_window_class(target_hwnd) if target_hwnd else "N/A"
    is_term = is_terminal_window(target_hwnd) if target_hwnd else False
    _dbg(f"text={text!r:.80}")
    _dbg(f"target_hwnd={target_hwnd}  class={tgt_cls!r}")
    _dbg(f"foreground_hwnd={fg}  class={fg_cls!r}")
    _dbg(f"is_terminal={is_term}")

    is_electron = "chrome_widgetwin_1" in tgt_cls.lower() if target_hwnd else False
    _dbg(f"is_electron={is_electron}")

    if target_hwnd and is_term:
        # Terminal path: type characters directly via Unicode events.
        _set_clipboard_text(text)
        time.sleep(0.05)
        sent = _type_unicode(text)
        _dbg(f"UNICODE SendInput returned {sent} (expected {len(text)*2})")
    else:
        # GUI path: clipboard + paste shortcut
        old_clipboard = None
        if preserve_clipboard:
            old_clipboard = _get_clipboard_text()

        _set_clipboard_text(text)
        time.sleep(0.05)

        if is_electron:
            # Electron apps (VS Code, Cursor, Chrome): Ctrl+Shift+V works
            # in both editor areas (plain-text paste) and integrated terminals.
            sent = _send_ctrl_shift_v()
            _dbg(f"Ctrl+Shift+V SendInput returned {sent} (expected 6)")
        else:
            sent = _send_ctrl_v()
            _dbg(f"Ctrl+V SendInput returned {sent} (expected 4)")
        time.sleep(0.05)

        if preserve_clipboard and old_clipboard is not None:
            time.sleep(0.2)
            _set_clipboard_text(old_clipboard)
