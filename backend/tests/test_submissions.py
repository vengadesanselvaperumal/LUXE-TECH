import io
import importlib
import uuid

import pytest
from PIL import Image

from app.services.submission_service import normalize_social_source_url


def _submission_form(source_url="https://www.instagram.com/p/ABC123xyz/"):
    if source_url == "https://www.instagram.com/p/ABC123xyz/":
        source_url = f"https://www.instagram.com/p/{uuid.uuid4().hex[:10]}/"
    return {
        "platform": "instagram",
        "source_url": source_url,
        "observation": "Soft sculptural shoulders are recurring in outfit posts.",
        "product_type": "Jacket",
    }


@pytest.mark.parametrize(
    ("platform", "source_url", "expected"),
    [
        (
            "instagram",
            "https://instagram.com/reel/AbC123/?igshid=tracking",
            "https://www.instagram.com/reel/AbC123",
        ),
        (
            "youtube",
            "https://youtu.be/AbC123_xyz?si=tracking",
            "https://www.youtube.com/watch?v=AbC123_xyz",
        ),
        (
            "tiktok",
            "https://www.tiktok.com/@designer/video/123456789?utm_source=feed",
            "https://www.tiktok.com/@designer/video/123456789",
        ),
        (
            "pinterest",
            "https://pinterest.com/pin/123456789/",
            "https://www.pinterest.com/pin/123456789",
        ),
    ],
)
def test_social_source_urls_are_platform_validated_and_canonicalized(platform, source_url, expected):
    assert normalize_social_source_url(platform, source_url) == expected


@pytest.mark.parametrize(
    ("platform", "source_url"),
    [
        ("instagram", "https://instagram.com/"),
        ("youtube", "https://www.youtube.com/channel/UC123456"),
        ("tiktok", "https://www.tiktok.com/@designer"),
        ("pinterest", "https://www.pinterest.com/"),
        ("instagram", "https://notinstagram.com/p/ABC123xyz"),
        ("other", "http://example.com/post"),
        ("other", "https://127.0.0.1/post"),
        ("instagram", "https://user:password@instagram.com/p/ABC123xyz"),
    ],
)
def test_social_source_urls_reject_non_posts_or_non_public_urls(platform, source_url):
    with pytest.raises(ValueError):
        normalize_social_source_url(platform, source_url)


def test_submission_requires_authentication_and_valid_public_post(client):
    form = _submission_form()
    assert client.post("/api/submissions", data=form).status_code == 401

    form["source_url"] = "https://www.instagram.com/"
    response = client.post("/api/submissions", data=form, headers={"Authorization": "Bearer invalid"})
    assert response.status_code == 401


def test_submission_is_pending_attributed_and_duplicate_normalized_url_is_rejected(client, auth_headers):
    form = _submission_form()
    response = client.post("/api/submissions", data=form, headers=auth_headers)

    assert response.status_code == 201
    submission = response.json()["data"]
    assert submission["status"] == "pending"
    assert submission["evidence_type"] == "user_submitted_observation"
    assert submission["verification_state"] == "user_submitted_unverified"
    assert "sales" in submission["limitations"][1]
    assert submission["source_url"] == form["source_url"]
    assert submission["image_url"] is None

    duplicate = client.post(
        "/api/submissions",
        data={
            **form,
            "source_url": form["source_url"].replace("www.instagram.com", "instagram.com") + "?utm_source=feed",
        },
        headers=auth_headers,
    )
    assert duplicate.status_code == 409


def test_submission_history_is_account_scoped(client, auth_headers):
    created = client.post("/api/submissions", data=_submission_form(), headers=auth_headers)
    assert created.status_code == 201

    second = client.post("/api/auth/register", json={
        "email": f"history_{uuid.uuid4().hex[:8]}@luxe.tech",
        "password": "Password123!",
        "name": "History Reader",
    })
    other_headers = {"Authorization": f"Bearer {second.json()['data']['token']}"}

    own_history = client.get("/api/submissions/mine", headers=auth_headers)
    other_history = client.get("/api/submissions/mine", headers=other_headers)
    assert len(own_history.json()["data"]) == 1
    assert other_history.json()["data"] == []


def test_image_upload_needs_rights_confirmation_and_is_private(client, auth_headers, monkeypatch, tmp_path):
    storage_module = importlib.import_module("app.services.supabase_service")
    monkeypatch.setattr(storage_module, "LOCAL_STORAGE_DIR", tmp_path)
    images_module = importlib.import_module("app.routers.images")
    monkeypatch.setattr(images_module, "LOCAL_STORAGE_DIR", tmp_path)
    image = Image.new("RGB", (16, 16), color="ivory")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    image_content = buffer.getvalue()
    form = _submission_form()

    denied = client.post(
        "/api/submissions",
        data=form,
        files={"file": ("sample.png", image_content, "image/png")},
        headers=auth_headers,
    )
    assert denied.status_code == 422

    invalid_image = client.post(
        "/api/submissions",
        data={**form, "rights_confirmed": "true"},
        files={"file": ("sample.gif", b"not-an-image", "image/gif")},
        headers=auth_headers,
    )
    assert invalid_image.status_code == 400

    uploaded = client.post(
        "/api/submissions",
        data={**form, "rights_confirmed": "true"},
        files={"file": ("sample.png", image_content, "image/png")},
        headers=auth_headers,
    )
    assert uploaded.status_code == 201

    image_url = uploaded.json()["data"]["image_url"]
    assert image_url is None
    history = client.get("/api/submissions/mine", headers=auth_headers).json()["data"]
    assert len(history) == 1
    private_url = history[0]["image_url"]
    assert private_url.startswith("/api/images/local/user-uploads/")
    assert client.get(private_url, headers=auth_headers).status_code == 200

    second = client.post("/api/auth/register", json={
        "email": f"private_{uuid.uuid4().hex[:8]}@luxe.tech",
        "password": "Password123!",
        "name": "Other User",
    })
    other_headers = {"Authorization": f"Bearer {second.json()['data']['token']}"}
    assert client.get(private_url, headers=other_headers).status_code == 403


def test_submission_review_requires_privileged_role(client, auth_headers, privileged_user_headers):
    created = client.post("/api/submissions", data=_submission_form(), headers=auth_headers)
    submission_id = created.json()["data"]["id"]

    denied = client.patch(
        f"/api/submissions/{submission_id}/review",
        json={"status": "accepted"},
        headers=auth_headers,
    )
    accepted = client.patch(
        f"/api/submissions/{submission_id}/review",
        json={"status": "accepted", "review_note": "Reviewed with source attribution."},
        headers=privileged_user_headers,
    )
    assert denied.status_code == 403
    assert accepted.status_code == 200
    assert accepted.json()["data"]["status"] == "accepted"
