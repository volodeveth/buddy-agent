#!/usr/bin/env python3
"""Voice format utilities — convert between OGG, WAV, MP3 using PyAV (bundled with faster-whisper)."""

import sys
import json
import os
from pathlib import Path

import av


def convert(input_path: str, output_format: str = "wav") -> str:
    """Convert audio file to specified format. Returns output path."""
    input_file = Path(input_path)
    output_path = str(input_file.with_suffix(f".{output_format}"))

    # Map format names to container/codec
    format_map = {
        "wav": ("wav", "pcm_s16le"),
        "mp3": ("mp3", "mp3"),
        "ogg": ("ogg", "libvorbis"),
    }

    container_fmt, codec_name = format_map.get(output_format, (output_format, None))

    input_container = av.open(input_path)
    input_stream = input_container.streams.audio[0]

    output_container = av.open(output_path, mode="w", format=container_fmt)
    if codec_name:
        output_stream = output_container.add_stream(codec_name, rate=input_stream.rate)
    else:
        output_stream = output_container.add_stream(codec_name or "pcm_s16le", rate=input_stream.rate)

    for frame in input_container.decode(audio=0):
        for packet in output_stream.encode(frame):
            output_container.mux(packet)

    for packet in output_stream.encode():
        output_container.mux(packet)

    output_container.close()
    input_container.close()

    return output_path


def get_duration(input_path: str) -> float:
    """Get audio duration in seconds."""
    container = av.open(input_path)
    duration_sec = container.duration / 1_000_000 if container.duration else 0.0
    container.close()
    return round(duration_sec, 1)


def main() -> None:
    if len(sys.argv) < 3:
        print(json.dumps({"error": "Usage: voice_utils.py <convert|duration> <file_path> [format]"}))
        sys.exit(1)

    command = sys.argv[1]
    file_path = sys.argv[2]

    if not os.path.exists(file_path):
        print(json.dumps({"error": f"File not found: {file_path}"}))
        sys.exit(1)

    try:
        if command == "convert":
            fmt = sys.argv[3] if len(sys.argv) > 3 else "wav"
            result = convert(file_path, fmt)
            print(json.dumps({"output_path": result}))
        elif command == "duration":
            duration = get_duration(file_path)
            print(json.dumps({"duration_seconds": duration}))
        else:
            print(json.dumps({"error": f"Unknown command: {command}"}))
            sys.exit(1)
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
