# Plan: Raspberry Pi Port With Laptop Fallback

**Spec**: `_work/pi-port/spec.md`
**Branch**: `feature/pi-port`
**Work type**: fix-infra
**Feature doc**: none

## Context

Narly moves from the laptop to a Raspberry Pi 4 (4 GB) inside the cabinet. He starts on power-up,
restarts himself, and keeps a log that survives a power cut. The laptop stays a working fallback
at every point. The Pi goes to the event only if it scores at least 17 of 20 on the Increment 2
session. This is Increment 3 in `ROADMAP.md`. It covers V2 `3c`–`3f` and V3 `0a` / `3a`–`3f`, cut
down by the spec's lean-path decisions. The unit of work is the V2 grouping "Pi deployment", all
verified on the Pi. Code changes that must also hold on the laptop come first, each with pytest
cover, because the test suite is the automated half of the fallback guarantee. The Pi-only kit
lives under `deploy/`, and the owner runs the Pi and booth checks by hand.

Built on: `logger.py` already logs to stdout, which is what journald collects. `audio_out.py`
already plays cues through pygame, which works on Linux. `print_client.py` already prints over
direct USB. `configure_providers` and `fakes.py` let the coin flow run in tests without hardware.

---

## Key Decisions

- **The known-good version is a tag, `laptop-known-good-2026-09-28`, on `c8bb755`.** That's the
  `main` head that scored 95%. It's an annotated tag pushed to `origin`, so going back is one
  `git switch --detach` on any machine. `main` itself isn't touched until the laptop proof in
  Step 9 passes.
- **The laptop's working copy is this repo.** "Run on the laptop" means `git switch main` (or the
  tag) in `/Users/dkardys/Sites/fortune-service`. **No new Python dependencies** are added, so the
  laptop's `.venv` works on the tag, on `main`, and on this branch. Everything the Pi needs extra
  comes from `apt` in the setup script.
- **`--port` has a real default of "detect".** Today `--port` defaults to the `PORT` literal, so
  `args.port or find_port()` never calls `find_port()`. Detection is dead code, and on the Pi,
  hardware mode would open a Mac path and crash. The default becomes `None`, and the `PORT`
  literal is removed. `--port` still overrides. On the laptop this swaps a literal that's right
  only in one USB-C jack for detection that works in both (see memory
  `arduino-serial-port-varies`).
- **The Arduino is detected by USB identity as well as by name.** The laptop's Uno reports VID
  `0x2341`, PID `0x0043`, device `/dev/cu.usbmodem1101`, and description `IOUSBHostDevice`, as
  listed on 2026-09-28. The current "Arduino in description" test therefore misses it on the Mac,
  and only `usbmodem` matches. On the Pi the same board is `/dev/ttyACM0`. `find_port()` accepts
  VIDs `0x2341` and `0x2A03` (Arduino) and keeps the `usbmodem` rule. CH340 clones (`0x1A86`)
  are left out: that chip is on plenty of other USB-serial adapters, and the owner's Uno is genuine.
- **With no Arduino, hardware mode waits instead of exiting.** It logs once, retries every few
  seconds, and logs again about every minute. If it exited, the Pi's service would restart it
  until it hit the retry limit (10 in 300 s) and then give up for good. That's the wrong outcome
  for "the Arduino is plugged in a minute late". Simulate mode doesn't wait. It runs without LEDs,
  as offline testers need.
- **One Arduino connection per run (the lean V3 `0a`).** `listen_serial_mode` opens the port once
  with `exclusive=True`. A module-level `_led` in `serial_trigger.py` wraps that same open port, so
  `on_coin_event` stops constructing `LedClient` per coin. Simulate mode opens one `LedClient` at
  start and keeps it. No reader thread, no event queue, no `SerialLink`. The coin read and the LED
  writes happen on the same thread, one after the other, so nothing can race.
- **`LedClient`'s default port becomes `None`, meaning no LEDs** (V2 `3c`'s fix for the stale
  `tty.` default). It gains a way to wrap an already-open port, and in that mode `close()` leaves
  the port open for its owner.
- **An unplugged Arduino ends the run with exit code 1 and one clear log line.** On the Pi,
  systemd restarts Narly, which waits for the Arduino (see above). On the laptop, the operator
  restarts him by hand, as today. No in-process reconnect.
- **Startup refuses to run without `OPENAI_API_KEY` unless `--offline` is set.** A missing `.env`
  otherwise prints "Narly drifted off" on every coin and never says why, since `ai_client` builds
  the client per call. The check runs in `main()` and exits 1 with a message naming `.env`. On
  the Pi, systemd's retry limit then stops the loop, which is the spec's "persistent fault".
