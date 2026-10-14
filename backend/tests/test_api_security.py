import io
from pathlib import Path
from unittest.mock import AsyncMock
import uuid
import pytest
from PIL import Image
from app.config import Settings
from app.database import Collection, Prophecy, SessionLocal
from app.services.gemini_service import gemini_service
from app.services.supabase_service import LOCAL_STORAGE_DIR, supabase_service
from app.utils.rate_limit import limiter
from app.utils.security import create_access_token


def test_anonymous_requests_to_protected_routes_return_401(client):
    """
    Verify that all state-changing mutation and AI-invoking routes
    strictly reject unauthenticated requests with HTTP 401.
    """
    # 1. POST /api/trends
    res = client.post("/api/trends", json={
        "name": "Cyber Baroque",
        "category": "Couture",
        "season": "FW 2027",
        "description": "Fusion of tech and rococo"
    })
    assert res.status_code == 401

    # 2. POST /api/collections/generate
    res = client.post("/api/collections/generate", json={"trend_id": "digital-nature"})
    assert res.status_code == 401

    # 3. POST /api/products/generate
    res = client.post("/api/products/generate", json={
        "trend_id": "digital-nature",
        "category": "Tailoring"
    })
    assert res.status_code == 401

    # 4. POST /api/forecast/{trend_id}
    res = client.post("/api/forecast/digital-nature")
    assert res.status_code == 401

    # 5. POST /api/prophecy/{trend_id}
    res = client.post("/api/prophecy/digital-nature")
    assert res.status_code == 401

    # 6. POST /api/images/analyze
    fake_img = io.BytesIO(b"fake_image_bytes")
    res = client.post("/api/images/analyze", files={"file": ("test.jpg", fake_img, "image/jpeg")})
    assert res.status_code == 401


def test_public_read_only_routes_remain_accessible_without_auth(client):
    """
    Verify that public discovery endpoints remain accessible to anonymous users.
    """
    public_endpoints = [
        "/api/health",
        "/api/dashboard",
        "/api/trends/categories",
        "/api/trends",
        "/api/collections/digital-nature",
        "/api/products",
        "/api/products/trend/digital-nature",
        "/api/forecast/digital-nature",
        "/api/prophecy/digital-nature",
        "/api/signals/live",
        "/api/retail",
        "/api/search?q=Digital",
    ]
    for endpoint in public_endpoints:
        res = client.get(endpoint)
        assert res.status_code == 200, f"Endpoint {endpoint} failed with {res.status_code}"
        assert res.json().get("success") is True, f"Endpoint {endpoint} returned success=False"

    hidden_demo_trend = client.get("/api/trends/digital-nature")
    assert hidden_demo_trend.status_code == 200
    assert hidden_demo_trend.json()["success"] is False
    assert hidden_demo_trend.json()["error"]["code"] == "TREND_NOT_FOUND"


def test_role_based_access_control_on_platform_mutations(client, ordinary_user_headers, privileged_user_headers):
    """
    Verify that state-changing platform catalog mutations strictly require
    privileged user roles (admin / lead_analyst), failing closed with 403 Forbidden
    for ordinary users, while personal actions (saving trends) remain available to ordinary users.
    """
    # 1. Ordinary user gets 403 Forbidden on shared catalog mutations
    res_forecast = client.post("/api/forecast/digital-nature", headers=ordinary_user_headers)
    assert res_forecast.status_code == 403
    assert "privileges required" in res_forecast.json()["error"]["message"].lower()

    res_prophecy = client.post("/api/prophecy/digital-nature", headers=ordinary_user_headers)
    assert res_prophecy.status_code == 403

    res_col = client.post("/api/collections/generate", json={"trend_id": "digital-nature"}, headers=ordinary_user_headers)
    assert res_col.status_code == 403

    res_prod = client.post("/api/products/generate", json={"trend_id": "digital-nature", "category": "Knitwear"}, headers=ordinary_user_headers)
    assert res_prod.status_code == 403

    res_trend = client.post("/api/trends", json={
        "name": "New Luxury Trend",
        "category": "Silhouettes",
        "season": "FW 2027",
        "description": "Unauthorized catalog insertion attempt"
    }, headers=ordinary_user_headers)
    assert res_trend.status_code == 403

    # 2. Ordinary user CAN still access personal bookmarks
    res_save = client.post("/api/trends/digital-nature/save", headers=ordinary_user_headers)
    assert res_save.status_code == 200
    assert res_save.json()["data"]["saved"] is True

    # 3. Privileged user succeeds (200 OK) on platform mutations
    res_p_fc = client.post("/api/forecast/digital-nature", headers=privileged_user_headers)
    assert res_p_fc.status_code == 200

    res_p_pr = client.post("/api/prophecy/digital-nature", headers=privileged_user_headers)
    assert res_p_pr.status_code == 200

    res_p_col = client.post("/api/collections/generate", json={"trend_id": "digital-nature"}, headers=privileged_user_headers)
    assert res_p_col.status_code == 200

    res_p_prod = client.post("/api/products/generate", json={"trend_id": "digital-nature", "category": "Knitwear"}, headers=privileged_user_headers)
    assert res_p_prod.status_code == 200


