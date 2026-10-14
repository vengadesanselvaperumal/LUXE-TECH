import asyncio
from datetime import datetime, timezone
import io
import sys
import uuid

import httpx
from PIL import Image
import pytest

from app.services.submission_service import normalize_social_source_url
from app.services.video_provider import VideoProviderError, YouTubeDataApiProvider


# ---------------------------------------------------------
# Test Helpers
# ---------------------------------------------------------

class MockYouTubeClient:
    def __init__(self, result):
        self.result = result
        self.params = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        return None

    async def get(self, _url, params):
        self.params = params
        if isinstance(self.result, Exception):
            raise self.result
        return httpx.Response(
            200,
            json=self.result,
            request=httpx.Request("GET", "https://www.googleapis.com/youtube/v3/search"),
        )


def _submission_form(source_url=None):
    if source_url is None:
        source_url = f"https://www.instagram.com/p/{uuid.uuid4().hex[:10]}/"
    return {
        "platform": "instagram",
        "source_url": source_url,
        "observation": "Sculptural draping across luxury collections.",
        "product_type": "Dresses",
    }


# ---------------------------------------------------------
# 1. Video Provider Status & Search & Caching & Timeouts
# ---------------------------------------------------------

def test_video_provider_status_and_search_report_unconfigured_state(client, monkeypatch):
    monkeypatch.setattr("app.routers.videos.youtube_video_provider.api_key", "")
    status_response = client.get("/api/videos/status")
    search_response = client.get("/api/videos/search?q=couture")

    assert status_response.status_code == 200
    status_data = status_response.json()["data"]
    assert status_data["available"] is False
    assert status_data["state"] == "unavailable"
    assert "limitations" in status_data
    # 503 Service Unavailable when video provider is not configured
    assert search_response.status_code == 503
    assert search_response.json()["error"]["message"]["code"] == "credentials_missing"


def test_video_provider_caching_and_source_attribution(monkeypatch):
    provider = YouTubeDataApiProvider()
    provider.api_key = "test-api-key"

    client = MockYouTubeClient({
        "items": [{
            "id": {"videoId": "test_video_123"},
            "snippet": {
                "title": "Milan Fashion Week Runway Highlights",
                "channelTitle": "Fashion Channel",
                "publishedAt": "2026-10-12T10:00:00Z",
                "thumbnails": {"high": {"url": "https://i.ytimg.com/vi/test_video_123/hqdefault.jpg"}},
            },
        }],
    })
    network_calls = []

    def build_client(**_kwargs):
        network_calls.append(True)
        return client

    monkeypatch.setattr("app.services.video_provider.httpx.AsyncClient", build_client)

    async def execute():
        res1 = await provider.search("milan runway", region_code="it")
        res2 = await provider.search("milan runway", region_code="IT")
        return res1, res2

    res1, res2 = asyncio.run(execute())
    assert res1 == res2
    # Caching ensures only 1 external HTTP request was dispatched
    assert len(network_calls) == 1
    assert res1[0]["video_id"] == "test_video_123"
    assert res1[0]["source"] == "YouTube Data API"
    assert res1[0]["canonical_url"] == "https://www.youtube.com/watch?v=test_video_123"
    assert provider.status()["last_successful_fetch"] is not None


def test_video_provider_timeout_handling(monkeypatch):
    provider = YouTubeDataApiProvider()
    provider.api_key = "test-api-key"
    timeout_client = MockYouTubeClient(httpx.TimeoutException("Connection timed out"))
    monkeypatch.setattr("app.services.video_provider.httpx.AsyncClient", lambda **_kwargs: timeout_client)

    with pytest.raises(VideoProviderError) as exc_info:
        asyncio.run(provider.search("runway"))
    assert exc_info.value.code == "provider_timeout"


# ---------------------------------------------------------
# 2. SSRF Protection & URL Canonicalization
# ---------------------------------------------------------

@pytest.mark.parametrize(
    ("platform", "source_url", "expected"),
    [
        (
            "instagram",
            "https://instagram.com/p/Cxyz123/?utm_source=ig_web_copy_link&igshid=track123",
            "https://www.instagram.com/p/Cxyz123",
        ),
        (
            "youtube",
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ&si=tracking_id_999",
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        ),
        (
            "tiktok",
            "https://www.tiktok.com/@vogue/video/9876543210?is_copy_url=1",
            "https://www.tiktok.com/@vogue/video/9876543210",
        ),
        (
            "pinterest",
            "https://pinterest.com/pin/123456789012345678/?utm_campaign=share",
            "https://www.pinterest.com/pin/123456789012345678",
        ),
    ],
)
def test_ssrf_canonicalization_and_tracker_stripping(platform, source_url, expected):
    assert normalize_social_source_url(platform, source_url) == expected


@pytest.mark.parametrize(
    ("platform", "source_url"),
    [
        # SSRF: Private IP ranges
        ("other", "https://127.0.0.1/post"),
        ("other", "https://10.0.0.1/private"),
        ("other", "https://192.168.1.1/admin"),
        ("other", "https://169.254.169.254/latest/meta-data/"),
        ("other", "https://localhost:8000/leak"),
        # Protocol violations
        ("instagram", "http://instagram.com/p/test/"),
        ("other", "ftp://example.com/file"),
        ("other", "javascript:alert(1)"),
        # Credentials in URL
        ("instagram", "https://admin:secret@instagram.com/p/test/"),
        # Non-post profile pages or mismatched domains
        ("instagram", "https://instagram.com/"),
        ("instagram", "https://instagram.com/explore/"),
        ("youtube", "https://youtube.com/@channelname"),
        ("tiktok", "https://tiktok.com/@username"),
        ("pinterest", "https://pinterest.com/"),
        ("instagram", "https://malicious-instagram.com/p/test/"),
    ],
)
def test_ssrf_and_invalid_urls_are_strictly_rejected(platform, source_url):
    with pytest.raises(ValueError):
        normalize_social_source_url(platform, source_url)


