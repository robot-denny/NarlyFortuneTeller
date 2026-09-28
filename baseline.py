"""Scoring Narly's capture baseline.

This module decides whether Narly "heard correctly": whether the words the
recognizer returned are the question the volunteer read from the script.

The rule is mechanical on purpose. It ignores letter case and punctuation and
nothing else, so every iteration is scored the same way and the success rate
can be compared from one session to the next. Do not make it fuzzier: a rule
that drifts would make old and new numbers impossible to compare.
"""

import re
from dataclasses import dataclass, field

_NOT_LETTER_DIGIT_OR_SPACE = re.compile(r"[^a-z0-9 ]")
_RUN_OF_SPACES = re.compile(r" +")


def _normalise(text: str) -> str:
    """Lowercase, turn punctuation into spaces, collapse spaces, and trim."""
    text = _NOT_LETTER_DIGIT_OR_SPACE.sub(" ", text.lower())
    return _RUN_OF_SPACES.sub(" ", text).strip()


def heard_correctly(asked: str, heard: str | None) -> bool:
    """Return True only when `heard` is the same words as `asked`.

    A missing or blank transcript is never correct.
    """
    if heard is None:
        return False
    normalised_heard = _normalise(heard)
    return normalised_heard != "" and normalised_heard == _normalise(asked)


UNREACHABLE = "recognizer_error"
MISHEARD = "misheard"

# Narly stops listening after 8 seconds (phrase_time_limit=8 in
# serial_trigger.py). Audio arrives in chunks, so a clip that ran to the limit
# can be a little short of 8.0; 7.9 seconds or more counts as hitting the cap.
CAP_SECONDS = 7.9


@dataclass
class Row:
    """One question asked during a session, and what Narly made of it."""

    id: str
    condition: str
    asked: str
    outcome: str
    heard: str | None
    clip_seconds: float | None


@dataclass
class Miss:
    """A row that wasn't heard correctly. `kind` is its outcome, or `misheard`."""

    id: str
    asked: str
    heard: str | None
    kind: str


@dataclass
class Summary:
    """The scores for one set of rows. Percentages are out of `counted`."""

    correct: int = 0
    counted: int = 0
    unreachable: int = 0
    hit_cap: int = 0
    overall_percent: float | None = None
    condition_percent: dict[str, float | None] = field(default_factory=dict)
    condition_counts: dict[str, tuple[int, int]] = field(default_factory=dict)
    misses_by_kind: dict[str, int] = field(default_factory=dict)
    misses: list[Miss] = field(default_factory=list)


def _percent(correct: int, counted: int) -> float | None:
    return 100 * correct / counted if counted else None


def score(rows: list[Row]) -> Summary:
    """Count how many rows were heard correctly, overall and per condition.

    A `recognizer_error` row means Google couldn't be reached, which says
    nothing about how well Narly hears. It is counted as unreachable and left
    out of every percentage.
    """
    summary = Summary()
    per_condition: dict[str, list[int]] = {}  # condition -> [correct, counted]

    for row in rows:
        if row.clip_seconds is not None and row.clip_seconds >= CAP_SECONDS:
            summary.hit_cap += 1
        if row.outcome == UNREACHABLE:
            summary.unreachable += 1
            continue
        tally = per_condition.setdefault(row.condition, [0, 0])
        summary.counted += 1
        tally[1] += 1
        if row.outcome == "heard" and heard_correctly(row.asked, row.heard):
            summary.correct += 1
            tally[0] += 1
        else:
            # Outcome "heard" but the words don't match is a near miss: "misheard".
            kind = MISHEARD if row.outcome == "heard" else row.outcome
            summary.misses_by_kind[kind] = summary.misses_by_kind.get(kind, 0) + 1
            summary.misses.append(Miss(row.id, row.asked, row.heard, kind))

    summary.overall_percent = _percent(summary.correct, summary.counted)
    summary.condition_percent = {
        condition: _percent(correct, counted)
        for condition, (correct, counted) in per_condition.items()
    }
    summary.condition_counts = {
        condition: (correct, counted) for condition, (correct, counted) in per_condition.items()
    }
    return summary


def _show_percent(percent: float | None) -> str:
    return "n/a" if percent is None else f"{percent:.0f}%"


def _cell(text: str | None) -> str:
    """Make text safe for one cell of a Markdown table."""
    if text is None or text == "":
        return "(nothing)"
    return text.replace("|", "\\|")


def to_markdown(summary: Summary, title: str) -> str:
    """Render a summary as a short Markdown block to paste into the results file."""
    lines = [
        f"### {title}",
        "",
        f"- Heard correctly overall: {_show_percent(summary.overall_percent)}"
        f" ({summary.correct} of {summary.counted})",
    ]
    for condition, percent in summary.condition_percent.items():
        correct, counted = summary.condition_counts[condition]
        lines.append(f"- {condition}: {_show_percent(percent)} ({correct} of {counted})")
    lines.append(
        f"- Unreachable (recognizer_error, left out of the shares): {summary.unreachable}"
    )
    lines.append(f"- Hit the 8-second cap: {summary.hit_cap}")

    if summary.misses_by_kind:
        kinds = ", ".join(
            f"{kind} {count}" for kind, count in sorted(summary.misses_by_kind.items())
        )
        lines.append(f"- Misses by kind: {kinds}")
    else:
        lines.append("- Misses by kind: none")

    if summary.misses:
        lines += ["", "| id | kind | asked | heard |", "| --- | --- | --- | --- |"]
        for miss in summary.misses:
            lines.append(
                f"| {_cell(miss.id)} | {miss.kind} | {_cell(miss.asked)} | {_cell(miss.heard)} |"
            )

    return "\n".join(lines) + "\n"
