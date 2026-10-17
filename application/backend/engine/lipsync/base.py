"""Lip sync: the provider base class and the provider registry."""

from pathlib import Path

from engine.config import find_tool
from engine.errors import PipelineError

LIPSYNC_PROVIDERS: dict[str, type["LipSyncProvider"]] = {}
_provider_instances: dict[str, "LipSyncProvider"] = {}


class LipSyncProvider:
    def analyze(self, wav_path: Path, text: str) -> list[tuple[float, float, str]]:
        """Mouth cues as (start_s, end_s, shape), shape being one of the VISEMES (X, A-H). Covers the whole file."""
        raise NotImplementedError


def get_lipsync_provider(name: str) -> LipSyncProvider:
    # Importing the provider modules fills LIPSYNC_PROVIDERS (done here to avoid circular imports).
    from engine.lipsync import amplitude, rhubarb  # noqa: F401

    if name == "rhubarb" and find_tool("rhubarb") is None:
        name = "amplitude"
    if name not in LIPSYNC_PROVIDERS:
        raise PipelineError(f"Unknown lip sync engine '{name}'. Use one of: {', '.join(sorted(LIPSYNC_PROVIDERS))}.")
    if name not in _provider_instances:
        _provider_instances[name] = LIPSYNC_PROVIDERS[name]()
    return _provider_instances[name]
