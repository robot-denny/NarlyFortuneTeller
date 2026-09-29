# Pi bring-up

The Step 8 checks from `_work/pi-port/plan.md`, run by the owner on the Pi and at the cabinet. They
repeat the laptop checks in `laptop-checks.md` on the Pi, and test `deploy/README.md` as a guide.

Work through the items in order. Tick each one (`- [x]`) and write what you saw on its `Result:`
line. If something fails, note it under that item and in [Problems found](#problems-found), then
tell Claude. Claude fixes it on `feature/pi-port`: a code fix gets a test first, and a guide fix
goes into `deploy/README.md`. Then, **on the Pi**, `cd ~/fortune-service && git pull`, and re-check
the item. (If `git pull` lists `requirements.txt` or anything under `deploy/`, run
`bash deploy/setup-pi.sh` first, as the guide's "Updating the code" says.)

**On the Pi** means in the SSH window (`<user>@narly:~ $`). **On the laptop** means an ordinary
Terminal window on the Mac.

**Any run of Narly you start by hand on the Pi begins with `sudo systemctl stop narly`**, and ends
with `sudo systemctl start narly`. The background copy holds the Arduino, the mic, and the speaker.
See "Stop the service before running Narly by hand" in `deploy/README.md`.

If a `journalctl` command says `You are currently not seeing messages from other users and the
system`, put `sudo` in front of it.

## Recorded on the Pi

All **on the Pi**, from `~/fortune-service`.

- Pi OS version, from `cat /etc/os-release | head -2`:
  `____`
- Python version, from `python3 --version` (should be 3.11):
  `____`
- Persona, from `journalctl -u narly -b | grep 'Persona:'` (should be `umbraco-2026`):
  `____`
- Arduino port, from the start-up log line `Arduino port: …`
  (`journalctl -u narly -b | grep 'Arduino port:'`):
  `____`
- Mic list. Stop the service first, then start it again after:

  ```bash
  sudo systemctl stop narly
  .venv/bin/python -c "import speech_recognition as sr; print(sr.Microphone.list_microphone_names())"
  sudo systemctl start narly
  ```

  `____`
- The AM8's name in that list:
  `____`
- The `Microphone: …` start-up line (`journalctl -u narly -b | grep 'Microphone:'`). It should
  mention `fifine`. If it says `Microphone: "fifine" not found, using the default input`, see "The
  microphone isn't found" in `deploy/README.md`:
  `____`
- `vcgencmd get_throttled`:
  `____`

## Checklist

- [ ] **1. Blank SD card to running Narly, from `deploy/README.md` alone.**
  Follow the guide from step 1 to step 9, on the machine each step names. Note any step where you
  needed help from outside the guide (a search, Claude, a guess), and what was missing.
  You should end at step 9 with `systemctl status narly` showing `active (running)`.
  Result:

- [ ] **2. The service file checks clean.**
  **On the Pi:**

  ```bash
  systemd-analyze verify /etc/systemd/system/narly.service
  ```

  You should see nothing at all, just the prompt back.
  Result:

- [ ] **3. Offline fortune: a ticket, and the cues from the Bose.**
  This is step 8 of the guide. **On the Pi:**

  ```bash
  sudo systemctl stop narly
  .venv/bin/python serial_trigger.py --mode simulate --offline --persona umbraco-2026 --question "Will I find treasure today?"
  ```

  Press **Enter** for the coin. You should hear the chime, then the thinking sound, from the Bose.
  You should see `capture outcome=heard`, then `✓ Printed successfully`, then
  `✓ Fortune cycle complete`, and get a ticket reading `[TEST FORTUNE] You will find what you
  seek.` Press **Ctrl+C**, then `sudo systemctl start narly`.
  Also note: does the headphone jack hiss through the Bose when nothing is playing? If it does,
  the fix is a USB audio adapter, and `Headphones` (the card name in `deploy/asound.conf` and
  `deploy/setup-pi.sh`) changes to the adapter's name from `aplay -l`. Tell Claude.
  Result:
  Hiss (yes / no):

- [ ] **4. Starts by himself after a power cut.**
  Pull the Pi's power, then plug it back in. Don't log in, and don't touch a keyboard.
  You should hear the start-up cue from the Bose. That's the ready cue, `sfx/sfx_start.mp3`, which
  plays once the log says `Ready!`. Then insert a coin and get a ticket. (If the first coin does
  nothing, that's item 6's workaround. Insert a second one and note it.)
  Result:

- [ ] **5. Comes back by himself after a crash.**
  **On the Pi:**

  ```bash
  sudo pkill -9 -f serial_trigger.py
  journalctl -u narly -f
  ```

  You should see him stop, then start again on his own: the start-up lines again, ending in
  `Ready!`, and the ready cue from the Bose. How long it takes doesn't matter. The journal should
  show the restart, with lines like `Main process exited, code=killed, status=9/KILL` and
  `Scheduled restart job`. Press **Ctrl+C** to stop watching, then insert a coin to check he's
  waiting for one.
  Note: `sudo systemctl stop narly` does **not** restart him. That's a deliberate stop. Only a
  crash or a kill brings him back by himself.
  Result:

- [ ] **6. Two coins in a row, and the first-coin workaround.**
  **On the Pi**, restart him and watch the log:

  ```bash
  sudo systemctl restart narly
  journalctl -u narly -f
  ```

  Wait for `Ready!`. **Before inserting any coin**, watch for a minute: does
  `[arduino] Ignoring first coin signal` appear on its own? That would be a spurious coin from the
  Arduino starting up.
  Then insert two coins, one after the other finishes. You should see the LEDs for both, and no
  `Initializing Arduino...` or other Arduino start-up lines between them. Note whether your first
  real coin was ignored (the log shows `[arduino] Ignoring first coin signal` right after you
  inserted it, and nothing else happens).
  This is the laptop's "Finding for Step 8" in [laptop-checks.md](laptop-checks.md#step-3-one-arduino-connection-per-run-2026-09-29):
  there, the first real coin after every start was swallowed.
  Result:
  Spurious coin at start-up, before any coin inserted (yes / no):
  First real coin ignored (yes / no):

- [ ] **7. Unplugging the Arduino, and a different USB port.**
  **On the Pi**, `journalctl -u narly -f`. Unplug the Arduino's USB cable, and plug it into a
  different USB port on the Pi.
  You should see `Arduino disconnected: …`, then he restarts, then (if he got back before the
  Arduino did) `⏳ Waiting for the Arduino... plug it in (or use --port). Ctrl+C to stop.`, then
  `Arduino port: …` and `Ready!`. Insert a coin and get a ticket (a second one if the first is
  ignored). Note the new `Arduino port:` value.
  Result:

- [ ] **8. A missing `.env` stops him at once, with no restart.**
  **On the Pi:**

  ```bash
  mv ~/fortune-service/.env ~/fortune-service/.env.off
  sudo systemctl restart narly
  systemctl status narly
  ```

  `systemctl status narly` should show `failed` (or `inactive`), with `status=78`, and should not
  go back to `active (running)` if you run it again a few seconds later. Press `q` to get the
  prompt back. Then:

  ```bash
  journalctl -u narly -n 20
  ```

  You should see `No OPENAI_API_KEY found. Put it in the .env file next to serial_trigger.py …`,
  and no `Scheduled restart job` after it.
  Put it back and start him:

  ```bash
  mv ~/fortune-service/.env.off ~/fortune-service/.env
  sudo systemctl reset-failed narly && sudo systemctl start narly
  ```

  `systemctl status narly` should show `active (running)` again.
  Result:

- [ ] **9. The log survives a power cut.**
  Give three fortunes (three coins, plus one more if the first is ignored). Wait 20 seconds, then
  pull the Pi's power. Plug it back in, then **on the laptop** `ssh <user>@narly.local`, and **on
  the Pi:**

  ```bash
  journalctl -u narly -b -1 | grep -c 'capture outcome='
  ```

  `-b -1` means "the boot before this one". You should see `3`.
  Result:

- [x] **10. The booth Wi-Fi, rehearsed with the phone hotspot.**
  This is the test at the end of step 3 of the guide. Turn the home Wi-Fi off, or take the Pi out
  of its range. Turn on the phone's hotspot and join the laptop to it. Power the Pi on (or **on
  the Pi**, `sudo reboot`, before the home Wi-Fi goes).
  **On the laptop**, on the hotspot:

  ```bash
  ssh <user>@narly.local
  ```

  You should get the Pi's prompt. Turn the home Wi-Fi back on afterwards.
  Result: **pass, 2026-09-29.** The hotspot `DennisPhone` (WPA2, channel 11) was stored and the
  Pi joined it with `sudo nmcli connection up hotspot`. The laptop, on the hotspot, logged in with
  `ssh dkardys@narly.local`. The first try (home Wi-Fi off, waiting for the Pi to switch) failed,
  because the iPhone wasn't broadcasting: see Problems found.

- [ ] **11. No low power after a print.**
  Right after a ticket prints, **on the Pi:**

  ```bash
  vcgencmd get_throttled
  ```

  You should see `throttled=0x0`. Anything else, see "Checking for low power" in the guide.
  Result:

## Problems found

Each problem: which item, what you saw, what fixed it (the commit, or the guide section), and
whether the re-check passed.

- **Item 10: the Pi couldn't see the iPhone hotspot.** With the home Wi-Fi off, the Pi never
  joined (the address scan found only the phone and the laptop), and `nmcli device wifi list`
  didn't show `DennisPhone`. Cause: an iPhone only broadcasts its hotspot while the Personal
  Hotspot screen is open. With the screen open and `sudo nmcli device wifi rescan`, it showed up,
  and `sudo nmcli connection up hotspot` joined it. **Fix:** guide step 3 now says to rename the
  phone plainly, turn on Maximize Compatibility, keep the screen open, and test with
  `nmcli connection up` (no need to turn the home Wi-Fi off). The booth steps say to keep the
  screen open until the Pi joins. Re-check: passed (this was the test).
- **Item 10, minor: a frozen SSH session wouldn't close** with Enter, `~`, `.`. Opening a new
  Terminal tab (Cmd+T) worked. The guide now says to close the tab with Cmd+W.

- **Item 5 (setup) / 3: `/etc/asound.conf` broke all sound.** `aplay -l` printed `card is not a
  string … /etc/asound.conf may be old or corrupted`, and setup warned it couldn't set the volume.
  Cause: the short form `defaults.pcm.card Headphones` takes only a card number on this ALSA.
  **Fix:** `14337b8`, the long form (`pcm.!default` plug to `hw:Headphones`, `ctl.!default` card
  `Headphones`). Re-check: passed. `aplay -l` was clean (card 0 `Headphones`), and `speaker-test`
  played through the Bose (`Playback device is default`).
- **Item 3: scratchy hiss on the cues.** The jack was at 100%, which is +4 dB on this chip. At
  `0dB` (and at `-6dB`) the scratch went away. **Fix:** the setup script now sets `0dB`. Saved on
  the Pi with `sudo alsactl store`. A small click heard at the end of a hand-played
  `sfx_generate.mp3` was the test command cutting it off at 5 s (`sfx stuck`), not Narly, who
  plays that cue without waiting.
- **Item 1 / capture: every question came back `not_understood`.** Three coins, each ran to the
  8 s limit (`secs=8.4`, `8.4`, `7.6`) with no words found. `arecord -D plughw:3,0 …` recorded
  clearly, but a recording made the way Narly opens the mic (`sr.Microphone(device_index=1)`,
  `fifine Microphone: USB Audio (hw:3,0)`, `rate 44100`) played back **garbled**. Cause: the raw
  `hw:` device, with nothing converting the rate. **Fix:** `deploy/asound.conf` adds `fifine_mic`
  (plug to `hw:Microphone`), and `pick_mic_index` prefers a match without `(hw:` (tested). That
  alone did not fix it: `deploy/mic_check.py` showed the recording was garbled and sped up at
  **44,100 Hz** (the mic library's default), and clear at 16,000 and 48,000 Hz, whatever the chunk
  size. **Fix 2:** on Linux the mic is opened at 16,000 Hz (`choose_mic_rate`, overridable with
  `MIC_SAMPLE_RATE`). The laptop keeps its own default. Re-check: pending.
- **Item 6 evidence: the first coin is a real one on the Pi too.** `Ready!` at 10:13:22, then
  nothing until the owner's coin at 10:14:05, which was dropped as `Ignoring first coin signal`.
  The same happened at 10:27:35. No spurious start-up coin was seen on either machine, so the
  workaround only swallows attendees' coins. It should be removed in its own change, with a test.
- **Noise, not a fault:** each time the mic opens, the log fills with `ALSA lib … Unknown PCM …`
  and `jack server is not running` lines. That is the mic library probing every device. Worth
  hiding later. It doesn't affect anything.
