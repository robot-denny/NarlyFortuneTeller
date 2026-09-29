# Laptop checks

The manual checks from Steps 2–5 of `_work/pi-port/plan.md`, run by the owner on the laptop in a
plain terminal. Step 8 repeats the Pi versions in `pi-bringup.md`.

## Step 2: finding the Arduino (2026-09-29)

- Arduino plugged in at start: found as `/dev/cu.usbmodem1101` (USB-A to USB-C adapter), no
  `--port` given.
- Arduino unplugged at start: the waiting line appeared. Once it was plugged in, Narly found it and
  carried on. Pass.
- Unplugging *during* a run crashed with a `SerialException` traceback. That's expected until
  Step 4 turns it into a clean exit.

## Step 3: one Arduino connection per run (2026-09-29)

`.venv/bin/python serial_trigger.py`, hardware mode, printer attached, three coins:

- Coin 1: nothing happened. The log showed `[arduino] Ignoring first coin signal`. **The
  `first_coin_ignored` workaround swallowed a real coin**, as the owner expected.
- Coins 2 and 3: LEDs glowed and pulsed, and both tickets printed. Pass.

**Finding for Step 8:** on the laptop, the first real coin after each start is lost, so at the booth
the first attendee after every start or restart pays and gets nothing. On the Pi, restarts happen on
their own (a crash, an unplugged Arduino), which makes this more likely to hit an attendee. Step 8
checks the same thing on the Pi. If it matches, remove the workaround in its own change, with a test
that the first coin counts. If a spurious coin does appear at start-up, filter it by timing instead
(ignore `COIN` lines that arrive during the start-up settle) rather than always dropping the first
one.
