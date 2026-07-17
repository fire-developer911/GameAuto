# PS4 Games Telegram Scraper

A production-ready scraper that downloads PS4 game metadata from the Telegram PS4 Library Bot using the **official Telegram API**.

## Features

- ✅ **Official Telegram API** - Uses Telethon, the standard Python library for official Telegram client automation
- ✅ **Persistent Sessions** - Login once, subsequent runs don't require code re-entry
- ✅ **Resume Support** - Crashes are survivable; scraper resumes from where it left off
- ✅ **Atomic Database Writes** - `games.json` is always valid JSON, updated immediately after each game
- ✅ **Robust Parsing** - Flexible field extraction that adapts to future bot changes
- ✅ **File Downloads** - Torrents and cover images stored locally with Telegram file IDs
- ✅ **Error Tracking** - Failed game IDs logged for manual inspection
- ✅ **Local Search API** - HTTP server with game search, no Telegram communication required
- ✅ **Exponential Backoff** - Automatic retry with rate limit handling
- ✅ **Comprehensive Logging** - Detailed logs for debugging and monitoring

## Architecture

```
ps4_scraper/
├── config.json                 # Configuration (API credentials, ranges)
├── main.py                     # Entry point
├── scraper.py                  # Main scraper orchestrator
├── telegram_client.py          # Telethon wrapper with message collection
├── parser.py                   # Game metadata parser (flexible field extraction)
├── database.py                 # games.json manager (atomic writes)
├── downloader.py               # Torrent/cover file downloader
├── resume.py                   # Progress tracking (progress.json, failed.json)
├── server.py                   # Local HTTP search API
├── requirements.txt            # Python dependencies
└── data/
    ├── games.json             # Main game database (auto-created)
    ├── progress.json          # Scraping resume point (auto-created)
    ├── failed.json            # Failed game IDs (auto-created)
    ├── torrents/              # Downloaded .torrent files
    └── covers/                # Downloaded cover images
```

## Installation

### 1. Get Official Telegram API Credentials

Visit **https://my.telegram.org/auth** and log in with your Telegram account.

1. Click **"API development tools"** in the left menu
2. Create a new application (fill in any name, e.g., "PS4 Scraper")
3. Copy your **API ID** and **API Hash** - these are long strings
4. Keep them private (like passwords)

### 2. Clone and Setup

```bash
git clone <repo-url>
cd ps4_scraper

# Install Python 3.9+
python3 --version

# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure

Edit `config.json`:

```json
{
  "telegram": {
    "api_id": 12345678,
    "api_hash": "abcdefg1234567890abcdefg1234567",
    "phone": "+1234567890"
  },
  "bot": {
    "username": "PS4_library_bot",
    "activation_password": "rome"
  },
  "scraping": {
    "first_id": 1,
    "last_id": 3912,
    "retry_attempts": 3,
    "retry_delay_base": 2,
    "message_wait_timeout": 30
  },
  "folders": {
    "data_dir": "data",
    "torrents_dir": "data/torrents",
    "covers_dir": "data/covers",
    "logs_dir": "logs"
  },
  "server": {
    "host": "127.0.0.1",
    "port": 8080
  }
}
```

**Configuration Details:**

- `api_id`, `api_hash`: From https://my.telegram.org
- `phone`: Your Telegram account phone (with country code, e.g., `+1234567890`)
- `first_id`, `last_id`: Game ID range to scrape (default: 1-3912)
- `message_wait_timeout`: Seconds to wait for bot response (default: 30)
- `server.port`: Port for search API (default: 8080)

## Usage

### First Run - Login

```bash
python3 main.py scrape
```

On first run, you'll be prompted:

1. Telethon generates a login link or asks for verification
2. Follow the prompts (may require entering a login code from Telegram)
3. Session is saved (you won't need to login again)
4. Scraper activates the bot with "rome"
5. Scraping begins from game ID 1

### Resume After Interruption

```bash
python3 main.py scrape
```

Scraper automatically resumes from the last completed game ID (stored in `progress.json`).

### Start Fresh (Ignore Previous Progress)

```bash
python3 main.py scrape --no-resume
```

### Run Search Server

```bash
python3 main.py server
```

Server runs on `http://127.0.0.1:8080`

