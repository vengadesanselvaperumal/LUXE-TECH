import asyncio
import importlib
import logging
from types import SimpleNamespace
from unittest.mock import AsyncMock

from app.config import Settings

gemini_module = importlib.import_module("app.services.gemini_service")


def _service(monkeypatch, api_key="test-key", model="gemini-3.8-flash"):
    configured = Settings(_env_file=None, GEMINI_API_KEY=api_key, GEMINI_MODEL=model)
    monkeypatch.setattr(gemini_module, "settings", configured)
    return gemini_module.GeminiService()


def test_model_comes_from_settings_and_uses_async_genai_sdk(monkeypatch):
    service = _service(monkeypatch, model="configured-model")
    assert service._client is not None
    mocked_generate = AsyncMock(return_value=SimpleNamespace(text='{"summary":"verified"}'))
    monkeypatch.setattr(service._client.aio.models, "generate_content", mocked_generate)

    response = asyncio.run(service._call_gemini("test prompt"))

    assert response == {"summary": "verified"}
    mocked_generate.assert_awaited_once()
    call = mocked_generate.await_args
    assert call is not None
    assert call.kwargs["model"] == "configured-model"
    assert call.kwargs["config"].response_mime_type == "application/json"


def test_image_request_uses_sdk_part_with_mime_type(monkeypatch):
    service = _service(monkeypatch)
    assert service._client is not None
    mocked_generate = AsyncMock(return_value=SimpleNamespace(text='{"ok":true}'))
    monkeypatch.setattr(service._client.aio.models, "generate_content", mocked_generate)

    asyncio.run(service._call_gemini("analyze image", image_bytes=b"image-data", mime_type="image/png"))

    call = mocked_generate.await_args
    assert call is not None
    image_part = call.kwargs["contents"][1]
    assert image_part.inline_data.mime_type == "image/png"


def test_missing_key_skips_gemini_and_uses_fallback(monkeypatch):
    service = _service(monkeypatch, api_key="")

    result = asyncio.run(service.analyze_trend("Test trend", "Color", "SS27", {}))

    assert result["summary"]
    assert service._client is None


def test_invalid_response_schema_uses_fallback(monkeypatch, caplog):
    service = _service(monkeypatch)
    service._call_gemini = AsyncMock(return_value={"summary": "not a complete response"})

    with caplog.at_level(logging.WARNING, logger="luxe_tech.gemini"):
        result = asyncio.run(service.analyze_trend("Test trend", "Color", "SS27", {}))

    assert result["visual_dna"]["colors"]
    assert "did not match the expected schema" in caplog.text


def test_api_exception_uses_fallback_without_logging_exception_text(monkeypatch, caplog):
    secret = "do-not-log-this-key"
    service = _service(monkeypatch, api_key=secret)
    assert service._client is not None
    service._client.aio.models.generate_content = AsyncMock(
        side_effect=RuntimeError(f"request failed with key {secret}")
    )

    with caplog.at_level(logging.WARNING, logger="luxe_tech.gemini"):
        result = asyncio.run(service._call_gemini("test prompt"))

    assert result is None
    assert secret not in caplog.text


def test_image_cache_is_scoped_to_image_bytes(monkeypatch):
    service = _service(monkeypatch)
    service._call_gemini = AsyncMock(return_value=None)
    features = {"dominant_colors": [{"hex": "#123456"}]}

    first = asyncio.run(service.analyze_image(b"first-image", "image/png", features))
    second = asyncio.run(service.analyze_image(b"second-image", "image/png", features))

    assert first == second
    assert service._call_gemini.await_count == 2


def test_missing_ai_provider_returns_no_generated_product_or_scenario(monkeypatch):
    service = _service(monkeypatch, api_key="")

    products = asyncio.run(service.generate_product_opportunities("Test", {}, ""))
    prophecy = asyncio.run(service.generate_prophecy("Test", {}, None))
    retail = asyncio.run(service.generate_retail_interpretation("Test", {}, "EU"))

    assert products == []
    assert prophecy == []
    assert retail["data_status"] == "demo"
    assert retail["price_tier"] == "insufficient_data"


def test_product_concepts_drop_unvalidated_scores(monkeypatch):
    service = _service(monkeypatch)
    service._call_gemini = AsyncMock(return_value=[
        {
            "name": f"Concept {index}",
            "category": "Tailoring",
            "description": "A hypothetical apparel design concept.",
            "material": "Wool",
            "silhouette": "Relaxed",
            "color": "Charcoal",
            "target_consumer": "Not specified",
            "design_rationale": "The material and cut create a soft structure.",
            "opportunity_score": 95,
        }
        for index in range(3)
    ])

    concepts = asyncio.run(service.generate_product_opportunities("Test", {}, ""))

    assert len(concepts) == 3
    assert all("opportunity_score" not in concept for concept in concepts)
    assert all("ai_reasoning" not in concept for concept in concepts)
    assert concepts[0]["design_rationale"]


def test_retail_interpretation_validates_and_caches_ai_response(monkeypatch):
    service = _service(monkeypatch)
    service._call_gemini = AsyncMock(return_value={
        "interpretation": "The submitted observations indicate stronger demand.",
        "assortment_recommendation": "Prioritize the supplied high-demand category.",
        "price_tier": "premium",
    })

    first = asyncio.run(service.generate_retail_interpretation("Test", {"demand": 72}, "EU"))
    second = asyncio.run(service.generate_retail_interpretation("Test", {"demand": 72}, "EU"))

    assert first["data_status"] == "ai_generated"
    assert first["region"] == "EU"
    assert second == first
    service._call_gemini.assert_awaited_once()


def test_invalid_retail_interpretation_uses_demo_fallback(monkeypatch):
    service = _service(monkeypatch)
    service._call_gemini = AsyncMock(return_value=["not", "an", "object"])

    result = asyncio.run(service.generate_retail_interpretation("Test", {}, "EU"))

    assert result["data_status"] == "demo"
    assert result["price_tier"] == "insufficient_data"
