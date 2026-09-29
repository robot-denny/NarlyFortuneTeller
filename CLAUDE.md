# Narly Fortune Teller — AI Context

## What this is
A coin-operated AI fortune teller for festivals. Physical pipeline: Coin → Mic → Speech-to-Text → OpenAI → Thermal Printer. Arduino handles coin detection and LEDs; Python handles everything else.

## Key entry points
- `serial_trigger.py` — main orchestrator. Run with `--mode simulate --dry-run` for testing.
  Add `--offline` for no network and no API spend, with `--question "..."` or `--clip file.wav` in
  place of the mic. `--log-file <path>` also writes a rotating log.
- `app.py` — standalone test, skips coin and mic.
- Both accept `--persona <name>` and `--list-personas`.
- `docs/testing.md` — the tester runbook: setup (Python 3.10–3.12, PortAudio), tests, offline
  fortunes, and counting outcomes in the log.

## Architecture
- `config_loader.py` — `load_config(persona)` reads `personas/<name>/content.json` and loads its `prompts.md`. Paths resolve relative to the file, not cwd.
- `ai_client.py` — call `init_ai(persona)` at startup, then `get_ai_response(question)`.
- `formatters.py` — `render_ticket(message, config)` formats for 32-char thermal printer.
- `led_client.py` — sends `START <mode>` / `STOP` to Arduino over serial. Degrades gracefully if Arduino not connected.
- `capture_client.py` — `capture_question(get_audio, transcribe, on_ready)` returns one of six
  outcomes (`heard`, `no_speech`, `not_understood`, `recognizer_error`, `mic_error`, `overrun`).
  `serial_trigger.py` logs each as one `capture outcome=...` line plus a `question source=...` line.
- `audio_out.py` — `PygameAudioOut` plays the cues in-process (macOS and Linux); degrades if no
  sound device.
- `logger.py` — `configure_logging()` / `get_logger()`: timestamped, levelled lines to stdout.
- `fakes.py` — stand-ins for the recognizer, the fortune call, and the speaker. `--offline` and
  the tests use them.
- Providers (mic, recognizer, fortune, speaker) are set once by `main()` through
  `configure_providers(...)`. Tests set them the same way.

## Tests
- `.venv/bin/python -m pytest -q`. Install with `requirements-dev.txt`, which stays off the Pi.
  Tests live in `tests/test_<module>.py`.
- They cover the hardware-free paths only. The mic, Arduino, and printer are checked by hand.

## Personas
Live in `personas/<name>/content.json` + `prompts.md`. Current personas: `default` (general), `music`, `umbraco-2025` (Umbraco festival), `umbraco-2026` (Umbraco 2026 US Festival, Chicago). Default persona is always the fallback.

## Arduino serial protocol
- Arduino → Python: `COIN X` (coin inserted)
- Python → Arduino: `START <mode>`, `STOP`
- Baud: 115200. The port is **not stable** — it depends on which USB-C port on the laptop the
  Arduino is plugged into (`143101` and `143301` are both real values seen on this machine), and
  it varies by machine besides. Do not treat any literal as correct.
  - `serial_trigger.py` falls back to `find_port()`, which scans for an Arduino-like device.
  - `--port` overrides both. Prefer it over editing the `PORT` constant when the value changes.

## Upgrade status
`ROADMAP.md` is the live queue and takes precedence. `docs/v2-upgrade-plan.md` and
`docs/v3-upgrade-plan.md` hold the detailed steps; their item IDs are kept in the roadmap.
Current behavior of capture is in `_features/audio-capture.md`. Shipped increments are archived
under `_work/shipped/`.
- Phase 1 (personas + code reorg): **COMPLETE** (2026-02-20)
- Phase 2 (Arduino LEDs): **COMPLETE** (2026-02-28) — trimmed to LED wiring for a same-day
  event; the PIR sensor and toggle switches became Phase 4.
- Increment 1, measure and fix attendee capture: **COMPLETE** (2026-09-28). Logging (V2 `3a`),
  offline testing, listening on the chime's end, default threshold, pygame cues. The V2 `3b`
  watchdog was dropped: systemd replaces it on the Pi.
- Increment 2, live baseline: **NOW**. The Fifine AM8 (the chosen mic; the Samson Q20 is out of
  scope) on a stand, a replay set of clips, the first measured success rate. Deliberately lean.
- Increment 3, Pi port (V2 `3c`–`3f`): **NEXT**. Increment 4, endpointing and recognition, follows.
- Sensors, toggle switch, state machine (was Phase 4): **LATER**.

## User notes
- Owner is new to Arduino, Raspberry Pi, and Python — explain clearly.
- Phased approach: complete and verify one phase before starting the next.
- Python venv: `/Users/dkardys/Sites/fortune-service/.venv/`
- Interactive runs (pressing Enter for a coin, listening for cues, speaking to the mic) must be
  run by the owner in a plain terminal, never through Claude. Without a keyboard attached, Narly
  quits at the second prompt and cuts off the thinking cue.
