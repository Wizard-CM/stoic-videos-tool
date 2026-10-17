"""The Claude settings from config.yaml ("claude:"), the API key and the offline test switch."""

import os

from engine.config import DEFAULT_CLAUDE, load_config

FAKE_ENV = "TOONFORGE_FAKE_CLAUDE"
EFFORT_LEVELS = ("low", "medium", "high", "xhigh", "max")


def claude_settings() -> dict:
    """Lead and worker models, effort, limits, the API key variable name and the CLI path, with defaults filled in."""
    raw = load_config().claude or {}
    settings = {**DEFAULT_CLAUDE, **raw}
    settings["workers"] = {**DEFAULT_CLAUDE["workers"], **(raw.get("workers") or {})}
    if settings["effort"] not in EFFORT_LEVELS:
        settings["effort"] = DEFAULT_CLAUDE["effort"]
    settings["max_turns"] = int(settings["max_turns"] or DEFAULT_CLAUDE["max_turns"])
    settings["max_parallel_workers"] = max(1, int(settings["max_parallel_workers"] or 1))
    budget = settings.get("max_budget_usd")
    settings["max_budget_usd"] = float(budget) if budget not in (None, "", 0) else None
    settings["api_key_env"] = settings.get("api_key_env") or "ANTHROPIC_API_KEY"
    settings["cli_path"] = settings.get("cli_path") or None
    return settings


def fake_mode() -> bool:
    """TOONFORGE_FAKE_CLAUDE=1: tests and offline UI work; no Claude call is ever made."""
    return os.environ.get(FAKE_ENV, "").strip().lower() in ("1", "true", "yes", "on")


def api_key(settings: dict | None = None) -> str | None:
    """The Anthropic API key from the environment variable named in config.yaml, if set."""
    settings = settings or claude_settings()
    value = os.environ.get(settings["api_key_env"], "").strip()
    return value or None


def model_names(settings: dict | None = None) -> dict:
    """{"lead": ..., "workers": {"sonnet": ..., "haiku": ...}} for the status route and made_by."""
    settings = settings or claude_settings()
    return {"lead": settings["lead_model"], "workers": dict(settings["workers"])}
