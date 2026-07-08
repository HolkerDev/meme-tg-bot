from meme_nova.bot import rank_weekly_users
from meme_nova.reaction_store import TopRecipient
from meme_nova.stats_store import TopUser


def test_rank_weekly_users_sorts_by_reactions_then_links() -> None:
    link_users = [
        TopUser(user_id=1, display_name="@alice", count=10),
        TopUser(user_id=2, display_name="@bob", count=5),
        TopUser(user_id=3, display_name="@carol", count=1),
    ]
    reaction_counts = {1: 2, 2: 8, 3: 8}
    reaction_users = [
        TopRecipient(user_id=2, display_name="@bob", count=8),
        TopRecipient(user_id=3, display_name="@carol", count=8),
    ]

    ranked = rank_weekly_users(link_users, reaction_counts, reaction_users)

    assert [(row.user_id, row.reaction_count, row.link_count) for row in ranked] == [
        (2, 8, 5),
        (3, 8, 1),
        (1, 2, 10),
    ]


def test_rank_weekly_users_includes_reaction_only_users() -> None:
    ranked = rank_weekly_users(
        link_users=[],
        reaction_counts={4: 3},
        reaction_users=[TopRecipient(user_id=4, display_name="@dave", count=3)],
    )

    assert len(ranked) == 1
    assert ranked[0].display_name == "@dave"
    assert ranked[0].link_count == 0
    assert ranked[0].reaction_count == 3
