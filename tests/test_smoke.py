"""Smoke tests: pin two behaviours the rest of the project already trusts.

Run from the repo root with:  .venv/bin/python -m pytest -q

Nothing here touches the mic, serial port, printer, or network, so these
pass with no hardware plugged in and no .env file.
"""

from config_loader import list_personas, load_config
from formatters import render_ticket


def test_list_personas_returns_the_three_known_personas():
    """Config loading still finds every persona folder that has a content.json."""
    # Update this list when a persona folder is added or removed — that is a
    # deliberate content change, and this test exists to make you notice it.
    assert list_personas() == ["default", "music", "umbraco-2025"]


def test_render_ticket_never_exceeds_thermal_printer_width():
    """Every rendered line fits the Maikrt 58mm thermal printer, which prints 32 characters per line."""
    ticket = render_ticket("hello", load_config("default"))
    for line in ticket.split("\n"):
        assert len(line) <= 32, f"line too wide for the printer: {line!r}"
