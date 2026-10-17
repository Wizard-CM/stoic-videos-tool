"""Director providers: who writes the direction. "basic" is built in; "claude" lives in claude_layer.director."""

import importlib
from collections.abc import Callable
from pathlib import Path

from engine.direction.basic import basic_direction
from engine.errors import PipelineError

CLAUDE_DIRECTOR_MODULE = "claude_layer.director"


class DirectorProvider:
    def direct(
        self,
        brief: dict,
        workspace: Path,
        report: Callable[[float, str], None],
        should_cancel: Callable[[], bool],
        cast: dict | None = None,
        backgrounds: dict | None = None,
    ) -> dict:
        """{"direction", "backgrounds": {SPEAKER: art}, "notes", "cost_usd"}. cast and backgrounds are the kits and chosen art."""
        raise NotImplementedError


class BasicDirector(DirectorProvider):
    def direct(
        self,
        brief: dict,
        workspace: Path,
        report: Callable[[float, str], None],
        should_cancel: Callable[[], bool],
        cast: dict | None = None,
        backgrounds: dict | None = None,
    ) -> dict:
        return {"direction": basic_direction(brief), "backgrounds": {}, "notes": "Basic rule-based direction (offline).", "cost_usd": None}


DIRECTOR_PROVIDERS: dict[str, type[DirectorProvider]] = {"basic": BasicDirector}


def get_director_provider(name: str) -> DirectorProvider:
    if name == "claude" and "claude" not in DIRECTOR_PROVIDERS:
        try:
            importlib.import_module(CLAUDE_DIRECTOR_MODULE)  # registers DIRECTOR_PROVIDERS["claude"]
        except Exception as error:  # noqa: BLE001 - any failure here means the Claude director is unusable
            raise PipelineError(f"The Claude director could not be loaded ({error}). Choose the basic director or check the install.") from error
        if "claude" not in DIRECTOR_PROVIDERS:
            raise PipelineError("The Claude director could not be loaded. Choose the basic director or check the install.")
    if name not in DIRECTOR_PROVIDERS:
        raise PipelineError(f"Unknown director '{name}'. Use one of: {', '.join(sorted(set(DIRECTOR_PROVIDERS) | {'claude'}))}.")
    return DIRECTOR_PROVIDERS[name]()
