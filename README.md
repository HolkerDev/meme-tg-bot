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
Use a burner account, not your main.

Two ways to authenticate:

**A. Interactive CLI login (preferred, supports 2FA):**

```bash
uv run instaloader -l YOUR_INSTAGRAM_USERNAME
# completes interactive login, writes session file to instaloader's default path.
```

Then set `INSTAGRAM_USERNAME` in `.env`.

**B. Username + password from env (no 2FA support):**

Set `INSTAGRAM_USERNAME` and `INSTAGRAM_PASSWORD`. On startup the bot tries the
session file first; if missing it logs in with the password and saves a session
file so subsequent runs don't re-login. Programmatic login is more block-prone
than option A — Instagram may flag suspicious activity, requiring a manual
checkpoint clearance via the app/web. If the account has 2FA, this path will
fail and you must use option A.

`INSTAGRAM_SESSION_FILE` is optional — leave empty to use instaloader's default
location, or set an absolute path if you stored the file elsewhere.

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
