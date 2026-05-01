# meme-nova

Telegram bot.

## Setup

```bash
uv sync
cp .env.example .env
# edit .env, paste token from @BotFather
```

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
