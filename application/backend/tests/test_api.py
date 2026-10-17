"""The HTTP API without Claude: starter library, characters, backgrounds, options, projects and cast, Claude status."""

import pytest
from fastapi.testclient import TestClient

PNG_START = b"\x89PNG"


@pytest.fixture
def client(clean_storage):
    from app.main import app

    with TestClient(app) as test_client:  # "with" runs the startup that copies the starter library
        yield test_client


def test_starter_library_has_the_example_characters_and_backgrounds(client):
    characters = client.get("/api/characters").json()
    assert {character["id"] for character in characters} == {"jade-example", "ron-example"}
    assert "kit" not in characters[0] and "point" in next(c for c in characters if c["id"] == "jade-example")["gestures"]

    backgrounds = client.get("/api/backgrounds").json()
    assert {background["id"] for background in backgrounds} == {"office-example", "night-city-example"}
    assert "art" not in backgrounds[0]


def test_options_list_emotions_gestures_voices_and_settings(client):
    options = client.get("/api/options").json()
    assert {"emotions", "gestures", "voices", "genders", "ages", "aspects", "qualities", "script_lengths", "max_length_s"} <= set(options)
    assert {"value": "angry", "label": "Angry"} in options["emotions"]


def test_character_detail_previews_and_sheets(client):
    jade = client.get("/api/characters/jade-example").json()
    assert jade["kit"]["format"] == "toonforge-kit/1" and "angry" in jade["expressions"]

    for url in [
        "/api/characters/jade-example/preview.png?expression=angry&gesture=point",
        "/api/characters/jade-example/sheet.png?sheet=mouths",
        "/api/characters/jade-example/avatar.png?size=64",
        "/api/backgrounds/office-example/preview.png?width=320&character_id=jade-example",
    ]:
        response = client.get(url)
        assert response.status_code == 200, url
        assert response.content.startswith(PNG_START)

    assert client.get("/api/characters/jade-example/sheet.png?sheet=nope").status_code == 422
    assert client.get("/api/characters/nobody").status_code == 404


def test_character_metadata_update_repicks_an_auto_voice(client):
    ron = client.put("/api/characters/ron-example", json={"name": "Ronald", "voice": {"voice_id": "ryan", "auto": True}}).json()
    assert ron["name"] == "Ronald" and ron["voice"]["voice_id"] == "ryan"

    changed = client.put("/api/characters/ron-example", json={"gender": "female"}).json()
    assert changed["gender"] == "female"
    assert changed["voice"]["voice_id"] != "ryan"  # auto voice follows the new gender
    assert client.put("/api/characters/ron-example", json={"age": "ancient"}).status_code == 422


def test_export_then_import_keeps_the_kit(client):
    exported = client.get("/api/characters/jade-example/export").json()
    client.delete("/api/characters/jade-example")
    imported = client.post("/api/characters/import", json=exported)
    assert imported.status_code == 201
    assert imported.json()["id"] == "jade-example" and imported.json()["kit"] == exported["kit"]

    broken = {**exported, "kit": {**exported["kit"], "mouths": {}}}
    assert client.post("/api/characters/import", json=broken).status_code == 422


def test_cast_and_background_choice(client):
    project = client.post("/api/projects", json={"title": "Delegation"}).json()
    client.put(f"/api/projects/{project['id']}", json={"script": "JADE [angry]: You knew!\nRON [smug]: Of course."})

    assert client.put(f"/api/projects/{project['id']}/cast/JADE/background", json={"library_id": "office-example"}).status_code == 409
    client.put(f"/api/projects/{project['id']}/cast/JADE", json={"library_id": "jade-example"})
    project = client.put(f"/api/projects/{project['id']}/cast/JADE/background", json={"library_id": "office-example"}).json()
    entry = project["cast"]["JADE"]
    assert entry["library_id"] == "jade-example" and entry["background_library_id"] == "office-example"
    assert entry["background"]["art"]["format"] == "toonforge-background/1"

    project = client.put(f"/api/projects/{project['id']}/cast/JADE", json={"library_id": "ron-example"}).json()
    assert project["cast"]["JADE"]["background_library_id"] == "office-example"  # a new character keeps the background choice
    project = client.put(f"/api/projects/{project['id']}/cast/JADE/background", json={"library_id": None}).json()
    assert project["cast"]["JADE"]["background"] is None
    assert client.get(f"/api/projects/{project['id']}/thumbnail.png").content.startswith(PNG_START)


def test_claude_is_ready_in_test_mode_and_generation_starts_a_task(client, no_task_process):
    status = client.get("/api/claude/status").json()
    assert status["ready"] is True and status["message"]
    assert status["models"]["lead"] == "claude-opus-5-5"
    assert client.post("/api/claude/test").json()["ok"] is True
    assert client.get("/api/claude/tasks").json() == []

    response = client.post("/api/characters/generate", json={"name": "Max", "description": "a tired barista"})
    assert response.status_code == 202
    task_id = response.json()["task_id"]
    assert response.json() == {"task_id": task_id} and task_id.startswith("t-")

    task = client.get(f"/api/claude/tasks/{task_id}").json()
    assert task["state"] == "queued" and task["title"] == "Designing Max" and "_pid" not in task
    assert [listed["id"] for listed in client.get("/api/claude/tasks").json()] == [task_id]
    assert client.post(f"/api/claude/tasks/{task_id}/cancel").json()["id"] == task_id
    assert client.get("/api/claude/tasks/t-000000").status_code == 404

    revise = client.post("/api/characters/jade-example/revise", json={"feedback": "a red scarf"})
    assert revise.status_code == 202 and revise.json()["task_id"].startswith("t-")
    assert client.post("/api/backgrounds/generate", json={"name": "Office", "description": "a calm office"}).status_code == 202
