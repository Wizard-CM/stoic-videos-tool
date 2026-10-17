"""app/services/preflight.py: check_tools, including the "Claude is ready to direct" check that only appears when
the claude director is active and the project's direction has not been cached yet."""

import types

from app.core.paths import project_dir
from app.services import claude as claude_service
from app.services import preflight

PROJECT = {"id": "p-test", "cast": {}}


def _fake_config(director: str, output_folder) -> types.SimpleNamespace:
    return types.SimpleNamespace(providers={"tts": "fake", "director": director}, output_folder=output_folder)


def _check_for(checks: list[dict], key: str) -> dict | None:
    return next((check for check in checks if check["key"] == key), None)


def test_no_claude_check_when_director_is_basic(clean_storage, monkeypatch, tmp_path):
    monkeypatch.setattr(preflight, "load_config", lambda: _fake_config("basic", tmp_path))

    checks = preflight.check_tools(PROJECT)

    assert _check_for(checks, "claude") is None


def test_no_claude_check_when_director_is_basic_even_with_a_cached_direction(clean_storage, monkeypatch, tmp_path):
    direction_dir = project_dir(PROJECT["id"]) / "cache" / "direction"
    direction_dir.mkdir(parents=True)
    (direction_dir / "abc123.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(preflight, "load_config", lambda: _fake_config("basic", tmp_path))

    checks = preflight.check_tools(PROJECT)

    assert _check_for(checks, "claude") is None


def test_claude_check_appears_and_reports_ready_when_direction_is_not_cached(clean_storage, monkeypatch, tmp_path):
    monkeypatch.setattr(preflight, "load_config", lambda: _fake_config("claude", tmp_path))
    monkeypatch.setattr(claude_service, "get_status", lambda: {"ready": True, "message": "Claude is ready."})

    checks = preflight.check_tools(PROJECT)

    assert _check_for(checks, "claude") == {"key": "claude", "label": "Claude is ready to direct", "ok": True, "message": "Claude is ready."}


def test_claude_check_appears_and_reports_not_ready_when_claude_is_signed_out(clean_storage, monkeypatch, tmp_path):
    monkeypatch.setattr(preflight, "load_config", lambda: _fake_config("claude", tmp_path))
    monkeypatch.setattr(claude_service, "get_status", lambda: {"ready": False, "message": "Claude isn't signed in yet."})

    checks = preflight.check_tools(PROJECT)

    assert _check_for(checks, "claude") == {
        "key": "claude", "label": "Claude is ready to direct", "ok": False, "message": "Claude isn't signed in yet.",
    }


def test_no_claude_check_when_direction_is_already_cached(clean_storage, monkeypatch, tmp_path):
    direction_dir = project_dir(PROJECT["id"]) / "cache" / "direction"
    direction_dir.mkdir(parents=True)
    (direction_dir / "abc123.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(preflight, "load_config", lambda: _fake_config("claude", tmp_path))
    monkeypatch.setattr(claude_service, "get_status", lambda: {"ready": True, "message": "Claude is ready."})

    checks = preflight.check_tools(PROJECT)

    assert _check_for(checks, "claude") is None
