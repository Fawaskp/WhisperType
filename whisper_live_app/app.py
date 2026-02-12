import whisper
import sounddevice as sd
import numpy as np
from scipy.io.wavfile import write
import tempfile
import os
import threading

# Settings
SAMPLE_RATE = 16000
MODEL_SIZE = "base"  # tiny, base, small, medium, large


def record_audio(sample_rate):
    """Record audio until the user presses Enter to stop."""
    chunks = []
    stop_event = threading.Event()

    def callback(indata, frames, time_info, status):
        if not stop_event.is_set():
            chunks.append(indata.copy())

    stream = sd.InputStream(
        samplerate=sample_rate,
        channels=1,
        dtype="int16",
        callback=callback,
    )

    print("Recording... Press Enter to stop.")
    stream.start()
    input()
    stop_event.set()
    stream.stop()
    stream.close()

    if not chunks:
        return None

    audio = np.concatenate(chunks, axis=0)
    duration = len(audio) / sample_rate
    print(f"Recording finished. ({duration:.1f}s)")
    return audio


def save_temp_wav(audio, sample_rate):
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    write(temp_file.name, sample_rate, audio)
    return temp_file.name


def transcribe_audio(file_path, model):
    print("Transcribing...")
    result = model.transcribe(file_path)
    return result["text"]


def main():
    print(f"Loading Whisper model '{MODEL_SIZE}'...")
    model = whisper.load_model(MODEL_SIZE)
    print("Model loaded.\n")

    while True:
        input("Press Enter to start recording (Ctrl+C to exit)...")

        audio = record_audio(SAMPLE_RATE)
        if audio is None:
            print("No audio recorded.\n")
            continue

        wav_path = save_temp_wav(audio, SAMPLE_RATE)
        text = transcribe_audio(wav_path, model)

        print("\nTranscribed Text:")
        print("----------------------------------")
        print(text)
        print("----------------------------------\n")

        os.remove(wav_path)


if __name__ == "__main__":
    main()
