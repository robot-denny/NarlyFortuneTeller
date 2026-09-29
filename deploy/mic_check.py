"""mic_check.py: record a few seconds from the mic the way Narly does, and play it back.

For the Pi (it works on the laptop too). Stop the service first, so the mic is free:

    sudo systemctl stop narly
    .venv/bin/python deploy/mic_check.py

It picks the mic the same way Narly does (MIC_NAME, default "fifine"), then records 4 seconds
at a few different settings. Before each one it prints "SPEAK NOW". Talk until the next line
appears. Each recording is saved as /tmp/mic-<rate>-<chunk>.wav and played back through the
speaker straight away, so you can hear which settings come out clear and which come out garbled.

    sudo systemctl start narly     # afterwards
"""

import os
import subprocess
import sys
import time
from pathlib import Path

# Run from anywhere: find serial_trigger.py in the folder above this one.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import speech_recognition as sr  # noqa: E402
import serial_trigger  # noqa: E402

# (sample rate, chunk size). The first is what Narly itself uses (serial_trigger.choose_mic_rate:
# 16000 on the Pi; None, the mic's own default, on the laptop). 44100 garbled the Pi's recording.
SETTINGS = [(serial_trigger.choose_mic_rate(), 1024), (44100, 1024), (16000, 4096), (48000, 1024)]
SECONDS = 4


def main():
    names = sr.Microphone.list_microphone_names()
    wanted = os.environ.get("MIC_NAME", "fifine")
    index = serial_trigger.pick_mic_index(names, wanted)
    label = names[index] if index is not None else "the default input"
    print(f"\nMic: {label} (device {index})\n", flush=True)

    for rate, chunk in SETTINGS:
        path = f"/tmp/mic-{rate}-{chunk}.wav"
        try:
            mic = sr.Microphone(device_index=index, sample_rate=rate, chunk_size=chunk)
            with mic as source:
                print(f"rate {rate or 'mic default'}, chunk {chunk}: get ready...", flush=True)
                time.sleep(2)
                print("   SPEAK NOW", flush=True)
                audio = sr.Recognizer().record(source, duration=SECONDS)
            Path(path).write_bytes(audio.get_wav_data())
            print(f"   saved {path}. Playing it back...", flush=True)
            subprocess.run(["aplay", "-q", path], check=False)
        except Exception as e:
            print(f"   FAILED: {type(e).__name__}: {e}", flush=True)
        print(flush=True)

    print("Done. Note which settings sounded clear and which sounded garbled.", flush=True)


if __name__ == "__main__":
    main()
