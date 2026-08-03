"""Tests for api.py: job registry, file endpoints, input validation."""

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from herold import api

# No context manager: skips startup events (no data/ dirs created on the host)
client = TestClient(api.app)

VALID_PAYLOAD = {
    "ansagen": [
        {"id": "welcome", "text_de": "Willkommen!", "text_en": "Welcome!"},
    ]
}


class TestStatus:
    def test_status_healthy(self):
        resp = client.get("/api/status")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "healthy"
        assert body["version"]


class TestFileDownload:
    """GET /api/files/{dirname}/{filename} — path safety and content."""

    def test_unknown_dirname(self):
        resp = client.get("/api/files/secret/foo.wav")
        assert resp.status_code == 404

    def test_disallowed_extension(self):
        resp = client.get("/api/files/renders/evil.sh")
        assert resp.status_code == 404

    def test_wav_not_allowed_in_final(self):
        resp = client.get("/api/files/final/welcome.wav")
        assert resp.status_code == 404

    def test_invalid_stem_rejected(self):
        # Stem with dots (e.g. path traversal fragments) must be rejected
        resp = client.get("/api/files/renders/..foo.wav")
        assert resp.status_code == 400

    def test_missing_file(self):
        resp = client.get("/api/files/renders/does-not-exist.wav")
        assert resp.status_code == 404

    def test_download_existing_file(self, tmp_path, monkeypatch):
        wav = tmp_path / "welcome_en.wav"
        wav.write_bytes(b"RIFF-fake-wav-data")
        monkeypatch.setattr(api.config, "renders_dir", str(tmp_path))

        resp = client.get("/api/files/renders/welcome_en.wav")
        assert resp.status_code == 200
        assert resp.content == b"RIFF-fake-wav-data"
        assert resp.headers["content-type"].startswith("audio/wav")


class TestFileListing:
    def test_listing_contains_only_allowed_types(self, tmp_path, monkeypatch):
        renders = tmp_path / "renders"
        final = tmp_path / "final"
        renders.mkdir()
        final.mkdir()
        (renders / "welcome_en.wav").write_bytes(b"x")
        (renders / "notes.txt").write_bytes(b"x")  # must be filtered out
        (final / "welcome_en.mp3").write_bytes(b"x")
        monkeypatch.setattr(api.config, "renders_dir", str(renders))
        monkeypatch.setattr(api.config, "final_dir", str(final))

        resp = client.get("/api/files")
        assert resp.status_code == 200
        files = resp.json()["files"]
        names = {(f["dir"], f["name"]) for f in files}
        assert ("renders", "welcome_en.wav") in names
        assert ("final", "welcome_en.mp3") in names
        assert all(f["name"] != "notes.txt" for f in files)
        assert all(f["url"].startswith("/api/files/") for f in files)

    def test_listing_with_missing_dirs(self, monkeypatch):
        monkeypatch.setattr(api.config, "renders_dir", "/nonexistent/renders")
        monkeypatch.setattr(api.config, "final_dir", "/nonexistent/final")
        resp = client.get("/api/files")
        assert resp.status_code == 200
        assert resp.json()["files"] == []


class TestJobs:
    """Job registry lifecycle (render_batch/batch_convert mocked)."""

    def test_unknown_job(self):
        resp = client.get("/api/jobs/deadbeef")
        assert resp.status_code == 404

    def test_render_job_done(self):
        with patch.object(api, "render_batch") as mock_render:
            resp = client.post("/api/render", json=VALID_PAYLOAD)
        assert resp.status_code == 202
        job_id = resp.json()["job_id"]
        mock_render.assert_called_once()

        # TestClient runs background tasks before returning
        job = client.get(f"/api/jobs/{job_id}").json()
        assert job["status"] == "done"
        assert job["kind"] == "render"
        assert job["items"] == ["welcome"]
        assert job["error"] is None

    def test_render_job_failed(self):
        with patch.object(api, "render_batch", side_effect=RuntimeError("CUDA OOM")):
            resp = client.post("/api/render", json=VALID_PAYLOAD)
        assert resp.status_code == 202
        job_id = resp.json()["job_id"]

        job = client.get(f"/api/jobs/{job_id}").json()
        assert job["status"] == "failed"
        assert "CUDA OOM" in job["error"]

    def test_render_invalid_text_no_job(self):
        payload = {"ansagen": [{"id": "welcome", "text_de": "", "text_en": "Welcome!"}]}
        resp = client.post("/api/render", json=payload)
        assert resp.status_code == 400

    def test_convert_job_done(self):
        with patch.object(api, "batch_convert") as mock_convert:
            resp = client.post("/api/convert", json={})
        assert resp.status_code == 202
        job_id = resp.json()["job_id"]
        mock_convert.assert_called_once()

        job = client.get(f"/api/jobs/{job_id}").json()
        assert job["status"] == "done"
        assert job["kind"] == "convert"


class TestDemoPage:
    def test_root_redirects_to_demo(self):
        resp = client.get("/", follow_redirects=False)
        assert resp.status_code in (302, 307)
        assert resp.headers["location"] == "/demo/"

    def test_demo_page_served(self):
        resp = client.get("/demo/")
        assert resp.status_code == 200
        assert "Herold-TTS" in resp.text
