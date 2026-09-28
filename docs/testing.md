# Testing Narly

This page shows you how to run Narly's automated tests, and how to run a whole fortune on your own
computer with no coin slot, microphone, printer, or internet. It also shows you how to read Narly's
log afterwards and count how each fortune went.

You don't need to know Python to follow it. Every command is spelled out. Type each one into a
terminal exactly as shown.

## Quick start

If Narly is already set up on your computer, this is the whole test:

```bash
.venv/bin/python serial_trigger.py --mode simulate --dry-run --offline --question "Will I find treasure today?"
```

Press **Enter** when it says `Press ENTER for coin →`. That stands in for a coin. A few seconds
later a pretend ticket appears on screen, starting with `[TEST FORTUNE]`. Press **Ctrl+C** to stop.

If that didn't work, start with the setup below.

## One-time setup

You do these steps once per computer. They take about ten minutes.

### 1. Open a terminal

Use a plain terminal where you can type. In VS Code, choose **Terminal → New Terminal**. On a Mac,
the **Terminal** app works too.

Run Narly in a terminal you type into yourself. Don't run it through an AI assistant or any tool
that starts programs without a keyboard attached. Narly waits for you to press Enter, and without a
keyboard it quits at the second prompt with an `EOFError`.

### 2. Check your Python version

```bash
python3 --version
```

You need Python **3.12 or earlier** (3.10, 3.11, or 3.12). Narly's speech library doesn't work on
Python 3.13 yet. If you see 3.13 or later, install Python 3.12 from python.org and use `python3.12`
in place of `python3` in step 5.

### 3. Install PortAudio

PortAudio is a small sound library that Narly's microphone package needs. Without it, step 6 fails
with an error about building `pyaudio`.

On a Mac with Homebrew:

```bash
brew install portaudio
```

On Linux or a Raspberry Pi:

```bash
sudo apt install portaudio19-dev
```

### 4. Get the code

```bash
git clone https://github.com/robot-denny/NarlyFortuneTeller.git
cd NarlyFortuneTeller
```

Every command from here on runs from this folder, the one that holds `serial_trigger.py`.

### 5. Make a Python environment

A virtual environment is a private folder, `.venv`, that holds Narly's Python packages. It keeps
them apart from anything else on your computer.

```bash
python3 -m venv .venv
```

### 6. Install Narly's packages

```bash
.venv/bin/pip install -r requirements.txt
.venv/bin/pip install -r requirements-dev.txt
```

The first line installs what Narly needs to run. The second adds `pytest`, the tool that runs the
automated tests. Only testers and developers need it.

You don't need a `.env` file or an OpenAI key for anything on this page. Those are only for real
fortunes.

## Run the automated tests

```bash
.venv/bin/python -m pytest -q
```

The tests check the parts of Narly that don't need hardware. They take about a second. A good run
ends with a line like this:

```
40 passed, 2 warnings in 0.90s
```

The two warnings are expected. They come from the speech library and don't mean anything is wrong.
If any test says `failed`, copy the whole output and send it to the owner.

The tests can't check the microphone, the Arduino, or the printer. Those are still checked by hand,
on the real booth.

## Run a fortune with no hardware

These runs use `--offline`. Narly swaps its speech-to-text and fortune services for stand-ins, so
nothing is sent over the internet and nothing costs money. The ticket is printed on screen, not on
paper, because of `--dry-run`.

### Type a question

```bash
.venv/bin/python serial_trigger.py --mode simulate --dry-run --offline --question "Will I find treasure today?"
```

Press **Enter** at `Press ENTER for coin →`. You'll hear the readiness chime if your computer has
sound. Then you'll see this:

```
2026-09-28 11:58:46,322 INFO     💰 [COIN EVENT] pulses=1
2026-09-28 11:58:48,265 INFO     capture outcome=heard heard="Will I find treasure today?" secs=1.9
2026-09-28 11:58:48,265 INFO     question source=heard text="Will I find treasure today?"
2026-09-28 11:58:48,266 INFO       🔮 Generating fortune...
2026-09-28 11:58:48,266 INFO       ✓ Fortune generated (43 chars)
2026-09-28 11:58:48,267 INFO       🖨️  Printing fortune...

--- DRY RUN OUTPUT ---

        - Your Fortune -
--------------------------------
[TEST FORTUNE] You will find
what you seek.
--------------------------------
            - Narly

--- END DRY RUN ---

2026-09-28 11:58:48,267 INFO     ✓ Fortune cycle complete
Press ENTER for coin →
```

Press Enter again for another fortune, or **Ctrl+C** to stop.

The ticket always says `[TEST FORTUNE] You will find what you seek.` That is on purpose. It proves
the whole path from coin to ticket works, and nobody can mistake it for a real fortune.

