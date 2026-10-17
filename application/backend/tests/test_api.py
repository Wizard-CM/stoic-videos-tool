import shutil
import time

import pytest
from fastapi.testclient import TestClient
from helpers import SMALL_SCRIPT

from engine.config import find_tool

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
MISSING_PROJECT_ID = "p-000000"
JOB_TIMEOUT_SECONDS = 120


@pytest.fixture(scope="module")
def client(storage_dir):
    from app.main import app

    for child in storage_dir.iterdir():
        shutil.rmtree(child, ignore_errors=True)
    with TestClient(app) as test_client:
        yield test_client


def new_character_body(client, name="Ron", gender="male") -> dict:
    response = client.post("/api/characters/new", json={"name": name, "gender": gender})
    assert response.status_code == 200
    return response.json()


def make_project(client, script=SMALL_SCRIPT, with_cast=True, title="Test project") -> dict:
    project = client.post("/api/projects", json={"title": title}).json()
    project = client.put(f"/api/projects/{project['id']}", json={"script": script}).json()
    if with_cast:
        for speaker in ("JADE", "RON"):
            character = new_character_body(client, speaker.title())
            project = client.put(f"/api/projects/{project['id']}/cast/{speaker}", json={"character": character, "library_id": None}).json()
    return project


# ---------- options and script ----------

def test_options_has_everything_the_ui_builds_from(client):
    options = client.get("/api/options").json()

    assert set(options) == {"controls", "sections", "emotions", "backgrounds", "voices", "aspects", "qualities", "max_length_s"}
    assert options["max_length_s"] == 900
    assert {"neutral", "angry"} <= {emotion["value"] for emotion in options["emotions"]}
    assert [aspect["value"] for aspect in options["aspects"]] == ["16:9", "9:16"]
    hair_control = next(control for control in options["controls"] if control["key"] == "hair_style")
    assert set(hair_control["options_by_gender"]) == {"male", "female"}
    assert {control["type"] for control in options["controls"]} == {"slider", "select", "color", "toggle"}
    assert all({"id", "label", "gender", "age"} <= set(voice) for voice in options["voices"])


def test_script_validate_returns_lines_speakers_and_estimate(client):
    result = client.post("/api/script/validate", json={"script": SMALL_SCRIPT}).json()

    assert result["speakers"] == ["JADE", "RON"]
    assert len(result["lines"]) == 3
    assert result["error_count"] == 0
    assert result["estimated_length_s"] > 0


def test_script_validate_reports_issues_with_levels(client):
    result = client.post("/api/script/validate", json={"script": "JADE [grumpy]: Hi.\nRON: Hello.\nnot a line"}).json()

    levels = {issue["level"] for issue in result["issues"]}
    assert levels == {"warning", "error"}
    assert result["warning_count"] == 1
    assert result["error_count"] == 1


def test_script_validate_needs_a_script_field(client):
    assert client.post("/api/script/validate", json={}).status_code == 422


# ---------- characters ----------

def test_new_character_is_unsaved_with_defaults(client):
    character = new_character_body(client, "Jade", "female")

    assert character["id"] is None
    assert character["name"] == "Jade"
    assert character["params"]["gender"] == "female"
    assert character["voice"]["voice_id"]


def test_character_create_get_update_list_delete(client):
    created = client.post("/api/characters", json=new_character_body(client, "Zed")).json()
    assert created["id"]
    assert client.post("/api/characters", json=new_character_body(client, "alpha")).status_code == 201

    assert client.get(f"/api/characters/{created['id']}").json() == created

    created["name"] = "Zed Renamed"
    created["params"]["head_width"] = 3
    updated = client.put(f"/api/characters/{created['id']}", json=created).json()
    assert updated["name"] == "Zed Renamed"
    assert updated["params"]["head_width"] == 1.0
    assert updated["id"] == created["id"]
    assert updated["created_at"] == created["created_at"]

    names = [character["name"].lower() for character in client.get("/api/characters").json()]
    assert names == sorted(names)

    assert client.delete(f"/api/characters/{created['id']}").json() == {"ok": True}
    assert client.get(f"/api/characters/{created['id']}").status_code == 404


