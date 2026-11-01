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
        "Потужні лайки тижня\n"
        "\n"
        "1. @bob - 0 потужнолайків (12)\n"
        "2. @alice - 0 потужнолайків (5)\n"
        "3. carol - 0 потужнолайків (1)"
    )


def test_formatter_breaks_ties_alphabetically() -> None:
    formatter = WeeklyReactionReportFormatter()
    entries = [
        WeeklyReactionEntry(display_name="Zed", reaction_count=3),
        WeeklyReactionEntry(display_name="Amy", reaction_count=3),
    ]

    text = formatter.format(entries)

    assert "1. Amy - 0 потужнолайків (3)" in text
    assert "2. Zed - 0 потужнолайків (3)" in text


def test_super_likes_rank_first_and_reactions_are_shown_in_parentheses() -> None:
    formatter = WeeklyReactionReportFormatter()
    entries = [
        WeeklyReactionEntry(display_name="@alice", reaction_count=1, super_like_count=2),
        WeeklyReactionEntry(display_name="@bob", reaction_count=5),
    ]

    text = formatter.format(entries)

    assert "1. @alice - 2 потужнолайка (1)" in text
    assert "2. @bob - 0 потужнолайків (5)" in text
