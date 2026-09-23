"""Tests for replaying a fortune with no microphone and no network.

Acceptance Criteria 4 and 5 made concrete: a recorded clip becomes audio the
recognizer can consume, and the same typed question run twice produces the
same log records while spending nothing (no OpenAI call, no Google call).

The speaker and LEDs are silenced by the shared autouse fixture in
`conftest.py`; the providers are wired exactly the way `main()` wires them for
`--mode simulate --dry-run --offline --question "..."`.
"""

import argparse
import logging
import re
import wave

import pytest
import speech_recognition as sr

import serial_trigger
from capture_client import wav_get_audio
from fakes import FakeFortune, FakeTranscriber, typed_get_audio


pytestmark = pytest.mark.usefixtures("quiet_and_configured")

QUESTION = "Should I take the job?"


def _silent_wav(path, seconds=1, rate=16000):
    """Write `seconds` of 16 kHz mono 16-bit silence to `path` with the stdlib."""
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"\x00\x00" * rate * seconds)
    return path


def test_wav_file_becomes_audio_data_and_fires_the_cue_once(tmp_path):
    """A WAV on disk is read into `sr.AudioData`, and the readiness cue fires exactly once —
    a replayed clip must feel the same to a tester as a live question does to an attendee."""
    path = _silent_wav(tmp_path / "silence.wav")
    calls = []

    audio = wav_get_audio(str(path))(lambda: calls.append("cue"))

    assert isinstance(audio, sr.AudioData)
    assert calls == ["cue"]


def test_typed_text_fires_the_cue_once_and_hands_back_the_text():
    """Typed text skips the mic entirely: the cue still fires once, and the "audio" handed to
    the transcriber is just the text (its `FakeTranscriber` partner ignores it anyway)."""
    calls = []

    audio = typed_get_audio(QUESTION)(lambda: calls.append("cue"))

    assert calls == ["cue"]
    assert audio == QUESTION


def test_same_typed_question_twice_yields_identical_records_and_spends_nothing(caplog, log_lines):
    """Two offline runs of the same typed question must log the same capture and question
    records, and neither may reach a real fortune service.

    The `secs=` token is stripped before comparing the capture lines: it is wall-clock time
    for the attempt, formatted to a tenth of a second, and can legitimately read 0.0 on one
    run and 0.1 on the next on a busy machine. Everything else on the line must match.
    """
    fortune = FakeFortune()
    # Exactly what main() wires for: --mode simulate --dry-run --offline --question "..."
    serial_trigger.configure_providers(
        get_audio=typed_get_audio(QUESTION),
        transcribe=FakeTranscriber(QUESTION),
        fortune=fortune,
        audio_out=None,
    )
    caplog.set_level(logging.INFO)

    serial_trigger.on_coin_event(pulses=1, dry_run=True)
    serial_trigger.on_coin_event(pulses=1, dry_run=True)

    capture_lines = log_lines("capture ", expect=2)
    question_lines = log_lines("question ", expect=2)

    without_timing = [re.sub(r" secs=\S+", "", line) for line in capture_lines]
    assert without_timing[0] == without_timing[1]
    for line in capture_lines:
        assert "outcome=heard" in line
        assert f'heard="{QUESTION}"' in line

    assert question_lines[0] == question_lines[1]
    assert question_lines[0] == f'question source=heard text="{QUESTION}"'

    # Both fortunes came from the fake: no real fortune call happened.
    assert fortune.questions == [QUESTION, QUESTION]


def test_offline_alone_needs_no_microphone(caplog, log_lines):
    """`--offline` with neither `--clip` nor `--question` must not open the microphone: it
    runs the persona's default question as typed text, so a tester with no hardware at all
    still gets a fortune — and the log shows that default as what was heard."""
    args = argparse.Namespace(offline=True, clip=None, question=None)

    get_audio, transcribe, fortune = serial_trigger.build_providers(args)

    assert get_audio is not serial_trigger.mic_get_audio
    assert isinstance(fortune, FakeFortune)

    serial_trigger.configure_providers(get_audio, transcribe, fortune, None)
    caplog.set_level(logging.INFO)
    serial_trigger.on_coin_event(pulses=1, dry_run=True)

    default_question = serial_trigger._config["default_question"]
    capture_line = log_lines("capture ", expect=1)[0]
    assert f'outcome=heard heard="{default_question}"' in capture_line
    assert fortune.questions == [default_question]
