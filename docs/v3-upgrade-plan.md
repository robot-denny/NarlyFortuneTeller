# Narly V3 Upgrade Plan

## Context

V2 generalized Narly (personas, LED wiring) and got him through a second event on a laptop. V3 moves
him onto a Raspberry Pi 4 Model B (4 GB) and then gives him ways to react to his surroundings.

Before either of those, the runtime needs to change shape. Today the main loop blocks for the entire
30–50 second fortune cycle, the serial port is opened a second time on every coin event, there are
no tests, and the whole pipeline depends on an undocumented Google endpoint. Those are the things
that will bite hardest on a headless device in a booth, so they come first.

The plan is split into phases that are each independently testable and shippable, in the same
spirit as `docs/v2-upgrade-plan.md`. Phases 3 and 4 of the V2 plan are absorbed here: Phase 3
(Pi deployment) becomes V3 Phase 3; V2 Phase 4 (PIR, toggle switches, state-colored LEDs) becomes
V3 Phase 5.

Target hardware for this round: **Raspberry Pi 4 Model B, 4 GB**, with the existing Arduino Uno
kept as the real-time I/O controller. See *Decisions* at the end for why.

---

## Phase 0: Foundations (before any new features)

**Goal:** Make the codebase safe to change. Nothing user-visible changes in this phase.

**Status: NOT STARTED**

### 0a. Single serial owner

`listen_serial_mode()` holds the Arduino port open, then every `on_coin_event()` constructs a
second `LedClient` on the same port. On macOS the second open may fail silently (LEDs go no-op);
on Linux it succeeds but toggles DTR, which resets the Uno, costs ~2 s of reboot, emits a spurious
`READY`, and drops any coin pulses in that window. The `first_coin_ignored` hack is most likely
masking this.

Replace `LedClient` + the inline `serial.Serial` with one `SerialLink` that:

- opens the port once for the process lifetime (`exclusive=True`)
- runs a reader thread that parses lines into typed events (`CoinEvent`, `PirEvent`,
  `SwitchEvent`, `ArduinoLog`) and puts them on a `queue.Queue`
- exposes `send(cmd)` used for `START <mode>` / `STOP`
- reconnects with backoff if the USB device disappears (V2 Phase 3c)
- matches the device by USB VID/PID via `serial.tools.list_ports`, not by a hardcoded path

### 0b. Fake hardware layer

Add `hardware/` with a protocol (or ABC) per device and two implementations each:

| Device | Real | Fake |
|---|---|---|
| Serial / Arduino | `SerialLink` | `FakeSerialLink` — scriptable event list, records commands sent |
| Microphone | `sounddevice` capture | `FakeMicrophone` — returns a WAV fixture or a transcript |
| Printer | `python-escpos` / `lpr` | `FakePrinter` — captures ticket text |
| Audio out | `pygame.mixer` | `FakeAudio` — records cue names |
| STT / LLM | real clients | fakes returning canned text, with injectable failures |

`--mode simulate` becomes "wire up the fakes" rather than a separate code path. Every later phase
must be demonstrable with the fakes before it is tried on hardware.

### 0c. Tests + Feature docs

`docs/narly-behavior.md` is already written as Given/When/Then. Turn it into executable Feature
docs and a `tests/` suite that drives the full coin → print flow through the fakes, including the
failure branches (no speech, STT down, LLM down, printer jam). Use Cantrip's `/retrofit` for this
(see *Tooling*).

### 0d. Housekeeping

- `CLAUDE.md` is stale: says Phase 2 not started, hardcodes a venv path, still describes the owner
  as new to Python. Rewrite it (or move to `AGENTS.md`) to describe the V3 architecture.
- `README.md` still points at the old `sthomsondiagram/NarlyFortuneTeller` clone path and
  `NarlyFortuneTeller/serial_trigger.py` paths.
- Strip the `Received:` / `LED mode set to:` debug echoes from the Arduino sketch, or gate them
  behind the DEBUG switch from Phase 5. The Python side currently has to filter them.
- Rotate the OpenAI key before the device lives unattended in a booth.

### How to verify

```bash
pytest                                   # full flow through fakes, all failure branches
python serial_trigger.py --mode simulate --dry-run
# Coin → print cycle works; no second serial open; no Arduino reset between coins
```