## Search API

### Get All Games

```bash
curl http://127.0.0.1:8080/games
```

Response:
```json
{
  "1": {
    "id": 1,
    "title": "2Dark",
    "year": "2017",
    "genre": "Horror Adventure",
    ...
  },
  ...
}
```

### Get Specific Game

```bash
curl http://127.0.0.1:8080/games/1
```

### Search by Title

```bash
curl "http://127.0.0.1:8080/search?q=Dark"
```

Searches are:
- Case-insensitive
- Partial matching (e.g., "FC" matches "FIFA" and "AFC")
- Local only (no Telegram API calls)

Response:
```json
{
  "query": "Dark",
  "count": 5,
  "results": {
    "1": { "title": "2Dark", ... },
    "42": { "title": "Dark Souls", ... }
  }
}
```

### Download Files

```bash
# Cover image
curl -O http://127.0.0.1:8080/covers/1.jpg

# Torrent file
curl -O http://127.0.0.1:8080/torrents/1.torrent
```

## Database Format

### games.json

Automatically created and updated. Always valid JSON.

```json
{
  "1": {
    "id": 1,
    "title": "2Dark",
    "year": "2017",
    "genre": "Horror Adventure Stealth",
    "developer": "Gloomywood",
    "publisher": "Bigben Interactive",
    "cusa": "CUSA04802",
    "region": "EUR",
    "version": "1.00",
    "firmware": "4.00",
    "interface_languages": "English, German, Italian, French, Spanish, Japanese, Portuguese (Brazil), Polish",
    "voice_languages": "English",
    "players": "1",
    "rating": "3.42",
    "ranking": "852",
    "release_type": "Full",
    "tested": "No",
    "torrent": {
      "filename": "2Dark [EUR, ENG] (v1.00) [397.8 MB]",
      "size": 416534528,
      "telegram_file_id": "BQADBAADzq...",
      "local_path": "data/torrents/1.torrent"
    },
    "cover": {
      "telegram_file_id": "AgADBAADzq...",
      "local_path": "data/covers/1.jpg"
    },
    "metadata": { ... },
    "raw_cover_text": "...",
    "scraped_at": "2024-01-15T12:34:56.789012"
  },
  "2": { ... }
}
```

### Template JSON for Games.json

```json
{
  "123": {
    "id": 123,
    "title": "Game Title",
    "year": "2020",
    "genre": "Action Adventure",
    "developer": "Developer Name",
    "publisher": "Publisher Name",
    "cusa": "CUSAXXXXX",
    "region": "EUR",
    "version": "1.00",
    "firmware": "4.00",
    "interface_languages": "English, French, German",
    "voice_languages": "English",
    "players": "1-4",
    "rating": "4.50",
    "ranking": "100",
    "release_type": "Full",
    "tested": "Yes",
    "torrent": {
      "filename": "game_title.torrent",
      "size": 4294967296,
      "telegram_file_id": "BQADBAADzq...",
      "local_path": "data/torrents/123.torrent"
    },
    "cover": {
      "telegram_file_id": "AgADBAADzq...",
      "local_path": "data/covers/123.jpg"
    },
    "metadata": {
      "additional_field_1": "value",
      "additional_field_2": "value"
    },
    "raw_cover_text": "Full bot response text",
    "scraped_at": "2024-01-15T12:34:56.789012"
  }
}
```

### progress.json

Tracks scraping progress for resuming.

```json
{
  "last_completed": 1578,
  "updated": "2024-01-15T12:34:56.789012"
}
```

### failed.json

Lists games that failed to scrape.

```json
{
  "failed_ids": [42, 89, 256],
  "updated": "2024-01-15T12:34:56.789012"
}
```

## Logs

All logs written to `logs/scraper.log` and stdout.

