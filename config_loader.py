from pathlib import Path
import json

from logger import get_logger

log = get_logger(__name__)

# Resolve paths relative to this file, not the working directory
_BASE_DIR = Path(__file__).resolve().parent


def list_personas():
    """Return sorted list of available persona names."""
    personas_dir = _BASE_DIR / "personas"
    if not personas_dir.exists():
        return []
    return sorted(
        p.name for p in personas_dir.iterdir()
        if p.is_dir() and (p / "content.json").exists()
    )


def load_config(persona: str = "default"):
    """Load persona config from personas/<persona>/content.json.

    Resolves system_prompt_file relative to the persona directory.
    Falls back to 'default' persona if the requested one doesn't exist.
    """
    persona_dir = _BASE_DIR / "personas" / persona

    if not persona_dir.exists():
        log.warning(f"  persona '{persona}' not found, falling back to 'default'")
        persona = "default"
        persona_dir = _BASE_DIR / "personas" / "default"

    config_path = persona_dir / "content.json"
    if not config_path.exists():
        raise FileNotFoundError(f"No content.json found in {persona_dir}")

    cfg = json.loads(config_path.read_text(encoding="utf-8"))

    # Resolve system_prompt_file relative to the persona directory
    prompt_file = cfg.get("system_prompt_file")
    if prompt_file:
        prompt_path = (persona_dir / prompt_file).resolve()
        if not prompt_path.exists():
            raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
        cfg["system_prompt"] = prompt_path.read_text(encoding="utf-8")

    if "system_prompt" not in cfg or not cfg["system_prompt"].strip():
        raise ValueError(
            f"system_prompt is empty for persona '{persona}'. "
            "Check prompts.md or content.json in the persona directory."
        )

    # Stash persona name for downstream use
    cfg["_persona_name"] = persona

    return cfg