def test_cross_user_isolation_on_saved_trends(client):
    """
    Verify that saved trends are strictly isolated per user and cannot be seen
    or modified by another user.
    """
    # Register User A
    user_a_email = f"user_a_{uuid.uuid4().hex[:6]}@luxe.tech"
    res_a = client.post("/api/auth/register", json={
        "email": user_a_email,
        "password": "Password123!",
        "name": "User Alpha"
    })
    token_a = res_a.json()["data"]["token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # Register User B
    user_b_email = f"user_b_{uuid.uuid4().hex[:6]}@luxe.tech"
    res_b = client.post("/api/auth/register", json={
        "email": user_b_email,
        "password": "Password123!",
        "name": "User Beta"
    })
    token_b = res_b.json()["data"]["token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # User A saves trend 'digital-nature'
    save_resp = client.post("/api/trends/digital-nature/save", headers=headers_a)
    assert save_resp.status_code == 200
    assert save_resp.json()["data"]["saved"] is True

    # User A checks saved trends -> has 1 item
    list_a = client.get("/api/trends/saved", headers=headers_a)
    assert list_a.status_code == 200
    assert len(list_a.json()["data"]) == 1
    assert list_a.json()["data"][0]["slug"] == "digital-nature"

    # User B checks saved trends -> MUST be empty (zero cross-user leakage)
    list_b = client.get("/api/trends/saved", headers=headers_b)
    assert list_b.status_code == 200
    assert len(list_b.json()["data"]) == 0

    # User B toggles save on 'digital-nature' -> saves for User B, doesn't unsave User A
    save_b = client.post("/api/trends/digital-nature/save", headers=headers_b)
    assert save_b.status_code == 200
    assert save_b.json()["data"]["saved"] is True

    # User A's list still intact
    list_a_again = client.get("/api/trends/saved", headers=headers_a)
    assert len(list_a_again.json()["data"]) == 1


def test_upload_bounded_chunk_size_enforcement(client, auth_headers):
    """
    Verify that uploads exceeding 10MB are rejected with 413 via bounded chunk reads.
    """
    # 10.5 MB payload
    oversized_bytes = b"0" * (10 * 1024 * 1024 + 512 * 1024)
    file_payload = {"file": ("giant.jpg", io.BytesIO(oversized_bytes), "image/jpeg")}

    res = client.post("/api/images/analyze", files=file_payload, headers=auth_headers)
    assert res.status_code == 413
    assert "File exceeds maximum size limit" in res.json()["error"]["message"]


def test_upload_format_and_empty_file_validation(client, auth_headers):
    """
    Verify upload validation rejecting unsupported extensions, invalid MIME types,
    empty files, and corrupted image content.
    """
    # Empty file
    empty_file = {"file": ("empty.jpg", io.BytesIO(b""), "image/jpeg")}
    res_empty = client.post("/api/images/analyze", files=empty_file, headers=auth_headers)
    assert res_empty.status_code == 400
    assert "empty" in res_empty.json()["error"]["message"].lower()

    # Disallowed extension
    script_file = {"file": ("script.sh", io.BytesIO(b"echo 'pwned'"), "text/x-sh")}
    res_ext = client.post("/api/images/analyze", files=script_file, headers=auth_headers)
    assert res_ext.status_code == 400
    assert "extension" in res_ext.json()["error"]["message"].lower()

    # Disallowed MIME type
    bad_mime = {"file": ("fake.jpg", io.BytesIO(b"not an image"), "application/pdf")}
    res_mime = client.post("/api/images/analyze", files=bad_mime, headers=auth_headers)
    assert res_mime.status_code == 400
    assert "mime" in res_mime.json()["error"]["message"].lower()

    # Corrupted image content (JPEG extension and MIME, but invalid content)
    corrupted = {"file": ("corrupt.jpg", io.BytesIO(b"JFIF garbage bytes not a real image"), "image/jpeg")}
    res_corrupt = client.post("/api/images/analyze", files=corrupted, headers=auth_headers)
    assert res_corrupt.status_code == 400
    assert "corrupted" in res_corrupt.json()["error"]["message"].lower()


def test_production_cors_rejects_wildcard_and_empty():
    """
    Verify that in production mode, wildcard origins and empty configurations
    are strictly rejected.
    """
    # 1. Production with wildcard '*' origin must raise ValueError
    prod_wildcard = Settings(
        ENVIRONMENT="production",
        CORS_ORIGINS="*",
        _env_file=None
    )
    with pytest.raises(ValueError, match=r"Wildcard '\*' CORS origin is strictly forbidden"):
        _ = prod_wildcard.cors_origins_list

    # 2. Production with empty CORS_ORIGINS must raise ValueError
    prod_empty = Settings(
        ENVIRONMENT="production",
        CORS_ORIGINS="",
        _env_file=None
    )
    with pytest.raises(ValueError, match="CORS_ORIGINS must be explicitly configured in production"):
        _ = prod_empty.cors_origins_list

    # 3. Production with invalid origin format (missing scheme)
    prod_invalid = Settings(
        ENVIRONMENT="production",
        CORS_ORIGINS="app.luxe.tech,admin.luxe.tech",
        _env_file=None
    )
    with pytest.raises(ValueError, match="must include http:// or https:// scheme"):
        _ = prod_invalid.cors_origins_list

    # 4. Production with valid HTTPS origins succeeds
    prod_valid = Settings(
        ENVIRONMENT="production",
        CORS_ORIGINS="https://app.luxe.tech,https://admin.luxe.tech",
        _env_file=None
    )
    assert prod_valid.cors_origins_list == ["https://app.luxe.tech", "https://admin.luxe.tech"]

    # 5. Development mode with empty CORS_ORIGINS safely falls back to localhost, NEVER '*'
    dev_empty = Settings(
        ENVIRONMENT="development",
        CORS_ORIGINS="",
        _env_file=None
    )
    assert "*" not in dev_empty.cors_origins_list
    assert any("localhost" in origin for origin in dev_empty.cors_origins_list)


def test_rate_limiting_enforcement(client):
    """
    Verify that exceeding the rate limit triggers HTTP 429 Too Many Requests.
    """
    limiter.reset()

    # Auth login limit is 10 requests / 60 seconds
    for i in range(10):
        res = client.post("/api/auth/login", json={
            "email": "ratelimit_test@luxe.tech",
            "password": "WrongPassword123!"
        })
        assert res.status_code == 401

    # 11th request within window must be rate-limited with 429
    rate_limited_res = client.post("/api/auth/login", json={
        "email": "ratelimit_test@luxe.tech",
        "password": "WrongPassword123!"
    })
    assert rate_limited_res.status_code == 429
    assert "Rate limit exceeded" in rate_limited_res.json()["error"]["message"]


def test_invalid_and_expired_jwt_rejection(client):
    """
    Verify that malformed, corrupted, and expired JWTs are strictly rejected with 401.
    """
    from app.utils.security import create_access_token

    # 1. Completely malformed token string
    res_malformed = client.post(
        "/api/forecast/digital-nature",
        headers={"Authorization": "Bearer not.a.valid.jwt.token"}
    )
    assert res_malformed.status_code == 401

    # 2. Expired token (issued with negative expiration)
    expired_token = create_access_token(
        {"sub": str(uuid.uuid4()), "email": "expired@luxe.tech", "role": "user"},
        expires_in_seconds=-3600
    )
    res_expired = client.post(
        "/api/forecast/digital-nature",
        headers={"Authorization": f"Bearer {expired_token}"}
    )
    assert res_expired.status_code == 401

    # 3. Empty Bearer scheme
    res_empty_bearer = client.post(
        "/api/forecast/digital-nature",
        headers={"Authorization": "Bearer "}
    )
    assert res_empty_bearer.status_code == 401

    # 4. Non-Bearer authorization scheme
    res_basic = client.post(
        "/api/forecast/digital-nature",
        headers={"Authorization": "Basic dXNlcjpwYXNz"}
    )
    assert res_basic.status_code == 401


def test_upload_pixel_dimension_boundary_validation(client, auth_headers):
    """
    Verify upload validation dimension boundaries (minimum 10x10 px).
    """
    # 9x9 image (below minimum 10x10 boundary)
    small_img = Image.new("RGB", (9, 9), color=(255, 0, 0))
    buf = io.BytesIO()
    small_img.save(buf, format="JPEG")
    small_bytes = buf.getvalue()

    res_small = client.post(
        "/api/images/analyze",
        files={"file": ("small.jpg", io.BytesIO(small_bytes), "image/jpeg")},
        headers=auth_headers
    )
    assert res_small.status_code == 400
    assert "too small" in res_small.json()["error"]["message"].lower()


def test_rate_limiter_rejects_spoofed_forwarding_headers(client):
    """
    Verify that client-supplied X-Forwarded-For headers are not trusted by default,
    preventing attackers from bypassing the rate limiter by cycling spoofed IPs.
    """
    limiter.reset()

    # Client rotating X-Forwarded-For IPs on every request
    for i in range(10):
        spoofed_ip = f"198.51.100.{i}"
        res = client.post(
            "/api/auth/login",
            json={"email": "attacker@luxe.tech", "password": "WrongPassword123!"},
            headers={"X-Forwarded-For": spoofed_ip}
        )
        assert res.status_code == 401

    # 11th request: Even with another spoofed IP, it MUST be rate-limited with 429
    res_blocked = client.post(
        "/api/auth/login",
        json={"email": "attacker@luxe.tech", "password": "WrongPassword123!"},
        headers={"X-Forwarded-For": "198.51.100.99"}
    )
    assert res_blocked.status_code == 429
    assert "rate limit exceeded" in res_blocked.json()["error"]["message"].lower()


def test_get_endpoints_strictly_read_only_with_zero_writes_and_zero_ai_calls(client, monkeypatch):
    """
    Verify that GET requests for missing collections or prophecies:
    1. Strictly return 404
    2. Cause ZERO database inserts or commits
    3. Make ZERO calls to Gemini or AI generation engines
    """
    gemini_spy = AsyncMock(return_value={"text": "unexpected"})
    monkeypatch.setattr(gemini_service, "_call_gemini", gemini_spy)
    monkeypatch.setattr(gemini_service, "generate_prophecy", gemini_spy)

    db = SessionLocal()
    try:
        initial_collections = db.query(Collection).count()
        initial_prophecies = db.query(Prophecy).count()
    finally:
        db.close()

    # 1. GET non-existent collection
    res_col = client.get("/api/collections/non-existent-trend-xyz")
    assert res_col.status_code == 404
    assert res_col.json()["error"]["code"] in ("HTTP_404", "TREND_NOT_FOUND", "COLLECTION_NOT_FOUND")

    # 2. GET non-existent prophecy
    res_pr = client.get("/api/prophecy/non-existent-trend-xyz")
    assert res_pr.status_code == 404
    assert res_pr.json()["error"]["code"] in ("HTTP_404", "TREND_NOT_FOUND", "PROPHECY_NOT_FOUND")

    # Verify zero database modifications occurred
    db = SessionLocal()
    try:
        final_collections = db.query(Collection).count()
        final_prophecies = db.query(Prophecy).count()
        assert final_collections == initial_collections, "GET endpoint created unexpected Collection record"
        assert final_prophecies == initial_prophecies, "GET endpoint created unexpected Prophecy record"
    finally:
        db.close()

    # Verify zero AI generation calls were made
    assert gemini_spy.call_count == 0, "GET endpoint invoked expensive AI provider"


def test_private_uploads_bucket_and_signed_url_separation(client, ordinary_user_headers, privileged_user_headers):
    """
    Verify upload routing:
    - Ordinary user uploads route to private 'user-uploads' bucket with namespaced storage paths.
    - Privileged catalog uploads route to public 'trend-images' bucket.
    - supabase_service.get_public_url strictly rejects private buckets with ValueError.
    """
    img = Image.new("RGB", (100, 100), color=(50, 100, 150))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    img_bytes = buf.getvalue()

    # 1. Ordinary user personal upload
    res_user = client.post(
        "/api/images/analyze",
        files={"file": ("personal.jpg", io.BytesIO(img_bytes), "image/jpeg")},
        headers=ordinary_user_headers
    )
    assert res_user.status_code == 200
    user_data = res_user.json()["data"]
    assert user_data["bucket"] == "user-uploads"
    assert "/" in user_data["storage_path"]
    user_prefix = user_data["storage_path"].split("/")[0]
    assert len(user_prefix) > 0

    # 2. Privileged user catalog upload with trend_id
    res_catalog = client.post(
        "/api/images/analyze",
        files={"file": ("catalog.jpg", io.BytesIO(img_bytes), "image/jpeg")},
        data={"trend_id": "digital-nature"},
        headers=privileged_user_headers
    )
    assert res_catalog.status_code == 200
    cat_data = res_catalog.json()["data"]
    assert cat_data["bucket"] == "trend-images"
    assert cat_data["storage_path"].startswith("trends/digital-nature/")

    # 3. get_public_url on private bucket must raise ValueError
    with pytest.raises(ValueError, match="not configured for public access"):
        supabase_service.get_public_url("user-uploads", "user_123/img.jpg")


def test_local_storage_serving_authorization(client, tmp_path, monkeypatch):
    """
    Verify access control on local storage serving for private buckets:
    - 401 for unauthenticated requests
    - 403 for unauthorized users trying to access another user's file
    - 200 for file owner and privileged roles
    - 400 for path traversal
    """
    import app.routers.images as images_router
    monkeypatch.setattr(images_router, "LOCAL_STORAGE_DIR", tmp_path)

    user_a_id = f"user-a-{uuid.uuid4().hex[:6]}"
    user_b_id = f"user-b-{uuid.uuid4().hex[:6]}"

    token_a = create_access_token({"sub": user_a_id, "email": "a@luxe.tech", "role": "user"})
    token_b = create_access_token({"sub": user_b_id, "email": "b@luxe.tech", "role": "user"})
    token_admin = create_access_token({"sub": "admin-1", "email": "admin@luxe.tech", "role": "admin"})

    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}
    headers_admin = {"Authorization": f"Bearer {token_admin}"}

    # Write a dummy private file for User A
    user_a_dir = tmp_path / "user-uploads" / user_a_id
    user_a_dir.mkdir(parents=True, exist_ok=True)
    test_file = user_a_dir / "private_asset.jpg"
    test_file.write_bytes(b"\xff\xd8\xff\xe0test_bytes")

    file_rel_path = f"{user_a_id}/private_asset.jpg"

    # 1. Unauthenticated request -> 401
    res_unauth = client.get(f"/api/images/local/user-uploads/{file_rel_path}")
    assert res_unauth.status_code == 401

    # 2. User B accessing User A's file -> 403 Forbidden
    res_user_b = client.get(f"/api/images/local/user-uploads/{file_rel_path}", headers=headers_b)
    assert res_user_b.status_code == 403

    # 3. User A accessing own file -> 200 OK
    res_user_a = client.get(f"/api/images/local/user-uploads/{file_rel_path}", headers=headers_a)
    assert res_user_a.status_code == 200

    # 4. Admin accessing file -> 200 OK
    res_admin = client.get(f"/api/images/local/user-uploads/{file_rel_path}", headers=headers_admin)
    assert res_admin.status_code == 200

    # 5. Path traversal attempt -> 400
    res_traversal = client.get("/api/images/local/user-uploads/../../etc/passwd", headers=headers_a)
    assert res_traversal.status_code in (400, 404)


def test_authenticated_rate_limit_keyed_on_user_identity(client):
    """
    Verify that authenticated requests are rate limited by user identity,
    preventing NAT-based collisions between different users sharing an IP.
    """
    limiter.reset()

    token_u1 = create_access_token({"sub": f"u1-{uuid.uuid4().hex[:6]}", "email": "u1@luxe.tech", "role": "lead_analyst"})
    token_u2 = create_access_token({"sub": f"u2-{uuid.uuid4().hex[:6]}", "email": "u2@luxe.tech", "role": "lead_analyst"})

    headers_u1 = {"Authorization": f"Bearer {token_u1}"}
    headers_u2 = {"Authorization": f"Bearer {token_u2}"}

    # Exhaust limit for User 1 on forecast trigger (10 requests)
    for _ in range(10):
        res = client.post("/api/forecast/digital-nature", headers=headers_u1)
        assert res.status_code == 200

    # 11th request for User 1 is rate limited
    res_u1_blocked = client.post("/api/forecast/digital-nature", headers=headers_u1)
    assert res_u1_blocked.status_code == 429

    # User 2 from the exact same client IP is NOT blocked
    res_u2_allowed = client.post("/api/forecast/digital-nature", headers=headers_u2)
    assert res_u2_allowed.status_code == 200


def test_image_record_ownership_and_access_control(client):
    """
    Verify ownership enforcement and access control on ImageRecord entities:
    - Personal image upload creates record in private bucket.
    - Anonymous request to view private image returns 401.
    - Other user accessing private image returns 403.
    - Owner accessing private image returns 200 with URL.
    - Owner can list own images; other users cannot see them.
    - Other user cannot delete owner's image (403).
    - Owner can delete image (200).
    - Deleted image returns 404.
    """
    # Create User A & User B
    user_a_id = f"user-a-{uuid.uuid4().hex[:6]}"
    user_b_id = f"user-b-{uuid.uuid4().hex[:6]}"

    token_a = create_access_token({"sub": user_a_id, "email": "a@luxe.tech", "role": "user"})
    token_b = create_access_token({"sub": user_b_id, "email": "b@luxe.tech", "role": "user"})

    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    img = Image.new("RGB", (100, 100), color=(120, 140, 160))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    img_bytes = buf.getvalue()

    # 1. User A uploads private image
    res_upload = client.post(
        "/api/images/analyze",
        files={"file": ("secret_design.jpg", io.BytesIO(img_bytes), "image/jpeg")},
        headers=headers_a
    )
    assert res_upload.status_code == 200
    img_id = res_upload.json()["data"]["image_id"]
    assert img_id

    # 2. Anonymous request -> 401
    res_anon = client.get(f"/api/images/{img_id}")
    assert res_anon.status_code == 401

    # 3. User B accessing User A's private image -> 403 Forbidden
    res_b = client.get(f"/api/images/{img_id}", headers=headers_b)
    assert res_b.status_code == 403

    # 4. User A accessing own image -> 200 OK
    res_a = client.get(f"/api/images/{img_id}", headers=headers_a)
    assert res_a.status_code == 200
    assert res_a.json()["data"]["id"] == img_id

    # 5. User B listing own images -> empty
    res_b_list = client.get("/api/images?mine=true", headers=headers_b)
    assert res_b_list.status_code == 200
    assert not any(item["id"] == img_id for item in res_b_list.json()["data"])

    # 6. User A listing own images -> contains uploaded image
    res_a_list = client.get("/api/images?mine=true", headers=headers_a)
    assert res_a_list.status_code == 200
    assert any(item["id"] == img_id for item in res_a_list.json()["data"])

    # 7. User B attempting to delete User A's image -> 403 Forbidden
    res_b_del = client.delete(f"/api/images/{img_id}", headers=headers_b)
    assert res_b_del.status_code == 403

    # 8. User A deleting own image -> 200 OK
    res_a_del = client.delete(f"/api/images/{img_id}", headers=headers_a)
    assert res_a_del.status_code == 200
    assert res_a_del.json()["data"]["deleted"] is True

    # 9. GET deleted image -> 404 Not Found
    res_after = client.get(f"/api/images/{img_id}", headers=headers_a)
    assert res_after.status_code == 404

