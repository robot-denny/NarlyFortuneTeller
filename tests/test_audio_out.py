"""Tests for Narly's sound cues — the software half of Acceptance Criterion 8.

Three things are checked here:

1. During a fortune, the readiness chime is requested first and BLOCKING (so
   listening can start the instant it ends), then the "thinking" cue is
   requested without blocking (so the AI call is not held up). `FakeAudioOut`
   records the requests, so this proves the ORDER and the blocking flag, not the
   timing — the real chime's length is checked by hand with a speaker.
2. The real player, `PygameAudioOut`, asked to play a file that does not exist,
   logs a warning and carries on instead of crashing the fortune.
3. If the speaker never reports the chime finished, the wait gives up after
   `max_wait` seconds instead of freezing the booth.
"""

import logging
import time

import pytest

import serial_trigger
from audio_out import PygameAudioOut
from fakes import FakeAudioOut, FakeFortune, FakeTranscriber


pytestmark = pytest.mark.usefixtures("quiet_and_configured")

SENTINEL = object()  # stands in for sr.AudioData
QUESTION = "Will I find treasure today?"


def test_cues_play_in_order_chime_blocking_then_thinking_cue():
    """The chime plays (and is waited on) when the mic is ready; the thinking cue follows."""
    audio_out = FakeAudioOut()
    serial_trigger.configure_providers(
        get_audio=lambda on_ready: (on_ready(), SENTINEL)[1],
        transcribe=FakeTranscriber(QUESTION),
        fortune=FakeFortune(),
        audio_out=audio_out,
    )

    serial_trigger.on_coin_event(1, dry_run=True)

    assert audio_out.played == [
        (serial_trigger.SFX_START, True),
        (serial_trigger.SFX_END, False),
    ]


def test_missing_sound_file_is_logged_not_raised(caplog):
    """A missing cue file must never stop a fortune: it is skipped with one warning."""
    caplog.set_level(logging.WARNING)

    PygameAudioOut().play("/nonexistent.mp3")  # must not raise

    warnings = [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]
    assert "sfx missing: /nonexistent.mp3" in warnings


class _StuckMusic:
    """A pygame music player that starts a sound and never reports it finished."""

    def __init__(self):
        self.stopped = False

    def load(self, path): pass
    def set_volume(self, volume): pass
    def play(self): pass
    def get_busy(self): return not self.stopped
    def stop(self): self.stopped = True


def test_stuck_chime_gives_up_after_max_wait(tmp_path, caplog):
    """If the speaker never reports the chime finished, stop waiting rather than hang the booth."""
    caplog.set_level(logging.WARNING)
    cue = tmp_path / "cue.mp3"
    cue.write_bytes(b"")
    player = PygameAudioOut()
    player.available = True
    player._music = _StuckMusic()

    started = time.monotonic()
    player.play(str(cue), wait=True, max_wait=0.2)
    elapsed = time.monotonic() - started

    assert elapsed < 1.0
    assert player._music.stopped
    warnings = [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]
    assert f"sfx stuck: {cue}" in warnings
