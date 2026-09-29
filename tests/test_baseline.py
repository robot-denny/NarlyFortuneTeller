"""Tests for baseline.py — the mechanical "heard correctly" rule.

The rule decides whether what the recognizer heard counts as the question the
volunteer asked. It ignores case and punctuation and nothing else, so a single
wrong word is a miss.
"""

import wave

import speech_recognition as sr

from baseline import Row, heard_correctly, live_rows, replay_rows, score, to_markdown
from fakes import FakeTranscriber


def _rows(condition, first_id, correct, total, miss_outcome="no_speech"):
    """Build `total` rows for one condition; the first `correct` are heard right."""
    rows = []
    for n in range(total):
        row_id = str(first_id + n)
        if n < correct:
            rows.append(Row(row_id, condition, "Will I be lucky?", "heard", "will I be lucky", 3.0))
        else:
            rows.append(Row(row_id, condition, "Will I be lucky?", miss_outcome, None, None))
    return rows


def _spec_example():
    """The spec's example session: 60 rows, 42 heard correctly."""
    return (
        _rows("quiet", 1, correct=18, total=20)
        + _rows("conversation", 21, correct=11, total=20)
        + _rows("leaning", 41, correct=13, total=20)
    )


def test_case_and_punctuation_differences_still_count_as_correct():
    assert heard_correctly("Will I find treasure today?", "will I find treasure today") is True


def test_one_wrong_word_is_not_correct():
    assert heard_correctly("Should I take the job?", "should I bake the job") is False


def test_blank_or_missing_transcript_is_never_correct():
    assert heard_correctly("Will I find treasure today?", "") is False
    assert heard_correctly("Will I find treasure today?", None) is False


def test_score_gives_overall_and_per_condition_share_for_the_spec_example():
    summary = score(_spec_example())

    assert summary.correct == 42
    assert summary.counted == 60
    assert summary.overall_percent == 70
    assert summary.condition_percent == {"quiet": 90, "conversation": 55, "leaning": 65}
    assert summary.misses_by_kind == {"no_speech": 18}


def test_recognizer_errors_are_unreachable_and_left_out_of_the_share():
    rows = (
        _rows("quiet", 1, correct=18, total=20)
        + _rows("conversation", 21, correct=11, total=18)
        + _rows("conversation", 39, correct=0, total=2, miss_outcome="recognizer_error")
        + _rows("leaning", 41, correct=13, total=18)
        + _rows("leaning", 59, correct=0, total=2, miss_outcome="recognizer_error")
    )

    summary = score(rows)

    assert summary.unreachable == 4
    assert summary.counted == 56
    assert summary.overall_percent == 75  # 42 of 56
    assert summary.condition_percent["quiet"] == 90  # 18 of 20
    assert "recognizer_error" not in summary.misses_by_kind


def test_heard_with_wrong_words_is_a_misheard_miss_listed_with_both_strings():
    rows = [
        Row("1", "quiet", "Should I take the job?", "heard", "should I bake the job", 2.5),
        Row("2", "quiet", "Will I be lucky?", "heard", "will I be lucky", 2.0),
        Row("3", "quiet", "Is love near?", "no_speech", None, None),
    ]

    summary = score(rows)

    assert summary.misses_by_kind == {"misheard": 1, "no_speech": 1}
    misheard = [miss for miss in summary.misses if miss.id == "1"]
    assert len(misheard) == 1
    assert misheard[0].asked == "Should I take the job?"
    assert misheard[0].heard == "should I bake the job"
    assert misheard[0].kind == "misheard"
    assert [miss.id for miss in summary.misses] == ["1", "3"]


def test_a_clip_of_eight_seconds_hits_the_cap_but_shorter_or_missing_clips_do_not():
    rows = [
        Row("1", "quiet", "Will I be lucky?", "heard", "will I be lucky", 8.0),
        Row("2", "quiet", "Will I be lucky?", "heard", "will I be lucky", 7.5),
        Row("3", "quiet", "Will I be lucky?", "no_speech", None, None),
    ]

    assert score(rows).hit_cap == 1


def test_markdown_shows_the_overall_share_and_each_conditions_share():
    markdown = to_markdown(score(_spec_example()), "Live, 2026-09-30")

    lines = markdown.splitlines()

    def line_with(word):
        return next(line for line in lines if word in line.lower())

    assert "Live, 2026-09-30" in markdown
    assert "70%" in line_with("overall")
    assert "90%" in line_with("quiet")
    assert "55%" in line_with("conversation")
    assert "65%" in line_with("leaning")


# --- Scoring a live session from its log -------------------------------------

_SCRIPT = """id,condition,question
1,quiet,Will I find treasure today?
2,quiet,Should I take the job?
3,quiet,Is love near?
"""


def _write_session(tmp_path, log_text):
    log = tmp_path / "session.log"
    log.write_text(log_text)
    script = tmp_path / "script.csv"
    script.write_text(_SCRIPT)
    clips = tmp_path / "clips"
    clips.mkdir()
    return log, script, clips