```
2024-01-15 12:34:56,789 - root - INFO - Scraping /download1
2024-01-15 12:34:57,123 - root - INFO - Game 1: Torrent downloaded (416534528 bytes)
2024-01-15 12:34:58,456 - root - INFO - Scraping /cover1
2024-01-15 12:34:59,789 - root - INFO - Game 1: Cover downloaded (1048576 bytes)
2024-01-15 12:35:01,012 - root - INFO - Game 1: Successfully scraped and saved
```

## Parser Design

The parser is **flexible and future-proof**:

- ❌ Does NOT hardcode field positions
- ✅ Matches field labels dynamically (e.g., "Genre:", "Genre :")
- ✅ Preserves unknown fields in `metadata`
- ✅ Adapts if bot changes field order or introduces new fields

Field patterns are in `parser.py` and use regex for robust matching.

## Error Handling

### Exponential Backoff

Failed commands retry automatically:
- Attempt 1: immediate
- Attempt 2: after 2 seconds
- Attempt 3: after 4 seconds

### FloodWait

If Telegram returns `FloodWaitError`, scraper:
1. Logs the wait duration
2. Sleeps for exactly that long
3. Retries the command

### Failed Games

Games that fail after all retries are:
1. Logged to `failed.json`
2. Skipped in the current run
3. Can be retried manually or in next run (with `--no-resume`)

## Troubleshooting

### "API ID and API Hash must be configured"

Edit `config.json` and fill in values from https://my.telegram.org

### "Invalid phone number"

Phone must include country code (e.g., `+1234567890`, not `1234567890`)

### "Login failed"

1. Ensure phone and credentials are correct
2. Delete `sessions/` directory to force re-login
3. Check that 2FA is not blocking login

### "No response from bot"

- Bot may be temporarily unavailable
- Increase `message_wait_timeout` in config
- Check bot is online: https://t.me/PS4_library_bot

### "Torrent file is empty"

- Telegram download may have failed
- Try again (will resume from last game)
- Check disk space

### "Database corruption"

If `games.json` becomes invalid:
1. Backup the corrupted file: `cp data/games.json data/games.json.backup`
2. Delete `data/games.json`
3. Reset progress: `rm data/progress.json`
4. Run scraper with `--no-resume`

## Performance

- **Speed**: ~2-3 games per minute (respects Telegram rate limits)
- **Database**: Atomic writes mean zero data loss on crash
- **Storage**: ~100 KB per game (torrents 300-500 MB, covers 1-5 MB)

## Advanced

### Change Scrape Range

Edit `config.json`:

```json
{
  "scraping": {
    "first_id": 1000,
    "last_id": 2000
  }
}
```

Then run:

```bash
python3 main.py scrape --no-resume
```

### Manual Retry of Failed Games

Scraper automatically skips failed games. To retry:

```bash
# Delete failed list to retry
rm data/failed.json

# Run scraper
python3 main.py scrape
```

### Search Multiple Servers

Run multiple `server` instances on different ports:

```bash
# Terminal 1
python3 main.py server  # port 8080

# Terminal 2
sed -i 's/"port": 8080/"port": 8081/' config.json
python3 main.py server  # port 8081
```

## Dependencies

- **telethon** - Official Telegram client API library
- **aiohttp** - Async HTTP server
- **Pillow** - Image handling (optional, for future image processing)
- **python-dotenv** - Environment variable support

All specified in `requirements.txt`.

## License

MIT License - feel free to use, modify, and distribute.

## Support

- Issues? Check logs in `logs/scraper.log`
- Database corrupt? Delete `data/games.json` and resume
- Session broken? Delete `sessions/` directory
- Still stuck? Check Telegram bot status: https://t.me/PS4_library_bot

## Bot Link

Bot: https://t.me/PS4_library_bot

## Legal

This scraper respects official Telegram API terms:
- Uses only official APIs (no web scraping)
- No account abuse or automation tricks
- Respects rate limits
- Follows Telegram ToS

Use responsibly.