Leave out `--question` and Narly uses the persona's usual question, "What is my fortune for today?"

### Replay a recording

```bash
.venv/bin/python serial_trigger.py --mode simulate --dry-run --offline --clip path/to/question.wav
```

`--clip` plays a recorded file into Narly in place of the microphone. It accepts WAV, AIFF, or FLAC.

With `--offline`, the stand-in recognizer doesn't listen to the words in the file. It always
reports the persona's usual question. So an offline clip run tests that Narly can read the file, not
what it hears in it. A file Narly can't read gives a `mic_error` line, like this:

```
2026-09-28 11:59:14,008 WARNING  capture outcome=mic_error heard="" secs=2.0 detail="Audio file could not be read as PCM WAV, AIFF/AIFF-C, or Native FLAC; check if file is corrupted or in another format"
2026-09-28 11:59:14,008 INFO     question source=substituted text="What is my fortune for today?"
```

Without `--offline`, a clip goes to Google's real speech recognizer and one real OpenAI fortune is
made. That needs a `.env` file with an OpenAI key, and it costs a little money. The result can also
differ from run to run. Only offline runs give the same result every time.

### Other flags you might use

| Flag | What it does |
|---|---|
| `--persona music` | Use a different persona. `--list-personas` shows them all |
| `--auto` | Drop a pretend coin every 10 seconds, so you don't have to press Enter |
| `--log-file narly.log` | Also save the log to a file. See below |
| `--help` | List every flag |

### Testing with the real microphone

This is hardware testing for the owner, not part of the remote test. Narly listens on your
computer's default input. To use the USB microphone, first choose it under **System Settings →
Sound → Input** on a Mac. Then run the command without `--offline` or `--question`:

```bash
.venv/bin/python serial_trigger.py --mode simulate --dry-run
```

This makes real fortunes, so it needs the `.env` file and costs a little per fortune.

If you stay silent at a quiet desk, Narly logs `not_understood`, not `no_speech`. That is expected
and not a fault. In a quiet room, Narly's listening level drops until the microphone's own faint
hiss counts as someone starting to speak. Festival rooms are never that quiet.

## Read the log

Every fortune writes two lines that say how listening went. The first line says what happened:

```
capture outcome=heard heard="Will I find treasure today?" secs=1.9
```

- `outcome` is one of the six results in the table below.
- `heard` is the words Narly understood. It is empty when listening failed.
- `secs` is how long listening took, in seconds.
- `detail` appears only when something failed. It gives the reason in the error's own words.

The second line says which question Narly answered:

```
question source=heard text="Will I find treasure today?"
```

`source=heard` means Narly answered what the person asked. `source=substituted` means listening
failed, so Narly answered the persona's usual question in its place.

### The six outcomes

| Outcome | What it means |
|---|---|
| `heard` | Narly understood the question |
| `no_speech` | Nobody started speaking before Narly stopped waiting |
| `not_understood` | Narly heard sound but couldn't make out any words |
| `recognizer_error` | The speech-to-text service failed, often a network problem |
| `mic_error` | The microphone, or the recording given with `--clip`, couldn't be read |
| `overrun` | Listening and understanding together took longer than Narly allows |

Offline runs always log `outcome=heard`, because the stand-in recognizer always understands. The
`Offline:` line at startup tells you the run was offline.

### Save the log to a file

Narly always prints its log in the terminal. Add `--log-file` to keep a copy in a file as well:

```bash
.venv/bin/python serial_trigger.py --mode simulate --dry-run --offline --log-file narly.log
```

Each run adds to the end of the file, so one file can hold a whole day. The file can't grow without
limit. When it reaches 5 MB, Narly renames it to `narly.log.1` and starts a fresh one. It keeps three
old files at most (`narly.log.1` to `narly.log.3`) and deletes anything older.

Where the file should live at a festival, and how long to keep it, hasn't been decided yet.

### Count a day's outcomes

`grep -c` counts the lines in a file that contain some text. One command per outcome:

```bash
grep -c 'outcome=heard' narly.log
grep -c 'outcome=no_speech' narly.log
grep -c 'outcome=not_understood' narly.log
grep -c 'outcome=recognizer_error' narly.log
grep -c 'outcome=mic_error' narly.log
grep -c 'outcome=overrun' narly.log
```

Each prints a single number. To count how many fortunes answered a substituted question:

```bash
grep -c 'source=substituted' narly.log
```

If the file holds more than one day, pick a single day by its date first:

```bash
grep '^2026-09-28' narly.log | grep -c 'outcome=no_speech'
```

These commands only look at `narly.log`. On a busy day, some lines may already have moved to
`narly.log.1`. To count across all the files at once, use `cat narly.log* | grep -c 'outcome=heard'`.
