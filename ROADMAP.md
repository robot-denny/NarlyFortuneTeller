# Roadmap

The queue. Reordered on 2026-09-22 from `_work/shipped/capture-measure-and-fix/discovery.md`, which
reconciled `docs/v3-upgrade-plan.md` (the September audit) against two events of field
experience. `docs/v2-upgrade-plan.md` and the V3 plan remain the detailed references; the V2
and V3 item IDs are kept below so those documents stay navigable.

Priority order: hear attendees reliably → Pi for the next event → refine → sensors.
The aim is **visible improvement, measured rather than felt**, from one run to the next. The
long-run mark is ≥ 60% of attendees heard correctly in a room with background conversation, but
hitting it is not the goal of any one increment.

## Now

**Increment 2 — Live baseline.** Tools shipped (PR #2): clip saving, live and replay scoring,
the runbook `docs/capture-baseline.md`, and the 60-question script. Full hardware run on the Mac
confirmed 2026-09-28 (coin → LEDs → mic → printer, PR #3). Spec: `_work/live-baseline/spec.md`.

- Measuring session done 2026-09-28, scaled down to what the owner could run alone: 20
  questions, ids 1–10 quiet and 21–30 with crowd noise, on the laptop with the AM8. **60% heard
  correctly** (quiet 70%, conversation 50%); replay identical. All eight misses were clipped
  first or last words, not mishearing. Results in `docs/capture-baseline.md`.
- Wake level held while listening (`dynamic_energy_threshold = False` after calibration),
  measured the same evening with the same 20: **95%** (quiet 100%, conversation 90%), one end
  cut-off left. Results in `docs/capture-baseline.md`.

## Next

**Increment 3 — Pi port.** Critical path to the next event.

- Persistent, size-capped journald — *not* volatile; post-event review needs the logs to
  survive a power cut. V3 `3a`.
- systemd unit with `Restart=always`. Replaces the V2 `3b` watchdog. V3 `3b`.
- Single serial owner — one port open for the process lifetime, reader thread, reconnect with
  backoff. Fixes the Uno DTR reset on every coin event (a day-one Linux defect) and absorbs
  V2 `3c`, including `led_client.py`'s stale `tty.` default. V3 `0a`.
- Stable device names by VID/PID and udev; audio devices by name. V3 `3d`.
- `deploy/` — setup script, unit file, journald drop-in, README. V2 `3f` / V3 `3e`.
- Power budget: official 3 A supply; mic, Arduino, and printer share the USB bus. V3 `3f`.
- Re-run Increment 2's 20-question session on the Pi, live, with the same setup, and replay the
  laptop clips there. The laptop score is the comparison. If the Pi scores worse and can't be
  fixed easily before an event, that event runs on the laptop.

**Increment 4 — Endpointing and recognition.** Measured against the Increment 2 fixtures.

- Silero VAD replaces energy-based endpointing, which cannot find a pause in noise. V3 `2a`.
- Cloud STT (gpt-4o-transcribe or Deepgram) replacing the free Google endpoint, with a small
  local fallback. Drops `SpeechRecognition`. V3 `2b`.

## Later

- Fortune bank fallback — only after logging exists, since it hides the one failure tell the
  operator has today. V3 `1c`.
- TTS readiness prompt, if the timed cues from Increment 1 prove insufficient. V3 `2e`.
- Event loop and explicit state machine. Unblocks the sensor work. V3 `1a`–`1b`.
- LLM refresh — current model, `max_tokens` 1500 → ~150, prompt caching. V3 `2c`.
- Housekeeping: README paths, Arduino debug echoes, dead `textwrap3`, key rotation. V3 `0d`.
- **Sensors and sketch rewrite — last.** PIR, toggle switches, full LED palette, wiring guide.
  V2 `4a`–`4e` / V3 `4`–`5`.

## Dropped

- **Custom watchdog wrapper** (V2 `3b`). The next event runs on the Pi; systemd restarts the
  process with zero code. Not worth writing to throw away.

## Recently shipped

- **Increment 1 — Measure and fix attendee capture** (2026-09-28,
  `_work/shipped/capture-measure-and-fix/`). Every fortune logs what was heard, or which of five
  failures struck, and whether the question was substituted (V2 `3a`). A full fortune runs with
  no hardware and no API spend, from typed text or a clip (scoped-down V3 `0b`); a colleague
  confirmed it from `docs/testing.md` alone. Listening starts the instant the chime ends; the
  threshold is the library default, adapting. Cues play in-process via pygame (V2 `3d` / V3
  `2d`), and `pyaudio` is in `requirements.txt` (V2 `3e`). First pytest suite. Behavior is in
  `_features/audio-capture.md`.
- **Phase 2 — LED wiring + first boot** (2026-02-28). WS2812B strip wired to pin 6 via a 330Ω
  resistor, shared ground, `NUM_LEDS` 60 → 180, serial port corrected to `/dev/cu.usbmodem143301`.
  Verified in both dry-run and hardware mode. Scope was deliberately trimmed to LED wiring for a
  same-day event; the rest became Phase 4.
- **Phase 1 — Personas + code organisation** (2026-02-20). `personas/`, `sfx/`, `arduino/`
  directories; `load_config(persona)` / `list_personas()`; `--persona` and `--list-personas`
  flags; file-relative path resolution; `default` persona created, `umbraco-2025` preserved.
