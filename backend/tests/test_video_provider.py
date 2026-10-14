import asyncio
from datetime import datetime, timezone

import httpx
import pytest

from app.services.video_provider import VideoProviderError, YouTubeDataApiProvider


class StubYouTubeClient:
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


def test_youtube_provider_returns_source_attribution_and_caches(monkeypatch):
    provider = YouTubeDataApiProvider()
    provider.api_key = "test-key"
    client = StubYouTubeClient({
        "items": [{
            "id": {"videoId": "AbC123_xyz"},
            "snippet": {
                "title": "Runway collection overview",
                "channelTitle": "Fashion Publisher",
                "publishedAt": "2026-10-12T08:30:00Z",
                "thumbnails": {"high": {"url": "https://i.ytimg.com/vi/AbC123_xyz/hqdefault.jpg"}},
            },
        }],
    })
    calls = []

    def build_client(**_kwargs):
        calls.append(True)
        return client

    monkeypatch.setattr("app.services.video_provider.httpx.AsyncClient", build_client)

    async def check():
        first = await provider.search(
            "runway",
            published_after=datetime(2026, 10, 1, tzinfo=timezone.utc),
            region_code="gb",
        )
        second = await provider.search(
            "runway",
            published_after=datetime(2026, 10, 1, tzinfo=timezone.utc),
            region_code="GB",
        )
        return first, second

    first, second = asyncio.run(check())
    assert first == second
    assert calls == [True]
    assert first == [{
        "title": "Runway collection overview",
        "creator": "Fashion Publisher",
        "thumbnail_url": "https://i.ytimg.com/vi/AbC123_xyz/hqdefault.jpg",
        "published_at": "2026-10-12T08:30:00Z",
        "canonical_url": "https://www.youtube.com/watch?v=AbC123_xyz",
        "video_id": "AbC123_xyz",
        "source": "YouTube Data API",
    }]
    assert client.params["key"] == "test-key"
    assert client.params["regionCode"] == "GB"
    assert client.params["publishedAfter"] == "2026-10-01T00:00:00Z"
    assert provider.status()["last_successful_fetch"]


def test_youtube_provider_explicitly_rejects_missing_credentials():
    provider = YouTubeDataApiProvider()
    provider.api_key = ""

    assert provider.status()["available"] is False
    assert provider.status()["state"] == "unavailable"
    with pytest.raises(VideoProviderError) as error:
        asyncio.run(provider.search("fashion"))
    assert error.value.code == "credentials_missing"
    assert "test-key" not in str(provider.status())


def test_youtube_provider_maps_timeouts_and_empty_results(monkeypatch):
    provider = YouTubeDataApiProvider()
    provider.api_key = "test-key"
    timeout_client = StubYouTubeClient(httpx.TimeoutException("request timed out"))
    monkeypatch.setattr("app.services.video_provider.httpx.AsyncClient", lambda **_kwargs: timeout_client)

    with pytest.raises(VideoProviderError) as timeout_error:
        asyncio.run(provider.search("fashion"))
    assert timeout_error.value.code == "provider_timeout"

    empty_provider = YouTubeDataApiProvider()
    empty_provider.api_key = "test-key"
    monkeypatch.setattr(
        "app.services.video_provider.httpx.AsyncClient",
        lambda **_kwargs: StubYouTubeClient({"items": []}),
    )
    assert asyncio.run(empty_provider.search("fashion")) == []
    assert empty_provider.status()["last_successful_fetch"]


def test_youtube_provider_surfaces_quota_and_permission_failures(monkeypatch):
    provider = YouTubeDataApiProvider()
    provider.api_key = "test-key"

    class QuotaClient(StubYouTubeClient):
        async def get(self, _url, params):
            self.params = params
            return httpx.Response(
                403,
                json={"error": {"message": "private provider details"}},
                request=httpx.Request("GET", "https://www.googleapis.com/youtube/v3/search"),
            )

    monkeypatch.setattr(
        "app.services.video_provider.httpx.AsyncClient",
        lambda **_kwargs: QuotaClient({}),
    )
    with pytest.raises(VideoProviderError) as error:
        asyncio.run(provider.search("fashion"))
    assert error.value.code == "quota_or_permission"
    assert "private provider details" not in str(error.value)


def test_video_status_and_search_report_missing_credentials(client, monkeypatch):
    monkeypatch.setattr("app.routers.videos.youtube_video_provider.api_key", "")
    status_response = client.get("/api/videos/status")
    search_response = client.get("/api/videos/search")

    assert status_response.status_code == 200
    assert status_response.json()["data"]["available"] is False
    assert search_response.status_code == 503
    assert search_response.json()["error"]["message"]["code"] == "credentials_missing"