---

## Phase 1: Event loop + state machine

**Goal:** Let Narly do two things at once. Prerequisite for every environmental reaction.

**Status: NOT STARTED**

### 1a. Explicit states

```
IDLE → LISTENING → THINKING → PRINTING → IDLE
  ↘ ERROR (auto-returns to IDLE)
```

This is the same table as V2 Phase 4a, promoted from an LED palette to the Python architecture.
Each state owns its LED command, its audio cue, and its timeout. Transitions are driven by events
from a single queue: serial events from `SerialLink`, timer events, and results from worker
threads.

### 1b. Replace the three `ThreadPoolExecutor` wrappers

Keep the per-step timeouts (they are right), but run the pipeline as a worker that posts
`StepDone` / `StepFailed` events back to the main loop instead of blocking it. Either `asyncio` +
`pyserial-asyncio`, or a thread-per-worker with `queue.Queue` — the second is simpler to reason
about and fine at this scale.

### 1c. Fortune bank fallback

Replace the "Narly drifted off in the currents" slip. Generate 50–100 fortunes per persona offline
(`scripts/build_fortune_bank.py`), store as `personas/<name>/fortune_bank.json`, and fall through
to a random one whenever STT or the LLM fails. The guest still gets a real fortune. This is the
largest reliability gain per line of code in the plan.

### How to verify

```bash
pytest tests/test_state_machine.py
# With fakes: PIR ON during THINKING is observed and does not interrupt the cycle
# With fakes: LLM failure injected → ticket comes from fortune bank, not the error slip
```

---

## Phase 2: Library upgrades (testable on the Mac)

**Goal:** Replace the fragile or macOS-only dependencies. All of this runs and tests on the laptop
before the Pi is involved.

**Status: NOT STARTED**

### 2a. Audio capture + endpointing

Drop `SpeechRecognition` and PyAudio. Use:

- `sounddevice` for capture (PortAudio binding; no PyAudio build pain on the Pi)
- **Silero VAD** to decide when the guest has finished speaking, replacing the hand-tuned
  `energy_threshold = 1100` / fixed `pause_threshold`. Much better in crowd noise.
- Select audio devices **by name**, never by index (indices shuffle on reboot).

### 2b. Speech-to-text: cloud primary, local fallback

- **Primary:** OpenAI `gpt-4o-transcribe` (same key already in `.env`) or Deepgram Nova-3. Both
  are strong on noisy input and return in ~1 s for an 8 s clip. Internet is already a hard
  dependency for the LLM, so this adds no new failure mode.
- **Fallback:** `faster-whisper` `tiny` (int8) or **Moonshine** `tiny` via `moonshine-onnx`.
  On a Pi 4 these transcribe an 8 s clip in roughly 3–5 s with mediocre accuracy in noise —
  acceptable as "the network is down, give me something", not as the daily path. Moonshine is the
  better fallback candidate at this size. Load the model at startup so the failure path is fast.
- Put this behind an `stt/` module with a `Transcriber` protocol so backends are swappable via
  `.env`.

### 2c. LLM

`gpt-4o-mini` is two generations old; the `"You are trained on data up to October 2023"`
string-strip in `ai_client.py` is a symptom of that model and goes away with it.

- Make the existing `AI_PROVIDER` seam real: add an Anthropic branch using
  `claude-haiku-4-5-20251001` ($1 / $5 per MTok, fastest tier) and/or bump OpenAI to a current
  small model. A 30-word fortune costs a fraction of a cent either way.
- `max_tokens=1500` → ~150. Bounds the failure mode where the model ignores the length rule.
- Cache the persona `system_prompt` (prompt caching) — it is identical on every call.

### 2d. Sound playback

Replace `afplay` with `pygame.mixer` in-process: cross-platform, volume control, overlapping cues
without spawning subprocesses, and deterministic "cue finished → open mic" timing.

### 2e. Voice output (optional, enables Phase 4)

**Piper TTS** runs comfortably on a Pi 4 (~1–2 s per sentence, medium voices ~60 MB). OpenAI or
ElevenLabs TTS if a distinctive character voice matters more than latency. Behind a `tts/` module
with the same swappable-backend pattern as STT.

### 2f. `requirements.txt`

