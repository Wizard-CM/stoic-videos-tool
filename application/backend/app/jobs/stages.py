"""The stage list shown in the Job, and how a progress event from the engine changes it."""

from engine.config import load_config
from engine.pipeline.registry import STAGE_LABELS

STORYBOARD_LAST_STAGE = "timeline"


def _new_stage(key: str) -> dict:
    return {"key": key, "label": STAGE_LABELS.get(key, key.capitalize()), "state": "waiting", "note": ""}


def new_stages(kind: str) -> list[dict]:
    keys = load_config().pipeline
    if kind == "storyboard" and STORYBOARD_LAST_STAGE in keys:
        keys = keys[: keys.index(STORYBOARD_LAST_STAGE) + 1]
    return [_new_stage(key) for key in keys]


def apply_stage_event(stages: list[dict], event: dict) -> None:
    """Update one stage from the event. A stage the list does not know yet is added at the end."""
    stage = next((stage for stage in stages if stage["key"] == event["stage"]), None)
    if stage is None:
        stage = _new_stage(event["stage"])
        stages.append(stage)
    stage["state"] = event["stage_state"]
    stage["note"] = event.get("note") or ""
