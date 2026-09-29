# Plan: Live Baseline

**Spec**: `_work/live-baseline/spec.md`
**Branch**: `feature/live-baseline`
**Work type**: change-to audio-capture
**Feature doc**: audio-capture

## Context

This increment takes the first real reading of how often Narly hears attendees correctly, using
the Fifine AM8. It also sets up a replay set so every later iteration is scored the same way. It is
deliberately lean: at every choice it takes the simpler path. A baseline and a way to track it are
the goal, not hitting 60% before the event.

The work builds on Increment 1:
- the one-line `capture outcome=` log record
- `capture_question(get_audio, transcribe)` in `capture_client.py`, which never raises
- `wav_get_audio(path)`, which turns a WAV file into audio a recognizer can read
- `google_transcribe`, the real recognizer (Google's free endpoint, no key or cost)
- the provider seam `build_providers(args)` → `configure_providers(...)` in `serial_trigger.py`

The unit of work is one increment. The software is small: save clips during a session, score a
session's log, replay clips, and one mechanical "heard correctly" rule. The rest is a runbook and
a measuring session the owner runs at the booth.

---

## Key Decisions

- **Lean by the owner's rule.** At every choice, take the simpler path, and never plan in time
  estimates. The spec's "decided while writing" list is binding here: recorded crowd noise, the
  mechanical match, clips saved by Narly in one pass, the mic check as a checklist line, and early
  wake-ups noted by watching.
- **One new module, `baseline.py`, at the root.** It holds the match rule, the scorer, and a small
  command-line interface with two subcommands, `live` and `replay`. This follows `paths.md`'s flat
  layout. It is not a `<thing>_client.py`, because it drives no device. It is run as
  `.venv/bin/python baseline.py <subcommand> …`. Tests go in `tests/test_baseline.py`.
- **"Heard correctly" rule.** Lowercase both strings, replace every character that isn't a letter,
  digit, or space with a space, collapse runs of spaces, and trim. Correct means the two results
  are equal. A missing or blank transcript is never correct. Nothing fuzzier: the rule must not
  drift between iterations.
- **Kinds of miss.** A miss is either one of the five failure outcomes (`no_speech`,
  `not_understood`, `mic_error`, `overrun`, plus `recognizer_error`, which is handled separately),
  or `misheard`: outcome `heard`, but the words don't match. `misheard` is the only new label. It
  is the "near miss" the spec wants listed.
- **Unreachable is excluded.** A `recognizer_error` run is counted and reported on its own line,
  and left out of every percentage's denominator.
- **Hitting the cap.** A run counts as having hit the 8-second cap when its saved clip lasts
  **7.9 seconds or more**. That is `phrase_time_limit=8` at `serial_trigger.py:147`, less a tenth
  of a second for chunk rounding. The length is read from the WAV (frames ÷ rate) with the
  standard `wave` module. A run with no clip is not counted as hitting the cap.
- **Saving clips: a `--save-clips DIR` flag, simulate mode only.** It wraps the real mic provider,
  and nothing else changes. With the flag, the simulate prompt accepts typed text before Enter.
  That text is the clip's **label**, the script's question number. A blank label takes the next
  number in sequence. `--save-clips` is refused, via `parser.error`, together with `--offline`,
  `--clip`, or `--question`, because a typed question or a replayed clip gives no new audio worth
  saving. **Without the flag, `build_providers` returns `mic_get_audio` unwrapped**, so a normal
  run saves nothing.
- **Where the label travels.** A module-level `_clip_label` in `serial_trigger.py` is set by
  `simulate_mode` from the prompt's typed text, before each `on_coin_event`. The wrapper reads it
  through a `label_source` callable. This is the same module-global pattern as `_config` and the
  providers. `on_coin_event`'s signature is unchanged.
- **The saving wrapper lives in `capture_client.py`,** next to `wav_get_audio`, as
  `clip_saving_get_audio(inner, directory, label_source)`. It logs `clip id=<label>` **before**
  calling the inner provider, so a run that fails before any audio (for example `no_speech`) is
  still labelled in the log. When audio comes back, it writes `<directory>/<label>.wav` from
  `AudioData.get_wav_data()` and logs `clip saved id=<label> path=<path>`. It never changes the
  audio or the exceptions it passes along. A failure to write the file is logged as a WARNING and
  does not stop the fortune.
- **The live score is read from the session's log**, as the spec says. `baseline.py live LOG
  SCRIPT --clips DIR` pairs each `clip id=<label>` line with the next `capture outcome=` line. The
  `capture` line format is Increment 1's fixed contract, and `heard="…"` has been flattened, so a
  regular expression on `outcome=(\S+)` and `heard="([^"]*)"` is enough. The session must run with
  `--log-file`.
