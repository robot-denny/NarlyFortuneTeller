# Running Narly on the Raspberry Pi

This guide takes you from a blank SD card to Narly running on a Raspberry Pi 4 inside the cabinet.
Once it's done, Narly starts by himself when the Pi gets power, restarts himself if he crashes, and
keeps a log that survives a power cut.

You don't need to know Linux. Every command is spelled out. Type each one exactly as shown.

The laptop stays a working fallback the whole time. To move the booth from one to the other, see
[docs/switching-computers.md](../docs/switching-computers.md).

## Before you start

**Two machines, two terminals.** Most of this guide runs on the Pi, but you type it on the laptop,
through an SSH session (a terminal window that is logged in to the Pi). A few commands run on the
laptop itself. Every step says which:

- **On the Pi** means in the SSH window. Its prompt looks like `you@narly:~ $`.
- **On the laptop** means in an ordinary Terminal window on the Mac. Its prompt ends in `%`.

If a command fails with "No such file or directory" or "command not found", first check you are in
the right window.

**Some words are yours to fill in.** `<user>` is the username you choose in the Imager (step 1).
`<name>` and `<password>` are a Wi-Fi network's name and password. Type your own values and leave
out the `< >`.

**Stop the service before running Narly by hand.** Once setup is done, the Pi starts Narly on every
boot. That background copy holds the Arduino, the microphone, and the speaker. Before any run you
start yourself (the first check, a measuring session, a test), stop it first:

```bash
sudo systemctl stop narly
```

When you're done, start it again:

```bash
sudo systemctl start narly
```

If you forget, the copy you started can't get at the hardware. Hardware mode says
`Could not open the Arduino port … (is Narly already running? …)`, and simulate mode says
`Could not open LED port … is Narly already running?`. Either line means: stop the service, then
try again.

## Part 1: Set up the Pi

### 1. Write the SD card with Raspberry Pi Imager

**On the laptop.** Install Raspberry Pi Imager from raspberrypi.com/software and open it. Put the
SD card in the laptop.

1. **Device:** Raspberry Pi 4.
2. **Operating system:** open **Raspberry Pi OS (other)** and choose the **Legacy, 64-bit, Lite**
   entry. Its description mentions **Bookworm**, and it has no desktop.

   *Why this one:* the newest Pi OS ships Python 3.13, and Narly's speech library doesn't work on
   3.13 yet. Bookworm ships Python 3.11, which works. Lite has no desktop, which Narly doesn't need.
3. **Storage:** the SD card.
4. When it asks about **OS customisation**, choose **Edit settings** and fill in:
   - **Hostname:** `narly`. This is how the laptop finds the Pi, as `narly.local`.
   - **Username and password:** your choice. Write them down. The username is `<user>` in the rest
     of this guide.
   - **Wireless LAN:** your home Wi-Fi's name and password, and your country.
   - **Services** tab: turn on **Enable SSH**, with **Use password authentication**.
5. Save, confirm, and let it write. When it says it's finished, take the card out.

### 2. First boot and logging in

1. Put the SD card in the Pi and plug in its power. Nothing else needs to be connected yet.
2. The first boot is slower than later ones, because the Pi sets itself up. If the next step
   can't find the Pi at first, wait and try again.
