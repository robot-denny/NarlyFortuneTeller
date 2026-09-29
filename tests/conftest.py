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
def quiet_and_configured():
    """Load the default persona and silence the LEDs for a test.

    The speaker needs no stub here: `on_coin_event` plays sound only through the
    `audio_out` provider, and every test wires a `FakeAudioOut` there, which
    records the request and makes no sound. The run's shared LED client,
    `serial_trigger._led`, is set to `_NoLeds` so the test never touches the
    Arduino. A test that opens a (fake) port through `listen_serial_mode`
    replaces it, and this fixture puts it back.

    The module globals the tests set (`_config`, `_led`, and the four
    providers) are put back afterwards, so no test file inherits what the last
    test wired.
    """
    saved = (serial_trigger._config, serial_trigger._led, serial_trigger._get_audio,
             serial_trigger._transcribe, serial_trigger._fortune, serial_trigger._audio_out)
    serial_trigger._config = load_config("default")
    serial_trigger._led = _NoLeds()
    yield
    (serial_trigger._config, serial_trigger._led, serial_trigger._get_audio,
     serial_trigger._transcribe, serial_trigger._fortune, serial_trigger._audio_out) = saved


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


def errors_logged(caplog):
    """The messages of every ERROR record captured so far, in order."""
    return [r.getMessage() for r in caplog.records if r.levelname == "ERROR"]
