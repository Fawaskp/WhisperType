# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**WhisperType** is a cross-platform (Windows, macOS, Linux) Python voice-to-text overlay application. It provides an always-on-top floating overlay; users press a hotkey to record audio, faster-whisper transcribes it locally, and the text is automatically pasted into the previously-focused window.

## Commands

```bash
# Run the application
python -m voice_app
python -m voice_app base   # override Whisper model size (base|small|medium|large)

# Install with platform extras
pip install ".[windows]"   # Windows
pip install ".[macos]"     # macOS
pip install ".[linux]"     # Linux

# Build with PyInstaller (platform-specific specs)
pyinstaller packaging/whispertype_windows.spec --noconfirm
pyinstaller packaging/whispertype_macos.spec --noconfirm
pyinstaller packaging/whispertype_linux.spec --noconfirm

# Build installers
iscc packaging/inno_setup.iss              # Windows (Inno Setup)
bash packaging/build_dmg.sh                # macOS DMG
bash packaging/build_appimage.sh           # Linux AppImage
```

No test suite or linter is configured.

## Architecture

### Package: `voice_app/`

**Entry point:** `main.py` → `main()` (also `__main__.py` for `python -m` invocation)

**Services (`services/`):**
- `recorder.py` — Captures microphone input via `sounddevice` at 16kHz mono int16. Detects silence (RMS < 300) for auto-stop after configurable timeout. Cross-platform.
- `transcriber.py` — Wraps `faster_whisper`. Loads model on CPU with INT8 quantization, returns transcribed text. Cross-platform.
- `focus_manager.py` — Thin facade that delegates to the platform-specific focus manager.
- `text_injector.py` — Thin facade that delegates to the platform-specific text injector.

**Platform Abstraction Layer (`services/platform/`):**
- `base.py` — Abstract base classes: `PlatformFocusManager`, `PlatformTextInjector`, `PlatformHotkeyManager`, `PlatformSoundPlayer`
- `__init__.py` — Factory functions (`get_focus_manager()`, `get_text_injector()`, `get_hotkey_manager()`, `get_sound_player()`) that detect `sys.platform` and return the correct adapter
- `_sound.py` — Cross-platform beep via `sounddevice` + `numpy` sine wave (replaces `winsound.Beep`)
- `windows.py` — Win32 adapter: `ctypes`-based focus, clipboard, SendInput, `keyboard` library hotkeys
- `macos.py` — macOS adapter: PyObjC (`NSWorkspace`) for focus, `pyperclip` + `pynput` for paste, `pynput.keyboard.GlobalHotKeys` for hotkeys
- `linux.py` — Linux adapter: `xdotool` subprocess for focus, `pyperclip` + `pynput` for paste, `pynput.keyboard.GlobalHotKeys` for hotkeys

**Config (`config/`):**
- `settings.py` — Loads/saves `config.json` and `overlay_position.json` in the platform-appropriate config directory (`%APPDATA%/WhisperType`, `~/Library/Application Support/WhisperType`, `~/.config/whispertype`).

**UI (`ui/`):**
- `overlay_window.py` — PySide6 `QWidget` implementing the floating overlay with states: loading → idle (compact circle) → recording (expanded with waveform) → transcribing → preview (shows transcribed text). Draggable, animated transitions, context menu. Win32 `WS_EX_NOACTIVATE` hack guarded behind `sys.platform == "win32"`. Platform-aware font selection.

### Application Flow

1. Load config → create PySide6 `QApplication` → init services → show overlay in "loading" state
2. Background thread loads faster-whisper model → on success, register global hotkeys → set "idle" state
3. Hotkey press → save focused window → start recording → poll for silence timeout → stop recording
4. Background thread transcribes audio → restore focus → inject text via `text_injector` → show preview → return to idle

### Thread Safety

Qt UI updates from background threads go through an `_Invoker` helper class that uses PySide6 Signal/Slot to marshal calls to the main thread.

### Configuration (`config.json`)

| Key | Default | Purpose |
|-----|---------|---------|
| `model` | `"base"` | Whisper model size |
| `model_path` | `null` | Custom model path (uses HF cache if null) |
| `compute_type` | `"int8"` | CTranslate2 quantization type |
| `hotkey` | `"ctrl+shift+space"` | Global recording hotkey |
| `language` | `"en"` | Transcription language |
| `silence_timeout` | `1` | Seconds of silence before auto-stop |
| `prepend_space` | `true` | Add leading space before pasted text |
| `sound_feedback` | `true` | Beep on record start/stop |

### Packaging (`packaging/`)

- `whispertype_windows.spec` / `whispertype_macos.spec` / `whispertype_linux.spec` — PyInstaller specs
- `inno_setup.iss` — Windows installer (Inno Setup)
- `build_dmg.sh` — macOS DMG builder
- `build_appimage.sh` — Linux AppImage builder

### CI/CD (`.github/workflows/build.yml`)

Matrix build for all 3 platforms. On tag push (`v*`), builds all installers and creates a GitHub Release with artifacts.

## Platform Notes

- **Windows:** Uses `keyboard` library (supports hotkey suppression) and Win32 `ctypes` for focus/clipboard/SendInput.
- **macOS:** Requires Accessibility permission (System Settings > Privacy > Accessibility). Uses PyObjC + pynput. Hotkey `ctrl` is mapped to `cmd`.
- **Linux:** Requires X11 + `xdotool` + `xclip`. Wayland is detected and warned about (xdotool/pynput don't work on Wayland).
- The virtual environment is expected at `voice_app/venv/` (used by bat scripts).
- When building with PyInstaller, faster-whisper/ctranslate2 must be included and torch excluded.