3. **On the laptop**, log in to the Pi:

   ```bash
   ssh <user>@narly.local
   ```

   The first time, it asks `Are you sure you want to continue connecting (yes/no)?`. Type `yes`,
   then your password. (Nothing appears as you type the password. That's normal.)

   You should see a prompt like `<user>@narly:~ $`. You're now on the Pi.

   If it says `Could not resolve hostname narly.local`, see
   [Troubleshooting](#narlylocal-not-found).
4. **On the Pi**, check the Python version:

   ```bash
   python3 --version
   ```

   You should see `Python 3.11` followed by a number. If you see 3.13, the card has the wrong OS
   on it: go back to step 1 and pick the Legacy entry.

To leave the Pi at any point, type `exit`. You're back on the laptop.

### 3. Add the phone hotspot

The Pi can store Wi-Fi networks it can't see right now and join them later. Store your phone's
hotspot now, so the Pi can go online at the booth before the event Wi-Fi is set up.

First, on an iPhone:

- **Give the phone a plain name**, such as `DennisPhone` (**Settings → General → About → Name**).
  The hotspot uses the phone's name, and iPhone names often have a curly apostrophe (’) that you
  can't type to match. No apostrophes or spaces is safest.
- **Settings → Personal Hotspot:** turn on **Maximize Compatibility**, and note the **Wi-Fi
  Password**.
- **An iPhone only shows its hotspot while the Personal Hotspot screen is open.** Keep that
  screen open whenever the Pi needs to find the hotspot. Once joined, it stays joined.

1. **On the Pi**, with your phone's hotspot name and password (keep the double quotes):

   ```bash
   sudo nmcli connection add type wifi ifname wlan0 con-name hotspot ssid "<name>" wifi-sec.key-mgmt wpa-psk wifi-sec.psk "<password>"
   ```

   You should see `Connection 'hotspot' (…) successfully added.`
2. Check it is stored:

   ```bash
   nmcli connection show
   ```

   You should see a line starting `hotspot`, next to your home network (the Imager names that one
   `preconfigured`).

**Test the hotspot once at home, before the event.** The event Wi-Fi details only arrive at setup
the day before, so the hotspot is how you'll reach the Pi at first. You don't need to turn the
home Wi-Fi off for this:

1. Open the phone's **Personal Hotspot** screen and leave it open.
2. **On the Pi**, check it can see the hotspot:

   ```bash
   sudo nmcli device wifi rescan
   nmcli device wifi list | grep -i dennis
   ```

   Use part of your hotspot's name in place of `dennis`. You should see one line with the name.
   If nothing prints, check the Personal Hotspot screen is still open and try again.
3. **On the Pi**, move it onto the hotspot:

   ```bash
   sudo nmcli connection up hotspot
   ```

   The terminal freezes. That's the Pi leaving your home Wi-Fi, and it means it worked. (If
   instead you get `Error: Connection activation failed`, the password is wrong.) Close that
   Terminal tab with **Cmd+W**. Typing `exit` won't work, because the connection is gone.
4. Join the **laptop** to the hotspot. In a new Terminal tab (**Cmd+T**),
   `ssh <user>@narly.local`. If you get the Pi's prompt, the hotspot works.
5. Move the Pi back to home Wi-Fi. **On the Pi:** `sudo nmcli connection up preconfigured`. The
   terminal freezes again. Close the tab, put the laptop back on home Wi-Fi, and SSH in as usual.

If `narly.local` isn't found on the hotspot, find the Pi's address. **On the laptop:**

```bash
for i in $(seq 1 14); do ping -c 1 -t 1 172.20.10.$i >/dev/null & done; wait; arp -a | grep 172.20.10
```

`172.20.10.1` is the phone and one address is the laptop (`ipconfig getifaddr en0` shows which).
Any other address with a value after `at` is the Pi: `ssh <user>@172.20.10.X`.

### 4. Get Narly's code

**On the Pi:**

1. Make sure `git` is installed (it may already be):

   ```bash
   sudo apt update && sudo apt install -y git
   ```
2. Download the code into a folder called `fortune-service` in your home folder:

   ```bash
   cd ~
   git clone https://github.com/robot-denny/NarlyFortuneTeller.git fortune-service
   ```

   It ends with a line like `Resolving deltas: 100% … done.`
3. Switch to the Pi branch. Until it's merged into `main`, the Pi version of Narly lives on its own
   branch:

   ```bash
   cd fortune-service
   git switch feature/pi-port
   ```

   You should see `Switched to a new branch 'feature/pi-port'`. Check the setup script is there:

   ```bash
   ls deploy
   ```

   You should see `setup-pi.sh` among the files.

Every command from here on runs from this folder, `~/fortune-service`, on the Pi.

### 5. Run the setup script

The setup script installs everything Narly needs and tells the Pi to start him on power-up.

**On the Pi:**

```bash
bash deploy/setup-pi.sh
```

That uses the `default` persona. To use another, name it at the end, for example
`bash deploy/setup-pi.sh umbraco-2025`. `.venv/bin/python serial_trigger.py --list-personas` lists
them, but only after this script has made `.venv`. The folder names under `personas/` are the same
list.

A few things to know:

- **Don't put `sudo` in front.** The script asks for your password itself when it needs it. With
  `sudo` in front, it stops and tells you to run it without.
- It prints a line starting `==>` for each of its steps, numbered 1 to 6, with step 4 in three
  parts (4a, 4b, 4c), then `Setup finished. What next:`. Step 2 (the Python packages) is the
  slowest, because one of them is built on the Pi.
- It stops early if the persona doesn't exist (it lists the ones that do), or if the folder has a
  space in its name.
- At this point you haven't copied `.env` yet, so it prints a `WARNING` saying there is no `.env`
  file. That's expected. Step 6 fixes it.
- If it prints `WARNING: Could not set the headphone jack volume`, carry on. See
  [No sound](#no-sound) afterwards.

It ends with `==> Setup finished. What next:` and a short numbered list. That list matches the
rest of this guide.

It's safe to run the script again. It doesn't start or restart Narly.

**Log out and back in** so your user picks up its new permissions (for the Arduino, the sound card,
and the printer):

1. **On the Pi**, type `exit`.
2. **On the laptop**, `ssh <user>@narly.local` again, then `cd ~/fortune-service`.
3. **On the Pi**, check:

   ```bash
   groups
   ```

   The list should include `dialout`, `audio`, and `plugdev`.

### 6. Copy the `.env` file from the laptop

`.env` holds the OpenAI key and the printer's IDs. It's secret, so it never goes in git. Copy it
straight from the laptop to the Pi.

1. **On the laptop** (in a Terminal window that is *not* logged in to the Pi):

   ```bash
   scp /Users/dkardys/Sites/fortune-service/.env <user>@narly.local:~/fortune-service/.env
   ```

   It asks for the Pi's password, then shows `.env` with `100%`.
2. **On the Pi**, list the names in it, without showing the values:

   ```bash
   cut -d= -f1 .env
   ```

   You should see `AI_PROVIDER`, `OPENAI_API_KEY`, `OPENAI_MODEL`, the four `ESCPOS_…` printer
   IDs, and `PRINTER_NAME`, plus some comment lines starting with `#`. `PRINTER_NAME` is only used
   on the Mac, and it does no harm on the Pi. `MIC_NAME` may appear too; it's optional.

   Nothing else in it should name a Mac device or a port, like `/dev/cu.…` or `usbmodem`. If
   something does, delete that line (see [Editing `.env`](#editing-env)).

### 7. Plug in the hardware

With the Pi's power **unplugged**:

1. The **Arduino**, by USB, to any of the Pi's USB ports.
2. The **Fifine AM8** microphone, by USB.
3. The **thermal printer**, by USB. Switch it on.
4. The **Bose speaker**, by AUX cable, into the Pi's headphone jack. That's the small round socket
   next to the HDMI ports. Plug the Bose into mains power and switch it on.
5. The **LED strip** stays on its own 5 V supply, wired as it is now (see `arduino/README.md`).
   Don't power it from the Pi.
6. Last, the Pi's power: the **official Raspberry Pi USB-C supply (3 A)**.

   *Why the official one:* the Pi feeds the Arduino, the mic, and the printer's USB connection from
   its own power. A weaker phone charger lets the voltage sag, and then USB devices drop out at
   random. [Checking for low power](#checking-for-low-power) tells you if that's happening.

Log in again (**on the laptop**, `ssh <user>@narly.local`, then `cd ~/fortune-service`), and check
the Pi sees everything. **On the Pi:**

```bash
ls /dev/ttyACM*
```

You should see `/dev/ttyACM0`. That's the Arduino.

```bash
aplay -l
```

You should see a line containing `Headphones`. That's the jack the Bose is on.

```bash
lsusb
```

You should see a line containing `0485:5741`. That's the printer.

### 8. First check: one offline fortune

This runs a whole fortune with no internet and no OpenAI key. It uses the real printer, the real
speaker, and the LEDs. You type the question, so the microphone isn't used.

**On the Pi**, stop the background copy first, then run it:

```bash
sudo systemctl stop narly
.venv/bin/python serial_trigger.py --mode simulate --offline --question "Will I find treasure today?"
```

You should see these lines, among others:

```
Persona: default
Offline: speech-to-text and fortune are stand-ins; no network calls will be made
LED port: /dev/ttyACM0
   LEDs ready
Press ENTER for coin →
```

Press **Enter** for the coin. You should:

- **hear** the readiness chime from the Bose, then the "thinking" sound,
- **see** `capture outcome=heard`, then `✓ Printed successfully`, then `✓ Fortune cycle complete`,
- **get** a paper ticket that says `[TEST FORTUNE] You will find what you seek.`

`[TEST FORTUNE]` is expected. It's the offline stand-in, so nobody can mistake it for a real
fortune.

Press **Ctrl+C** to stop. Then start the background copy again:

```bash
sudo systemctl start narly
```

If there's no sound, see [No sound](#no-sound). If the printer says `Resource busy`, see
[The printer says "Resource busy"](#the-printer-says-resource-busy).

### 9. Start Narly and watch his log

1. **On the Pi**, start him (if you didn't already at the end of step 8):

   ```bash
   sudo systemctl start narly
   ```
2. Watch his log:

   ```bash
   journalctl -u narly -f
   ```

   Each line starts with the date and some system details, then Narly's own line. Among them you
   should see:

   ```
   Persona: default
   Microphone: … (device …)
   Arduino port: /dev/ttyACM0
   🔌 Hardware mode: Listening on /dev/ttyACM0 @ 115200...
      Initializing Arduino...
      Ready!
   ```

   The `Microphone:` line names the mic Narly chose. It should mention `fifine`. If it says
   `Microphone: "fifine" not found, using the default input`, see
   [The microphone isn't found](#the-microphone-isnt-found).
3. **Insert a test coin.** You should hear the chime, ask a question, and get a real fortune on
   paper. The first coin after each start may be ignored: the log says
   `[arduino] Ignoring first coin signal`. That's a known workaround under review, so insert a
   second coin. **After every start or restart, insert one test coin yourself**, so no attendee
   loses theirs.
4. Press **Ctrl+C** to stop watching. That only closes the log view. Narly keeps running.

To check he's running at any time:

```bash
systemctl status narly
```

You should see `active (running)` in green. Press `q` to get the prompt back.

**Check he starts by himself.** **On the Pi**, `sudo reboot`. Wait for it to come back up, log in
again, and run `journalctl -u narly -f`. You should see the start-up lines above again, with no
one having typed anything. Or skip the login: insert a coin (then a second, if the first is
ignored) and get a ticket.

**The ready cue.** Once Narly is `Ready!` for coins, he plays a short sound through the Bose. It
plays every time he starts, including after a restart. From the booth, the cue is how you know
he's up without a laptop. Still insert one test coin after it, because the first coin may be
ignored.

## Part 2: At the booth and after

### Adding the event Wi-Fi at the booth

The event Wi-Fi's name and password usually arrive at setup, the day before the event.

1. Turn on your phone's hotspot, and **keep the Personal Hotspot screen open** until the Pi has
   joined.
2. Join the laptop to the hotspot.
3. Power on the Pi. It joins the hotspot by itself, because you stored it in step 3.
4. **On the laptop**, log in: `ssh <user>@narly.local`.
5. **On the Pi**, store the event network, with its name and password:

   ```bash
   sudo nmcli connection add type wifi ifname wlan0 con-name event ssid "<name>" wifi-sec.key-mgmt wpa-psk wifi-sec.psk "<password>"
   ```

   You should see `Connection 'event' (…) successfully added.`
6. Restart the Pi:

   ```bash
   sudo reboot
   ```
7. Turn the phone's hotspot off, and join the laptop to the event Wi-Fi. **On the laptop**,
   `ssh <user>@narly.local`. If you get the Pi's prompt, the Pi is on the event Wi-Fi.

If the Pi doesn't appear, turn the hotspot back on: it will rejoin that, and you can check the
event network's name and password with the organisers. If the event Wi-Fi has a login web page
("captive portal"), the Pi can't get past it. Use the hotspot for the event instead.

### Running a measuring session

This is the session from [docs/capture-baseline.md](../docs/capture-baseline.md), on the Pi. Read
that page first for the script, the conditions, and the setup checklist. Two differences on the Pi:

- The clips and log go in `clips/pi/`, so they don't mix with the laptop's.
- The Pi has no System Settings. Narly picks the AM8 by name instead: check the `Microphone:` line
  when the session starts.

**On the Pi:**

1. Stop the background copy:

   ```bash
   sudo systemctl stop narly
   ```
2. If `clips/pi` is already there from an earlier session, move it aside, putting today's date in
   its new name:

   ```bash
   mv clips/pi clips/pi-old-YYYY-MM-DD
   ```

   `No such file or directory` means there wasn't one. That's fine.
3. Start the session:

   ```bash
   .venv/bin/python serial_trigger.py --mode simulate --dry-run --save-clips clips/pi --log-file clips/pi/session.log
   ```

   Near the top, check the line `Microphone: … (device …)` mentions `fifine`. If it says
   `"fifine" not found`, stop with Ctrl+C and see [The microphone isn't found](#the-microphone-isnt-found).
4. Work through the questions exactly as in capture-baseline.md: type the id, press **Enter**, wait
   for the chime to end, then ask. Press **Ctrl+C** after the last one.
5. Score it:

   ```bash
   .venv/bin/python baseline.py live clips/pi/session.log docs/baseline-script.csv --clips clips/pi
   .venv/bin/python baseline.py replay clips/pi docs/baseline-script.csv
   ```

   Each prints a block starting `### Live` or `### Replay`. Select it in the SSH window and copy it
   into the results in capture-baseline.md on the laptop.
6. Start the background copy again:

   ```bash
   sudo systemctl start narly
   ```

### Counting outcomes

Narly's log on the Pi lives in the system log, not in a file. `journalctl -u narly` prints it, and
`grep -c` counts the lines that contain some text. **On the Pi:**

```bash
journalctl -u narly | grep -c 'outcome=no_speech'
```

That prints one number: how many coins had nobody speaking. Swap in any of the six outcomes from
[docs/testing.md](../docs/testing.md#the-six-outcomes), such as `outcome=heard`. To count only
today:

```bash
journalctl -u narly --since today | grep -c 'outcome=heard'
```

The log keeps up to 100 MB, which is many event days, and survives reboots and power cuts. At most
the last 15 seconds before a power cut can be lost.

### Changing persona

The persona is set when the setup script runs. To change it, run the script again with the new
name, then restart Narly. **On the Pi:**

```bash
bash deploy/setup-pi.sh music
sudo systemctl restart narly
```

Then `journalctl -u narly -f` should show `Persona: music`.

### Updating the code

**On the Pi:**

```bash
cd ~/fortune-service
git pull
sudo systemctl restart narly
```

`git pull` lists the files that changed. If that list includes `requirements.txt` or anything under
`deploy/`, run `bash deploy/setup-pi.sh` (with your persona) before the restart.

### Checking for low power

**On the Pi:**

```bash
vcgencmd get_throttled
```

`throttled=0x0` is good. Anything else means the Pi's voltage has sagged since it last started,
which makes USB devices drop out. Use the official 3 A supply, and check nothing else draws power
from the Pi.

### Editing `.env`

**On the Pi**, `nano .env` opens it in a simple text editor. Use the arrow keys to move. To save,
press **Ctrl+O**, then **Enter**. To leave, press **Ctrl+X**. Then restart Narly so he reads the
change: `sudo systemctl restart narly`.

## Troubleshooting

### `narly.local` not found

`ssh` says `Could not resolve hostname narly.local`.

- Wait a little and try again. After power-on, the Pi takes a while to join Wi-Fi.
- Check the laptop and the Pi are on the same network. At the booth, that's the hotspot or the
  event Wi-Fi, not both.
- Try `ping narly.local` **on the laptop**. Press Ctrl+C to stop it. If it never answers, the Pi
  isn't on this network.
- If it still fails at home, re-check the Wi-Fi name, password, and country in the Imager's
  settings. Re-writing the card is safe; then start this guide again from step 1.

### The printer says "Resource busy"

If printing fails with `Resource busy` in the log, Linux's own printer driver is holding the
printer. Tell it to leave the printer alone. **On the Pi:**

```bash
echo "blacklist usblp" | sudo tee /etc/modprobe.d/no-usblp.conf
sudo reboot
```

Only do this if you see `Resource busy`.

### No sound

1. Check the Bose: plugged into mains power, switched on, volume up, and the AUX cable pushed all
   the way into the Pi's headphone jack (not an HDMI port).
2. **On the Pi**, `aplay -l` should list a card named `Headphones`. If it doesn't, the Pi's audio
   is switched off. Re-run `bash deploy/setup-pi.sh` and watch for the headphone-jack WARNING.
3. Play a test sound with the background copy stopped:

   ```bash
   sudo systemctl stop narly
   speaker-test -c 2 -t wav -l 1
   sudo systemctl start narly
   ```

   You should hear a voice say "Front left", "Front right". If you hear that but not Narly's cues
   in a run you started by hand, put `SDL_AUDIODRIVER=alsa ` at the start of the command, before
   `.venv/bin/python`. (The service already has it.)
4. The Bose may switch itself off after a while with no sound. If the cues go quiet at the booth,
   press its power button.

### The microphone isn't found

The log says `Microphone: "fifine" not found, using the default input`. Narly looks for a mic whose
name contains `fifine`. To see the names the Pi reports, **on the Pi**:

```bash
sudo systemctl stop narly
.venv/bin/python -c "import speech_recognition as sr; print(sr.Microphone.list_microphone_names())"
```

Find the AM8 in the list. Then open `.env` (see [Editing `.env`](#editing-env)) and add a line with
a word from its name that no other device in the list has. For example, if the list shows
`'AM8: USB Audio (hw:2,0)'`, add:

```
MIC_NAME=AM8
```

Save, then `sudo systemctl start narly`, and check the `Microphone:` line in the log.

### Narly keeps waiting for the Arduino

The log repeats `⏳ Waiting for the Arduino... plug it in (or use --port). Ctrl+C to stop.` Narly
can't see the Arduino. Check its USB cable at both ends. `ls /dev/ttyACM*` should show
`/dev/ttyACM0`. Once it's plugged in, Narly finds it by himself.

If the Arduino is unplugged while Narly is running, the log says `Arduino disconnected: …` and he
stops. The Pi restarts him, and he waits for the Arduino again. Plug it back in, then insert a test
coin.

### Narly has stopped for good

Hardware faults (an unplugged Arduino, a loose cable) always end in a restart, however often they
happen. Narly only stays stopped for a setup mistake that restarting can't fix. Then
`systemctl status narly` shows `failed` (or `inactive`), with `status=78`. Press `q` to get the
prompt back.

1. Find out why. **On the Pi**:

   ```bash
   journalctl -u narly -n 50
   ```

   That shows his last 50 lines. The usual reason is `No OPENAI_API_KEY found`: the `.env` file
   is missing or has no key. Copy it again (step 6).
2. Fix the cause, then clear the failure and start him:

   ```bash
   sudo systemctl reset-failed narly
   sudo systemctl start narly
   ```

### `journalctl` shows nothing

If `journalctl -u narly` says `You are currently not seeing messages from other users and the
system`, put `sudo` in front: `sudo journalctl -u narly -f`.