- **The replay never touches the fortune code.** `baseline.py replay CLIPDIR SCRIPT` calls
  `capture_question(wav_get_audio(path), transcribe)` for each script row that has a clip.
  `transcribe` defaults to `serial_trigger.google_transcribe` and can be injected for tests. The
  replay never imports or calls `ai_client`, so "no fortune cost" holds by construction. Script
  rows with no clip (nothing was captured live) are listed as "no clip" and left out of the replay
  percentages.
- **The script is `docs/baseline-script.csv`,** with columns `id,condition,question`, and is
  committed. `condition` is one of `quiet`, `conversation`, `leaning`. The same 20 questions are
  asked in each condition: ids 1–20 quiet, 21–40 conversation, 41–60 leaning. That is the lean
  choice: one list to write, and the three conditions stay directly comparable.
- **Clips live in `clips/` at the repo root.** `.gitignore` ignores the whole folder, so
  neither a clip nor a session log (which holds volunteers' words) can be committed by accident. They are copied to the Pi when the Pi
  port re-runs the set, which is already in the roadmap's Increment 3.
- **Replayed clips can only measure the recognizer, never the endpointing.** A saved clip starts
  when listening started and stops where endpointing stopped it. This is accepted in the spec
  (Edge Cases). Increment 4 will need raw recordings for its voice-detection work.
- **Output is Markdown on stdout,** ready to paste into the results file. No file writing, and no
  JSON. The owner reads the output and pastes it.
- **The results and the runbook are one file, `docs/capture-baseline.md`.** It holds the setup
  checklist, the session procedure, the scoring commands, and the dated results entries. One file
  is the lean choice, and it is evergreen, so it belongs in `docs/`.
- **The session is not an implement-step.** It needs a person, a mic, and volunteers, typing into
  a plain terminal, so it is listed after the numbered steps for the owner to run. It is not
  something to dispatch.
- **Commands:**
  - tests: `.venv/bin/python -m pytest -q`
  - compile check: `.venv/bin/python -m compileall -q *.py`
  - smoke check: `.venv/bin/python serial_trigger.py --list-personas`

  All three are from `stack.md` → *Build*. No new dependency: `wave`, `csv`, `re`, and `argparse`
  are in the standard library.

---

## Steps

Each step is designed to be completed independently in its own context window.
The step heading contains a ready-to-use prompt you can paste into a new session.

---

### Step 1 — The "heard correctly" rule

> **Prompt**: Implement Step 1 of `_work/live-baseline/plan.md`. Create `baseline.py` at the repo
> root with one function, `heard_correctly(asked: str, heard: str | None) -> bool`. It lowercases
> both strings, replaces every character that is not a letter, digit, or space with a space,
> collapses repeated spaces, and trims. It returns True only when the two normalised strings are
> equal and not empty. `None` or blank `heard` returns False. Write `tests/test_baseline.py` FIRST
> with three tests:
> - (a) `"Will I find treasure today?"` vs `"will I find treasure today"` → True
> - (b) `"Should I take the job?"` vs `"should I bake the job"` → False
> - (c) any question vs `""` and vs `None` → False
>
> Run `.venv/bin/python -m pytest -q tests/test_baseline.py`, confirm RED (import error, then
> failing assertions), implement, and confirm GREEN. Add a module docstring saying the rule is
> mechanical on purpose, so every iteration is scored the same way.

**What to build**: `baseline.py` (new, one function); `tests/test_baseline.py` (new).

**Test first**:
- `tests/test_baseline.py` asserts the three examples above, through `heard_correctly` only.
- Run the test command and confirm RED before implementing.

**Validation**:
- [Automated]: `.venv/bin/python -m pytest -q`. The whole suite passes, with 3 new tests.

---

### Step 2 — Score a set of results

> **Prompt**: Implement Step 2 of `_work/live-baseline/plan.md`. In `baseline.py`, add a small
> `Row` dataclass (`id`, `condition`, `asked`, `outcome`, `heard`, `clip_seconds: float | None`)
> and two functions: `score(rows) -> Summary` and `to_markdown(summary, title) -> str`. Use
> `heard_correctly` from Step 1.
>
> `score` counts:
> - rows heard correctly: outcome `heard` and the words match
> - misses by kind: each failure outcome, plus `misheard` for outcome `heard` with non-matching
>   words
> - `recognizer_error` rows as **unreachable**, excluded from every denominator
> - the share correct overall and for each condition
> - rows with `clip_seconds >= 7.9` as having hit the cap
> - a list of misses with id, asked, and heard
>
> `to_markdown` renders all of that as a short Markdown block for pasting into
> `docs/capture-baseline.md`.
>
> Write the tests FIRST in `tests/test_baseline.py`, one behavior at a time, each RED then GREEN:
> - (a) the spec's example: 60 rows, 42 correct (18 quiet, 11 conversation, 13 leaning) gives 70%
>   overall and 90%, 55%, 65% by condition
> - (b) 4 `recognizer_error` rows out of 60 are reported as unreachable, and the share is out of 56
> - (c) outcome `heard` with wrong words is counted as `misheard` and listed with both strings
> - (d) a row with `clip_seconds=8.0` counts as hitting the cap, 7.5 doesn't, and `None` doesn't
> - (e) the Markdown contains the overall share and each condition's share
>
> Build rows directly in the tests; no files. Run `.venv/bin/python -m pytest -q`.

**What to build**: `baseline.py` (`Row`, `Summary`, `score`, `to_markdown`); tests added to
`tests/test_baseline.py`.

**Test first**:
- Each of (a)–(e) is written and seen failing before the code that makes it pass.
- Assert on what `score` returns and what the Markdown contains, never on internals.

**Validation**:
- [Automated]: `.venv/bin/python -m pytest -q`. All pass.

---

### Step 3 — Save what Narly heard during a measuring session

> **Prompt**: Implement Step 3 of `_work/live-baseline/plan.md`.
>
> In `capture_client.py`, add `clip_saving_get_audio(inner, directory, label_source)`. It returns
> a one-argument provider `_(on_ready)` that:
> - logs INFO `clip id=<label>`, where the label comes from `label_source()`, before calling
>   `inner(on_ready)`
> - on success, writes `<directory>/<label>.wav` from `audio.get_wav_data()`, creating
>   `directory` if needed, logs INFO `clip saved id=<label> path=<path>`, and returns the same
>   `audio` object
> - lets any exception from `inner` pass through untouched, saving nothing
> - on a failed write, logs a WARNING `clip not saved id=<label>: <reason>` and still returns the
>   audio
>
> In `serial_trigger.py`:
> - Add module global `_clip_label = None`.
> - Add a `--save-clips DIR` argument. Refuse it with `parser.error` unless `--mode simulate`, and
>   when combined with `--offline`, `--clip`, or `--question`.
> - In `build_providers`, when `args.save_clips` is set, wrap the mic provider:
>   `clip_saving_get_audio(mic_get_audio, args.save_clips, lambda: _clip_label)`. Without the flag,
>   return `mic_get_audio` unwrapped. Existing tests build `argparse.Namespace` objects with no
>   `save_clips`, so read it as `getattr(args, "save_clips", None)`.
> - In `simulate_mode`'s Enter loop, keep the text typed at the prompt. When clip saving is on,
>   set `_clip_label` to the stripped text, or to the next number in a per-session counter if the
>   text is blank.
>
> Write the tests FIRST in `tests/test_clip_saving.py`:
> - (a) with an inner provider returning a real `sr.AudioData` (1 s of 16 kHz silence), the
>   wrapper writes `<tmp>/27.wav` when the label is `"27"`, and the file is a readable WAV;
>   `caplog` shows `clip id=27` before `clip saved id=27`
> - (b) an inner provider raising `sr.WaitTimeoutError` → the same exception propagates, no file is
>   written, and `clip id=27` is still logged
> - (c) `build_providers` on `Namespace(offline=False, clip=None, question=None, save_clips=None)`
>   returns `mic_get_audio` itself: a normal run saves nothing
>
> Run RED → implement → GREEN with `.venv/bin/python -m pytest -q`. Also run
> `.venv/bin/python -m compileall -q *.py` and `--list-personas`.

**What to build**: modify `capture_client.py` (`clip_saving_get_audio`) and `serial_trigger.py`
(`_clip_label`, `--save-clips`, the wrap in `build_providers`, the typed label in
`simulate_mode`); create `tests/test_clip_saving.py`.

**Test first**:
- (a)–(c) above, one at a time, each seen failing first.
- The tests never open a microphone: the inner provider is a lambda.

**Validation**:
- [Automated]: `.venv/bin/python -m pytest -q` all pass; `compileall` clean; `--list-personas`
  prints three personas.
- [Manual]: the owner runs this in a plain terminal, not through Claude:
  `.venv/bin/python serial_trigger.py --mode simulate --dry-run --save-clips clips --log-file clips/test.log`
  with the AM8 as the input. Type `1` at the coin prompt and press Enter, then ask a question after
  the chime. Confirm that `clips/1.wav` exists and plays (`afplay clips/1.wav`), and that the log
  shows `clip id=1`, then `clip saved id=1 path=clips/1.wav`, then the `capture` line. Delete the
  test files afterwards. This run makes one real fortune, so it needs `.env`.

---

### Step 4 — Score a session live, from its log

> **Prompt**: Implement Step 4 of `_work/live-baseline/plan.md`. In `baseline.py`, add
> `live_rows(log_path, script_path, clips_dir) -> list[Row]` and a command-line entry point using
> `argparse` subcommands. Run it as
> `.venv/bin/python baseline.py live LOG SCRIPT --clips DIR`, which prints `to_markdown(score(rows),
> "Live")`.
>
> `live_rows`:
> - reads the script CSV (`id,condition,question`)
> - walks the log in order, pairing each `clip id=<label>` line with the next line containing
>   `capture outcome=`, taking the outcome with `outcome=(\S+)` and the heard text with
>   `heard="([^"]*)"`
> - sets `clip_seconds` from `<clips_dir>/<label>.wav` when that file exists (frames ÷ rate,
>   via `wave`), otherwise `None`
>
> A label not in the script is reported on stderr and skipped. A script id asked twice uses the
> **last** pairing (a volunteer's re-ask).
>
> Write the tests FIRST in `tests/test_baseline.py`, each RED then GREEN:
> - (a) a small log text written to `tmp_path`, in the real line format from Increment 1 (copy one
>   from `docs/testing.md`), with three labelled runs (heard-correct, `no_speech`, misheard) gives
>   three rows with the right outcomes and heard text
> - (b) a re-asked label keeps only the last pairing
> - (c) `clip_seconds` comes from a WAV of known length in `tmp_path`, and is `None` when the WAV is
>   missing
>
> Run `.venv/bin/python -m pytest -q`.

**What to build**: `baseline.py` (`live_rows`, the `live` subcommand, `if __name__ == "__main__"`);
tests added to `tests/test_baseline.py`.

**Test first**:
- (a)–(c) as above, driven through `live_rows`, with real files in `tmp_path`.

**Validation**:
- [Automated]: `.venv/bin/python -m pytest -q` all pass; `compileall` clean.
- [Automated]: `.venv/bin/python baseline.py --help` lists `live`.

---

### Step 5 — Replay the clips through the real recognizer

> **Prompt**: Implement Step 5 of `_work/live-baseline/plan.md`. In `baseline.py`, add
> `replay_rows(clips_dir, script_path, transcribe=None) -> tuple[list[Row], list[str]]`. For each
> script row whose `<clips_dir>/<id>.wav` exists, it calls
> `capture_question(wav_get_audio(path), transcribe)` from `capture_client`, and builds a `Row`
> from the result's outcome and text, with `clip_seconds` from the WAV. It returns the rows, plus
> the ids that had no clip.
>
> `transcribe` defaults to `serial_trigger.google_transcribe`. Import it lazily inside the
> function, so tests can inject `FakeTranscriber` without loading the orchestrator's globals.
>
> Add the subcommand `.venv/bin/python baseline.py replay CLIPDIR SCRIPT`. It prints
> `to_markdown(score(rows), "Replay")` and then a `No clip:` line listing the missing ids.
> `baseline.py` must never import or call `ai_client`, so no fortune is ever generated.
>
> Write the tests FIRST in `tests/test_baseline.py`, each RED then GREEN, with silent WAVs written
> to `tmp_path`:
> - (a) with `FakeTranscriber("Will I find treasure today?")` and a script row asking that
>   question, the row is heard correctly
> - (b) with `FakeTranscriber(raises=sr.RequestError("down"))`, the row is `recognizer_error` and
>   `score` reports it as unreachable
> - (c) a script id with no WAV appears in the no-clip list, not in the rows
>
> Run `.venv/bin/python -m pytest -q`.

**What to build**: `baseline.py` (`replay_rows`, the `replay` subcommand); tests added to
`tests/test_baseline.py`.

**Test first**:
- (a)–(c) as above.
- The "no fortune" guarantee is structural (no `ai_client` import in `baseline.py`); state it in
  the module docstring, not in a test.

**Validation**:
- [Automated]: `.venv/bin/python -m pytest -q` all pass; `compileall` clean;
  `.venv/bin/python baseline.py --help` lists `live` and `replay`.
- [Manual]: the owner makes a clip with `say -o clips/1.wav --data-format=LEI16@16000 "Will I
  find treasure today?"`, and a one-row script `clips/test.csv` containing `id,condition,question`
  and `1,quiet,Will I find treasure today?`. Then run
  `.venv/bin/python baseline.py replay clips clips/test.csv`, which needs the network. Confirm the
  output shows 1 of 1 heard correctly (or a visible `misheard` with the words), and that no fortune
  or ticket appeared. Delete the test files afterwards.

---

### Step 6 — The runbook, the script, and the results file

> **Prompt**: Implement Step 6 of `_work/live-baseline/plan.md`. Documentation only; no code.
>
> Create `docs/baseline-script.csv` with header `id,condition,question` and 60 rows. Write 20
> short, distinct fortune-teller questions, 4–8 words each, the kind attendees ask (for example
> "Will I find treasure today?", "Should I take the job?"). Use them for ids 1–20 (`quiet`), the
> same 20 in the same order for 21–40 (`conversation`), and again for 41–60 (`leaning`).
>
> Create `docs/capture-baseline.md`, written for the owner and volunteers, who are new to Python,
> using the `prose-discipline` skill. It has these sections:
> - **Setup checklist**: mount the AM8 on its stand up by Narly, aimed at where an attendee's
>   mouth will be. Record the height, distance, and angle, and the gain knob position. Set the
>   Mac's input to the AM8 (System Settings → Sound → Input), and check the level meter moves at
>   arm's length. Pick a crowd-noise recording, and a phone volume for it, and note both.
> - **Running the session**: in a plain terminal, not through Claude, run
>   `.venv/bin/python serial_trigger.py --mode simulate --dry-run --save-clips clips --log-file clips/session.log`.
>   At each coin prompt, type the question's id from the script, press Enter, and have the
>   volunteer ask it after the chime ends. Volunteers say the question exactly as written, without
>   "Narly" first: the scoring is word for word, and Google hears the name as "gnarly", so a
>   perfectly heard question would score as a miss. This is only for the session; attendees can
>   say anything. Conditions go in id order. If a volunteer goes off
>   script, re-type the same id and ask again (the last attempt counts). Note it needs `.env`,
>   because each coin makes a real fortune. For the chime check: during the conversation block, a
>   volunteer at the attendee's spot says clearly, faintly, or not at all. Note early wake-ups seen.
> - **Scoring**: `.venv/bin/python baseline.py live clips/session.log docs/baseline-script.csv --clips clips`
>   and `.venv/bin/python baseline.py replay clips docs/baseline-script.csv`.
> - **Re-running later**: after any change, replay the same `clips/` against the same script. Copy
>   `clips/` to the Pi for the Pi-port rerun. The clips are volunteers' voices and the log
>   holds their words, so neither is ever committed; `clips/` is git-ignored.
> - **Results**: an empty dated-entry template with the setup, the conditions, the Live and Replay
>   Markdown blocks, the chime verdict, and early wake-ups noted. Future entries are added
>   underneath.
>
> Add a one-line pointer to `docs/capture-baseline.md` in `docs/testing.md`'s real-microphone
> section. Run `.venv/bin/python -m pytest -q` to confirm nothing moved.

**What to build**: `docs/baseline-script.csv` (new); `docs/capture-baseline.md` (new);
`docs/testing.md` (one-line pointer).

**Validation**:
- [Automated]: `.venv/bin/python -m pytest -q` all pass. The script parses:
  `.venv/bin/python -c "import csv; r=list(csv.DictReader(open('docs/baseline-script.csv'))); print(len(r), {x['condition'] for x in r})"`
  prints `60 {'quiet', 'conversation', 'leaning'}` (the set's order may vary).
- [Manual]: every command in `docs/capture-baseline.md` matches `serial_trigger.py --help` and
  `baseline.py --help`.

---

### Session — the measuring session *(run by the owner, not an implement-step)*

Not numbered, because it needs a person at the booth typing into a plain terminal. Follow
`docs/capture-baseline.md`:
1. Do the setup checklist.
2. Run the 60 scripted questions.
3. Do the chime check.
4. Run `live` and `replay`.
5. Paste both Markdown blocks, the chime verdict, and any early wake-ups into a dated entry under
   **Results**.
6. Commit `docs/capture-baseline.md`. The clips stay local.

This covers acceptance criteria 2, 5, 6, and 7. Criterion 8 (the Pi rerun) is already on the
roadmap.

---

### Final — Record the durable behavior *(a spell you cast, not an implement-step)*

**Do not number this as an implementation step.** It is cast directly, `/feature update
audio-capture`, after the implement-step loop and the session.

> **Prompt**: Run `/feature update audio-capture`. Fold **only** the operator-observable behavior
> changes from this work into the existing capability doc; do not create a new feature doc.
>
> The behavior changes:
> - during a measuring session, Narly can save what it heard on each coin as a clip, labelled by
>   the question number typed at the prompt
> - a normal run saves nothing
> - a set of saved clips can be replayed through the real recognizer and scored, with no fortune
>   generated
> - a session's log can be scored against its script
>
> Also update the evidence:
> - record the baseline's results against the "adjusts to the room" scenario
> - update Open Issue 7 with the chime verdict
> - update Open Issue 6: the replay set now shows what the recognizer hears in a clip, run online
> - add the 8-second-cap count as an observation on "A long-winded question is cut off"
>
> Leave the scoring rule's internals and the session procedure in the shipped spec and in
> `docs/capture-baseline.md`; they are not Rules. Add a revision note dated today describing what
> changed.
>
> **Validation**: The capability doc describes current behavior with no transition-style ("goes
> from… to…") Rules; no new feature doc was added; every `Covered` row points at a test that
> exists and passes.

---

## File Summary

| Action | File |
|--------|------|
| Create | `baseline.py` |
| Create | `tests/test_baseline.py` |
| Create | `tests/test_clip_saving.py` |
| Modify | `capture_client.py` (`clip_saving_get_audio`) |
| Modify | `serial_trigger.py` (`_clip_label`, `--save-clips`, `build_providers`, `simulate_mode`) |
| Create | `docs/baseline-script.csv` |
| Create | `docs/capture-baseline.md` |
| Modify | `docs/testing.md` (one-line pointer) |
| Update | `_features/audio-capture.md` (fold observable behavior only; **no new file**) |
