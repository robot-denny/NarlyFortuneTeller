"""Tests for the capture record that serial_trigger.on_coin_event writes to the log.

These are Acceptance Criteria 1 and 2 made concrete: one run where nobody
spoke must be recorded as `outcome=no_speech` and `source=substituted` with
the persona's default question; one run where the attendee was heard must be
recorded as `outcome=heard` with their exact words.

Every failure kind is run end to end here, not just in `capture_client`: an
unreachable recognizer, an unplugged mic, and an overrun must each still reach
the fortune with the substituted question. One test also pins the coin line as
the start of each run in the operator's live view.

No hardware is touched. The mic, the recognizer, and the OpenAI call are all
replaced through `configure_providers`, the same seam `main()` uses, and the
speaker by a `FakeAudioOut` wired the same way. The Arduino `LedClient` is
silenced by the shared fixture in `conftest.py`, which also loads the default
persona and restores the module globals after each test.
"""

import logging
import re
import time

import pytest
import speech_recognition as sr

import serial_trigger
from fakes import FakeAudioOut, FakeFortune, FakeTranscriber


pytestmark = pytest.mark.usefixtures("quiet_and_configured")

AUDIO = object()  # a sentinel standing in for sr.AudioData
QUESTION = "Will I find treasure today?"


def test_silent_run_is_recorded_as_no_speech_and_substituted(caplog, log_lines):
    """Nobody spoke: the log says no_speech, then that the default question was substituted."""

    def get_audio(on_ready):
        raise sr.WaitTimeoutError("no speech")

    fortune = FakeFortune()
    serial_trigger.configure_providers(
        get_audio=get_audio,
        transcribe=FakeTranscriber(QUESTION),  # never reached: the mic stage fails first
        fortune=fortune,
        audio_out=FakeAudioOut(),
    )
    caplog.set_level(logging.INFO)

    serial_trigger.on_coin_event(pulses=1, dry_run=True)

    default_question = serial_trigger._config["default_question"]
    capture_line = log_lines("capture ", expect=1)[0]
    question_line = log_lines("question ", expect=1)[0]
    assert "outcome=no_speech" in capture_line
    assert 'heard=""' in capture_line
    assert 'detail="no speech"' in capture_line
    assert question_line == f'question source=substituted text="{default_question}"'
    # Every failure path still prints a fortune: the substituted question reached the AI.
    assert fortune.questions == [default_question]


def test_heard_run_records_the_attendees_words(caplog, log_lines):
    """The attendee was heard: the log says heard, with their words, and the AI got them."""
    fortune = FakeFortune()
    serial_trigger.configure_providers(
        get_audio=lambda on_ready: AUDIO,
        transcribe=FakeTranscriber(QUESTION),
        fortune=fortune,
        audio_out=FakeAudioOut(),
    )
    caplog.set_level(logging.INFO)

    serial_trigger.on_coin_event(pulses=1, dry_run=True)

    capture_line = log_lines("capture ", expect=1)[0]
    question_line = log_lines("question ", expect=1)[0]
    assert "outcome=heard" in capture_line
    assert f'heard="{QUESTION}"' in capture_line
    assert "detail=" not in capture_line  # detail is a failure-only field
    assert question_line == f'question source=heard text="{QUESTION}"'
    assert fortune.questions == [QUESTION]


def test_capture_line_levels_match_outcome(caplog, log_lines):
    """A heard run is INFO; a failed capture is WARNING, so `grep WARNING` finds the failures."""
    serial_trigger.configure_providers(
        get_audio=lambda on_ready: AUDIO,
        transcribe=FakeTranscriber(raises=sr.UnknownValueError()),
        fortune=FakeFortune(),
        audio_out=FakeAudioOut(),
    )
    caplog.set_level(logging.INFO)

    serial_trigger.on_coin_event(pulses=1, dry_run=True)

    capture_records = [r for r in caplog.records if r.getMessage().startswith("capture ")]
    assert len(capture_records) == 1
    assert capture_records[0].levelno == logging.WARNING
    assert "outcome=not_understood" in capture_records[0].getMessage()


def test_multiline_error_detail_stays_on_one_line(caplog, log_lines):
    """An error message with a newline in it must not split the capture record across lines."""

    def get_audio(on_ready):
        raise OSError("first line\nsecond line")

    serial_trigger.configure_providers(
        get_audio=get_audio,
        transcribe=FakeTranscriber(QUESTION),
        fortune=FakeFortune(),
        audio_out=FakeAudioOut(),
    )
    caplog.set_level(logging.INFO)

    serial_trigger.on_coin_event(pulses=1, dry_run=True)

    capture_records = [r for r in caplog.records if r.getMessage().startswith("capture ")]
    assert len(capture_records) == 1
    message = capture_records[0].getMessage()
    assert "\n" not in message
    assert "outcome=mic_error" in message
    assert 'detail="first line second line"' in message


def test_transcript_with_quotes_and_newlines_stays_one_parseable_line(caplog, log_lines):
    """An attendee's words can contain quotes or line breaks; the log line must stay one
    line with its key="value" shape intact — the same rule detail= already follows."""
    serial_trigger.configure_providers(
        get_audio=lambda on_ready: AUDIO,
        transcribe=FakeTranscriber('say "hello"\nworld'),
        fortune=FakeFortune(),
        audio_out=FakeAudioOut(),
    )
    caplog.set_level(logging.INFO)

    serial_trigger.on_coin_event(pulses=1, dry_run=True)

    capture_line = log_lines("capture ", expect=1)[0]
    question_line = log_lines("question ", expect=1)[0]
    for line in (capture_line, question_line):
        assert "\n" not in line
    assert 'heard="say \'hello\' world"' in capture_line
    assert question_line == 'question source=heard text="say \'hello\' world"'


