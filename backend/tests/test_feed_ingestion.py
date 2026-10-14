import time
import uuid
from unittest.mock import AsyncMock, MagicMock
import httpx
import pytest

from app.database import Trend, TrendSignal
from app.services.feed_ingestion_service import (
    FeedIngestionService,
    FeedSourceConfig,
    THEME_ARCHETYPES,
    article_matches_archetype,
    canonicalize_url,
    clean_html_text,
    feed_ingestion_service,
    parse_rfc822_or_iso_date,
)
from tests.conftest import TestingSessionLocal


SAMPLE_VOGUE_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:media="http://search.yahoo.com/mrss/">
  <channel>
    <title>Vogue Fashion</title>
    <link>https://www.vogue.com</link>
    <description>The latest fashion news and runway coverage.</description>
    <item>
      <title>Sculptural Tailoring Dominates Paris Haute Couture Week</title>
      <link>https://www.vogue.com/article/sculptural-tailoring-paris?utm_source=rss&amp;utm_medium=feed</link>
      <description>&lt;p&gt;Architectural blazers, oversized suiting, and sharp wool tailoring define the new silhouette.&lt;/p&gt;</description>
      <pubDate>Mon, 12 Oct 2026 08:30:00 +0000</pubDate>
      <category>Couture</category>
      <category>Silhouettes</category>
      <media:thumbnail url="https://assets.vogue.com/photos/sculptural-tailoring.jpg"/>
    </item>
    <item>
      <title>The Return of Butter Yellow for Spring</title>
      <link>https://www.vogue.com/article/butter-yellow-trend</link>
      <description>Pale yellow palettes and pastel poplin dresses take center stage.</description>
      <pubDate>Mon, 12 Oct 2026 09:15:00 +0000</pubDate>
      <category>Color</category>
    </item>
  </channel>
</rss>"""

SAMPLE_HARPERS_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Harper's Bazaar</title>
    <link>https://www.harpersbazaar.com</link>
    <item>
      <title>How to Style Sculptural Tailoring and Oversized Blazers This Fall</title>
      <link>https://www.harpersbazaar.com/fashion/trends/sculptural-tailoring-guide/</link>
      <description>&lt;p class="rte"&gt;From padded shoulders to wide-leg trousers, suiting gets an architectural upgrade.&lt;/p&gt;</description>
      <pubDate>Sun, 11 Oct 2026 22:00:00 +0000</pubDate>
    </item>
    <item>
      <title>Invalid HTTP Article</title>
      <link>http://insecure-site.com/article</link>
      <description>Insecure article link should be ignored</description>
      <pubDate>Sun, 11 Oct 2026 21:00:00 +0000</pubDate>
    </item>
  </channel>
</rss>"""


def test_url_canonicalization():
    assert canonicalize_url("https://www.vogue.com/article/test?utm_source=twitter&utm_medium=social") == "https://www.vogue.com/article/test"
    assert canonicalize_url("https://www.vogue.com/article/test/") == "https://www.vogue.com/article/test"
    assert canonicalize_url("http://insecure.com/article") is None
    assert canonicalize_url("ftp://ftp.example.com") is None
    assert canonicalize_url("") is None
    assert canonicalize_url(None) is None


def test_html_text_cleaning():
    raw = "<p>Clean <b>text</b> with &amp; entities and <i>tags</i>.</p>"
    cleaned = clean_html_text(raw)
    assert cleaned == "Clean text with & entities and tags."
    assert clean_html_text(None) == ""
    assert clean_html_text("") == ""


def test_date_parsing_rfc822_and_iso():
    assert parse_rfc822_or_iso_date("Mon, 12 Oct 2026 08:30:00 +0000") == "2026-10-12T08:30:00+00:00"
    assert parse_rfc822_or_iso_date("2026-10-12T08:30:00Z") == "2026-10-12T08:30:00+00:00"
    assert parse_rfc822_or_iso_date("invalid-date-string") is None
    assert parse_rfc822_or_iso_date("") is None
    assert parse_rfc822_or_iso_date(None) is None


