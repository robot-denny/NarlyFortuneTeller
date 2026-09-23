# serial_trigger.py - Orchestrates the full fortune-telling flow
# Adds short audio cues (afplay) and fail-safe LED cues without changing core logic.

import sys
import re
import argparse
import subprocess
import serial
import time
import speech_recognition as sr
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, TimeoutError

from ai_client import get_ai_response, init_ai
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
        def start(self, *a, **kw): pass
        def stop(self): pass
        def close(self): pass

# ---- Paths ----
_BASE_DIR = Path(__file__).resolve().parent

# ---- Serial config ----
PORT = "/dev/cu.usbmodem143301"  # Change to your Arduino port, e.g. "COM4" on Windows
BAUD = 115200

# ---- Timeout configuration (in seconds) ----
TIMEOUT_RECORDING = 15      # Max time to wait for speech input
TIMEOUT_AI        = 30      # Max time for AI response
TIMEOUT_PRINT     = 10      # Max time for printing

# ---- Audio cues ----
SFX_START = str(_BASE_DIR / "sfx" / "sfx_magic.mp3")      # Plays when mic is ready
SFX_END   = str(_BASE_DIR / "sfx" / "sfx_generate.mp3")   # Plays when AI starts generating

# LED control usually shares the same board/port
LED_PORT = PORT  # override with --port if you use a separate LED Arduino

# ---- Module-level config (set at startup by main()) ----
_config = None

# ----------------------------------------
# Helpers
# ----------------------------------------
def afplay(path: str, wait=False, volume=1.0):
    """Play a short WAV/AIFF/MP3 via macOS 'afplay'. Never crash if missing."""
    if not path or not Path(path).exists():
        return
    try:
        if wait:
            subprocess.run(["afplay", "-v", str(volume), path], check=False)  # Wait for completion
        else:
            subprocess.Popen(["afplay", "-v", str(volume), path])  # Fire and forget
    except Exception:
        pass

def find_port():
    """Try to auto-detect an Arduino-like serial device if --port not provided."""
    try:
        import serial.tools.list_ports
        for p in serial.tools.list_ports.comports():
            if "Arduino" in (p.description or "") or "usbmodem" in (p.device or ""):
                return p.device
    except Exception:
        pass
    return None

# ----------------------------------------
# Recording / Transcription
# ----------------------------------------
def record_and_transcribe():
    """Record audio from microphone and transcribe to text."""
    recognizer = sr.Recognizer()
    mic = sr.Microphone()

    # Play sound first - signals mic is about to be ready
    afplay(SFX_START, wait=True, volume=3.0)  # 2x louder (adjust 1.0-4.0)

    log.info("  🎤 Listening for question...")
    try:
        with mic as source:
            # Quick ambient noise calibration while sound plays
            recognizer.adjust_for_ambient_noise(source, duration=0.8)
            # Settings tuned for noisy environments
            recognizer.pause_threshold = 1.5  # Allow pauses while thinking through question
            recognizer.energy_threshold = 1100  # Lower threshold to capture speech
            recognizer.dynamic_energy_threshold = False  # Use fixed threshold

            # Mic is ready now, listen for speech
            audio = recognizer.listen(source, timeout=10, phrase_time_limit=8)

        log.info("  🧠 Transcribing...")
        text = recognizer.recognize_google(audio)
        log.info(f"  ✓ Question: {text}")
        return text
    except sr.WaitTimeoutError:
        log.warning("  ⚠ No speech detected (timeout)")
        return None
    except sr.UnknownValueError:
        log.warning("  ⚠ Could not understand audio")
        return None
    except sr.RequestError as e:
        log.warning(f"  ⚠ Speech recognition error: {e}")
        return None
    except Exception as e:
        log.warning(f"  ⚠ Microphone error: {e}")
        return None

