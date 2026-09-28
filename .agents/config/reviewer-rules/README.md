# Reviewer rules — shared context

Narly the Narwhal is a coin-operated AI fortune teller for festivals: a flat-layout Python 3 app
run from the repo root (`serial_trigger.py` is the entry point) driving the pipeline
Coin → Mic → Speech-to-Text → OpenAI → 58mm thermal printer, with an Arduino Uno sketch
(`arduino/fortune-controller/`) owning coin-pulse interrupts and WS2812B LED animations.

Python and Arduino talk over USB serial at 115200 baud in plain text — Arduino sends `COIN X`,
Python sends `START <mode>` / `STOP`. Event-day reliability is the governing concern: a guest
has paid a coin, so every failure path still prints a fallback slip, and the app must run with
no hardware attached under `--mode simulate --dry-run`.

A pytest suite (`.venv/bin/python -m pytest -q`) covers the hardware-free paths — capture outcomes,
logging, cue order, offline replay, ticket width. The mic, Arduino, and printer are still checked
by hand, and there is no CI, so reviews remain the main quality gate for hardware behaviour.

## Reviewer names

Empty — the three reviewers are the toolkit's own (`code-reviewer`, `perf-reviewer`,
`accessibility-reviewer`, symlinked into `.claude/agents/`). Role discovery picks them
correctly; nothing to disambiguate.