def test_feed_parsing_preserves_provenance():
    service = FeedIngestionService()
    source = FeedSourceConfig(
        name="Vogue",
        feed_url="https://www.vogue.com/feed/rss",
        publisher="Vogue",
        homepage="https://www.vogue.com",
    )
    fetched_at = "2026-10-12T10:00:00+00:00"

    articles = service.parse_feed_xml(SAMPLE_VOGUE_XML, source, fetched_at)
    assert len(articles) == 2

    art1 = articles[0]
    assert art1["title"] == "Sculptural Tailoring Dominates Paris Haute Couture Week"
    assert art1["canonical_url"] == "https://www.vogue.com/article/sculptural-tailoring-paris"
    assert art1["publisher"] == "Vogue"
    assert art1["source_name"] == "Vogue"
    assert art1["source_url"] == "https://www.vogue.com/feed/rss"
    assert art1["published_at"] == "2026-10-12T08:30:00+00:00"
    assert art1["observed_at"] == "2026-10-12T08:30:00+00:00"
    assert art1["fetched_at"] == fetched_at
    assert art1["quality"] == "publisher_rss"
    assert art1["data_status"] == "observed"
    assert art1["image_url"] == "https://assets.vogue.com/photos/sculptural-tailoring.jpg"
    assert "Silhouettes" in art1["categories"]
    assert "tailoring" in art1["keywords"]


def test_feed_deduplication_by_canonical_url():
    service = FeedIngestionService()
    articles = [
        {
            "canonical_url": "https://www.vogue.com/article/test-tailoring",
            "title": "Article One",
            "publisher": "Vogue",
        },
        {
            "canonical_url": "https://www.vogue.com/article/test-tailoring",
            "title": "Article One Duplicate",
            "publisher": "Vogue",
        },
        {
            "canonical_url": "https://www.harpersbazaar.com/article/other",
            "title": "Article Two",
            "publisher": "Harper's Bazaar",
        },
    ]

    deduped = service.deduplicate_articles(articles)
    assert len(deduped) == 2
    assert deduped[0]["canonical_url"] == "https://www.vogue.com/article/test-tailoring"
    assert deduped[1]["canonical_url"] == "https://www.harpersbazaar.com/article/other"


def test_feed_handles_malformed_xml():
    service = FeedIngestionService()
    source = FeedSourceConfig(
        name="Vogue",
        feed_url="https://www.vogue.com/feed/rss",
        publisher="Vogue",
        homepage="https://www.vogue.com",
    )
    corrupted_xml = b"<?xml version='1.0'?><rss><channel><item><title>Broken<link>"
    articles = service.parse_feed_xml(corrupted_xml, source, "2026-10-12T10:00:00+00:00")
    assert articles == []


def test_feed_handles_empty_channel_and_missing_items():
    service = FeedIngestionService()
    source = FeedSourceConfig(
        name="Vogue",
        feed_url="https://www.vogue.com/feed/rss",
        publisher="Vogue",
        homepage="https://www.vogue.com",
    )
    empty_channel = b"<?xml version='1.0'?><rss><channel><title>Empty</title></channel></rss>"
    no_channel = b"<?xml version='1.0'?><rss><feed></feed></rss>"

    assert service.parse_feed_xml(empty_channel, source, "2026-10-12T10:00:00+00:00") == []
    assert service.parse_feed_xml(no_channel, source, "2026-10-12T10:00:00+00:00") == []


@pytest.mark.anyio
async def test_feed_fetch_handles_network_timeout_and_errors():
    service = FeedIngestionService()
    source = FeedSourceConfig(
        name="TestTimeout",
        feed_url="https://www.example.com/feed/rss",
        publisher="Test Publisher",
        homepage="https://www.example.com",
    )

    mock_client = AsyncMock()
    mock_client.get.side_effect = httpx.TimeoutException("Connection timed out")

    articles = await service.fetch_source(mock_client, source, "2026-10-12T10:00:00+00:00")
    assert articles == []
    status = service._status_by_source["TestTimeout"]
    assert status.status == "failing"
    assert "timed out" in status.error.lower()


