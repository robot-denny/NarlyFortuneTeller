# logger.py - One place to set up logging for the whole program.
#
# Every module does:
#     from logger import get_logger
#     log = get_logger(__name__)
# and then calls log.info(...) / log.warning(...) / log.error(...) instead of print().
#
# main() in serial_trigger.py calls configure_logging() once at startup. Until it
# does, Python's built-in fallback still shows WARNING and above on stderr, so a
# module imported on its own (for example by app.py) never loses a warning.

import logging
import logging.handlers
import sys

# One line per event, e.g.:
#   2026-09-22 14:03:07,123 INFO capture outcome=heard heard="will it rain" secs=4.2
# Greppable by eye and by `grep -c 'outcome=no_speech' narly.log`.
# The level is padded to 8 characters so every message starts in the same column
# whatever its severity (INFO is 4 letters, WARNING is 7) — the leading indentation
# in the messages only lines up if the prefix is a fixed width.
LOG_FORMAT = "%(asctime)s %(levelname)-8s %(message)s"

# The optional log file rolls over at 5 MB and keeps 3 old copies
# (narly.log, narly.log.1, narly.log.2, narly.log.3), so it never grows without bound.
MAX_BYTES = 5_000_000
BACKUP_COUNT = 3

# Third-party libraries that log at INFO on every request. Their lines would land in
# the operator's event log once per fortune, so they are held to WARNING and above.
NOISY_LIBRARIES = ("httpx", "httpcore", "openai", "urllib3")

# The handlers THIS module attached last time configure_logging ran. We remove only
# these on a repeat call — never anything someone else put on the root logger
# (pytest's log capture, for one), which we have no business touching.
_our_handlers: list[logging.Handler] = []


def configure_logging(log_file: str | None = None, level=logging.INFO):
    """Set up where log lines go. Call once at startup.

    Two possible destinations ("handlers" in logging's vocabulary):

    1. stdout — ALWAYS attached. This is what you see in the terminal, and on
       the Raspberry Pi it is what journald collects, so it is the one sink
       that is always on.
    2. A rotating file — attached ONLY when `log_file` is given (the `--log-file`
       flag). It is capped at 5 MB per file with 3 backups, so a day at a
       festival cannot fill the disk.

    Both destinations use the same one-line format: timestamp, level, message.

    Safe to call more than once: the handlers this function attached last time are
    removed first, so repeated calls (tests do this) never duplicate output. Handlers
    added by anything else are left alone.

    If the log file cannot be opened, logging carries on to stdout alone and one
    ERROR line says why — a bad path must never stop the fortune teller starting.
    """
    root = logging.getLogger()
    root.setLevel(level)

    # Remove only what we added last time, so calling this twice does not double
    # every line — and so we leave other people's handlers alone.
    for handler in _our_handlers:
        root.removeHandler(handler)
        handler.close()
    _our_handlers.clear()

    formatter = logging.Formatter(LOG_FORMAT)

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(formatter)
    root.addHandler(stdout_handler)
    _our_handlers.append(stdout_handler)

    if log_file:
        # A bad path (typo, unmounted drive, no permission) must not take the whole
        # program down before the first coin. Stay on stdout and say what happened.
        try:
            file_handler = logging.handlers.RotatingFileHandler(
                log_file, maxBytes=MAX_BYTES, backupCount=BACKUP_COUNT, encoding="utf-8"
            )
        except OSError as e:
            logging.getLogger(__name__).error(
                "✗ Could not open log file %s (%s) — logging to stdout only", log_file, e
            )
        else:
            file_handler.setFormatter(formatter)
            root.addHandler(file_handler)
            _our_handlers.append(file_handler)

    for name in NOISY_LIBRARIES:
        logging.getLogger(name).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Return the logger for a module. Use `get_logger(__name__)` at the top of each file."""
    return logging.getLogger(name)
