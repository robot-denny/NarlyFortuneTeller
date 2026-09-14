# Code review — project rules

- **Secrets.** The OpenAI key and printer settings live in `.env` (git-ignored). A key, port, or
  endpoint appearing in a tracked file is a blocker. A new setting must also land in
  `.env.example`.
- **Persona content must not migrate into code.** Tone, rules, ticket header/footer and the
  default question belong in `personas/<name>/prompts.md` and `content.json` so non-developers
  can edit them. Fortune wording hardcoded in a `.py` file is a finding.
- **Path resolution.** Modules must locate `personas/` and `sfx/` via `config_loader.py`'s
  file-relative `_BASE_DIR`, never via the working directory. A bare relative path or
  `os.getcwd()` breaks loading silently.
- **Graceful degradation is a contract, not a nicety.** `led_client.py` tolerates a missing
  Arduino; printer and mic paths tolerate missing hardware. Code that assumes a device is
  present breaks `--mode simulate --dry-run`, which is the only desk-testable path.
- **Every failure path still prints.** An exception that escapes without a fallback slip is a
  blocker — a paying guest gets nothing. Watch for swallowed exceptions too: a bare `except:
  pass` around the AI or printer call hides the failure instead of triggering the fallback.
- **Timeouts.** Mic capture, the OpenAI call, and printing each carry a timeout. A new blocking
  call without one can hang the machine mid-festival.
- **Ticket width is 32 characters.** `formatters.py` owns that wrapping. Changes to fortune
  length or ticket furniture must respect it.
- **Style.** Flat modules at the repo root, one concern each; external devices as
  `<thing>_client.py`. Plain `print()` for user-facing output is the current idiom — Phase 3
  replaces it with `logging`, so flag new `print()` calls only once that migration has started.
