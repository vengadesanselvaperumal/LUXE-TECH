import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Protocol, Tuple

import httpx

from app.config import get_settings

YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
VIDEO_CACHE_TTL_SECONDS = 300
VIDEO_TOPICS = {
    "runway": "fashion runway collection",
    "street style": "fashion street style",
    "colour": "fashion colour trends",
    "silhouette": "fashion silhouettes",
    "knitwear": "fashion knitwear",
    "indian ethnic wear": "Indian ethnic wear fashion",
    "kurti": "kurti fashion collection",
    "designer collections": "fashion designer collection",
}


class VideoProviderError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


class FashionVideoProvider(Protocol):
    @property
    def configured(self) -> bool: ...

    async def search(
        self,
        query: str,
        published_after: Optional[datetime] = None,
        order: str = "relevance",
        region_code: Optional[str] = None,
        duration: str = "any",
        limit: int = 12,
    ) -> List[Dict[str, Any]]: ...


@dataclass
class CachedVideoSearch:
    expires_at: float
    videos: List[Dict[str, Any]]


class YouTubeDataApiProvider:
    def __init__(self):
        self.api_key = get_settings().YOUTUBE_API_KEY.strip()
        self.last_successful_fetch: Optional[str] = None
        self.last_error: Optional[str] = None
        self._cache: Dict[Tuple[Any, ...], CachedVideoSearch] = {}

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    async def search(
        self,
        query: str,
        published_after: Optional[datetime] = None,
        order: str = "relevance",
        region_code: Optional[str] = None,
        duration: str = "any",
        limit: int = 12,
    ) -> List[Dict[str, Any]]:
        if not self.configured:
            raise VideoProviderError("credentials_missing", "Video discovery is unavailable because YOUTUBE_API_KEY is not configured.")

        cache_key = (
            query.casefold(),
            published_after.isoformat() if published_after else None,
            order,
            region_code.upper() if region_code else None,
            duration,
            limit,
        )
        cached = self._cache.get(cache_key)
        if cached and cached.expires_at > time.monotonic():
            return [video.copy() for video in cached.videos]

        params: Dict[str, Any] = {
            "part": "snippet",
            "type": "video",
            "q": query,
            "maxResults": limit,
            "order": order,
            "safeSearch": "moderate",
            "videoDuration": duration,
            "key": self.api_key,
        }
        if published_after:
            timestamp = published_after
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=timezone.utc)
            params["publishedAfter"] = timestamp.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        if region_code:
            params["regionCode"] = region_code.upper()

        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(8.0, connect=3.0)) as client:
                response = await client.get(YOUTUBE_SEARCH_URL, params=params)
        except httpx.TimeoutException as exc:
            self.last_error = "timeout"
            raise VideoProviderError("provider_timeout", "Video provider timed out. Try again shortly.") from exc
        except httpx.HTTPError as exc:
            self.last_error = "network_error"
            raise VideoProviderError("provider_unavailable", "Video provider could not be reached.") from exc

        if response.status_code in (403, 429):
            self.last_error = "quota_or_permission"
            raise VideoProviderError("quota_or_permission", "Video provider rejected the request due to quota or API permissions.")
        if response.status_code != 200:
            self.last_error = "provider_error"
            raise VideoProviderError("provider_unavailable", "Video provider returned an error.")

        try:
            payload = response.json()
            rows = payload.get("items", [])
            if not isinstance(rows, list):
                raise ValueError("items is not a list")
        except (ValueError, AttributeError) as exc:
            self.last_error = "invalid_response"
            raise VideoProviderError("invalid_provider_response", "Video provider returned an invalid response.") from exc

        videos = []
        for row in rows:
            snippet = row.get("snippet") if isinstance(row, dict) else None
            video_id = (row.get("id") or {}).get("videoId") if isinstance(row, dict) else None
            if not isinstance(snippet, dict) or not isinstance(video_id, str) or not video_id:
                continue
            thumbnails = snippet.get("thumbnails") or {}
            thumbnail_url = next(
                (
                    thumbnails[key].get("url")
                    for key in ("maxres", "high", "medium", "default")
                    if isinstance(thumbnails.get(key), dict)
                    and isinstance(thumbnails[key].get("url"), str)
                    and thumbnails[key]["url"].startswith("https://")
                ),
                None,
            )
            videos.append({
                "title": str(snippet.get("title") or ""),
                "creator": str(snippet.get("channelTitle") or ""),
                "thumbnail_url": thumbnail_url,
                "published_at": snippet.get("publishedAt"),
                "canonical_url": f"https://www.youtube.com/watch?v={video_id}",
                "video_id": video_id,
                "source": "YouTube Data API",
            })

        fetched_at = datetime.now(timezone.utc).isoformat()
        self.last_successful_fetch = fetched_at
        self.last_error = None
        self._cache[cache_key] = CachedVideoSearch(
            expires_at=time.monotonic() + VIDEO_CACHE_TTL_SECONDS,
            videos=videos,
        )
        return [video.copy() for video in videos]

    def status(self) -> Dict[str, Any]:
        return {
            "provider": "youtube_data_api",
            "available": self.configured,
            "state": "ready" if self.configured else "unavailable",
            "last_successful_fetch": self.last_successful_fetch,
            "last_error": self.last_error,
            "capabilities": {
                "search": self.configured,
                "official_embed": True,
                "public_video_metadata": True,
            },
            "limitations": [
                "A recent publication date does not establish that a video is viral or trending."
            ],
        }


youtube_video_provider = YouTubeDataApiProvider()
