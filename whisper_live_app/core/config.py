import json
import os

_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CONFIG_PATH = os.path.join(_DIR, "config.json")
_POSITION_PATH = os.path.join(_DIR, "overlay_position.json")

DEFAULTS = {
    "model": "base",
    "hotkey": "ctrl+shift+space",
    "language": "en",
    "prepend_space": True,
    "sound_feedback": True,
    "silence_timeout": 3,
}


def load_config():
    if os.path.exists(_CONFIG_PATH):
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            stored = json.load(f)
        cfg = {**DEFAULTS, **stored}
    else:
        cfg = dict(DEFAULTS)
        save_config(cfg)
    return cfg


def save_config(cfg):
    with open(_CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)


def load_position():
    if os.path.exists(_POSITION_PATH):
        with open(_POSITION_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("x"), data.get("y")
    return None, None


def save_position(x, y):
    with open(_POSITION_PATH, "w", encoding="utf-8") as f:
        json.dump({"x": x, "y": y}, f)