Split into `requirements.txt` (runtime) and `requirements-dev.txt` (pytest, fakes). Pin versions.
Remove `SpeechRecognition`, `textwrap3` (stdlib `textwrap` is already what `formatters.py` uses).

### How to verify

```bash
pytest
python serial_trigger.py --mode simulate --dry-run     # real mic + cloud STT on the Mac
STT_BACKEND=local python serial_trigger.py --mode simulate --dry-run   # forces the fallback
```

---

## Phase 3: Raspberry Pi 4 deployment

**Goal:** Narly runs headless on the Pi, survives crashes and power cuts, and is debuggable over SSH.

**Status: NOT STARTED**

Carries forward V2 Phase 3 with these changes:

### 3a. Logging

Replace `print()` with `logging`. On the Pi, log to stdout only and let systemd/journald own it
(`journalctl -u narly -f` is the debug console). Cap journald (`SystemMaxUse=`) or make it
volatile — a Pi that logs to a cheap SD card and gets power-cut after every event will eventually
corrupt the card.

### 3b. Process supervision

**Skip the custom `watchdog_wrapper.py`.** systemd does this with zero code:

```ini
[Service]
Restart=always
RestartSec=5
StartLimitIntervalSec=300
StartLimitBurst=10
```

### 3c. Printing

Prefer `python-escpos` direct USB with a udev rule over CUPS/`lpr` on the Pi — fewer moving parts,
no print queue to get stuck. Keep `lpr` as the fallback it already is.

### 3d. Device stability

- udev rules giving stable names: `/dev/narly-arduino`, `/dev/narly-printer`
- Arduino matched by VID/PID (already done in Phase 0a)
- Audio devices matched by name (already done in Phase 2a)

### 3e. `deploy/`

- `deploy/setup-pi.sh` — apt packages (`portaudio19-dev`, `libsndfile1`, `python3-pygame`
  or SDL deps, `cups` only if using lpr), venv, pip install, `dialout`/`audio`/`lp` groups,
  udev rules
- `deploy/narly.service` — the unit above, `WantedBy=multi-user.target`
- `deploy/journald.conf.d/narly.conf` — size cap
- `deploy/README.md` — flash Pi OS Lite (64-bit), clone, run setup, fill `.env`, connect
  hardware, `systemctl enable --now narly`

### 3f. Pi 4 specifics

- **Power:** the AC-404 mic, Arduino, and printer USB control line all draw from the Pi's USB
  bus. Use the official 3 A supply. Keep the LED strip on its own 5 V PSU as now. A brownout
  shows up as random USB disconnects that look exactly like software bugs.
- **Storage:** A2-rated microSD at minimum; USB SSD boot is better.
- **Audio out:** the Pi 4 still has the 3.5 mm jack (the Pi 5 dropped it), so a small speaker
  works without a dongle. The onboard DAC is noisy — a ~$10 USB audio adapter is worth it if
  Narly's voice matters.
- **Memory budget (4 GB):** cloud pipeline + Silero VAD + one tiny local STT model + pygame +
  Piper fits comfortably. Do not plan on a local LLM on this board.

### How to verify

1. `kill -9` the main process → systemd restarts it within 5 s
2. Unplug the Arduino mid-cycle → logged, reconnects when re-plugged, no crash
3. Pull power during a print → Pi boots clean, service comes up, SD card intact
4. `journalctl -u narly -f` shows the full coin → print cycle
5. Full end-to-end with all hardware on the Pi, both personas

---

## Phase 4: Environmental interactivity

**Goal:** Narly notices and reacts to people before they insert a coin.

**Status: NOT STARTED** — do this only after Phase 3 is stable and you have headroom
measurements from the Pi 4.

### 4a. Sensors → Arduino → events

All sensors live on the Arduino and arrive as serial events, exactly like `COIN`:

- `PIR ON` / `PIR OFF` — HC-SR501 on pin 4 (from V2 Phase 4)
- `DIST <cm>` — optional ultrasonic (HC-SR04) for "someone is close"
- `LIGHT <n>` — optional photoresistor for time-of-day mood
- `SWITCH DEMO|QUIET|DEBUG` — two toggle switches (from V2 Phase 4)

The Arduino also handles the IDLE ↔ SHIMMER LED transition locally on PIR so it stays snappy
even if the Pi is busy.

