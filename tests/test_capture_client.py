"""Tests for capture_client.py — one test per capture outcome.

Each test injects two plain callables in place of the microphone and the
recognizer, so no hardware, network, or fixture file is needed. The point of
the six outcome tests is that every failure path comes back as its OWN
outcome — none of them collapses into another, and none of them raises.
"""

import time

import speech_recognition as sr

from capture_client import CaptureOutcome, CaptureResult, capture_question


AUDIO = object()  # a sentinel standing in for sr.AudioData
QUESTION = "Will I find treasure today?"


def _assert_timing(result, at_least=0.0):
    """seconds must be a real measurement: a float no smaller than the time we know
    the attempt had to take (the sleep a test deliberately put in its path)."""
    assert isinstance(result.seconds, float)
    assert result.seconds >= at_least, f"seconds={result.seconds} but the attempt took at least {at_least}"


def test_heard_returns_text():
    """Mic returns audio, recognizer returns text: HEARD carrying that text, no detail."""

    def get_audio(on_ready):
        time.sleep(0.05)  # a known floor, so the timing assertion can catch an unmeasured result
        return AUDIO

    result = capture_question(get_audio=get_audio, transcribe=lambda audio: QUESTION)

    assert isinstance(result, CaptureResult)
    assert result.outcome is CaptureOutcome.HEARD
    assert result.text == QUESTION
    assert result.detail is None
    _assert_timing(result, at_least=0.05)


def test_no_speech_when_listen_times_out():
    """Nobody spoke before the listening window closed: NO_SPEECH."""

    def get_audio(on_ready):
        raise sr.WaitTimeoutError("listening timed out")

    result = capture_question(get_audio=get_audio, transcribe=lambda audio: QUESTION)

    assert result.outcome is CaptureOutcome.NO_SPEECH
    assert result.text is None
    assert result.detail == "listening timed out"
    _assert_timing(result)


def test_not_understood_when_recognizer_cannot_make_out_words():
    """Audio was captured but the recognizer found no words: NOT_UNDERSTOOD."""

    def transcribe(audio):
        raise sr.UnknownValueError()

    result = capture_question(get_audio=lambda on_ready: AUDIO, transcribe=transcribe)

    assert result.outcome is CaptureOutcome.NOT_UNDERSTOOD
    assert result.text is None
    assert result.detail == "UnknownValueError"  # the exception carries no message, so its name stands in
    _assert_timing(result)


def test_recognizer_error_when_service_unreachable():
    """The recognizer service could not be reached: RECOGNIZER_ERROR."""

    def transcribe(audio):
        raise sr.RequestError("service down")

    result = capture_question(get_audio=lambda on_ready: AUDIO, transcribe=transcribe)

    assert result.outcome is CaptureOutcome.RECOGNIZER_ERROR
    assert result.text is None
    assert result.detail == "service down"
    _assert_timing(result)


def test_mic_error_when_get_audio_raises_anything_else():
    """The microphone could not be opened (or any other mic-side fault): MIC_ERROR."""

    def get_audio(on_ready):
        raise OSError("Could not find PyAudio")

    result = capture_question(get_audio=get_audio, transcribe=lambda audio: QUESTION)

    assert result.outcome is CaptureOutcome.MIC_ERROR
    assert result.text is None
    assert result.detail == "Could not find PyAudio"
    _assert_timing(result)


def test_overrun_when_whole_attempt_exceeds_overall_timeout():
    """The attempt ran past the outer guard: OVERRUN, regardless of what the mic would return."""

    def get_audio(on_ready):
        time.sleep(0.3)
        return AUDIO

    result = capture_question(
        get_audio=get_audio,
        transcribe=lambda audio: QUESTION,
        overall_timeout=0.05,
    )

    assert result.outcome is CaptureOutcome.OVERRUN
    assert result.text is None
    assert result.detail == "exceeded 0.05s"
    _assert_timing(result, at_least=0.3)  # the true stall, not the guard — the with-block waits it out


def test_on_ready_is_passed_through_and_called_exactly_once():
    """The cue callback the orchestrator supplies reaches get_audio and fires once."""
    calls = []

    def get_audio(on_ready):
        on_ready()
        return AUDIO

    result = capture_question(
        get_audio=get_audio,
        transcribe=lambda audio: QUESTION,
        on_ready=lambda: calls.append("cue"),
    )

    assert calls == ["cue"]
    assert result.outcome is CaptureOutcome.HEARD


def test_unexpected_transcribe_failure_is_recognizer_error_not_mic_error():
    """A non-speech_recognition exception from the recognizer stage is the
    recognizer's fault, not the microphone's."""

    def transcribe(audio):
        raise RuntimeError("boom")

    result = capture_question(get_audio=lambda on_ready: AUDIO, transcribe=transcribe)

    assert result.outcome is CaptureOutcome.RECOGNIZER_ERROR
    assert result.text is None
    assert result.detail == "boom"
    _assert_timing(result)


def test_empty_transcript_is_not_understood_not_heard():
    """The recognizer returned no words at all: that is NOT_UNDERSTOOD, never HEARD with
    nothing in it — otherwise the log would say "heard" beside a substituted question."""
    result = capture_question(get_audio=lambda on_ready: AUDIO, transcribe=lambda audio: "")

    assert result.outcome is CaptureOutcome.NOT_UNDERSTOOD
    assert result.text is None
    assert result.detail == "recognizer returned no words"
    _assert_timing(result)
