# led_client.py
import time
try:
    import serial
except Exception:
    serial = None

from logger import get_logger

log = get_logger(__name__)

SEND_REPEATS = 3
SEND_GAP_S = 0.015  # longer than one strip update, shorter than the 30 ms between them

class LedClient:
    """Sends LED commands to the Arduino.

    Two ways to make one:

    - ``LedClient(port, baud)`` opens the port itself (and waits the 2 s an
      Uno needs to reset). ``port=None``, the default, means no Arduino: every
      call does nothing.
    - ``LedClient.sharing(ser)`` wraps a port that is already open, such as
      the one hardware mode reads coins from. Opening a port resets the Uno,
      so sharing avoids a second reset on every coin. ``close()`` then leaves
      the port open, because it belongs to whoever opened it.
    """

    def __init__(self, port=None, baud=115200):
        self._ok = False
        self._ser = None
        self._owns_port = True
        self._failing = False  # True after a failed write, until one works again
        if serial is None or port is None:  # no Arduino: no LEDs, and no reset wait
            return
        try:
            # exclusive=True: refuse to open a port another program already has.
            # write_timeout: a write that can't go through gives up after 1 s rather than
            # holding up a fortune (the failure is logged once, in _send).
            self._ser = serial.Serial(port, baudrate=baud, timeout=1, write_timeout=1, exclusive=True)
            time.sleep(2.0)  # Uno resets on open
            self._ok = True
        except Exception as e:
            self._ok = False
            log.warning(f"⚠️  Could not open LED port {port} ({e}), so no LEDs this run: "
                        "is Narly already running? On the Pi: sudo systemctl stop narly")

    @classmethod
    def sharing(cls, ser):
        """Wrap an already-open serial port. No reset wait; close() leaves it open."""
        led = cls(None)
        led._ser = ser
        led._ok = ser is not None
        led._owns_port = False
        return led

    def start(self, mode="GLOW"):
        self._send(f"START {mode}")

    def stop(self):
        self._send("STOP")

    def _send(self, cmd):
        # While the Uno writes to the LED strip (about 5 ms every 30 ms) it misses
        # serial bytes, so a command can arrive cut short ("STOP" as "ST"). Send it
        # a few times, spaced so at least one copy lands outside that window. The
        # leading newline ends any cut-off fragment so it can't swallow the next copy.
        #
        # A failed write doesn't switch the LEDs off for good: one client lasts
        # the whole run, so the next command simply tries again. The failure is
        # logged once, when it starts, so a port that keeps failing can't fill
        # the log. (If the Arduino is really gone, the coin listener notices.)
        if not self._ok:
            return
        try:
            # The Arduino replies to every command. When this client owns the port (simulate
            # mode), nothing else reads those replies, so throw them away first. Left to pile
            # up, they filled the buffer after about seven questions and stalled every LED
            # command for 15-20 s (Pi, 2026-09-29). A shared port (hardware mode) is left alone:
            # the coin listener reads everything on it, coins included.
            if self._owns_port:
                clear = getattr(self._ser, "reset_input_buffer", None)
                if clear:
                    clear()
            for i in range(SEND_REPEATS):
                if i:
                    time.sleep(SEND_GAP_S)
                self._ser.write(f"\n{cmd}\n".encode("utf-8"))
            self._ser.flush()
            self._failing = False
        except Exception as e:
            if not self._failing:
                log.warning(f"⚠️  LED command failed ({e}); will keep trying on the next one")
            self._failing = True

    def close(self):
        if not self._owns_port:  # shared port: its owner closes it
            return
        try:
            if self._ser:
                self._ser.close()
        except Exception:
            pass
