"""Tests for saving what Narly heard during a measuring session.

`--save-clips DIR` wraps the real microphone so each attendee's audio is kept
as `<DIR>/<label>.wav`, and the log says which label each run had. The inner
microphone here is always a lambda: no test opens a real mic.
"""

import argparse
import logging
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
