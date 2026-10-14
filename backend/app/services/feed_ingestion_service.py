import asyncio
import html
import json
import logging
import re
import time
import uuid
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import httpx
from app.utils.validation import slugify

logger = logging.getLogger("luxe_tech.feed_ingestion")

_BLOCK_TAG_RE = re.compile(r"<\s*/?\s*(?:p|div|br|hr|h[1-6]|li|tr|blockquote)[^>]*>", re.IGNORECASE)
_ANY_TAG_RE = re.compile(r"<[^>]+>")
_XML_MEDIA_NS = {"media": "http://search.yahoo.com/mrss/"}


def clean_html_text(raw_text: Optional[str], max_len: int = 500) -> str:
    """Safely strip HTML tags, unescape HTML entities, and collapse whitespace."""
    if not raw_text or not isinstance(raw_text, str):
        return ""
    unescaped = html.unescape(raw_text)
    # Replace block-level tags with space so words don't merge
    with_block_spaces = _BLOCK_TAG_RE.sub(" ", unescaped)
    # Strip remaining inline tags without adding whitespace before punctuation
    stripped = _ANY_TAG_RE.sub("", with_block_spaces)
    cleaned = " ".join(stripped.split())
    if len(cleaned) > max_len:
        return cleaned[:max_len].rsplit(" ", 1)[0] + "..."
    return cleaned


def canonicalize_url(raw_url: Optional[str]) -> Optional[str]:
    """
    Validate that the URL is an absolute HTTPS URL and strip tracking parameters
    (e.g., utm_*, fbclid, ref) to produce a canonical representation for deduplication.
    """
    if not raw_url or not isinstance(raw_url, str):
        return None
    raw_url = raw_url.strip()
    try:
        parsed = urlparse(raw_url)
    except Exception:
        return None

    if parsed.scheme != "https" or not parsed.netloc:
        return None

    # Strip marketing/tracking query parameters
    filtered_params = [
        (k, v)
        for k, v in parse_qsl(parsed.query)
        if not (k.startswith("utm_") or k in {"fbclid", "gclid", "ref", "source", "recirc"})
    ]

    path = parsed.path.rstrip("/")
    if not path:
        path = "/"

    cleaned = parsed._replace(
        netloc=parsed.netloc.lower(),
        path=path,
        query=urlencode(filtered_params),
        fragment="",
    )
    return urlunparse(cleaned)


