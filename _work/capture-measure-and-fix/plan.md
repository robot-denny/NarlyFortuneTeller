# Plan: Measure and Fix Attendee Capture

**Spec**: `_work/capture-measure-and-fix/spec.md`
**Branch**: `feature/capture-measure-and-fix`
**Work type**: change-to audio-capture
**Feature doc**: audio-capture

## Context

Narly hears attendees correctly about a third of the time in a room with conversation, and every
one of its five capture failures prints the same generic fortune, so nothing records which one
struck. This increment makes capture observable (a log record per fortune saying what was heard
or which failure occurred, and whether the question was substituted), reproducible (a full
fortune runs with no hardware and no API spend, from a recorded clip or typed text), and lands
the two fixes the evidence indicates: listening starts the instant the readiness chime ends, and
the wake threshold returns to the library default with adaptation on. Sound cues move in-process
so they play on Linux, where the next event runs.

The unit of work is the increment (the spec groups V2 `3a`, a scoped-down V3 `0b`, and two
fixes — see `conventions.md` → *Grouping sub-phases*). It builds on what exists: a flat module
layout with one module per concern, `--mode simulate --dry-run` already faking the coin and the
printer, `LedClient` already degrading to no-op, and a module-level `_config` global set once by
`main()` — the pattern the new seams follow. `SpeechRecognition` stays as the capture library;
replacing it is the next increment.

---

## Key Decisions

- **Test convention — SET, not followed.** `stack.md` → *Tests* is "None". This plan establishes:
  `pytest` in a new `requirements-dev.txt`; tests in `tests/test_<module>.py`; a
  `pyproject.toml` with `[tool.pytest.ini_options]` setting `testpaths = ["tests"]` and
  `pythonpath = ["."]` so the flat root modules import without packaging. Run with
  `.venv/bin/python -m pytest -q`. Record this in `stack.md` at Step 9 so the next increment
  inherits it.
