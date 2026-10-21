"""Web API tests. The LLM is replaced by rule-based stand-ins, so no key is needed."""

import pymupdf
import pytest
from fastapi.testclient import TestClient

from autoformfill.web import create_app
from tests.conftest import RuleBasedLLM


class FakeLLM(RuleBasedLLM):
    def complete_json(self, system, user):
        if "RESUME TEXT" in user:
            return self.profile.model_dump()
        return super().complete_json(system, user)


@pytest.fixture
def client(tmp_path, profile):
    app = create_app(llm_factory=lambda: FakeLLM(profile),
                     profile_path=tmp_path / "profile.json",
                     screenshot_dir=tmp_path / "shots")
    return TestClient(app)


def _pdf_bytes(text: str) -> bytes:
    doc = pymupdf.open()
    doc.new_page().insert_text((72, 72), text)
    return doc.tobytes()


def test_index_page_is_served(client):
    res = client.get("/")
    assert res.status_code == 200 and "autoformfill" in res.text


def test_profile_starts_empty_then_saves(client, profile):
    assert client.get("/api/profile").json() == {"profile": None}
    res = client.put("/api/profile", json=profile.model_dump())
    assert res.status_code == 200
    assert client.get("/api/profile").json()["profile"]["email"] == profile.email


def test_profile_needs_name_or_email(client):
    res = client.put("/api/profile", json={"skills": ["Python"]})
    assert res.status_code == 422


def test_resume_upload(client, profile):
    files = {"file": ("cv.pdf", _pdf_bytes("Enaba Salman, enaba@example.com"), "application/pdf")}
    res = client.post("/api/resume", files=files)
    assert res.status_code == 200
    assert res.json()["profile"]["first_name"] == profile.first_name


def test_resume_rejects_non_pdf(client):
    res = client.post("/api/resume", files={"file": ("cv.txt", b"hello", "text/plain")})
    assert res.status_code == 415


def test_fill_requires_details_first(client, form_url):
    res = client.post("/api/fill", json={"url": form_url})
    assert res.status_code == 409


def test_fill_rejects_bad_url(client, profile):
    client.put("/api/profile", json=profile.model_dump())
    assert client.post("/api/fill", json={"url": "javascript:alert(1)"}).status_code == 422


def test_fill_end_to_end(client, profile, form_url, chromium_available):
    client.put("/api/profile", json=profile.model_dump())
    res = client.post("/api/fill", json={"url": form_url})
    assert res.status_code == 200, res.text
    report = res.json()
    assert report["filled"] == 8 and report["failed"] == 0
    shot = client.get(report["screenshot_url"])
    assert shot.status_code == 200 and shot.headers["content-type"] == "image/png"


def test_screenshot_path_traversal_blocked(client):
    assert client.get("/api/screenshots/..%2Fprofile.json").status_code == 404
