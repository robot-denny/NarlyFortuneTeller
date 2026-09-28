# Narly V2 Upgrade Plan

## Context

Narly V1 was built for the Umbraco 2025 US Festival in Chicago. The persona, wiring, and deployment are all tailored to that single event (Umbraco references, laptop-based, single persona). For V2, we need to generalize Narly so he can be deployed at any event, add richer LED feedback, improve hardware resilience, and migrate from a laptop to a Raspberry Pi 4.

The work is split into 3 phases. Each phase is independently testable and shippable.

---

## Phase 1: Personas + Code Organization -- COMPLETED

**Goal:** Support multiple personas selectable at startup; reorganize the project.

**Status: DONE** (completed 2026-02-20)

### What was done

- Reorganized file layout: `personas/`, `sfx/`, `arduino/` directories created
- `config_loader.py` rewritten with `load_config(persona)` and `list_personas()`; paths resolve relative to script location
- `ai_client.py` updated with `init_ai(persona)` for startup caching
- `formatters.py` updated — `render_ticket()` accepts a `config` parameter
- `serial_trigger.py` updated — `--persona` and `--list-personas` flags; config loaded once at startup; SFX paths resolve from `_BASE_DIR / "sfx"`
- `app.py` updated — same persona flags; cleaned up commented-out code
- Default persona created (`personas/default/`) — general sea-mystic Narly, no Umbraco/Chicago
- Umbraco persona preserved (`personas/umbraco-2025/`)
- Arduino sketch (`led-test.ino`) copied into `arduino/fortune-controller/fortune-controller.ino`
- Root `content.json` and `prompts.md` deleted (replaced by persona dirs)
- `.gitignore` updated (added `*.wav`, `.DS_Store`)
- Unused Python files removed: `mic_trigger.py`, `serial_trigger-test.py`, `serial_trigger.py.backup`, `test_openai.py`, `printer_escpos_test.py`

### How to verify

```bash
python serial_trigger.py --list-personas
# Should print: default, umbraco-2025

python serial_trigger.py --mode simulate --dry-run
# Uses default persona

python serial_trigger.py --mode simulate --dry-run --persona umbraco-2025
# Uses Umbraco persona

python app.py --persona default --dry-run
# Quick standalone test
```

---

## Phase 2: LED Wiring + First Boot (event-day scope)

**Goal:** Get LED animations working with the existing sketch. No PIR, no toggle switch.

**Status: COMPLETED** (2026-02-28)

> **Scope note (2026-02-28):** Phase 2 is trimmed to LED wiring only for an event happening today. PIR sensor, toggle switch, state machine expansion, and wiring documentation are deferred to Phase 4.

### What was done

- Wired WS2812B strip: red → PSU +5V rail, white → PSU GND rail, teal (Din) → 330Ω resistor → Arduino pin 6
- Shared ground: breadboard negative rail → Arduino GND (reused existing coin acceptor ground wire)
- 470µF capacitor already on breadboard across power rails — confirmed correct polarity, kept in place
- Updated `NUM_LEDS` from 60 → 180 (3m strip × 60 LEDs/m)
- Fixed hardcoded port in `serial_trigger.py`: `/dev/cu.usbmodem143101` → `/dev/cu.usbmodem143301`
- Verified full flow: GLOW animates on coin event, resets after fortune cycle
- Tested in both `--dry-run` and hardware (real printer) mode

### 2a. Wire LEDs

Nothing is wired yet. Steps (guided with photos):

1. WS2812B data wire → Arduino **pin 6** (add a 300–500Ω resistor inline on the data line if available)
2. WS2812B 5V + GND → Aclorol 5V 20A PSU output rails
3. **Shared ground:** run a wire from PSU GND → Arduino GND ⚠️ critical — LEDs won't respond reliably without this
4. Arduino powered separately via USB cable to laptop

### 2b. Verify sketch constants and upload

Open `arduino/fortune-controller/fortune-controller.ino` in Arduino IDE. Confirm:
- `NUM_LEDS = 60`
- `LED_PIN = 6`

Upload to Arduino Uno.

### 2c. Smoke test

```bash
python serial_trigger.py --mode simulate --dry-run
```

Expected: LEDs animate on simulated coin trigger, stop after fortune prints to terminal.

If the serial port isn't auto-detected, pass it manually:
```bash
python serial_trigger.py --mode simulate --dry-run --port /dev/cu.usbmodem<XXXX>
```

### How to verify

```bash
python serial_trigger.py --mode simulate --dry-run
# LEDs should GLOW purple on coin event, off after fortune cycle

python serial_trigger.py --mode simulate
# Same with real printer
```

### Known-good coin acceptor wiring (reference, do not change)

- HX-916 red wire → barrel jack adapter (+)
- HX-916 black wire → barrel jack adapter (−)
- Black jumper → barrel jack adapter (−) → breadboard power rail (−) at row 47
- Black jumper → breadboard power rail (−) → Arduino GND (shared ground)
- HX-916 white wire (signal) → breadboard F47
- 110 ohm resistor → G47 to G49 (current-limiting)
- Jumper → F49 → Arduino pin 2 (DIP2)
- Barrel jack adapter → 12V CyberPower wall plug

---

## Phase 3: Raspberry Pi Deployment (post-event)

**Goal:** Auto-restart on crash, hardware failure resilience, migrate to Raspberry Pi 4.

**Status: NOT STARTED**

### 3a. Add proper logging (`logger.py`)

Replace all `print()` calls with `logging`. Write to both stdout and a rotating log file. Critical for debugging on a headless Pi.

