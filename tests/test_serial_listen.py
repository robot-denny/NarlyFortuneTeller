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
from tests.conftest import errors_logged as _errors
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


# ---- An Arduino that goes away ends the run cleanly ----
#
# On the Pi, systemd restarts Narly after a non-zero exit, and the restart
# waits for the Arduino to come back. So an unplug must end the run with exit
# code 1 and one ERROR line the operator can read, not a traceback.


class UnpluggedArduino(FakeArduino):
    """Reads like an Arduino whose USB cable is pulled: pyserial raises
    SerialException from `readline()`."""

    def readline(self):
        raise serial_trigger.serial.SerialException(
            "device reports readiness to read but returned no data")


def test_an_unplugged_arduino_ends_the_run_with_code_1_and_one_error(monkeypatch, caplog):
    monkeypatch.setattr(serial_trigger.serial, "Serial", UnpluggedArduino)
    monkeypatch.setattr(serial_trigger.time, "sleep", lambda s: None)

    with pytest.raises(SystemExit) as exit_info:
        serial_trigger.listen_serial_mode("/dev/fake-arduino", dry_run=True)

    assert exit_info.value.code == 1
    errors = _errors(caplog)
    assert len(errors) == 1
    assert errors[0].startswith("Arduino disconnected: ")
    assert "returned no data" in errors[0]
    assert "restart" in errors[0]


def test_a_port_that_cannot_be_opened_ends_the_run_with_code_1_and_a_hint(monkeypatch, caplog):
    def locked_port(*args, **kwargs):
        raise serial_trigger.serial.SerialException("Could not exclusively lock port")

    monkeypatch.setattr(serial_trigger.serial, "Serial", locked_port)
    monkeypatch.setattr(serial_trigger.time, "sleep", lambda s: None)

    with pytest.raises(SystemExit) as exit_info:
        serial_trigger.listen_serial_mode("/dev/fake-arduino", dry_run=True)

    assert exit_info.value.code == 1
    errors = _errors(caplog)
    assert len(errors) == 1
    assert errors[0].startswith("Could not open the Arduino port /dev/fake-arduino: ")
    assert "Could not exclusively lock port" in errors[0]
    assert "is Narly already running?" in errors[0]
    assert "sudo systemctl stop narly" in errors[0]


def test_ctrl_c_still_exits_quietly(monkeypatch, caplog):
    FakeArduino.opened = []
    monkeypatch.setattr(serial_trigger.serial, "Serial", FakeArduino)
    monkeypatch.setattr(serial_trigger.time, "sleep", lambda s: None)
    monkeypatch.setattr(FakeArduino, "LINES", [])  # the first read is Ctrl+C

    serial_trigger.listen_serial_mode("/dev/fake-arduino", dry_run=True)  # no SystemExit

    assert _errors(caplog) == []


# ---- The ready cue ----
#
# Narly lives in a cabinet with no screen. The ready cue is how the operator
# knows, from the booth, that he has started (or restarted) and is waiting for
# a coin.


def test_the_ready_cue_plays_once_before_any_coin(monkeypatch):
    FakeArduino.opened = []
    monkeypatch.setattr(serial_trigger.serial, "Serial", FakeArduino)
    monkeypatch.setattr(serial_trigger.time, "sleep", lambda s: None)
    speaker = FakeAudioOut()
    serial_trigger.configure_providers(
        get_audio=lambda on_ready: AUDIO,
        transcribe=FakeTranscriber("Will I find treasure today?"),
        fortune=FakeFortune(),
        audio_out=speaker,
    )

    serial_trigger.listen_serial_mode("/dev/fake-arduino", dry_run=True)

    played = [path for path, wait in speaker.played]
    assert played[0] == serial_trigger.SFX_READY
    assert played.count(serial_trigger.SFX_READY) == 1
