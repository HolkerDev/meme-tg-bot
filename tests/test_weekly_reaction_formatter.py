from meme_nova.reports.weekly_reaction_formatter import (
    WeeklyReactionEntry,
    WeeklyReactionReportFormatter,
)


def test_formatter_returns_empty_message_when_no_entries() -> None:
    formatter = WeeklyReactionReportFormatter()

    assert formatter.format([]) == "No reactions this week."


def test_formatter_ranks_users_by_reaction_count() -> None:
    formatter = WeeklyReactionReportFormatter()
    entries = [
        WeeklyReactionEntry(display_name="@alice", reaction_count=5),
        WeeklyReactionEntry(display_name="@bob", reaction_count=12),
        WeeklyReactionEntry(display_name="carol", reaction_count=1),
    ]

    text = formatter.format(entries)

    assert text == (
        "Weekly reaction leaderboard\n"
        "\n"
        "1. @bob — 12 reactions\n"
        "2. @alice — 5 reactions\n"
        "3. carol — 1 reaction"
    )


def test_formatter_breaks_ties_alphabetically() -> None:
    formatter = WeeklyReactionReportFormatter()
    entries = [
        WeeklyReactionEntry(display_name="Zed", reaction_count=3),
        WeeklyReactionEntry(display_name="Amy", reaction_count=3),
    ]

    text = formatter.format(entries)

    assert "1. Amy — 3 reactions" in text
    assert "2. Zed — 3 reactions" in text
