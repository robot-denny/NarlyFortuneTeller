"""Tests for hardware mode's serial loop, `serial_trigger.listen_serial_mode`.

Opening the Arduino's port resets the Uno. So hardware mode must open it once
per run and send the LED commands down that same connection, never open a
second one per coin.

No hardware is touched: `serial.Serial` is replaced by `FakeArduino`, which
plays back a fixed list of lines and records every byte written to it. The
mic, recognizer, fortune and speaker are the fakes from `fakes.py`, wired
through `configure_providers` as `main()` does. Printing is a dry run.
"""

import pytest

import serial_trigger
from fakes import FakeAudioOut, FakeFortune, FakeTranscriber


pytestmark = pytest.mark.usefixtures("quiet_and_configured")

AUDIO = object()  # a sentinel standing in for sr.AudioData


class FakeArduino:
    """Stands in for `serial.Serial`. Each `readline()` returns the next line
    from `LINES`; after the last one it raises KeyboardInterrupt, as Ctrl+C
    would. `opened` lists how each instance was constructed."""

    LINES = [b"COIN 1\n", b"COIN 1\n", b"COIN 1\n"]
    opened = []

    def __init__(self, *args, **kwargs):
        FakeArduino.opened.append((args, kwargs))
        self.written = b""
        self.lines = list(self.LINES)
        self.written_before_each_line = []  # where each line's effects start

    def readline(self):
        self.written_before_each_line.append(len(self.written))
        if not self.lines:
            raise KeyboardInterrupt
        return self.lines.pop(0)

    def write(self, data):
        self.written += data

    def flush(self): pass
    def reset_input_buffer(self): pass
    def close(self): pass


def _commands(written):
    return [line for line in written.decode().split("\n") if line]


def test_two_coins_share_one_connection_and_both_light_the_leds(monkeypatch):
    FakeArduino.opened = []
    ports = []
    monkeypatch.setattr(serial_trigger.serial, "Serial",
                        lambda *a, **kw: ports.append(FakeArduino(*a, **kw)) or ports[-1])
    monkeypatch.setattr(serial_trigger.time, "sleep", lambda s: None)
    serial_trigger.configure_providers(
        get_audio=lambda on_ready: AUDIO,
        transcribe=FakeTranscriber("Will I find treasure today?"),
        fortune=FakeFortune(),
        audio_out=FakeAudioOut(),
    )

    serial_trigger.listen_serial_mode("/dev/fake-arduino", dry_run=True)

    # One open for the whole run, and nobody else may share the port.
    assert len(FakeArduino.opened) == 1
    assert FakeArduino.opened[0][1].get("exclusive") is True

    # Slice what the Arduino received by the coin line that caused it. Line 1
    # is the ignored first coin; lines 2 and 3 are the two real coins.
    ser = ports[0]
    marks = ser.written_before_each_line + [len(ser.written)]
    first_coin, second_coin = (ser.written[marks[i]:marks[i + 1]] for i in (1, 2))
    for coin in (first_coin, second_coin):
        assert "START GLOW" in _commands(coin)
        assert "STOP" in _commands(coin)
