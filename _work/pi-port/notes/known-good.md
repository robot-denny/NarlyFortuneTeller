# Known-good laptop build

Step 1 of `_work/pi-port/plan.md`.

- **Tag**: `laptop-known-good-2026-09-28` (annotated)
- **Commit**: `c8bb755` (`c8bb755307580b015e53bebbb3040122dff3fbcd`), the `main` head that scored 95% on 2026-09-28
- **Message**: "Known-good laptop build: 95% baseline, before the Pi port"
- **Pushed to `origin`**: yes, 2026-09-28. `git ls-remote --tags origin laptop-known-good-2026-09-28` shows it.

## Going back to it on the laptop

From `/Users/dkardys/Sites/fortune-service`. Commit or stash any changes first (`git stash`), or
`git switch` refuses to run:

```
git fetch --tags
git switch --detach laptop-known-good-2026-09-28
```

The shared `.venv` works on it as is. No new Python dependencies came after this tag.

## Check that the tag runs (2026-09-28)

Run from a scratch worktree of the tag (`git worktree add ../narly-known-good laptop-known-good-2026-09-28`),
using `/Users/dkardys/Sites/fortune-service/.venv/bin/python`. The worktree was removed afterwards.

`serial_trigger.py --list-personas` exited 0:

```
Available personas:
  default
  music
  umbraco-2025
```

`serial_trigger.py --mode simulate --dry-run --offline --question "Will I find treasure today?"`,
with `--auto --interval 60` added. Without a keyboard the Enter prompt ends the run at once, so one
coin was fired automatically and the run was stopped with Ctrl+C (SIGINT) after the ticket. It exited 0:

```
INFO     capture outcome=heard heard="Will I find treasure today?" secs=1.9
INFO     question source=heard text="Will I find treasure today?"
INFO       ✓ Fortune generated (43 chars)

--- DRY RUN OUTPUT ---
        - Your Fortune -
--------------------------------
[TEST FORTUNE] You will find
what you seek.
--------------------------------
            - Narly
--- END DRY RUN ---

INFO     ✓ Fortune cycle complete
INFO     🛑 Exiting simulation mode.
```

Result: pass. The tagged code runs on the shared `.venv` and prints a `[TEST FORTUNE]` ticket offline.
