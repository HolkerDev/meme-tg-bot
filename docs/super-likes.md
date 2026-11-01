# Super Likes

In the main chat, Memeproxy (`-1002564248375`), a single video or photo sent by
the bot has a **Потужний лайк** button with that post's Super Like count. Telegram
does not support inline keyboards on albums sent with `sendMediaGroup`, so the bot
replies to the last album item with one button message for the whole album. The
button uses a callback, so it is not kept when someone forwards the media.

Each Telegram user can give one Super Like per **Europe/Berlin calendar day**.
The limit applies across posts in the main chat. Tapping again on the same day
shows a brief Telegram popup and does not change the count. The post's sender
cannot Super Like their own post. The next Berlin day, the user can choose any
post, including one they liked before.

Super Likes are stored separately from ordinary Telegram reactions. The Friday
leaderboard ranks senders by Super Likes, with ordinary reactions as a tie-breaker.
Each row shows the Super Like total and the reaction count in parentheses, for
example `1. @alice - 2 потужнолайка (12)`. A Super Like is attributed to the
user who posted the original link, because the bot's media reply is registered
to that user. For albums, the button message is registered to the same sender;
the album items remain registered for ordinary reactions.

The database schema is added by Alembic revision `d3e4f5a6b7c8`. Run
`uv run alembic upgrade head` before restarting the bot with this code.
