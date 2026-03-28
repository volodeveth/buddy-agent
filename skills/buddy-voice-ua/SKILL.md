---
name: buddy-voice-ua
description: Ukrainian voice messages - STT via local Whisper, TTS via Edge-TTS. When you receive a voice message (audio file), you MUST use the exec tool to run python scripts for transcription.
trigger:
  - on_voice_message
  - on_command: /voice
priority: 80
tools:
  - exec
  - read
  - write
---

# Voice Message Processing

## CRITICAL: How to process voice messages

When you see `[media attached: ...ogg]` in a user message, this is a voice message.
You MUST use the **exec** tool to transcribe it. Do NOT guess or imagine the transcription text.

### Step 1: Transcribe voice with exec tool

Call the `exec` tool with this command (replace FILE_PATH with the actual path from the message):

```
python C:/Users/User/.openclaw/workspace/skills/buddy-voice-ua/stt_whisper.py "FILE_PATH"
```

The script returns JSON to stdout: `{"text": "transcribed text here", "language": "uk", ...}`

### Step 2: Respond to the transcribed text

Parse the `text` field from the JSON output and respond to it normally.

### Full Example

User message: `[media attached: C:\Users\User\.openclaw\media\inbound\file_4---abc.ogg (audio/ogg)]`

You MUST call exec tool:
- command: `python C:/Users/User/.openclaw/workspace/skills/buddy-voice-ua/stt_whisper.py "C:/Users/User/.openclaw/media/inbound/file_4---abc.ogg"`

exec returns: `{"text": "Привіт, як справи?", "language": "uk", "language_probability": 1.0, "duration": 1.8}`

Then respond to "Привіт, як справи?" as a normal text message.

## TTS (Text-to-Speech) — voice reply

To send a voice reply after responding, call exec tool:
- command: `python C:/Users/User/.openclaw/workspace/skills/buddy-voice-ua/tts_edge.py "YOUR_RESPONSE" "C:/Users/User/.openclaw/workspace/data/temp/reply.mp3"`

Then use sessions_send to deliver the audio file.

## /voice command

When user sends `/voice some text`, call exec with tts_edge.py to generate voice and send it back.

## Errors

- If exec/STT fails: reply "Не вдалося розпізнати голос. Спробуй ще раз або надішли текстом."
- First STT run downloads ~461MB model (may take 1-2 minutes)
