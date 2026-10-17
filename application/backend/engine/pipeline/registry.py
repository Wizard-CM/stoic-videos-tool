"""Stage lookup by key, with the names shown to the user and each stage's share of the progress bar."""

from engine.pipeline.stage import Stage
from engine.pipeline.stages import (
    CastStage,
    DirectStage,
    EncodeStage,
    LipSyncStage,
    MixStage,
    ParseStage,
    RenderStage,
    TimelineStage,
    VoiceStage,
)

STAGE_CLASSES: list[type[Stage]] = [
    ParseStage, CastStage, VoiceStage, LipSyncStage, DirectStage, TimelineStage, MixStage, RenderStage, EncodeStage,
]
STAGES: dict[str, type[Stage]] = {stage_class.key: stage_class for stage_class in STAGE_CLASSES}

STAGE_LABELS = {
    "parse": "Check script",
    "cast": "Load characters",
    "voice": "Make voices",
    "lipsync": "Match mouths",
    "direct": "Direct the video (Claude)",
    "timeline": "Plan the timeline",
    "mix": "Mix audio",
    "render": "Draw frames",
    "encode": "Join and save MP4",
}
BASIC_DIRECTOR_LABEL = "Direct the video"

# Voice, directing (Claude) and render take the longest, so they get the biggest share.
STAGE_WEIGHTS = {
    "parse": 1,
    "cast": 1,
    "voice": 18,
    "lipsync": 8,
    "direct": 15,
    "timeline": 1,
    "mix": 4,
    "render": 48,
    "encode": 4,
}


def stage_label(key: str, providers: dict | None = None) -> str:
    """The label shown for a stage. The direct stage only mentions Claude when Claude is the director."""
    if key == "direct" and (providers or {}).get("director", "claude") != "claude":
        return BASIC_DIRECTOR_LABEL
    return STAGE_LABELS[key]