def test_candidate_trend_derivation_from_multiple_articles():
    service = FeedIngestionService()
    vogue_source = FeedSourceConfig(name="Vogue", feed_url="https://www.vogue.com/feed/rss", publisher="Vogue", homepage="https://www.vogue.com")
    harpers_source = FeedSourceConfig(name="Harper's Bazaar", feed_url="https://www.harpersbazaar.com/rss/all.xml", publisher="Harper's Bazaar", homepage="https://www.harpersbazaar.com")

    articles_vogue = service.parse_feed_xml(SAMPLE_VOGUE_XML, vogue_source, "2026-10-12T10:00:00+00:00")
    articles_harpers = service.parse_feed_xml(SAMPLE_HARPERS_XML, harpers_source, "2026-10-12T10:00:00+00:00")

    combined = articles_vogue + articles_harpers

    # When min_articles is 2, Sculptural Tailoring & Suiting should be derived because both Vogue and Harper's mention tailoring / blazers
    candidate_trends = service.derive_candidate_trends(combined, min_articles=2)
    assert len(candidate_trends) >= 1

    tailoring_trend = next(t for t in candidate_trends if "Tailoring" in t["name"])
    assert tailoring_trend["data_status"] == "news_derived"
    assert tailoring_trend["category"] == "Silhouettes"
    assert "not a consumer or market metric" in tailoring_trend["description"].lower()
    assert tailoring_trend["is_candidate"] is True
    assert len(tailoring_trend["attributing_articles"]) >= 2
    assert "Vogue" in tailoring_trend["description"]
    assert "Harper's Bazaar" in tailoring_trend["description"]
    assert tailoring_trend["publisher_count"] == 2
    assert "confidence" not in tailoring_trend
    assert "momentum" not in tailoring_trend
    assert "velocity" not in tailoring_trend
    assert "signals" not in tailoring_trend
    assert "dna" not in tailoring_trend

    # When an archetype has only 1 article (e.g. Butter Yellow only in Vogue sample), it must NOT be derived when min_articles=2
    yellow_trend = next((t for t in candidate_trends if "Yellow" in t["name"]), None)
    assert yellow_trend is None


@pytest.mark.anyio
async def test_cached_candidate_trends_filter_by_category():
    service = FeedIngestionService()
    service._candidate_trends = [
        {"name": "Tailoring", "category": "Silhouettes"},
        {"name": "Butter Yellow", "category": "Color"},
    ]
    service._cached_at = time.monotonic()

    assert await service.get_candidate_trends("sILHouettes") == [
        {"name": "Tailoring", "category": "Silhouettes"}
    ]
    assert await service.get_candidate_trends("Accessories") == []
    assert len(await service.get_candidate_trends()) == 2


@pytest.mark.anyio
async def test_news_refresh_does_not_persist_editorial_candidates():
    service = FeedIngestionService()
    source1 = FeedSourceConfig(name="Vogue", feed_url="https://www.vogue.com/feed/rss", publisher="Vogue", homepage="https://www.vogue.com")
    source2 = FeedSourceConfig(name="Harper's Bazaar", feed_url="https://www.harpersbazaar.com/rss/all.xml", publisher="Harper's Bazaar", homepage="https://www.harpersbazaar.com")

    articles = (
        service.parse_feed_xml(SAMPLE_VOGUE_XML, source1, "2026-10-12T10:00:00+00:00")
        + service.parse_feed_xml(SAMPLE_HARPERS_XML, source2, "2026-10-12T10:00:00+00:00")
    )
    candidates = service.derive_candidate_trends(articles, min_articles=2)
    assert len(candidates) >= 1

    service.fetch_source = AsyncMock(return_value=articles)
    db = TestingSessionLocal()
    try:
        trends_before = db.query(Trend).count()
        signals_before = db.query(TrendSignal).count()
        result = await service.ingest_all()
        assert result["candidate_trends_count"] >= 1
        assert result["db_persistence"] == {
            "status": "not_attempted",
            "persisted_trends": 0,
            "persisted_signals": 0,
        }
        assert db.query(Trend).count() == trends_before
        assert db.query(TrendSignal).count() == signals_before
    finally:
        db.close()