- **Fakes are runtime code, one flat module.** `--mode simulate` must wire them for remote
  testers, so they cannot live only under `tests/`. `paths.md` says flat layout, no package for
  a single module; four small classes in one `fakes.py` at the root respects that. Not a
  `hardware/` package (the audit's shape) — that is more structure than four classes earn.
- **Seams follow the `_config` pattern.** `serial_trigger.py` gains module-level providers —
  `_get_audio`, `_transcribe`, `_fortune`, `_audio_out` — set once by `main()` via a
  `configure_providers(...)` function, and set by tests the same way. No dependency-injection
  framework; this is how the codebase already passes startup state.
- **Capture is extracted to `capture_client.py`.** Matches the `<thing>_client.py` naming in
  `paths.md`. It exposes `capture_question(get_audio, transcribe) -> CaptureResult`, where
  `CaptureResult` carries `outcome` (one of six), `text`, and `seconds`. The six outcomes are
  `heard`, `no_speech`, `not_understood`, `recognizer_error`, `mic_error`, `overrun` — the five
  failures the spec names plus success. The 25s outer guard becomes `overrun` inside this module.
- **Audio enters as a callable that receives the cue.** `get_audio(on_ready)` returns
  `sr.AudioData` or raises the same exceptions the mic path raises today, and calls `on_ready()`
  at the moment the attendee should start speaking. The orchestrator supplies `on_ready` (it
  plays the readiness chime, blocking); the provider decides *when* in its own sequence to fire
  it. The real provider wraps `sr.Microphone` + `listen()`; the WAV provider wraps
  `sr.AudioFile` + `record()`; tests pass lambdas. This is what lets the six outcomes, the cue
  order, and the cue itself all be tested without a mic or a fixture file — and why the
  sequencing fix in Step 8 is a reorder inside one function rather than a hunt across the file.
- **Log format — one greppable line per event, key=value.** Stdlib `logging`, format
  `%(asctime)s %(levelname)-8s %(message)s` — the level padded to 8 so every message starts
  in the same column regardless of severity (amended at Step 2's review; the original
  unpadded form shifted the indentation by up to three characters between INFO and WARNING). The capture record is exactly
  `capture outcome=<kind> heard="<text>" secs=<n>`, and substitution is a second line
  `question source=<heard|substituted> text="<text>"`. The operator counts a day with
  `grep -c 'outcome=no_speech' <log>`. Not JSON: the owner reads these by eye and greps them;
  structure beyond key=value is cost without benefit here.
- **Stdout always; file optional.** Per discovery and ROADMAP: stdout is the always-on sink
  (journald owns it on the Pi). A `RotatingFileHandler` is added only when `--log-file <path>`
  is given, capped at 5 MB × 3 files — the laptop convenience, and the spec's "log does not grow
  without bound". Where the file lives and how long it is kept remains the spec's open question;
  this plan does not decide retention.
- **Playback — `pygame.mixer`.** The audit's recommendation; plays the existing `.mp3` files
  without conversion, cross-platform, and `mixer.music.get_busy()` gives a precise "cue has
  ended" signal for the sequencing fix. Alternatives ruled out: `simpleaudio` is WAV-only and
  unmaintained; `sounddevice` + `soundfile` needs an mp3-capable libsndfile that is not reliably
  present. Risk carried forward: PortAudio device contention between pygame and the mic on the
  Pi. That is a Pi-increment verification, not this one.
- **Sequencing — listen starts when the chime ENDS, not when it starts.** *Deviation from the
  spec's scenario wording, deliberately.* The mic will hear a 1.96s chime played at volume 3.0
  from inches away; with a sensitive, adapting threshold, listening during the chime records the
  chime as speech. Field evidence is that attendees speak as the chime ends. So, inside
  `mic_get_audio`: ambient calibration runs *before* `on_ready()` (attendee not yet cued, so
  nothing is lost), `on_ready()` plays the chime blocking via `pygame`, and `listen()` is called
  on the very next line after it returns. Dead window relative to the cue attendees key on: ~0. The spec's "as the chime
  starts" scenario should be reworded to "as the chime ends" at `/feature update`.
- **Threshold — delete two lines, fix one comment.** Remove `energy_threshold = 1100` and
  `dynamic_energy_threshold = False`. Keep `adjust_for_ambient_noise` (now before the chime,
  0.5s). The library default (300, dynamic on) is the spec's requirement. The comment "Lower
  threshold to capture speech" is deleted with the line it described.
- **Deliberately out of scope**, recorded so nobody reaches for them: `TIMEOUT_RECORDING` being
  inert (Open Issue 2 — goes with endpointing in the next increment); the double serial open and
  `led_client.py` default port (Pi increment); `app.py` (unchanged; it never captures audio);
  replacing `SpeechRecognition` (next increment).
- **Simulate-mode flags.** `--offline` wires `FakeTranscriber` and `FakeFortune` (no network,
  no spend). `--clip <path.wav>` replays a file through the recognizer path; `--question "<text>"`
  skips capture and supplies the text directly. `--clip` without `--offline` runs the *real*
  Google recognizer on the file — permitted, for testing the recogniser against fixtures later,
  but not deterministic and not what "same clip, same outcome" promises. Reproducibility is
  guaranteed only with `--offline`.
- **Decided at Step 2's review.** `configure_logging` removes only the handlers it attached
  itself, never others' (pytest's `caplog` was being silently stripped, which would have let
  Step 5's tests pass while asserting nothing). A bad `--log-file` path degrades to stdout-only
  with one ERROR line rather than crashing `main()`. `httpx`, `httpcore`, `openai`, and
  `urllib3` are held to WARNING so the event log is not interleaved with one HTTP line per
  fortune. The blank lines that used to separate cycles on the terminal are gone and are **not**
  being replaced: the unconditional `💰 [COIN EVENT]` line is the grouping anchor.
- **`pyaudio` is added at Step 7, not the Pi increment.** Step 2's manual check found it absent
  from the venv (`Could not find PyAudio`), so the real mic cannot open on the laptop at all —
  which would make Step 8's arm's-length check impossible. V2 `3e` had it as a Pi item; the mic
  needs it on every platform, so it lands with the other runtime dependency this increment adds.
- **Decided at Step 3's review.** `FakeFortune`'s default text is `"[TEST FORTUNE] You will find
  what you seek."` rather than the plan's literal — a dry-run ticket from an offline run must
  not be mistakable for a real one by a tester reading only the ticket. `FakeAudioOut` is not
  wired by any flag and the docstrings no longer claim it is: `PygameAudioOut` already degrades
  when no speaker exists, so the fake serves tests only, and it proves cue *order*, not timing.
- **Decided at Step 4's review.** `CaptureResult` gains `detail: str | None` — the failing
  error's message, or its class name when it has none — so the log line can say which mic or
  recognizer error struck, not just that one did (today's code logs `{e}`; losing it would be a
  regression). The capture log line therefore extends to `capture outcome=<kind> heard="<text>"
  secs=<n> detail="<why>"`, the last field present only on failures, so every grep in the plan
  still works. A recognizer that returns empty text is `not_understood`, never `heard` — the
  module normalises it so the log can never say "heard" beside a substituted question. `secs=` on
  `overrun` is the true stall time, not the guard value; do not truncate it.
- **Decided at Step 5's review.** Every quoted value on the two log lines — `heard`, `text`,
  and `detail` — goes through one `_flatten()` (whitespace collapsed, `"` → `'`) so an attendee's
  words can no more split an event across lines than an error message can. `on_coin_event`
  raises a plain `RuntimeError` if `configure_providers()` was never called, rather than letting
  a `None` provider surface as a misleading `mic_error`. The capture call passes
  `overall_timeout=TIMEOUT_RECORDING + 10`, restoring the exact relationship the deleted wrapper
  had — this does not fix Open Issue 2 (the constant still does not control `listen()`) and does
  not claim to. Tests stub `LedClient` as well as `afplay`, so a test run on a laptop with the
  Arduino attached never opens the port or animates the booth.
- **Decided at Step 6's review.** `--offline` with neither `--clip` nor `--question` is a typed
  run of the persona's `default_question`, not a real-mic run: the whole audience for `--offline`
  is a tester with nothing plugged in, and until Step 7 lands `pyaudio` the real mic could only
  produce `mic_error`. Flag logic lives in `build_providers(args)`, outside `main()`, so a test can
  drive it. `--clip` paths are validated at startup with `parser.error`, not discovered per coin
  as a mislabelled `mic_error`. The conftest fixture is opt-in (`pytestmark = usefixtures`) so the
  four test files that never touch `serial_trigger` stay independent of its import graph. Offline
  runs log `outcome=heard` with the fake's text — the capture-line format is a fixed contract and
  the startup `Offline:` line gives the context; `/feature update` should say so in the doc.
- **Decided at Step 7.** pygame's volume runs 0.0–1.0, so the old `afplay -v 3.0` boost is lost;
  the physical speaker's volume compensates. `PygameAudioOut.play` checks the file before the
  device, so `sfx missing` is logged even on a machine with no speaker. `on_coin_event`'s
  "providers not configured" guard now includes `_audio_out`, since a `None` there would crash
  inside `on_ready` and be logged as a misleading `mic_error`. `pygame.mixer.music` is one
  channel: a new cue stops the one playing (the 10.5 s thinking cue is cut off by the next coin's
  chime), where `afplay` processes could overlap.
- **Decided at Step 7's review.** A blocking `play(..., wait=True)` gives up after `max_wait`
  (default `MAX_WAIT_SECONDS = 5.0`, against a 1.96 s chime), stops the sound, and logs
  `sfx stuck: <path>`. Without it a speaker that never reports "finished" would freeze the booth:
  `capture_question`'s 25 s guard decides the outcome but still waits for its worker thread.
- **Carried forward from Step 7's review** (Pi increment): `pygame.mixer.init()` runs once in
  `main()` with no timeout, so a Linux audio stack that hangs on init would stop Narly starting at
  all. Verify on the Pi alongside the pygame/mic device-contention check; bound it only if it is
  seen to hang. Also at the booth: with the `-v 3.0` boost gone, confirm the readiness chime — the
  cue that tells a guest to speak — is audible over room noise at the real speaker volume.
- **Carried forward from Step 5's review** (Increment 4, recognizer): inside the 25 s guard,
  worst-case chime (1.96 s) + calibration (0.8 s) + `listen` (10 s wait + 8 s phrase) leaves
  ~4.2 s for the Google round-trip, and `recognize_google` has no timeout of its own. Slow
  festival Wi-Fi can legitimately produce `overrun`. Pre-existing; weigh it when the recognizer
  changes.
- **Carried forward from Step 3's review** (Pi increment): `audioop` is removed in Python 3.13
  and `SpeechRecognition` 3.16 imports it (the `DeprecationWarning` on every test run is this).
  The Pi image must ship Python ≤ 3.12 until the next increment drops `SpeechRecognition`.
- **Carried forward from Step 1's review** (not this increment's work): the Pi deploy script
  must install `requirements.txt` explicitly, never a `requirements*.txt` glob, or pytest lands on
  the Pi. Belongs to the Pi increment's spec.