def test_character_not_found_is_404_with_a_message(client):
    for response in (
        client.get("/api/characters/nobody-123456"),
        client.put("/api/characters/nobody-123456", json=new_character_body(client)),
        client.delete("/api/characters/nobody-123456"),
        client.get("/api/characters/nobody-123456/export"),
        client.get("/api/characters/nobody-123456/avatar.png"),
    ):
        assert response.status_code == 404
        assert response.json()["detail"]


def test_character_id_with_bad_characters_is_404(client):
    assert client.get("/api/characters/..%2F..%2Fconfig").status_code == 404
    assert client.get("/api/characters/a.b").status_code == 404


def test_character_export_and_import_round_trip(client):
    created = client.post("/api/characters", json=new_character_body(client, "Exported Ron")).json()

    export = client.get(f"/api/characters/{created['id']}/export")

    assert export.status_code == 200
    assert "attachment" in export.headers["content-disposition"]
    assert ".json" in export.headers["content-disposition"]
    imported = client.post("/api/characters/import", json=export.json())
    assert imported.status_code == 201
    assert imported.json()["id"] != created["id"]
    assert imported.json()["params"] == created["params"]

    client.delete(f"/api/characters/{created['id']}")
    reimported = client.post("/api/characters/import", json=export.json()).json()
    assert reimported["id"] == created["id"]


def test_character_import_rejects_other_json(client):
    response = client.post("/api/characters/import", json={"hello": "world"})

    assert response.status_code == 422
    assert response.json()["detail"]


def test_character_import_never_uses_an_unsafe_id(client, storage_dir):
    shared = new_character_body(client, "Sneaky")
    shared["id"] = "../../evil"

    imported = client.post("/api/characters/import", json=shared).json()

    assert imported["id"] != "../../evil"
    assert (storage_dir / "characters" / f"{imported['id']}.json").is_file()
    assert not (storage_dir.parent / "evil.json").exists()


def test_character_create_ignores_an_id_in_the_body(client):
    body = new_character_body(client, "Idless")
    body["id"] = "../evil"

    created = client.post("/api/characters", json=body).json()

    assert created["id"] != "../evil"
    assert client.get(f"/api/characters/{created['id']}").status_code == 200


def test_character_new_with_an_unknown_gender_falls_back_to_a_valid_one(client):
    character = client.post("/api/characters/new", json={"gender": "robot"}).json()

    assert character["params"]["gender"] in ("male", "female")


def test_character_preview_with_an_unknown_emotion_still_draws(client):
    response = client.post("/api/characters/preview", json={"character": new_character_body(client), "emotion": "grumpy"})

    assert response.status_code == 200
    assert response.content.startswith(PNG_SIGNATURE)


def test_character_autofill_applies_the_description(client):
    body = {"description": "old woman with silver hair and glasses", "character": new_character_body(client)}

    result = client.post("/api/characters/autofill", json=body).json()

    assert result["character"]["params"]["gender"] == "female"
    assert result["character"]["params"]["age"] == "elderly"
    assert result["character"]["params"]["glasses"] != "none"
    assert result["matched"]
    assert result["unmatched"] == []


def test_character_randomize_keeps_name_gender_and_voice(client):
    character = new_character_body(client, "Keeper", "female")

    result = client.post("/api/characters/randomize", json={"character": character}).json()["character"]

    assert result["name"] == "Keeper"
    assert result["params"]["gender"] == "female"
    assert result["voice"] == character["voice"]
    assert result["params"] != character["params"]


def test_character_auto_voice_respects_exclude(client):
    first = client.post("/api/characters/auto-voice", json={"gender": "male", "age": "adult", "exclude": []}).json()["voice_id"]

    second = client.post("/api/characters/auto-voice", json={"gender": "male", "age": "adult", "exclude": [first]}).json()["voice_id"]

    assert first and second != first


