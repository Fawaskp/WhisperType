# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**WhisperType** is a Windows-only Python voice-to-text overlay application. It provides an always-on-top floating overlay; users press a hotkey to record audio, faster-whisper transcribes it locally, and the text is automatically pasted into the previously-focused window.

## Commands

```batch
# Run the application
python -m voice_app
python -m voice_app base   # override Whisper model size (base|small|medium|large)

# Build standalone .exe with PyInstaller
pyinstaller --name WhisperType voice_app/main.py --noconfirm
# Output: dist\WhisperType\WhisperType.exe
```

No test suite or linter is configured.

## Architecture

### Package: `voice_app/`

**Entry point:** `main.py` → `main()` (also `__main__.py` for `python -m` invocation)

**Services (`services/`):**
- `recorder.py` — Captures microphone input via `sounddevice` at 16kHz mono int16. Detects silence (RMS < 300) for auto-stop after configurable timeout.
- `transcriber.py` — Wraps `faster_whisper`. Loads model on CPU with INT8 quantization, returns transcribed text.
- `focus_manager.py` — Saves/restores the foreground window handle using Win32 `ctypes` calls so text gets pasted into the correct window.
- `text_injector.py` — Smart paste: detects window type by class name and chooses strategy (direct Unicode `SendInput` for terminals, `Ctrl+Shift+V` for Electron apps like VS Code, clipboard `Ctrl+V` for regular GUI). Preserves original clipboard.

**Config (`config/`):**
- `settings.py` — Loads/saves `config.json` and `overlay_position.json`.

**UI (`ui/`):**
- `overlay_window.py` — PySide6 `QWidget` implementing the floating overlay with states: loading → idle (compact circle) → recording (expanded with waveform) → transcribing → preview (shows transcribed text). Draggable, animated transitions, context menu.

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
| `silence_timeout` | `3` | Seconds of silence before auto-stop |
| `prepend_space` | `true` | Add leading space before pasted text |
| `sound_feedback` | `true` | Beep on record start/stop |

## Notes

- The virtual environment is expected at `voice_app/venv/` (used by bat scripts).
- Windows-only: heavy use of Win32 API via `ctypes` for window management, clipboard, and input simulation.
- When building with PyInstaller, faster-whisper/ctranslate2 must be included and torch excluded.
