import time

import numpy as np
import sounddevice as sd
import threading

SAMPLE_RATE = 16000
SILENCE_RMS_THRESHOLD = 300  # int16 amplitude; below this counts as silence


class AudioRecorder:
    def __init__(self, sample_rate=SAMPLE_RATE):
        self.sample_rate = sample_rate
        self._chunks = []
        self._stream = None
        self._lock = threading.Lock()
        self._last_voice_time = 0.0

    def start(self):
        self._chunks = []
        self._last_voice_time = time.monotonic()
        self._stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype="int16",
            callback=self._callback,
        )
        self._stream.start()

    def _callback(self, indata, frames, time_info, status):
        with self._lock:
            self._chunks.append(indata.copy())
        rms = np.sqrt(np.mean(indata.astype(np.float32) ** 2))
        if rms >= SILENCE_RMS_THRESHOLD:
            self._last_voice_time = time.monotonic()

    def stop(self):
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None

        with self._lock:
            if not self._chunks:
                return None
            audio = np.concatenate(self._chunks, axis=0)

        duration = len(audio) / self.sample_rate
        if duration < 0.3:
            return None
        return audio

    @property
    def is_recording(self):
        return self._stream is not None and self._stream.active

    @property
    def silence_duration(self):
        """Seconds of continuous silence since last detected voice."""
        if not self.is_recording:
            return 0.0
        return time.monotonic() - self._last_voice_time
