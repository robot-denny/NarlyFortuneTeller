"""Tests for baseline.py — the mechanical "heard correctly" rule.

The rule decides whether what the recognizer heard counts as the question the
volunteer asked. It ignores case and punctuation and nothing else, so a single
wrong word is a miss.
"""

from baseline import Row, heard_correctly, score, to_markdown


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
