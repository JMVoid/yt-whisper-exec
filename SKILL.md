---
name: yt-whisper
description: "Transcribe YouTube videos to text via Deepgram Whisper — downloads audio, splits, transcribes in parallel."
version: 0.2.0
---

# yt-whisper — YouTube Audio Transcription

Downloads audio from YouTube videos (via pytubefix), splits into chunks, and transcribes via Deepgram's Nova-2 Whisper model. Designed as the **fallback** when no subtitles are available on a video.

## When to Use

When an AI agent needs text from a YouTube video that has **no subtitles**. This is Step 2 of the summarization pipeline (after `yt-dl-subtitle` returns empty).

## Quick Start

```bash
# Using compiled binary:
./dist/yt-whisper "https://www.youtube.com/watch?v=VIDEO_ID" --lang zh

# Using Python directly:
python3 cli.py "https://www.youtube.com/watch?v=VIDEO_ID" --lang zh
```

The URL is a **positional argument**. `--lang` is optional (auto-detect if omitted).

## Pipeline

```
pytubefix download audio
    → ffmpeg split into 480-second chunks
    → 4-thread concurrent Deepgram transcription
    → merged transcript text
```

## Environment Configuration (`.env`)

```
WHISPER_PROVIDER=deepgram          # Required: deepgram, cloudflare, groq
WHISPER_API_KEY=your-api-key       # Required: Deepgram API key
YT_DL_PROXY=http://proxy:port      # Optional: proxy for YouTube access
```

Both `WHISPER_PROVIDER` and `WHISPER_API_KEY` must be set. Currently only **Deepgram** is fully implemented (Cloudflare and Groq are stubs).

## Requirements

- Python 3.11+
- **ffmpeg** installed (`sudo apt install ffmpeg`)
- Deepgram API key
- Dependencies: `pytubefix`, `deepgram-sdk>=0.4.0`, `python-dotenv`

## Output Format

Success:
```json
{
  "status": "success",
  "title": "Video Title",
  "description": "Video description text...",
  "transcript": "Full transcribed text..."
}
```

Failure:
```json
{
  "status": "error",
  "reason": "WHISPER_PROVIDER and WHISPER_API_KEY environment variables must be set"
}
```

## Supported Languages (35+)

`en`, `zh`, `es`, `hi`, `ar`, `pt`, `ru`, `ja`, `fr`, `de`, `ko`, `it`, `tr`, `nl`, `pl`, `vi`, `th`, `id`, `ms`, `fa`, `ur`, `bn`, `he`, `fil`, `sv`, `el`, `cs`, `hu`, `da`, `no`, `fi`, `ro`, `uk`, `sr`

Invalid codes trigger a warning and fall back to auto-detection.

## Project Structure

```
yt-whisper-exec/
├── cli.py                         # CLI entry point
├── whisper/
│   ├── whisper_deepgram.py        # Deepgram transcription (Nova-2)
│   └── whisper_cf.py              # Cloudflare stub (not implemented)
├── youtube/
│   └── yt_audio_dl.py             # Audio download via pytubefix
├── utils/
│   ├── constant.py                # MAX_WORKERS_NUMBER, defaults
│   └── utils.py                   # Shared utilities
├── dist/yt-whisper                # Pre-built standalone executable
└── pyproject.toml
```

## Error Handling for Agents

| Situation | Output | Agent Action |
|-----------|--------|-------------|
| Transcription succeeds | `status: "success"` with transcript | Proceed with content |
| Missing API key | `status: "error"`, reason explains | Tell user to configure `.env` |
| ffmpeg not found | Download fails | Install ffmpeg: `sudo apt install ffmpeg` |
| pytubefix blocked | Bot detection error | Check `YT_DL_PROXY` is set |
| Invalid language code | Warning logged, auto-detect used | Transcript still succeeds |
| Unsupported provider | `status: "error"` | Only `deepgram` is implemented |

## Troubleshooting

1. **"ffmpeg not found"** → `sudo apt install ffmpeg`
2. **Bot detection on YouTube** → configure `YT_DL_PROXY` in `.env`
3. **"WHISPER_PROVIDER and WHISPER_API_KEY must be set"** → create `.env` with both values
4. **Transcription timeout** → the tool uses a heartbeat every 30s to keep long transcriptions alive; if it still times out, check network/API quota

## Related

- **First try**: yt-dl-subtitle (subtitle extraction — faster, no API key needed)
- **Orchestration**: youtube-tools skill defines the full pipeline: subtitle → audio → whisper
- **Home in Hermes**: `~/hermes/youtube-data/yt-whisper-exec/`