### 3b. Watchdog wrapper (`watchdog_wrapper.py`)

A simple script that runs `serial_trigger.py` as a subprocess and restarts it on crash. Caps at 10 restarts, resets counter after 5 minutes of stability.

### 3c. Serial port recovery

Wrap the serial listener in a reconnection loop — if the Arduino USB disconnects, log the error, wait 5 seconds, re-detect the port, and reconnect.

**Fix `led_client.py`'s default port as part of this.** `LedClient.__init__` currently defaults to
`port="/dev/tty.usbmodem143101"`, which is wrong twice over: it is a stale port value, and it is a
`tty.` device where the rest of the code uses `cu.` (on macOS, opening `tty.*` blocks waiting for
carrier detect; `cu.*` does not).

It is harmless today only because nothing reaches it — both call sites pass the port explicitly as
`LedClient(LED_PORT, BAUD)`, and there are no bare `LedClient()` calls. Reconnection is what makes
it dangerous: a recovery path that rebuilds a `LedClient` without threading the port through will
silently fall back to a hardcoded `tty.` device instead of the one just re-detected, and the most
likely symptom is a hang rather than an error.

- Change the default to `port=None`.
- When `port` is `None`, resolve it via `find_port()` rather than a literal.
- Keep the re-detected port as the single source of truth through the reconnect path — the LED
  client and the coin listener share one board, so they must not drift apart after a reconnect.

Remember that the port name is not stable: it follows which USB-C jack the Arduino is plugged into
(`143101` and `143301` are both real on the dev laptop). Re-detect; never re-hardcode.

### 3d. Cross-platform audio

Replace macOS-only `afplay` with a `play_sound()` function that detects the platform:
- macOS: `afplay`
- Linux/Pi: `mpg123` (mp3) or `aplay` (wav)

### 3e. Fix `requirements.txt`

Add missing dependencies: `SpeechRecognition`, `pyaudio` (needed on Pi for mic access).

### 3f. Raspberry Pi deployment

- `deploy/setup-pi.sh` — installs system packages (`portaudio19-dev`, `mpg123`, `cups`), creates venv, installs Python deps, sets up user permissions (`dialout`, `audio`, `lp` groups)
- `deploy/narly-fortune.service` — systemd unit that runs the watchdog wrapper, auto-starts on boot, logs to journald
- `deploy/README.md` — step-by-step guide: flash Pi OS, clone repo, run setup script, configure .env, connect hardware, test, enable service

### How to verify
1. Kill the main process — watchdog should restart it within 5 seconds
2. Unplug Arduino USB mid-operation — app should log error and reconnect when re-plugged
   - Re-plug into the *other* USB-C port so the device name changes; it should still reconnect
   - Confirm the LEDs still respond after reconnect, not just the coin listener
3. On Pi: `sudo systemctl start narly-fortune` then `journalctl -u narly-fortune -f` to watch logs
4. Reboot Pi — service should auto-start
5. Full end-to-end on Pi with all hardware

---

## Phase 4: PIR Sensor, Toggle Switch + Hardening (future)

**Goal:** Add presence detection, state-colored LED animations, physical mode switch, and full wiring documentation.

**Status: NOT STARTED**

> Deferred from original Phase 2 scope. Do this after Phase 3 (Pi deployment) is stable.

### 4a. Define state machine + serial protocol

| State | LED Command | Animation | Color (HSV) |
|---|---|---|---|
| Idle (no one nearby) | `START IDLE` | Very dim breathe | Ocean blue H=160, V=10-40 |
| Presence detected | `START SHIMMER` | Gentle twinkle | Ocean blue H=160, V=60-180 |
| Listening | `START LISTEN` | Warm solid glow | Amber H=32, V=200 |
| Thinking | `START THINK` | Random sparkle | Purple H=180-220 |
| Printing | `START PRINT` | Chase/sweep | Cyan H=128, V=255 |
| Error | `START ERROR` | 3 red flashes, auto-return | Red H=0 |

New Arduino → Python messages:
- `PIR ON` / `PIR OFF` — presence sensor state change
- `SWITCH DEMO` / `SWITCH QUIET` / `SWITCH DEBUG` — toggle switch changed

### 4b. Rewrite Arduino sketch

Keep coin detection (pin 2) and LEDs (pin 6). Add:
- PIR sensor on pin 4 (HC-SR501)
- Two toggle switches on pins 7 & 8 (INPUT_PULLUP, active low)
  - Both off = DEMO, A on = QUIET, B on = DEBUG
- LED animation functions for all 7 states
- PIR auto-transitions IDLE ↔ SHIMMER locally

### 4c. Update `led_client.py`

Add convenience methods: `idle()`, `shimmer()`, `listen()`, `think()`, `printing()`, `error()`. Validate mode names against a whitelist.

### 4d. Update `serial_trigger.py`

- Parse `PIR ON/OFF` and `SWITCH` messages in the serial loop
- Track `operating_mode` from switch messages
- In QUIET mode: skip all `afplay()` calls
- In DEBUG mode: print all serial traffic
- Update `on_coin_event()` to use state-based LED commands

### 4e. Wiring guide (`arduino/README.md`)

Complete beginner-friendly reference: parts list, coin acceptor, LEDs, PIR, toggle switches, full pin table, per-component isolation tests.

> **Started 2026-09-23.** `arduino/README.md` now documents the current build (pin table, rail map, PSU terminals, coin acceptor, LED strip) and the recommended change to take LED power off the breadboard. PIR, toggle switches, parts list, and isolation tests are still to be added when 4a–4d land.
