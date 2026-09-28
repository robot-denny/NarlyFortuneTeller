"""Tests for fakes.py — the hardware-free stand-ins wired by --mode simulate."""

import pytest
import speech_recognition as sr

from fakes import FakeAudioOut, FakeFortune, FakeTranscriber


def test_transcriber_returns_configured_text():
    """Whatever audio it is given, the fake hands back the text it was built with."""
    transcribe = FakeTranscriber(text="Will I find treasure today?")

    assert transcribe(b"ignored") == "Will I find treasure today?"


def test_transcriber_raises_the_given_exception_instance():
    """'Heard but not understood' — the fake raises the very object it was given."""
    not_understood = sr.UnknownValueError()
    transcribe = FakeTranscriber(raises=not_understood)

    with pytest.raises(sr.UnknownValueError) as excinfo:
        transcribe(b"ignored")

    assert excinfo.value is not_understood


def test_transcriber_raises_request_error_instance():
    """'Recognizer unreachable' — a different failure kind, same raise-what-you-were-given rule."""
    service_down = sr.RequestError("down")
    transcribe = FakeTranscriber(raises=service_down)

    with pytest.raises(sr.RequestError) as excinfo:
        transcribe(b"ignored")

    assert excinfo.value is service_down


def test_fortune_returns_default_text_and_records_question():
    """With no text given, the fake returns a fortune that announces itself as a test."""
    fortune = FakeFortune()

    result = fortune("Will I find treasure today?")

    assert result == "[TEST FORTUNE] You will find what you seek."
    assert fortune.questions == ["Will I find treasure today?"]


def test_fortune_returns_custom_text_and_records_every_question():
    """Every question asked is kept, in order, so a test can prove what the fortune call saw."""
    fortune = FakeFortune(text="Beware the tide.")

    first = fortune("First?")
    second = fortune("Second?")

    assert first == "Beware the tide."
    assert second == "Beware the tide."
    assert fortune.questions == ["First?", "Second?"]


def test_audio_out_records_plays_and_is_never_busy():
    """Each cue request is recorded with its wait flag; the fake never blocks."""
    audio_out = FakeAudioOut()

    audio_out.play("sfx/a.mp3", wait=True)
    audio_out.play("sfx/b.mp3")

    assert audio_out.played == [("sfx/a.mp3", True), ("sfx/b.mp3", False)]
    assert audio_out.is_busy() is False
