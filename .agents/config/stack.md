# Stack

## Build

No build step. Python 3, interpreted, run directly from the repo root with the venv
activated: `.venv/bin/python <script>.py` (or `source .venv/bin/activate` first).

Dependencies: `pip install -r requirements.txt`.

The closest thing to a compile check, and the one used to verify this slot:

```bash
.venv/bin/python -m compileall -q *.py     # exits 0, no output, on success
```

**Working directory matters.** `config_loader.py` resolves persona and SFX paths relative to
the script's own location, but the documented invocations assume the repo root. Run everything
from `/Users/dkardys/Sites/fortune-service`. The README's `python NarlyFortuneTeller/serial_trigger.py`
form is stale — there is no `NarlyFortuneTeller/` subdirectory; the modules sit at the repo root.

Smoke check that exercises config loading without hitting the OpenAI API, the mic, or hardware
(verified — prints three personas, exits 0):

```bash
.venv/bin/python serial_trigger.py --list-personas
# Available personas: default, music, umbraco-2025
```

Fuller manual verification, which **does** call the OpenAI API (costs money) but neither prints
nor needs an Arduino:

```bash
.venv/bin/python serial_trigger.py --mode simulate --dry-run
.venv/bin/python app.py --question "Will I find treasure today?" --dry-run
```

**Arduino.** `arduino/fortune-controller/fortune-controller.ino` is compiled and flashed by hand
through the Arduino IDE. There is no `arduino-cli` on this machine and no automated build for the
sketch — a change to the `.ino` is not covered by any command above and must be flashed and
smoke-tested on the device.

## Tests

None. The project has no test framework, no test files, and no test runner installed — `pytest`
is not in the venv and not in `requirements.txt`. Verification today is manual, by running the
flows in `## Build` and the *How to verify* sections of `docs/v2-upgrade-plan.md`.

Nothing is established here, so anything adding tests is **setting** the convention rather than
following one, and should say so.
