import led_client
from led_client import LedClient


class FakeSerial:
    def __init__(self, *args, **kwargs):
        self.written = b""

    def write(self, data):
        self.written += data

    def flush(self):
        pass

    def close(self):
        pass


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
