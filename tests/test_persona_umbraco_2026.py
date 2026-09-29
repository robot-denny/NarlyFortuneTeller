"""Guards on the umbraco-2026 persona's instructions.

The fortunes themselves are judged by reading, since a model's wording can't be
pinned by a test. These tests cover what is deterministic: the loaded persona
instructions no longer carry the dead 2025 rules, and the almanac is dated.

Run from the repo root with:  .venv/bin/python -m pytest -q
"""

import re

from config_loader import load_config


def _system_prompt():
    return load_config("umbraco-2026")["system_prompt"]


def test_umbraco_2026_no_longer_deflects_by_keyword():
    """The 2025 keyword trigger list is gone: deflection is by intent now."""
    assert "best, top, worst, compare" not in _system_prompt()


def test_umbraco_2026_drops_dead_2025_rules():
    """The October 2023 guard, the anti-repetition section and the stray command line are gone."""
    prompt = _system_prompt()
    for dead in ("October 2023", "Anti-repetition", "python serial_trigger.py"):
        assert dead not in prompt, f"dead 2025 rule still in the prompt: {dead!r}"


def test_umbraco_2026_almanac_is_dated():
    """Narly's almanac says when its facts were true."""
    assert re.search(r"^As of: \d{4}-\d{2}-\d{2}", _system_prompt(), re.MULTILINE)