- **The mic is chosen by name.** `pick_mic_index(names, wanted)` is a pure function. It finds the
  first device whose name contains `wanted` (case-insensitive), otherwise returns `None`, which
  means the system default, as today. `wanted` comes from the optional `.env` value `MIC_NAME`,
  default `fifine`, added to `.env.example`. (Planned as `AM8`; changed in Step 5 because macOS
  lists the mic as `fifine Microphone`, with no model number.) `main()` logs which mic was chosen. The exact name the
  AM8 reports on the Pi isn't known yet. Step 8 records it.
- **Pi OS: Raspberry Pi OS Lite (64-bit), Legacy (Bookworm), with Python 3.11.** The current Pi
  OS ships Python 3.13, and `SpeechRecognition` needs `audioop`, which was removed in 3.13 (see
  `docs/testing.md`: 3.10–3.12 only). Bookworm is the Imager's "Legacy" entry. Choosing it avoids
  any Python install step.
- **The Pi needs `flac` from apt.** `SpeechRecognition` sends Google FLAC audio, and it bundles a
  `flac` program only for x86. On an arm64 Pi it needs the system one, or every capture fails as
  `recognizer_error`. It isn't needed on the Mac.
- **Sound out: the Pi's headphone jack, by AUX cable to the Bose.** `deploy/asound.conf` makes the
  jack (ALSA card `Headphones`) the default output, because plugging in the AM8 reorders the cards.
  The unit sets `SDL_AUDIODRIVER=alsa` for pygame. The setup script sets the jack's volume to
  100%, and the Bose's buttons do the rest. No Bluetooth, no PipeWire.
- **Printer: direct USB only on the Pi,** with a udev rule so the service user may open
  `0485:5741`. `python-escpos` detaches the kernel's `usblp` driver itself when it opens the
  printer. If that fails on the Pi ("Resource busy"), the fix is to blacklist `usblp`, and Step 8
  says so. No CUPS, so there's no `lpr` fallback on the Pi. A print failure still prints to the
  log, as it does today.
- **Logs: journald, persistent, capped, synced often.** The drop-in sets `Storage=persistent`,
  `SystemMaxUse=100M`, and `SyncIntervalSec=15s`. journald's default sync interval is 5 minutes,
  so a power pull could lose that much of the log. The unit sets `PYTHONUNBUFFERED=1`. The
  operator reads the log with `journalctl -u narly -f`, and counts outcomes with `journalctl -u
  narly | grep -c 'outcome=no_speech'`. `--log-file` isn't used by the service.
- **The service starts without waiting for the network.** Narly makes no network call until the
  first coin, so there's no `network-online.target` dependency and nothing to crash-loop on while
  Wi-Fi joins. If the network still isn't up at the first coin, that coin gets the usual fallback
  slip.
- **The persona is fixed when the setup script runs.** `deploy/setup-pi.sh [persona]` writes it
  into the installed unit, defaulting to `default`. Changing it means re-running the script, which
  is safe to repeat.
- **Networks: home Wi-Fi from the Imager, and the phone hotspot added over SSH.** The event network
  is added at the booth. Bookworm uses NetworkManager, so `nmcli connection add ...` stores a
  network that's out of range. The Pi is reached as `narly.local`, hostname `narly`, set in the
  Imager.
- **The repo is public** (`https://github.com/robot-denny/NarlyFortuneTeller` returned 200 on
  2026-09-28), so the Pi clones over HTTPS with no token. The Pi runs `feature/pi-port`, pushed,
  until it merges.
- **`first_coin_ignored` stays.** Opening the connection once still resets the Uno once at start,
  so a spurious first coin may still arrive. Step 8 checks on both machines whether the first real
  coin is being swallowed. Removing the workaround is a later change, with its own test.
- **Coin-to-ticket time comes from the logs.** It's the gap between `💰 [COIN EVENT]` and `✓
  Fortune cycle complete`. The laptop figures already exist in `clips/threshold-hold/session.log`
  (the 95% run), at about 7–9 s per cycle in its first entries. No new tool.
- **New test files follow `stack.md` → *Tests*:** `tests/test_arduino_port.py` (detection and
  waiting, a flow across `serial_trigger`), `tests/test_led_client.py` (extended),
  `tests/test_serial_listen.py` (one connection, clean exit on unplug),
  `tests/test_startup_checks.py`, and `tests/test_mic_choice.py`. The shared `quiet_and_configured`
  fixture in `tests/conftest.py` switches from patching `LedClient` to setting `serial_trigger._led`.
- **Commands used**, all from `stack.md`: `.venv/bin/python -m pytest -q`,
  `.venv/bin/python -m compileall -q *.py`, and `.venv/bin/python serial_trigger.py
  --list-personas`. For shell files: `bash -n deploy/setup-pi.sh`, a syntax check that works on
  the Mac. `systemd-analyze verify` only runs on the Pi, in Step 8.
- **Pushes and tags are confirmed with the owner at the time.** Steps 1 and 8 push to `origin`,
  which counts as outward-facing.

---

## Steps

Each step is designed to be completed independently in its own context window.
The step heading contains a ready-to-use prompt you can paste into a new session.

---

### Step 1 — Tag the known-good version

> **Prompt**: Implement Step 1 of `_work/pi-port/plan.md`. Create an annotated git tag
> `laptop-known-good-2026-09-28` on commit `c8bb755` (the `main` head that scored 95% on
> 2026-09-28), message "Known-good laptop build: 95% baseline, before the Pi port". Ask the owner
> before running `git push origin laptop-known-good-2026-09-28`. Then prove the tag runs: in a
> scratch worktree (`git worktree add ../narly-known-good laptop-known-good-2026-09-28`), run
> `/Users/dkardys/Sites/fortune-service/.venv/bin/python serial_trigger.py --list-personas` and
> `... serial_trigger.py --mode simulate --dry-run --offline --auto --interval 60 --question "Will I
> find treasure today?"` from that worktree's root (`--auto` fires the coin, since there's no
> keyboard to press Enter; stop it with Ctrl+C after the ticket), confirm a `[TEST FORTUNE]` ticket prints to the console,
> then `git worktree remove ../narly-known-good`. Make no code changes. Record the tag name and
> the check in `_work/pi-port/notes/known-good.md` and commit that note.

