import io
import importlib
import json
import uuid
from datetime import datetime, timedelta, timezone
import pytest
from PIL import Image
from app.database import Forecast, ImageRecord, SessionLocal, Trend, TrendSignal
from app.services.forecast_engine import forecast_engine
from app.services.vision_engine import vision_engine
from app.utils.security import hash_password, verify_password

supabase_module = importlib.import_module("app.services.supabase_service")


def test_health_check(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["status"] == "healthy"
    assert data["data"]["database_connected"] is True
    assert data["data"]["database_backend"] == "sqlite"
    assert data["data"]["supabase_postgres_connected"] is False


def test_authentication_flow(client):
    test_email = f"test_designer_{uuid.uuid4().hex[:8]}@luxe.tech"
    # 1. Register
    reg_resp = client.post("/api/auth/register", json={
        "email": test_email,
        "password": "Password123!",
        "name": "Test Designer"
    })
    assert reg_resp.status_code == 200
    reg_json = reg_resp.json()
    assert reg_json["success"] is True
    token = reg_json["data"]["token"]
    assert token

    # 2. Login
    login_resp = client.post("/api/auth/login", json={
        "email": test_email,
        "password": "Password123!"
    })
    assert login_resp.status_code == 200
    assert login_resp.json()["data"]["token"]

    invalid_login = client.post("/api/auth/login", json={
        "email": test_email,
        "password": "WrongPassword123!"
    })
    assert invalid_login.status_code == 401

    unknown_login = client.post("/api/auth/login", json={
        "email": "unknown@luxe.tech",
        "password": "Password123!"
    })
    assert unknown_login.status_code == 401

    # 3. Protected /me endpoint
    me_resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 200
    assert me_resp.json()["data"]["email"] == test_email

    tampered_token = token[:-1] + ("a" if token[-1] != "a" else "b")
    tampered_me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {tampered_token}"})
    assert tampered_me.status_code == 401


def test_password_hash_uses_salted_pbkdf2():
    first_hash = hash_password("correct horse battery staple")
    second_hash = hash_password("correct horse battery staple")

    assert first_hash != second_hash
    assert first_hash.startswith("pbkdf2_sha256$")
    assert verify_password("correct horse battery staple", first_hash)
    assert not verify_password("wrong password", first_hash)


def test_dashboard_endpoint(client):
    response = client.get("/api/dashboard")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    data = body["data"]

    assert "hero" in data
    assert "recent_trends" in data
    assert "live_signals" in data
    assert "featured_trends" in data
    assert "current_fashion" in data
    assert "featured_products" in data
    assert "forecast_highlights" in data
    assert "prophecy_highlights" in data

    # Live signals strip channels
    live = data["live_signals"]
    for ch in ["runway", "social", "search", "retail", "culture"]:
        assert ch in live
        assert live[ch] is None
    assert live["data_status"] == "insufficient_data"


def test_trends_and_categories(client):
    # Test categories
    cat_resp = client.get("/api/trends/categories")
    assert cat_resp.status_code == 200
    cats = cat_resp.json()["data"]
    assert len(cats) == 16
    assert any(c["name"] == "Color" for c in cats)
    assert any(c["name"] == "Silhouettes" for c in cats)

    # Test list trends
    trends_resp = client.get("/api/trends?sort=recent&limit=10")
    assert trends_resp.status_code == 200
    trends = trends_resp.json()["data"]
    assert trends == []

    # Test category filtering
    filter_resp = client.get("/api/trends?category=Color")
    assert filter_resp.status_code == 200
    filtered = filter_resp.json()["data"]
    assert filtered == []


def test_trend_detail_access_controls_and_candidate_resolution(client):
    # Default query strictly isolates unverified demo and candidate trends
    hidden_demo = client.get("/api/trends/digital-nature")
    assert hidden_demo.status_code == 200
    assert hidden_demo.json()["success"] is False
    assert hidden_demo.json()["error"]["code"] == "TREND_NOT_FOUND"

    # Explicit include_demo surfaces demo trend with honest confidence=None
    demo_resp = client.get("/api/trends/digital-nature?include_demo=true")
    if demo_resp.json().get("success"):
        data = demo_resp.json()["data"]
        assert data["data_status"] == "demo"
        assert data["confidence"] is None

    # Explicit include_candidates surfaces news-derived candidate with confidence=None and momentum=None
    cand_resp = client.get("/api/trends/tactile-suede-heritage-leather?include_candidates=true")
    if cand_resp.json().get("success"):
        cdata = cand_resp.json()["data"]
        assert cdata["data_status"] == "news_derived"
        assert cdata["confidence"] is None
        assert cdata["momentum"] is None


def test_signals_endpoints(client):
    live_resp = client.get("/api/signals/live")
    assert live_resp.status_code == 200
    live_data = live_resp.json()["data"]
    assert "runway" in live_data
    assert "social" in live_data

    # Trend signals
    signals_resp = client.get("/api/signals/digital-nature")
    assert signals_resp.status_code == 200
    sigs = signals_resp.json()["data"]
    assert sigs == []


def test_collections_endpoints(client):
    col_resp = client.get("/api/collections/digital-nature")
    assert col_resp.status_code == 200
    col = col_resp.json()["data"]
    assert "color_palette" in col
    assert "materials" in col
    assert "silhouettes" in col


def test_products_endpoints(client, auth_headers, privileged_user_headers):
    # List products
    prod_resp = client.get("/api/products?limit=10")
    assert prod_resp.status_code == 200
    prods = prod_resp.json()["data"]
    assert prods == []

    # Trend products
    trend_prods = client.get("/api/products/trend/digital-nature")
    assert trend_prods.status_code == 200
    assert trend_prods.json()["data"] == []

    # Unauthenticated generate products returns 401
    unauth_resp = client.post("/api/products/generate", json={
        "trend_id": "digital-nature",
        "category": "Tailoring"
    })
    assert unauth_resp.status_code == 401

    # Ordinary user generate products returns 403 Forbidden
    forbidden_resp = client.post("/api/products/generate", json={
        "trend_id": "digital-nature",
        "category": "Tailoring"
    }, headers=auth_headers)
    assert forbidden_resp.status_code == 403

    # Privileged user cannot generate products from an unverified demo trend.
    gen_resp = client.post("/api/products/generate", json={
        "trend_id": "digital-nature",
        "category": "Tailoring"
    }, headers=privileged_user_headers)
    assert gen_resp.status_code == 200
    assert gen_resp.json()["success"] is False
    assert gen_resp.json()["error"]["code"] == "TREND_NOT_FOUND"


def test_retail_endpoints(client):
    ret_resp = client.get("/api/retail")
    assert ret_resp.status_code == 200
    ret_data = ret_resp.json()["data"]
    assert "market" in ret_data
    assert "regions" in ret_data
    assert "categories" in ret_data

    # Trend retail
    trend_ret = client.get("/api/retail/trend/digital-nature")
    assert trend_ret.status_code == 200
    assert trend_ret.json()["data"]["signals"] == []
    assert trend_ret.json()["data"]["data_status"] == "insufficient_data"


def test_forecast_models_and_insufficient_data(client, auth_headers, privileged_user_headers):
    insufficient_response = client.get("/api/forecast/digital-nature")
    assert insufficient_response.status_code == 200
    assert insufficient_response.json()["data"]["status"] == "insufficient_data"

    db = SessionLocal()
    try:
        trend = db.query(Trend).filter(Trend.slug == "digital-nature").first()
        fetched_at = datetime.now(timezone.utc).isoformat()
        for index in range(12):
            db.add(TrendSignal(
                trend_id=trend.id,
                source="search",
                signal_type="demand_index",
                strength=float(40 + 2 * index + index % 3),
                timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc) + timedelta(days=30 * index),
                metadata_json=json.dumps({
                    "source_name": "test fixture",
                    "source_url": "https://example.org/test-dataset.csv",
                    "fetched_at": fetched_at,
                }),
                data_status="observed",
            ))
        db.commit()
    finally:
        db.close()

    # Valid trend forecast
    fc_resp = client.get("/api/forecast/digital-nature")
    assert fc_resp.status_code == 200
    fc_data = fc_resp.json()["data"]
    assert "selected_model" in fc_data
    assert "model_evaluations" in fc_data
    assert len(fc_data["model_evaluations"]) > 0
    assert "backtest_accuracy" in fc_data
    assert "confidence" not in fc_data
    assert {model["name"] for model in fc_data["model_evaluations"]} == {
        "moving_average",
        "simple_exponential_smoothing",
        "holt_winters",
        "linear_regression",
    }
    for model in fc_data["model_evaluations"]:
        assert {"mae", "rmse", "mape", "backtest_accuracy"} <= model.keys()
        assert model["backtest_accuracy"] == round(max(0.0, 100.0 - model["mape"]), 1)
    assert "historical_points" in fc_data
    assert "projected_points" in fc_data
    assert fc_data["historical_points"][0]["source_url"] == "https://example.org/test-dataset.csv"
    assert fc_data["historical_points"][0]["fetched_at"]

    # Unauthenticated forecast POST returns 401
    unauth_saved = client.post("/api/forecast/digital-nature")
    assert unauth_saved.status_code == 401

    # Ordinary user forecast POST returns 403 Forbidden
    forbidden_saved = client.post("/api/forecast/digital-nature", headers=auth_headers)
    assert forbidden_saved.status_code == 403

    # Privileged user forecast POST returns 200 OK
    saved_resp = client.post("/api/forecast/digital-nature", headers=privileged_user_headers)
    assert saved_resp.status_code == 200
    saved_data = saved_resp.json()["data"]
    db = SessionLocal()
    try:
        saved_forecast = db.query(Forecast).filter(Forecast.trend_id == saved_data["trend_id"]).first()
        assert saved_forecast is not None
        assert saved_forecast.backtest_accuracy == saved_data["backtest_accuracy"]
        assert saved_forecast.data_status == "forecast"
        assert saved_forecast.training_start is not None
        assert saved_forecast.training_end is not None
    finally:
        db.close()

    observations = [
        {
            "timestamp": (datetime(2024, 1, 1, tzinfo=timezone.utc) + timedelta(days=30 * index)).isoformat(),
            "strength": float(40 + 2 * index + index % 3),
        }
        for index in reversed(range(12))
    ]
    chronological_result = forecast_engine.generate_forecast(observations)
    history = chronological_result["historical_points"]
    assert history[0]["timestamp"].startswith("2024-01-01")
    assert history[-1]["timestamp"].startswith("2024-11-26")

    # Direct ForecastEngine insufficient data test
    few_obs = [{"strength": 75.0, "timestamp": "2026-01-01"}]
    res = forecast_engine.generate_forecast(few_obs)
    assert res["status"] == "insufficient_data"
    assert res["data_status"] == "insufficient_data"


