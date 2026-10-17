"""Stage lookup by key, with the names shown to the user and each stage's share of the progress bar."""

from engine.pipeline.stage import Stage
from engine.pipeline.stages import (
    CastStage,
    EmotionStage,
    EncodeStage,
    LipSyncStage,
    MixStage,
    ParseStage,
    RenderStage,
    TimelineStage,
    VoiceStage,
)

STAGE_CLASSES: list[type[Stage]] = [
    ParseStage, CastStage, VoiceStage, LipSyncStage, EmotionStage, TimelineStage, MixStage, RenderStage, EncodeStage,
]
STAGES: dict[str, type[Stage]] = {stage_class.key: stage_class for stage_class in STAGE_CLASSES}

STAGE_LABELS = {
    "parse": "Check script",
    "cast": "Load characters",
    "voice": "Make voices",
    "lipsync": "Match mouths",
    "emotion": "Set expressions",
    "timeline": "Plan shots",
    "mix": "Mix audio",
    "render": "Draw frames",
    "encode": "Join and save MP4",
}

# Voice and render take the longest, so they get the biggest share.
STAGE_WEIGHTS = {
    "parse": 1,
    "cast": 1,
    "voice": 20,
    "lipsync": 10,
    "emotion": 1,
    "timeline": 2,
    "mix": 5,
    "render": 55,
    "encode": 5,
}
