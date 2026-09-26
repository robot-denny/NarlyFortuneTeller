"""Plays Narly's short sound cues through the computer's speaker.

Replaces the old macOS-only `afplay` command with `pygame.mixer`, which plays
the existing `.mp3` files in-process on macOS and on Linux (the Raspberry Pi).

It degrades gracefully, like `LedClient`: if pygame is not installed or there
is no sound device, the player logs one warning at startup and every `play()`
quietly does nothing — the fortune still runs and still prints.

Volume note: pygame's volume only goes from 0.0 to 1.0 (full), so the old
`afplay -v 3.0` boost is gone. Turn the physical speaker up to compensate.
"""

import os
import time

from logger import get_logger

log = get_logger(__name__)

# pygame prints a "Hello from the pygame community" banner on import; keep the
# booth's log clean.
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

# The longest `play(..., wait=True)` will wait. The readiness chime is about 2s;
# if the speaker never reports it finished, give up rather than freeze the booth.
MAX_WAIT_SECONDS = 5.0


class PygameAudioOut:
    """The real speaker. `FakeAudioOut` in `fakes.py` stands in for it in tests."""

    def __init__(self):
        self.available = False
        try:
            import pygame
            pygame.mixer.init()
            self._music = pygame.mixer.music
            self.available = True
        except Exception as e:
            log.warning(f"audio_out unavailable: {e}")

    def play(self, path, wait=False, max_wait=MAX_WAIT_SECONDS):
        """Play the sound file at `path`.

        With `wait=True` this returns only once the sound has finished — that
        is how listening starts the instant the readiness chime ends. With
        `wait=False` it starts the sound and returns at once. The wait never
        lasts longer than `max_wait` seconds: past that the sound is stopped
        and logged as stuck, so a speaker fault cannot hang the fortune.
        Never raises: a missing file or a playback problem is logged and skipped.
        """
        # The file check comes first so a missing cue is reported even on a
        # machine with no speaker — it is a setup mistake either way.
        if not path or not os.path.exists(path):
            log.warning(f"sfx missing: {path}")
            return
        if not self.available:
            return
        try:
            self._music.load(path)
            self._music.set_volume(1.0)  # pygame's maximum
            self._music.play()
            if wait:
                deadline = time.monotonic() + max_wait
                while self._music.get_busy():
                    if time.monotonic() >= deadline:
                        self._music.stop()
                        log.warning(f"sfx stuck: {path}")
                        return
                    time.sleep(0.01)
        except Exception as e:
            log.warning(f"sfx failed: {path}: {e}")

    def is_busy(self):
        """True while a sound is still playing."""
        return self.available and bool(self._music.get_busy())