def test_forecast_mape_is_undefined_when_backtest_actuals_include_zero():
    observations = [
        {"strength": value, "timestamp": (datetime(2025, 1, 1, tzinfo=timezone.utc) + timedelta(days=30 * index)).isoformat()}
        for index, value in enumerate([10.0, 12.0, 11.0, 15.0, 14.0, 13.0, 0.0, 0.0])
    ]

    result = forecast_engine.generate_forecast(observations)

    assert result["status"] == "success"
    assert result["backtest_accuracy"] is None
    assert all(item["mape"] is None for item in result["model_evaluations"])
    assert all(item["backtest_accuracy"] is None for item in result["model_evaluations"])


def test_prophecy_endpoint(client):
    pr_resp = client.get("/api/prophecy/digital-nature")
    assert pr_resp.status_code == 200
    pr_data = pr_resp.json()["data"]
    assert "timeline" in pr_data
    assert pr_data["timeline"] == []
    assert pr_data["data_status"] == "insufficient_data"
    assert "validated ai scenario" in pr_data["message"].lower()


def test_search_endpoint(client):
    s_resp = client.get("/api/search?q=Digital")
    assert s_resp.status_code == 200
    results = s_resp.json()["data"]
    assert "trends" in results
    assert "products" in results
    assert results["trends"] == []
    assert results["products"] == []


