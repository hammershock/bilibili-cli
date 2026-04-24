# bilicli

A read-only Bilibili CLI tool for terminal and agent use.

## Install

```bash
pip install -e .
```

**Requires:** Python 3.9+, `ffmpeg` (for video/audio download only)

**Optional:** `mlx-whisper` (for local speech-to-text on macOS Apple Silicon)

## Usage

### Authentication

```bash
bilicli login          # QR code login (scan with Bilibili app)
bilicli whoami         # Show current user
bilicli logout         # Clear credentials
```

### Browse

```bash
bilicli feed                           # Recommended videos (fresh each run)
bilicli search "keyword"               # Search videos
bilicli search-user "username"         # Search users (UP主)
bilicli user 12345678                  # User profile by UID
bilicli user-videos 12345678           # User's uploaded videos
```

### Video Details

```bash
bilicli video BV1xx411c7mD             # Video info (shows page count if multi-part)
bilicli pages BV1xx411c7mD             # List parts (分P) with CID and duration
bilicli subtitle BV1xx411c7mD          # Subtitles (default: Chinese)
bilicli subtitle-langs BV1xx411c7mD    # List available subtitle languages
bilicli danmaku BV1xx411c7mD           # Bullet comments
bilicli comments BV1xx411c7mD          # Top-level comments (with picture URLs)
bilicli replies BV1xx411c7mD 12345     # Replies under a comment (by rpid)
```

### Download

```bash
bilicli download BV1xx411c7mD              # Download as MP4 (default: 1080p)
bilicli download BV1xx411c7mD -q 4k        # Download at 4K quality
bilicli download BV1xx411c7mD --page 3     # Download specific part of multi-part video
bilicli download BV1xx411c7mD --quiet      # Only print output path (for agent use)
bilicli download-audio BV1xx411c7mD        # Download audio only as M4A (saves bandwidth)
bilicli download-audio BV1xx411c7mD --page 1  # Audio of a specific part
bilicli download-cover BV1xx411c7mD        # Download cover image
```

Quality options: `360p`, `480p`, `720p`, `1080p` (default), `1080p+`, `4k`

Higher qualities require a Bilibili Premium (大会员) account.

### Transcribe

```bash
bilicli transcribe BV1xx411c7mD            # Transcribe audio with mlx-whisper
bilicli transcribe BV1xx411c7mD --page 2   # Transcribe specific part
bilicli transcribe BV1xx411c7mD --lang en  # Transcribe in English
bilicli transcribe BV1xx411c7mD --json     # JSON output with timestamps
```

Requires macOS Apple Silicon and `pip install mlx-whisper`.

### Multi-Part Videos (分P)

Many Bilibili videos have multiple parts. Use `bilicli pages <bvid>` to list them, then `--page N` to target a specific part:

```bash
bilicli pages BV1xx411c7mD                 # List all parts with CID and duration
bilicli download BV1xx411c7mD --page 3     # Download part 3
bilicli download-audio BV1xx411c7mD --page 1  # Audio of part 1
bilicli subtitle BV1xx411c7mD --page 5     # Subtitles for part 5
bilicli danmaku BV1xx411c7mD --page 2      # Danmaku for part 2
bilicli transcribe BV1xx411c7mD --page 1   # Transcribe part 1
```

### Common Options

| Option | Description |
|--------|-------------|
| `--json` | Machine-readable JSON output |
| `-n/--limit` | Max items to return (default varies) |
| `--offset` | Skip first N items |
| `--all` | Return all items |
| `--detail` | Show expanded info (views, date, etc.) |
| `--page N` | Target part N of a multi-part video |
| `-w/--width` | Max text width (0=full, applies to comments/video/user) |
| `--quiet` | Minimal output for agent use (download commands) |
| `-h/--help` | Show help for any command |

### For Agent Use

- Use `--json` for structured output
- Use `--quiet` with `download`/`download-audio`/`download-cover` to get only the file path
- Pagination footer hints guide how to fetch more data
- All listing commands support `--offset`, `-n`, `--all` for controlled data retrieval
- Comment picture URLs are shown inline as `[img] https://...`

## Credentials

Stored at `~/.config/bilicli/cookies.json`.

## Dependencies

- `httpx` — HTTP client
- `click` — CLI framework
- `qrcode` — Terminal QR code display

**Optional:**
- `mlx-whisper` — Local speech-to-text (macOS Apple Silicon only)

## License

MIT