- **Existing test-free smoke checks stay.** `compileall` and `--list-personas` remain in
  validation lines; they are the checks `stack.md` already trusts.

---

## Steps

Each step is designed to be completed independently in its own context window.
The step heading contains a ready-to-use prompt you can paste into a new session.

---

### Step 1 — Establish the test harness

> **Prompt**: Implement Step 1 of `_work/capture-measure-and-fix/plan.md`. This project has no
> tests and no test runner; you are setting the convention. Create `requirements-dev.txt`
> containing `pytest>=8,<9`. Create `pyproject.toml` with only a `[tool.pytest.ini_options]`
> table: `testpaths = ["tests"]`, `pythonpath = ["."]`. Create `tests/__init__.py` (empty) and
> `tests/test_smoke.py` with two tests: `list_personas()` from `config_loader` returns exactly
> `["default", "music", "umbraco-2025"]`; and `render_ticket("hello", load_config("default"))`
> from `formatters` produces no line longer than 32 characters. Install with
> `.venv/bin/pip install -r requirements-dev.txt`, then run `.venv/bin/python -m pytest -q` from
> the repo root and confirm 2 passed. Do not modify any existing module.

**What to build**: `requirements-dev.txt`, `pyproject.toml`, `tests/__init__.py`,
`tests/test_smoke.py`.