def test_character_preview_is_a_png_of_the_requested_size(client):
    body = {"character": new_character_body(client), "emotion": "angry", "width": 200, "height": 260}

    response = client.post("/api/characters/preview", json=body)

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.content.startswith(PNG_SIGNATURE)


def test_character_preview_rejects_a_huge_size(client):
    body = {"character": new_character_body(client), "width": 99999}

    assert client.post("/api/characters/preview", json=body).status_code == 422


def test_character_avatar_is_a_png(client):
    created = client.post("/api/characters", json=new_character_body(client, "Avatar")).json()

    response = client.get(f"/api/characters/{created['id']}/avatar.png?size=64")

    assert response.status_code == 200
    assert response.content.startswith(PNG_SIGNATURE)
    assert client.get(f"/api/characters/{created['id']}/avatar.png?size=5").status_code == 422


def test_voice_sample_is_a_wav_with_the_fake_voice(client):
    voice = new_character_body(client)["voice"]

    response = client.post("/api/voices/sample", json={"voice": voice, "text": "Hello there."})

    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/wav"
    assert response.content[:4] == b"RIFF"


def test_voice_sample_with_an_unknown_voice_is_404(client):
    response = client.post("/api/voices/sample", json={"voice": {"voice_id": "nobody"}})

    assert response.status_code == 404


# ---------- projects ----------

def test_project_create_and_get(client):
    created = client.post("/api/projects", json={"title": "  My   video  "})

    assert created.status_code == 201
    project = created.json()
    assert project["title"] == "My video"
    assert project["status"] == "draft"
    assert project["settings"] == {"aspect": "16:9", "music": True, "quality": "1080p"}
    assert project["cast"] == {}
    assert client.get(f"/api/projects/{project['id']}").json() == project


def test_project_create_without_a_title_uses_the_default(client):
    assert client.post("/api/projects", json={}).json()["title"] == "Untitled project"


def test_project_update_title_script_and_partial_settings(client):
    project = client.post("/api/projects", json={}).json()

    updated = client.put(f"/api/projects/{project['id']}", json={"title": "Renamed", "script": SMALL_SCRIPT, "settings": {"music": False}}).json()

    assert updated["title"] == "Renamed"
    assert updated["script"] == SMALL_SCRIPT
    assert updated["estimated_length_s"] > 0
    assert updated["settings"] == {"aspect": "16:9", "music": False, "quality": "1080p"}


def test_project_update_rejects_unknown_aspect_and_quality(client):
    project = client.post("/api/projects", json={}).json()

    assert client.put(f"/api/projects/{project['id']}", json={"settings": {"aspect": "4:3"}}).status_code == 422
    assert client.put(f"/api/projects/{project['id']}", json={"settings": {"quality": "8k"}}).status_code == 422


def test_project_list_is_newest_first(client):
    first = client.post("/api/projects", json={"title": "Older"}).json()
    time.sleep(1.1)
    second = client.post("/api/projects", json={"title": "Newer"}).json()

    ids = [item["id"] for item in client.get("/api/projects").json()]

    assert ids.index(second["id"]) < ids.index(first["id"])
    item = next(item for item in client.get("/api/projects").json() if item["id"] == first["id"])
    assert set(item) == {"id", "title", "status", "length_s", "estimated_length_s", "aspect", "updated_at", "has_thumbnail", "progress"}
    assert item["has_thumbnail"] is False
    assert item["progress"] is None


def test_project_cast_set_and_remove(client):
    project = make_project(client, with_cast=False)
    character = new_character_body(client, "Jade")

    with_cast = client.put(f"/api/projects/{project['id']}/cast/jade", json={"character": character, "library_id": "jade-1a2b3c"}).json()

    assert list(with_cast["cast"]) == ["JADE"]
    assert with_cast["cast"]["JADE"]["library_id"] == "jade-1a2b3c"
    assert with_cast["cast"]["JADE"]["character"]["name"] == "Jade"
    without_cast = client.delete(f"/api/projects/{project['id']}/cast/JADE").json()
    assert without_cast["cast"] == {}


