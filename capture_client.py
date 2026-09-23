"""Capture the attendee's spoken question and say exactly what happened.

Before this module existed, every way the microphone step could fail looked
the same from the outside: the orchestrator got back ``None`` and printed the
default fortune. Nothing recorded WHICH failure struck, so there was no way to
count them over a day and see what to fix. This module runs the two capture
stages — get audio from the mic, then turn it into text — and always returns a
``CaptureResult`` naming one of six outcomes. It never raises: whatever goes
wrong, the fortune teller still gets an answer it can act on and log.

The six outcomes (``CaptureOutcome``):

- ``heard`` — the attendee spoke and the recognizer returned their words.
- ``no_speech`` — the attendee said nothing, or too quietly, before the
  listening window closed.
- ``not_understood`` — sound was captured, but the recognizer could not make
  out any words in it (a cough, crowd noise, a mumble).
- ``recognizer_error`` — the speech-to-text service could not be reached or
  failed on its side (no network, quota, an unexpected fault in that stage).
- ``mic_error`` — the microphone itself could not be opened or read (no
  device, the audio library missing, a permissions problem).
- ``overrun`` — the whole attempt ran past the outer time guard, whatever the
  microphone or recognizer would eventually have said.

Every failure also carries a short ``detail`` — the error's own message, or
its name if it had none — so the log can say not just *that* the mic failed
but *how* ("Could not find PyAudio" and "permission denied" are different
problems with different fixes).

For maintainers: the mic and the recognizer are not imported here. They are
handed in as two small functions, ``get_audio`` and ``transcribe``, so the
same code runs against the real microphone, a recorded WAV file, or a
one-line stand-in inside a test.
"""

import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from dataclasses import dataclass
from enum import Enum

import speech_recognition as sr


class CaptureOutcome(Enum):
    """What happened when we tried to hear the attendee. The string values are
    what appears in the log line, e.g. ``capture outcome=no_speech``."""

    HEARD = "heard"
    NO_SPEECH = "no_speech"
    NOT_UNDERSTOOD = "not_understood"
    RECOGNIZER_ERROR = "recognizer_error"
    MIC_ERROR = "mic_error"
    OVERRUN = "overrun"


@dataclass
class CaptureResult:
    """The answer from one capture attempt.

    ``text`` is the attendee's words when ``outcome`` is ``HEARD`` and ``None``
    otherwise. ``seconds`` is how long the whole attempt took, measured even
    when it failed. ``detail`` says why a failure happened, in the error's own
    words; it is ``None`` when the attendee was heard."""

    outcome: CaptureOutcome
    text: str | None
    seconds: float
    detail: str | None = None


def _describe(error: BaseException) -> str:
    """The error's message, or its class name when it carries no message
    (``sr.UnknownValueError()`` is raised bare, and an empty detail is useless)."""
    return str(error) or type(error).__name__


def capture_question(get_audio, transcribe, on_ready=lambda: None, overall_timeout=25.0) -> CaptureResult:
    """Run one capture attempt and report which of the six outcomes occurred.

    ``get_audio(on_ready)`` is the microphone side. It is handed the
    ``on_ready`` callback and must call it at the moment the attendee should
    start speaking (the orchestrator uses that to play the readiness chime).
    It returns audio for ``transcribe`` or raises: ``sr.WaitTimeoutError``
    when nobody spoke in time, anything else when the mic itself failed.

    ``transcribe(audio)`` is the recognizer side. It returns the words as a
    string or raises: ``sr.UnknownValueError`` when it found no words,
    ``sr.RequestError`` when the service could not be reached. Any other
    exception from this stage is treated as the recognizer's fault too.

    ``overall_timeout`` is the outer guard in seconds. If both stages together
    have not finished by then, the outcome is ``OVERRUN``.

    This function never raises. Every path returns a ``CaptureResult``.
    """
    started = time.monotonic()

    def attempt() -> CaptureResult:
        # Stage 1: the microphone. Caught separately from stage 2 so that a
        # surprise exception here is blamed on the mic, not the recognizer.
        try:
            audio = get_audio(on_ready)
        except sr.WaitTimeoutError as e:
            return CaptureResult(CaptureOutcome.NO_SPEECH, None, 0.0, _describe(e))
        except Exception as e:
            return CaptureResult(CaptureOutcome.MIC_ERROR, None, 0.0, _describe(e))

        # Stage 2: the recognizer.
        try:
            text = transcribe(audio)
        except sr.UnknownValueError as e:
            return CaptureResult(CaptureOutcome.NOT_UNDERSTOOD, None, 0.0, _describe(e))
        except sr.RequestError as e:
            return CaptureResult(CaptureOutcome.RECOGNIZER_ERROR, None, 0.0, _describe(e))
        except Exception as e:
            return CaptureResult(CaptureOutcome.RECOGNIZER_ERROR, None, 0.0, _describe(e))

        # A recognizer that returns nothing has, for our purposes, understood
        # nothing. Never report HEARD with no words — the log would then say
        # "heard" right beside a substituted question.
        if not text:
            return CaptureResult(CaptureOutcome.NOT_UNDERSTOOD, None, 0.0, "recognizer returned no words")

        return CaptureResult(CaptureOutcome.HEARD, text, 0.0)

    # Same shape as serial_trigger.py's existing timeout wrappers. Note that
    # leaving the ``with`` block waits for the worker thread to finish, so on
    # OVERRUN the caller still blocks until get_audio/transcribe returns; the
    # timeout decides the outcome, not how long we wait. Preserved on purpose.
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(attempt)
        try:
            result = future.result(timeout=overall_timeout)
        except FutureTimeoutError:
            result = CaptureResult(CaptureOutcome.OVERRUN, None, 0.0, f"exceeded {overall_timeout}s")

    result.seconds = time.monotonic() - started
    return result