**Test first**: This step *is* the first test. RED is "pytest is not installed / no tests
collected"; GREEN is `2 passed`. The two assertions pin behaviour `stack.md` already trusts, so a
later step that breaks config loading or the 32-char ticket fails here.

**Validation**:
- [Automated]: `.venv/bin/python -m pytest -q` → `2 passed`.
- [Manual]: `.venv/bin/python serial_trigger.py --list-personas` still prints three personas
  (proves `pyproject.toml` did not disturb running the modules directly).

---

### Step 2 — Logging module, and replace `print()` in the orchestrator

> **Prompt**: Implement Step 2 of `_work/capture-measure-and-fix/plan.md`. Create `logger.py` at
> the repo root exposing `configure_logging(log_file: str | None = None, level=logging.INFO)`
> and `get_logger(name)`. `configure_logging` attaches a stdout `StreamHandler` always, with
> format `%(asctime)s %(levelname)s %(message)s`; when `log_file` is given it also attaches a
> `logging.handlers.RotatingFileHandler(log_file, maxBytes=5_000_000, backupCount=3)` with the
> same format. Write `tests/test_logger.py` FIRST: configure with a `tmp_path` file, emit one
> INFO and one WARNING via `get_logger("test")`, read the file back, and assert each line starts
> with a timestamp, contains the level name, and the two levels are distinguishable; a second
> test asserts that emitting more than 5 MB rotates (file count grows, largest ≤ 5 MB). Run
> pytest, confirm RED, then implement. Then in `serial_trigger.py` add `--log-file` to argparse,
> call `configure_logging(args.log_file)` first thing in `main()`, and replace every `print()` in
> `serial_trigger.py` and the one in `config_loader.py` with `log.info` / `log.warning` /
> `log.error` on a module logger — choose the level by the existing emoji: ✓ and plain progress
> are INFO, ⚠ is WARNING, ✗ and "error" are ERROR. Keep the emoji in the messages so the live
> view still reads as it does today. Leave the `print(ticket)` calls inside the dry-run blocks
> (`--- DRY RUN OUTPUT ---`) as `print`: that is output, not a log record. Do not touch
> `app.py`.

**What to build**: `logger.py`; `tests/test_logger.py`; modify `serial_trigger.py` (argparse,
`main()`, ~57 `print` sites) and `config_loader.py` (1 site).

**Test first**:
- `tests/test_logger.py` — timestamp + level present; INFO vs WARNING distinguishable; rotation
  caps the file. RED before `logger.py` exists.

**Validation**:
- [Automated]: `.venv/bin/python -m pytest -q` → all passing; `.venv/bin/python -m compileall
  -q *.py` exits 0.
- [Manual]: `.venv/bin/python serial_trigger.py --mode simulate --dry-run --log-file
  _scratch/narly.log`, press Enter once (this DOES call OpenAI and the real mic — say nothing and
  let it time out). Confirm the terminal shows the same emoji progress as before, each line now
  prefixed with a timestamp and level, and `_scratch/narly.log` holds the same lines.
  `--list-personas` output unchanged.

---

### Step 3 — Fakes: transcriber, fortune, audio-out

> **Prompt**: Implement Step 3 of `_work/capture-measure-and-fix/plan.md`. Create `fakes.py` at
> the repo root with three small classes. `FakeTranscriber(text=None, raises=None)`: callable
> taking `audio` and returning `text`, or raising the exception instance in `raises` (tests will
> pass `speech_recognition.UnknownValueError()` and `speech_recognition.RequestError("down")`).
> `FakeFortune(text="You will find what you seek.")`: callable taking `question` and returning
> `text`; record every question received in `.questions`. `FakeAudioOut()`: has
> `play(path, wait=False)` that appends `(path, wait)` to `.played` and returns immediately, and
> `is_busy()` returning False. Write `tests/test_fakes.py` FIRST with one test per class proving
> exactly the behaviour above (return value, raise, recording). Run pytest → RED → implement →
> GREEN. Nothing else in the codebase changes in this step.

**What to build**: `fakes.py`; `tests/test_fakes.py`.

**Test first**: `tests/test_fakes.py` — `FakeTranscriber` returns text / raises the given
exception; `FakeFortune` returns text and records the question; `FakeAudioOut` records plays and
is never busy.

**Validation**:
- [Automated]: `.venv/bin/python -m pytest -q` → all passing.

---

### Step 4 — `capture_client.py`: six distinct outcomes

