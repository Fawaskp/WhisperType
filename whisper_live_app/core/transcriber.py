import os
import tempfile

import numpy as np
import whisper
from scipy.io.wavfile import write as write_wav


class Transcriber:
    def __init__(self):
        self.model = None
        self.model_name = None

    def load_model(self, model_name="base"):
        self.model_name = model_name
        self.model = whisper.load_model(model_name)

    def transcribe(self, audio, sample_rate=16000, language=None):
        if self.model is None:
            raise RuntimeError("Model not loaded")

        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        try:
            write_wav(tmp.name, sample_rate, audio)
            tmp.close()
            kwargs = {}
            if language:
                kwargs["language"] = language
            result = self.model.transcribe(tmp.name, **kwargs)
            return result["text"].strip()
        finally:
            try:
                os.remove(tmp.name)
            except OSError:
                pass
