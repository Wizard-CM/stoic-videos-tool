"""Errors the engine raises on purpose. Their message is shown to the user as-is."""


class PipelineError(Exception):
    """Something the user can fix (script too long, missing tool, bad cast...)."""


class Cancelled(Exception):
    """The user pressed Cancel. Raised from inside long loops when should_cancel() is True."""
