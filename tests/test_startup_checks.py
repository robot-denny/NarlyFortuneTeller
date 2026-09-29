"""Tests for `serial_trigger.check_can_start`, the check `main()` runs before
the first coin.

Without an OpenAI key, every coin would print the fallback slip and never say
why. So a run that will call OpenAI refuses to start, with one ERROR line
naming `.env`, and exits with code 78, the standard "configuration error"
code. On the Pi, the service is told never to restart on 78, so it stops at
once with the reason in the log. An `--offline` run makes no OpenAI call, so
it needs no key.

Each test passes its own `env` dict, so the real environment and the real
`.env` file are never read or changed.
"""

import pytest

import serial_trigger
from tests.conftest import errors_logged as _errors


def _args(*flags):
    return serial_trigger.build_parser().parse_args(list(flags))


@pytest.mark.parametrize("env", [{}, {"OPENAI_API_KEY": ""}], ids=["unset", "empty"])
def test_no_key_in_hardware_mode_refuses_to_start(env, caplog):
    with pytest.raises(SystemExit) as exit_info:
        serial_trigger.check_can_start(_args("--mode", "hardware"), env=env)

    assert exit_info.value.code == 78
    errors = _errors(caplog)
    assert len(errors) == 1
    assert "OPENAI_API_KEY" in errors[0]
    assert ".env" in errors[0]
    assert ".env.example" in errors[0]


def test_a_question_without_offline_still_needs_the_key(caplog):
    with pytest.raises(SystemExit) as exit_info:
        serial_trigger.check_can_start(
            _args("--mode", "simulate", "--question", "Will it rain?"), env={})

    assert exit_info.value.code == 78


def test_no_key_offline_starts(caplog):
    serial_trigger.check_can_start(_args("--mode", "simulate", "--offline"), env={})

    assert _errors(caplog) == []


def test_key_present_starts(caplog):
    serial_trigger.check_can_start(_args("--mode", "hardware"), env={"OPENAI_API_KEY": "sk-test"})

    assert _errors(caplog) == []
