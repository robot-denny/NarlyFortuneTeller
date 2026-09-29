"""Narly stops when he is asked to.

On the Pi, `systemctl stop narly` (and a normal shutdown) sends SIGTERM. The
sound library pygame uses (SDL) takes SIGTERM over by default and turns it into
a "quit" event that Narly never reads, so without care he ignores it and
systemd force-kills him 90 seconds later.

This runs a real offline Narly in the background (no mic, no network, no
Arduino, no printer), waits until he is up, checks he is still running, sends
SIGTERM, and checks he exits.
"""

import os
import queue
import signal
import subprocess
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# "LEDs ready" is logged by simulate mode after main() has started pygame's
# sound library, which is what takes SIGTERM over. Waiting for it (rather than
# a whole fortune) keeps this test quick.
UP_LINE = "LEDs ready"
START_TIMEOUT_S = 30
STOP_TIMEOUT_S = 5


def _wait_for_line(proc, text, timeout):
    """Return True once `text` appears in the process's output, False if it
    doesn't within `timeout` seconds or the output ends. The output is read on
    a background thread, so a process that goes silent can't hang the test."""
    lines = queue.Queue()

    def read():
        for line in proc.stdout:
            lines.put(line)
        lines.put(None)  # the output has ended

    threading.Thread(target=read, daemon=True).start()
    while True:
        try:
            line = lines.get(timeout=timeout)
        except queue.Empty:
            return False
        if line is None:
            return False
        if text in line:
            return True


def test_narly_exits_when_sent_sigterm():
    env = dict(os.environ, OPENAI_API_KEY="")
    proc = subprocess.Popen(
        [sys.executable, "serial_trigger.py", "--mode", "simulate", "--dry-run",
         "--offline", "--auto", "--interval", "60"],
        cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    try:
        assert _wait_for_line(proc, UP_LINE, START_TIMEOUT_S), \
            f'Narly never logged "{UP_LINE}" (did he fail to start?)'
        assert proc.poll() is None, "Narly had already exited before SIGTERM was sent"

        proc.send_signal(signal.SIGTERM)
        try:
            proc.wait(timeout=STOP_TIMEOUT_S)
        except subprocess.TimeoutExpired:
            raise AssertionError(f"Narly ignored SIGTERM: still running {STOP_TIMEOUT_S} s later")
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait()