> **Prompt**: Implement Step 4 of `_work/capture-measure-and-fix/plan.md`. Create
> `capture_client.py` at the repo root. Define `CaptureOutcome` as an `Enum` with members
> `HEARD, NO_SPEECH, NOT_UNDERSTOOD, RECOGNIZER_ERROR, MIC_ERROR, OVERRUN` whose values are the
> lowercase strings `heard`, `no_speech`, `not_understood`, `recognizer_error`, `mic_error`,
> `overrun`. Define a `CaptureResult` dataclass with `outcome: CaptureOutcome`,
> `text: str | None`, `seconds: float`. Implement
> `capture_question(get_audio, transcribe, on_ready=lambda: None, overall_timeout=25.0)
> -> CaptureResult`: run `get_audio(on_ready)` then `transcribe(audio)` inside a
> `ThreadPoolExecutor(max_workers=1)` future with `overall_timeout`; map
> `speech_recognition.WaitTimeoutError → NO_SPEECH`, `UnknownValueError → NOT_UNDERSTOOD`,
> `RequestError → RECOGNIZER_ERROR`, any other exception from `get_audio` → `MIC_ERROR`,
> `concurrent.futures.TimeoutError → OVERRUN`, success → `HEARD` with the text. Never raise.
> Write `tests/test_capture_client.py` FIRST with one test per outcome — six tests — each
> injecting lambdas (`get_audio` as `lambda on_ready: ...` returning a sentinel object or
> raising; `transcribe` returning text or raising) and asserting the exact `outcome` member and,
> for HEARD, the text. For OVERRUN, `get_audio` sleeps past a very short `overall_timeout`. Add a
> seventh test: a `get_audio` that calls `on_ready()` causes a passed-in recording `on_ready` to
> be invoked exactly once. Run pytest → RED → implement → GREEN. Do not wire this into
> `serial_trigger.py` yet.

**What to build**: `capture_client.py`; `tests/test_capture_client.py`.

**Test first**: Six tests, one behaviour each: every failure path produces its own distinct
outcome and none collapses into another. This is Acceptance Criterion 2's foundation.

**Validation**:
- [Automated]: `.venv/bin/python -m pytest -q` → all passing, six new.

---

### Step 5 — Wire capture into the orchestrator and log the record

> **Prompt**: Implement Step 5 of `_work/capture-measure-and-fix/plan.md`. In
> `serial_trigger.py`: add module-level providers `_get_audio = None`, `_transcribe = None`,
> `_fortune = None`, `_audio_out = None` beside `_config`, and a
> `configure_providers(get_audio, transcribe, fortune, audio_out)` function that sets them.
> Move the body of `record_and_transcribe()` into a real provider pair. `mic_get_audio(on_ready,
> recognizer=None, mic=None)`: uses the passed recognizer/mic or creates `sr.Recognizer()` /
> `sr.Microphone()`; then — PRESERVING today's order exactly, Step 8 changes it — calls
> `on_ready()` first, then inside `with mic as source:` calibrates 0.8s, sets the existing
> `pause_threshold`, `energy_threshold = 1100`, `dynamic_energy_threshold = False` lines
> unchanged, and returns `recognizer.listen(source, timeout=10, phrase_time_limit=8)`.
> `google_transcribe(audio)` calls `sr.Recognizer().recognize_google(audio)`. The old
> `afplay(SFX_START, ...)` call is REMOVED from the moved body: `on_coin_event` now supplies it
> as `on_ready=lambda: afplay(SFX_START, wait=True, volume=3.0)`. Delete `record_and_transcribe`
> and `record_and_transcribe_with_timeout`. In `on_coin_event`, replace the capture call with
> `result = capture_client.capture_question(_get_audio, _transcribe, on_ready=...)`, then log
> exactly one line `capture outcome=<result.outcome.value> heard="<text or empty>"
> secs=<seconds:.1f>` at INFO for HEARD and WARNING otherwise — and, when `result.detail` is
> not None (every failure), append ` detail="<result.detail>"` to that same line so the operator
> can see *which* mic or recognizer error it was. Do not round `secs` beyond one decimal: on an
> `overrun` it reports the true stall duration, not the guard, and that is diagnostic. If `result.text` is falsy,
> substitute the persona default as today and log `question source=substituted text="<default>"`;
> otherwise log `question source=heard text="<text>"`. Replace the `get_ai_response(question)`
> call inside `generate_fortune` with `_fortune(question)`, and have `main()` call
> `configure_providers(mic_get_audio, google_transcribe, get_ai_response, None)` for now
> (`audio_out` is wired in Step 7). Write `tests/test_on_coin_event.py` FIRST: it calls
> `configure_providers` with `get_audio=lambda on_ready: (_ for _ in ()).throw(
> sr.WaitTimeoutError())` (or a small def that raises), a `FakeTranscriber`, a `FakeFortune`,
> and `FakeAudioOut()`, sets `serial_trigger._config` via `load_config("default")`, runs
> `on_coin_event(pulses=1, dry_run=True)` with `caplog` at INFO, and asserts the log contains
> `outcome=no_speech` and `source=substituted` and the persona's `default_question`. A second
> test uses `get_audio=lambda on_ready: SENTINEL` and a
> `FakeTranscriber("Will I find treasure today?")` and asserts `outcome=heard` and
> `source=heard text="Will I find treasure today?"`. Run → RED → implement → GREEN.

