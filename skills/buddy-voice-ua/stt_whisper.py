#!/usr/bin/env python3
"""Speech-to-Text using faster-whisper (local, free)."""

import sys
import io
import json
import os

# Force UTF-8 output on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# Configure ffmpeg path for av/pydub (from imageio_ffmpeg bundled binary)
try:
    import imageio_ffmpeg
    os.environ["PATH"] = os.path.dirname(imageio_ffmpeg.get_ffmpeg_exe()) + os.pathsep + os.environ.get("PATH", "")
except ImportError:
    pass

from faster_whisper import WhisperModel

# Use "small" model - good balance of speed and accuracy for Ukrainian
# Downloads ~461MB on first run, then cached
MODEL_SIZE = "small"

# Cache model instance to avoid reloading on every call
_model = None


def get_model():
    global _model
    if _model is None:
        _model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")
    return _model


def transcribe(audio_path: str) -> dict:
    model = get_model()
    segments, info = model.transcribe(audio_path, language="uk", beam_size=5)

    text = " ".join([segment.text.strip() for segment in segments])

    return {
        "text": text,
        "language": info.language,
        "language_probability": round(info.language_probability, 2),
        "duration": round(info.duration, 1)
    }


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "No audio file path provided"}))
        sys.exit(1)

    audio_path = sys.argv[1]

    if not os.path.exists(audio_path):
        print(json.dumps({"error": f"File not found: {audio_path}"}))
        sys.exit(1)

    try:
        result = transcribe(audio_path)
        print(json.dumps(result, ensure_ascii=False))
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
