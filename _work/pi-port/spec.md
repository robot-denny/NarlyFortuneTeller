# Spec for pi-port

> This spec captures initial requirements and design rationale. For **current system
> behavior**, see the doc named on the **Work type** line below — a new feature doc for a new
> capability, an existing feature doc for a change, or a `docs/` runbook for a fix.

branch: feature/pi-port
design reference (if any): none
discovery: none of its own. Scoped by `ROADMAP.md` → *Next* → Increment 3, with detail from
`docs/v3-upgrade-plan.md` Phase 3 (and `0a`) and `docs/v2-upgrade-plan.md` Phase 3 (`3c`–`3f`).

**Work type**: fix-infra
**Feature doc**: none

<!--
  Why fix-infra: an attendee gets the same fortune, cues, LEDs, and ticket whichever computer
  is in the cabinet. What changes is where Narly runs and how the operator starts, watches, and
  swaps him. The criteria read as transitions ("runs on the Pi", "the laptop still works after
  the change"), which is the tell. The durable record is the Pi setup guide under `deploy/`, a
  switch-back runbook under `docs/`, and a short section in CLAUDE.md. If the plan finds a
  change an attendee would notice, it folds into `_features/audio-capture.md`, not a new doc.
-->

## Summary

Narly runs on a laptop today. The laptop is hard to fit into the cabinet and hard to reach once
it's in. It can't be left unattended with confidence, and it has to be kept from going to sleep.
A Raspberry Pi 4 (4 GB) solves all three. It is small enough to live inside the cabinet. It
starts Narly on its own when it gets power. And it has no screen, lid, or sleep settings to
manage.

**Nobody has tested Narly on the Pi yet, and the next event starts Wednesday 2026-09-30.** So
this increment has two jobs of equal weight:

1. **Get Narly running on the Pi**, then measure him there the same way he was measured on the
   laptop.
2. **Keep the laptop a working fallback at every point.** If the Pi's results are poor and
   there's no time to fix them, the event runs on the laptop exactly as it would have without
   this work. At the very least, the project can return to the exact code that scored 95% on
   2026-09-28.

The Pi only earns its place at the event by passing a **go/no-go check**: the same 20-question
session from Increment 2, run live on the Pi, compared against the laptop's 95%. If the Pi falls
short, the laptop goes to the event. That's a planned outcome, not a failure of this increment.

The Arduino stays as the controller for the coin and the LEDs. The Pi replaces only the laptop
(see `docs/v3-upgrade-plan.md` → *Decisions*). The mic, the Arduino, the printer, and the
speaker are the same devices. Moving between the laptop and the Pi means unplugging cables and
plugging them in again, with nothing reflashed and nothing reconfigured.

This increment is **deliberately lean**: at each choice it takes the simpler path, and the
choices are recorded below so the owner can overrule them.

## Functional Requirements

**A known-good point to return to (done before any code changes)**

- The code as it stands on `main` today, the version that scored 95%, gets a **name in git** (a
  tag) and is pushed to GitHub. "Revert to the current state" then means checking out that one
  name, on any machine. It doesn't depend on remembering a commit or keeping a branch alive.
- The laptop's own copy of Narly (its folder, virtual environment, and `.env`) is left as it is,
  so it can still run the event as-is.

**The laptop keeps working, unchanged, throughout**

- Every change this increment makes has to keep working on the laptop too. The commands the
  owner runs on the laptop today (`serial_trigger.py` with its current flags, `app.py`,
  `--offline`, `baseline.py`) work the same afterwards.
- **The Arduino sketch doesn't change.** If it did, switching back would mean reflashing, which
  can't be done in a hurry at a booth.
- Anything that only applies to the Pi (the setup script, the start-on-boot service, the log
  settings) lives under `deploy/`, and the laptop never runs it.
- Before the event, the merged code gets a full hardware run on the laptop (coin → LEDs → mic →
  printer), as happened on 2026-09-28. That proves the fallback still works after the Pi changes.
  Only then is the fallback considered safe.

**Narly on the Pi**

- **Set up by following a guide.** `deploy/README.md` walks the owner step by step from a blank
  SD card to a running Narly: flash the Pi OS, join the network, get the code, run one setup
  script, put the `.env` in place, plug in the hardware, turn the service on. It's written for
  someone new to the Pi and Linux (see CLAUDE.md → *User notes*). The `.env` is copied over by
  hand and never committed.
- **Starts itself.** When the Pi gets power, Narly starts without a keyboard, a screen, or anyone
  logging in. He's waiting for a coin once the start-up cue has played.
- **Comes back by himself.** If Narly crashes, he restarts within a few seconds. If he keeps
  crashing (for example, because the `.env` is missing), he stops retrying rather than looping
  forever, and the log says why.
- **Finds his hardware by itself.** The Arduino is found without typing a port name. The Pi names
  serial devices differently from the Mac, and today's auto-detect only knows the Mac's names.
  The AM8 is used as the mic without picking a device number. Today Narly uses whatever the
  computer's default input is, and on the Pi that may not be the AM8. The printer is reached the
  same way it is on the laptop. `--port` still overrides the Arduino port.
- **Opens the Arduino connection once.** Today each coin opens a second connection to the
  Arduino, for the LEDs. On the Mac that happens not to matter. On the Pi, it restarts the
  Arduino on every coin, which drops the LED command and any coins inserted in the next couple
  of seconds. On the Pi, and on the laptop too, the connection is opened once when Narly starts
  and shared by the coin listener and the LEDs.
- **Plays the cues through the Bose SoundLink, over an AUX cable** from the Pi's headphone jack,
  from the same sound files, at a volume that can be heard at the booth. The Bose sits where the
  audience can hear it, and it's easier to reach than anything else in the cabinet. The Pi needs no
  Bluetooth pairing, and there's no connection to drop or delay to add. If the headphone jack
  hisses audibly through the Bose, a small USB audio adapter replaces it. Nothing else changes.
- **Keeps a log that survives a power cut.** The operator can watch the log live over SSH, and
  after the event it's still there to review, including after the power has been pulled. The log
  has a size cap so it can't fill the SD card. The `capture outcome=` and `question source=`
  lines appear exactly as they do on the laptop, so the same counting works on both.
- **Survives having the power pulled.** Unplugging the Pi, which is how the booth gets shut down,
  doesn't stop it from starting cleanly next time.
- **Has a large enough power supply.** Narly runs on the official 3 A supply. The mic, Arduino,
  and printer all draw from the Pi's USB ports, and an underpowered Pi causes random USB
  disconnects that look like software bugs. The LED strip stays on its own 5 V supply, as now.

**The go/no-go check**

- The Increment 2 session is repeated on the Pi: the same 20 questions (ids 1–10 quiet, 21–30
  with crowd noise), the same AM8 on its stand, the same crowd-noise volume, scored the same way.
  The result is recorded in `docs/capture-baseline.md` next to the laptop's rows.
- **The Pi session plays the cues through the Bose on its AUX cable, as it will at the event.**
  The laptop's 95% was measured *without* the Bose connected. The Bose is louder, and it's the
  thing the mic has to hear past. So the Pi session measures the setup that will actually run.
  The row in `docs/capture-baseline.md` notes this difference, and a small drop from 95% may come
  from the Bose rather than the Pi.
- **The laptop fallback uses the same AUX cable to the Bose**, not Bluetooth. That way, the
  fallback plays sound the same way the Pi does, and never depends on pairing. The laptop is
  checked with the Bose on the cable during its pre-event hardware run.
- The laptop's saved clips are also replayed on the Pi. This checks that the Pi can reach the
  recognizer and score clips. It doesn't test the Pi's hearing, because the clips were recorded
  on the laptop.
- The time from coin to printed ticket is noted on both machines, using the timestamps in the
  log, so a slow Pi shows up as a number, not a feeling.
- The decision rule is written down **before** the session is run, so the result decides it and
  nobody argues it afterwards (see *Open Questions* for the threshold).
- A no-go is a result, not a blocker. The increment still ships its Pi setup, the fallback proof,
  and the recorded numbers. The next increment starts from those numbers.

**Switching back**

- A short runbook in `docs/` covers the swap in both directions: which cables move, in what
  order, what to run on the laptop, and how to check it worked (the start-up cue, one test coin,
  one ticket). It includes the laptop steps the Pi made unnecessary: keep it plugged in, stop it
  sleeping for the day, and keep the lid-closed setting from suspending it.
- The runbook also covers the worst case: getting the laptop back to the tagged known-good code
  with one checkout, and what to run afterwards to confirm it.

## Decisions taken on the lean path (revisitable)

- **An unplugged Arduino is handled by restarting, not by reconnecting in place.** If the Arduino
  disappears, Narly exits with a clear log line and the Pi's service restarts him, which finds the
  Arduino again when it comes back. That drops most of the V2 `3c` / V3 `0a` reconnect work.
  Narly must exit, not hang. On the laptop, the operator restarts him by hand, as today.
- **No custom device names (udev rules).** Auto-detection by what the device is, not where it's
  plugged in, is enough for one Arduino and one printer. Deferred from V3 `3d`.
- **No reader thread or event queue for the serial port.** Opening the connection once fixes the
  Arduino-reset defect. The fuller `SerialLink` design in V3 `0a` waits for the sensor work that
  needs it.
- **The printer's route isn't changed.** It keeps the direct-USB path with the `lpr` fallback it
  already has. The plan only makes sure the Pi has permission to use the printer.
- **The SD card is used as-is** (A2-rated), with no USB SSD boot.
- **The Bose is connected by AUX cable, not Bluetooth,** on both the Pi and the laptop. This
  avoids pairing with no screen, reconnecting after the speaker drops out, Bluetooth and Wi-Fi
  sharing the Pi's radio, and Bluetooth's delay, which could let the mic hear the tail of the chime.

## Possible Edge Cases

- **At the booth, the Pi knows neither network** because the phone hotspot wasn't on when it
  booted. It joins once the hotspot turns on. Narly must still be running when it does, not stuck
  in the retry limit (see the next case).
- **The Pi starts before the network is up.** The first fortune needs the internet for the
  recognizer and OpenAI. Narly must not crash-loop into the retry limit while the Wi-Fi joins.
- **No internet at the booth at all.** This is the same as on the laptop today: the fallback slip
  prints. It's not something this increment has to solve.
- **The Arduino is plugged in after the Pi has started**, or into a different USB port on the Pi.
- **The operator runs a measuring session over SSH while the service is running.** Two copies of
  Narly would fight over the Arduino and the mic. The guide says to stop the service first, and a
  second copy fails with a clear message rather than working in a confusing half-state.
- **The Pi's clock is wrong** before it reaches the network. Log timestamps would be off, which
  affects the coin-to-ticket timing and reviewing logs after the event.
- **The first coin after a restart is ignored today** (`first_coin_ignored`, which probably masks
  the Arduino reset). Opening the connection once may make that workaround unnecessary. If it's
  removed, the first real coin must still count, on both machines.
- **The mic or printer is unplugged mid-fortune.** A ticket still prints (the fallback slip if
  need be), as the implementation rules require. Nothing hangs.
- **The Bose switches itself off** after a while with nothing playing. Many Bose portables do this
  to save battery, and between attendees there can be long quiet stretches. Narly carries on, but
  attendees hear no cues. The Bose is the easiest thing in the cabinet to reach, so the runbook
  covers the check: keep it on mains power if it has a charger, and press its power button if the
  cues go quiet. No code handles this.
- **The Bose's volume is too low or too high** compared with the laptop, because the headphone jack
  sends a different level than Bluetooth did. The volume is set once at the booth with the Bose's
  own buttons, and the runbook says so.
- **Low power under load**: the printer, mic, and Arduino active at once during a print. The
  guide says how to check the Pi's under-voltage warning after the session.
- **The laptop's copy falls behind `main`.** The fallback is only as good as the laptop's checkout
  on the day. The runbook says which version the laptop should be on for the event.
- **`.env` differences between machines**: printer USB IDs are the same, but anything path- or
  port-shaped must not be copied over from the Mac.

## Acceptance Criteria

1. The code that scored 95% has a tag, pushed to GitHub, before anything else changes, and
   checking it out on the laptop gives a working Narly.
2. After this increment merges, the laptop passes the test suite and a full hardware run (coin →
   LEDs → mic → printer), with the same commands as before and the Arduino sketch untouched.
3. Starting from a blank SD card and following only `deploy/README.md`, the Pi runs Narly with
   all the hardware attached.
4. Powering the Pi on starts Narly with no keyboard, screen, or login. A coin produces a ticket.
5. When Narly crashes on the Pi, he's back within a few seconds. A persistent fault stops the
   retries and the log says why.
6. On the Pi, the Arduino and the AM8 are found without anyone typing a port or device number.
7. The Arduino connection is opened once per run, so consecutive coins on the Pi each light the
   LEDs and none are lost.
8. The Pi's log can be watched live, and it survives the power being pulled. Its size is capped.
9. The 20-question session has been run live on the Pi and recorded beside the laptop's result,
   along with the coin-to-ticket time on both machines. The go/no-go decision is recorded as
   well, made against a rule written down beforehand.
10. The switch-back runbook exists, and one swap from the Pi to the laptop has been done by
    following it.

## Scenarios (Draft)

Draft BDD scenarios derived from the acceptance criteria using Example Mapping. Each Rule maps
to an acceptance criterion; scenarios use concrete examples. These get verified and refined
after implementation — the feature doc holds the verified version.

Terms used: **operator** is the owner running the booth; **attendee** is the person with a coin;
**known-good version** is the tagged code that scored 95%; **the service** is what starts Narly
on the Pi.

### Rule: There is always a known-good version to return to

```scenario
Scenario: Returning the laptop to the known-good version
  Given the known-good version was tagged at the commit that scored 95% on 2026-09-28
  And the laptop has later Pi-port code checked out
  When the operator checks out the known-good version on the laptop
  And inserts a coin and asks "Will I find treasure today?"
  Then Narly hears the question and prints a fortune ticket
```

### Rule: The laptop keeps working after the Pi changes

```scenario
Scenario: A full laptop run after the Pi port merges
  Given the Pi-port changes are merged into main and checked out on the laptop
  And the Arduino still has the same sketch flashed as on 2026-09-28
  When the operator starts Narly on the laptop with the same command as before
  And inserts a coin
  Then the LEDs light, the ready cue plays, Narly hears the question, and a ticket prints
```

```scenario
Scenario: Pi-only setup never touches the laptop
  Given the laptop's copy of Narly
  When the operator follows the laptop runbook to start Narly
  Then nothing under deploy/ is run
```

### Rule: The Pi can be set up from the guide alone

```scenario
Scenario: A blank SD card to a working Narly
  Given a Pi 4 with a blank SD card, the official 3 A supply, and the .env copied from the laptop
  When the operator follows deploy/README.md from the first step to the last
  Then Narly is running on the Pi
  And an offline fortune for "Will I find treasure today?" prints on the ticket printer
```

```scenario
Scenario: Adding the event's Wi-Fi at on-site setup
  Given the Pi was set up at home with home Wi-Fi and the operator's phone hotspot
  And the event's network name and password were only given out at the venue
  When the operator turns on the hotspot, connects the laptop to it, and adds the event network
    over SSH following deploy/README.md
  Then after a restart the Pi is on the event network
  And a coin produces a fortune ticket
```

### Rule: The Pi starts Narly on power-up, without anyone at a keyboard

```scenario
Scenario: Plugging in the booth
  Given the Pi is set up and switched off, with the Arduino, AM8, and printer attached
  And the Bose is on and connected to the Pi's headphone jack by its AUX cable
  When the operator plugs in the Pi's power
  Then the start-up cue plays with no keyboard, screen, or login
  And a coin inserted after the cue produces a ticket
```

### Rule: Narly recovers from a crash on his own, but stops retrying a persistent fault

```scenario
Scenario: A crash mid-afternoon
  Given Narly is running on the Pi and waiting for a coin
  When his process is killed
  Then he is waiting for a coin again within 10 seconds
  And the log shows the crash and the restart
```

```scenario
Scenario: A missing .env
  Given the .env file has been removed from the Pi
  When the service starts Narly
  Then the service stops retrying after its limit
  And the log names the missing file as the reason
```

```scenario
Scenario: The Arduino is pulled out and plugged back into a different port
  Given Narly is running on the Pi
  When the operator unplugs the Arduino and plugs it into a different USB port on the Pi
  Then Narly logs that the Arduino disappeared and restarts
  And the next coin lights the LEDs and produces a ticket
```

### Rule: The Pi finds the Arduino and the mic without being told

```scenario
Scenario: No port given on the Pi
  Given the Arduino is plugged into any USB port on the Pi
  And the service starts Narly without a --port
  Then the log shows Narly connected to the Arduino
```

```scenario
Scenario: The AM8 is used even though it is not the Pi's default input
  Given the AM8 is plugged in and the Pi's default input is something else
  When an attendee asks "What does the ocean hold for me?"
  Then Narly hears it through the AM8 and logs capture outcome=heard
```

### Rule: The Arduino is not restarted by each coin

```scenario
Scenario: Two coins in a row on the Pi
  Given Narly is running on the Pi
  When an attendee inserts a coin and gets a ticket
  And a second attendee inserts a coin straight afterwards
  Then the LEDs light for both fortunes
  And the log shows two coins, with no Arduino start-up message between them
```

### Rule: The Pi's log survives a power cut and cannot fill the card

```scenario
Scenario: Reviewing the day after the power was pulled
  Given Narly on the Pi logged 3 fortunes
  When the operator pulls the Pi's power and later powers it back on
  Then the log still contains all 3 capture outcome= lines
```

### Rule: The Pi goes to the event only if it measures up to the laptop

```scenario
Scenario: The Pi passes the check
  Given the go/no-go threshold was written down before the session
  And the laptop scored 19 of 20 with the wake level held
  When the same 20 questions are asked live on the Pi and it scores at or above the threshold
  Then the Pi's score and coin-to-ticket time are recorded beside the laptop's
  And the decision "Pi goes to the event" is recorded
```

```scenario
Scenario: The Pi falls short
  Given the go/no-go threshold was written down before the session
  When the Pi scores below it on the same 20 questions
  Then the decision "the laptop goes to the event" is recorded with the Pi's score
  And the laptop runbook is used for the event
```

### Rule: Switching back to the laptop follows a runbook

```scenario
Scenario: Swapping the Pi out for the laptop at the booth
  Given Narly is running on the Pi in the cabinet
  When the operator follows the switch-back runbook
  Then the Arduino, AM8, and printer are connected to the laptop
  And the Bose's AUX cable is in the laptop's headphone jack
  And the laptop is set not to sleep
  And one test coin produces a ticket
```

## Open Questions

- **Go/no-go threshold (decided 2026-09-28):** the Pi passes at **17 of 20 or better** (no more
  than two misses beyond the laptop's one), with no crashes during the session, and a
  coin-to-ticket time no more than a few seconds longer than the laptop's. Recorded here before
  the session, as the rule requires.
- **Hardware in hand (answered 2026-09-28):** the Pi 4, the SD card, the official 3 A supply, and
  an AUX cable long enough for now. A longer one is an errand, not a spec change.
- **The event's Wi-Fi details arrive at on-site setup, the day before the event (answered
  2026-09-28).** So the Pi must be reachable at the booth *before* it knows that network. The lean
  way is to store the operator's **phone hotspot** on the Pi as a second network during setup at
  home, next to home Wi-Fi. At the booth: turn on the hotspot, join it from the laptop too, SSH in,
  and add the event network. The guide covers that as its own short section. The hotspot is also a
  backup network if the event Wi-Fi turns out to be poor. To SSH in, the laptop has to be on the
  same network as the Pi.
- **Speaker (answered 2026-09-28):** the Bose SoundLink, which has an AUX input. It was used over
  Bluetooth at past events and was not connected during the 95% baseline. Wired on both machines
  is the lean choice (see *Functional Requirements*). Bluetooth on the Pi stays possible later if
  the cable proves awkward.
- **Does the Bose switch itself off?** Not known yet. Leave it idle for half an hour during the Pi
  session and see.
- **Which version does the laptop run if the Pi is a no-go?** Either the merged `main`, proven by
  the full laptop run, or the known-good tag. Suggestion: merged `main` if the laptop run passed,
  otherwise the tag.
- **Does the ignored first coin stay?** Once the connection is opened only once, the spurious first
  coin may disappear. The plan should check on both machines before removing the workaround.
- **Is a cue volume boost needed on the Pi?** The laptop lost its `afplay` boost in Increment 1.
  The Pi's headphone jack may send a quieter signal than Bluetooth did. The Bose's own volume
  buttons are the first fix to try, before any change to Narly.

## Testing Guidelines

Meaningful tests for the cases below, without going too heavy:

- **Arduino auto-detect**: given a list of connected devices shaped like a Mac's and like a Pi's,
  detection picks the Arduino in both cases and nothing when no Arduino is present. It needs no
  hardware.
- **One connection per run**: with a stand-in serial link, two coin events in a row open the
  connection once, and both send the LED start and stop commands.
- **An Arduino that disappears ends the run with an error**, rather than looping or hanging, so
  the service can restart it.
- **Mic selection by name**: given a device list with and without an AM8, the AM8 is chosen when
  present. Otherwise Narly falls back to the default input, as today.
- The existing suite passes unchanged on the laptop. That's the automated half of the fallback
  guarantee.
- Everything else is checked by hand on the Pi, and the plan says what to observe: booting on
  power-up, restarting after a crash, the persistent log, the cue volume, the 20-question session,
  and the laptop swap. The owner runs these in a plain terminal or at the booth, not through
  Claude.
