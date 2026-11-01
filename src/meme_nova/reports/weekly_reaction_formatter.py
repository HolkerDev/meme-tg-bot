from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class WeeklyReactionEntry:
    display_name: str
    reaction_count: int
    super_like_count: int = 0


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
            line = f"{rank}. {entry.display_name} — {entry.reaction_count} {reaction_label}"
            if entry.super_like_count:
                super_like_label = "super like" if entry.super_like_count == 1 else "super likes"
                line += f" · {entry.super_like_count} {super_like_label}"
            lines.append(line)
        return "\n".join(lines)
