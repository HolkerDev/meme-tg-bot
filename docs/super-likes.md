# Super Likes

In the main chat, Memeproxy (`-1002564248375`), a single video sent by the bot
has a **Потужний лайк** button with that video's Super Like count. Albums sent
with `sendMediaGroup` do not have the button because Telegram does not support
inline keyboards on media groups. The button uses a callback, so it is not kept
when someone forwards the video.

Each Telegram user can give one Super Like per **Europe/Berlin calendar day**.
The limit applies across videos in the main chat. Tapping again on the same day
shows a brief Telegram popup and does not change the count. The video's sender
cannot Super Like their own video. The next Berlin day, the user can choose any
video, including one they liked before.

Super Likes are stored separately from ordinary Telegram reactions. The Friday
leaderboard ranks senders by Super Likes, with ordinary reactions as a tie-breaker.
Each row shows the Super Like total and the reaction count in parentheses, for
example `1. @alice - 2 потужнолайка (12)`. A Super Like is attributed to the
user who posted the original link, because the bot's video reply is registered
to that user.

The database schema is added by Alembic revision `d3e4f5a6b7c8`. Run
`uv run alembic upgrade head` before restarting the bot with this code.
