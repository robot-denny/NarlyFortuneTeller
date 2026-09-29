# Switching Narly between the Pi and the laptop

Narly can run on the Raspberry Pi inside the cabinet or on the laptop. This page is the swap in
both directions: which cables move, what to run, and how to check it worked.

Every step says where it runs:

- **On the Pi** means in an SSH window logged in to the Pi (`ssh <user>@narly.local`, from
  [deploy/README.md](../deploy/README.md)).
- **On the laptop** means in an ordinary Terminal window on the Mac, in the Narly folder:

  ```bash
  cd /Users/dkardys/Sites/fortune-service
  ```

## Which code the laptop runs at the event

The laptop runs one of two versions. Pick it before the event, not at the booth.

- **`main`**, if the laptop proof in Step 9 of the Pi port passed and the Pi work has been merged.
  This is the normal choice.
- **The tag `laptop-known-good-2026-09-28`** if the laptop proof didn't pass, or `main` misbehaves
  on the day. That's the version that scored 95% on 2026-09-28, before the Pi work. It behaves a
  little differently: see [On the known-good tag](#on-the-known-good-tag).

Both use the laptop's existing `.venv`. There's nothing to reinstall.

## Pi → laptop

### 1. Stop the Pi

If you can log in to the Pi, **on the Pi**:

```bash
sudo systemctl stop narly
```

In a hurry, just pull the Pi's power. The log is written to the card every 15 seconds, so you lose
at most that much of it.

### 2. Move the cables

Move these from the Pi to the laptop:

1. The **Arduino**'s USB cable. Either USB-C port on the laptop works (with the adapter, if the
   cable is USB-A).
2. The **Fifine AM8**'s USB cable.
3. The **printer**'s USB cable.
4. The **Bose** AUX cable, from the Pi's headphone jack into the laptop's headphone jack.

The LED strip stays on its own 5 V supply. Nothing about it changes.

### 3. Get the laptop ready

**On the laptop:**

1. **Plug in the laptop's power.** It must not run on battery all day.
2. **Stop it sleeping.** Open a **new** Terminal window and run:

   ```bash
   caffeinate -dims
   ```

   It shows nothing and keeps running. That's right. Leave this window open for the whole event.
   Closing it, or pressing Ctrl+C in it, lets the laptop sleep again. (Another way: **System
   Settings → Battery → Options**, and turn on preventing sleep when the display is off, on power
   adapter.)
3. **Don't close the lid**, unless an external display is attached. With the lid closed and no
   display, the Mac sleeps whatever else you've set.
4. **Check the sound goes to the Bose.** In **System Settings → Sound → Output**, choose
   **External Headphones**. Turn the Mac's volume up.

### 4. Switch to the event code

**On the laptop**, in the Narly folder (not the `caffeinate` window):

1. Check for unsaved changes:

   ```bash
   git status
   ```

   If it lists any `modified:` files, put them aside first, or `git switch` refuses:

   ```bash
   git stash
   ```
2. Switch to the version from [Which code the laptop runs at the event](#which-code-the-laptop-runs-at-the-event).

   For `main`:

   ```bash
   git switch main
   git pull
   ```

   Or, for the known-good tag:

   ```bash
   git fetch --tags
   git switch --detach laptop-known-good-2026-09-28
   ```

   The tag prints a note about a "detached HEAD". That's expected: you're on a fixed version, not
   a branch.

### 5. Start Narly

**On the laptop**, on `main`:

```bash
.venv/bin/python serial_trigger.py --log-file clips/narly.log
```

Narly finds the Arduino by himself in either USB-C port, so there's no `--port`. The log goes in
`clips/`, which git ignores, so it never shows up as a new file in `git status`.

You should see, among other lines:

```
Microphone: fifine Microphone (device …)
Arduino port: /dev/cu.usbmodem…
   Ready!
```

and the ready cue plays through the Bose.

On the tag, the command is different. See [On the known-good tag](#on-the-known-good-tag).

### 6. Test coin, test ticket

Insert a coin. You should hear the chime from the Bose, ask a question, and get a ticket.

The first coin after each start may be ignored: the log says `[arduino] Ignoring first coin signal`.
Insert a second coin. **After every start, insert one test coin yourself**, so no attendee loses
theirs.

### If the Arduino is unplugged on the laptop

On `main`, Narly stops with one line, `Arduino disconnected: …`. Plug it back in and run the start
command from step 5 again, then insert a test coin. The laptop doesn't restart him by itself, unlike
the Pi.

## Laptop → Pi

### 1. Stop the laptop

**On the laptop**, press **Ctrl+C** in the window where Narly is running. You should see
`🛑 Exiting serial mode.` You can also stop `caffeinate` with Ctrl+C in its window.

### 2. Move the cables

Move the Arduino, the AM8, and the printer USB cables to the Pi, and the Bose AUX cable into the
Pi's headphone jack.

### 3. Power on the Pi

Plug in the Pi's power (the official 3 A supply). Narly starts by himself:

1. Wait for the **ready cue**, a short sound from the Bose. It means Narly is up and waiting for a
   coin.
2. Insert a test coin. You should hear the chime, ask a question, and get a ticket.
3. If nothing happens, insert a second coin: the first after each start may be ignored.

If you have the laptop to hand, you can also watch him start. **On the laptop**,
`ssh <user>@narly.local`, then **on the Pi**, `journalctl -u narly -f`. Wait for `Ready!`. Press
Ctrl+C to stop watching; Narly keeps running.

If the Pi was already running with the cables unplugged, he may be waiting for the Arduino. He
finds it by himself once it's plugged in.

## The Bose speaker

Whichever machine is running Narly:

- **Mains power.** Plug the Bose into the wall, not its battery.
- **Set the volume at the booth**, with the Bose's own buttons, using a test coin. The Pi's
  headphone jack is always at full volume; on the laptop, set the Mac's volume to full as well.
- **If the cues go quiet**, the Bose may have switched itself off after a stretch with no sound.
  Press its power button, then insert a test coin.

## On the known-good tag

The tag is the older version, from before the Pi work. Three things differ:

1. **It doesn't find the Arduino by itself.** You have to tell it the port. **On the laptop**:

   ```bash
   ls /dev/cu.usbmodem*
   ```

   That prints one name, such as `/dev/cu.usbmodem1101`. It changes with the USB-C port the
   Arduino is plugged into. Put it after `--port`:

   ```bash
   .venv/bin/python serial_trigger.py --port /dev/cu.usbmodem1101 --log-file clips/narly.log
   ```
2. **It listens on the Mac's default input.** Before starting, open **System Settings → Sound →
   Input** and choose the AM8. There's no `Microphone:` line in the log to check it.
3. **An unplugged Arduino ends in an error message** (a long `Traceback`) rather than one line.
   Plug it back in and run the command again, as above.

Everything else, including the test coin and the first-coin rule, is the same.

To go back to `main` later: `git switch main`.
