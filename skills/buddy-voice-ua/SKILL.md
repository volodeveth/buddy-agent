---
name: buddy-voice-ua
description: Ukrainian voice messages - STT via local Whisper, TTS via Edge-TTS. Handles incoming voice messages and generates voice replies.
trigger:
  - on_voice_message
  - on_command: /voice
priority: 80
tools:
  - shell
  - send_voice
  - file_read
  - file_write
---

## Incoming Voice (STT)
1. Receive voice message from Telegram (OGG/Opus format)
2. Save to temp file: data/temp/voice_in_TIMESTAMP.ogg
3. Run: python stt_whisper.py <input_file>
4. Get transcribed text (Ukrainian)
5. Process the text as a normal text message
6. Delete temp file after processing

## Outgoing Voice (TTS)
1. After generating a text response, also generate voice:
2. Run: python tts_edge.py "<response_text>" <output_file>
3. Voice: "uk-UA-OstapNeural" (male) or "uk-UA-PolinaNeural" (female)
4. Send voice message via Telegram send_voice
5. Also send text version (for readability)
6. Delete temp file after sending

## /voice Command
When user sends /voice followed by text:
- Generate TTS of that text and send as voice message

## Error Handling
- If STT fails: reply with "Не вдалося розпізнати голос. Спробуй ще раз або надішли текстом."
- If TTS fails: send text-only reply with note "Голосова генерація тимчасово недоступна"
- If voice file is too long (>5 minutes): transcribe first 5 minutes, warn about truncation
