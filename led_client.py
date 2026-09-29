# led_client.py
import time
try:
    import serial
except Exception:
    serial = None

SEND_REPEATS = 3
SEND_GAP_S = 0.015  # longer than one strip update, shorter than the 30 ms between them

class LedClient:
    def __init__(self, port="/dev/tty.usbmodem143101", baud=115200):
        self._ok = False
        self._ser = None
        if serial is None:
            return
        try:
            self._ser = serial.Serial(port, baudrate=baud, timeout=1)
            time.sleep(2.0)  # Uno resets on open
            self._ok = True
        except Exception:
            self._ok = False

    def start(self, mode="GLOW"):
        self._send(f"START {mode}")

    def stop(self):
        self._send("STOP")

    def _send(self, cmd):
        # While the Uno writes to the LED strip (about 5 ms every 30 ms) it misses
        # serial bytes, so a command can arrive cut short ("STOP" as "ST"). Send it
        # a few times, spaced so at least one copy lands outside that window. The
        # leading newline ends any cut-off fragment so it can't swallow the next copy.
        if not self._ok:
            return
        try:
            for i in range(SEND_REPEATS):
                if i:
                    time.sleep(SEND_GAP_S)
                self._ser.write(f"\n{cmd}\n".encode("utf-8"))
            self._ser.flush()
        except Exception:
            self._ok = False

    def close(self):
        try:
            if self._ser:
                self._ser.close()
        except Exception:
            pass