**What to build**:
- An annotated tag `laptop-known-good-2026-09-28` → `c8bb755`, pushed to `origin` after the
  owner confirms.
- `_work/pi-port/notes/known-good.md`: the tag, the commit, and the two commands to return to it
  on the laptop (`git fetch --tags`, `git switch --detach laptop-known-good-2026-09-28`), plus the
  check's result.

**Validation**:
- [Automated]: `git tag -n1 laptop-known-good-2026-09-28` shows the message.
  `git ls-remote --tags origin laptop-known-good-2026-09-28` shows the tag on GitHub.
- [Manual]: the offline dry run from the worktree prints a `[TEST FORTUNE]` ticket and exits
  cleanly. It uses the shared `.venv`, which proves the venv works on the tagged code.

---

### Step 2 — Find the Arduino on either machine, and wait for it

> **Prompt**: Implement Step 2 of `_work/pi-port/plan.md`. In `serial_trigger.py`, make Arduino
> detection work on macOS and on Linux (the Pi), and make hardware mode wait for an Arduino rather
> than exit. Do it in three test-first cycles, each RED then GREEN before the next.
> (a) `find_port()` takes an optional list of ports, each with `.device`, `.description`, `.vid`,
> defaulting to `serial.tools.list_ports.comports()`. It returns the first Arduino-like device,
> matched by VID in {0x2341, 0x2A03}, "Arduino" in the description, or "usbmodem" in the
> device, and `None` if there isn't one. Tests use `types.SimpleNamespace` ports shaped like the
> laptop's (`/dev/cu.usbmodem1101`, description `IOUSBHostDevice`, vid 0x2341) and the Pi's
> (`/dev/ttyACM0`, description `ttyACM0`, vid 0x2341), and a list with only
> `/dev/cu.Bluetooth-Incoming-Port` (vid None) → None.
> (b) `--port` defaults to `None`, and the `PORT` literal is removed. Test through the parser:
> factor the parser into `build_parser()` so a test can call `build_parser().parse_args([])` and
> see `port is None`, and `["--port", "/dev/x"]` keep `/dev/x`.
> (c) Add `wait_for_port(find=find_port, sleep=time.sleep)`. It returns the first port `find()`
> gives, calling `sleep` between tries, and logs "Waiting for the Arduino" once, then again about
> every minute. Test with a `find` that returns None twice then `/dev/ttyACM0`: the result is
> `/dev/ttyACM0`, the waiting line is logged, and `sleep` was called twice.
> Then wire it in: hardware mode uses `args.port or wait_for_port()`, and simulate mode uses
> `args.port or find_port()` (no waiting) for `LED_PORT`. Tests go in
> `tests/test_arduino_port.py`. Run `.venv/bin/python -m pytest -q`.

