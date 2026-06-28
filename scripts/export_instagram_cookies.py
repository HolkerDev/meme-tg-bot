#!/usr/bin/env python3
"""Export Instagram session cookies to a Netscape cookie file.

Usage:
    uv run python scripts/export_instagram_cookies.py

Reads INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD, and INSTAGRAM_COOKIES_FILE from .env.
Writes a Netscape-format cookies file that yt-dlp and gallery-dl can consume.
"""

import os
import sys
import time
from pathlib import Path
from http.cookiejar import MozillaCookieJar

import requests
from dotenv import load_dotenv

_IG_APP_ID = "936619743392459"
_LOGIN_PAGE = "https://www.instagram.com/accounts/login/"
_LOGIN_API = "https://www.instagram.com/api/v1/web/accounts/login/ajax/"


def _make_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/125.0.0.0 Safari/537.36"
        ),
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Origin": "https://www.instagram.com",
        "Referer": "https://www.instagram.com/",
        "X-IG-App-ID": _IG_APP_ID,
        "X-Requested-With": "XMLHttpRequest",
    })
    return session


def login(username: str, password: str) -> requests.Session:
    session = _make_session()

    # Seed initial cookies (csrftoken, mid, etc.)
    session.get(_LOGIN_PAGE, timeout=30)

    csrf = session.cookies.get("csrftoken", "")
    if not csrf:
        raise RuntimeError("Could not get csrftoken from Instagram login page")

    session.headers["X-CSRFToken"] = csrf

    resp = session.post(
        _LOGIN_API,
        data={
            "username": username,
            # enc_password type 0 = plaintext (safe over HTTPS, accepted by Instagram web)
            "enc_password": f"#PWD_INSTAGRAM_BROWSER:0:{int(time.time())}:{password}",
            "queryParams": '{"source":"auth_switcher"}',
            "optIntoOneTap": "false",
            "trustedDeviceRecords": "{}",
        },
        timeout=30,
        allow_redirects=False,
    )

    try:
        data = resp.json()
    except Exception:
        raise RuntimeError(f"Unexpected response from Instagram login: {resp.text[:300]}")

    if data.get("two_factor_required"):
        raise RuntimeError(
            "2FA is enabled on this account. Disable 2FA temporarily or export cookies manually from a browser."
        )
    if data.get("checkpoint_url"):
        raise RuntimeError(
            f"Instagram requires a security checkpoint: {data['checkpoint_url']}\n"
            "Log in via browser to clear the checkpoint, then re-run this script."
        )
    if not data.get("authenticated"):
        message = data.get("message") or data.get("errors") or str(data)
        raise RuntimeError(f"Login failed: {message}")

    return session


def write_netscape_cookies(session: requests.Session, path: Path) -> list[str]:
    jar = MozillaCookieJar(str(path))
    for cookie in session.cookies:
        jar.set_cookie(cookie)  # type: ignore[arg-type]
    jar.save(ignore_discard=True, ignore_expires=True)
    return [c.name for c in session.cookies]


def main() -> None:
    load_dotenv()

    username = os.environ.get("INSTAGRAM_USERNAME")
    password = os.environ.get("INSTAGRAM_PASSWORD")
    cookies_path = os.environ.get("INSTAGRAM_COOKIES_FILE", "instagram-cookies.txt")

    if not username:
        print("ERROR: INSTAGRAM_USERNAME is not set in .env", file=sys.stderr)
        sys.exit(1)
    if not password:
        print("ERROR: INSTAGRAM_PASSWORD is not set in .env", file=sys.stderr)
        sys.exit(1)

    print(f"Logging in as {username} ...")
    try:
        session = login(username, password)
    except RuntimeError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    out = Path(cookies_path)
    names = write_netscape_cookies(session, out)

    print(f"Exported {len(names)} cookies to: {out.resolve()}")
    print(f"Set in .env:  INSTAGRAM_COOKIES_FILE={out.resolve()}")
    if "sessionid" in names:
        print("sessionid: present")
    else:
        print("sessionid: MISSING — check if the account requires browser verification", file=sys.stderr)


if __name__ == "__main__":
    main()
