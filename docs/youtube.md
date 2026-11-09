# YouTube cookies

Set `YOUTUBE_COOKIES_FILE` to a Netscape-format cookie file exported from a
logged-in YouTube browser session. The bot passes this file to yt-dlp for
YouTube links only. Without this setting, downloads use no cookies.

Copy the exported file to the bot host as `youtube-cookies.txt`, restrict its
permissions with `chmod 600 youtube-cookies.txt`, and set an absolute path in
the host's `.env`:

```dotenv
YOUTUBE_COOKIES_FILE=/home/holker/Projects/meme-tg-bot/youtube-cookies.txt
```

Restart the bot after changing the setting. Keep the cookie file private;
`youtube-cookies.txt` and `.env` are ignored by Git. Replace the file when the
session expires or YouTube asks for a fresh login.

## JavaScript runtime on the Pi

YouTube challenge solving also needs a JavaScript runtime. Deno is installed
at `/home/holker/.local/bin/deno` on the Pi. Keep that directory in the bot's
`PATH` when restarting it:

```bash
export PATH="$HOME/.local/bin:$PATH"
cd /home/holker/Projects/meme-tg-bot
uv run meme-nova
```

The project's `yt-dlp[default]` dependency includes the companion challenge
solver scripts. See the [yt-dlp JavaScript setup guide](https://github.com/yt-dlp/yt-dlp/wiki/EJS).
Missing runtime support can produce `n challenge solving failed` followed by
`No video formats found`, even with valid cookies.

YouTube often offers separate video and audio streams. The bot prefers streams
up to 720p and uses FFmpeg to merge them into one MP4 before uploading. FFmpeg
must be available in the bot's `PATH`.

Verify with a real video URL without downloading media:

```bash
uv run yt-dlp --cookies youtube-cookies.txt -F 'https://www.youtube.com/watch?v=<id>'
```
