# serial_trigger.py - Orchestrates the full fortune-telling flow
# Adds short audio cues (pygame, via audio_out.py) and fail-safe LED cues without changing core logic.

import os
import sys
import re
import argparse
import serial
import time
import speech_recognition as sr
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, TimeoutError

from ai_client import get_ai_response, init_ai
from audio_out import PygameAudioOut
from capture_client import CaptureOutcome, capture_question, clip_saving_get_audio, wav_get_audio
from fakes import FakeFortune, FakeTranscriber, typed_get_audio
from formatters import render_ticket
from print_client import print_ticket
from config_loader import load_config, list_personas
from logger import configure_logging, get_logger

log = get_logger(__name__)

# ---- Optional LED client (safe no-op if missing) ----
try:
    from led_client import LedClient  # separate file providing a no-op-safe serial wrapper
except Exception:
    class LedClient:  # fallback no-op
        def __init__(self, *a, **kw): pass
        @classmethod
        def sharing(cls, ser): return cls()
        def start(self, *a, **kw): pass
        def stop(self): pass
        def close(self): pass

# ---- Paths ----
_BASE_DIR = Path(__file__).resolve().parent

# ---- Serial config ----
BAUD = 115200

# USB vendor IDs that Arduino boards report. 0x2341 is Arduino (the owner's
# Uno); 0x2A03 is the same boards sold under arduino.org. Cheap clones with a
# CH340 chip (0x1A86) are left out on purpose: that chip is in lots of other
# USB-serial adapters too, so it would match things that aren't Narly's board.
ARDUINO_VIDS = {0x2341, 0x2A03}

# How often to look for the Arduino while waiting for it (seconds), and how
# often to say so in the log.
PORT_RETRY_S = 2
PORT_WAIT_LOG_S = 60

# ---- Timeout configuration (in seconds) ----
TIMEOUT_RECORDING = 15      # Max time to wait for speech input
TIMEOUT_AI        = 30      # Max time for AI response
TIMEOUT_PRINT     = 10      # Max time for printing

# ---- Audio cues ----
SFX_START = str(_BASE_DIR / "sfx" / "sfx_magic.mp3")      # Plays when mic is ready
SFX_END   = str(_BASE_DIR / "sfx" / "sfx_generate.mp3")   # Plays when AI starts generating
SFX_READY = str(_BASE_DIR / "sfx" / "sfx_start.mp3")      # Plays once hardware mode is ready for coins

# Exit code for a setup mistake that retrying can't fix, such as a missing
# OPENAI_API_KEY. 78 is the standard "configuration error" code. The Pi's
# service is told never to restart on it (RestartPreventExitStatus=78), so a
# missing key stops Narly at once with the reason in the log, while hardware
# faults (exit 1) restart for as long as it takes.
EXIT_CONFIG = 78

# LED control usually shares the same board/port
LED_PORT = None  # simulate mode only, set by main(): --port or the detected Arduino; None means no LEDs

# The one LED client for the whole run. Every coin uses it; none opens its own.
# Opening the Arduino's port resets the Uno, so it is opened once per run:
# hardware mode shares the port it reads coins from (LedClient.sharing), and
# simulate mode opens LED_PORT once at start. Until then it does nothing.
_led = LedClient(None)

# ---- Module-level config (set at startup by main()) ----
_config = None

# Which input device the real microphone opens. None means the computer's
# default input. main() sets it from MIC_NAME when the real mic is used.
_mic_index = None

# ---- Module-level providers (set at startup by main(), or by a test) ----
# These are the four things Narly needs that involve hardware or the network:
# a way to get audio from the mic, a way to turn it into text, a way to ask for
# a fortune, and a way to play sound. main() plugs in the real ones; a test (or
# later, `--mode simulate --offline`) plugs in the stand-ins from fakes.py. The
# rest of this file calls them through these names and never knows which it got.
_get_audio = None    # callable(on_ready) -> sr.AudioData, or raises
_transcribe = None   # callable(audio) -> str, or raises
_fortune = None      # callable(question) -> str
_audio_out = None    # object with .play(path, wait) — PygameAudioOut, or FakeAudioOut in tests

