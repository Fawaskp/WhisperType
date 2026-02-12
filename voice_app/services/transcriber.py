import numpy as np
from faster_whisper import WhisperModel


class Transcriber:
    def __init__(self):
        self.model = None
        self.model_name = None

    def load_model(self, model_name="base", model_path=None, compute_type="int8"):
        self.model_name = model_name
        model_id = model_path if model_path else model_name
        self.model = WhisperModel(model_id, device="cpu", compute_type=compute_type)

    def transcribe(self, audio, sample_rate=16000, language=None):
        if self.model is None:
            raise RuntimeError("Model not loaded")

        # Convert int16 audio to float32 normalized to [-1, 1]
        if audio.dtype == np.int16:
            audio_f32 = audio.flatten().astype(np.float32) / 32768.0
        else:
            audio_f32 = audio.flatten().astype(np.float32)

        kwargs = {}
        if language:
            kwargs["language"] = language

        segments, _info = self.model.transcribe(audio_f32, **kwargs)
        text = " ".join(seg.text.strip() for seg in segments)
        return text.strip()
