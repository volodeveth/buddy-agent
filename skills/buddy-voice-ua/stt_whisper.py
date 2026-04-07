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
from pathlib import Path
import subprocess
import tempfile

# Use "medium" model - significantly better Ukrainian accuracy vs "small"
# Downloads ~1.5GB on first run, then cached
MODEL_SIZE = "medium"

# Cache model instance to avoid reloading on every call
_model = None

SKILL_DIR = Path(__file__).parent.resolve()


def get_model() -> WhisperModel:
    global _model
    if _model is None:
        _model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")
    return _model


def convert_to_wav(input_path: str) -> str:
    """Convert OGG/OPUS to WAV using voice_utils.py for reliable transcription."""
    input_ext = Path(input_path).suffix.lower()
    if input_ext in (".wav", ".mp3", ".flac"):
        return input_path

    voice_utils = SKILL_DIR / "voice_utils.py"
    if not voice_utils.exists():
        return input_path  # fallback: let whisper try the original

    try:
        result = subprocess.run(
            [sys.executable, str(voice_utils), "convert", input_path, "wav"],
            capture_output=True, text=True, timeout=30, encoding="utf-8"
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            if data.get("status") == "success" and data.get("output_path"):
                return data["output_path"]
    except Exception:
        pass
    return input_path


def transcribe(audio_path: str) -> dict:
    # Convert OGG/OPUS to WAV for reliable decoding
    wav_path = convert_to_wav(audio_path)

    model = get_model()
    segments, info = model.transcribe(
        wav_path,
        language="uk",
        beam_size=5,
        condition_on_previous_text=False,
        vad_filter=True,
        vad_parameters=dict(
            min_silence_duration_ms=300,
            speech_pad_ms=200,
        ),
        no_speech_threshold=0.6,
        log_prob_threshold=-1.0,
        compression_ratio_threshold=2.4,
        repetition_penalty=1.2,
        temperature=[0.0, 0.2, 0.4],
    )

    # Filter out hallucinated segments (very low avg_logprob or high no_speech_prob)
    filtered_texts = []
    for segment in segments:
        if segment.no_speech_prob > 0.7:
            continue
        if segment.avg_logprob < -1.5:
            continue
        text = segment.text.strip()
        if text and len(text) > 1:
            filtered_texts.append(text)

    text = " ".join(filtered_texts)

    # Clean up temp WAV if we created one
    if wav_path != audio_path and Path(wav_path).exists():
        try:
            Path(wav_path).unlink()
        except OSError:
            pass

    return {
        "text": text,
        "language": info.language,
        "language_probability": round(info.language_probability, 2),
        "duration": round(info.duration, 1)
    }


def main() -> None:
    if len(sys.argv) < 2:
        print(json.dumps({"error": "No audio file path provided"}))
        sys.exit(1)

    audio_path = sys.argv[1]

    if not os.path.exists(audio_path):
        print(json.dumps({"error": f"File not found: {audio_path}"}))
        sys.exit(1)

    try:
        result = transcribe(audio_path)
        print(json.dumps(result, ensure_ascii=True))
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
