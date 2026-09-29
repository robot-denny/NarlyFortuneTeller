"""Finding the Arduino on either machine, and waiting for it.

The Arduino's port name changes with the USB-C jack on the laptop, and is a
different kind of name again on the Pi. These tests describe the ports each
machine really lists (as seen on 2026-09-28) and check that Narly picks the
Arduino out of them, that `--port` is optional, and that hardware mode waits
for a late Arduino instead of giving up.
"""
from types import SimpleNamespace

import serial_trigger


def _port(device, description, vid):
    """A port shaped like one entry from serial.tools.list_ports.comports()."""
    return SimpleNamespace(device=device, description=description, vid=vid)


BLUETOOTH = _port("/dev/cu.Bluetooth-Incoming-Port", "n/a", None)


# ---- (a) find_port ----

def test_finds_the_arduino_on_the_laptop():
    ports = [BLUETOOTH, _port("/dev/cu.usbmodem1101", "IOUSBHostDevice", 0x2341)]
    assert serial_trigger.find_port(ports) == "/dev/cu.usbmodem1101"


def test_finds_the_arduino_on_the_pi():
    ports = [_port("/dev/ttyAMA0", "ttyAMA0", None), _port("/dev/ttyACM0", "ttyACM0", 0x2341)]
    assert serial_trigger.find_port(ports) == "/dev/ttyACM0"


def test_finds_an_arduino_org_board_by_its_vendor_id():
    ports = [_port("/dev/ttyACM1", "ttyACM1", 0x2A03)]
    assert serial_trigger.find_port(ports) == "/dev/ttyACM1"


def test_finds_nothing_when_no_arduino_is_plugged_in():
    assert serial_trigger.find_port([BLUETOOTH]) is None


# ---- (b) --port is optional ----

def test_port_defaults_to_auto_detect():
    assert serial_trigger.build_parser().parse_args([]).port is None


def test_port_flag_overrides_detection():
    assert serial_trigger.build_parser().parse_args(["--port", "/dev/x"]).port == "/dev/x"


# ---- (c) wait_for_port ----

def test_waits_until_the_arduino_appears(caplog):
    answers = iter([None, None, "/dev/ttyACM0"])
    sleeps = []

    with caplog.at_level("INFO"):
        port = serial_trigger.wait_for_port(find=lambda: next(answers), sleep=sleeps.append)

    assert port == "/dev/ttyACM0"
    assert len(sleeps) == 2
    assert sum("Waiting for the Arduino" in r.getMessage() for r in caplog.records) == 1


def test_repeats_the_waiting_line_about_once_a_minute(caplog):
    # Five minutes of empty tries at one try every 2 s, then the Arduino appears.
    answers = iter([None] * 150 + ["/dev/ttyACM0"])

    with caplog.at_level("INFO"):
        serial_trigger.wait_for_port(find=lambda: next(answers), sleep=lambda s: None)

    lines = sum("Waiting for the Arduino" in r.getMessage() for r in caplog.records)
    assert lines == 5


def test_does_not_wait_when_the_arduino_is_already_there(caplog):
    sleeps = []
    with caplog.at_level("INFO"):
        port = serial_trigger.wait_for_port(find=lambda: "/dev/ttyACM0", sleep=sleeps.append)

    assert port == "/dev/ttyACM0"
    assert sleeps == []
    assert not any("Waiting for the Arduino" in r.getMessage() for r in caplog.records)


def test_a_failing_port_scan_says_why_it_is_still_waiting(caplog, monkeypatch):
    # Listing the ports fails once (as a permissions problem would on the Pi),
    # then works. The waiting line carries the reason instead of hiding it.
    import serial.tools.list_ports

    def comports_answers():
        yield PermissionError("no access to /dev")
        yield [_port("/dev/ttyACM0", "ttyACM0", 0x2341)]

    answers = comports_answers()

    def comports():
        answer = next(answers)
        if isinstance(answer, Exception):
            raise answer
        return answer

    monkeypatch.setattr(serial.tools.list_ports, "comports", comports)

    with caplog.at_level("INFO"):
        port = serial_trigger.wait_for_port(sleep=lambda s: None)

    assert port == "/dev/ttyACM0"
    waiting = [r.getMessage() for r in caplog.records if "Waiting for the Arduino" in r.getMessage()]
    assert len(waiting) == 1
    assert "port scan failed: no access to /dev" in waiting[0]


def test_find_port_still_returns_none_when_the_scan_fails(monkeypatch):
    # Simulate mode calls find_port() directly and must carry on without LEDs.
    import serial.tools.list_ports

    def comports():
        raise PermissionError("no access to /dev")

    monkeypatch.setattr(serial.tools.list_ports, "comports", comports)
    assert serial_trigger.find_port() is None
