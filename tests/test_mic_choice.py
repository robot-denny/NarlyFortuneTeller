"""Tests for choosing the microphone by name.

The computer's default input is not always the Fifine AM8: on the Pi,
plugging it in reorders the sound devices, and on the laptop the default can
be the built-in mic. So Narly looks the mic up by part of the name it
reports (`MIC_NAME` in `.env`, default `fifine`) and falls back to the default
input when nothing matches.

No real audio device is opened here: the names are plain lists, and the
microphone class is replaced with a stand-in that only records what it was
asked for.
"""

import serial_trigger


PI_NAMES = ["bcm2835 Headphones: - (hw:0,0)", "AM8: USB Audio (hw:2,0)", "default"]


def test_picks_the_device_whose_name_contains_the_wanted_text():
    assert serial_trigger.pick_mic_index(PI_NAMES, "AM8") == 1


def test_the_match_ignores_upper_and_lower_case():
    assert serial_trigger.pick_mic_index(PI_NAMES, "am8") == 1


def test_no_match_means_the_default_input():
    assert serial_trigger.pick_mic_index(["MacBook Pro Microphone"], "AM8") is None


def test_an_empty_wanted_name_means_the_default_input():
    assert serial_trigger.pick_mic_index(PI_NAMES, "") is None


def test_the_real_mic_provider_opens_the_chosen_device(monkeypatch):
    opened = []

    class RecordingMicrophone:
        def __init__(self, device_index=None):
            opened.append(device_index)

        def __enter__(self):
            # Stop here: the test only cares which device was asked for.
            raise RuntimeError("stand-in mic, nothing to record")

        def __exit__(self, *exc):
            return False

    monkeypatch.setattr(serial_trigger.sr, "Microphone", RecordingMicrophone)
    monkeypatch.setattr(serial_trigger, "_mic_index", 1, raising=False)

    try:
        serial_trigger.mic_get_audio(on_ready=lambda: None)
    except RuntimeError:
        pass

    assert opened == [1]


# The names macOS listed on the owner's laptop on 2026-09-29. The Fifine AM8
# reports itself as "fifine Microphone": the model number isn't in the name.
LAPTOP_NAMES = ["Dennis's iPhone Microphone", "fifine Microphone", "MacBook Pro Microphone",
                "MacBook Pro Speakers", "Microsoft Teams Audio"]


def test_with_no_mic_name_set_the_am8_is_found_on_the_laptop(monkeypatch):
    monkeypatch.setattr(serial_trigger.sr.Microphone, "list_microphone_names",
                        staticmethod(lambda: LAPTOP_NAMES))
    assert serial_trigger.choose_mic(env={}) == 1


def test_mic_name_in_env_overrides_the_default(monkeypatch):
    monkeypatch.setattr(serial_trigger.sr.Microphone, "list_microphone_names",
                        staticmethod(lambda: LAPTOP_NAMES))
    assert serial_trigger.choose_mic(env={"MIC_NAME": "MacBook Pro Microphone"}) == 2