def record_and_transcribe_with_timeout():
    """Wrapper to enforce timeout on recording/transcription."""
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(record_and_transcribe)
        try:
            # Wait for recording + transcription to complete
            # The inner function handles its own timeout (WaitTimeoutError)
            return future.result(timeout=TIMEOUT_RECORDING + 10)  # Extra time for transcription
        except TimeoutError:
            log.warning(f"  ⚠ Total timeout exceeded - force stopping")
            return None
        except Exception as e:
            log.warning(f"  ⚠ Unexpected error during recording: {e}")
            return None

# ----------------------------------------
# AI generation
# ----------------------------------------
def generate_fortune(question: str) -> str:
    """Call AI to generate fortune response."""
    log.info("  🔮 Generating fortune...")
    try:
        fortune = get_ai_response(question)
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

    # Create a safe LED client (no-op if not available)
    led = LedClient(LED_PORT, BAUD)

    try:
        # Step 1: Record and transcribe (with timeout) — show "listening"
        led.start("GLOW")
        question = record_and_transcribe_with_timeout()
        led.stop()

        if not question:
            question = _config.get("default_question", "What is my fortune?") if _config else "What is my fortune?"
            log.info(f"  → Using default question: {question}")

        # Step 2: Generate fortune (with timeout) — show "thinking"
        led.start("PULSE")
        afplay(SFX_END)  # Play generate sound to signal AI is working
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
        led.stop()
        led.close()

# ----------------------------------------
# Modes
# ----------------------------------------
def listen_serial_mode(port: str, dry_run: bool = False):
    """Listen for COIN X messages from Arduino on serial port."""
    log.info(f"🔌 Hardware mode: Listening on {port} @ {BAUD}...")
    log.info("   Waiting for coin insertion...")

    ser = serial.Serial(port, BAUD, timeout=1)
    line_re = re.compile(r"^\s*COIN\s+(\d+)\s*$")

    # Allow Arduino to settle and ignore spurious signals during boot
    log.info("   Initializing Arduino...")
    time.sleep(3)
    ser.reset_input_buffer()  # Clear any buffered boot messages
    log.info("   Ready!")

    first_coin_ignored = False  # Flag to ignore first spurious coin signal

    try:
        while True:
            raw = ser.readline().decode("utf-8", errors="ignore")
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

def simulate_mode(dry_run: bool = False, auto: bool = False, interval: int = 10):
    """Simulate coin events for testing without hardware."""
    log.info("🎮 Simulation mode")

    # Reset LEDs to DIM on startup (clears any leftover state from previous session)
    log.info("   Initializing LEDs...")
    led_init = LedClient(LED_PORT, BAUD)
    led_init.stop()
    led_init.close()
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
        try:
            while True:
                input("Press ENTER for coin → ")
                on_coin_event(pulses=1, dry_run=dry_run)
        except KeyboardInterrupt:
            log.info("🛑 Exiting simulation mode.")

# ----------------------------------------
# CLI
# ----------------------------------------
def main():
    global PORT, LED_PORT, _config

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
        default=PORT,
        help=f"Serial port for hardware mode (default: {PORT})"
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

    args = parser.parse_args()
    configure_logging(args.log_file)

    # List personas and exit if requested
    if args.list_personas:
        print("Available personas:")
        for name in list_personas():
            print(f"  {name}")
        sys.exit(0)

    # Load persona config once at startup
    _config = load_config(args.persona)
    init_ai(args.persona)
    log.info(f"Persona: {_config['_persona_name']}")

    # Keep LED port aligned to main serial unless you override at runtime
    PORT = args.port or PORT
    LED_PORT = PORT

    if args.mode == "hardware":
        port = args.port or find_port()
        if not port:
            log.error("❌ Could not auto-detect serial port.")
            log.error("   Use --port to specify manually, e.g.: --port /dev/cu.usbmodem143101")
            sys.exit(1)
        listen_serial_mode(port, dry_run=args.dry_run)
    else:
        simulate_mode(dry_run=args.dry_run, auto=args.auto, interval=args.interval)

if __name__ == "__main__":
    main()
