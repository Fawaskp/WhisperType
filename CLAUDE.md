# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Whisper Live** is a Windows-only Python voice-to-text overlay application. It provides an always-on-top floating overlay; users press a hotkey to record audio, OpenAI Whisper transcribes it, and the text is automatically pasted into the previously-focused window.

## Commands

```batch
# Run the application
run.bat
python -m whisper_live_app
python -m whisper_live_app base   # override Whisper model size (base|small|medium|large)

# Install in editable mode (creates `whisper-live` CLI command)
pip install -e .

# Build standalone .exe with PyInstaller
build.bat
# Output: dist\WhisperLive\WhisperLive.exe
```

No test suite or linter is configured.

## Architecture

### Package: `whisper_live_app/`

**Entry point:** `overlay.py` → `main()` (also `__main__.py` for `python -m` invocation)

**Core modules (`core/`):**
- `audio_recorder.py` — Captures microphone input via `sounddevice` at 16kHz mono int16. Detects silence (RMS < 300) for auto-stop after configurable timeout.
- `transcriber.py` — Wraps `openai-whisper`. Loads model, writes audio to temp WAV, returns transcribed text.
- `focus_manager.py` — Saves/restores the foreground window handle using Win32 `ctypes` calls so text gets pasted into the correct window.
- `text_injector.py` — Smart paste: detects window type by class name and chooses strategy (direct Unicode `SendInput` for terminals, `Ctrl+Shift+V` for Electron apps like VS Code, clipboard `Ctrl+V` for regular GUI). Preserves original clipboard.
- `config.py` — Loads/saves `config.json` and `overlay_position.json`.

**UI (`ui/`):**
- `overlay_window.py` — PySide6 `QWidget` implementing the floating overlay with states: loading → idle (compact circle) → recording (expanded with waveform) → preview (shows transcribed text). Draggable, animated transitions, context menu for settings.

### Application Flow

1. Load config → create PySide6 `QApplication` → init core components → show overlay in "loading" state
2. Background thread loads Whisper model → on success, register global hotkeys → set "idle" state
3. Hotkey press → save focused window → start recording → poll for silence timeout → stop recording
4. Background thread transcribes audio → restore focus → inject text via `TextInjector` → show preview → return to idle

### Thread Safety

Qt UI updates from background threads go through an `_Invoker` helper class that uses PySide6 Signal/Slot to marshal calls to the main thread.

### Configuration (`config.json`)

| Key | Default | Purpose |
|-----|---------|---------|
| `model` | `"base"` | Whisper model size |
| `hotkey` | `"ctrl+shift+space"` | Global recording hotkey |
| `language` | `"en"` | Transcription language |
| `silence_timeout` | `3` | Seconds of silence before auto-stop |
| `prepend_space` | `true` | Add leading space before pasted text |
| `sound_feedback` | `true` | Beep on record start/stop |

## Notes

- `app.py` is a duplicate of `overlay.py` — all entry points reference `overlay.py`.
- The virtual environment is expected at `whisper_live_app/venv/` (used by `run.bat` and `build.bat`).
- Windows-only: heavy use of Win32 API via `ctypes` for window management, clipboard, and input simulation.
- PyInstaller spec bundles Whisper assets (mel filters, multilingual vocab) and hidden imports for torch/PySide6/numpy.