def _write_wav(path, seconds, rate=16000):
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        wav.writeframes(b"\x00\x00" * int(rate * seconds))


def test_live_rows_pairs_each_clip_label_with_the_next_capture_line(tmp_path):
    log, script, clips = _write_session(
        tmp_path,
        "2026-09-28 11:58:40,001 INFO     clip id=1\n"
        "2026-09-28 11:58:47,100 INFO     clip saved id=1 path=clips/1.wav\n"
        '2026-09-28 11:58:48,265 INFO     capture outcome=heard heard="Will I find treasure today?" secs=1.9\n'
        "2026-09-28 11:59:00,001 INFO     clip id=2\n"
        '2026-09-28 11:59:06,002 WARNING  capture outcome=no_speech heard="" secs=6.0 detail="listening timed out"\n'
        "2026-09-28 11:59:20,001 INFO     clip id=3\n"
        "2026-09-28 11:59:23,100 INFO     clip saved id=3 path=clips/3.wav\n"
        '2026-09-28 11:59:24,265 INFO     capture outcome=heard heard="is love here" secs=2.1\n',
    )

    rows = live_rows(log, script, clips)

    assert [(r.id, r.condition, r.asked, r.outcome, r.heard) for r in rows] == [
        ("1", "quiet", "Will I find treasure today?", "heard", "Will I find treasure today?"),
        ("2", "quiet", "Should I take the job?", "no_speech", ""),
        ("3", "quiet", "Is love near?", "heard", "is love here"),
    ]
    assert score(rows).misses_by_kind == {"misheard": 1, "no_speech": 1}


def test_live_rows_keeps_only_the_last_pairing_for_a_re_asked_label(tmp_path):
    log, script, clips = _write_session(
        tmp_path,
        "2026-09-28 11:58:40,001 INFO     clip id=2\n"
        '2026-09-28 11:58:46,002 WARNING  capture outcome=no_speech heard="" secs=6.0\n'
        "2026-09-28 11:59:00,001 INFO     clip id=2\n"
        '2026-09-28 11:59:04,265 INFO     capture outcome=heard heard="should I take the job" secs=2.4\n',
    )

    rows = live_rows(log, script, clips)

    assert [(r.id, r.outcome, r.heard) for r in rows] == [
        ("2", "heard", "should I take the job"),
    ]


def test_live_rows_reads_clip_length_from_the_wav_and_none_when_missing(tmp_path):
    log, script, clips = _write_session(
        tmp_path,
        "2026-09-28 11:58:40,001 INFO     clip id=1\n"
        '2026-09-28 11:58:48,265 INFO     capture outcome=heard heard="will I find treasure today" secs=8.0\n'
        "2026-09-28 11:59:00,001 INFO     clip id=2\n"
        '2026-09-28 11:59:06,002 WARNING  capture outcome=no_speech heard="" secs=6.0\n',
    )
    _write_wav(clips / "1.wav", seconds=2.5)

    rows = live_rows(log, script, clips)

    assert {r.id: r.clip_seconds for r in rows} == {"1": 2.5, "2": None}


# --- Replaying saved clips ---------------------------------------------------


def _write_replay_set(tmp_path, clip_ids):
    """A script of three questions and a clips folder holding a silent WAV for each id given."""
    script = tmp_path / "script.csv"
    script.write_text(_SCRIPT)
    clips = tmp_path / "clips"
    clips.mkdir()
    for clip_id in clip_ids:
        _write_wav(clips / f"{clip_id}.wav", seconds=1.0)
    return clips, script


def test_replay_counts_a_clip_as_heard_correctly_when_the_recognizer_returns_the_question(tmp_path):
    clips, script = _write_replay_set(tmp_path, ["1"])

    rows, no_clip = replay_rows(clips, script, transcribe=FakeTranscriber("Will I find treasure today?"))

    assert [(r.id, r.outcome, r.heard, r.clip_seconds) for r in rows] == [
        ("1", "heard", "Will I find treasure today?", 1.0),
    ]
    summary = score(rows)
    assert (summary.correct, summary.counted) == (1, 1)


def test_replay_with_the_recognizer_unreachable_is_reported_as_unreachable(tmp_path):
    clips, script = _write_replay_set(tmp_path, ["1"])

    rows, _ = replay_rows(clips, script, transcribe=FakeTranscriber(raises=sr.RequestError("down")))

    assert [r.outcome for r in rows] == ["recognizer_error"]
    summary = score(rows)
    assert (summary.unreachable, summary.counted) == (1, 0)


def test_replay_lists_script_ids_with_no_clip_and_leaves_them_out_of_the_rows(tmp_path):
    clips, script = _write_replay_set(tmp_path, ["1", "3"])

    rows, no_clip = replay_rows(clips, script, transcribe=FakeTranscriber("anything"))

    assert [r.id for r in rows] == ["1", "3"]
    assert no_clip == ["2"]
