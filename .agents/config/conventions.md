# Conventions

## Branch naming

`feature/<slug>` — one branch per increment, cut from `main` and merged back, e.g.
`feature/phase-3a-logging`.

Adopted at setup (2026-09-14) rather than inferred: the history shows work committed straight to
`main`, and the only other branch, `backup-before-author-rewrite`, is a one-off safety branch.
This is the convention going forward, not a description of the log.

`origin` is `https://github.com/robot-denny/NarlyFortuneTeller.git`. No remote is off-limits.

## Commit format

Plain prose, no type prefixes, no emoji, no ticket references. Sentence-style, mostly past
tense describing what changed, subject only — the history has no bodies.

Observed in `git log --oneline -30`:

```
Add MIT license
updated requirements.txt to include speechRecognition
updated narly prompts and personality options
LEDs hooked up and working
Removed unused files, organized code base, and added the arduino files to the repo
```

Capitalisation is inconsistent (`Add`, `updated`, `Removed`) and subject length runs long — up
to ~85 characters. Match the plain-prose style; do not import conventional-commit prefixes the
project has never used.

## Commit trailers

The project has no trailer convention of its own — 29 of the last 30 commits carry none.

The single exception, `efcf25f`, carries `Co-Authored-By: Claude Opus 5 (1M context)`, which is
agent attribution on an agent-authored commit rather than a project practice. Add that trailer
to agent-authored commits; add nothing to human ones.

## Unit of work

A **sub-phase** from `docs/v2-upgrade-plan.md` — `3a` "Add proper logging", `3b` "Watchdog
wrapper", `4c` "Update led_client.py" — not a whole phase. Each names one deliverable, usually
one or two modules, and carries its own verification.

Phases are the shipping unit: the plan states "each phase is independently testable and
shippable," and the owner works them strictly in order, verifying one before starting the next.
So a phase is the roadmap entry; a sub-phase is the increment.

A slice routinely spans the Python orchestrator, a client module, the Arduino sketch, and the
persona content — Phase 4 changes all four at once. Treat the sketch as part of the slice even
though no automated command covers it.

## Planning gotchas

- **Paths resolve relative to the file, not the working directory.** `config_loader.py` uses
  `_BASE_DIR` to find `personas/` and `sfx/`. A plan that moves a module, or introduces a
  package directory, silently breaks persona and SFX loading without any import error.
- **Run from the repo root.** The README's `python NarlyFortuneTeller/serial_trigger.py` form
  is stale — the modules are at the root. A plan that quotes the README's commands will quote
  paths that do not exist.
- **A persona is a directory with both files.** `personas/<name>/` needs `content.json` *and*
  `prompts.md`; `content.json` points at the prompts file. Adding one without the other yields
  a persona that lists but fails to load. `default` is the fallback and must keep working.
- **The ticket is 32 characters wide.** `formatters.py` wraps to the Maikrt 58mm printer's
  width. Any change to fortune length, headers, or footers is constrained by it, and the
  constraint is invisible in `--dry-run` output unless you count.
- **The serial port is hardcoded and has already drifted once.** Phase 2 changed
  `/dev/cu.usbmodem143101` → `143301`. It varies by machine and USB port; `--port` overrides it.
  Do not plan around the literal value.
- **The Arduino sketch has no automated build.** No `arduino-cli` is installed. Any `.ino`
  change needs a manual IDE flash and an on-device smoke test — plan that as an explicit step,
  because no command in `stack.md` will catch a broken sketch.
- **There is no test suite.** Every verification step is a manual run. A plan cannot lean on a
  RED→GREEN signal that does not exist; say what you will observe by hand instead.

## Implementation rules

- **Explain clearly — the owner is new to Arduino, Raspberry Pi, and Python.** From `CLAUDE.md`
  § *User notes*. Wiring and hardware steps especially: name the pin, the colour, and the
  reason. `docs/v2-upgrade-plan.md` sets the register with its photo-guided, numbered steps.
- **Finish and verify one phase before starting the next.** Also from `CLAUDE.md`. Do not
  bundle work from a later phase into the current one; Phase 2 was explicitly *trimmed* rather
  than expanded when an event deadline hit, and the deferred scope became Phase 4.
- **Degrade gracefully when hardware is absent.** `led_client.py` already does this when no
  Arduino is connected. Simulation (`--mode simulate`) and `--dry-run` must keep working with
  nothing plugged in — that is the only way the project is testable at a desk.
- **Every failure path still prints a fortune.** If STT, the API, or the printer fails, a
  fallback slip prints ("Narly drifted off in the currents—try again in a moment"). A guest has
  paid a coin; they do not leave empty-handed. Mic, AI, and printer each carry a timeout so
  nothing hangs.
- **Non-developers edit the personas.** `personas/*/prompts.md` and `content.json` are meant to
  be edited by people who do not read Python. Keep tone, rules, and ticket text in those files;
  do not migrate persona wording into code.
- **Secrets live in `.env`, never in the repo.** `.env` is git-ignored; `.env.example` is the
  committed template and must be updated whenever a new key is introduced.

## Memory

Not established — the project keeps no agent memory directory. Use the `memory-discipline`
default layout unchanged if one becomes warranted.
