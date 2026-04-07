#!/usr/bin/env python3
"""Text-to-Speech using edge-tts (Microsoft Edge, free, Ukrainian supported)."""

import sys
import json
import asyncio
import edge_tts

# Ukrainian voices available in edge-tts:
# - uk-UA-OstapNeural (male)
# - uk-UA-PolinaNeural (female)
DEFAULT_VOICE = "uk-UA-OstapNeural"


async def synthesize(text: str, output_path: str, voice: str = DEFAULT_VOICE) -> dict:
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)
    return {
        "status": "success",
        "output_path": output_path,
        "voice": voice,
        "text_length": len(text)
    }


def main() -> None:
    if len(sys.argv) < 3:
        print(json.dumps({"error": "Usage: tts_edge.py <text> <output_path> [voice]"}))
        sys.exit(1)

    text = sys.argv[1]
    output_path = sys.argv[2]
    voice = sys.argv[3] if len(sys.argv) > 3 else DEFAULT_VOICE

    try:
        result = asyncio.run(synthesize(text, output_path, voice))
        print(json.dumps(result, ensure_ascii=True))
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
