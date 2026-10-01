"""HTTP API: the full journey through the API, plus auth/host protections (ADR 0006). F1–F8."""

import io
import json
import time
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from storelistingkit.server import AppState, create_app

TOKEN = "test-token-123"


@pytest.fixture
def client(tmp_path):
    state = AppState(token=TOKEN, port=9999, workspace=tmp_path / "ws")
    c = TestClient(create_app(state))
    c.headers["X-SLK-Token"] = TOKEN
    return c


def zip_dir(path: Path) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for f in path.rglob("*"):
            if f.is_file():
                zf.write(f, f.relative_to(path.parent).as_posix())
    return buf.getvalue()


def png(w=1280, h=720) -> bytes:
    b = io.BytesIO()
    Image.new("RGB", (w, h), (30, 120, 200)).save(b, "PNG")
    return b.getvalue()


def test_requires_token(client):
    r = client.get("/api/status", headers={"X-SLK-Token": "wrong"})
    assert r.status_code == 401


def test_rejects_foreign_host(client):
    r = client.get("/api/status", headers={"Host": "evil.example:9999"})
    assert r.status_code == 403


def test_index_served_with_csp(client):
    r = client.get("/")
    assert r.status_code == 200 and "Store Listing Kit" in r.text
    assert "default-src 'self'" in r.headers["content-security-policy"]


def test_key_is_never_returned(client):
    r = client.post("/api/key", json={"key": "sk-ant-secret-value"})
    assert r.status_code == 200 and "secret" not in r.text
    status = client.get("/api/status").text
    assert "secret" not in status and json.loads(status)["key_source"] == "session"
    client.delete("/api/key")


def test_bad_key_rejected(client):
    assert client.post("/api/key", json={"key": "hello"}).status_code == 400


def test_full_journey_offline(client, fixtures):
    data = zip_dir(fixtures / "unreal_basic" / "QuickOutline")
    r = client.post("/api/projects/upload", files={"file": ("repo.zip", data, "application/zip")})
    assert r.status_code == 200, r.text
    project = r.json()
    pid = project["id"]
    assert project["profile"]["engine"] == "unreal" and project["stores"] == ["fab"]

    profile = project["profile"]
    profile["display_name"] = "Quick Outline Pro"
    r = client.put(f"/api/projects/{pid}/profile", json=profile)
    assert r.json()["profile"]["sources"]["display_name"] == "edited by user"

    r = client.post(f"/api/projects/{pid}/screenshots",
                    files=[("files", ("a.png", png(), "image/png")), ("files", ("b.txt", b"x", "text/plain")),
                           ("files", ("c.png", b"not an image", "image/png"))])
    body = r.json()
    assert len(body["screenshots"]) == 1 and len(body["errors"]) == 2

    r = client.post(f"/api/projects/{pid}/generate", json={"mode": "template"})
    job_id = r.json()["job_id"]
    for _ in range(100):
        job = client.get(f"/api/jobs/{job_id}").json()
        if job["state"] != "running":
            break
        time.sleep(0.05)
    assert job["state"] == "done", job
    kit = job["kit"]
    assert kit["copies"]["fab"]["title"] == "Quick Outline Pro"
    assert {i["slot"] for i in kit["images"]} == {"thumbnail", "gallery"}

    img = kit["images"][0]
    assert client.get(f"/api/projects/{pid}/images/fab/{img['filename']}").status_code == 200

    r = client.put(f"/api/projects/{pid}/copies/fab", json={"title": "X" * 500})
    assert any(i["field"] == "title" and i["severity"] == "error" for i in r.json()["kit"]["issues"])
    assert r.json()["kit"]["copies"]["fab"]["generated_by"] == "template+edited"

    r = client.get(f"/api/projects/{pid}/export", params={"t": TOKEN}, headers={"X-SLK-Token": ""})
    assert r.status_code == 200
    names = zipfile.ZipFile(io.BytesIO(r.content)).namelist()
    assert any(n.endswith("fab/listing.txt") for n in names)
    assert any(n.endswith("fab/images/thumbnail.png") for n in names)


def test_upload_rejects_traversal_zip(client):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("../../evil.txt", "x")
    r = client.post("/api/projects/upload", files={"file": ("x.zip", buf.getvalue(), "application/zip")})
    assert r.status_code == 400 and "Unsafe path" in r.json()["detail"]


def test_local_folder_source(client, fixtures):
    r = client.post("/api/projects/source", json={"path": str(fixtures / "unity_basic")})
    assert r.status_code == 200 and r.json()["profile"]["engine"] == "unity"


def test_bad_url_is_400(client):
    r = client.post("/api/projects/source", json={"url": "https://evil.com/a/b"})
    assert r.status_code == 400


def test_claude_mode_without_key_is_clean_400(client, fixtures):
    pid = client.post("/api/projects/source", json={"path": str(fixtures / "unity_basic")}).json()["id"]
    r = client.post(f"/api/projects/{pid}/generate", json={"mode": "claude"})
    assert r.status_code == 400 and "API key" in r.json()["detail"]


def test_rate_limit(client, fixtures, monkeypatch):
    from storelistingkit import config

    monkeypatch.setattr(config.LIMITS, "generate_per_minute", 2)
    pid = client.post("/api/projects/source", json={"path": str(fixtures / "unity_basic")}).json()["id"]
    codes = [client.post(f"/api/projects/{pid}/generate", json={"mode": "template"}).status_code for _ in range(3)]
    assert codes == [200, 200, 429]


def test_generation_error_surfaces_cleanly(tmp_path, fixtures):
    from storelistingkit.generator import GenerationError

    class Failing:
        name = "claude"

        def generate(self, profile, store):
            raise GenerationError("Could not produce a valid listing.", ["title: too long"])

    state = AppState(token=TOKEN, port=9999, workspace=tmp_path / "ws", generator_factory=lambda m: Failing())
    c = TestClient(create_app(state))
    c.headers["X-SLK-Token"] = TOKEN
    pid = c.post("/api/projects/source", json={"path": str(fixtures / "unity_basic")}).json()["id"]
    jid = c.post(f"/api/projects/{pid}/generate", json={}).json()["job_id"]
    for _ in range(100):
        job = c.get(f"/api/jobs/{jid}").json()
        if job["state"] != "running":
            break
        time.sleep(0.05)
    assert job["state"] == "error"
    assert job["errors"]["unity_asset_store"] == ["Could not produce a valid listing.", "title: too long"]
