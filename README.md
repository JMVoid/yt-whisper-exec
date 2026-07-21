# YT Whisper

A command-line tool for transcribing audio from YouTube videos into text using Whisper-based transcription services.

## Features

- **Audio Download**: Downloads audio from YouTube videos using pytubefix
- **Audio Transcription**: Transcribes audio to text using Deepgram API
- **Extensive Language Support**: Supports 35+ languages for transcription with auto-detection
- **Smart Audio Processing**: Splits long audio files for optimal transcription quality
- **Concurrent Processing**: Uses multi-threading for faster transcription of audio segments

## Requirements

- Python 3.10+
- ffmpeg (for audio processing)
- Deepgram API key (for transcription)

## Installation

### Build from Source

To build the executable, run:

```bash
pyinstaller yt-whisper.spec --clean
```

After compilation, the executable will be located at:
- **Linux/macOS**: `dist/yt-whisper/yt-whisper`
- **Windows**: `dist/yt-whisper/yt-whisper.exe`

> **Note**: The `--clean` flag removes temporary build files before compilation for a clean build.

## Usage

### Command-line Usage

```bash
yt-whisper <URL> [--lang LANG]
```

**Arguments:**
- `URL` (required): The full URL of the YouTube video
- `--lang` (optional): Language code for transcription. If not specified, auto-detection is used.

**Example:**
```bash
./yt-whisper "https://www.youtube.com/watch?v=xxxxx" --lang zh
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
- Configure proxy settings in `.env` file
- Format: `YT_DL_PROXY=http://username:password@ip:port`

**3. Transcription fails with "WHISPER_PROVIDER and WHISPER_API_KEY must be set"**
- Ensure `WHISPER_PROVIDER` and `WHISPER_API_KEY` are set in your `.env` file

**4. Invalid language code warning**
- The specified language code is not supported. Auto-detection will be used instead.

## License

MIT License
