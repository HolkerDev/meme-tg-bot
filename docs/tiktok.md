# TikTok cookies

Public TikTok videos use yt-dlp without authentication by default. Some posts
require a logged-in session, including posts TikTok marks as sensitive. Set
`TIKTOK_COOKIES_FILE` to a Netscape-format cookie file to let the TikTok handler
use that session. Other yt-dlp handlers do not receive these cookies.

The cookie file is a session credential. Keep it out of Git and readable only
by the bot's user. The repository ignores `tiktok-cookies.txt` and `.env`.

To refresh it, log in to TikTok in Chromium, then use gallery-dl's domain-scoped
browser cookie reader to write a Netscape file. Install `gallery-dl` and
`secretstorage` in a local Python environment first. Adjust the Chromium
profile path if needed:

```python
from http.cookiejar import MozillaCookieJar
from pathlib import Path
from gallery_dl.cookies import load_cookies

path = Path("tiktok-cookies.txt")
cookies = load_cookies((
    "chromium", str(Path.home() / ".config/chromium/Profile 1"),
    "gnomekeyring", None, "tiktok.com",
))
assert cookies and all(
    c.domain == "tiktok.com" or c.domain.endswith(".tiktok.com")
    for c in cookies
)
jar = MozillaCookieJar(str(path))
for cookie in cookies:
    jar.set_cookie(cookie)
jar.save(ignore_discard=True)
path.chmod(0o600)
```

Check that the exported file contains a `sessionid` cookie without exposing
its value. Copy the file to the Pi, set
`TIKTOK_COOKIES_FILE=/home/holker/Projects/meme-tg-bot/tiktok-cookies.txt` in
the Pi's `.env`, and restart the bot. A login or verification prompt in TikTok
may require refreshing the session again.

Verify without downloading media:

```bash
uv run yt-dlp --cookies tiktok-cookies.txt -F 'https://vm.tiktok.com/ZSg3yVDkJ/'
```

The [yt-dlp cookie FAQ](https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp)
notes that its browser export copies cookies for every site. Keep the export
scoped to TikTok.