### 4b. Reactions (Pi side)

Small, cheap behaviours first, driven by the Phase 1 state machine:

- PIR ON while IDLE → SHIMMER + a short Piper line from a persona-specific "lure" list
- Long presence without a coin → a second, cheekier lure
- QUIET mode → suppress all audio; DEBUG mode → log every serial line

### 4c. Wake word (measure first)

**openWakeWord** ("Hey Narly") is a good fit but is always-on inference. Add it only after
measuring CPU headroom on the Pi 4 with VAD + TTS + fallback STT resident. If it fits, it can
trigger a lure or even a coinless "free sample" fortune in DEMO mode.

### How to verify

- With fakes: `PirEvent(on=True)` while IDLE → SHIMMER command sent + lure audio recorded
- With fakes: coin during a lure → lure is cut off, LISTENING starts cleanly
- On Pi: walk up, get shimmer + line; insert coin; full cycle; walk away → IDLE

---

## Phase 5: Arduino sketch rewrite + wiring guide

**Goal:** Land V2 Phase 4b–4e now that the Python side can consume the events.

**Status: NOT STARTED**

- Rewrite `fortune-controller.ino` with the full state palette (IDLE, SHIMMER, LISTEN, THINK,
  PRINT, ERROR), PIR on pin 4, switches on pins 7 & 8 (INPUT_PULLUP)
- Replace `String`-based command parsing with a small fixed buffer (String churn on the Uno
  fragments the heap over a long event day)
- `arduino/README.md` — parts list, per-component isolation tests, full pin table
- If pins or animation headroom run out, an ESP32 or RP2040 board is a drop-in on the same serial
  protocol

---

## Tooling: Cantrip + agentic workflow

`fortune-service` has no `.claude/` directory. Install the Cantrip core spellbook and use this
project as its first non-.NET, non-CMS consumer:

```bash
DISABLE_TELEMETRY=1 npx skills add robot-denny/cantrip/skills/core --all
mkdir -p .claude/agents && for f in .claude/skills/reviewer-discipline/agents/*.md; do \
  n=$(basename "$f"); ln -s "../skills/reviewer-discipline/agents/$n" ".claude/agents/$n"; done
```

Then:

- `/setup` after Phase 0d so it reads accurate repo context
- `/retrofit` to turn `docs/narly-behavior.md` into Feature docs + tests (Phase 0c)
- `/spec` → `/plan` → `/implement-step` for each phase above
- `/code-review` on every increment; the fakes make it runnable

**Stack pack to author:** Cantrip has no Python or hardware pack. A `python-hardware` (or
`raspberry-pi`) pack would carry starter facts (Pi 5 GPIO changes, ALSA device selection,
pyserial DTR-reset behaviour, systemd conventions, `python-escpos` udev permissions) and reviewer
rules that matter for a booth device: every external call has a timeout, every hardware
dependency degrades gracefully, nothing blocks the event loop, no hardcoded device paths. Generic
enough to publish.

---

## Decisions

**Keep the Arduino as the real-time controller; the Pi replaces only the laptop.**
The Pi 5 changed its GPIO controller and broke `rpi_ws281x`; Adafruit's PIO/SPI alternatives
work but would move LED timing and coin debounce into a userspace Python process that is also
doing audio and network I/O. The existing coprocessor split is the right architecture. It also
means none of the Pi 5 NeoPixel churn applies to this project at all.

**Cloud-first pipeline, local fallback.** On a 4 GB Pi 4, local STT is a safety net and a local
LLM is out of scope. Accuracy in a noisy tent comes from cloud STT; resilience comes from the
fortune bank and the tiny local model.

**Pi 4 now; Pi 5 only if measurements say so.** The Pi 4 covers Phases 0–3 comfortably. The
only place a Pi 5 (8 GB) would matter is Phase 4c if wake word + VAD + TTS + local STT all need
to be resident. Decide that with numbers from the Pi 4, not up front. Phases 0–2 make the runtime
board-agnostic so a swap is a reflash and a `git clone`.

**systemd over a hand-rolled watchdog.** Less code, same behaviour, better logs.

**Suggested order:** 0 → 1 → 2 → 3 → 4 → 5. Phases 0–2 are all verifiable on the Mac; the Pi
is not needed until Phase 3.
