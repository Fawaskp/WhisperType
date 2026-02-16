import json
import os
import sys


def _config_dir():
    """Return the platform-appropriate user config directory for WhisperType."""
    if sys.platform == "win32":
        base = os.environ.get("APPDATA", os.path.expanduser("~"))
        return os.path.join(base, "WhisperType")
    if sys.platform == "darwin":
        return os.path.join(os.path.expanduser("~"), "Library",
                            "Application Support", "WhisperType")
    # Linux / other
    xdg = os.environ.get("XDG_CONFIG_HOME", os.path.join(os.path.expanduser("~"), ".config"))
    return os.path.join(xdg, "whispertype")


_DIR = _config_dir()
_CONFIG_PATH = os.path.join(_DIR, "config.json")
_POSITION_PATH = os.path.join(_DIR, "overlay_position.json")

DEFAULTS = {
    "model": "base",
    "model_path": None,
    "compute_type": "int8",
    "hotkey": "ctrl+shift+space",
    "language": "en",
    "prepend_space": True,
    "sound_feedback": True,
    "silence_timeout": 1,
}


def _ensure_dir():
    os.makedirs(_DIR, exist_ok=True)


def load_config():
    _ensure_dir()
    if os.path.exists(_CONFIG_PATH):
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            stored = json.load(f)
        cfg = {**DEFAULTS, **stored}
    else:
        cfg = dict(DEFAULTS)
        save_config(cfg)
    return cfg


def save_config(cfg):
    _ensure_dir()
    with open(_CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)


def load_position():
    if os.path.exists(_POSITION_PATH):
        with open(_POSITION_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("x"), data.get("y")
    return None, None


def save_position(x, y):
    _ensure_dir()
    with open(_POSITION_PATH, "w", encoding="utf-8") as f:
        json.dump({"x": x, "y": y}, f)
