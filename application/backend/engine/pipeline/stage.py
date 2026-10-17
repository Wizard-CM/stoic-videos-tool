"""The base class every pipeline stage follows."""

from collections.abc import Callable

from engine.errors import Cancelled
from engine.pipeline.context import PipelineContext

# report(fraction 0..1, note, message, chunk, caption): the runner turns this into a progress event.
ReportProgress = Callable[..., None]


class Stage:
    key = ""
    done_note = ""

    def __init__(self, report: ReportProgress = lambda *args, **kwargs: None):
        self.report = report

    def run(self, context: PipelineContext):
        raise NotImplementedError

    def check_cancel(self, context: PipelineContext) -> None:
        if context.should_cancel():
            raise Cancelled()
