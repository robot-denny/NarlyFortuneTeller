import logging

import led_client
from led_client import LedClient


class FakeSerial:
    """Stands in for pyserial's Serial. Records what was written, how it was
    opened, and how many times it was closed."""

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.written = b""
        self.closed = 0

    def write(self, data):
        self.written += data

    def flush(self):
        pass

    def close(self):
        self.closed += 1


def _client(monkeypatch):
    monkeypatch.setattr(led_client.serial, "Serial", FakeSerial)
    monkeypatch.setattr(led_client.time, "sleep", lambda s: None)
    return LedClient("/dev/fake")


def _commands_seen_by_arduino(written):
    # The sketch reads one line at a time and ignores lines it doesn't know.
    return [line for line in written.decode().split("\n") if line]


def test_each_command_is_sent_more_than_once(monkeypatch):
    led = _client(monkeypatch)

    led.start("PULSE")
    led.stop()

    assert _commands_seen_by_arduino(led._ser.written) == ["START PULSE"] * 3 + ["STOP"] * 3


def test_a_cut_off_copy_does_not_spoil_the_next(monkeypatch):
    led = _client(monkeypatch)
    led.stop()

    # The Arduino misses the tail of the first copy while it updates the strip.
    first = b"\nSTOP\n"
    garbled = led._ser.written.replace(first, b"\nST", 1)

    assert "STOP" in _commands_seen_by_arduino(garbled)


def test_no_port_means_no_leds_and_no_wait(monkeypatch):
    # With no Arduino found, Narly passes port None. That must not open
    # anything, and must not spend the 2 s an Uno needs to reset.
    opened, slept = [], []
    monkeypatch.setattr(led_client.serial, "Serial", lambda *a, **kw: opened.append(a) or FakeSerial())
    monkeypatch.setattr(led_client.time, "sleep", slept.append)

    led = LedClient(None)
    led.start("GLOW")
    led.stop()
    led.close()

    assert opened == []
    assert slept == []


def test_no_port_given_means_no_leds(monkeypatch):
    # The old default was a Mac-only path. With no port named, open nothing.
    opened = []
    monkeypatch.setattr(led_client.serial, "Serial", lambda *a, **kw: opened.append(a) or FakeSerial())
    monkeypatch.setattr(led_client.time, "sleep", lambda s: None)

    LedClient().start("GLOW")

    assert opened == []


def test_port_is_opened_exclusively(monkeypatch):
    # A second Narly (or a stray serial monitor) must not share the Arduino.
    opened = []
    monkeypatch.setattr(led_client.serial, "Serial", lambda *a, **kw: opened.append(kw) or FakeSerial())
    monkeypatch.setattr(led_client.time, "sleep", lambda s: None)

    LedClient("/dev/fake")

    assert opened[0].get("exclusive") is True


def test_a_failed_open_logs_one_warning_with_a_hint(monkeypatch, caplog):
    def busy(*a, **kw):
        raise OSError("Resource busy")
    monkeypatch.setattr(led_client.serial, "Serial", busy)
    monkeypatch.setattr(led_client.time, "sleep", lambda s: None)
    caplog.set_level(logging.WARNING)

    led = LedClient("/dev/fake")
    led.start("GLOW")  # still safe to use: it just does nothing

    warnings = [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 1
    assert "/dev/fake" in warnings[0]
    assert "is Narly already running?" in warnings[0]
    assert "sudo systemctl stop narly" in warnings[0]


def test_sharing_writes_to_the_given_port_without_waiting(monkeypatch):
    slept = []
    monkeypatch.setattr(led_client.time, "sleep", slept.append)
    ser = FakeSerial()

    led = LedClient.sharing(ser)
    led.start("GLOW")
    led.stop()

    assert _commands_seen_by_arduino(ser.written) == ["START GLOW"] * 3 + ["STOP"] * 3
    assert 2.0 not in slept  # no Uno reset wait: the owner already opened it


def test_closing_a_shared_client_leaves_the_port_open(monkeypatch):
    monkeypatch.setattr(led_client.time, "sleep", lambda s: None)
    ser = FakeSerial()

    led = LedClient.sharing(ser)
    led.close()
    led.stop()  # the owner still uses the port after the LED client is done

    assert ser.closed == 0
    assert _commands_seen_by_arduino(ser.written) == ["STOP"] * 3


class FlakySerial(FakeSerial):
    """A port whose writes fail a set number of times, then work again, as a
    USB hiccup would."""

    def __init__(self, failures, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.failures = failures

    def write(self, data):
        if self.failures:
            self.failures -= 1
            raise OSError("write failed")
        super().write(data)


def test_one_failed_write_does_not_turn_the_leds_off_for_good(monkeypatch, caplog):
    # The shared client lasts the whole run, so a single glitch must not leave
    # every later attendee without LEDs. The failure is logged once.
    monkeypatch.setattr(led_client.time, "sleep", lambda s: None)
    port = FlakySerial(failures=1)
    led = LedClient.sharing(port)

    with caplog.at_level(logging.WARNING):
        led.start("GLOW")   # fails
        led.stop()          # works again

    assert "STOP" in _commands_seen_by_arduino(port.written)
    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 1
    assert "LED command failed" in warnings[0].getMessage()


def test_a_port_that_keeps_failing_is_logged_once_not_every_command(monkeypatch, caplog):
    monkeypatch.setattr(led_client.time, "sleep", lambda s: None)
    led = LedClient.sharing(FlakySerial(failures=100))

    with caplog.at_level(logging.WARNING):
        for _ in range(5):
            led.start("GLOW")
            led.stop()

    assert sum(r.levelno == logging.WARNING for r in caplog.records) == 1
