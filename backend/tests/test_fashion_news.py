from datetime import datetime, timezone

from app.services.fashion_news_service import (
    FashionNewsService,
    FashionNewsUnavailable,
    VOGUE_FEED_URL,
    fashion_news_service,
)


def test_rss_parser_preserves_publisher_and_observation_provenance():
    content = b"""<?xml version="1.0"?>
    <rss version="2.0">
      <channel>
        <item>
          <title>Verified Fashion Report</title>
          <link>https://www.vogue.com/article/verified-fashion-report</link>
          <description>Publisher-supplied article summary.</description>
          <pubDate>Sun, 11 Oct 2026 14:58:59 +0000</pubDate>
        </item>
        <item><title>Unsafe link</title><link>javascript:alert(1)</link></item>
      </channel>
    </rss>"""
    fetched_at = datetime.now(timezone.utc).isoformat()

    items = FashionNewsService._parse_feed(content, fetched_at)

    assert len(items) == 1
    assert items[0]["title"] == "Verified Fashion Report"
    assert items[0]["source_name"] == "Vogue"
    assert items[0]["source_url"] == VOGUE_FEED_URL
    assert items[0]["observed_at"] == "2026-10-11T14:58:59+00:00"
    assert items[0]["fetched_at"] == fetched_at
    assert items[0]["quality"] == "publisher_rss"
    assert items[0]["data_status"] == "observed"


def test_current_news_endpoint_returns_sourced_articles(client, monkeypatch):
    async def fake_news():
        return {
            "items": [{
                "title": "Verified Fashion Report",
                "url": "https://www.vogue.com/article/verified-fashion-report",
                "source_name": "Vogue",
                "source_url": VOGUE_FEED_URL,
                "observed_at": "2026-10-11T14:58:59+00:00",
                "fetched_at": "2026-10-11T15:00:00+00:00",
                "quality": "publisher_rss",
                "data_status": "observed",
            }],
            "source_name": "Vogue",
            "source_url": VOGUE_FEED_URL,
            "fetched_at": "2026-10-11T15:00:00+00:00",
            "data_status": "observed",
            "stale": False,
        }

    monkeypatch.setattr(fashion_news_service, "get_current_news", fake_news)
    response = client.get("/api/news/current")

    assert response.status_code == 200
    article = response.json()["data"]["items"][0]
    assert article["source_url"] == VOGUE_FEED_URL
    assert article["observed_at"]
    assert article["fetched_at"]
    assert article["data_status"] == "observed"


def test_current_news_endpoint_surfaces_provider_unavailable(client, monkeypatch):
    async def unavailable():
        raise FashionNewsUnavailable("Fashion news provider is temporarily unavailable.")

    monkeypatch.setattr(fashion_news_service, "get_current_news", unavailable)
    response = client.get("/api/news/current")

    assert response.status_code == 503
    assert response.json()["success"] is False
