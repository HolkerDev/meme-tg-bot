# Instagram downloads

How the bot fetches Instagram posts, what breaks, and how the current setup avoids it.

## Pipeline

```
Instagram URL
    │
    ├─► yt-dlp (+ Chrome TLS impersonation, no cookies)
    │       └─► reels / videos  ✓
    │       └─► photo-only posts → "There is no video in this post"
    │
    └─► gallery-dl fallback (+ Netscape cookies file)
            └─► photos / carousels  ✓ (needs valid session)
```

Code: `src/meme_nova/platforms/instagram.py` → fallback in `gallery_dl.py`.

| Content | Tool | Auth |
|---------|------|------|
| Reel / video | yt-dlp | Browser impersonation via `curl_cffi` — **no cookies** |
| Photo / carousel | gallery-dl | `INSTAGRAM_COOKIES_FILE` (Netscape cookies) |

## Why videos need impersonation (not cookies)

Instagram rejects ordinary Python TLS fingerprints. Anonymous API calls without browser-like TLS fail with errors such as:

- `Instagram sent an empty media response`
- `Requested content is not available, rate-limit reached or login required`
- `Main webpage is locked behind the login page`

**Fix:** depend on `yt-dlp[curl-cffi,default]` and pass

```python
"impersonate": ImpersonateTarget.from_str("chrome")
```

into `YoutubeDL` options. The Python API needs an `ImpersonateTarget` object — a plain `"chrome"` string raises an assertion error.

With impersonation, **public** reels usually work without logging in.

## Why we do not pass cookies to yt-dlp

Stale, challenged, or browser-exported sessions often make the **logged-in** Instagram API path worse:

- With cookies → `HTTP 404` / empty media on `/media/{id}/info/`
- Without cookies + impersonate → same public reel downloads fine

So cookies are **only** passed to gallery-dl. yt-dlp stays cookie-free on purpose.

## Why photos need cookies

yt-dlp is video-oriented. Photo posts fail with `There is no video in this post`, then the bot falls back to gallery-dl.

gallery-dl without a session hits:

```text
HTTP redirect to login page (https://www.instagram.com/accounts/login/)
```

A Netscape cookies file with a live `sessionid` fixes that for public photo posts.

## Cookie file setup

Env: `INSTAGRAM_COOKIES_FILE=/absolute/path/to/instagram-cookies.txt`

Prefer exporting from a real browser (burner account), not the password script — Instagram often returns a security checkpoint on scripted login.

### Export from Chrome (recommended)

On a machine where you are logged into Instagram in Chrome:

```bash
uv run yt-dlp --cookies-from-browser chrome --cookies /tmp/ig-cookies-full.txt --skip-download "https://www.instagram.com/"
```

`Unsupported URL` on the homepage is expected; cookies are still written. Optionally keep only Instagram rows, then copy to the bot host:

```bash
# filter to .instagram.com (optional but cleaner)
# then:
scp instagram-cookies.txt holker@bot-host:/path/to/meme-tg-bot/instagram-cookies.txt
```

Confirm:

```bash
grep -E 'sessionid|csrftoken|ds_user_id' instagram-cookies.txt
```

Restart the bot after updating the file (settings are loaded at process start).

### Password export script (fragile)

`scripts/export_instagram_cookies.py` / `make cookies` can work, but often fails with:

```text
Instagram requires a security checkpoint: /auth_platform/?apc=...
```

Clear the checkpoint in a browser, then prefer browser cookie export instead.

### Cron refresh — disabled

A weekly cron used to run `export_instagram_cookies.py` and overwrite `instagram-cookies.txt`. That conflicted with good browser cookies (weak/challenged sessions). **Remove it** if reintroduced; refresh cookies manually when gallery-dl starts failing login redirects.

## Common errors

| Symptom | Meaning | What to do |
|---------|---------|------------|
| `empty media response` / login required (yt-dlp) | Missing impersonation or TLS blocked | Ensure `curl_cffi` installed; `impersonate` set |
| `ImpersonateTarget` / assertion on `"chrome"` | Wrong Python API type | Use `ImpersonateTarget.from_str("chrome")` |
| yt-dlp `404` **with** cookies | Bad session on logged-in API | Do not pass cookies to yt-dlp |
| `There is no video in this post` | Photo/carousel | Expected; gallery-dl fallback |
| gallery-dl → login page / home redirect | Missing or dead cookies | Re-export browser cookies; restart bot |
| Script `checkpoint_url` / `/auth_platform/` | Instagram blocked scripted login | Clear in browser; use `--cookies-from-browser` |

## Verify on the host

```bash
# Video path (no cookies)
uv run yt-dlp --impersonate chrome -F "https://www.instagram.com/reel/<id>/"

# Photo path (with cookies)
uv run python -m gallery_dl --cookies "$INSTAGRAM_COOKIES_FILE" "https://www.instagram.com/p/<id>/"

# What the bot loads
uv run python -c "
from meme_nova.settings import Settings
from pathlib import Path
s = Settings.load()
print(s.instagram_cookies_file, Path(s.instagram_cookies_file or '').is_file())
"
```

## Operational notes

- Use a **burner** Instagram account for gallery-dl cookies; avoid your main account.
- Absolute path for `INSTAGRAM_COOKIES_FILE` avoids cwd issues under systemd/tmux.
- After Instagram challenges the account, re-export cookies; do not keep retrying the password script in a loop (rate limits / more checkpoints).
- `INSTAGRAM_SESSION_FILE` is legacy and unused.
- `INSTAGRAM_USERNAME` / `INSTAGRAM_PASSWORD` are unused by yt-dlp in the current handler (cookies go to gallery-dl only).