def test_news_status_endpoint(client):
    res = client.get("/api/news/status")
    assert res.status_code == 200
    data = res.json()["data"]
    assert "sources" in data
    assert len(data["sources"]) == 4
    source_names = {s["name"] for s in data["sources"]}
    assert source_names == {"Vogue", "Harper's Bazaar", "Elle", "GQ"}
    assert "total_articles_cached" in data
    assert "cache_ttl_seconds" in data
    # Ensure no secrets leak
    raw_str = res.text
    assert "password" not in raw_str.lower()
    assert "secret" not in raw_str.lower()
    assert "token" not in raw_str.lower()


def test_candidate_trends_api_returns_attributable_editorial_candidates(client, monkeypatch):
    candidate = {
        "name": "Sculptural Tailoring",
        "slug": "sculptural-tailoring",
        "category": "Silhouettes",
        "publisher_count": 2,
        "attributing_articles": [
            {
                "publisher": "Vogue",
                "title": "Sculptural Tailoring Dominates Paris Haute Couture Week",
                "published_at": "2026-10-12T08:30:00+00:00",
                "canonical_url": "https://www.vogue.com/article/sculptural-tailoring-paris",
            },
            {
                "publisher": "Harper's Bazaar",
                "title": "How to Style Sculptural Tailoring",
                "published_at": "2026-10-11T22:00:00+00:00",
                "canonical_url": "https://www.harpersbazaar.com/fashion/trends/sculptural-tailoring-guide",
            },
        ],
        "data_status": "observed",
        "confidence": 85.0,
        "momentum": 58.0,
        "image_url": "https://example.com/not-an-editorial-image.jpg",
    }

    async def mock_get_candidate_trends(category=None):
        assert category is None
        return [candidate]

    monkeypatch.setattr(feed_ingestion_service, "get_candidate_trends", mock_get_candidate_trends)

    response = client.get("/api/news/candidate-trends")

    assert response.status_code == 200
    candidates = response.json()["data"]
    assert candidates == [
        {
            "record_type": "news_derived_candidate",
            "name": "Sculptural Tailoring",
            "slug": "sculptural-tailoring",
            "category": "Silhouettes",
            "publisher_count": 2,
            "articles": [
                {
                    "publisher": "Vogue",
                    "headline": "Sculptural Tailoring Dominates Paris Haute Couture Week",
                    "published_at": "2026-10-12T08:30:00+00:00",
                    "article_url": "https://www.vogue.com/article/sculptural-tailoring-paris",
                },
                {
                    "publisher": "Harper's Bazaar",
                    "headline": "How to Style Sculptural Tailoring",
                    "published_at": "2026-10-11T22:00:00+00:00",
                    "article_url": "https://www.harpersbazaar.com/fashion/trends/sculptural-tailoring-guide",
                },
            ],
        }
    ]
    assert "data_status" not in candidates[0]
    assert "confidence" not in candidates[0]
    assert "momentum" not in candidates[0]
    assert "image_url" not in candidates[0]


def test_candidate_trends_api_filters_by_category(client, monkeypatch):
    requested_categories = []

    async def mock_get_candidate_trends(category=None):
        requested_categories.append(category)
        candidate = {
            "name": "Sculptural Tailoring",
            "slug": "sculptural-tailoring",
            "category": "Silhouettes",
            "publisher_count": 2,
            "attributing_articles": [],
        }
        return [candidate] if category is None or candidate["category"].casefold() == category.casefold() else []

    monkeypatch.setattr(feed_ingestion_service, "get_candidate_trends", mock_get_candidate_trends)

    matching = client.get("/api/news/candidate-trends?category=sILHouettes")
    non_matching = client.get("/api/news/candidate-trends?category=Color")

    assert matching.status_code == 200
    assert [candidate["category"] for candidate in matching.json()["data"]] == ["Silhouettes"]
    assert non_matching.status_code == 200
    assert non_matching.json()["data"] == []
    assert requested_categories == ["sILHouettes", "Color"]


