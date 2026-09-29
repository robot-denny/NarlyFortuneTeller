"""Tests for the order in which serial_trigger.mic_get_audio does its three jobs.

This is the software half of Acceptance Criteria 6 and 7. Attendees start
talking the moment the readiness chime ends, so the microphone must already be
calibrated by then and must start listening on the very next step. And the
wake threshold must be the speech library's own (300, adapting to the room),
not a fixed number of ours.

No real microphone is opened. `FakeRecognizer` and `FakeMic` below stand in
for `sr.Recognizer()` and `sr.Microphone()` and simply write down what was
asked of them, in order, in a shared `events` list.
"""

import serial_trigger


AUDIO = object()  # a sentinel standing in for the sr.AudioData listen() returns


class FakeMic:
    """Stands in for sr.Microphone(): usable in `with mic as source:`, records nothing."""

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class FakeRecognizer:
    """Stands in for sr.Recognizer(), starting from the library's own defaults.

    Each method appends a word to the shared `events` list, so the test can see
    the exact order calibration, the chime, and listening happened in."""

    def __init__(self, events):
        self.events = events
        self.energy_threshold = 300
        self.dynamic_energy_threshold = True
        self.pause_threshold = 0.8

    def adjust_for_ambient_noise(self, source, duration=1):
        self.events.append("calibrate")

    def listen(self, source, **kw):
        self.events.append("listen")
        return AUDIO


def _run():
    events = []
    fake = FakeRecognizer(events)
    audio = serial_trigger.mic_get_audio(
        on_ready=lambda: events.append("cue"),
        recognizer=fake,
        mic=FakeMic(),
    )
    return events, fake, audio


def test_calibration_happens_before_the_chime_and_listening_right_after_it():
    """Calibrate while the attendee is not yet cued, then chime, then listen at once."""
    events, _, audio = _run()

    assert events == ["calibrate", "cue", "listen"]
    assert audio is AUDIO  # whatever listen() heard is what comes back


def test_calibrated_threshold_is_kept_and_held_while_listening():
    """The room measurement is not overwritten, and it stops adapting once taken.

    Adapting mid-question raised the threshold toward the speaker's loudness, so
    a softer last word counted as the pause and was cut off."""
    _, fake, _ = _run()

    assert fake.energy_threshold == 300  # nothing overwrites what calibration set
    assert fake.dynamic_energy_threshold is False


def test_pause_threshold_still_allows_thinking_pauses():
    """An attendee can pause 1.5s mid-question without being cut off."""
    _, fake, _ = _run()

    assert fake.pause_threshold == 1.5