def parse_rfc822_or_iso_date(date_str: Optional[str]) -> Optional[str]:
    """Parse pubDate in RFC 2822 or ISO 8601 into a UTC ISO 8601 string."""
    if not date_str or not isinstance(date_str, str):
        return None
    date_str = date_str.strip()

    # Try RFC 2822 first
    try:
        dt = parsedate_to_datetime(date_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat()
    except (TypeError, ValueError, OverflowError):
        pass

    # Try ISO 8601
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat()
    except (TypeError, ValueError):
        pass

    return None


def article_matches_archetype(
    corpus: str,
    keywords: List[str],
    negative_patterns: Optional[List[str]] = None,
) -> bool:
    """
    Match an article text corpus against archetype keywords using word boundaries,
    preventing naive substring false-positives (e.g. 'baggy' or 'eye-bag surgery' matching 'bag').
    """
    if not corpus or not keywords:
        return False

    # Check negative exclusions first
    if negative_patterns:
        for neg in negative_patterns:
            neg_clean = neg.lower().strip()
            if not neg_clean:
                continue
            # Match negative pattern across hyphens or spaces with word boundaries
            neg_regex = r"\b" + re.escape(neg_clean).replace(r"\-", r"[\s\-]") + r"\b"
            if re.search(neg_regex, corpus, re.IGNORECASE):
                return False

    # Check keyword matches with word boundaries and optional plural/inflection suffix
    for kw in keywords:
        kw_clean = kw.lower().strip()
        if not kw_clean:
            continue
        # Anchor on word boundaries so e.g. \bbag(?:s|es)?\b matches 'bag'/'bags' but rejects 'baggy'
        pattern = r"\b" + re.escape(kw_clean) + r"(?:s|es)?\b"
        if re.search(pattern, corpus, re.IGNORECASE):
            return True

    return False



@dataclass
class FeedSourceConfig:
    name: str
    feed_url: str
    publisher: str
    homepage: str
    default_categories: List[str] = field(default_factory=list)
    enabled: bool = True
    timeout_seconds: float = 8.0
    connect_timeout_seconds: float = 3.0


@dataclass
class FeedStatus:
    name: str
    feed_url: str
    publisher: str
    status: str  # healthy, degraded, failing, idle
    last_fetched_at: Optional[str] = None
    article_count: int = 0
    freshness_seconds: Optional[int] = None
    error: Optional[str] = None
    response_time_ms: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# Verified fashion RSS feeds tested for accessibility, standard RSS 2.0 structure, and non-violating terms.
VERIFIED_FEEDS: List[FeedSourceConfig] = [
    FeedSourceConfig(
        name="Vogue",
        feed_url="https://www.vogue.com/feed/rss",
        publisher="Vogue",
        homepage="https://www.vogue.com",
        default_categories=["Couture", "Womenswear", "Materials", "Color"],
    ),
    FeedSourceConfig(
        name="Harper's Bazaar",
        feed_url="https://www.harpersbazaar.com/rss/all.xml",
        publisher="Harper's Bazaar",
        homepage="https://www.harpersbazaar.com",
        default_categories=["Womenswear", "Accessories", "Color"],
    ),
    FeedSourceConfig(
        name="Elle",
        feed_url="https://www.elle.com/rss/all.xml",
        publisher="Elle",
        homepage="https://www.elle.com",
        default_categories=["Womenswear", "Streetwear", "Culture"],
    ),
    FeedSourceConfig(
        name="GQ",
        feed_url="https://www.gq.com/feed/rss",
        publisher="GQ",
        homepage="https://www.gq.com",
        default_categories=["Menswear", "Streetwear", "Silhouettes"],
    ),
]


CATEGORY_KEYWORD_MAP: Dict[str, List[str]] = {
    "Color": [
        "color", "colour", "palette", "hue", "monochrome", "neon", "pastel",
        "burgundy", "crimson", "khaki", "indigo", "olive", "yellow", "brown",
        "cherry red", "metallic", "silver", "gold", "oxblood", "wine",
    ],
    "Materials": [
        "leather", "silk", "denim", "wool", "cashmere", "linen", "organza",
        "satin", "tweed", "velvet", "sheer", "cotton", "mesh", "suede", "lace",
        "knit", "knitwear", "chiffon", "nylon", "boucle", "alpaca",
    ],
    "Silhouettes": [
        "tailoring", "oversized", "draped", "blazer", "trench", "wide-leg",
        "maxi", "mini", "corset", "sculptural", "drop-waist", "asymmetric",
        "cinched", "boxy", "cape", "coat", "jacket", "trousers", "suiting",
    ],
    "Patterns": [
        "stripes", "striped", "polka dots", "checks", "checked", "tartan",
        "plaid", "geometric", "houndstooth", "argyle",
    ],
    "Prints": [
        "floral", "animal print", "leopard", "zebra", "graphic", "tie-dye",
        "abstract print", "botanical",
    ],
    "Textures": [
        "ribbed", "quilted", "pleated", "embossed", "fringed", "ruffles",
        "frayed", "distressed", "crochet", "patent", "shearling",
    ],
    "Accessories": [
        "handbag", "bag", "shoes", "boots", "loafers", "jewelry", "belt",
        "eyewear", "sunglasses", "scarf", "hat", "tote", "heels", "sneakers",
    ],
    "Womenswear": [
        "womenswear", "gown", "dress", "skirt", "feminine", "lingerie", "blouse",
    ],
    "Menswear": [
        "menswear", "suit", "tie", "loafers", "tuxedo", "shirting", "masculine", "men's",
    ],
    "Streetwear": [
        "sneakers", "hoodie", "cargo", "streetwear", "utility", "workwear", "bomber",
    ],
    "Couture": [
        "couture", "atelier", "haute", "craftsmanship", "runway", "handcrafted",
        "artisanal", "fashion week", "dark romance",
    ],
    "Retail": [
        "retail", "store", "shopping", "ecommerce", "luxury market", "pricing",
        "flagship", "sales", "boutique", "earnings",
    ],
}


THEME_ARCHETYPES = [
    {
        "name": "Sculptural Tailoring & Suiting",
        "category": "Silhouettes",
        "keywords": ["tailoring", "blazer", "sculptural", "oversized", "suiting", "trousers"],
        "colors": ["Black", "Charcoal", "Bone"],
        "materials": ["Wool Twill", "Cashmere Blend", "Fine Gabardine"],
        "textures": ["Structured", "Pressed", "Crisp"],
        "silhouettes": ["Oversized Shoulder", "Boxy Fit", "Wide-Leg Trouser"],
        "patterns": ["Solid", "Pinstripe"],
    },
    {
        "name": "Sheer & Translucent Layering",
        "category": "Materials",
        "keywords": ["sheer", "organza", "chiffon", "mesh", "translucent", "gauze"],
        "colors": ["Smoky Quartz", "Nude", "Onyx"],
        "materials": ["Silk Organza", "Chiffon", "Technical Mesh"],
        "textures": ["Gauzy", "Delicate", "Layered"],
        "silhouettes": ["Fluid Drape", "Tiered Slip"],
        "patterns": ["Monochrome"],
    },
    {
        "name": "Butter Yellow & Warm Pastels",
        "category": "Color",
        "keywords": ["butter yellow", "yellow", "pastel", "pale yellow", "lemon", "vanilla"],
        "colors": ["Butter Yellow (#FFF3B0)", "Vanilla Cream (#F7F4EA)", "Muted Ochre (#D4A373)"],
        "materials": ["Cotton Poplin", "Fine Gauge Knit", "Silk Sateen"],
        "textures": ["Matte", "Soft Touch"],
        "silhouettes": ["Soft Suiting", "Slip Dress"],
        "patterns": ["Solid Colorblock"],
    },
    {
        "name": "Deep Burgundy & Oxblood Accents",
        "category": "Color",
        "keywords": ["burgundy", "wine", "oxblood", "crimson", "cherry red", "bordeaux"],
        "colors": ["Deep Burgundy (#58111A)", "Oxblood (#4A0E17)", "Cherry Black (#2B0C10)"],
        "materials": ["Buffed Leather", "Wool Flannel", "Satin"],
        "textures": ["Patent", "Brushed", "Gloss"],
        "silhouettes": ["Trench", "Pencil Skirt", "Structured Tote"],
        "patterns": ["Deep Solid"],
    },
    {
        "name": "Tactile Suede & Heritage Leather",
        "category": "Textures",
        "keywords": ["suede", "leather", "tactile", "shearling", "fringe", "embossed"],
        "colors": ["Tobacco Brown", "Caramel", "Cognac"],
        "materials": ["Brushed Suede", "Calfskin", "Shearling"],
        "textures": ["Velvety", "Brushed", "Heavy Grain"],
        "silhouettes": ["Oversized Jacket", "Riding Boot", "Slouchy Tote"],
        "patterns": ["Tonal"],
    },
    {
        "name": "Artisanal Knitwear & Open Weave",
        "category": "Materials",
        "keywords": ["knitwear", "crochet", "knit", "ribbed", "wool", "cashmere", "open weave", "alpaca"],
        "colors": ["Ecru", "Heather Grey", "Sage"],
        "materials": ["Chunky Wool", "Boucle", "Alpaca"],
        "textures": ["Ribbed", "Open Gauge", "Chunky Woven"],
        "silhouettes": ["Slouchy Cardigan", "Column Knit Dress"],
        "patterns": ["Cable", "Ribbed Repeat"],
    },
    {
        "name": "Raw Denim & Chambray Structures",
        "category": "Materials",
        "keywords": ["denim", "chambray", "jeans", "indigo", "cotton twill", "selvedge"],
        "colors": ["Indigo", "Washed Blue", "Raw Ecru"],
        "materials": ["Japanese Selvedge Denim", "Rigid Cotton", "Chambray"],
        "textures": ["Stiff", "Twill Weave", "Unwashed"],
        "silhouettes": ["Wide-Leg Trouser", "Oversized Trucker", "Column Skirt"],
        "patterns": ["Indigo Warp"],
    },
    {
        "name": "Supple Leather & Polished Skins",
        "category": "Materials",
        "keywords": ["leather", "calfskin", "patent", "nappa", "suede", "lambskin"],
        "colors": ["Cognac", "Black Gloss", "Espresso"],
        "materials": ["Nappa Leather", "Buffed Suede", "Patent Leather"],
        "textures": ["Polished", "Supple", "High Shine"],
        "silhouettes": ["Structured Trench", "Midi Skirt", "Straight Trouser"],
        "patterns": ["Solid Glaze"],
    },
    {
        "name": "Liquid Silk & Satin Fluidity",
        "category": "Materials",
        "keywords": ["silk", "satin", "charmeuse", "draped silk", "chiffon", "viscose"],
        "colors": ["Champagne", "Pearl", "Midnight Blue"],
        "materials": ["Heavy Silk Satin", "Silk Crepe", "Liquid Charmeuse"],
        "textures": ["Gloss", "Fluid", "Slippery"],
        "silhouettes": ["Bias-Cut Slip Dress", "Draped Halter", "Liquid Trouser"],
        "patterns": ["Reflective Sheen"],
    },
    {
        "name": "Brushed Wool & Cashmere Tailoring",
        "category": "Materials",
        "keywords": ["wool", "cashmere", "flannel", "gabardine", "tweed", "alpaca"],
        "colors": ["Heather Grey", "Camel", "Charcoal Melange"],
        "materials": ["Virgin Wool", "Double-Faced Cashmere", "Wool Flannel"],
        "textures": ["Brushed", "Dense", "Felted"],
        "silhouettes": ["Overcoat", "Tailored Trouser", "Wrap Coat"],
        "patterns": ["Melange", "Herringbone"],
    },
    {
        "name": "Utility Workwear & Structured Outerwear",
        "category": "Silhouettes",
        "keywords": ["utility", "workwear", "cargo", "trench", "outerwear", "bomber", "jacket"],
        "colors": ["Olive Drab", "Field Tan", "Navy"],
        "materials": ["Cotton Canvas", "Ripstop", "Weatherproof Gabardine"],
        "textures": ["Rugged", "Matte Waxed"],
        "silhouettes": ["Cargo Trousers", "Cropped Utility Jacket"],
        "patterns": ["Minimalist Utilitarian"],
    },
    {
        "name": "Dark Romance & Gothic Elegance",
        "category": "Couture",
        "keywords": ["dark romance", "lace", "corset", "draped", "velvet", "gothic", "victorian"],
        "colors": ["Midnight", "Blood Red", "Antiqued Gold"],
        "materials": ["Chantilly Lace", "Silk Velvet", "Tulle"],
        "textures": ["Ruffled", "Brocade", "Layered Sheer"],
        "silhouettes": ["Hourglass Corset", "Sweeping Hemline"],
        "patterns": ["Flocked Floral", "Victorian Scroll"],
    },
    {
        "name": "Architectural Footwear & Statement Bags",
        "category": "Accessories",
        "keywords": ["shoes", "boots", "loafers", "bag", "handbag", "handbags", "tote", "heels", "sneakers", "statement bag", "it bag"],
        "negative_patterns": [
            "eye bag", "eye-bag", "eyebag", "blepharoplasty", "under-eye", "under eye",
            "bags under eyes", "bag under eyes", "tea bag", "sleeping bag", "punching bag",
            "colostomy bag", "body bag"
        ],
        "colors": ["Ebony", "Chestnut", "Metallic Silver"],
        "materials": ["Box Calfskin", "Polished Hardware", "Spazzolato Leather"],
        "textures": ["Mirror Polish", "Embossed", "Matte Grain"],
        "silhouettes": ["Sculptural Heel", "Angular Shoulder Bag"],
        "patterns": ["Minimalist Geometry"],
    },
]


class FeedIngestionService:
    CACHE_TTL_SECONDS = 300  # 5 minutes bounded caching

    def __init__(self, sources: Optional[List[FeedSourceConfig]] = None):
        self._sources = sources or VERIFIED_FEEDS
        self._articles: List[Dict[str, Any]] = []
        self._status_by_source: Dict[str, FeedStatus] = {
            src.name: FeedStatus(
                name=src.name,
                feed_url=src.feed_url,
                publisher=src.publisher,
                status="idle",
            )
            for src in self._sources
        }
        self._last_ingested_at: Optional[str] = None
        self._cached_at: float = 0.0
        self._candidate_trends: List[Dict[str, Any]] = []
        self._lock = asyncio.Lock()

    def parse_feed_xml(
        self,
        content: bytes,
        source: FeedSourceConfig,
        fetched_at: str,
    ) -> List[Dict[str, Any]]:
        """
        Parse RSS XML content into normalized article records.
        Preserves provenance: source_name, source_url, canonical_url, observed_at, fetched_at.
        """
        try:
            root = ET.fromstring(content)
        except ET.ParseError as exc:
            logger.warning("Feed %s returned malformed XML: %s", source.name, exc)
            return []

        channel = root.find("channel")
        if channel is None:
            logger.warning("Feed %s XML has no <channel> element", source.name)
            return []

        articles: List[Dict[str, Any]] = []
        for item in channel.findall("item"):
            raw_title = item.findtext("title")
            raw_link = item.findtext("link")
            title = clean_html_text(raw_title, max_len=200)
            canonical_url = canonicalize_url(raw_link)

            if not title or not canonical_url:
                continue

            raw_desc = item.findtext("description")
            summary = clean_html_text(raw_desc, max_len=400)

            pub_date_raw = item.findtext("pubDate")
            published_at = parse_rfc822_or_iso_date(pub_date_raw)

            # Thumbnail / Image extraction
            image_url = None
            thumbnail = item.find("media:thumbnail", _XML_MEDIA_NS)
            if thumbnail is not None:
                img = thumbnail.get("url")
                if img and img.startswith("https://"):
                    image_url = img

            if not image_url:
                media_content = item.find("media:content", _XML_MEDIA_NS)
                if media_content is not None:
                    img = media_content.get("url")
                    if img and img.startswith("https://"):
                        image_url = img

            if not image_url:
                enclosure = item.find("enclosure")
                if enclosure is not None and "image" in enclosure.get("type", ""):
                    img = enclosure.get("url")
                    if img and img.startswith("https://"):
                        image_url = img

            # Feed category tags
            raw_categories = [
                clean_html_text(c.text, max_len=60)
                for c in item.findall("category")
                if c.text
            ]

            # Categorize article based on title, description, and raw categories
            matched_categories, matched_keywords = self._classify_article(
                title=title,
                summary=summary,
                raw_categories=raw_categories,
                default_categories=source.default_categories,
            )

            article = {
                "id": str(uuid.uuid4()),
                "title": title,
                "summary": summary,
                "canonical_url": canonical_url,
                "url": canonical_url,
                "image_url": image_url,
                "publisher": source.publisher,
                "source_name": source.publisher,
                "source_url": source.feed_url,
                "published_at": published_at,
                "observed_at": published_at,
                "fetched_at": fetched_at,
                "categories": matched_categories,
                "keywords": matched_keywords,
                "quality": "publisher_rss",
                "data_status": "observed",
            }
            articles.append(article)

        return articles

    def _classify_article(
        self,
        title: str,
        summary: str,
        raw_categories: List[str],
        default_categories: List[str],
    ) -> Tuple[List[str], List[str]]:
        """Identify matching fashion categories and keywords."""
        search_corpus = f"{title} {summary} {' '.join(raw_categories)}".lower()

        matched_cats: Set[str] = set()
        matched_kws: Set[str] = set()

        for cat, keywords in CATEGORY_KEYWORD_MAP.items():
            for kw in keywords:
                pattern = r"\b" + re.escape(kw) + r"(?:s|es)?\b"
                if re.search(pattern, search_corpus, re.IGNORECASE):
                    matched_cats.add(cat)
                    matched_kws.add(kw)

        # Include default source categories if no specific category matched
        if not matched_cats and default_categories:
            matched_cats.update(default_categories[:2])

        return sorted(list(matched_cats)), sorted(list(matched_kws))

    async def fetch_source(
        self,
        client: httpx.AsyncClient,
        source: FeedSourceConfig,
        fetched_at: str,
    ) -> List[Dict[str, Any]]:
        if source.name not in self._status_by_source:
            self._status_by_source[source.name] = FeedStatus(
                name=source.name,
                feed_url=source.feed_url,
                publisher=source.publisher,
                status="idle",
            )
        status = self._status_by_source[source.name]
        start_time = time.monotonic()

        try:
            response = await client.get(
                source.feed_url,
                timeout=httpx.Timeout(source.timeout_seconds, connect=source.connect_timeout_seconds),
                follow_redirects=True,
                headers={"User-Agent": "LUXE.TECH Fashion News Reader/1.0"},
            )
            elapsed_ms = round((time.monotonic() - start_time) * 1000, 1)

            if response.status_code != 200:
                status.status = "degraded"
                status.error = f"HTTP {response.status_code}"
                status.response_time_ms = elapsed_ms
                logger.warning("Feed %s returned HTTP %s", source.name, response.status_code)
                return []

            articles = self.parse_feed_xml(response.content, source, fetched_at)
            status.status = "healthy"
            status.last_fetched_at = fetched_at
            status.article_count = len(articles)
            status.freshness_seconds = 0
            status.error = None
            status.response_time_ms = elapsed_ms
            return articles

        except httpx.TimeoutException as exc:
            elapsed_ms = round((time.monotonic() - start_time) * 1000, 1)
            status.status = "failing"
            status.error = "Connection timed out"
            status.response_time_ms = elapsed_ms
            logger.warning("Feed %s timed out: %s", source.name, exc)
            return []
        except Exception as exc:
            elapsed_ms = round((time.monotonic() - start_time) * 1000, 1)
            status.status = "failing"
            status.error = f"Fetch failed: {type(exc).__name__}"
            status.response_time_ms = elapsed_ms
            logger.warning("Feed %s failed: %s", source.name, exc)
            return []

    def deduplicate_articles(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Deduplicate articles by canonical URL."""
        seen_urls: Set[str] = set()
        deduped: List[Dict[str, Any]] = []

        for art in articles:
            url = art["canonical_url"]
            if url in seen_urls:
                continue
            seen_urls.add(url)
            deduped.append(art)

        return deduped

    def derive_candidate_trends(
        self,
        articles: List[Dict[str, Any]],
        min_articles: int = 2,
    ) -> List[Dict[str, Any]]:
        """
        Derive candidate trend topics from multiple attributable articles.
        Preserves original article evidence. Labeled as 'news_derived'.
        Explicitly disclaims that article frequency does NOT represent actual sales or demand.
        """
        candidate_trends: List[Dict[str, Any]] = []

        for archetype in THEME_ARCHETYPES:
            theme_name = archetype["name"]
            theme_cat = archetype["category"]
            keywords = archetype["keywords"]
            negative_patterns = archetype.get("negative_patterns", [])

            # Find matching articles
            attributing_articles: List[Dict[str, Any]] = []
            for art in articles:
                corpus = f"{art['title']} {art['summary']} {' '.join(art.get('keywords', []))}".lower()
                if article_matches_archetype(corpus, keywords, negative_patterns):
                    attributing_articles.append(art)

            if len(attributing_articles) < min_articles:
                continue

            # Publishers represented
            publishers = sorted(list(set(a["publisher"] for a in attributing_articles)))
            article_count = len(attributing_articles)
            pub_count = len(publishers)

            description = (
                f"News-derived grouping of {article_count} attributed articles from "
                f"{', '.join(publishers)}. Article frequency is not a consumer or market metric."
            )

            trend_slug = slugify(theme_name)
            trend_record = {
                "id": trend_slug,
                "name": theme_name,
                "slug": trend_slug,
                "category": theme_cat,
                "description": description,
                "data_status": "news_derived",
                "is_candidate": True,
                "attributing_articles": attributing_articles,
                "publisher_count": pub_count,
                "article_count": article_count,
            }
            candidate_trends.append(trend_record)

        return candidate_trends

    def persist_candidates_to_db(self, candidate_trends: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Persist news-derived candidate trends and their source-attributed article signals
        to PostgreSQL idempotently. Explicitly marked as data_status='news_derived'.
        """
        from app.database import SessionLocal, Trend, TrendSignal, TrendDNA, now_utc
        db = SessionLocal()
        persisted_trends = 0
        persisted_signals = 0
        try:
            for candidate in candidate_trends:
                slug = candidate["slug"]
                name = candidate["name"]
                cat = candidate["category"]
                desc = candidate["description"]
                articles = candidate.get("attributing_articles", [])

                # Pick lead image
                lead_image = None
                for a in articles:
                    if a.get("image_url"):
                        lead_image = a["image_url"]
                        break

                trend = db.query(Trend).filter(Trend.slug == slug).first()
                if not trend:
                    trend_id = str(uuid.uuid4())
                    trend = Trend(
                        id=trend_id,
                        slug=slug,
                        name=name,
                        category=cat,
                        season="Season not established",
                        description=f"[news_derived] {desc}",
                        image_url=lead_image,
                        status="emerging",
                        confidence=0.0,
                        momentum=0.0,
                        velocity=0.0,
                        acceleration=0.0,
                        data_status="news_derived",
                    )
                    db.add(trend)
                    db.flush()
                    persisted_trends += 1
                else:
                    if lead_image and not trend.image_url:
                        trend.image_url = lead_image
                    trend.updated_at = now_utc()
                    db.flush()

                # Ensure TrendDNA exists
                dna = db.query(TrendDNA).filter(TrendDNA.trend_id == trend.id).first()
                if not dna:
                    archetype = next((a for a in THEME_ARCHETYPES if a["name"] == name), None)
                    colors = archetype.get("colors", []) if archetype else []
                    materials = archetype.get("materials", []) if archetype else []
                    textures = archetype.get("textures", []) if archetype else []
                    silhouettes = archetype.get("silhouettes", []) if archetype else []
                    patterns = archetype.get("patterns", []) if archetype else []

                    dna = TrendDNA(
                        id=str(uuid.uuid4()),
                        trend_id=trend.id,
                        colors_json=json.dumps(colors),
                        materials_json=json.dumps(materials),
                        textures_json=json.dumps(textures),
                        silhouettes_json=json.dumps(silhouettes),
                        patterns_json=json.dumps(patterns),
                        visual_description=f"Archetype visual attributes for news-derived candidate {name}.",
                        ai_interpretation="Editorial-derived candidate. Visual attributes reflect archetype definitions, not computer-vision measurements.",
                        data_status="news_derived",
                    )
                    db.add(dna)

                # Persist signals for each attributing article
                existing_signals = db.query(TrendSignal).filter(
                    TrendSignal.trend_id == trend.id,
                    TrendSignal.signal_type == "news_derived"
                ).all()
                existing_urls = set()
                for s in existing_signals:
                    meta = s.signal_metadata
                    if meta.get("canonical_url"):
                        existing_urls.add(meta["canonical_url"])

                for art in articles:
                    can_url = art.get("canonical_url")
                    if not can_url or can_url in existing_urls:
                        continue

                    pub_dt = None
                    if art.get("published_at"):
                        try:
                            pub_dt = datetime.fromisoformat(art["published_at"].replace("Z", "+00:00"))
                        except Exception:
                            pass

                    sig = TrendSignal(
                        id=str(uuid.uuid4()),
                        trend_id=trend.id,
                        source="culture",
                        signal_type="news_derived",
                        strength=1.0,
                        direction="up",
                        timestamp=pub_dt or now_utc(),
                        metadata_json=json.dumps({
                            "publisher": art.get("publisher"),
                            "title": art.get("title"),
                            "canonical_url": can_url,
                            "source_url": art.get("source_url"),
                            "source_name": art.get("source_name"),
                            "published_at": art.get("published_at"),
                            "fetched_at": art.get("fetched_at"),
                            "image_url": art.get("image_url"),
                            "summary": art.get("summary"),
                            "signal_kind": "news_derived",
                            "quality": "publisher_rss",
                        }),
                        data_status="news_derived",
                    )
                    db.add(sig)
                    existing_urls.add(can_url)
                    persisted_signals += 1

            db.commit()
            return {
                "status": "success",
                "persisted_trends": persisted_trends,
                "persisted_signals": persisted_signals,
            }
        except Exception as exc:
            db.rollback()
            logger.error("Failed to persist candidates to database: %s", exc)
            return {
                "status": "failed",
                "error": str(exc),
                "persisted_trends": 0,
                "persisted_signals": 0,
            }
        finally:
            db.close()

    async def ingest_all(self) -> Dict[str, Any]:
        """
        Refresh the in-memory article and editorial-candidate cache.
        Editorial coverage is not automatically persisted as market observations.
        """
        async with self._lock:
            fetched_at = datetime.now(timezone.utc).isoformat()
            all_articles: List[Dict[str, Any]] = []

            async with httpx.AsyncClient(follow_redirects=True) as client:
                fetch_tasks = [
                    self.fetch_source(client, src, fetched_at)
                    for src in self._sources
                    if src.enabled
                ]
                results = await asyncio.gather(*fetch_tasks, return_exceptions=True)

                for res in results:
                    if isinstance(res, list):
                        all_articles.extend(res)

            deduped_articles = self.deduplicate_articles(all_articles)
            candidate_trends = self.derive_candidate_trends(deduped_articles, min_articles=2)

            self._articles = deduped_articles
            self._candidate_trends = candidate_trends
            self._last_ingested_at = fetched_at
            self._cached_at = time.monotonic()

            return {
                "fetched_at": fetched_at,
                "total_articles": len(deduped_articles),
                "candidate_trends_count": len(candidate_trends),
                "sources_queried": len(self._sources),
                "db_persistence": {
                    "status": "not_attempted",
                    "persisted_trends": 0,
                    "persisted_signals": 0,
                },
            }

    async def get_status(self) -> Dict[str, Any]:
        """Return the current per-source status, counts, and freshness without secrets."""
        now_mono = time.monotonic()
        sources_status = []
        for src in self._sources:
            status = self._status_by_source[src.name]
            stat_dict = status.to_dict()
            if self._cached_at > 0:
                stat_dict["freshness_seconds"] = int(now_mono - self._cached_at)
            sources_status.append(stat_dict)

        return {
            "sources": sources_status,
            "total_articles_cached": len(self._articles),
            "candidate_trends_count": len(self._candidate_trends),
            "last_ingested_at": self._last_ingested_at,
            "cache_ttl_seconds": self.CACHE_TTL_SECONDS,
            "pipeline_version": "phase_1_rss",
        }

    async def get_articles(
        self,
        category: Optional[str] = None,
        publisher: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Return normalized articles with optional category or publisher filtering."""
        # Refresh if cache expired or empty
        if not self._articles or (time.monotonic() - self._cached_at > self.CACHE_TTL_SECONDS):
            await self.ingest_all()

        results = self._articles
        if publisher:
            results = [a for a in results if a["publisher"].lower() == publisher.lower()]
        if category:
            results = [a for a in results if any(c.lower() == category.lower() for c in a.get("categories", []))]

        return results[:limit]

    async def get_candidate_trends(
        self,
        category: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Return in-memory editorial candidates, optionally filtered by category."""
        if not self._candidate_trends or (time.monotonic() - self._cached_at > self.CACHE_TTL_SECONDS):
            await self.ingest_all()
        if category:
            return [
                candidate
                for candidate in self._candidate_trends
                if candidate["category"].casefold() == category.casefold()
            ]
        return self._candidate_trends

feed_ingestion_service = FeedIngestionService()
