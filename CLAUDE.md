# Narly Fortune Teller — AI Context

## What this is
A coin-operated AI fortune teller for festivals. Physical pipeline: Coin → Mic → Speech-to-Text → OpenAI → Thermal Printer. Arduino handles coin detection and LEDs; Python handles everything else.

## Key entry points
- `serial_trigger.py` — main orchestrator. Run with `--mode simulate --dry-run` for testing.
- `app.py` — standalone test, skips coin and mic.
- Both accept `--persona <name>` and `--list-personas`.

## Architecture
- `config_loader.py` — `load_config(persona)` reads `personas/<name>/content.json` and loads its `prompts.md`. Paths resolve relative to the file, not cwd.
- `ai_client.py` — call `init_ai(persona)` at startup, then `get_ai_response(question)`.
- `formatters.py` — `render_ticket(message, config)` formats for 32-char thermal printer.
- `led_client.py` — sends `START <mode>` / `STOP` to Arduino over serial. Degrades gracefully if Arduino not connected.

## Personas
Live in `personas/<name>/content.json` + `prompts.md`. Current personas: `default` (general), `music`, `umbraco-2025` (Umbraco festival). Default persona is always the fallback.

## Arduino serial protocol
- Arduino → Python: `COIN X` (coin inserted)
- Python → Arduino: `START <mode>`, `STOP`
- Baud: 115200. The port is **not stable** — it depends on which USB-C port on the laptop the
  Arduino is plugged into (`143101` and `143301` are both real values seen on this machine), and
  it varies by machine besides. Do not treat any literal as correct.
  - `serial_trigger.py` falls back to `find_port()`, which scans for an Arduino-like device.
  - `--port` overrides both. Prefer it over editing the `PORT` constant when the value changes.

## V2 upgrade status
`ROADMAP.md` is the live queue and takes precedence; `docs/v2-upgrade-plan.md` holds the detailed
wiring and verification steps. Current status:
- Phase 1 (personas + code reorg): **COMPLETE** (2026-02-20)
- Phase 2 (Arduino LEDs): **COMPLETE** (2026-02-28) — scope was trimmed to LED wiring for a
  same-day event; the PIR sensor and toggle switches it originally included became Phase 4.
- Phase 3 (logging, watchdog, serial recovery, Raspberry Pi deployment): **NEXT**
- Phase 4 (PIR sensor, toggle switch, state machine): **LATER**

## User notes
- Owner is new to Arduino, Raspberry Pi, and Python — explain clearly.
- Phased approach: complete and verify one phase before starting the next.
- Python venv: `/Users/dkardys/Sites/fortune-service/.venv/`