**What to build**:
- `serial_trigger.py`: `find_port(ports=None)`, `ARDUINO_VIDS`, `build_parser()` extracted from
  `main()`, `--port` default `None`, the `PORT` literal removed (the help text says "auto-detect
  if omitted"), `wait_for_port(find, sleep)`, and `main()` wired as above.
- `tests/test_arduino_port.py`.

**Test first**:
- Cycle (a): detection returns the right device for Mac-shaped and Pi-shaped lists, and `None`
  when no Arduino is there. RED: the Pi case fails against today's code.
- Cycle (b): with no `--port`, the parsed port is `None`. RED: today it's the literal.
- Cycle (c): waiting returns the port once it appears and logs the waiting line.
- `.venv/bin/python -m pytest -q`: confirm RED before each implementation.

**Validation**:
- [Automated]: `.venv/bin/python -m pytest -q` all pass (the two known `DeprecationWarning`s are
  expected). `.venv/bin/python serial_trigger.py --list-personas` still lists three personas.
- [Manual] (owner, plain terminal): with the Arduino plugged into either USB-C jack, run
  `.venv/bin/python serial_trigger.py --dry-run` with no `--port`. The log shows the
  `/dev/cu.usbmodem…` port it found. Unplug it and start again: the log says it's waiting.
  Plug it in: it carries on. Ctrl+C ends it.

---

### Step 3 — One Arduino connection per run

> **Prompt**: Implement Step 3 of `_work/pi-port/plan.md`. Stop `on_coin_event` from opening a
> second serial connection to the Arduino on every coin. On the Pi, each open resets the Uno.
> Test first, one cycle per behavior:
> (a) In `led_client.py`, `LedClient(port=None)` is a no-op that opens nothing. Add
> `LedClient.sharing(ser)`, which wraps an already-open serial object without the 2-second sleep,
> and whose `close()` leaves that port open. Open with `exclusive=True`. If opening fails, log one
> WARNING naming the port and hinting "is Narly already running? On the Pi: sudo systemctl stop
> narly". Extend `tests/test_led_client.py` with a `FakeSerial` that records `close()` calls.
> (b) In `serial_trigger.py`, add a module-level `_led` (default: a no-op object). `on_coin_event`
> uses `_led` and no longer constructs or closes an `LedClient`. `listen_serial_mode` opens
> `serial.Serial(port, BAUD, timeout=1, exclusive=True)` once and sets `_led =
> LedClient.sharing(ser)`. `simulate_mode` sets `_led = LedClient(LED_PORT, BAUD)` once at start,
> replacing `led_init`. Update `tests/conftest.py` → `quiet_and_configured` to set and restore
> `serial_trigger._led` to its `_NoLeds` instead of patching `LedClient`. In
> `tests/test_serial_listen.py`, patch `serial_trigger.serial.Serial` with a fake whose
> `readline()` yields `b"COIN 1\n"` (ignored as the first), `b"COIN 1\n"`, `b"COIN 1\n"`, then
> raises `KeyboardInterrupt`. Patch `time.sleep` to do nothing and `on_coin_event`'s providers
> with the fakes from `fakes.py` (dry run). Assert `Serial` was constructed exactly once, and
> that the bytes written to it contain `START GLOW` and `STOP` for both coins.
> Run `.venv/bin/python -m pytest -q`. Keep `first_coin_ignored` as it is.

**What to build**:
- `led_client.py`: `port=None` default, the `sharing(ser)` constructor, `exclusive=True`, and the
  warning on a failed open.
- `serial_trigger.py`: `_led`, with `on_coin_event`, `listen_serial_mode`, and `simulate_mode`
  changed as above. The `LedClient` import fallback class stays.
- `tests/conftest.py`, `tests/test_led_client.py`, `tests/test_serial_listen.py`.

**Test first**:
- Cycle (a): a shared client writes to the given port and its `close()` doesn't close it. With
  `port=None`, nothing is opened. RED first.
- Cycle (b): two real coins through `listen_serial_mode` → one `Serial(...)` construction, with
  LED commands for both. RED: today the LED client opens its own port per coin.

**Validation**:
- [Automated]: `.venv/bin/python -m pytest -q` all pass, including every existing
  `on_coin_event` test through the updated fixture.
- [Manual] (owner, plain terminal, laptop + Arduino + printer): `.venv/bin/python
  serial_trigger.py` (hardware mode, no `--port`). Insert two coins in a row. The LEDs glow and
  pulse for both, both tickets print, and the log shows no `[arduino]` ready/boot lines between
  the coins. Note whether the very first coin was ignored.

---

### Step 4 — Fail clearly, so the service can act

> **Prompt**: Implement Step 4 of `_work/pi-port/plan.md`. Two behaviors in `serial_trigger.py`,
> each test-first.
> (a) An Arduino that disappears ends the run. In `listen_serial_mode`, catch
> `serial.SerialException` and `OSError` from the read loop. Log one ERROR, `Arduino
> disconnected: <detail>`, which also says a restart will look for it again, then `sys.exit(1)`.
> Ctrl+C still exits quietly. Do the same when **opening** the port fails (for example, because
> `exclusive=True` finds another copy of Narly holding it). Log one ERROR, `Could not open the
> Arduino port <port>: <detail>`, with the hint "is Narly already running? On the Pi: sudo
> systemctl stop narly", then `sys.exit(1)`. Test both with a fake serial. For the open: patch
> `serial_trigger.serial.Serial` to raise `serial.SerialException("Could not exclusively lock
> port")`. For the read: a fake serial whose
> `readline()` raises `serial.SerialException("device reports readiness to read but returned no
> data")`: `pytest.raises(SystemExit)` with code 1, and the ERROR line is logged.
> (b) Startup refuses to run without an OpenAI key. In `main()`, after parsing and
> `configure_logging`, if `--offline` isn't set and `OPENAI_API_KEY` is empty, log an ERROR naming
> `.env` and `.env.example`, then exit 1. `--list-personas` still works without a key. The check
> relies on `ai_client.py` having loaded `.env` when it was imported at the top of
> `serial_trigger.py`, so keep that import above the check. The test passes its own `env` dict
> rather than touching the real environment or `.env`. Put the
> check in a small function `check_can_start(args, env=os.environ)` and test it in
> `tests/test_startup_checks.py`: no key + hardware → SystemExit 1 with the message; no key +
> `--offline` → no exit; key present → no exit.
> Run `.venv/bin/python -m pytest -q`.

**What to build**:
- `serial_trigger.py`: the disconnect handling in `listen_serial_mode`, `check_can_start()`, and
  the call from `main()`.
- `tests/test_serial_listen.py` (extended), `tests/test_startup_checks.py`.

**Test first**:
- Cycle (a): an unplug mid-read → exit code 1 and one ERROR line. RED: today the exception
  escapes as a traceback.
- Cycle (b): no key and not offline → exit 1 with the `.env` message. RED first.

**Validation**:
- [Automated]: `.venv/bin/python -m pytest -q` all pass. The existing offline tests still pass,
  and they run without a key.
- [Manual] (owner, plain terminal): with the Arduino in, start hardware mode, then pull the USB
  cable. Narly logs `Arduino disconnected` and returns to the shell prompt, with no traceback.
  `echo $?` prints `1`.

---

### Step 5 — Choose the AM8 by name

> **Prompt**: Implement Step 5 of `_work/pi-port/plan.md`. Make Narly use the Fifine AM8 even
> when it isn't the computer's default input. Test-first in `tests/test_mic_choice.py`: add a pure
> function `pick_mic_index(names, wanted)` to `serial_trigger.py`. It returns the index of the
> first name containing `wanted` (case-insensitive), or `None` when there's no match or `wanted`
> is empty. Test cases: `["bcm2835 Headphones: - (hw:0,0)", "AM8: USB Audio (hw:2,0)", "default"]`
> with `"AM8"` → 1; `"am8"` also → 1; `["MacBook Pro Microphone"]` → None. Then wire it:
> add a module-level `_mic_index = None`. `mic_get_audio` creates `sr.Microphone(device_index=_mic_index)`
> when no mic is passed in. In `main()`, if the mic is really used (not `--question`, `--offline`,
> or `--clip`), read `MIC_NAME` from the environment (default `AM8`), call
> `sr.Microphone.list_microphone_names()` inside a try, set `_mic_index`, and log either
> `Microphone: <name> (device <i>)` or `Microphone: "<wanted>" not found, using the default
> input`. Add a commented `MIC_NAME=AM8` block to `.env.example` explaining that it's part of the
> name the mic reports. Run `.venv/bin/python -m pytest -q`.

**What to build**:
- `serial_trigger.py`: `pick_mic_index`, `_mic_index`, the change to `mic_get_audio`, and the
  startup lookup and log line in `main()`.
- `.env.example`: the `MIC_NAME` entry.
- `tests/test_mic_choice.py`.

**Test first**:
- `pick_mic_index` picks the AM8 by part of its name, ignoring case, and returns `None`
  otherwise. RED: the function doesn't exist.

**Validation**:
- [Automated]: `.venv/bin/python -m pytest -q` all pass.
- [Manual] (owner, plain terminal, laptop + AM8): `.venv/bin/python serial_trigger.py --mode
  simulate --dry-run`. The startup log names the AM8 and its device number. Press Enter, ask
  "Will I find treasure today?", and the log shows `capture outcome=heard`. Then set a different
  default input in macOS Sound settings and repeat: the AM8 is still chosen.

---

### Step 6 — The Pi kit under `deploy/`

> **Prompt**: Implement Step 6 of `_work/pi-port/plan.md`. Create the Pi-only files under
> `deploy/`. The laptop never runs them. Target: Raspberry Pi OS Lite 64-bit **Legacy
> (Bookworm)**, Python 3.11, repo cloned at `~/fortune-service`, run as the login user.
> (1) `deploy/setup-pi.sh [persona]` (bash, `set -euo pipefail`, safe to re-run, explained with
> comments for a beginner). It `apt install`s `git python3-venv python3-dev portaudio19-dev flac
> libusb-1.0-0`. It creates `.venv` and runs `pip install -r requirements.txt`. It adds the user
> to `dialout audio plugdev`. It installs `deploy/99-narly-printer.rules` to
> `/etc/udev/rules.d/`, `deploy/asound.conf` to `/etc/asound.conf`, and
> `deploy/journald-narly.conf` to `/etc/systemd/journald.conf.d/narly.conf` (creating
> `/var/log/journal`), and restarts journald. It renders `deploy/narly.service` with the user,
> the repo path, and the persona (default `default`) into `/etc/systemd/system/narly.service`,
> runs `daemon-reload`, and runs `systemctl enable narly` without starting it. It sets the
> headphone jack to 100% (`amixer -c Headphones sset PCM 100%`, then `alsactl store`). If `.env`
> is missing it warns and says not to start the service yet.
> (2) `deploy/narly.service`: `[Unit]` has `Description=Narly fortune teller`,
> `StartLimitIntervalSec=300`, `StartLimitBurst=10`. `[Service]` has `User=@USER@`,
> `WorkingDirectory=@DIR@`, `ExecStart=@DIR@/.venv/bin/python serial_trigger.py --mode hardware
> --persona @PERSONA@`, `Environment=PYTHONUNBUFFERED=1`, `Environment=SDL_AUDIODRIVER=alsa`,
> `Restart=always`, `RestartSec=5`. `[Install]` has `WantedBy=multi-user.target`. No network
> dependency.
> (3) `deploy/journald-narly.conf`: `[Journal]` with `Storage=persistent`, `SystemMaxUse=100M`,
> `SyncIntervalSec=15s`.
> (4) `deploy/99-narly-printer.rules`: USB `0485:5741`, `GROUP="plugdev"`, `MODE="0660"`.
> (5) `deploy/asound.conf`: `defaults.pcm.card Headphones` and `defaults.ctl.card Headphones`.
> Each file has a header comment saying what it's for and why (see `_work/pi-port/plan.md` →
> Key Decisions). Check with `bash -n deploy/setup-pi.sh`. Don't change any Python module.

