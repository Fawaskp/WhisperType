"""Cross-platform beep using sounddevice + numpy (replaces winsound.Beep)."""

import threading

import numpy as np
import sounddevice as sd

from .base import PlatformSoundPlayer

# Default output sample rate for tones
_TONE_SR = 44100


class CrossPlatformSoundPlayer(PlatformSoundPlayer):
    """Generate simple sine-wave beeps via sounddevice."""

    def beep(self, frequency, duration_ms):
        threading.Thread(
            target=self._play, args=(frequency, duration_ms), daemon=True
        ).start()

    @staticmethod
    def _play(frequency, duration_ms):
        try:
            n_samples = int(_TONE_SR * duration_ms / 1000)
            t = np.linspace(0, duration_ms / 1000, n_samples, endpoint=False)
            wave = (np.sin(2 * np.pi * frequency * t) * 0.4).astype(np.float32)
            sd.play(wave, samplerate=_TONE_SR, blocking=True)
        except Exception:
            pass  # audio feedback is best-effort
