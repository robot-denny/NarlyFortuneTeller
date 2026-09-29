import pytest

import escpos.printer

from print_client import _print_via_escpos


class FakeUsb:
    instances = []
    fail_next = False

    def __init__(self, *args, **kwargs):
        self.lines = []
        self.closed = False
        self.fail_on_text = FakeUsb.fail_next
        FakeUsb.instances.append(self)

    def set(self, **kwargs):
        pass

    def text(self, line):
        if self.fail_on_text:
            raise OSError("printer went away")
        self.lines.append(line)

    def cut(self):
        pass

    def close(self):
        self.closed = True


@pytest.fixture
def fake_usb(monkeypatch):
    FakeUsb.instances = []
    FakeUsb.fail_next = False
    monkeypatch.setattr(escpos.printer, "Usb", FakeUsb)
    monkeypatch.setenv("ESCPOS_USB_VENDOR_ID", "0x0485")
    monkeypatch.setenv("ESCPOS_USB_PRODUCT_ID", "0x5741")
    return FakeUsb


def test_each_ticket_releases_the_printer(fake_usb):
    _print_via_escpos("first")
    _print_via_escpos("second")

    assert [p.closed for p in fake_usb.instances] == [True, True]
    assert fake_usb.instances[1].lines == ["second\n"]


def test_printer_is_released_when_printing_fails(fake_usb):
    fake_usb.fail_next = True

    with pytest.raises(OSError):
        _print_via_escpos("ticket")

    assert fake_usb.instances[0].closed
