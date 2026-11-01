# Agent notes

## Main chat

The main Telegram chat is **Memeproxy**, chat ID `-1002564248375`. Use the chat
ID for chat-specific behavior; the title may change.

## Project docs

Operational and domain knowledge lives in [`docs/`](docs/). Read the relevant
doc before changing related behavior.

Notable entries:

- [`docs/instagram.md`](docs/instagram.md) — Instagram download pipeline
  (yt-dlp + impersonation for video, gallery-dl + cookies for photos), failure
  modes, and cookie refresh.
- [`docs/tiktok.md`](docs/tiktok.md) — TikTok cookie file setup for posts that
  require a logged-in session.
- [`docs/super-likes.md`](docs/super-likes.md) — Main-chat Super Like button,
  daily limit, leaderboard totals, and migration.

## Skills

Project skills live in [`.cursor/skills/`](.cursor/skills/). Read the matching
`SKILL.md` when the task fits its description.

- [`ssh-pi`](.cursor/skills/ssh-pi/SKILL.md) — SSH / deploy / restart the bot on
  the Raspberry Pi (`192.168.0.8`).
