import asyncio
import importlib

import pytest

supabase_module = importlib.import_module("app.services.supabase_service")


class FakeResponse:
    def __init__(self, status_code, payload=None):
        self.status_code = status_code
        self._payload = payload or {}

    def json(self):
        return self._payload


class FakeAsyncClient:
    responses = []
    calls = []

    def __init__(self, **_kwargs):
        self.responses = type(self).responses
        self.calls = type(self).calls

    async def __aenter__(self):
        return self

    async def __aexit__(self, _exc_type, _exc, _traceback):
        return False

    async def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.responses.pop(0)


def _configured_storage(monkeypatch, responses):
    service = supabase_module.SupabaseService()
    service.supabase_url = "https://project.example"
    service.service_key = "server-only-test-key"
    service.anon_key = "public-test-key"
    service.active_key = service.service_key
    FakeAsyncClient.responses = list(responses)
    FakeAsyncClient.calls = []
    monkeypatch.setattr(supabase_module.httpx, "AsyncClient", FakeAsyncClient)
    return service


def test_public_bucket_upload_returns_public_url(monkeypatch):
    service = _configured_storage(monkeypatch, [FakeResponse(200)])

    result = asyncio.run(
        service.upload_file("trend-images", "asset.png", b"image", "image/png")
    )

    assert result == (
        "https://project.example/storage/v1/object/public/trend-images/asset.png"
    )
    assert len(FakeAsyncClient.calls) == 1


def test_private_bucket_upload_returns_temporary_signed_url(monkeypatch):
    service = _configured_storage(
        monkeypatch,
        [
            FakeResponse(200),
            FakeResponse(
                200,
                {"signedURL": "/object/sign/user-uploads/asset.png?token=temporary"},
            ),
        ],
    )

    result = asyncio.run(
        service.upload_file("user-uploads", "asset.png", b"image", "image/png")
    )

    assert result == (
        "https://project.example/storage/v1/object/sign/"
        "user-uploads/asset.png?token=temporary"
    )
    assert len(FakeAsyncClient.calls) == 2
    signing_url, signing_request = FakeAsyncClient.calls[1]
    assert signing_url.endswith("/storage/v1/object/sign/user-uploads/asset.png")
    assert signing_request["json"] == {"expiresIn": 3600}


def test_private_bucket_cannot_be_given_a_public_url(monkeypatch):
    service = _configured_storage(monkeypatch, [])

    with pytest.raises(ValueError, match="not configured for public access"):
        service.get_public_url("user-uploads", "asset.png")


def test_configured_storage_upload_failure_does_not_fall_back_to_local(
    monkeypatch, tmp_path
):
    service = _configured_storage(monkeypatch, [FakeResponse(403)])
    monkeypatch.setattr(supabase_module, "LOCAL_STORAGE_DIR", tmp_path)

    with pytest.raises(RuntimeError, match="local fallback is disabled"):
        asyncio.run(
            service.upload_file("user-uploads", "asset.png", b"image", "image/png")
        )

    assert not (tmp_path / "user-uploads" / "asset.png").exists()


def test_configured_storage_network_failure_does_not_fall_back_to_local(
    monkeypatch, tmp_path
):
    service = _configured_storage(monkeypatch, [])
    monkeypatch.setattr(supabase_module, "LOCAL_STORAGE_DIR", tmp_path)

    async def fail_upload(self, _url, **_kwargs):
        raise supabase_module.httpx.ConnectError("test connection failure")

    monkeypatch.setattr(FakeAsyncClient, "post", fail_upload)

    with pytest.raises(RuntimeError, match="local fallback is disabled"):
        asyncio.run(
            service.upload_file("user-uploads", "asset.png", b"image", "image/png")
        )

    assert not (tmp_path / "user-uploads" / "asset.png").exists()
