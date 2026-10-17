"""Shared test setup.

engine.config and app.core.paths read their environment variables when they are first imported, so the temp storage
folder and temp config.yaml are created here, before any test file imports the engine or the app.
"""

import copy
import json
import os
import shutil
import tempfile
from pathlib import Path

import pytest
import yaml

TEST_HOME = Path(tempfile.mkdtemp(prefix="toonforge_tests_"))
TEST_STORAGE_DIR = TEST_HOME / "storage"
TEST_CONFIG_PATH = TEST_HOME / "config.yaml"
TEST_OUTPUT_DIR = TEST_HOME / "videos"

TEST_CONFIG = {
    "output_folder": str(TEST_OUTPUT_DIR),
    "providers": {"tts": "fake", "lipsync": "amplitude", "music": "procedural", "director": "basic"},
    "features": {"storyboard": True, "music": True},
    "render": {"fps": 24, "chunk_seconds": 30, "x264_preset": "ultrafast", "x264_crf": 30},
    "storyboard": {"frame_count": 3, "preview_seconds": 2},
}

TEST_CONFIG_PATH.write_text(yaml.safe_dump(TEST_CONFIG), encoding="utf-8")
TEST_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
os.environ["TOONFORGE_STORAGE"] = str(TEST_STORAGE_DIR)
os.environ["TOONFORGE_CONFIG"] = str(TEST_CONFIG_PATH)
# Tests never call the real Claude: the Claude layer writes the example files instead.
os.environ["TOONFORGE_FAKE_CLAUDE"] = "1"

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
_MINI_KIT = json.loads((FIXTURES_DIR / "mini_kit.json").read_text(encoding="utf-8"))
_MINI_BACKGROUND = json.loads((FIXTURES_DIR / "mini_background.json").read_text(encoding="utf-8"))


def pytest_sessionfinish(session, exitstatus):
    shutil.rmtree(TEST_HOME, ignore_errors=True)


@pytest.fixture(scope="session")
def storage_dir() -> Path:
    """The temp folder every app and worker process stores into (TOONFORGE_STORAGE)."""
    assert os.environ["TOONFORGE_STORAGE"] == str(TEST_STORAGE_DIR)
    return TEST_STORAGE_DIR


@pytest.fixture
def clean_storage(storage_dir):
    """An empty storage folder for one test."""
    for child in storage_dir.iterdir():
        if child.is_dir():
            shutil.rmtree(child, ignore_errors=True)
        else:
            child.unlink()
    return storage_dir


@pytest.fixture(scope="session")
def temp_config():
    """The engine config read from the temp config.yaml (fake voices, amplitude lip sync)."""
    from engine.config import load_config

    load_config.cache_clear()
    config = load_config()
    assert config.providers["tts"] == "fake"
    assert config.providers["lipsync"] == "amplitude"
    return config


@pytest.fixture
def small_script() -> str:
    from helpers import SMALL_SCRIPT

    return SMALL_SCRIPT


@pytest.fixture
def mini_kit() -> dict:
    """A small but complete puppet kit (simple shapes, every required key). A fresh copy per test."""
    return copy.deepcopy(_MINI_KIT)


@pytest.fixture
def mini_background() -> dict:
    """A small but complete background art dict. A fresh copy per test."""
    return copy.deepcopy(_MINI_BACKGROUND)


@pytest.fixture
def mini_character(mini_kit) -> dict:
    """A character record around the mini kit (not saved anywhere)."""
    return {
        "id": None, "name": "Jade", "description": "test character", "gender": "female", "age": "adult",
        "voice": {"voice_id": "amy", "auto": True, "pitch": 0.0, "speed": 0.0},
        "kit": mini_kit, "seed": 4242, "made_by": None,
    }


class FakeTaskProcess:
    """Stands in for a Claude task process: never starts, and counts as alive (it has this test's pid)."""

    def __init__(self, target, args):
        self.target = target
        self.args = args
        self.pid = os.getpid()

    def start(self):
        pass

    def is_alive(self):
        return True

    def terminate(self):
        pass


@pytest.fixture
def no_task_process(monkeypatch):
    """start_task makes FakeTaskProcess objects instead of real processes. Returns them, so a test can run
    run_claude_task(*process.args) itself, in this process."""
    from app.jobs import claude_tasks
    from app.jobs.processes import started_processes

    made = []

    def make_process(target, args):
        process = FakeTaskProcess(target, args)
        made.append(process)
        return process

    class FakeContext:
        Process = staticmethod(make_process)

    monkeypatch.setattr(claude_tasks.multiprocessing, "get_context", lambda method: FakeContext)
    yield made
    started_processes.pop(os.getpid(), None)
