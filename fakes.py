"""Hardware-free stand-ins for the parts of Narly that need a mic, the
network, or a speaker.

These are runtime code, not test-only code: ``serial_trigger.py --mode
simulate`` wires them in so a full fortune can run on a laptop (or a remote
tester's machine) with no hardware attached and no API spend. The unit tests
use the same classes. Each one is deliberately tiny — it stores what it is
given and hands it back, so a test can control exactly what "happened".

How they are used:

- ``FakeTranscriber`` stands in for the speech-to-text call. The ``--offline``
  flag wires it in so no audio leaves the machine.
- ``FakeFortune`` stands in for the OpenAI call. ``--offline`` wires this in
  too, so an offline run costs nothing.
- ``typed_get_audio`` stands in for the microphone when a tester types the
  question instead of speaking it. The ``--question`` flag wires it in,
  always paired with a ``FakeTranscriber`` carrying the same text.
- ``FakeAudioOut`` stands in for the speaker. It is NOT wired in by any flag:
  the real player (``PygameAudioOut`` in ``audio_out.py``) already goes quiet
  on its own when there is no speaker, so a fake is only needed by the tests,
  which use it to check that the cues are requested in the right order.

This is the "degrade gracefully when hardware is absent" rule made concrete:
rather than each module checking for a device, the orchestrator swaps in one
of these and the rest of the code runs unchanged.
"""


class FakeTranscriber:
    """Stands in for the recognizer: returns a fixed ``text`` for any audio,
    or raises the exact exception instance passed as ``raises``.

    Always pass one or the other. Called with neither, it returns ``None`` —
    and further down the line ``None`` is read as "heard nothing", so the
    fortune teller quietly substitutes its default question instead of
    failing loudly. That is a confusing way to discover a missing argument."""

    def __init__(self, text=None, raises=None):
        self.text = text
        self.raises = raises

    def __call__(self, audio):
        if self.raises is not None:
            raise self.raises
        return self.text


class FakeFortune:
    """Stands in for the OpenAI fortune call: returns a fixed ``text`` and
    keeps every question it was asked in ``.questions``.

    The default text is a placeholder for tests and offline runs only — it is
    not persona content, which lives in ``personas/<name>/``. It announces
    itself as a test fortune so that a printed (or dry-run) ticket from an
    offline run cannot be mistaken for a real one."""

    def __init__(self, text="[TEST FORTUNE] You will find what you seek."):
        self.text = text
        self.questions = []

    def __call__(self, question):
        self.questions.append(question)
        return self.text


class FakeAudioOut:
    """Stands in for the speaker: records each ``play`` call as
    ``(path, wait)`` in ``.played``, returns at once, and is never busy.

    Because ``play`` returns instantly even with ``wait=True``, a test using
    this can prove the cues were requested in the right ORDER, but says
    nothing about their TIMING — the real chime takes about two seconds.
    Timing is checked by hand with a real speaker and microphone."""

    def __init__(self):
        self.played = []

    def play(self, path, wait=False):
        self.played.append((path, wait))

    def is_busy(self):
        return False


def typed_get_audio(text):
    """Stands in for the microphone when the question is typed, not spoken.

    Returns a ``get_audio``-shaped function: it takes ``on_ready``, calls it
    once (so the readiness chime still plays and the cue is observable in a
    test), and hands back ``text`` itself as the "audio". That return value is
    just the string — never real audio — so it MUST be paired with
    ``FakeTranscriber(text)``, which ignores its input and returns the same
    words. Handing it to the real Google recognizer would fail.

    Used by ``serial_trigger.py --mode simulate --question "<text>"``."""

    def _(on_ready):
        on_ready()
        return text

    return _
