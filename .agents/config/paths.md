# Paths

## Code layout

Flat module layout — every Python module sits at the repo root, one module per concern, no
package directory. Follow it; do not introduce a `src/` or package structure for a single new
module.

| Path | Holds |
|---|---|
| `serial_trigger.py` | Main orchestrator — coin → mic → STT → AI → print. The real entry point. |
| `app.py` | Standalone test entry point; skips coin detection and the mic. |
| `ai_client.py` | OpenAI integration — `init_ai(persona)` at startup, then `get_ai_response(question)`. |
| `config_loader.py` | `load_config(persona)`, `list_personas()`. Resolves paths relative to the file, not cwd. |
| `formatters.py` | `render_ticket(message, config)` — 32-char thermal ticket layout. |
| `print_client.py` | Thermal printer driver (ESC/POS). |
| `led_client.py` | Arduino LED control over serial. |
| `personas/<name>/` | `content.json` + `prompts.md` per persona. Currently `default`, `music`, `umbraco-2025`. |
| `sfx/` | Sound effects (mp3), resolved from `_BASE_DIR / "sfx"`. |
| `arduino/fortune-controller/` | The Arduino sketch (`.ino`). |
| `docs/` | Durable reference — `narly-behavior.md`, `v2-upgrade-plan.md`, `reference/` wiring photos. |

A new client for an external device belongs at the root as `<thing>_client.py`, matching
`print_client.py` and `led_client.py`.

## Generated output

From `.gitignore`: `.venv/`, `__pycache__/`, `*.pyc`, `*.pyo`, `*.pyd`, `*.db`, `*.sqlite3`,
`*.wav`, `.DS_Store`, and `.env`.

`*.wav` is ignored because captured mic audio lands in the working tree — recorded input, not
source. `.env` holds the OpenAI key and printer settings; `.env.example` is the committed
template and is **not** generated.

## Workspace

The toolkit default layout, placed by `/setup`. The project had no competing specs-or-plans
convention, so there is no split to reconcile.

| Path | Holds | Committed |
|---|---|---|
| `ROADMAP.md` | Now / Next / Later / Recently shipped | yes |
| `_features/<area>.md` | One file per capability, named by area | yes |
| `_work/<slug>/` | One increment: `spec.md`, `plan.md`, `discovery.md`, `notes/`, `assets/` | yes |
| `_work/shipped/<slug>/` | Archived increments, moved as a unit | yes |
| `docs/` | Durable human reference — already in use, pre-dates the toolkit | yes |
| `docs/audits/` | Dated audit reports | yes |
| `_scratch/` | Disposable artifacts | no — git-ignored wholesale |

`docs/` already held the project's own reference material before setup ran; the toolkit writes
alongside it rather than taking it over.
