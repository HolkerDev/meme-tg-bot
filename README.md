# meme-nova

Telegram bot.

## Setup

```bash
uv sync
cp .env.example .env
# edit .env, paste token from @BotFather
```

### Instagram

Videos use yt-dlp with Chrome TLS impersonation (no cookies). Photos fall back
to gallery-dl and need `INSTAGRAM_COOKIES_FILE`. Details, failure modes, and
cookie refresh: [docs/instagram.md](docs/instagram.md).

### YouTube

Set `YOUTUBE_COOKIES_FILE` to a Netscape-format cookie file to use a browser
session for YouTube downloads. Setup: [docs/youtube.md](docs/youtube.md).

## Run

```bash
uv run meme-nova
# or
uv run python -m meme_nova
```

## Dev

```bash
uv run pytest
uv run ruff check .
uv run ruff format .
uv run mypy
```
