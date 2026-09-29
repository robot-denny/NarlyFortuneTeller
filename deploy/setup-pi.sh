#!/usr/bin/env bash
#
# setup-pi.sh — sets up a Raspberry Pi to run Narly on power-up.
#
# For: Raspberry Pi OS Lite (64-bit), Legacy (Bookworm), which ships Python 3.11.
#      (The newer Pi OS has Python 3.13, which SpeechRecognition cannot use.)
# The laptop never runs this file. It is for the Pi only.
#
# How to run it (as your normal login user, NOT with sudo in front):
#
#     cd ~/fortune-service
#     bash deploy/setup-pi.sh umbraco-2026   # first time: name the persona
#     bash deploy/setup-pi.sh                # later runs: keeps the persona already installed
#
# The script asks for your password when it needs sudo for a system step. Your own files
# (the repo and .venv) stay owned by you.
#
# It is safe to run again. Re-run it with a new name to change the persona, or with no name after
# pulling new code that changes requirements.txt or anything under deploy/: then it keeps the
# persona that is already installed. (Only the very first run, with no name, uses "default".)
# It never starts or restarts Narly itself.
#
# What it does, in order:
#   1. Installs the system packages Narly needs (apt).
#   2. Makes the Python environment (.venv) and installs Narly's Python packages into it.
#   3. Gives your user access to the Arduino, the sound card, and the printer.
#   4. Installs the printer rule, the sound setting, and the log setting.
#   5. Installs Narly as a service that starts on power-up (but does not start him now).
#   6. Turns the headphone jack up to 100%.
#   Then it checks for .env and prints what to do next (the last "==>" line is
#   "Setup finished. What next:").
#
# Full guide: deploy/README.md

# Stop at the first command that fails (-e), treat an unset variable as an error (-u), and
# count a failure anywhere in a pipeline (-o pipefail). A half-finished setup is worse than
# one that stops and says where.
set -euo pipefail

say()  { printf '\n==> %s\n' "$*"; }
warn() { printf '\n!!  WARNING: %s\n' "$*" >&2; }
die()  { printf '\n!!  ERROR: %s\n' "$*" >&2; exit 1; }

# --- Checks before changing anything -----------------------------------------------------

# Run as the login user, not root. If run with sudo, .venv would be owned by root and the
# service (which runs as your user) could not use it.
if [[ "$(id -u)" -eq 0 ]]; then
    die "Run this as your normal user, without sudo in front: bash deploy/setup-pi.sh [persona]
    The script uses sudo itself for the steps that need it."
fi

# Find the repo from where this script lives (deploy/..), so it works from any folder.
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_USER="$(id -un)"
INSTALLED_UNIT=/etc/systemd/system/narly.service

