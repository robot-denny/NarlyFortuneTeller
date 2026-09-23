# Narly hardware wiring

This page lets you rebuild, check, or safely change Narly's wiring without having the cabinet
open in front of you. It records the build as it stands on 2026-09-23. The PIR sensor and toggle
switches planned for Phase 4 are not wired yet and are not described here.

Photos of the LED build live in [`docs/reference/`](../docs/reference/). Start with
`breadboard.jpg` for the whole board and `power-supply.jpg` for the 5V supply's terminals.

## The picture in one paragraph

An Arduino Uno sits on the back half of a full-size breadboard and is powered by its USB cable
from the laptop. A 5V bench supply powers the LED strip. A 12V wall plug powers the coin
acceptor. All three of those grounds meet on one breadboard rail, and that shared rail is what
lets the Arduino read the coin pulses and drive the LED data line. The Arduino's own 5V pin is
connected to nothing. Keep it that way.

## Pin table

| Arduino pin | Direction | Connected to | Through |
|---|---|---|---|
| D2 | input, pull-up, falling-edge interrupt | HX-916 coin acceptor signal (white) | 110Ω resistor |
| D6 | output | WS2812B strip data in (teal) | 330Ω resistor |
| GND | | breadboard top rail, negative | black jumper |
| 5V | | nothing | |

The sketch constants that match this table are `COIN_PIN`, `LED_PIN`, and `NUM_LEDS` at the top
of [`fortune-controller.ino`](fortune-controller/fortune-controller.ino). `NUM_LEDS` is 180 for
the 3m strip at 60 LEDs per metre.

## Power rail

Only the top rail is used. It is the one between the Arduino and the main terminal strip. The
bottom rail is empty.

| Rail | Fed by | Also carries |
|---|---|---|
| Top positive (red line) | 5V PSU V+ (red) | LED strip red |
| Top negative (blue line) | 5V PSU V− (black) | LED strip white, barrel jack negative, Arduino GND |

A 470µF electrolytic capacitor sits across the two rails near column 40, just left of the
Arduino. Its striped side is on the negative rail. It smooths the 5V line where the strip draws
from it.

## 5V power supply

The supply is a metal-cased S-100-5, rated 5V at 20A. Its screw terminals, left to right under
the clear cover:

| Terminal | Label | Wired to |
|---|---|---|
| 1 | L | mains black |
| 2 | N | mains white |
| 3 | earth | mains green |
| 4 | V− | spare |
| 5 | V− | black lead to breadboard negative rail |
| 6 | V+ | red lead to breadboard positive rail |
| 7 | V+ | spare |

Black on L and white on N is the correct US convention. The spare V− and V+ terminals matter
for the change described under *Taking LED power off the breadboard* below.

The mains terminals are live whenever the supply is plugged in. Keep the clear cover on. Unplug
the supply before touching anything on that side.

## LED strip

The strip is a WS2812B, 3m, 180 LEDs. It ends in a three-pin JST connector plus two separate
power pigtails. Only the JST pigtail is used today.

1. Red from the JST pigtail goes to the top positive rail at the left end, around column 1.
2. White from the JST pigtail goes to the top negative rail beside it.
3. Teal (data in) goes to terminal strip column 20. A 330Ω resistor bridges to column 21. A teal
   jumper runs from column 21 to Arduino D6.

The strip's own red and white pigtails are unused and should be taped so they cannot touch
anything.

## Coin acceptor

This part of the board has been stable since V1. Do not move it.

- HX-916 red goes to the barrel jack adapter positive.
- HX-916 black goes to the barrel jack adapter negative.
- A black jumper runs from the barrel jack negative to the breadboard negative rail at the right
  end, around column 47. This is what puts the coin acceptor on the shared ground.
- HX-916 white (signal) goes to terminal strip F47.
- A 110Ω resistor bridges G47 to G49.
- A blue jumper runs from F49 to Arduino D2.
- The barrel jack adapter is fed by the 12V CyberPower wall plug.

## Breadboard column map

| Columns | What is there |
|---|---|
| 1 to 3 | LED strip red and white into the rails |
| 20 to 21 | 330Ω LED data resistor and the two teal jumpers |
| 40 | 470µF capacitor across the rails |
| 47 to 49 | 110Ω coin resistor, white signal in, blue jumper out |
| right end | barrel jack negative and Arduino GND into the negative rail |

## The one hard limit: breadboard current

The 5V supply can deliver 20A. A breadboard rail and a Dupont jumper can carry roughly one to
two amps before they heat up. The strip at full white would pull far more than that.

The build is safe today only because of what the sketch asks for. Idle and glow modes use a
single saturated hue at low value, and the global brightness cap trims everything further. The
sparkle mode lights individual pixels at full value, but only a few at a time.

Until the change below is made, two rules hold for any new animation:

- Never fill the whole strip with white or near-white.
- Never raise the global brightness cap in the sketch.

Break either and the breadboard becomes the fuse.

## Taking LED power off the breadboard

This is the recommended change before Phase 4 adds brighter animations. It routes the strip's
current straight from the supply and leaves only signals on the breadboard. Unplug the 5V supply
first.

1. **Feed the strip from the spare PSU terminals.** Screw the strip's separate red pigtail into
   terminal 7 (V+) and its white pigtail into terminal 4 (V−). If the pigtails are too short,
   extend them with 18 AWG wire and a two-position lever connector such as a Wago 221.
2. **Keep the shared ground.** Leave the black lead from terminal 5 to the breadboard negative
   rail in place. It now carries only the Arduino's reference ground, which is tiny. Without it
   the data line has nothing to measure against and the strip glitches.
3. **Pull the JST red and white out of the rails.** Tape the ends. Do not leave them plugged in
   alongside the direct run. Two parallel paths, one of them through the breadboard, means the
   breadboard still carries current you thought you had moved.
4. **Leave the data line alone.** Teal to the 330Ω resistor to D6 carries almost no current. The
   breadboard is fine for it.
5. **Move the capacitor to the strip end.** It works best across the strip's own power input,
   right where the red and white pigtails begin. Striped side to negative, as before.
6. **Optionally remove the red lead from terminal 6.** Once the strip is fed directly, nothing on
   the breadboard needs 5V from the supply. Removing it means the positive rail is dead, which
   is one less thing to short.

After this the breadboard holds only the coin signal, the LED data signal, and ground. You can
raise brightness and add white animations without the current limit above.

If you do go brighter, a 3m strip fed from one end dims and yellows toward the far end. The fix
is a second pair of power wires from terminals 4 and 7 to the far end of the strip.

## Longer term

Jumpers walk out of a breadboard under transport vibration. When the enclosure design is
settled, the cleaner step is a screw-terminal shield for the Uno, or a small soldered protoboard,
so every connection is either screwed or soldered. That belongs with the Phase 4 sketch rewrite,
which also brings the PIR sensor and toggle switches onto the board.

## Before an event

- Unplug the 5V supply and check the black lead is still firmly in terminal 5 and the red in
  terminal 6 (or the strip pigtails in 4 and 7, after the change above).
- Press each jumper down. The ones at columns 20, 21, 47, and 49 are the ones that matter.
- Confirm the Arduino GND jumper is in the negative rail. If the LEDs flicker or the coin
  is not detected, this is the first thing to check.
- Plug in and confirm the strip settles into the dim idle color before starting the Python side.
