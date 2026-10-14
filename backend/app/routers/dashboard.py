import time
from typing import Any, Dict, List, Optional, cast
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import Forecast, Prophecy, Trend, get_db
from app.schemas.common import ApiResponse
from app.services.observations import get_verified_signal_observations

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

_dashboard_cache: Optional[Dict[str, Any]] = None
_dashboard_cache_time: float = 0.0
DASHBOARD_CACHE_TTL = 30.0  # seconds


@router.get("", response_model=ApiResponse[Dict[str, Any]])
async def get_dashboard(db: Session = Depends(get_db)):
    global _dashboard_cache, _dashboard_cache_time
    now = time.monotonic()
    if _dashboard_cache is not None and (now - _dashboard_cache_time) < DASHBOARD_CACHE_TTL:
        return ApiResponse.ok(_dashboard_cache)

    # 1. Recent and featured trends (bounded limit to avoid full table scans)
    observed_trends = (
        db.query(Trend)
        .filter(Trend.data_status == "observed")
        .order_by(Trend.created_at.desc())
        .limit(10)
        .all()
    )
    trends_query = observed_trends if observed_trends else (
        db.query(Trend)
        .order_by(Trend.created_at.desc())
        .limit(10)
        .all()
    )

    recent_trends = [
        {
            "id": t.id,
            "slug": t.slug,
            "name": t.name,
            "category": t.category,
            "season": t.season,
            "description": t.description,
            "image_url": t.image_url,
            "status": t.status,
            "confidence": t.confidence if t.data_status == "observed" else None,
            "momentum": t.momentum if t.data_status == "observed" else None,
            "velocity": t.velocity if t.data_status == "observed" else None,
            "data_status": t.data_status,
        }
        for t in trends_query[:8]
    ]

    featured_trends = [
        {
            "id": t.id,
            "slug": t.slug,
            "name": t.name,
            "category": t.category,
            "status": t.status,
            "momentum": t.momentum if t.data_status == "observed" else None,
            "confidence": t.confidence if t.data_status == "observed" else None,
            "image_url": t.image_url,
            "data_status": t.data_status,
        }
        for t in trends_query[1:5]
    ]

    # 2. Live signals summary
    _, signals = get_verified_signal_observations(db)
    signal_by_src: Dict[str, List[float]] = {}
    for s in signals:
        signal_by_src.setdefault(cast(str, s.source), []).append(cast(float, s.strength))

    live_signals: Dict[str, Any] = {
        source: round(sum(values) / len(values), 1) if (values := signal_by_src.get(source)) else None
        for source in ("runway", "social", "search", "retail", "culture")
    }
    live_signals["data_status"] = "observed" if signals else "insufficient_data"

    # 3. Current fashion analysis from verified RSS editorial feeds
    from app.services.feed_ingestion_service import feed_ingestion_service
    articles = feed_ingestion_service._articles
    if articles:
        lead_art = articles[0]
        publishers = list(set(a.get("publisher") for a in articles[:8] if a.get("publisher")))
        current_fashion = {
            "title": "What's happening in fashion right now?",
            "headline": lead_art.get("title"),
            "summary": f"Editorial reporting across {', '.join(publishers)}. " + (lead_art.get("summary") or ""),
            "data_status": "news_derived",
            "lead_image": lead_art.get("image_url"),
            "source_url": lead_art.get("canonical_url"),
            "published_at": lead_art.get("published_at"),
        }
    else:
        current_fashion = {
            "title": "What's happening in fashion right now?",
            "headline": None,
            "summary": "Fashion news feeds are initializing.",
            "data_status": "insufficient_data",
        }

    # 4. Products from database labeled honestly with data_status
    from app.database import Product
    products_db = db.query(Product).limit(4).all()
    featured_products: List[Dict[str, Any]] = [
        {
            "id": p.id,
            "name": p.name,
            "category": p.category,
            "description": p.description,
            "material": p.material,
            "silhouette": p.silhouette,
            "color": p.color,
            "target_consumer": p.target_consumer,
            "data_status": p.data_status,
        }
        for p in products_db
    ]

    # 5. Forecast highlights
    forecasts = (
        db.query(Forecast)
        .order_by(Forecast.created_at.desc())
        .limit(3)
        .all()
    )
    forecast_highlights = [
        {
            "id": f.id,
            "trend_id": f.trend_id,
            "model": f.model,
            "horizon": f.horizon,
            "forecast_value": f.forecast_value,
            "backtest_accuracy": None,
            "data_status": f.data_status,
        }
        for f in forecasts
    ]

    # 6. Prophecy highlights
    prophecies = (
        db.query(Prophecy)
        .filter(Prophecy.stage == "emerging")
        .limit(3)
        .all()
    )
    prophecy_highlights = [
        {
            "id": pr.id,
            "trend_id": pr.trend_id,
            "stage": pr.stage,
            "forecast": pr.forecast,
            "opportunity": pr.opportunity,
            "confidence": None,
            "data_status": pr.data_status,
        }
        for pr in prophecies
    ]

    hero = {
        "kicker": "FASHION INTELLIGENCE PLATFORM",
        "title": "From runway to ready.",
        "subtitle": "AI-powered intelligence for understanding what fashion is becoming.",
        "live_signals": live_signals,
    }

    data = {
        "hero": hero,
        "recent_trends": recent_trends,
        "live_signals": live_signals,
        "featured_trends": featured_trends,
        "current_fashion": current_fashion,
        "featured_products": featured_products,
        "forecast_highlights": forecast_highlights,
        "prophecy_highlights": prophecy_highlights,
    }
    _dashboard_cache = data
    _dashboard_cache_time = now
    return ApiResponse.ok(data)
