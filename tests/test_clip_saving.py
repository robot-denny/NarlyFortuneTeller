"""Tests for saving what Narly heard during a measuring session.

`--save-clips DIR` wraps the real microphone so each attendee's audio is kept
as `<DIR>/<label>.wav`, and the log says which label each run had. The inner
microphone here is always a lambda: no test opens a real mic.
"""

import argparse
import logging
import subprocess
import sys
import wave

import pytest
import speech_recognition as sr

import serial_trigger
from capture_client import clip_saving_get_audio


RATE = 16000


def _one_second_of_silence():
    """1 s of 16 kHz mono 16-bit silence, as the recognizer's own audio type."""
    return sr.AudioData(b"\x00\x00" * RATE, RATE, 2)


def _messages(caplog):
    return [r.getMessage() for r in caplog.records]


def test_saves_the_heard_audio_under_its_label_and_logs_the_label_first(tmp_path, caplog):
    caplog.set_level(logging.INFO)
    audio = _one_second_of_silence()
    get_audio = clip_saving_get_audio(lambda on_ready: audio, tmp_path, lambda: "27")

    returned = get_audio(lambda: None)

    assert returned is audio
    saved = tmp_path / "27.wav"
    with wave.open(str(saved), "rb") as w:
        assert w.getframerate() == RATE
        assert w.getnframes() == RATE  # one second at 16 kHz
    messages = _messages(caplog)
    first_id = next(i for i, m in enumerate(messages) if m == "clip id=27")
    first_saved = next(i for i, m in enumerate(messages) if m.startswith("clip saved id=27 "))
    assert first_id < first_saved
    assert messages[first_saved] == f"clip saved id=27 path={saved}"


def test_a_run_with_no_speech_is_still_labelled_and_saves_nothing(tmp_path, caplog):
    caplog.set_level(logging.INFO)

    def nobody_spoke(on_ready):
        raise sr.WaitTimeoutError("listening timed out")

    get_audio = clip_saving_get_audio(nobody_spoke, tmp_path, lambda: "27")

    with pytest.raises(sr.WaitTimeoutError, match="listening timed out"):
        get_audio(lambda: None)

    assert list(tmp_path.iterdir()) == []
    assert "clip id=27" in _messages(caplog)


def test_a_normal_run_uses_the_bare_microphone_and_saves_nothing():
    args = argparse.Namespace(offline=False, clip=None, question=None, save_clips=None)

    get_audio, _, _ = serial_trigger.build_providers(args)

    assert get_audio is serial_trigger.mic_get_audio


def test_save_clips_with_auto_is_refused_before_anything_runs(tmp_path):
    """--auto types no question number, so every clip would land as None.wav and
    overwrite the last. The combination is refused at startup instead.
    (--dry-run and the short timeout keep a regression from printing or lingering.)"""
    result = subprocess.run(
        [sys.executable, "serial_trigger.py", "--mode", "simulate", "--dry-run", "--auto",
         "--save-clips", str(tmp_path / "clips")],
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 2, result.stderr
    assert "--auto" in result.stderr and "--save-clips" in result.stderr
    assert not (tmp_path / "clips").exists()


@pytest.mark.parametrize("typed, count, expected", [
    ("27", 0, ("27", 0)),   # a typed question number is used as it is
    ("", 0, ("1", 1)),      # blank takes the next number
    ("", 4, ("5", 5)),
    ("1 2", 0, ("1", 1)),   # a space would save one name and score another
    ("../x", 2, ("3", 3)),  # a path separator would save outside the folder
])
def test_the_typed_label_or_the_next_number_names_the_clip(typed, count, expected):
    assert serial_trigger.pick_clip_label(typed, count) == expected


def test_an_unusable_label_is_named_in_a_warning(caplog):
    with caplog.at_level(logging.WARNING):
        serial_trigger.pick_clip_label("1 2", 0)
    assert any("1 2" in m and "clip 1" in m for m in _messages(caplog))
