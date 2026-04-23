# bilicli

A read-only Bilibili CLI tool for terminal and agent use.

## Install

```bash
pip install -e .
```

**Requires:** Python 3.9+, `ffmpeg` (for video download only)

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
bilicli video BV1xx411c7mD             # Video info
bilicli subtitle BV1xx411c7mD          # Subtitles (default: Chinese)
bilicli subtitle-langs BV1xx411c7mD    # List available subtitle languages
bilicli danmaku BV1xx411c7mD           # Bullet comments
bilicli comments BV1xx411c7mD          # Top-level comments
bilicli replies BV1xx411c7mD 12345     # Replies under a comment (by rpid)
```

### Download

```bash
bilicli download BV1xx411c7mD              # Download as MP4 (default: 1080p)
bilicli download BV1xx411c7mD -q 4k        # Download at 4K quality
bilicli download BV1xx411c7mD --quiet      # Only print output path (for agent use)
bilicli cover BV1xx411c7mD                 # Download cover image
```

Quality options: `360p`, `480p`, `720p`, `1080p` (default), `1080p+`, `4k`

Higher qualities require a Bilibili Premium (大会员) account.

### Common Options

| Option | Description |
|--------|-------------|
| `--json` | Machine-readable JSON output |
| `-n/--limit` | Max items to return (default varies) |
| `--offset` | Skip first N items |
| `--all` | Return all items |
| `--detail` | Show expanded info (views, date, etc.) |
| `-w/--width` | Max text width (0=full, applies to comments/video/user) |
| `--quiet` | Minimal output for agent use (download/cover) |
| `-h/--help` | Show help for any command |

### For Agent Use

- Use `--json` for structured output
- Use `--quiet` with `download`/`cover` to get only the file path
- Pagination footer hints guide how to fetch more data
- All listing commands support `--offset`, `-n`, `--all` for controlled data retrieval

## Credentials

Stored at `~/.config/bilibili-cli/cookies.json`.

## Dependencies

- `httpx` — HTTP client
- `click` — CLI framework
- `qrcode` — Terminal QR code display

## License

MIT
