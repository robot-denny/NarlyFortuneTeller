# Narly the Narwhal — Fortune Teller

A coin-operated AI fortune teller for festivals. When a coin is inserted, Narly listens for a spoken question, generates a fortune via OpenAI, and prints it on a thermal receipt printer.

**Pipeline:** Coin → Mic → Speech-to-Text → OpenAI → Thermal Printer

---

## Project Structure

```
NarlyFortuneTeller/
  personas/
    default/              # General sea-mystic Narly (use for any event)
    umbraco-2025/         # Umbraco US Festival 2025 persona
  sfx/                    # Sound effect files (mp3)
  arduino/
    fortune-controller/   # Arduino sketch (coin detection + LED control)
  docs/
    narly-behavior.md     # Full behavior and hardware reference
    v2-upgrade-plan.md    # V2 upgrade plan and progress tracking
  serial_trigger.py       # Main entry point (coin → mic → AI → print)
  app.py                  # Standalone test (skips coin and mic)
  ai_client.py            # OpenAI integration
  config_loader.py        # Persona-aware config loader
  formatters.py           # Thermal printer ticket formatter
  print_client.py         # Thermal printer driver
  led_client.py           # Arduino LED control via serial
```

---

## Getting Started

### 1. Clone the repo
```bash
git clone https://github.com/sthomsondiagram/NarlyFortuneTeller.git
cd fortune-service/NarlyFortuneTeller
```

### 2. Set up Python environment
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure environment
Copy `.env.example` → `.env` and fill in your API keys and printer settings.

---

## Running the App

> **Working directory:** Run all commands from the repo root (`fortune-service/`), with the venv activated.

### Simulation mode (no hardware needed)
```bash
# Press ENTER to simulate a coin insertion
python NarlyFortuneTeller/serial_trigger.py --mode simulate --dry-run

python serial_trigger.py --persona music --mode simulate --dry-run


# Auto-trigger every 10 seconds
python NarlyFortuneTeller/serial_trigger.py --mode simulate --auto --interval 10 --dry-run
```

### Hardware mode (Arduino + printer connected)
```bash
# Test without printing
python NarlyFortuneTeller/serial_trigger.py --mode hardware --dry-run

# Production — actually prints
python NarlyFortuneTeller/serial_trigger.py --mode hardware

python serial_trigger.py --persona music --mode hardware

# Specify serial port manually if auto-detect fails
python NarlyFortuneTeller/serial_trigger.py --mode hardware --port /dev/cu.usbmodem143301
```

### Quick standalone test (no coin, no mic)
```bash
python NarlyFortuneTeller/app.py --question "Will I find treasure today?" --dry-run
```

---

## Personas

Narly supports multiple personas. Each persona has its own prompt and config in `personas/<name>/`.

```bash
# List available personas
python NarlyFortuneTeller/serial_trigger.py --list-personas

# Run with a specific persona
python NarlyFortuneTeller/serial_trigger.py --mode simulate --dry-run --persona umbraco-2025
```

To create a new persona, copy `personas/default/` to a new directory and edit `prompts.md` and `content.json`.

---

## Key Features

- **Persona system** — swap event-specific personalities at startup with `--persona`
- **Timeout protection** — mic, AI, and printer all have timeouts to prevent hanging
- **Error resilience** — fallback fortune printed if any step fails
- **Simulation mode** — full test without Arduino hardware
- **Dry-run mode** — preview ticket output without printing

---

## Editing a Persona

Non-developers can edit `personas/default/prompts.md` to adjust Narly's tone, rules, and personality. The `content.json` in the same folder controls the ticket header, footer, and default question.

---

## Hardware

See `docs/narly-behavior.md` for full hardware details. Key components:
- Arduino Uno (coin detection + LED control)
- HX-916 coin acceptor
- WS2812B LED strip (60 LEDs, 5V external supply)
- MXL AC-404 USB microphone
- Maikrt 58mm thermal receipt printer

---

## License

MIT — see [LICENSE](LICENSE). Copyright (c) 2025-2026 Diagram.
