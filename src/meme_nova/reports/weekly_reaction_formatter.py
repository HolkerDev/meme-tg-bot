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
            key=lambda entry: (
                -entry.super_like_count,
                -entry.reaction_count,
                entry.display_name.casefold(),
            ),
        )
        lines = ["Потужні лайки тижня", ""]
        for rank, entry in enumerate(ranked, start=1):
            count = entry.super_like_count
            if count % 100 in (11, 12, 13, 14):
                label = "потужнолайків"
            elif count % 10 == 1:
                label = "потужнолайк"
            elif count % 10 in (2, 3, 4):
                label = "потужнолайка"
            else:
                label = "потужнолайків"
            lines.append(
                f"{rank}. {entry.display_name} - {count} {label} ({entry.reaction_count})"
            )
        return "\n".join(lines)