**What to build**: modify `serial_trigger.py` (providers, `configure_providers`,
`mic_get_audio`, `google_transcribe`, `on_coin_event`, `generate_fortune`, `main()`);
`tests/test_on_coin_event.py`.

**Test first**: two tests — a substituted run is recorded as substituted with its cause; a heard
run records the heard text. These are Acceptance Criteria 1 and 2 made concrete.

**Validation**:
- [Automated]: `.venv/bin/python -m pytest -q` → all passing; `compileall` clean.
- [Manual]: `--mode simulate --dry-run`, press Enter, stay silent → after ~10s the log shows
  `capture outcome=no_speech` then `question source=substituted text="What is my fortune for
  today?"` and a ticket prints to the terminal. This still calls OpenAI once.

---

### Step 6 — Replay a clip or typed text, offline

> **Prompt**: Implement Step 6 of `_work/capture-measure-and-fix/plan.md`. In
> `capture_client.py` add `wav_get_audio(path)` returning a one-arg callable `_(on_ready)` that
> calls `on_ready()`, then opens `sr.AudioFile(path)` and returns `recognizer.record(source)`
> (an `AudioData`) — calling `on_ready` keeps the tester's experience the same as an attendee's
> (the chime plays) and keeps the cue observable in tests. In `fakes.py` add
> `typed_get_audio(text)` returning a one-arg callable that calls `on_ready()` and returns the
> sentinel string `text`; note in its docstring that it must be paired with
> `FakeTranscriber(text)`. In `serial_trigger.py` add argparse flags `--offline` (store_true),
> `--clip PATH`, `--question TEXT`, valid only with `--mode simulate`; in `main()`, when
> `--offline`: transcribe = `FakeTranscriber(args.question or "What is my fortune?")` and
> fortune = `FakeFortune()`; when `--clip`: get_audio = `wav_get_audio(args.clip)`; when
> `--question`: get_audio = `typed_get_audio(args.question)` and transcribe =
> `FakeTranscriber(args.question)`. Write `tests/test_replay.py` FIRST: (a) generate a 1-second
> 16 kHz mono silent WAV into `tmp_path` with the stdlib `wave` module, and assert
> `wav_get_audio(path)(lambda: None)` returns an `sr.AudioData`; (b) with providers configured
> as `--offline --question "Should I take the job?"` would set them, run `on_coin_event(1,
> dry_run=True)` twice under `caplog` and assert the two `capture ...` lines are identical and
> both contain `text="Should I take the job?"`, and assert `FakeFortune.questions` has two
> entries — proving no real fortune call happened. Run → RED → implement → GREEN.

**What to build**: modify `capture_client.py` (`wav_get_audio`), `fakes.py`
(`typed_get_audio`), `serial_trigger.py` (three flags, `main()` wiring);
`tests/test_replay.py`.

**Test first**: a WAV becomes audio; the same typed question twice yields identical records and
spends nothing. Acceptance Criteria 4 and 5.

**Validation**:
- [Automated]: `.venv/bin/python -m pytest -q` → all passing.
- [Manual]: `.venv/bin/python serial_trigger.py --mode simulate --dry-run --offline --question
  "Should I take the job?"`, press Enter → a ticket prints to the terminal with the fake fortune,
  no network, and the log shows `source=heard text="Should I take the job?"`. Then record a
  short WAV of yourself asking a question (QuickTime → export, or `sox`), run with `--clip
  that.wav --offline` and confirm the run completes; run with `--clip that.wav` (no `--offline`)
  and confirm the real recogniser transcribes it — this is the first time a recorded question
  has gone through Narly on a desk.

---

### Step 7 — In-process playback replacing `afplay`

