"""Narly stops when he is asked to.

On the Pi, `systemctl stop narly` (and a normal shutdown) sends SIGTERM. The
sound library pygame uses (SDL) takes SIGTERM over by default and turns it into
a "quit" event that Narly never reads, so without care he ignores it and
systemd force-kills him 90 seconds later.

This runs a real offline Narly in the background (no mic, no network, no
Arduino, no printer), waits until he is up, sends SIGTERM, and checks he exits.
"""

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_narly_exits_when_sent_sigterm():
    env = dict(os.environ, OPENAI_API_KEY="")
    proc = subprocess.Popen(
        [sys.executable, "serial_trigger.py", "--mode", "simulate", "--dry-run",
         "--offline", "--auto", "--interval", "60"],
        cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    try:
        # Wait for the first ticket, so pygame's sound library is fully started.
        deadline = time.monotonic() + 30
        for line in proc.stdout:
            if "Fortune cycle complete" in line or time.monotonic() > deadline:
                break

        proc.send_signal(signal.SIGTERM)
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            raise AssertionError("Narly ignored SIGTERM: still running 5 s later")
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait()
