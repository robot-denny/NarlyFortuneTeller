"""Tests for logger.py — the one place logging is configured.

Run from the repo root with:  .venv/bin/python -m pytest -q

Everything here writes to a pytest-provided temporary directory and reads the
log file back from disk, so it needs no hardware, no network, and no .env.
"""

import io
import logging
import logging.handlers
import re
import sys

from logger import configure_logging, get_logger

# The default shape of logging's %(asctime)s, e.g. "2026-09-22 14:03:07,123".
TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3} ")


def _flush_all_handlers():
    """Make sure every buffered record has reached disk before we read it."""
    for handler in logging.getLogger().handlers:
        handler.flush()


def test_each_line_has_timestamp_and_level_and_levels_are_distinguishable(tmp_path):
    """Every line in the log file starts with a timestamp and names its level."""
    log_file = tmp_path / "narly.log"
    configure_logging(str(log_file))

    log = get_logger("test")
    log.info("first message is info")
    log.warning("second message is a warning")
    _flush_all_handlers()

    lines = log_file.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2, f"expected exactly two log lines, got: {lines!r}"

    info_line, warning_line = lines
    for line in (info_line, warning_line):
        assert TIMESTAMP_RE.match(line), f"line does not start with a timestamp: {line!r}"

    assert "INFO" in info_line and "first message is info" in info_line
    assert "WARNING" in warning_line and "second message is a warning" in warning_line
    assert info_line != warning_line


def test_file_rotates_so_no_single_file_exceeds_five_megabytes(tmp_path):
    """Writing more than 5 MB rolls the file over instead of growing it without bound."""
    log_file = tmp_path / "narly.log"
    configure_logging(str(log_file))

    log = get_logger("test")
    one_kilobyte = "x" * 1024
    for _ in range(6000):  # ~6 MB total, comfortably past the 5 MB cap
        log.info(one_kilobyte)
    _flush_all_handlers()

    files = list(tmp_path.glob("narly.log*"))
    assert len(files) > 1, f"expected rotation to produce more than one file, got: {files!r}"
    for f in files:
        assert f.stat().st_size <= 5_000_000, f"{f.name} exceeds 5 MB: {f.stat().st_size} bytes"


def test_configure_logging_twice_does_not_duplicate_output(tmp_path):
    """Calling configure_logging again replaces the old handlers rather than stacking them."""
    log_file = tmp_path / "narly.log"
    configure_logging(str(log_file))
    configure_logging(str(log_file))

    get_logger("test").info("written once")
    _flush_all_handlers()

    lines = log_file.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1, f"expected one line, got: {lines!r}"

    # And the reason there is one line: exactly one of each handler we own, not two.
    # (pytest attaches its own capture handlers to the root logger during a test, so we
    # count only ours rather than asserting on the total.)
    ours = _our_handlers_on_root()
    assert len(ours["file"]) == 1, f"expected one file handler, got {len(ours['file'])}"
    assert len(ours["stdout"]) == 1, f"expected one stdout handler, got {len(ours['stdout'])}"


def _our_handlers_on_root():
    """Split the root logger's handlers into the two kinds configure_logging owns."""
    root = logging.getLogger()
    return {
        "file": [h for h in root.handlers if isinstance(h, logging.handlers.RotatingFileHandler)],
        "stdout": [h for h in root.handlers
                   if isinstance(h, logging.StreamHandler)
                   and not isinstance(h, logging.FileHandler)
                   and getattr(h, "stream", None) is sys.stdout],
    }


def test_configure_logging_leaves_handlers_it_did_not_add_alone(tmp_path):
    """Something else's handler on the root logger (pytest's caplog is the real case)
    survives configure_logging — we only replace the handlers we added ourselves."""
    root = logging.getLogger()
    someone_elses = logging.StreamHandler(io.StringIO())
    root.addHandler(someone_elses)
    try:
        configure_logging(str(tmp_path / "narly.log"))
        assert someone_elses in root.handlers, "configure_logging removed a handler it did not add"
    finally:
        root.removeHandler(someone_elses)


def test_unwritable_log_file_falls_back_to_stdout_instead_of_crashing(capsys):
    """A bad --log-file path must not take the whole program down before the first coin.
    Logging stays on stdout and says what went wrong."""
    configure_logging("/no/such/directory/narly.log")  # must not raise

    ours = _our_handlers_on_root()
    assert len(ours["stdout"]) == 1, "stdout handler missing after file handler failed"
    assert len(ours["file"]) == 0, "a file handler should not exist for an unwritable path"

    out = capsys.readouterr().out
    assert "ERROR" in out and "/no/such/directory/narly.log" in out, (
        f"expected an ERROR line naming the bad path on stdout, got: {out!r}")
