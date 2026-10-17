"""Lip sync with the Rhubarb command line tool. Falls back to the amplitude method if Rhubarb fails to run."""

import json
import subprocess
import tempfile
from pathlib import Path

from engine.audio.wavio import read_wav
from engine.config import find_tool
from engine.lipsync.amplitude import AmplitudeProvider
from engine.lipsync.base import LIPSYNC_PROVIDERS, LipSyncProvider

MIN_TIMEOUT_SECONDS = 60
TIMEOUT_PER_AUDIO_SECOND = 4


class RhubarbProvider(LipSyncProvider):
    def analyze(self, wav_path: Path, text: str) -> list[tuple[float, float, str]]:
        try:
            cues = self._run_rhubarb(Path(wav_path), text)
        except (subprocess.SubprocessError, OSError, ValueError, KeyError):
            cues = []
        if not cues:
            return AmplitudeProvider().analyze(wav_path, text)
        return cues

    def _run_rhubarb(self, wav_path: Path, text: str) -> list[tuple[float, float, str]]:
        samples, sample_rate = read_wav(wav_path)
        timeout = max(MIN_TIMEOUT_SECONDS, TIMEOUT_PER_AUDIO_SECOND * len(samples) / sample_rate)

        with tempfile.TemporaryDirectory(prefix="rhubarb_") as temp_dir:
            dialog_file = Path(temp_dir) / "dialog.txt"
            dialog_file.write_text(text, encoding="utf-8")
            command = [find_tool("rhubarb"), "-q", "-f", "json", "--extendedShapes", "GHX", "-d", str(dialog_file), str(wav_path)]
            result = subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=True)

        mouth_cues = json.loads(result.stdout)["mouthCues"]
        return [(float(cue["start"]), float(cue["end"]), cue["value"]) for cue in mouth_cues]


LIPSYNC_PROVIDERS["rhubarb"] = RhubarbProvider
