from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.schemas.common import ApiResponse
from app.services.fashion_news_service import FashionNewsUnavailable, fashion_news_service
from app.services.feed_ingestion_service import feed_ingestion_service
from app.utils.security import get_privileged_user

router = APIRouter(prefix="/news", tags=["news"])


@router.get("/current", response_model=ApiResponse[Dict[str, Any]])
async def get_current_fashion_news():
    """Returns real, timestamped Vogue fashion news articles with publisher provenance."""
    try:
        return ApiResponse.ok(await fashion_news_service.get_current_news())
    except FashionNewsUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/status", response_model=ApiResponse[Dict[str, Any]])
async def get_news_ingestion_status():
    """
    Returns the real-time health, article counts, and freshness of all
    configured fashion RSS feeds without leaking secrets or credentials.
    """
    status_data = await feed_ingestion_service.get_status()
    return ApiResponse.ok(status_data)


@router.get("/articles", response_model=ApiResponse[List[Dict[str, Any]]])
async def get_normalized_articles(
    category: Optional[str] = Query(None, description="Filter by fashion category"),
    publisher: Optional[str] = Query(None, description="Filter by publisher (e.g., Vogue, Elle)"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of articles to return"),
):
    """
    Returns normalized, deduplicated articles from verified fashion publishers.
    All articles include canonical URLs, publication timestamps, and category tags.
    """
    articles = await feed_ingestion_service.get_articles(
        category=category,
        publisher=publisher,
        limit=limit,
    )
    return ApiResponse.ok(articles)


@router.get("/candidate-trends", response_model=ApiResponse[List[Dict[str, Any]]])
async def get_candidate_trends(
    category: Optional[str] = Query(None, description="Filter by trend category"),
):
    """
    Returns candidate trend topics clustered from multiple attributable publisher articles.
    These are in-memory editorial candidates, not persisted trend observations.
    """
    topics = await feed_ingestion_service.get_candidate_trends(category=category)
    return ApiResponse.ok([
        {
            "record_type": "news_derived_candidate",
            "name": topic["name"],
            "slug": topic["slug"],
            "category": topic["category"],
            "publisher_count": topic["publisher_count"],
            "articles": [
                {
                    "publisher": article["publisher"],
                    "headline": article["title"],
                    "published_at": article.get("published_at"),
                    "article_url": article["canonical_url"],
                    **({"image_url": article["image_url"]} if article.get("image_url") else {}),
                }
                for article in topic["attributing_articles"]
            ],
        }
        for topic in topics
    ])


@router.post("/ingest", response_model=ApiResponse[Dict[str, Any]])
async def trigger_news_ingestion(
    persist: bool = Query(False, description="Persist candidate trends and signals to database"),
    _user: Dict[str, Any] = Depends(get_privileged_user),
):
    """
    Triggers a live RSS refresh and derives in-memory editorial candidates.
    Editorial coverage is optionally persisted with persist=true.
    Requires privileged user permissions (admin / lead_analyst).
    """
    result = await feed_ingestion_service.ingest_all()
    if persist and hasattr(feed_ingestion_service, "persist_candidates_to_db"):
        db_res = feed_ingestion_service.persist_candidates_to_db(feed_ingestion_service._candidate_trends)
        result["db_persistence"] = db_res
    return ApiResponse.ok(result)