def test_project_thumbnail_needs_a_cast(client):
    empty = make_project(client, with_cast=False)
    full = make_project(client)

    assert client.get(f"/api/projects/{empty['id']}/thumbnail.png").status_code == 404
    response = client.get(f"/api/projects/{full['id']}/thumbnail.png")
    assert response.status_code == 200
    assert response.content.startswith(PNG_SIGNATURE)
    assert next(item for item in client.get("/api/projects").json() if item["id"] == full["id"])["has_thumbnail"] is True


def test_project_duplicate_copies_script_and_cast_with_a_new_id(client):
    project = make_project(client, title="Original")

    response = client.post(f"/api/projects/{project['id']}/duplicate")

    assert response.status_code == 201
    copy = response.json()
    assert copy["id"] != project["id"]
    assert copy["title"] == "Original (copy)"
    assert copy["script"] == project["script"]
    assert copy["cast"] == project["cast"]
    assert copy["status"] == "draft"


def test_project_delete_removes_it(client):
    project = make_project(client)

    assert client.delete(f"/api/projects/{project['id']}").json() == {"ok": True}
    assert client.get(f"/api/projects/{project['id']}").status_code == 404
    assert project["id"] not in [item["id"] for item in client.get("/api/projects").json()]


def test_preflight_passes_with_a_cast_and_fails_without(client):
    ready = make_project(client)
    missing_cast = make_project(client, with_cast=False)

    ready_result = client.get(f"/api/projects/{ready['id']}/preflight").json()
    missing_result = client.get(f"/api/projects/{missing_cast['id']}/preflight").json()

    ready_checks = {check["key"]: check for check in ready_result["checks"]}
    assert {"script", "cast", "length", "ffmpeg", "voices", "output_folder"} <= set(ready_checks)
    assert ready_checks["script"]["ok"] and ready_checks["cast"]["ok"] and ready_checks["length"]["ok"]
    assert ready_result["ok"] == (find_tool("ffmpeg") is not None)
    assert missing_result["ok"] is False
    assert {check["key"]: check["ok"] for check in missing_result["checks"]}["cast"] is False


@pytest.mark.parametrize("path", [
    "", "/thumbnail.png", "/preflight", "/job", "/storyboard", "/output.mp4", "/files/latest.jpg",
])
def test_unknown_project_is_404_for_every_get_route(client, path):
    response = client.get(f"/api/projects/{MISSING_PROJECT_ID}{path}")

    assert response.status_code == 404
    assert response.json()["detail"]


def test_unknown_project_is_404_for_every_write_route(client):
    character = new_character_body(client)
    base = f"/api/projects/{MISSING_PROJECT_ID}"

    for response in (
        client.put(base, json={"title": "x"}),
        client.delete(base),
        client.post(f"{base}/duplicate"),
        client.put(f"{base}/cast/JADE", json={"character": character}),
        client.delete(f"{base}/cast/JADE"),
        client.post(f"{base}/storyboard"),
        client.post(f"{base}/render"),
        client.post(f"{base}/cancel"),
    ):
        assert response.status_code == 404


def test_badly_formed_project_id_is_404(client):
    assert client.get("/api/projects/not-a-project").status_code == 404
    assert client.get("/api/projects/p-ZZZZZZ").status_code == 404


def test_new_project_has_no_job_storyboard_or_output(client):
    project = make_project(client)

    assert client.get(f"/api/projects/{project['id']}/job").json() is None
    assert client.get(f"/api/projects/{project['id']}/storyboard").status_code == 404
    assert client.get(f"/api/projects/{project['id']}/output.mp4").status_code == 404
    assert client.post(f"/api/projects/{project['id']}/cancel").status_code == 409