> **Prompt**: Implement Step 7 of `_work/capture-measure-and-fix/plan.md`. Add `pygame>=2.5,<3`
> AND `pyaudio>=0.2.14,<0.3` to `requirements.txt`, then `.venv/bin/pip install -r
> requirements.txt`. `pyaudio` is what lets `sr.Microphone()` open at all — it is missing from the
> venv today, so the real mic cannot open on this laptop and Step 8's manual check would be
> impossible. If the `pyaudio` wheel fails to build on macOS, run `brew install portaudio` first
> and retry; on the Pi the equivalent is `apt install portaudio19-dev`, which the deploy script
> already lists. Confirm with `.venv/bin/python -c "import pyaudio; print(pyaudio.__version__)"`. Create `audio_out.py` at the repo root with class `PygameAudioOut`:
> `__init__` tries `import pygame` and `pygame.mixer.init()`, and on any failure sets
> `self.available = False` and logs one WARNING `audio_out unavailable: <reason>`; `play(path,
> wait=False)` returns immediately if not available or if `path` does not exist (logging a
> WARNING `sfx missing: <path>` in the latter case), otherwise loads and plays via
> `pygame.mixer.music` at volume 1.0 and, if `wait`, blocks until `pygame.mixer.music.get_busy()`
> is false; `is_busy()` wraps `get_busy()`. In `serial_trigger.py` delete the `afplay` function
> and its `subprocess` import if now unused; change `on_coin_event`'s `on_ready` lambda to
> `lambda: _audio_out.play(SFX_START, wait=True)` and replace `afplay(SFX_END)` with
> `_audio_out.play(SFX_END)`; have `main()` pass `PygameAudioOut()` as the fourth
> `configure_providers` argument. Write `tests/test_audio_out.py` FIRST: (a) configure providers
> as in Step 5's heard test but with `get_audio=lambda on_ready: (on_ready(), SENTINEL)[1]` and a
> `FakeAudioOut`; run `on_coin_event(1, dry_run=True)` and assert `FakeAudioOut.played` is
> exactly `[(SFX_START, True), (SFX_END, False)]` in that order; (b)
> `PygameAudioOut().play("/nonexistent.mp3")` does not raise and emits the `sfx missing` WARNING
> under `caplog`. Run → RED → implement → GREEN. Note for Key Decisions: pygame volume is
> 0.0–1.0, so the old `afplay -v 3.0` amplification is lost; physical speaker volume compensates.

**What to build**: `audio_out.py`; modify `requirements.txt` (add `pygame` and `pyaudio`),
`serial_trigger.py`; `tests/test_audio_out.py`.

**Test first**: the two cues are requested in order with the right blocking; a missing file
degrades and logs rather than raising. Acceptance Criterion 8's software half.

