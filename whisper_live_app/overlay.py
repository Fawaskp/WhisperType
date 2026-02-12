import sys
import threading
import time
import tkinter as tk
import winsound

import keyboard

try:
    from core.audio_recorder import AudioRecorder
    from core.config import load_config, save_config, load_position, save_position
    from core.transcriber import Transcriber
    from core.focus_manager import FocusManager
    from core.text_injector import inject_text
    from ui.overlay_window import OverlayWindow
except ImportError:
    from whisper_live_app.core.audio_recorder import AudioRecorder
    from whisper_live_app.core.config import load_config, save_config, load_position, save_position
    from whisper_live_app.core.transcriber import Transcriber
    from whisper_live_app.core.focus_manager import FocusManager
    from whisper_live_app.core.text_injector import inject_text
    from whisper_live_app.ui.overlay_window import OverlayWindow


def _beep(freq, duration):
    threading.Thread(target=winsound.Beep, args=(freq, duration), daemon=True).start()


class OverlayApp:
    def __init__(self, config):
        self.config = config
        self.state = "loading"

        self.root = tk.Tk()
        self.root.withdraw()

        self.recorder = AudioRecorder()
        self.transcriber = Transcriber()
        self.focus_mgr = FocusManager()

        pos = load_position()
        self.window = OverlayWindow(
            self.root,
            on_click=self._on_button_click,
            on_stop=self._on_stop_click,
            on_cancel=self._on_cancel_click,
            initial_pos=pos,
            on_drag_end=self._on_drag_end,
        )
        self.window.set_state("loading")

        t = threading.Thread(target=self._load_model, daemon=True)
        t.start()

    # ── Model loading ────────────────────────────────────────────────

    def _load_model(self):
        try:
            self.transcriber.load_model(self.config["model"])
            self.root.after(0, self._on_model_loaded)
        except Exception as e:
            err = e
            self.root.after(0, lambda: self._on_model_error(err))

    def _on_model_loaded(self):
        self.state = "idle"
        self.window.set_state("idle")
        self._register_hotkey()

    def _on_model_error(self, error):
        print(f"Model load error: {error}", file=sys.stderr)
        self.state = "idle"
        self.window.set_state("error")

    # ── Hotkeys ──────────────────────────────────────────────────────

    def _register_hotkey(self):
        keyboard.add_hotkey(self.config["hotkey"], self._on_hotkey, suppress=True)
        keyboard.add_hotkey("escape", self._on_escape, suppress=False)

    def _on_hotkey(self):
        self.root.after(0, self._toggle_recording)

    def _on_escape(self):
        if self.state == "recording":
            self.root.after(0, self._cancel_recording)

    # ── Button callbacks ─────────────────────────────────────────────

    def _on_button_click(self):
        self._toggle_recording()

    def _on_stop_click(self):
        if self.state == "recording":
            self._stop_recording()

    def _on_cancel_click(self):
        if self.state == "recording":
            self._cancel_recording()

    def _on_drag_end(self, x, y):
        save_position(x, y)

    # ── Recording control ────────────────────────────────────────────

    def _toggle_recording(self):
        if self.state == "idle":
            self._start_recording()
        elif self.state == "recording":
            self._stop_recording()

    def _start_recording(self):
        self.focus_mgr.save_focus()
        try:
            self.recorder.start()
        except Exception as e:
            print(f"Mic error: {e}", file=sys.stderr)
            self.state = "idle"
            self.window.set_state("error")
            return
        self.state = "recording"
        self.window.set_state("recording")
        if self.config["sound_feedback"]:
            _beep(800, 100)
        self._poll_silence()

    def _poll_silence(self):
        if self.state != "recording":
            return
        timeout = self.config.get("silence_timeout", 3)
        if timeout and self.recorder.silence_duration >= timeout:
            self._stop_recording()
            return
        self.root.after(250, self._poll_silence)

    def _stop_recording(self):
        audio = self.recorder.stop()
        if self.config["sound_feedback"]:
            _beep(400, 150)

        if audio is None:
            self.state = "idle"
            self.window.set_state("too_short")
            return

        self.state = "transcribing"
        self.window.set_state("transcribing")

        lang = self.config.get("language") or None
        t = threading.Thread(target=self._do_transcribe, args=(audio, lang), daemon=True)
        t.start()

    def _cancel_recording(self):
        self.recorder.stop()
        self.state = "idle"
        self.window.set_state("idle")
        if self.config["sound_feedback"]:
            def _cancel_beeps():
                winsound.Beep(300, 80)
                time.sleep(0.05)
                winsound.Beep(300, 80)
            threading.Thread(target=_cancel_beeps, daemon=True).start()

    # ── Transcription ────────────────────────────────────────────────

    def _do_transcribe(self, audio, language):
        try:
            text = self.transcriber.transcribe(audio, language=language)
            self.root.after(0, lambda: self._on_transcription_done(text))
        except Exception as e:
            self.root.after(0, lambda: self._on_transcription_error(e))

    def _on_transcription_done(self, text):
        if text:
            self.focus_mgr.restore_focus()
            self.root.after(300, lambda: self._do_paste(text))
        else:
            self.state = "idle"
            self.window.set_state("idle")

    def _do_paste(self, text):
        if self.config.get("prepend_space"):
            text = " " + text

        keyboard.unhook_all()
        try:
            inject_text(text, target_hwnd=self.focus_mgr.saved_hwnd)
        finally:
            self._register_hotkey()

        self.state = "idle"
        self.window.set_state("preview", text=text.strip())

    def _on_transcription_error(self, error):
        print(f"Transcription error: {error}", file=sys.stderr)
        self.state = "idle"
        self.window.set_state("error")

    # ── Run ──────────────────────────────────────────────────────────

    def run(self):
        try:
            self.root.mainloop()
        finally:
            keyboard.unhook_all()


def main():
    config = load_config()

    # CLI arg overrides model
    if len(sys.argv) > 1:
        config["model"] = sys.argv[1]

    app = OverlayApp(config)
    app.run()


if __name__ == "__main__":
    main()