def test_starting_a_job_without_a_full_cast_is_422(client):
    project = make_project(client, with_cast=False)

    response = client.post(f"/api/projects/{project['id']}/storyboard")

    assert response.status_code == 422
    assert "JADE" in response.json()["detail"]


# ---------- files ----------

def test_project_files_serves_a_file_and_blocks_path_traversal(client, storage_dir):
    project = make_project(client)
    files_dir = storage_dir / "projects" / project["id"] / "files"
    files_dir.mkdir(parents=True, exist_ok=True)
    (files_dir / "hello.txt").write_text("hi there", encoding="utf-8")
    base = f"/api/projects/{project['id']}/files"

    assert client.get(f"{base}/hello.txt").text == "hi there"
    assert client.get(f"{base}/missing.txt").status_code == 404

    attacks = [
        "../project.json",
        "..%2Fproject.json",
        "%2e%2e/project.json",
        "%2e%2e%2fproject.json",
        "sub/../../project.json",
        "..%5Cproject.json",
        "/etc/passwd",
        "%2Fetc%2Fpasswd",
        "..%2F..%2F..%2F..%2F..%2F..%2F..%2F..%2Fetc%2Fpasswd",
    ]
    for attack in attacks:
        response = client.get(f"{base}/{attack}")
        assert response.status_code == 404, attack
        assert "script" not in response.text, attack
        assert "root:" not in response.text, attack


# ---------- one job end to end ----------

def wait_for_job(client, project_id: str) -> dict:
    deadline = time.time() + JOB_TIMEOUT_SECONDS
    job = None
    while time.time() < deadline:
        job = client.get(f"/api/projects/{project_id}/job").json()
        if job and job["state"] not in ("queued", "running"):
            return job
        time.sleep(0.5)
    pytest.fail(f"The job did not finish in {JOB_TIMEOUT_SECONDS} seconds. Last state: {job}")


@pytest.mark.skipif(find_tool("ffmpeg") is None, reason="ffmpeg is not installed")
def test_storyboard_job_runs_end_to_end_and_a_second_job_gets_409(client, storage_dir):
    project = make_project(client)
    project_id = project["id"]

    started = client.post(f"/api/projects/{project_id}/storyboard")
    assert started.status_code == 202
    assert started.json()["kind"] == "storyboard"

    other_project = make_project(client)
    second = client.post(f"/api/projects/{other_project['id']}/storyboard")
    assert second.status_code == 409
    assert second.json()["detail"]

    job = wait_for_job(client, project_id)
    assert job["state"] == "done", job
    assert job["percent"] == 100.0
    assert job["error"] is None
    assert [stage["state"] for stage in job["stages"] if stage["key"] in ("parse", "voice", "mix")] == ["done", "done", "done"]

    storyboard = client.get(f"/api/projects/{project_id}/storyboard").json()
    assert storyboard["frames"]
    assert storyboard["aspect"] == "16:9"
    for frame in storyboard["frames"]:
        frame_response = client.get(frame["url"].split("?")[0])
        assert frame_response.status_code == 200
        assert frame_response.headers["content-type"] == "image/jpeg"
    assert client.get(storyboard["preview_url"].split("?")[0]).status_code == 200

    finished_project = client.get(f"/api/projects/{project_id}").json()
    assert finished_project["has_storyboard"] is True
    assert finished_project["status"] == "storyboarded"
    assert client.get("/api/projects").json()[0]["progress"] is None

    # Changing the script makes the old storyboard stale, so the project goes back to draft.
    edited = client.put(f"/api/projects/{project_id}", json={"script": SMALL_SCRIPT + "RON: One more line.\n"}).json()
    assert edited["status"] == "draft"
    assert edited["has_storyboard"] is False

    # The job is over, so a new one can start and be cancelled right away.
    third = client.post(f"/api/projects/{other_project['id']}/storyboard")
    assert third.status_code == 202
    assert client.post(f"/api/projects/{other_project['id']}/cancel").status_code == 200
    assert wait_for_job(client, other_project["id"])["state"] in ("cancelled", "done")