**Validation**:
- [Automated]: `.venv/bin/python -m pytest -q` → all passing; `.venv/bin/python -c "import pyaudio"`
  exits 0 (the mic can open again — prerequisite for Step 8's manual check).
- [Manual]: `--mode simulate --dry-run --offline --question "test"`, press Enter → the chime is
  audible from the laptop speaker, then the thinking cue. If a Linux machine is available, the
  same command plays both cues there — that is the criterion; if not, defer this check to the Pi
  increment and say so.

---

### Step 8 — Sequencing and threshold

> **Prompt**: Implement Step 8 of `_work/capture-measure-and-fix/plan.md`. In
> `serial_trigger.py`'s `mic_get_audio(on_ready, recognizer=None, mic=None)`: (1) REORDER so that
> inside `with mic as source:` the sequence is `recognizer.adjust_for_ambient_noise(source,
> duration=0.5)` → `on_ready()` → `return recognizer.listen(source, timeout=10,
> phrase_time_limit=8)`, with nothing between `on_ready()` returning and `listen` being called —
> today `on_ready()` fires before calibration, which is the 0.8s dead window; (2) DELETE the
> lines `recognizer.energy_threshold = 1100` and `recognizer.dynamic_energy_threshold = False`
> and their comments, leaving the library defaults (300, dynamic on); keep
> `recognizer.pause_threshold = 1.5`. Write `tests/test_sequencing.py` FIRST using a small
> recording `FakeRecognizer` (methods `adjust_for_ambient_noise(source, duration)` and
> `listen(source, **kw)` that append `"calibrate"` / `"listen"` to a shared `events` list, the
> latter returning a sentinel; attributes `energy_threshold=300`,
> `dynamic_energy_threshold=True`, `pause_threshold=0.8`) and a `FakeMic` usable as a context
> manager; call `mic_get_audio(on_ready=lambda: events.append("cue"), recognizer=fake,
> mic=FakeMic())` and assert `events == ["calibrate", "cue", "listen"]`; and assert afterwards
> that `fake.energy_threshold == 300` and `fake.dynamic_energy_threshold is True` — nothing
> overrode them — and `fake.pause_threshold == 1.5`. Run → RED (today's order is
> `["cue", "calibrate", "listen"]` and the threshold is overridden) → implement → GREEN.

**What to build**: modify `serial_trigger.py` (`mic_get_audio`, `on_coin_event`);
`tests/test_sequencing.py`.

**Test first**: calibrate → cue → listen, in that order, with nothing between cue-end and
listen; library threshold and adaptation untouched. Acceptance Criteria 6 and 7's software half.

**Validation**:
- [Automated]: `.venv/bin/python -m pytest -q` → all passing; `compileall` clean.
- [Manual, when the mic is available]: stand at arm's length, `--mode simulate --dry-run`, press
  Enter, wait for the chime to END, speak a question at conversational volume without leaning
  in. Confirm `outcome=heard` and that the transcript begins with your first word. Then repeat
  saying nothing → `outcome=no_speech` after ~10s. This is the check the whole increment exists
  to make possible; record the result in the spec's open-questions section.

---

### Step 9 — Runbook, config slots, and dependency hygiene

> **Prompt**: Implement Step 9 of `_work/capture-measure-and-fix/plan.md`. Documentation and
> config only; no behaviour changes. (1) Create `docs/testing.md`: how to run the tests
> (`.venv/bin/pip install -r requirements-dev.txt`; `.venv/bin/python -m pytest -q`); how a
> remote tester runs a fortune with no hardware (`--mode simulate --dry-run --offline --question
> "..."`, and with `--clip`); how to read the log and count a day's outcomes (`grep -c
> 'outcome=no_speech' narly.log`, one line per outcome kind); what `--log-file` does and that
> retention is undecided. Write it for someone new to Python — spell out the commands. (2) Update
> `.agents/config/stack.md`: replace the *Tests* section to say pytest is the runner, where tests
> live, the command, and that Step 1 of this plan set the convention; add the pytest command to
> *Build*. (3) Update `.agents/config/conventions.md` → *Planning gotchas*: change "There is no
> test suite" to say a pytest suite exists for hardware-free paths and that hardware paths
> (mic, Arduino, printer) remain manual. (4) Update `.env.example` with a commented
> `# LOG_FILE is a CLI flag: --log-file path` note. (5) Confirm `requirements.txt` has `pygame` and
> `pyaudio` (from Step 7) and note `textwrap3` is unused but leave its removal to the housekeeping item in
> ROADMAP *Later*. (6) Parametrize `test_render_ticket_never_exceeds_thermal_printer_width` over
> `list_personas()` so every persona's header and footer are checked against the 32-character
> width, not only `default` — `render_ticket`'s `center()` does not truncate, so an over-long
> header in one persona would slip past a test that checks another. Run `.venv/bin/python -m pytest -q` and `--list-personas` to confirm nothing
> moved.

**What to build**: `docs/testing.md`; modify `.agents/config/stack.md`,
`.agents/config/conventions.md`, `.env.example`.

**Validation**:
- [Automated]: `.venv/bin/python -m pytest -q` → all passing (unchanged count).
- [Manual]: a colleague following `docs/testing.md` alone can run a fortune offline on their
  machine. That is the remote-tester requirement; if you can, actually hand it to someone.

---

### Final — Record the durable behavior *(a spell you cast, not an implement-step)*

**Do not number this as an implementation step.** It is cast directly after the implement-step
loop finishes.

> **Prompt**: Run `/feature update audio-capture`. Fold **only** the operator- and
> attendee-observable behavior changes from this work into `_features/audio-capture.md` — do not
> create a new feature doc. Specifically: listening now begins the instant the readiness chime
> ends (reword the spec's "as the chime starts" scenario to "as the chime ends" and say why in the
> revision note); Narly wakes to an ordinary voice and adapts to the room; what was heard, or
> which of the five failures occurred, and whether the question was substituted, is on the record;
> a tester can run a fortune with no hardware from a clip or typed text. Move Open Issues 1 and 4
> (discarded calibration, dead window) to resolved with the commit that fixed them; leave Open
> Issues 2, 3, and 5 open with a note on what this increment changed about each (3: failures are
> now distinguishable in the log even though the ticket is unchanged; 5: the log now exists to
> diagnose hangs). Fill the coverage table with real `tests/test_*.py:L<n>` references for the
> scenarios the new tests prove; leave hardware-only scenarios `Not covered` with the manual
> check named. Leave architecture criteria — the test harness, the fakes' internals — in the
> shipped spec; they are point-in-time and must not appear as Rules. Add a revision note dated
> today. Also reconcile the spec's "the operator's live view behaves as it does today" with
> what is now true: every terminal line carries a timestamp and level, and the blank lines
> between cycles are gone (the `💰 [COIN EVENT]` line is the anchor). Say so plainly rather
> than leaving a sentence that is no longer accurate.
>
> **Validation**: The capability doc describes current behavior with no transition-style Rules;
> no new feature doc was added; every `Covered` row points at a test that exists and passes.

---

## File Summary

| Action | File |
|--------|------|
| Create | `requirements-dev.txt` |
| Create | `pyproject.toml` |
| Create | `tests/__init__.py` |
| Create | `tests/test_smoke.py` |
| Create | `logger.py` |
| Create | `tests/test_logger.py` |
| Create | `fakes.py` |
| Create | `tests/test_fakes.py` |
| Create | `capture_client.py` |
| Create | `tests/test_capture_client.py` |
| Create | `tests/test_on_coin_event.py` |
| Create | `tests/test_replay.py` |
| Create | `audio_out.py` |
| Create | `tests/test_audio_out.py` |
| Create | `tests/test_sequencing.py` |
| Create | `docs/testing.md` |
| Modify | `serial_trigger.py` |
| Modify | `config_loader.py` |
| Modify | `requirements.txt` |
| Modify | `.env.example` |
| Modify | `.agents/config/stack.md` |
| Modify | `.agents/config/conventions.md` |
| _(work type: `change-to audio-capture`)_ Update | `_features/audio-capture.md` (fold observable behavior only; **no new file**) |
