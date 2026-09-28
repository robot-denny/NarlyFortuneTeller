"""Scoring Narly's capture baseline.

This module decides whether Narly "heard correctly": whether the words the
recognizer returned are the question the volunteer read from the script.

The rule is mechanical on purpose. It ignores letter case and punctuation and
nothing else, so every iteration is scored the same way and the success rate
can be compared from one session to the next. Do not make it fuzzier: a rule
that drifts would make old and new numbers impossible to compare.

It also replays saved clips through the recognizer (the `replay` subcommand).
A replay never generates a fortune: this module does not import or call
`ai_client`, so no OpenAI call can happen and a replay costs nothing but the
free speech-to-text request. (The real recognizer is borrowed from
`serial_trigger`, which loads `ai_client` as a module, but nothing here ever
asks it for a fortune.)
"""

import argparse
import csv
import re
import sys
import wave
from dataclasses import dataclass, field
from pathlib import Path

from capture_client import capture_question, wav_get_audio

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


# --- Reading a live session --------------------------------------------------

# During a measuring session Narly logs "clip id=<label>" before it listens,
# then one "capture outcome=..." line once it has an answer. These patterns
# read those lines; the capture line's format is fixed, so they stay simple.
_CLIP_LABEL = re.compile(r"\bclip id=(\S+)")
_OUTCOME = re.compile(r"outcome=(\S+)")
_HEARD = re.compile(r'heard="([^"]*)"')


def _read_script(script_path) -> list[dict[str, str]]:
    """Read the question script: one dict per row, with id, condition, question."""
    with open(script_path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def clip_seconds(path: Path) -> float | None:
    """How long a saved clip lasts, in seconds, or None if there is no clip."""
    if not path.exists():
        return None
    with wave.open(str(path), "rb") as wav:
        return wav.getnframes() / wav.getframerate()


def live_rows(log_path, script_path, clips_dir) -> list[Row]:
    """Turn a session's log into one Row per script question that was asked.

    Each "clip id=<label>" line is paired with the next "capture outcome="
    line. If a question was asked twice (a volunteer's re-ask), the last try
    counts. Rows come back in script order.
    """
    script = _read_script(script_path)
    known_ids = {entry["id"] for entry in script}
    results: dict[str, tuple[str, str | None]] = {}  # label -> (outcome, heard)

    pending_label = None
    with open(log_path, encoding="utf-8") as log:
        for line in log:
            label_match = _CLIP_LABEL.search(line)
            if label_match:
                pending_label = label_match.group(1)
                continue
            if "capture outcome=" in line and pending_label is not None:
                outcome = _OUTCOME.search(line).group(1)
                heard_match = _HEARD.search(line)
                heard = heard_match.group(1) if heard_match else None
                if pending_label in known_ids:
                    results[pending_label] = (outcome, heard)
                else:
                    print(
                        f"Skipping clip id={pending_label}: it is not in the script.",
                        file=sys.stderr,
                    )
                pending_label = None

    clips = Path(clips_dir)
    rows = []
    for entry in script:
        if entry["id"] not in results:
            continue
        outcome, heard = results[entry["id"]]
        rows.append(
            Row(
                id=entry["id"],
                condition=entry["condition"],
                asked=entry["question"],
                outcome=outcome,
                heard=heard,
                clip_seconds=clip_seconds(clips / f"{entry['id']}.wav"),
            )
        )
    return rows


# --- Replaying saved clips ---------------------------------------------------


def replay_rows(clips_dir, script_path, transcribe=None) -> tuple[list[Row], list[str]]:
    """Send each script question's saved clip through the recognizer again.

    Returns one Row per script question that has a clip (<clips_dir>/<id>.wav),
    in script order, plus the ids that have no clip. Only the recognizer runs:
    no fortune is ever asked for.
    """
    if transcribe is None:
        # Imported here, not at the top, so tests can pass a fake recognizer
        # without loading the orchestrator.
        from serial_trigger import google_transcribe

        transcribe = google_transcribe

    clips = Path(clips_dir)
    rows = []
    no_clip = []
    for entry in _read_script(script_path):
        path = clips / f"{entry['id']}.wav"
        if not path.exists():
            no_clip.append(entry["id"])
            continue
        result = capture_question(wav_get_audio(str(path)), transcribe)
        rows.append(
            Row(
                id=entry["id"],
                condition=entry["condition"],
                asked=entry["question"],
                outcome=result.outcome.value,
                heard=result.text,
                clip_seconds=clip_seconds(path),
            )
        )
    return rows, no_clip


# --- Command line -------------------------------------------------------------


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Score how often Narly heard the script's questions correctly."
    )
    commands = parser.add_subparsers(dest="command", required=True)

    live = commands.add_parser(
        "live", help="score a measuring session from its log file"
    )
    live.add_argument("log", help="the session's log file (from --log-file)")
    live.add_argument("script", help="the question script, e.g. docs/baseline-script.csv")
    live.add_argument("--clips", required=True, help="folder the session saved its clips in")

    replay = commands.add_parser(
        "replay", help="send saved clips through the recognizer again and score them"
    )
    replay.add_argument("clips", help="folder of saved clips, named <id>.wav")
    replay.add_argument("script", help="the question script, e.g. docs/baseline-script.csv")

    args = parser.parse_args(argv)
    if args.command == "live":
        rows = live_rows(args.log, args.script, args.clips)
        print(to_markdown(score(rows), "Live"), end="")
    elif args.command == "replay":
        rows, no_clip = replay_rows(args.clips, args.script)
        print(to_markdown(score(rows), "Replay"), end="")
        # The blank line ends the Markdown list, so this is not read as part of its last bullet.
        print(f"\nNo clip: {', '.join(no_clip) if no_clip else 'none'}")


if __name__ == "__main__":
    main()
