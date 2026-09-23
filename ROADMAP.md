# Roadmap

Seeded from `docs/v2-upgrade-plan.md`, which remains the detailed reference. This file is the
queue; the plan doc holds the wiring steps and verification detail.

## Now

Nothing in flight.

## Next

**Phase 3 — Raspberry Pi deployment.** Make Narly survive an unattended festival day and move
it off the laptop.

- `3a` Proper logging (`logger.py`) — replace `print()` with `logging`, stdout + rotating file
- `3b` Watchdog wrapper — restart on crash, cap 10 restarts, reset after 5 min stable
- `3c` Serial port recovery — reconnect loop when the Arduino USB drops; also fixes `led_client.py`'s stale `tty.` default port
- `3d` Cross-platform audio — replace macOS-only `afplay` with a platform-detecting `play_sound()`
- `3e` Fix `requirements.txt` — add `pyaudio` (needed on the Pi for mic access)
- `3f` Pi deployment — `deploy/setup-pi.sh`, `deploy/narly-fortune.service`, `deploy/README.md`

## Later

**Phase 4 — PIR sensor, toggle switch, and hardening.** Deferred from the original Phase 2 when
an event deadline trimmed it to LED wiring only. Do this after Phase 3 is stable.

- `4a` State machine + serial protocol — 7 LED states, `PIR ON/OFF` and `SWITCH` messages
- `4b` Rewrite the Arduino sketch — PIR on pin 4, two toggle switches on pins 7 & 8
- `4c` `led_client.py` convenience methods + mode whitelist
- `4d` `serial_trigger.py` — parse PIR/SWITCH, track operating mode, QUIET and DEBUG behaviour
- `4e` Wiring guide (`arduino/README.md`) — beginner-friendly parts list and pin table

## Recently shipped

- **Phase 2 — LED wiring + first boot** (2026-02-28). WS2812B strip wired to pin 6 via a 330Ω
  resistor, shared ground, `NUM_LEDS` 60 → 180, serial port corrected to `/dev/cu.usbmodem143301`.
  Verified in both dry-run and hardware mode. Scope was deliberately trimmed to LED wiring for a
  same-day event; the rest became Phase 4.
- **Phase 1 — Personas + code organisation** (2026-02-20). `personas/`, `sfx/`, `arduino/`
  directories; `load_config(persona)` / `list_personas()`; `--persona` and `--list-personas`
  flags; file-relative path resolution; `default` persona created, `umbraco-2025` preserved.