# ---- Clip label (only used with --save-clips) ----
# The name of the next saved clip, e.g. "27" for the script's question 27.
# simulate_mode sets it from what the operator types at the coin prompt, just
# before each coin; the clip-saving wrapper reads it when the mic opens.
_clip_label = None


def configure_providers(get_audio, transcribe, fortune, audio_out):
    """Set the four providers above. Call once at startup, or from a test.

    Same pattern as `_config`: a plain module-level assignment, no framework.
    """
    global _get_audio, _transcribe, _fortune, _audio_out
    _get_audio = get_audio
    _transcribe = transcribe
    _fortune = fortune
    _audio_out = audio_out

# ----------------------------------------
# Helpers
# ----------------------------------------
def _flatten(value: str) -> str:
    """Make a string safe to sit inside key="value" on a one-line log record.

    Collapses any whitespace runs (including line breaks) to single spaces and
    swaps double quotes for single, so an attendee's words or an error message
    can never split an event across lines or break the key="value" shape."""
    return " ".join(str(value).split()).replace('"', "'")


def find_port(ports=None, quiet=True):
    """Find an Arduino-like serial device, or return None if there isn't one.

    `ports` is a list of serial ports, each with `.device`, `.description` and
    `.vid`. Leave it out to use the ports this machine lists right now. A port
    counts as the Arduino if any of these is true:
      - its USB vendor ID is an Arduino one (the most reliable test; it works
        on the Mac and on the Pi alike),
      - its description mentions "Arduino",
      - its name contains "usbmodem" (how macOS names a board like the Uno).

    If listing the ports fails, this returns None as if nothing were plugged
    in. With `quiet=False` it raises the error instead, so `wait_for_port` can
    say why it is still waiting.
    """
    try:
        if ports is None:
            import serial.tools.list_ports
            ports = serial.tools.list_ports.comports()
        for p in ports:
            if (p.vid in ARDUINO_VIDS
                    or "Arduino" in (p.description or "")
                    or "usbmodem" in (p.device or "")):
                return p.device
    except Exception:
        if not quiet:
            raise
    return None

