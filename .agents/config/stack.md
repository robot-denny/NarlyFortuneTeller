# Stack

## Build

No build step. Python 3, interpreted, run directly from the repo root with the venv
activated: `.venv/bin/python <script>.py` (or `source .venv/bin/activate` first).

Dependencies: `pip install -r requirements.txt` (needs PortAudio first for `pyaudio`:
`brew install portaudio` on macOS, `sudo apt install portaudio19-dev` on Linux). Development
dependencies: `pip install -r requirements-dev.txt`.

Tests (see `## Tests`):

```bash
.venv/bin/python -m pytest -q
```

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

`pytest` is the runner. It is a development-only dependency in `requirements-dev.txt`, kept out of
`requirements.txt` so it never lands on the Pi. Tests live in `tests/test_<module>.py`, or
`test_<flow>.py` for a flow across modules (e.g. `test_sequencing.py`). `pyproject.toml` →
`[tool.pytest.ini_options]` sets `testpaths = ["tests"]` and `pythonpath = ["."]`, so the flat
root modules import without packaging.

```bash
.venv/bin/pip install -r requirements-dev.txt   # once
.venv/bin/python -m pytest -q                    # all tests; no hardware, network, or .env needed
```

The suite covers the hardware-free paths: config loading, ticket formatting, logging, capture
outcomes, the fakes in `fakes.py`, and the coin-event flow with stand-in providers. The mic,
Arduino, and printer are still verified by hand (see `## Build` and `docs/testing.md`). Two
`DeprecationWarning`s from `SpeechRecognition` (`aifc`, `audioop`) are expected on every run.

This convention was **set** by Step 1 of `_work/capture-measure-and-fix/plan.md`; new tests follow it.