# Which persona: the one named on the command line; otherwise the one already installed, so a
# re-run after `git pull` can't quietly switch the booth back to "default"; otherwise "default".
if [[ $# -ge 1 ]]; then
    PERSONA="$1"
elif [[ -f "$INSTALLED_UNIT" ]] \
        && PERSONA="$(sed -n 's/^ExecStart=.*--persona \([A-Za-z0-9_-]*\).*/\1/p' "$INSTALLED_UNIT" | head -n 1)" \
        && [[ -n "$PERSONA" ]]; then
    say "No persona named, so keeping the one already installed: '$PERSONA'"
else
    PERSONA="default"
    warn "No persona named, so using 'default'. For the event, run: bash deploy/setup-pi.sh umbraco-2026"
fi

# systemd splits the start command on spaces, so the repo path must not contain any.
if [[ "$REPO_DIR" =~ [[:space:]] ]]; then
    die "The repo path has a space in it: '$REPO_DIR'. Clone it somewhere without spaces,
    for example ~/fortune-service."
fi

# The persona name goes into the service file, so allow only plain names like "umbraco-2025".
if [[ ! "$PERSONA" =~ ^[A-Za-z0-9_-]+$ ]]; then
    die "'$PERSONA' is not a valid persona name (letters, numbers, - and _ only)."
fi

# The persona must exist, or Narly would fall back to "default" without you noticing.
if [[ ! -f "$REPO_DIR/personas/$PERSONA/content.json" ]]; then
    available="$(cd "$REPO_DIR/personas" && ls -d */ 2>/dev/null | tr -d '/' | tr '\n' ' ' || true)"
    die "No persona called '$PERSONA' (looked for personas/$PERSONA/content.json).
    Available: ${available:-none found}"
fi

say "Setting up Narly in $REPO_DIR for user '$RUN_USER', persona '$PERSONA'"

# --- 1. System packages ------------------------------------------------------------------
# git            : to pull new versions of Narly.
# python3-venv   : to make the .venv Python environment.
# python3-dev,
# portaudio19-dev,
# build-essential: needed to build pyaudio (the microphone library) on the Pi. pip builds it
#                  from source there, which needs a C compiler; Pi OS Lite may not have one.
# flac           : SpeechRecognition sends audio to Google as FLAC. It brings its own flac
#                  program only for Intel/AMD machines, so the Pi needs the system one, or
#                  every question fails as "recognizer_error".
# libusb-1.0-0   : lets python-escpos talk to the printer over USB.
say "1. Installing system packages (apt)"
sudo apt-get update
sudo apt-get install -y git python3-venv python3-dev portaudio19-dev build-essential flac libusb-1.0-0

# --- 2. Python environment ---------------------------------------------------------------
# Making a venv where one already exists is fine: it keeps what is there.
# Only requirements.txt is installed. requirements-dev.txt (the test tools) stays off the Pi.
say "2. Creating .venv and installing Python packages"
python3 -m venv "$REPO_DIR/.venv"
"$REPO_DIR/.venv/bin/pip" install --upgrade pip
"$REPO_DIR/.venv/bin/pip" install -r "$REPO_DIR/requirements.txt"

# --- 3. User groups ----------------------------------------------------------------------
# dialout: open the Arduino's serial port (/dev/ttyACM0).
# audio  : use the sound card (cues out, mic in).
# plugdev: open the printer (see deploy/99-narly-printer.rules).
# Adding a group you already have does nothing, so this is safe to repeat.
say "3. Adding $RUN_USER to the dialout, audio and plugdev groups"
sudo usermod -aG dialout,audio,plugdev "$RUN_USER"

# --- 4. System settings ------------------------------------------------------------------
say "4a. Installing the printer rule (udev)"
sudo install -m 0644 "$REPO_DIR/deploy/99-narly-printer.rules" /etc/udev/rules.d/99-narly-printer.rules
# Apply the rule now, without a reboot.
sudo udevadm control --reload-rules
sudo udevadm trigger

say "4b. Making the headphone jack the default sound output (/etc/asound.conf)"
sudo install -m 0644 "$REPO_DIR/deploy/asound.conf" /etc/asound.conf

say "4c. Keeping the log on the SD card and writing it every 15 s (journald)"
# /var/log/journal is the folder that makes the log survive a reboot.
sudo mkdir -p /etc/systemd/journald.conf.d /var/log/journal
sudo install -m 0644 "$REPO_DIR/deploy/journald-narly.conf" /etc/systemd/journald.conf.d/narly.conf
sudo systemctl restart systemd-journald

# --- 5. The service ----------------------------------------------------------------------
# Fill in the template's placeholders and install it. "enable" means "start on power-up";
# it does not start Narly now.
say "5. Installing the narly service (starts on power-up; not started now)"
sed -e "s|@USER@|$RUN_USER|g" \
    -e "s|@DIR@|$REPO_DIR|g" \
    -e "s|@PERSONA@|$PERSONA|g" \
    "$REPO_DIR/deploy/narly.service" | sudo tee /etc/systemd/system/narly.service > /dev/null
sudo systemctl daemon-reload
sudo systemctl enable narly

# --- 6. Volume ---------------------------------------------------------------------------
# Turn the jack all the way up; the Bose's own buttons set the real volume. "alsactl store"
# saves the level so it survives a reboot. If the Headphones card is missing (for example,
# audio is turned off in /boot/firmware/config.txt), warn and carry on: it is not worth
# stopping the whole setup for.
say "6. Setting the headphone jack to 100%"
if amixer -c Headphones sset PCM 100% > /dev/null && sudo alsactl store; then
    echo "    Headphone jack set to 100% and saved."
else
    warn "Could not set the headphone jack volume. Check the card with 'aplay -l'
    (it should list 'Headphones'). Setup carries on; see deploy/README.md."
fi

# --- Last: checks and next steps ---------------------------------------------------------
env_missing=0
if [[ ! -f "$REPO_DIR/.env" ]]; then
    env_missing=1
    warn "There is no .env file in $REPO_DIR.
    Narly needs it for the OpenAI key. Do NOT start the service until it is there:
    without the key he stops at start-up (exit 78) and is not restarted."
fi

if systemctl is-active --quiet narly; then
    warn "Narly is already running with the old settings. To pick up a changed persona or
    new code, restart him:  sudo systemctl restart narly"
fi

say "Setup finished. What next:"
step=1
if [[ "$env_missing" -eq 1 ]]; then
    echo "  $step. Copy .env from the laptop into $REPO_DIR/.env (it holds the secrets; never commit it)."
    step=$((step + 1))
fi
echo "  $step. Log out and back in (or reboot) so the new groups take effect."; step=$((step + 1))
echo "  $step. Run the offline check in deploy/README.md."; step=$((step + 1))
echo "  $step. Start Narly:     sudo systemctl start narly"; step=$((step + 1))
echo "  $step. Watch his log:   journalctl -u narly -f"
echo
echo "  Full guide: deploy/README.md"
