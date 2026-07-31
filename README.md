# YT Whisper

A command-line tool for transcribing audio from YouTube videos into text using Whisper-based transcription services.

## Features

- **Audio Download**: Downloads audio from YouTube videos using yt-dlp
- **Audio Transcription**: Transcribes audio to text using Deepgram API
- **Extensive Language Support**: Supports 35+ languages for transcription with auto-detection
- **Smart Audio Processing**: Splits long audio files for optimal transcription quality
- **Concurrent Processing**: Uses multi-threading for faster transcription of audio segments
- **Cookie Authentication**: Supports Chrome cookie files for YouTube authentication (bypasses bot detection without proxy)

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- ffmpeg (for audio processing)
- Deepgram API key (for transcription)

## Installation

### 1. Install Dependencies

First, install project dependencies using `uv`:

```bash
uv sync
```

### 2. Build Executable

To build the standalone binary, run:

```bash
uv run pyinstaller yt-whisper.spec --clean
```

After compilation, the executable will be located at:
- **Linux/macOS**: `dist/yt-whisper`
- **Windows**: `dist/yt-whisper.exe`

> **Note**: The `--clean` flag removes temporary build files before compilation for a clean build. PyInstaller uses the `uv`-managed virtual environment to resolve dependencies.

## Usage

### Command-line Usage

```bash
yt-whisper <URL> [--lang LANG] [--cookies PATH]
```

**Arguments:**
- `URL` (required): The full URL of the YouTube video
- `--lang` (optional): Language code for transcription. If not specified, auto-detection is used.
- `--cookies` (optional): Path to a Chrome/Netscape-format cookies file for YouTube authentication. When this option is used, proxy is automatically disabled.

**Examples:**
```bash
# Basic usage with language specified
./yt-whisper "https://www.youtube.com/watch?v=xxxxx" --lang zh

# Use Chrome cookies file for authentication (bypass bot detection without proxy)
./yt-whisper "https://www.youtube.com/watch?v=xxxxx" --cookies /tmp/youtube_cookies.txt
```

### Environment Configuration

Create a `.env` file in the same directory as the executable to configure settings:

```env
# Transcription Service (Required)
WHISPER_PROVIDER=deepgram
WHISPER_API_KEY=your-api-key-here

# Proxy Configuration (Optional)
# Use this if you encounter 'Bot Detection' errors when accessing YouTube
# Format: "http://ip:port" or "http://username:password@ip:port"
YT_DL_PROXY=http://your-proxy-server:port
```

> **Note**: The `.env` file will be automatically bundled with the executable during PyInstaller build.

### Proxy vs Cookie Authentication

You can authenticate YouTube access in two mutually exclusive ways:

| Method | Configuration | When to Use |
|--------|---------------|-------------|
| **Proxy** | Set `YT_DL_PROXY` in `.env` | When you have a proxy server |
| **Cookies** | `--cookies /path/to/cookies.txt` | When you have Chrome cookies exported |

> **Important**: When `--cookies` is provided, `YT_DL_PROXY` is **automatically disabled**. The two methods cannot be combined.

To export cookies from Chrome, use a browser extension (e.g., "Get cookies.txt LOCALLY") and save as Netscape format.

## Supported Language Codes

The transcription command supports the following language codes:

`en`, `zh`, `es`, `hi`, `ar`, `pt`, `ru`, `ja`, `fr`, `de`, `ko`, `it`, `tr`, `nl`, `pl`, `vi`, `th`, `id`, `ms`, `fa`, `ur`, `bn`, `he`, `fil`, `sv`, `el`, `cs`, `hu`, `da`, `no`, `fi`, `ro`, `uk`, `sr`.

## API Providers

Currently supported transcription providers:
- **Deepgram**: Uses the Nova-2 model for high-quality transcription (supports 35+ languages)

## Output Format

The tool outputs a JSON response with the following structure:

```json
{
  "status": "success",
  "title": "Video Title",
  "description": "Video Description",
  "transcript": "Transcribed text..."
}
```

On error:

```json
{
  "status": "error",
  "reason": "Error message..."
}
```

## Troubleshooting

### Common Issues

**1. "ffmpeg not found" error**
- Install ffmpeg: `sudo apt install ffmpeg` (Linux) or download from https://ffmpeg.org/

**2. "Bot Detection" errors when downloading from YouTube**
- **Option A**: Use cookie authentication: `--cookies /path/to/cookies.txt` (recommended, no proxy needed)
  - Export cookies from Chrome using a browser extension like "Get cookies.txt LOCALLY"
- **Option B**: Configure proxy settings in `.env` file
  - Format: `YT_DL_PROXY=http://username:password@ip:port`
  - Note: Proxy is disabled when `--cookies` is used

**3. Transcription fails with "WHISPER_PROVIDER and WHISPER_API_KEY must be set"**
- Ensure `WHISPER_PROVIDER` and `WHISPER_API_KEY` are set in your `.env` file

**4. Invalid language code warning**
- The specified language code is not supported. Auto-detection will be used instead.

**5. "Cookies file not found" error**
- Ensure the cookies file path provided with `--cookies` exists and is in valid Netscape format

## License

MIT License
