import asyncio
import logging
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import httpx

logger = logging.getLogger("luxe_tech.fashion_news")

VOGUE_FEED_URL = "https://www.vogue.com/feed/rss"
_RSS_NS = {"media": "http://search.yahoo.com/mrss/"}


class FashionNewsUnavailable(Exception):
    pass


class FashionNewsService:
    CACHE_TTL_SECONDS = 300

    def __init__(self) -> None:
        self._items: List[Dict[str, Any]] = []
        self._fetched_at: Optional[str] = None
        self._cached_at = 0.0
        self._lock = asyncio.Lock()

    @staticmethod
    def _parse_feed(content: bytes, fetched_at: str) -> List[Dict[str, Any]]:
        try:
            root = ET.fromstring(content)
        except ET.ParseError as exc:
            raise FashionNewsUnavailable("Publisher feed returned invalid RSS.") from exc

        channel = root.find("channel")
        if channel is None:
            raise FashionNewsUnavailable("Publisher feed did not contain an RSS channel.")

        items: List[Dict[str, Any]] = []
        for item in channel.findall("item"):
            title = (item.findtext("title") or "").strip()
            url = (item.findtext("link") or "").strip()
            parsed_url = urlparse(url)
            if not title or parsed_url.scheme != "https" or not parsed_url.netloc:
                continue

            published_at = None
            published_text = item.findtext("pubDate")
            if published_text:
                try:
                    published = parsedate_to_datetime(published_text)
                    if published.tzinfo is None:
                        published = published.replace(tzinfo=timezone.utc)
                    published_at = published.astimezone(timezone.utc).isoformat()
                except (TypeError, ValueError, OverflowError):
                    published_at = None

            thumbnail = item.find("media:thumbnail", _RSS_NS)
            image_url = thumbnail.get("url") if thumbnail is not None else None
            items.append({
                "title": title,
                "summary": (item.findtext("description") or "").strip(),
                "url": url,
                "image_url": image_url,
                "source_name": "Vogue",
                "source_url": VOGUE_FEED_URL,
                "observed_at": published_at,
                "fetched_at": fetched_at,
                "quality": "publisher_rss",
                "data_status": "observed",
            })
            if len(items) == 20:
                break

        if not items:
            raise FashionNewsUnavailable("Publisher feed contained no usable articles.")
        return items

    async def get_current_news(self) -> Dict[str, Any]:
        if self._items and time.monotonic() - self._cached_at < self.CACHE_TTL_SECONDS:
            return self._response(stale=False)

        async with self._lock:
            if self._items and time.monotonic() - self._cached_at < self.CACHE_TTL_SECONDS:
                return self._response(stale=False)

            try:
                async with httpx.AsyncClient(
                    timeout=httpx.Timeout(8.0, connect=3.0),
                    follow_redirects=True,
                    headers={"User-Agent": "LUXE.TECH Fashion News Reader/1.0"},
                ) as client:
                    response = await client.get(VOGUE_FEED_URL)
                    response.raise_for_status()
                fetched_at = datetime.now(timezone.utc).isoformat()
                items = self._parse_feed(response.content, fetched_at)
            except (httpx.HTTPError, FashionNewsUnavailable) as exc:
                if self._items:
                    logger.warning("Publisher news refresh failed (%s); returning cached feed as stale.", type(exc).__name__)
                    return self._response(stale=True)
                logger.warning("Publisher news feed unavailable (%s).", type(exc).__name__)
                raise FashionNewsUnavailable("Fashion news provider is temporarily unavailable.") from exc

            self._items = items
            self._fetched_at = fetched_at
            self._cached_at = time.monotonic()
            return self._response(stale=False)

    def _response(self, stale: bool) -> Dict[str, Any]:
        return {
            "items": self._items,
            "source_name": "Vogue",
            "source_url": VOGUE_FEED_URL,
            "fetched_at": self._fetched_at,
            "data_status": "stale" if stale else "observed",
            "stale": stale,
        }


fashion_news_service = FashionNewsService()
