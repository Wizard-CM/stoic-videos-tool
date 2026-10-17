"""Runs the pipeline stages in order and turns their progress into the events the UI shows."""

from engine.errors import Cancelled
from engine.pipeline.context import PipelineContext
from engine.pipeline.registry import STAGE_LABELS, STAGE_WEIGHTS, STAGES


class ProgressTracker:
    """Works out the overall percent from the stage weights and sends the progress events."""

    def __init__(self, context: PipelineContext, stage_keys: list[str]):
        self.context = context
        self.total_weight = sum(STAGE_WEIGHTS[key] for key in stage_keys)
        self.finished_weight = 0.0

    def percent_now(self, stage: str, fraction: float = 0.0) -> float:
        percent = (self.finished_weight + STAGE_WEIGHTS[stage] * fraction) / self.total_weight * 100
        return round(min(percent, 100.0), 1)

    def send(
        self, stage: str, state: str, percent: float, note: str = "", message: str = "", chunk: dict | None = None, caption: str | None = None
    ) -> None:
        self.context.on_progress({
            "stage": stage,
            "stage_state": state,
            "percent": percent,
            "note": note,
            "message": message or STAGE_LABELS[stage],
            "chunk": chunk,
            "latest_frame_caption": caption,
        })

    def start_stage(self, stage: str) -> None:
        self.send(stage, "active", self.percent_now(stage))

    def update_stage(
        self, stage: str, fraction: float, note: str = "", message: str = "", chunk: dict | None = None, caption: str | None = None
    ) -> None:
        self.send(stage, "active", self.percent_now(stage, fraction), note, message, chunk, caption)

    def finish_stage(self, stage: str, note: str = "") -> None:
        self.finished_weight += STAGE_WEIGHTS[stage]
        self.send(stage, "done", self.percent_now(stage), note)

    def skip_stage(self, stage: str) -> None:
        self.send(stage, "skipped", self.percent_now(stage))


def check_cancel(context: PipelineContext) -> None:
    if context.should_cancel():
        raise Cancelled()


def run_stages(context: PipelineContext, tracker: ProgressTracker, stage_keys: list[str]) -> None:
    """Runs the stages in the given order. Each output is saved in context.outputs[stage key]."""
    for key in stage_keys:
        check_cancel(context)
        tracker.start_stage(key)

        def report(fraction, note="", message="", chunk=None, caption=None) -> None:
            tracker.update_stage(key, fraction, note, message, chunk, caption)

        stage = STAGES[key](report)
        context.outputs[key] = stage.run(context)
        tracker.finish_stage(key, stage.done_note)


def run_pipeline(context: PipelineContext) -> dict:
    stage_keys = context.config.pipeline
    tracker = ProgressTracker(context, stage_keys)
    run_stages(context, tracker, stage_keys)
    return {"output_path": str(context.output_path), "length_s": context.outputs["timeline"]["length_s"]}
