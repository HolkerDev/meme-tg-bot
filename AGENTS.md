# Agent notes

## Project docs

Operational and domain knowledge lives in [`docs/`](docs/). Read the relevant
doc before changing related behavior.

Notable entries:

- [`docs/instagram.md`](docs/instagram.md) — Instagram download pipeline
  (yt-dlp + impersonation for video, gallery-dl + cookies for photos), failure
  modes, and cookie refresh.

## Skills

Project skills live in [`.cursor/skills/`](.cursor/skills/). Read the matching
`SKILL.md` when the task fits its description.

- [`ssh-pi`](.cursor/skills/ssh-pi/SKILL.md) — SSH / deploy / restart the bot on
  the Raspberry Pi (`192.168.0.8`).
