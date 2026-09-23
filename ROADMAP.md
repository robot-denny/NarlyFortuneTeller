# Roadmap

The queue. Reordered on 2026-09-22 from `_work/capture-measure-and-fix/discovery.md`, which
reconciled `docs/v3-upgrade-plan.md` (the September audit) against two events of field
experience. `docs/v2-upgrade-plan.md` and the V3 plan remain the detailed references; the V2
and V3 item IDs are kept below so those documents stay navigable.

Priority order: hear attendees reliably → Pi for the next event → refine → sensors.
Target for the first two: **≥ 60% of attendees heard correctly** in a room with background
conversation, measured rather than felt, on the Pi.

## Now

**Increment 1 — `capture-measure-and-fix`.** Everything software-only that fits the current
hardware gap (mic days away, Arduino dismantled). Discovery done; spec next.

- Log the five capture failures distinctly and what was heard — the instrument that makes 60%
  checkable. Absorbs V2 `3a`.
- Fake mic replaying WAV fixtures, plus STT and LLM fakes, so a full run needs no hardware and
  no API spend; lets others test remotely. Scoped-down V3 `0b`.
- Cue and `listen()` start in the same instant — closes the ~2.8s dead window.
- `energy_threshold` to the library default with adaptation re-enabled; never tested below 800.
- Cross-platform playback replacing `afplay`, which dies silently on Linux. V2 `3d` / V3 `2d`.

## Next

**Increment 2 — Live baseline.** When the directional mic arrives and the Arduino is rewired.
New mic on a stand; record fixture clips (quiet room, conversation behind, leaning in); first
measured success rate against the log from Increment 1.

**Increment 3 — Pi port.** Critical path to the next event.

- Persistent, size-capped journald — *not* volatile; post-event review needs the logs to
  survive a power cut. V3 `3a`.
- systemd unit with `Restart=always`. Replaces the V2 `3b` watchdog. V3 `3b`.
- Single serial owner — one port open for the process lifetime, reader thread, reconnect with
  backoff. Fixes the Uno DTR reset on every coin event (a day-one Linux defect) and absorbs
  V2 `3c`, including `led_client.py`'s stale `tty.` default. V3 `0a`.
- Stable device names by VID/PID and udev; audio devices by name. V3 `3d`.
- `pyaudio` in `requirements.txt` while `SpeechRecognition` is still the capture path. V2 `3e`.
- `deploy/` — setup script, unit file, journald drop-in, README. V2 `3f` / V3 `3e`.
- Power budget: official 3 A supply; mic, Arduino, and printer share the USB bus. V3 `3f`.

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

- **Phase 2 — LED wiring + first boot** (2026-02-28). WS2812B strip wired to pin 6 via a 330Ω
  resistor, shared ground, `NUM_LEDS` 60 → 180, serial port corrected to `/dev/cu.usbmodem143301`.
  Verified in both dry-run and hardware mode. Scope was deliberately trimmed to LED wiring for a
  same-day event; the rest became Phase 4.
- **Phase 1 — Personas + code organisation** (2026-02-20). `personas/`, `sfx/`, `arduino/`
  directories; `load_config(persona)` / `list_personas()`; `--persona` and `--list-personas`
  flags; file-relative path resolution; `default` persona created, `umbraco-2025` preserved.
