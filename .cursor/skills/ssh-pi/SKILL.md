---
name: ssh-pi
description: >-
  SSH into the meme-tg-bot Raspberry Pi host, run remote commands, deploy files,
  restart the bot in tmux, and verify Instagram downloads on the Pi. Use when the
  user mentions the Pi, raspberrypi, 192.168.0.8, remote bot host, deploy to
  server, or asks to check/restart the bot on the LAN machine.
---

# SSH to Pi (meme-tg-bot)

## Connection

| | |
|---|---|
| Host | `PI_SSH_HOST` in `.env` (default `192.168.0.8`) |
| User | `PI_SSH_USER` in `.env` (default `holker`) |
| Password | `PI_SSH_PASSWORD` in `.env` |
| Hostname (prompt) | `raspberrypi` |
| Project | `/home/holker/Projects/meme-tg-bot` |

Credentials live in the **local** (gitignored) `.env` at the repo root:

```bash
PI_SSH_HOST=192.168.0.8
PI_SSH_USER=holker
PI_SSH_PASSWORD=…
```

Load them before SSH (do not commit `.env` or paste the password into skills/docs):

```bash
cd "$(git rev-parse --show-toplevel)"
set -a && source .env && set +a
export SSHPASS="$PI_SSH_PASSWORD"
sshpass -e ssh -o StrictHostKeyChecking=accept-new \
  "${PI_SSH_USER}@${PI_SSH_HOST}" '…'
sshpass -e scp -o StrictHostKeyChecking=accept-new \
  LOCAL "${PI_SSH_USER}@${PI_SSH_HOST}:REMOTE"
```

If `PI_SSH_PASSWORD` is missing/empty, ask the user — do not invent a password.

Note: Instagram passwords in `.env` may contain shell metacharacters; if
`source .env` errors, load only the Pi vars, e.g.
`export $(grep -E '^PI_SSH_' .env | xargs)` (still avoid echoing secrets).

`uv` on the Pi is at `~/.local/bin` — prefix remote shells:

```bash
export PATH="$HOME/.local/bin:$PATH"
cd /home/holker/Projects/meme-tg-bot
```

## Bot process

The bot is **not** a systemd unit. It runs in **tmux session `0`**:

```bash
# status / recent logs
tmux capture-pane -t 0 -p -S -40

# restart
tmux send-keys -t 0 C-c
sleep 1
tmux send-keys -t 0 'cd /home/holker/Projects/meme-tg-bot && uv run meme-nova' Enter
sleep 3
tmux capture-pane -t 0 -p -S -8   # expect: Starting bot polling
```

## Deploy from Mac workspace

Local repo: workspace root (typically `/Users/holker/src/meme-tg-bot`).

```bash
sshpass -e scp path/to/file \
  "${PI_SSH_USER}@${PI_SSH_HOST}:/home/holker/Projects/meme-tg-bot/path/to/file"
# then restart bot in tmux if runtime code/env changed
```

After `pyproject.toml` / `uv.lock` changes on the Pi: `uv sync`.

## Instagram on the Pi

See [docs/instagram.md](../../../docs/instagram.md).

- Cookies: `/home/holker/Projects/meme-tg-bot/instagram-cookies.txt`
- Env: `INSTAGRAM_COOKIES_FILE` (absolute path); loaded at bot start
- Videos: yt-dlp + impersonation, **no** cookies
- Photos: gallery-dl **with** cookies
- Do **not** reinstall the weekly `export_instagram_cookies.py` cron unless asked

Quick checks:

```bash
uv run yt-dlp --impersonate chrome -F 'https://www.instagram.com/reel/<id>/'
uv run python -m gallery_dl --cookies instagram-cookies.txt 'https://www.instagram.com/p/<id>/'
```

## Habits

- Always load `PI_SSH_*` from `.env`, then `export SSHPASS="$PI_SSH_PASSWORD"` before `sshpass -e`.
- Batch independent remote checks in one SSH invocation when possible.
- Prefer absolute remote paths.
- Do not `git push --force`, skip hooks, or change git config on the Pi unless asked.
- Prefer setting up SSH keys later so `sshpass` is unnecessary.
