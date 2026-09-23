"""Fixtures shared by the tests that drive `serial_trigger.on_coin_event`.

pytest loads this file automatically for the whole `tests/` directory. The
fixtures here are NOT autouse: a test file that drives `on_coin_event` opts in
with `pytestmark = pytest.mark.usefixtures("quiet_and_configured")`, so the four
test files that never touch `serial_trigger` stay independent of it.
"""

import pytest

import serial_trigger
from config_loader import load_config


class _NoLeds:
    """Stands in for LedClient so a test never opens the real serial port.

    Without this, a test on the owner's laptop with the Arduino plugged in would
    open the port, pay the two-second Uno reset, and animate the booth's LEDs."""

    def start(self, *args, **kwargs): pass
    def stop(self): pass
    def close(self): pass


@pytest.fixture
def quiet_and_configured(monkeypatch):
    """Load the default persona and silence the speaker and LEDs for a test.

    `on_coin_event` still plays its sound cues through macOS `afplay` at this
    step (the in-process player arrives in Step 7). Replacing it with a no-op
    keeps the test run silent; production code is untouched. `LedClient` is
    replaced for the same reason — see `_NoLeds`.

    The module globals the tests set (`_config` and the four providers) are put
    back afterwards, so no test file inherits what the last test wired.
    """
    monkeypatch.setattr(serial_trigger, "afplay", lambda *args, **kwargs: None)
    monkeypatch.setattr(serial_trigger, "LedClient", lambda *args, **kwargs: _NoLeds())
    saved = (serial_trigger._config, serial_trigger._get_audio, serial_trigger._transcribe,
             serial_trigger._fortune, serial_trigger._audio_out)
    serial_trigger._config = load_config("default")
    yield
    (serial_trigger._config, serial_trigger._get_audio, serial_trigger._transcribe,
     serial_trigger._fortune, serial_trigger._audio_out) = saved


@pytest.fixture
def log_lines(caplog):
    """Return a helper that finds the log messages starting with a prefix.

    `log_lines("capture ")` gives every capture record's message, in order.
    `log_lines("capture ", expect=1)` also asserts exactly that many were found,
    so a test does not have to repeat the count check itself."""

    def _find(prefix, expect=None):
        matches = [r.getMessage() for r in caplog.records if r.getMessage().startswith(prefix)]
        if expect is not None:
            assert len(matches) == expect, f"expected {expect} {prefix!r} record(s), got: {matches!r}"
        return matches

    return _find