def test_image_analysis_and_vision_engine(client, monkeypatch, tmp_path, auth_headers):
    monkeypatch.setattr(supabase_module, "LOCAL_STORAGE_DIR", tmp_path)
    monkeypatch.setattr(supabase_module.supabase_service, "supabase_url", "")
    monkeypatch.setattr(supabase_module.supabase_service, "active_key", "")

    # 1. Create a dummy synthetic JPEG image in memory
    img = Image.new("RGB", (200, 200), color=(13, 31, 34))
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format="JPEG")
    img_bytes = img_byte_arr.getvalue()

    # 2. Test Vision Engine directly
    features = vision_engine.extract_features_from_bytes(img_bytes)
    assert "dominant_colors" in features
    assert len(features["dominant_colors"]) > 0
    assert "contrast" in features
    assert "edge_density" in features
    assert features["width"] == 200
    assert features["height"] == 200

    # Unauthenticated upload returns 401
    unauth_files = {"file": ("test_runway.jpg", img_bytes, "image/jpeg")}
    unauth_resp = client.post("/api/images/analyze", files=unauth_files)
    assert unauth_resp.status_code == 401

    # 3. Test API endpoint POST /api/images/analyze with authentication
    files = {"file": ("test_runway.jpg", img_bytes, "image/jpeg")}
    response = client.post("/api/images/analyze", files=files, headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert "image_analysis" in body["data"]
    assert "vision_metrics" in body["data"]
    assert body["data"]["data_status"] == "demo"
    assert body["data"]["vision_metrics"]["data_status"] == "derived"
    assert body["data"]["storage_backend"] == "local"
    assert body["data"]["bucket"] == "user-uploads"
    stored_path = body["data"]["storage_path"]
    assert (tmp_path / "user-uploads" / stored_path).read_bytes() == img_bytes
    db = SessionLocal()
    try:
        record = db.query(ImageRecord).filter(ImageRecord.id == body["data"]["image_id"]).first()
        assert record is not None
        assert record.data_status == "demo"
        assert record.storage_path == stored_path
    finally:
        db.close()


def test_invalid_image_upload(client, auth_headers):
    # Text file masquerading as image
    files = {"file": ("malicious.exe", b"MZexecutable_code_here", "application/octet-stream")}
    response = client.post("/api/images/analyze", files=files, headers=auth_headers)
    assert response.status_code in [400, 422]
    assert response.json()["success"] is False