**What to build**:
- `deploy/setup-pi.sh`, `deploy/narly.service`, `deploy/journald-narly.conf`,
  `deploy/99-narly-printer.rules`, `deploy/asound.conf`.

**Validation**:
- [Automated]: `bash -n deploy/setup-pi.sh` exits 0. `.venv/bin/python -m pytest -q` still passes
  (nothing in Python changed). `git diff --stat main -- '*.py'` shows only Steps 2–5's changes.
- Nothing more can be checked on the Mac. Step 8 runs these files on the Pi.

---

### Step 7 — The Pi guide and the switch-back runbook

> **Prompt**: Implement Step 7 of `_work/pi-port/plan.md`. Write two documents for the owner, who
> is new to the Raspberry Pi and Linux (see CLAUDE.md → *User notes*; match the plain, numbered
> style of `docs/testing.md` and `docs/capture-baseline.md`).
> (1) `deploy/README.md`, from a blank SD card to a running Narly, in order:
> - In Raspberry Pi Imager, choose **Raspberry Pi OS Lite (64-bit) under "Legacy" (Bookworm)** and
>   say why. OS customisation: hostname `narly`, a username and password, home Wi-Fi, SSH on.
> - First boot and `ssh <user>@narly.local`.
> - Add the phone hotspot as a stored network with `nmcli connection add type wifi con-name
>   hotspot ssid "<name>" wifi-sec.key-mgmt wpa-psk wifi-sec.psk "<password>"`.
> - `git clone https://github.com/robot-denny/NarlyFortuneTeller.git fortune-service`, then
>   `git switch feature/pi-port` until merged.
> - `./deploy/setup-pi.sh [persona]`, then log out and back in for the new groups.
> - Copy `.env` from the laptop with `scp`. Check it's printer and key values only; nothing Mac-
>   or port-shaped.
> - Plug in the hardware: the Arduino, the AM8, the printer, and the Bose on the headphone jack by
>   AUX cable. The official 3 A supply. The LED strip on its own 5 V supply, as now.
> - First check: `.venv/bin/python serial_trigger.py --mode simulate --offline --question "Will I
>   find treasure today?"` prints a ticket and plays the cues.
> - `sudo systemctl start narly`, and watch with `journalctl -u narly -f`.
> - Short sections: *Adding the event Wi-Fi at the booth* (hotspot on, laptop on the hotspot, SSH
>   in, `nmcli connection add …` for the event network, `sudo reboot`). *Running a measuring
>   session* (`sudo systemctl stop narly` first, then the simulate `--save-clips` command from
>   `docs/capture-baseline.md` with `clips/pi/`, then `sudo systemctl start narly` after).
>   *Counting outcomes* (`journalctl -u narly | grep -c 'outcome=no_speech'`, and `--since
>   today`). *Changing persona* (re-run the setup script). *Updating the code* (`git pull`, then
>   `sudo systemctl restart narly`). *Checking for low power* (`vcgencmd get_throttled`; `0x0` is
>   good). *Troubleshooting*: `narly.local` not found; the printer reports "Resource busy" (the
>   `usblp` blacklist); no sound (`aplay -l`, the Headphones card, the Bose's volume and power);
>   and `systemctl status narly` after the retry limit (`sudo systemctl reset-failed narly`).
> (2) `docs/switching-computers.md`, the swap in both directions. Pi → laptop: `sudo systemctl
> stop narly` (or just pull the Pi's power). Move the Arduino, AM8, and printer USB cables to the
> laptop, and the Bose AUX cable to the laptop's headphone jack. On the laptop: `git switch main`,
> or `git switch --detach laptop-known-good-2026-09-28` if the laptop proof in Step 9 didn't pass.
> Plug in power. Stop it sleeping: `caffeinate -dims` in its own Terminal window, or System
> Settings → Battery → prevent sleep when the display is off. Don't close the lid unless an
> external display is attached. Then `.venv/bin/python serial_trigger.py --log-file clips/narly.log` (inside `clips/`, which git
> ignores, so the log never shows up as an untracked file),
> one test coin, one ticket. Laptop → Pi: the reverse, then power on and wait for the start-up
> cue. Also cover the Bose checks: mains power, volume set at the booth, press power if the cues
> go quiet. Say which code version the laptop should be on for the event.
> Link both from `docs/testing.md` where it fits. Don't change any Python module.

**What to build**:
- `deploy/README.md`, `docs/switching-computers.md`, and a link from `docs/testing.md`.

**Validation**:
- [Automated]: none, beyond `.venv/bin/python -m pytest -q` still passing.
- [Manual]: read-through by the owner. Every command is copy-pasteable, and every step says what
  you should see. Step 8 is the real test of the guide.

---

### Step 8 — Bring up the Pi from the guide (owner, on the Pi)

> **Prompt**: Implement Step 8 of `_work/pi-port/plan.md`. This step is run by the owner with the
> Pi and the booth hardware. Claude's part is to push the branch (ask first: `git push -u origin
> feature/pi-port`), then help with any failure the owner reports, keeping a log of it. Create
> `_work/pi-port/notes/pi-bringup.md` with the checklist below. The owner ticks each item and
> notes what they saw. Anything that fails is fixed on this branch: a code fix gets a test first,
> as in Steps 2–5; a guide fix goes into `deploy/README.md`. Then pull on the Pi and re-check.
> Record the AM8's name as the Pi reports it, from
> `.venv/bin/python -c "import speech_recognition as sr; print(sr.Microphone.list_microphone_names())"`,
> and the Arduino's port from the start-up log.
> Checklist:
> (1) Blank SD → running Narly by following `deploy/README.md` alone. Note any step that needed
> outside help.
> (2) `systemd-analyze verify /etc/systemd/system/narly.service` reports nothing.
> (3) The offline fortune prints a ticket, and the cues are heard from the Bose. Note whether the
> jack hisses (if it does, use a USB audio adapter and change the `Headphones` card name).
> (4) Pull the power, plug it back in: the start-up cue plays with no keyboard or login, and a coin
> gives a ticket.
> (5) `sudo pkill -9 -f serial_trigger.py`: Narly comes back on his own and waits for a coin again
> (how long it takes doesn't matter), and the journal shows the restart.
> (6) Two coins in a row: LEDs for both, no Arduino start-up lines between them. Also note whether
> the first coin after start was ignored.
> (7) Unplug the Arduino, plug it into a different USB port on the Pi: `Arduino disconnected`
> is logged, then waiting, then a coin works.
> (8) Rename `.env` away and restart: after the retry limit, `systemctl status narly` shows
> failed, and the journal names `.env`. Put it back and run `sudo systemctl reset-failed narly &&
> sudo systemctl start narly`.
> (9) Three fortunes, wait 20 s, pull the power, boot: `journalctl -u narly -b -1 | grep -c
> 'capture outcome='` shows 3.
> (10) Rehearse the booth Wi-Fi: with home Wi-Fi off or out of range, turn on the phone hotspot.
> The Pi joins it and `ssh <user>@narly.local` works from the laptop on the hotspot.
> (11) `vcgencmd get_throttled` after a print shows `0x0`.

**What to build**:
- `_work/pi-port/notes/pi-bringup.md` (the checklist and its results).
- Any fixes the checklist finds: code with a test first, or `deploy/` files and the guide.

**Validation**:
- [Manual] (owner, on the Pi and at the cabinet): all 11 checklist items ticked in
  `_work/pi-port/notes/pi-bringup.md`, with the AM8 name and Arduino port recorded.
- [Automated]: after any code fix, `.venv/bin/python -m pytest -q` passes on the laptop.

---

### Step 9 — The go/no-go session, the swap drill, and the laptop proof

> **Prompt**: Implement Step 9 of `_work/pi-port/plan.md`. The owner runs the sessions, and
> Claude scores them and writes up the results. The rule was set in `_work/pi-port/spec.md` →
> *Open Questions* before this session: **the Pi goes to the event if it scores at least 17 of
> 20, with no crashes, and its coin-to-ticket time is no more than a few seconds longer than the
> laptop's.**
> (1) On the Pi, following `deploy/README.md` → *Running a measuring session*: the same 20
> questions (ids 1–10 quiet, 21–30 with the crowd-noise track at the same volume), the AM8 on its
> stand, and the Bose on its AUX cable as at the event. Save to `clips/pi/`, logging to
> `clips/pi/session.log`. Leave the Bose idle for 30 minutes during the session and note whether
> it switched itself off.
> (2) Score it with `baseline.py`, as `docs/capture-baseline.md` describes. Copy the laptop's
> clips (`clips/threshold-hold/*.wav`) to the Pi's `clips/laptop/` with `scp`, and replay them
> there against `docs/baseline-script.csv`.
> (3) Coin-to-ticket times: from the gaps between `💰 [COIN EVENT]` and `✓ Fortune cycle
> complete` in `clips/pi/session.log` and in the laptop's `clips/threshold-hold/session.log`.
> Report the median and the longest for each.
> (4) Add a row to the results in `docs/capture-baseline.md`: "Pi 4, Bose on AUX". Note that the
> laptop's 95% was measured without the Bose. Write the decision: "Pi goes to the event" or "the
> laptop goes to the event", with the numbers. Update `ROADMAP.md` → *Now/Next* to match.
> (5) Swap drill: move from the Pi to the laptop by following `docs/switching-computers.md`
> exactly, with this branch checked out on the laptop. Run the full laptop hardware run (coin →
> LEDs → mic → printer) with the Bose on the laptop's headphone jack, plus
> `.venv/bin/python -m pytest -q`. If both pass, this is the laptop proof, and the branch may
> merge. If either fails, the laptop runs the tag at the event, and the runbook's version line
> says so.
> Commit the results. Open the PR only if the owner asks.

**What to build**:
- Results in `docs/capture-baseline.md`, the decision recorded, and `ROADMAP.md` updated.
- A tick-list of the swap drill appended to `_work/pi-port/notes/pi-bringup.md`, with any runbook
  corrections in `docs/switching-computers.md`.

**Validation**:
- [Manual] (owner): the Pi session was run and scored, the replay was run, the times were noted,
  the Bose idle result was noted, and the swap drill was done from the runbook alone, ending with
  a ticket from the laptop.
- [Automated]: `.venv/bin/python -m pytest -q` passes on the laptop with this branch checked out.

---

### Final — Record the durable behavior *(a spell you cast, not an implement-step)*

**If `fix-infra`:**

> **Prompt**: Do **not** create or touch any feature doc. The durable record for the Pi port is
> the runbooks `deploy/README.md` and `docs/switching-computers.md`, written in Step 7 and
> corrected in Steps 8–9. Make sure they match what actually worked on the Pi. In `CLAUDE.md`:
> add `deploy/` and the two runbooks under *Key entry points*. Under *Arduino serial protocol*,
> note that the port is auto-detected by USB identity (VID `0x2341`) and that `--port` overrides
> it. Record `MIC_NAME`. Note Bookworm/Python 3.11 and `flac` as Pi requirements. Record the
> known-good tag `laptop-known-good-2026-09-28`. Update *Upgrade status* for Increment 3 with the
> go/no-go result. Update `.agents/config/conventions.md` → *Planning gotchas*: the serial-port
> bullet now says the literal is gone and detection is real. Commit.
>
> **Validation**: The runbooks exist and match the Pi as built. CLAUDE.md names them. No feature
> doc was touched.

---

## File Summary

| Action | File |
|--------|------|
| Create | `_work/pi-port/notes/known-good.md` |
| Modify | `serial_trigger.py` |
| Modify | `led_client.py` |
| Modify | `.env.example` |
| Modify | `tests/conftest.py` |
| Modify | `tests/test_led_client.py` |
| Create | `tests/test_arduino_port.py` |
| Create | `tests/test_serial_listen.py` |
| Create | `tests/test_startup_checks.py` |
| Create | `tests/test_mic_choice.py` |
| Create | `deploy/setup-pi.sh` |
| Create | `deploy/narly.service` |
| Create | `deploy/journald-narly.conf` |
| Create | `deploy/99-narly-printer.rules` |
| Create | `deploy/asound.conf` |
| Create | `deploy/README.md` |
| Create | `docs/switching-computers.md` |
| Modify | `docs/testing.md` |
| Create | `_work/pi-port/notes/pi-bringup.md` |
| Modify | `docs/capture-baseline.md` |
| Modify | `ROADMAP.md` |
| Modify | `CLAUDE.md` |
| Modify | `.agents/config/conventions.md` |
| _(work type: `fix-infra`)_ Create/Update | runbooks `deploy/README.md` and `docs/switching-computers.md` (**no feature doc**) |