def test_candidate_trends_api_returns_empty_array(client, monkeypatch):
    async def mock_get_candidate_trends(category=None):
        return []

    monkeypatch.setattr(feed_ingestion_service, "get_candidate_trends", mock_get_candidate_trends)

    response = client.get("/api/news/candidate-trends")

    assert response.status_code == 200
    assert response.json()["data"] == []


def test_persisted_news_derived_trend_is_not_listed_as_market_observation(client):
    db = TestingSessionLocal()
    trend_slug = f"editorial-only-{uuid.uuid4().hex}"
    trend = Trend(
        id=str(uuid.uuid4()),
        slug=trend_slug,
        name="Editorial-only topic",
        category="Silhouettes",
        description="[news_derived] Publisher coverage only.",
        data_status="observed",
    )
    try:
        db.add(trend)
        db.commit()

        listed = client.get("/api/trends").json()["data"]
        detail = client.get(f"/api/trends/{trend_slug}").json()

        assert all(item["slug"] != trend_slug for item in listed)
        assert detail["success"] is False
    finally:
        db.delete(trend)
        db.commit()
        db.close()


def test_news_ingest_endpoint_rbac(client, ordinary_user_headers, privileged_user_headers, monkeypatch):
    async def mock_ingest_all():
        return {
            "fetched_at": "2026-10-12T10:00:00+00:00",
            "total_articles": 10,
            "candidate_trends_count": 2,
            "sources_queried": 4,
            "db_persistence": {
                "status": "not_attempted",
                "persisted_trends": 0,
                "persisted_signals": 0,
            },
        }

    monkeypatch.setattr(feed_ingestion_service, "ingest_all", mock_ingest_all)

    # 1. Anonymous request gets 401 Unauthorized
    res_anon = client.post("/api/news/ingest")
    assert res_anon.status_code == 401

    # 2. Ordinary user gets 403 Forbidden
    res_user = client.post("/api/news/ingest", headers=ordinary_user_headers)
    assert res_user.status_code == 403

    # 3. Privileged user gets 200 OK
    res_priv = client.post("/api/news/ingest", headers=privileged_user_headers)
    assert res_priv.status_code == 200
    data = res_priv.json()["data"]
    assert data["total_articles"] == 10
    assert data["candidate_trends_count"] == 2


def test_materials_theme_archetypes_and_candidate_filtering(client, monkeypatch):
    service = FeedIngestionService()
    articles = [
        {
            "id": "art-1",
            "title": "Raw Denim and Wide-Leg Jeans Define the Season",
            "summary": "Selvedge denim jackets and Japanese cotton twill jeans are everywhere.",
            "canonical_url": "https://www.vogue.com/article/raw-denim-jeans",
            "publisher": "Vogue",
            "published_at": "2026-10-12T10:00:00+00:00",
            "image_url": "https://assets.vogue.com/photos/denim.jpg",
            "keywords": ["denim", "jeans", "cotton twill", "selvedge"],
            "categories": ["Materials"],
        },
        {
            "id": "art-2",
            "title": "How to Wear Raw Denim Chambray Tailoring",
            "summary": "Indigo twill garments combine workwear with sharp cuts.",
            "canonical_url": "https://www.harpersbazaar.com/fashion/raw-denim-guide",
            "publisher": "Harper's Bazaar",
            "published_at": "2026-10-12T11:00:00+00:00",
            "image_url": "https://assets.harpersbazaar.com/photos/chambray.jpg",
            "keywords": ["denim", "chambray", "indigo"],
            "categories": ["Materials"],
        },
    ]

    candidates = service.derive_candidate_trends(articles, min_articles=2)
    assert len(candidates) >= 1
    material_candidate = next((c for c in candidates if c["category"] == "Materials"), None)
    assert material_candidate is not None
    assert "Denim" in material_candidate["name"]
    assert material_candidate["publisher_count"] == 2
    assert material_candidate["article_count"] == 2

    # Verify endpoint filtering for Materials
    async def mock_get_candidate_trends(category=None):
        if category and category.casefold() == "materials":
            return [material_candidate]
        return []

    monkeypatch.setattr(feed_ingestion_service, "get_candidate_trends", mock_get_candidate_trends)
    res = client.get("/api/news/candidate-trends?category=Materials")
    assert res.status_code == 200
    data = res.json()["data"]
    assert len(data) == 1
    assert data[0]["category"] == "Materials"
    assert data[0]["articles"][0]["image_url"] == "https://assets.vogue.com/photos/denim.jpg"


