from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.schemas.common import ApiResponse
from app.utils.rate_limit import rate_limit_dependency
from app.services.video_provider import (
    VIDEO_TOPICS,
    VideoProviderError,
    youtube_video_provider,
)

router = APIRouter(prefix="/videos", tags=["videos"])


@router.get("/status", response_model=ApiResponse[Dict[str, Any]])
def get_video_provider_status():
    return ApiResponse.ok(youtube_video_provider.status())


@router.get(
    "/search",
    response_model=ApiResponse[Dict[str, Any]],
    dependencies=[Depends(rate_limit_dependency(max_requests=20, window_seconds=60, scope="video_search"))],
)
async def search_fashion_videos(
    query: str = Query("fashion runway designer collection", min_length=2, max_length=200),
    topic: Optional[str] = Query(None, description="Curated fashion topic"),
    published_after: Optional[datetime] = Query(None),
    order: str = Query("relevance", pattern="^(date|relevance|viewCount|rating|title|videoCount)$"),
    region_code: Optional[str] = Query(None, pattern="^[A-Za-z]{2}$"),
    duration: str = Query("any", pattern="^(any|short|medium|long)$"),
    limit: int = Query(12, ge=1, le=50),
):
    normalized_topic = topic.strip().lower() if topic else None
    if normalized_topic and normalized_topic not in VIDEO_TOPICS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported topic. Choose one of: {', '.join(VIDEO_TOPICS)}.",
        )
    search_query = query.strip()
    if normalized_topic:
        search_query = f"{search_query} {VIDEO_TOPICS[normalized_topic]}"

    try:
        videos = await youtube_video_provider.search(
            query=search_query,
            published_after=published_after,
            order=order,
            region_code=region_code,
            duration=duration,
            limit=limit,
        )
    except VideoProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc

    provider_status = youtube_video_provider.status()
    return ApiResponse.ok({
        "items": videos,
        "provider": provider_status["provider"],
        "fetched_at": provider_status["last_successful_fetch"],
        "cached_for_seconds": 300,
    })
