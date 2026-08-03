from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class WeeklyReactionEntry:
    display_name: str
    reaction_count: int


class WeeklyReactionReportFormatter:
    def format(self, entries: list[WeeklyReactionEntry]) -> str:
        if not entries:
            return "No reactions this week."

        ranked = sorted(
            entries,
            key=lambda entry: (-entry.reaction_count, entry.display_name.casefold()),
        )
        lines = ["Weekly reaction leaderboard", ""]
        for rank, entry in enumerate(ranked, start=1):
            reaction_label = "reaction" if entry.reaction_count == 1 else "reactions"
            lines.append(f"{rank}. {entry.display_name} — {entry.reaction_count} {reaction_label}")
        return "\n".join(lines)