def wait_for_port(find=None, sleep=time.sleep):
    """Wait until an Arduino is plugged in, then return its port.

    Tries `find()` every PORT_RETRY_S seconds. Says "Waiting for the Arduino"
    on the first miss, then again about once a minute, so the log shows it is
    still waiting without filling up. It never gives up: on the Pi, exiting
    would make the service restart Narly over and over until it gave up for
    good, which is the wrong outcome for an Arduino plugged in a minute late.
    Ctrl+C stops it. `find` and `sleep` can be swapped out by a test.

    If looking for the Arduino itself fails (for example, no permission to
    list the ports), the waiting line says why, so the log shows a real
    problem and not just "plug it in".
    """
    find = find or (lambda: find_port(quiet=False))
    tries_per_log = max(1, PORT_WAIT_LOG_S // PORT_RETRY_S)
    misses = 0
    while True:
        try:
            port, problem = find(), None
        except Exception as e:
            port, problem = None, e
        if port:
            return port
        if misses % tries_per_log == 0:
            line = "⏳ Waiting for the Arduino... plug it in (or use --port). Ctrl+C to stop."
            if problem:
                log.warning(f"{line} (port scan failed: {_flatten(problem)})")
            else:
                log.info(line)
        misses += 1
        sleep(PORT_RETRY_S)

# ----------------------------------------
# Recording / Transcription
# ----------------------------------------
def pick_mic_index(names, wanted):
    """Find the microphone to use by part of its name.

    `names` is the list of input device names the computer reports, in order
    (the position in the list is the device number). `wanted` is part of the
    name to look for, such as "fifine"; upper and lower case don't matter.

    Returns the device number of the first name that contains `wanted`, or
    None when nothing matches or `wanted` is empty. None means "use the
    computer's default input", which is what Narly did before.
    """
    if not wanted:
        return None
    wanted = wanted.lower()
    for index, name in enumerate(names):
        if wanted in name.lower():
            return index
    return None

def mic_get_audio(on_ready, recognizer=None, mic=None):
    """The REAL microphone provider. There is no FakeMic class — in tests a
    one-line lambda stands in for this function.

    `capture_client.capture_question` calls this as `get_audio(on_ready)`.
    It opens the microphone, calibrates for room noise, plays the readiness
    chime (`on_ready`, which blocks until the chime ends), and then listens for
    one phrase, returning the audio for `google_transcribe`. It raises the same
    exceptions the mic path always has (`sr.WaitTimeoutError` when nobody
    spoke; anything else when the mic itself failed) — `capture_client` turns
    those into the six named outcomes, so nothing is caught here.

    The order matters. Calibration runs BEFORE the chime, while the attendee
    has not been cued yet, so no words are lost to it. Listening starts on the
    very next line after the chime ends, because that is when attendees start
    talking. (Listening during the chime would record the chime as speech.)

    The wake threshold starts at the speech library's default (300) and is set
    from the room by the calibration. It is then held for the question: left
    adapting, it climbed toward the speaker's own loudness mid-sentence, so a
    softer last word counted as the pause and was cut off.

    The microphone is created INSIDE this function on purpose: if PyAudio is
    missing, `sr.Microphone()` raises here, inside the capture stage, and is
    correctly recorded as `mic_error` rather than surfacing as a vague
    "unexpected error" outside it.

    The device it opens is `_mic_index`, the one main() chose by name
    (None means the computer's default input).

    `recognizer` and `mic` can be passed in for testing; by default the real
    ones are created.
    """
    recognizer = recognizer or sr.Recognizer()
    mic = mic or sr.Microphone(device_index=_mic_index)

    with mic as source:
        # Quick ambient noise calibration BEFORE the chime - the attendee
        # hasn't been cued yet, so nothing they say is missed
        recognizer.adjust_for_ambient_noise(source, duration=0.5)
        recognizer.dynamic_energy_threshold = False  # hold the room's level for the question
        recognizer.pause_threshold = 1.5  # Allow pauses while thinking through question
        log.info("  🎤 Calibrated — chime, then listening for question...")

        # Play the chime; this returns only once it has finished
        on_ready()
        # Listen the instant the chime ends - nothing may go between these two lines
        return recognizer.listen(source, timeout=10, phrase_time_limit=8)

def google_transcribe(audio):
    """The REAL recognizer provider — what `FakeTranscriber` stands in for.

    Sends the captured audio to Google's free speech-to-text and returns the
    words. Raises `sr.UnknownValueError` when it hears no words and
    `sr.RequestError` when the service cannot be reached; `capture_client`
    maps those to `not_understood` and `recognizer_error`.
    """
    log.info("  🧠 Transcribing...")
    return sr.Recognizer().recognize_google(audio)

# ----------------------------------------
# AI generation
# ----------------------------------------
def generate_fortune(question: str) -> str:
    """Call AI to generate fortune response."""
    log.info("  🔮 Generating fortune...")
    try:
        fortune = _fortune(question)
        log.info(f"  ✓ Fortune generated ({len(fortune)} chars)")
        return fortune
    except Exception as e:
        log.warning(f"  ⚠ AI error: {e}")
        return None

def generate_fortune_with_timeout(question: str):
    """Wrapper to enforce timeout on AI generation."""
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(generate_fortune, question)
        try:
            return future.result(timeout=TIMEOUT_AI)
        except TimeoutError:
            log.warning(f"  ⚠ AI timeout ({TIMEOUT_AI}s exceeded)")
            return None
        except Exception as e:
            log.warning(f"  ⚠ Unexpected error during AI generation: {e}")
            return None

# ----------------------------------------
# Printing
# ----------------------------------------
def print_fortune(fortune: str, dry_run: bool = False):
    """Format and print fortune ticket."""
    log.info("  🖨️  Printing fortune...")
    try:
        ticket = render_ticket(fortune, _config)
        if dry_run:
            print("\n--- DRY RUN OUTPUT ---")
            print(ticket)
            print("--- END DRY RUN ---\n")
        else:
            print_ticket(ticket)
            log.info("  ✓ Printed successfully")
    except Exception as e:
        log.warning(f"  ⚠ Print error: {e}")
        raise

def print_fortune_with_timeout(fortune: str, dry_run: bool = False):
    """Wrapper to enforce timeout on printing."""
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(print_fortune, fortune, dry_run)
        try:
            future.result(timeout=TIMEOUT_PRINT)
        except TimeoutError:
            log.warning(f"  ⚠ Print timeout ({TIMEOUT_PRINT}s exceeded)")
            raise
        except Exception as e:
            log.warning(f"  ⚠ Unexpected error during printing: {e}")
            raise

def print_fallback(dry_run: bool = False):
    """Print fallback message when something goes wrong."""
    fallback_msg = "Narly drifted off in the currents... try again in a moment."
    ticket = render_ticket(fallback_msg, _config)

    log.warning("  ⚠ Printing fallback message.")
    if dry_run:
        print("\n--- FALLBACK (DRY RUN) ---")
        print(ticket)
        print("--- END FALLBACK ---\n")
    else:
        try:
            # Use timeout for fallback too
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(print_ticket, ticket)
                future.result(timeout=TIMEOUT_PRINT)
            log.info("  ✓ Fallback printed")
        except TimeoutError:
            log.error(f"  ✗ Fallback print timeout ({TIMEOUT_PRINT}s) - showing on console:")
            print("\n" + ticket + "\n")
        except Exception as e:
            log.error(f"  ✗ Could not print fallback: {e}")
            log.info("  → Showing fallback on console instead:")
            print("\n" + ticket + "\n")

# ----------------------------------------
# Coin event flow with audio + LEDs
# ----------------------------------------
def on_coin_event(pulses: int, dry_run: bool = False):
    """
    Main orchestration: triggered when coin is inserted.
    Flow: coin → record → transcribe → generate → print
    All steps have timeout protection.
    """
    log.info(f"💰 [COIN EVENT] pulses={pulses}")

    # The run's shared LED client (a no-op if there is no Arduino).
    led = _led

    try:
        # A missing provider is a startup wiring bug, not a microphone fault.
        # Say so plainly instead of letting it surface as a misleading mic_error.
        if _get_audio is None or _transcribe is None or _fortune is None or _audio_out is None:
            raise RuntimeError("configure_providers() was not called before the first coin")

        # Step 1: Capture the question — show "listening".
        # capture_question never raises; it always hands back one of six outcomes.
        led.start("GLOW")
        result = capture_question(
            _get_audio,
            _transcribe,
            on_ready=lambda: _audio_out.play(SFX_START, wait=True),  # blocks until the chime ends
            overall_timeout=TIMEOUT_RECORDING + 10,  # the same outer guard the old wrapper used
        )
        led.stop()

        # One greppable line per capture, e.g.
        #   capture outcome=no_speech heard="" secs=10.3 detail="listening timed out"
        # Count a day's failures with:  grep -c 'outcome=no_speech' narly.log
        # Every quoted value goes through _flatten so the record stays one line.
        heard = _flatten(result.text or "")
        capture_line = f'capture outcome={result.outcome.value} heard="{heard}" secs={result.seconds:.1f}'
        if result.detail is not None:
            capture_line += f' detail="{_flatten(result.detail)}"'
        if result.outcome is CaptureOutcome.HEARD:
            log.info(capture_line)
        else:
            log.warning(capture_line)

        # Decide by the OUTCOME, not by whether text happens to be non-empty, so
        # this line can never disagree with the `capture outcome=` line above.
        if result.outcome is CaptureOutcome.HEARD:
            question = result.text
            log.info(f'question source=heard text="{_flatten(question)}"')
        else:
            question = _config.get("default_question", "What is my fortune?") if _config else "What is my fortune?"
            log.info(f'question source=substituted text="{_flatten(question)}"')

        # Step 2: Generate fortune (with timeout) — show "thinking"
        led.start("PULSE")
        _audio_out.play(SFX_END)  # Play generate sound to signal AI is working (does not block)
        fortune = generate_fortune_with_timeout(question)
        if not fortune:
            led.stop()
            print_fallback(dry_run)
            return

        # Step 3: Print (with timeout)
        try:
            print_fortune_with_timeout(fortune, dry_run)
            log.info("✓ Fortune cycle complete")
        except Exception:
            print_fallback(dry_run)
        finally:
            led.stop()

    except Exception as e:
        log.error(f"  ✗ Unexpected error in coin event handler: {e}")
        print_fallback(dry_run)
    finally:
        led.stop()  # the connection stays open for the next coin

# ----------------------------------------
# Modes
# ----------------------------------------
def _arduino_disconnected(error):
    """Log that the Arduino went away and end the run with exit code 1.

    There is no reconnect inside the program. On the Pi, systemd restarts
    Narly, and the restart waits for the Arduino to be plugged back in. On the
    laptop, start Narly again by hand. (listen_serial_mode's `finally` closes
    the port on the way out.)
    """
    log.error(f"Arduino disconnected: {error}. "
              "A restart will look for it again (on the Pi, systemd restarts Narly by itself).")
    sys.exit(1)


def listen_serial_mode(port: str, dry_run: bool = False):
    """Listen for COIN X messages from Arduino on serial port.

    The port is opened once for the whole run. The LED commands go down the
    same connection, so a coin never resets the Uno by opening it again.
    exclusive=True stops a second copy of Narly from sharing the port.
    """
    global _led
    log.info(f"🔌 Hardware mode: Listening on {port} @ {BAUD}...")
    log.info("   Waiting for coin insertion...")

    try:
        ser = serial.Serial(port, BAUD, timeout=1, exclusive=True)
    except (serial.SerialException, OSError) as e:
        # Most often another copy of Narly already holds the port (exclusive=True
        # refuses to share it). Say so plainly and stop, rather than a traceback.
        log.error(f"Could not open the Arduino port {port}: {e} "
                  "(is Narly already running? On the Pi: sudo systemctl stop narly)")
        sys.exit(1)
    _led = LedClient.sharing(ser)  # LEDs use this same open port
    line_re = re.compile(r"^\s*COIN\s+(\d+)\s*$")

    # Allow Arduino to settle and ignore spurious signals during boot
    log.info("   Initializing Arduino...")
    time.sleep(3)
    try:
        ser.reset_input_buffer()  # Clear any buffered boot messages
    except (serial.SerialException, OSError) as e:
        ser.close()
        _arduino_disconnected(e)
    log.info("   Ready!")
    # The ready cue: in a cabinet with no screen, this is how the operator
    # knows from the booth that Narly has started (or restarted) and is
    # waiting for a coin. It doesn't wait for the sound to finish.
    if _audio_out is not None:
        _audio_out.play(SFX_READY)

    first_coin_ignored = False  # Flag to ignore first spurious coin signal

    try:
        while True:
            # Only the serial read is guarded here: an unplugged cable shows up
            # as an error from readline(). on_coin_event handles its own errors.
            try:
                line = ser.readline()
            except (serial.SerialException, OSError) as e:
                _arduino_disconnected(e)
            raw = line.decode("utf-8", errors="ignore")
            if not raw:
                continue
            raw = raw.strip()

            # Skip Arduino boot/ready messages
            if "ready" in raw.lower() or "arduino" in raw.lower():
                log.info(f"[arduino] {raw}")
                continue

            m = line_re.match(raw)
            if m:
                # Ignore the first COIN signal (likely spurious from boot)
                if not first_coin_ignored:
                    log.info(f"[arduino] Ignoring first coin signal: {raw}")
                    first_coin_ignored = True
                    continue

                pulses = int(m.group(1))
                on_coin_event(pulses, dry_run)
            else:
                # Optional debug output
                if raw:
                    log.info(f"[arduino] {raw}")
    except KeyboardInterrupt:
        log.info("🛑 Exiting serial mode.")
    finally:
        ser.close()

def pick_clip_label(typed: str, clip_count: int) -> tuple[str, int]:
    """Name the next clip from what was typed at the coin prompt.

    Returns the label and the updated count. A typed question number is used
    as it is. A blank line takes the next number. So does a label with a space
    or a slash: a space would save the clip under one name and score it under
    another, and a slash would save it outside the clips folder. That case is
    logged as a WARNING, so the session log shows which number was used instead.
    """
    if typed and not any(c.isspace() or c in "/\\" for c in typed):
        return typed, clip_count
    clip_count += 1
    if typed:
        log.warning(f'⚠️  Label "{typed}" has a space or slash; saving as clip {clip_count}')
    return str(clip_count), clip_count


def simulate_mode(dry_run: bool = False, auto: bool = False, interval: int = 10, save_clips: bool = False):
    """Simulate coin events for testing without hardware.

    With ``save_clips``, whatever is typed at the coin prompt before Enter
    becomes the saved clip's label (the script's question number). A blank
    line takes the next number in sequence: 1, 2, 3, ...
    """
    global _clip_label, _led
    log.info("🎮 Simulation mode")

    # Open the LEDs once for the whole run (a no-op if LED_PORT is None), and
    # reset them to DIM, which clears any leftover state from the last session.
    # The port stays open until Narly exits, which closes it.
    log.info("   Initializing LEDs...")
    _led = LedClient(LED_PORT, BAUD)
    _led.stop()
    log.info("   LEDs ready")
    if auto:
        log.info(f"   Auto-triggering every {interval} seconds (Ctrl+C to stop)")
        try:
            while True:
                log.info("[AUTO] Simulating coin insertion...")
                on_coin_event(pulses=1, dry_run=dry_run)
                time.sleep(interval)
        except KeyboardInterrupt:
            log.info("🛑 Exiting simulation mode.")
    else:
        log.info("   Press ENTER to simulate coin insertion (Ctrl+C to stop)")
        if save_clips:
            log.info("   Saving clips: type the question number before ENTER (blank = next number)")
        clip_count = 0  # blank labels count up from 1 within this session
        try:
            while True:
                typed = input("Press ENTER for coin → ").strip()
                if save_clips:
                    _clip_label, clip_count = pick_clip_label(typed, clip_count)
                on_coin_event(pulses=1, dry_run=dry_run)
        except KeyboardInterrupt:
            log.info("🛑 Exiting simulation mode.")

def build_providers(args):
    """Choose the microphone, recognizer, and fortune source for this run.

    Hardware mode and plain simulate mode get the real ones. The simulate-only
    flags swap in stand-ins:

    - ``--clip PATH``   replays a recording instead of listening on the mic.
    - ``--question T``  skips the mic and recognizer entirely and uses T.
    - ``--save-clips DIR`` keeps each clip the real mic hears as
      ``DIR/<label>.wav``. Without it the mic is returned unwrapped, so a
      normal run saves nothing.
    - ``--offline``     replaces the recognizer and the fortune service so no
      network is used. With neither --clip nor --question it also replaces the
      mic with the persona's default question typed in, so an offline run needs
      no hardware at all — that is what a remote tester with nothing plugged in
      is for.

    Returns ``(get_audio, transcribe, fortune)`` ready for ``configure_providers``.
    Separate from main() so a test can check the flag logic directly.
    """
    get_audio, transcribe, fortune = mic_get_audio, google_transcribe, get_ai_response
    default_question = _config.get("default_question", "What is my fortune?") if _config else "What is my fortune?"
    question_text = args.question or default_question

    if args.clip:
        get_audio = wav_get_audio(args.clip)
        log.info(f"Replaying clip instead of the microphone: {args.clip}")
    elif args.question or args.offline:
        get_audio = typed_get_audio(question_text)
        log.info(f'Using typed question instead of the microphone: "{question_text}"')
    elif getattr(args, "save_clips", None):
        # main() refuses --save-clips with --clip/--question/--offline, so this
        # only ever wraps the real microphone.
        get_audio = clip_saving_get_audio(mic_get_audio, args.save_clips, lambda: _clip_label)
        log.info(f"Saving each clip the microphone hears to: {args.save_clips}")

    if args.question or args.offline:
        # Typed text is not audio, so the recognizer must be the stand-in that
        # simply hands the same words back. Offline uses it too, so nothing is
        # sent to Google even when a clip is being replayed.
        transcribe = FakeTranscriber(question_text)

    if args.offline:
        fortune = FakeFortune()
        log.info("Offline: speech-to-text and fortune are stand-ins; no network calls will be made")

    return get_audio, transcribe, fortune


# ----------------------------------------
# CLI
# ----------------------------------------
def build_parser():
    """Build the command-line parser: every flag Narly accepts, with its help text.

    Kept apart from main() so a test can check how flags are read without
    starting Narly."""
    parser = argparse.ArgumentParser(
        description="Narly Fortune Orchestrator - coordinates coin → mic → AI → print flow"
    )
    parser.add_argument(
        "--mode",
        choices=["hardware", "simulate"],
        default="hardware",
        help="Run mode: 'hardware' for real Arduino, 'simulate' for testing without hardware"
    )
    parser.add_argument(
        "--port",
        default=None,
        help="Serial port of the Arduino, e.g. /dev/ttyACM0 (auto-detect if omitted)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show output without actually printing to thermal printer"
    )
    parser.add_argument(
        "--auto",
        action="store_true",
        help="In simulate mode, auto-trigger coins at regular intervals"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=10,
        help="Seconds between auto-triggered coins in simulate mode (default: 10)"
    )
    parser.add_argument(
        "--persona",
        default="default",
        help="Persona to use (directory name under personas/). Default: 'default'"
    )
    parser.add_argument(
        "--list-personas",
        action="store_true",
        help="List available personas and exit"
    )
    parser.add_argument(
        "--log-file",
        default=None,
        help="Also write log lines to this file (rotates at 5 MB, keeps 3 backups). Stdout is always on."
    )

    # ---- Simulate-mode replay flags (all require --mode simulate) ----
    parser.add_argument(
        "--offline",
        action="store_true",
        help=(
            "Simulate only. Run a whole fortune with no microphone, no network, and no API spend: "
            "the speech-to-text and fortune services are replaced by stand-ins, and the fortune is "
            "marked [TEST FORTUNE]. On its own it uses the persona's default question, typed in; "
            "add --question to type your own, or --clip to replay a recording through the fake "
            "recognizer."
        )
    )
    replay = parser.add_mutually_exclusive_group()
    replay.add_argument(
        "--clip",
        metavar="PATH",
        default=None,
        help=(
            "Simulate only. Replay a recorded WAV/AIFF/FLAC file instead of listening on the "
            "microphone. Without --offline the real Google recognizer transcribes it and the real "
            "fortune is generated (one OpenAI call); with --offline neither service is contacted. "
            "Cannot be combined with --question."
        )
    )
    replay.add_argument(
        "--question",
        metavar="TEXT",
        default=None,
        help=(
            "Simulate only. Skip the microphone and recognizer and use TEXT as the attendee's "
            "question. Without --offline the REAL fortune is generated for it (one OpenAI call) - "
            "a quick way to type a question and see what Narly answers. Cannot be combined with --clip."
        )
    )

    parser.add_argument(
        "--save-clips",
        metavar="DIR",
        default=None,
        help=(
            "Simulate only, for a measuring session. Save what the microphone heard on each coin "
            "as DIR/<label>.wav. Type the script's question number at the coin prompt before "
            "ENTER to set the label; a blank line takes the next number. Use with --log-file so "
            "the session can be scored. Cannot be combined with --offline, --clip, --question, or --auto."
        )
    )

    return parser


def check_can_start(args, env=os.environ):
    """Stop with exit code 78 (EXIT_CONFIG) if this run would need OpenAI but has no key.

    Without the key, every coin would print the "Narly drifted off" slip and
    never say why. An --offline run uses a stand-in fortune, so it needs no key.
    (A --question run without --offline still asks OpenAI, so it does.)

    `env` is where the key is looked up. It is os.environ, which already holds
    the values from .env: ai_client loads .env when serial_trigger imports it.
    Tests pass their own dict instead. An empty key counts as missing.
    """
    if args.offline:
        return
    if not env.get("OPENAI_API_KEY"):
        log.error("No OPENAI_API_KEY found. Put it in the .env file next to serial_trigger.py "
                  "(copy .env.example to .env and fill it in), or run with --offline.")
        sys.exit(EXIT_CONFIG)


def choose_mic(env=os.environ):
    """Look up the mic named by MIC_NAME (default "fifine") and log the choice.

    The Fifine AM8 reports itself as "fifine Microphone" (the model number
    isn't in the name), so "fifine" is what finds it.

    Returns the device number to open, or None for the computer's default
    input. Listing the devices needs PyAudio; if that fails for any reason,
    Narly still starts, on the default input, with a WARNING saying why.
    """
    wanted = env.get("MIC_NAME", "fifine")
    try:
        names = sr.Microphone.list_microphone_names()
    except Exception as e:
        log.warning(f"Microphone: could not list the input devices ({_flatten(str(e))}), "
                    "using the default input")
        return None
    index = pick_mic_index(names, wanted)
    if index is None:
        log.info(f'Microphone: "{wanted}" not found, using the default input')
    else:
        log.info(f"Microphone: {names[index]} (device {index})")
    return index

def main():
    global LED_PORT, _config, _mic_index

    parser = build_parser()
    args = parser.parse_args()
    if args.mode != "simulate" and (args.offline or args.clip or args.question):
        parser.error("--offline/--clip/--question are only valid with --mode simulate")
    if args.save_clips and args.mode != "simulate":
        parser.error("--save-clips is only valid with --mode simulate")
    if args.save_clips and (args.offline or args.clip or args.question):
        parser.error("--save-clips cannot be combined with --offline, --clip, or --question: "
                     "only live microphone audio is worth saving")
    if args.save_clips and args.auto:
        parser.error("--save-clips cannot be combined with --auto: each clip is named by the "
                     "question number typed at the coin prompt")
    if args.clip and not os.path.isfile(args.clip):
        parser.error(f"--clip file not found: {args.clip}")
    configure_logging(args.log_file)

    # List personas and exit if requested
    if args.list_personas:
        print("Available personas:")
        for name in list_personas():
            print(f"  {name}")
        sys.exit(0)

    # Refuse to start without an OpenAI key, unless the run is offline.
    check_can_start(args)

    # Load persona config once at startup
    _config = load_config(args.persona)
    init_ai(args.persona)
    log.info(f"Persona: {_config['_persona_name']}")

    # Pick the real mic/recognizer/AI or their stand-ins from the flags.
    # The speaker is always the real player: it goes quiet by itself if there is no sound device.
    get_audio, transcribe, fortune = build_providers(args)
    # Only when the real mic is listening: open it by name, so the AM8 is used
    # even when it isn't the computer's default input.
    if not (args.clip or args.question or args.offline):
        _mic_index = choose_mic()
    configure_providers(get_audio, transcribe, fortune, PygameAudioOut())

    if args.mode == "hardware":
        # Hardware mode needs the Arduino for coins, so wait for it if it isn't there yet.
        port = args.port or wait_for_port()
        log.info(f"Arduino port: {port}")
        listen_serial_mode(port, dry_run=args.dry_run)
    else:
        # Simulate mode doesn't need the Arduino: use it for LEDs if it's there,
        # otherwise carry on without LEDs.
        LED_PORT = args.port or find_port()
        log.info(f"LED port: {LED_PORT or 'none found, running without LEDs'}")
        simulate_mode(dry_run=args.dry_run, auto=args.auto, interval=args.interval,
                      save_clips=bool(args.save_clips))

if __name__ == "__main__":
    main()