def test_architectural_footwear_excludes_baggy_and_eyebag_surgery():
    archetype = next(a for a in THEME_ARCHETYPES if a["name"] == "Architectural Footwear & Statement Bags")
    keywords = archetype["keywords"]
    negative_patterns = archetype.get("negative_patterns", [])

    # 1. "baggy" in corpus must NOT match "bag"
    baggy_corpus = "baggy jeans and oversized denim jackets are dominating street style"
    assert not article_matches_archetype(baggy_corpus, keywords, negative_patterns)

    # 2. "eye-bag surgery" in corpus must be rejected by negative patterns
    eyebag_corpus = "why eye-bag surgery and blepharoplasty procedures surged this year"
    assert not article_matches_archetype(eyebag_corpus, keywords, negative_patterns)

    # 3. Genuine statement bag or footwear article MUST match
    real_bag_corpus = "the sculptural statement bag and leather loafers redefining autumn accessories"
    assert article_matches_archetype(real_bag_corpus, keywords, negative_patterns)

    # 4. Derivation test with feed service
    service = FeedIngestionService()
    test_articles = [
        {
            "id": "1",
            "title": "Why Baggy Pants Are Everywhere",
            "summary": "From loose fits to baggy silhouettes.",
            "canonical_url": "https://vogue.com/baggy-pants",
            "publisher": "Vogue",
            "keywords": ["baggy", "denim"],
        },
        {
            "id": "2",
            "title": "Everything to Know About Under-Eye Bag Surgery",
            "summary": "Cosmetic surgeons report high demand for lower blepharoplasty.",
            "canonical_url": "https://harpersbazaar.com/eyebag-surgery",
            "publisher": "Harper's Bazaar",
            "keywords": ["surgery", "blepharoplasty"],
        },
        {
            "id": "3",
            "title": "The 10 Best Statement Bags of the Season",
            "summary": "Architectural totes and sculptural shoulder bags to invest in.",
            "canonical_url": "https://vogue.com/statement-bags",
            "publisher": "Vogue",
            "keywords": ["statement bag", "accessories"],
        },
        {
            "id": "4",
            "title": "Sculptural Boots and Loafers for Autumn",
            "summary": "Handcrafted leather footwear and high heels taking over Paris.",
            "canonical_url": "https://harpersbazaar.com/sculptural-boots",
            "publisher": "Harper's Bazaar",
            "keywords": ["boots", "loafers", "heels"],
        },
    ]

    candidates = service.derive_candidate_trends(test_articles, min_articles=2)
    acc_candidate = next((c for c in candidates if c["name"] == "Architectural Footwear & Statement Bags"), None)
    assert acc_candidate is not None
    # Must only contain article 3 and 4, NOT article 1 or 2
    matched_urls = [a["canonical_url"] for a in acc_candidate["attributing_articles"]]
    assert "https://vogue.com/statement-bags" in matched_urls
    assert "https://harpersbazaar.com/sculptural-boots" in matched_urls
    assert "https://vogue.com/baggy-pants" not in matched_urls
    assert "https://harpersbazaar.com/eyebag-surgery" not in matched_urls