# ---------------------------------------------------------
# 3. Social Submissions: Auth, Duplicate Rejection, User Isolation
# ---------------------------------------------------------

def test_submission_requires_authentication(client):
    form = _submission_form()
    # Anonymous POST must fail with 401
    resp = client.post("/api/submissions", data=form)
    assert resp.status_code == 401

    # Invalid token must fail with 401
    bad_auth = client.post("/api/submissions", data=form, headers={"Authorization": "Bearer badtoken"})
    assert bad_auth.status_code == 401


def test_submission_duplicate_normalized_url_rejection(client, auth_headers):
    unique_post = f"https://www.instagram.com/p/{uuid.uuid4().hex[:10]}/"
    form = _submission_form(unique_post)

    first = client.post("/api/submissions", data=form, headers=auth_headers)
    assert first.status_code == 201
    data = first.json()["data"]
    assert data["status"] == "pending"
    assert data["source_url"] == unique_post

    # Submitting the same post with tracking parameters must trigger 409 Conflict
    dup_url = f"{unique_post}?utm_source=twitter&igshid=abc123xyz"
    duplicate = client.post("/api/submissions", data=_submission_form(dup_url), headers=auth_headers)
    assert duplicate.status_code == 409
    assert "already been submitted" in duplicate.json()["error"]["message"]


def test_my_submissions_history_user_isolation(client, auth_headers):
    created = client.post("/api/submissions", data=_submission_form(), headers=auth_headers)
    assert created.status_code == 201

    # Create distinct second user
    reg = client.post("/api/auth/register", json={
        "email": f"isolated_{uuid.uuid4().hex[:8]}@luxe.tech",
        "password": "Password123!",
        "name": "Isolated User",
    })
    second_headers = {"Authorization": f"Bearer {reg.json()['data']['token']}"}

    # First user sees their 1 submission
    user1_history = client.get("/api/submissions/mine", headers=auth_headers)
    assert user1_history.status_code == 200
    assert len(user1_history.json()["data"]) == 1

    # Second user has 0 submissions
    user2_history = client.get("/api/submissions/mine", headers=second_headers)
    assert user2_history.status_code == 200
    assert len(user2_history.json()["data"]) == 0


def test_submission_image_upload_privacy_and_rights(client, auth_headers, monkeypatch, tmp_path):
    monkeypatch.setattr(sys.modules["app.services.supabase_service"], "LOCAL_STORAGE_DIR", tmp_path)
    monkeypatch.setattr("app.routers.images.LOCAL_STORAGE_DIR", tmp_path)

    # Generate synthetic image
    img = Image.new("RGB", (32, 32), color="#E8C8B1")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    image_bytes = buf.getvalue()

    form = _submission_form()

    # Missing rights confirmation yields 422
    denied = client.post(
        "/api/submissions",
        data=form,
        files={"file": ("look.jpg", image_bytes, "image/jpeg")},
        headers=auth_headers,
    )
    assert denied.status_code == 422

    # Rights confirmed yields 201
    uploaded = client.post(
        "/api/submissions",
        data={**form, "rights_confirmed": "true"},
        files={"file": ("look.jpg", image_bytes, "image/jpeg")},
        headers=auth_headers,
    )
    assert uploaded.status_code == 201
    # Creation response image_url is None for privacy (must use /api/submissions/mine)
    assert uploaded.json()["data"]["image_url"] is None

    # Retrieve history
    history = client.get("/api/submissions/mine", headers=auth_headers).json()["data"]
    assert len(history) == 1
    image_url = history[0]["image_url"]
    assert image_url.startswith("/api/images/local/user-uploads/")

    # Image accessible to owner
    assert client.get(image_url, headers=auth_headers).status_code == 200

    # Image inaccessible to other user (403 Forbidden)
    other = client.post("/api/auth/register", json={
        "email": f"intruder_{uuid.uuid4().hex[:8]}@luxe.tech",
        "password": "Password123!",
        "name": "Intruder User",
    })
    other_headers = {"Authorization": f"Bearer {other.json()['data']['token']}"}
    assert client.get(image_url, headers=other_headers).status_code == 403


def test_submission_review_role_based_access_control(client, auth_headers, privileged_user_headers):
    created = client.post("/api/submissions", data=_submission_form(), headers=auth_headers)
    submission_id = created.json()["data"]["id"]

    # Ordinary user receives 403 Forbidden
    forbidden = client.patch(
        f"/api/submissions/{submission_id}/review",
        json={"status": "reviewed"},
        headers=auth_headers,
    )
    assert forbidden.status_code == 403

    # Privileged user successfully transitions submission to accepted
    accepted = client.patch(
        f"/api/submissions/{submission_id}/review",
        json={"status": "accepted", "review_note": "Verified runway concordance."},
        headers=privileged_user_headers,
    )
    assert accepted.status_code == 200
    assert accepted.json()["data"]["status"] == "accepted"
