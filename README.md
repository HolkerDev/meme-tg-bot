# meme-nova

Telegram bot.

## Setup

```bash
uv sync
cp .env.example .env
# edit .env, paste token from @BotFather
```

### Optional: Instagram login

Public posts often work without login but Instagram rate-limits anonymous fetches.
To use a logged-in session:

```bash
uv run instaloader -l YOUR_INSTAGRAM_USERNAME
# completes interactive login, writes session file to instaloader's default path.
```

Then set `INSTAGRAM_USERNAME` in `.env` (and optionally `INSTAGRAM_SESSION_FILE` if you
moved the file). The bot loads the session at startup; if missing it logs a warning and
proceeds unauthenticated.

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
