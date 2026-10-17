"""Shared test setup.

engine.config and app.core.paths read their environment variables when they are first imported, so the temp storage
folder and temp config.yaml are created here, before any test file imports the engine or the app.
"""

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
    "providers": {"tts": "fake", "lipsync": "amplitude", "music": "procedural"},
    "features": {"storyboard": True, "music": True},
    "render": {"fps": 24, "chunk_seconds": 30, "x264_preset": "ultrafast", "x264_crf": 30},
    "storyboard": {"frame_count": 3, "preview_seconds": 2},
}

TEST_CONFIG_PATH.write_text(yaml.safe_dump(TEST_CONFIG), encoding="utf-8")
TEST_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
os.environ["TOONFORGE_STORAGE"] = str(TEST_STORAGE_DIR)
os.environ["TOONFORGE_CONFIG"] = str(TEST_CONFIG_PATH)


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