def test_unconfigured_providers_are_reported_as_a_wiring_error_not_a_mic_error(caplog, log_lines):
    """If configure_providers() was never called, the log must say so plainly rather than
    blaming the microphone — and the attendee still gets the fallback slip."""
    serial_trigger.configure_providers(None, None, None, None)
    caplog.set_level(logging.INFO)

    serial_trigger.on_coin_event(pulses=1, dry_run=True)

    messages = [r.getMessage() for r in caplog.records]
    assert not any("outcome=mic_error" in m for m in messages), messages
    assert any("configure_providers" in m for m in messages), messages
    assert any("Printing fallback message" in m for m in messages), messages


def test_unreachable_recognizer_is_recorded_and_the_fortune_still_arrives(caplog, log_lines):
    """No internet: the log names the recognizer as unreachable, the default question is
    substituted, and the attendee still gets a fortune."""
    fortune = FakeFortune()
    serial_trigger.configure_providers(
        get_audio=lambda on_ready: AUDIO,
        transcribe=FakeTranscriber(raises=sr.RequestError("recognition connection failed")),
        fortune=fortune,
        audio_out=FakeAudioOut(),
    )
    caplog.set_level(logging.INFO)

    serial_trigger.on_coin_event(pulses=1, dry_run=True)

    default_question = serial_trigger._config["default_question"]
    capture_line = log_lines("capture ", expect=1)[0]
    question_line = log_lines("question ", expect=1)[0]
    assert "outcome=recognizer_error" in capture_line
    assert 'detail="recognition connection failed"' in capture_line
    assert question_line == f'question source=substituted text="{default_question}"'
    assert fortune.questions == [default_question]


def test_overrun_is_recorded_with_its_real_duration_and_the_fortune_still_arrives(
    caplog, log_lines, monkeypatch
):
    """A capture slower than the whole-stage guard is recorded as overrun, with how long it
    really took, and the attendee still gets a fortune for the default question.

    The real guard is TIMEOUT_RECORDING + 10 = 25 s; this test shrinks it to 0.2 s so a
    0.5 s capture overruns it without making the suite slow."""
    monkeypatch.setattr(serial_trigger, "TIMEOUT_RECORDING", -9.8)

    def slow_get_audio(on_ready):
        time.sleep(0.5)
        return AUDIO

    fortune = FakeFortune()
    serial_trigger.configure_providers(
        get_audio=slow_get_audio,
        transcribe=FakeTranscriber(QUESTION),
        fortune=fortune,
        audio_out=FakeAudioOut(),
    )
    caplog.set_level(logging.INFO)

    serial_trigger.on_coin_event(pulses=1, dry_run=True)

    default_question = serial_trigger._config["default_question"]
    capture_line = log_lines("capture ", expect=1)[0]
    question_line = log_lines("question ", expect=1)[0]
    assert "outcome=overrun" in capture_line
    secs = float(re.search(r"secs=(\S+)", capture_line).group(1))
    assert secs >= 0.5  # the true stall time, not the guard value
    assert question_line == f'question source=substituted text="{default_question}"'
    assert fortune.questions == [default_question]


def test_each_fortune_run_starts_with_the_coin_line(caplog):
    """In the operator's live view, the coin line marks where each fortune starts: it comes
    before that run's capture and question lines, for every coin."""
    serial_trigger.configure_providers(
        get_audio=lambda on_ready: AUDIO,
        transcribe=FakeTranscriber(QUESTION),
        fortune=FakeFortune(),
        audio_out=FakeAudioOut(),
    )
    caplog.set_level(logging.INFO)

    serial_trigger.on_coin_event(pulses=1, dry_run=True)
    serial_trigger.on_coin_event(pulses=1, dry_run=True)

    kinds = []
    for record in caplog.records:
        message = record.getMessage()
        if message.startswith("💰 [COIN EVENT]"):
            kinds.append("coin")
        elif message.startswith("capture "):
            kinds.append("capture")
        elif message.startswith("question "):
            kinds.append("question")
    assert kinds == ["coin", "capture", "question", "coin", "capture", "question"]


def test_unplugged_microphone_is_recorded_and_the_fortune_still_arrives(caplog, log_lines):
    """The mic can't be opened: the log names a microphone fault with its reason, the default
    question is substituted, and the attendee still gets a fortune."""

    def get_audio(on_ready):
        raise OSError("Invalid input device")

    fortune = FakeFortune()
    serial_trigger.configure_providers(
        get_audio=get_audio,
        transcribe=FakeTranscriber(QUESTION),  # never reached: the mic stage fails first
        fortune=fortune,
        audio_out=FakeAudioOut(),
    )
    caplog.set_level(logging.INFO)

    serial_trigger.on_coin_event(pulses=1, dry_run=True)

    default_question = serial_trigger._config["default_question"]
    capture_line = log_lines("capture ", expect=1)[0]
    question_line = log_lines("question ", expect=1)[0]
    assert "outcome=mic_error" in capture_line
    assert 'detail="Invalid input device"' in capture_line
    assert question_line == f'question source=substituted text="{default_question}"'
    assert fortune.questions == [default_question]
