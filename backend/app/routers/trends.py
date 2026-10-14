import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, cast
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload
from app.database import SavedTrend, Trend, TrendDNA, TrendSignal, get_db
from app.schemas.common import ApiResponse
from app.schemas.trend import TrendCreate
from app.services.gemini_service import gemini_service
from app.services.observations import get_verified_signal_observations
from app.services.trend_engine import trend_engine
from app.utils.rate_limit import rate_limit_dependency
from app.utils.security import get_current_user, get_privileged_user
from app.utils.validation import slugify

router = APIRouter(prefix="/trends", tags=["trends"])


def _isoformat_if_present(value: Any) -> Optional[str]:
    timestamp = cast(Optional[datetime], value)
    return timestamp.isoformat() if timestamp is not None else None


ALL_CATEGORIES_16 = [
    {"name": "Color", "kicker": "01", "subtitle": "Current color momentum", "tone": "rose", "route": "trend"},
    {"name": "Materials", "kicker": "02", "subtitle": "New material language", "tone": "green", "route": "trend"},
    {"name": "Silhouettes", "kicker": "03", "subtitle": "Shape the next season", "tone": "sand", "route": "trend"},
    {"name": "Patterns", "kicker": "04", "subtitle": "The repeat system", "tone": "ink", "route": "trend"},
    {"name": "Prints", "kicker": "05", "subtitle": "Visual codes in motion", "tone": "plum", "route": "trend"},
    {"name": "Textures", "kicker": "06", "subtitle": "Touch is a signal", "tone": "green", "route": "trend"},
    {"name": "Product", "kicker": "07", "subtitle": "What should we create?", "tone": "rose", "route": "product"},
    {"name": "Accessories", "kicker": "08", "subtitle": "Details with momentum", "tone": "sand", "route": "product"},
    {"name": "Womenswear", "kicker": "09", "subtitle": "Signals by consumer", "tone": "plum", "route": "product"},
    {"name": "Menswear", "kicker": "10", "subtitle": "The new uniform", "tone": "ink", "route": "product"},
    {"name": "Streetwear", "kicker": "11", "subtitle": "Culture in product form", "tone": "green", "route": "trend"},
    {"name": "Couture", "kicker": "12", "subtitle": "Craft meets future", "tone": "rose", "route": "trend"},
    {"name": "Retail", "kicker": "13", "subtitle": "What is moving now", "tone": "sand", "route": "retail"},
    {"name": "Consumer", "kicker": "14", "subtitle": "The people behind demand", "tone": "green", "route": "retail"},
    {"name": "Market", "kicker": "15", "subtitle": "Opportunity by region", "tone": "ink", "route": "retail"},
    {"name": "Future Signals", "kicker": "16", "subtitle": "The next signal", "tone": "plum", "route": "prophecy"},
]


import time
from sqlalchemy import func

_categories_cache: Optional[List[Dict[str, Any]]] = None
_categories_cache_time: float = 0.0
CATEGORIES_CACHE_TTL = 60.0

@router.get("/categories", response_model=ApiResponse[List[Dict[str, Any]]])
def get_categories(db: Session = Depends(get_db)):
    global _categories_cache, _categories_cache_time
    now = time.monotonic()
    if _categories_cache is not None and (now - _categories_cache_time) < CATEGORIES_CACHE_TTL:
        return ApiResponse.ok(_categories_cache)

    category_counts_raw = (
        db.query(func.lower(Trend.category), func.count(Trend.id))
        .filter(
            Trend.data_status == "observed",
            ~Trend.description.startswith("[news_derived]"),
        )
        .group_by(func.lower(Trend.category))
        .all()
    )
    category_counts = {cat_name.lower(): count for cat_name, count in category_counts_raw if cat_name}

    results = []
    for cat in ALL_CATEGORIES_16:
        count = category_counts.get(cat["name"].lower(), 0)
        results.append({
            "code": cat["kicker"],
            "name": cat["name"],
            "title": cat["name"].upper(),
            "subtitle": cat["subtitle"],
            "tone": cat["tone"],
            "route": cat["route"],
            "trend_count": count
        })

    _categories_cache = results
    _categories_cache_time = now
    return ApiResponse.ok(results)


_trends_list_cache: Dict[str, Any] = {}
_trends_list_cache_time: Dict[str, float] = {}
TRENDS_LIST_CACHE_TTL = 15.0

@router.get("", response_model=ApiResponse[List[Dict[str, Any]]])
def list_trends(
    sort: str = Query("recent", description="Sort order: recent, momentum, confidence"),
    category: Optional[str] = Query(None, description="Filter by category"),
    include_demo: bool = Query(False, description="Include demo/unverified trends"),
    include_candidates: bool = Query(False, description="Include news-derived candidate trends"),
    data_status: Optional[str] = Query(None, description="Filter by data_status: observed, demo, news_derived"),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    cache_key = f"{sort}:{category}:{include_demo}:{include_candidates}:{data_status}:{limit}"
    now = time.monotonic()
    if cache_key in _trends_list_cache and (now - _trends_list_cache_time.get(cache_key, 0)) < TRENDS_LIST_CACHE_TTL:
        return ApiResponse.ok(_trends_list_cache[cache_key])

    query = db.query(Trend).options(joinedload(Trend.dna))

    if data_status:
        query = query.filter(Trend.data_status == data_status)
    elif include_demo or include_candidates:
        if not include_candidates:
            query = query.filter(~Trend.description.startswith("[news_derived]"))
    else:
        query = query.filter(
            Trend.data_status == "observed",
            ~Trend.description.startswith("[news_derived]"),
        )

    if category:
        query = query.filter(Trend.category.ilike(category))

    query = query.order_by(Trend.created_at.desc())

    trends = query.limit(limit).all()

    items = [
        {
            "id": t.id,
            "slug": t.slug,
            "name": t.name,
            "category": t.category,
            "season": t.season,
            "description": t.description,
            "image_url": t.image_url if cast(str, t.data_status) == "observed" or include_demo or include_candidates else None,
            "status": t.status,
            "confidence": t.confidence if cast(str, t.data_status) == "observed" else None,
            "momentum": t.momentum if cast(str, t.data_status) == "observed" else None,
            "velocity": t.velocity if cast(str, t.data_status) == "observed" else None,
            "acceleration": t.acceleration if cast(str, t.data_status) == "observed" else None,
            "data_status": t.data_status,
            "dna": t.dna.to_dict() if t.dna else None,
            "created_at": _isoformat_if_present(t.created_at),
        }
        for t in trends
    ]
    _trends_list_cache[cache_key] = items
    _trends_list_cache_time[cache_key] = now
    return ApiResponse.ok(items)


@router.get("/saved", response_model=ApiResponse[List[Dict[str, Any]]])
def get_saved_trends(current_user: Dict[str, Any] = Depends(get_current_user), db: Session = Depends(get_db)):
    saved = db.query(SavedTrend).filter(SavedTrend.user_id == current_user["id"]).all()
    results = []
    for item in saved:
        if item.trend:
            results.append({
                "id": item.trend.id,
                "slug": item.trend.slug,
                "name": item.trend.name,
                "category": item.trend.category,
                "image_url": item.trend.image_url,
                "saved_at": _isoformat_if_present(item.created_at),
            })
    return ApiResponse.ok(results)


@router.post("/{trend_id}/save", response_model=ApiResponse[Dict[str, Any]])
def toggle_save_trend(trend_id: str, current_user: Dict[str, Any] = Depends(get_current_user), db: Session = Depends(get_db)):
    trend = db.query(Trend).filter((Trend.id == trend_id) | (Trend.slug == trend_id)).first()
    if not trend:
        return ApiResponse.fail(code="TREND_NOT_FOUND", message="Trend not found.", status_code=404)

    existing = db.query(SavedTrend).filter(SavedTrend.user_id == current_user["id"], SavedTrend.trend_id == trend.id).first()
    if existing:
        db.delete(existing)
        db.commit()
        return ApiResponse.ok({"saved": False, "trend_id": trend.id})

    new_saved = SavedTrend(id=str(uuid.uuid4()), user_id=current_user["id"], trend_id=trend.id)
    db.add(new_saved)
    db.commit()
    return ApiResponse.ok({"saved": True, "trend_id": trend.id})


@router.get("/{slug}", response_model=ApiResponse[Dict[str, Any]])
def get_trend_detail(
    slug: str,
    include_demo: bool = Query(False, description="Include demo trends"),
    include_candidates: bool = Query(False, description="Include news-derived candidate trends"),
    db: Session = Depends(get_db)
):
    query = db.query(Trend).filter((Trend.slug == slug) | (Trend.id == slug))
    if not (include_demo or include_candidates):
        query = query.filter(
            Trend.data_status == "observed",
            ~Trend.description.startswith("[news_derived]"),
        )
    elif not include_candidates:
        query = query.filter(~Trend.description.startswith("[news_derived]"))

    trend = query.first()
    if not trend:
        return ApiResponse.fail(code="TREND_NOT_FOUND", message=f"Trend '{slug}' not found.", status_code=404)

    # Fetch signals
    if cast(str, trend.data_status) == "observed":
        _, signals = get_verified_signal_observations(db, cast(str, trend.id))
        signal_dicts = [
            {
                "id": s.id,
                "source": s.source,
                "signal_type": s.signal_type,
                "strength": s.strength,
                "direction": s.direction,
                "timestamp": _isoformat_if_present(s.timestamp),
                "metadata": s.signal_metadata,
                "data_status": s.data_status,
            }
            for s in signals
        ]
        metrics = trend_engine.compute_metrics(signal_dicts)
    else:
        raw_signals = db.query(TrendSignal).filter(TrendSignal.trend_id == trend.id).all()
        signal_dicts = [
            {
                "id": s.id,
                "source": s.source,
                "signal_type": s.signal_type,
                "strength": s.strength,
                "direction": s.direction,
                "timestamp": _isoformat_if_present(s.timestamp),
                "metadata": s.signal_metadata,
                "data_status": s.data_status,
            }
            for s in raw_signals
        ]
        metrics = {
            "momentum": None,
            "velocity": None,
            "acceleration": None,
            "persistence": None,
            "source_diversity": None,
            "cross_source_agreement": None,
            "trend_score": None,
        }

    # Fetch DNA
    dna = db.query(TrendDNA).filter(TrendDNA.trend_id == trend.id).first()
    dna_dict = dna.to_dict() if dna else None

    return ApiResponse.ok({
        "id": trend.id,
        "slug": trend.slug,
        "name": trend.name,
        "category": trend.category,
        "season": trend.season,
        "description": trend.description,
        "image_url": trend.image_url if cast(str, trend.data_status) == "observed" or include_demo or include_candidates else None,
        "status": trend.status,
        "confidence": trend.confidence if cast(str, trend.data_status) == "observed" else None,
        "momentum": metrics["momentum"],
        "velocity": metrics["velocity"],
        "acceleration": metrics["acceleration"],
        "persistence": metrics.get("persistence"),
        "source_diversity": metrics.get("source_diversity"),
        "cross_source_agreement": metrics["cross_source_agreement"],
        "trend_score": metrics["trend_score"],
        "data_status": trend.data_status,
        "signals": signal_dicts,
        "dna": dna_dict,
        "created_at": _isoformat_if_present(trend.created_at),
    })


@router.post(
    "",
    response_model=ApiResponse[Dict[str, Any]],
    dependencies=[Depends(rate_limit_dependency(max_requests=10, window_seconds=60, scope="trend_create"))]
)
async def create_trend(
    req: TrendCreate,
    _current_user: Dict[str, Any] = Depends(get_privileged_user),
    db: Session = Depends(get_db)
):
    slug = req.slug or slugify(req.name)
    existing = db.query(Trend).filter(Trend.slug == slug).first()
    if existing:
        return ApiResponse.fail(code="SLUG_EXISTS", message=f"Trend with slug '{slug}' already exists.", status_code=400)

    # Synthesize AI trend interpretation
    signals_input: Dict[str, float] = {}
    analysis = await gemini_service.analyze_trend(req.name, req.category, req.season or "SS 2027", signals_input)

    trend_id = str(uuid.uuid4())
    trend = Trend(
        id=trend_id,
        slug=slug,
        name=req.name,
        category=req.category,
        season=req.season,
        description=req.description or analysis.get("summary", ""),
        image_url=req.image_url,
        status=req.status,
        confidence=req.confidence,
        momentum=req.momentum,
        velocity=req.velocity,
        acceleration=req.acceleration,
        data_status=analysis.get("data_status", "demo")
    )
    db.add(trend)

    # Add DNA from AI analysis
    dna_info = analysis.get("visual_dna", {})
    dna = TrendDNA(
        id=str(uuid.uuid4()),
        trend_id=trend_id,
        colors_json=json.dumps(dna_info.get("colors", [])),
        materials_json=json.dumps(dna_info.get("materials", [])),
        textures_json=json.dumps(dna_info.get("textures", [])),
        silhouettes_json=json.dumps(dna_info.get("silhouettes", [])),
        patterns_json=json.dumps(dna_info.get("patterns", [])),
        visual_description=req.description,
        ai_interpretation=analysis.get("summary"),
        data_status=analysis.get("data_status", "demo")
    )
    db.add(dna)
    db.commit()
    db.refresh(trend)

    return ApiResponse.ok({
        "id": trend.id,
        "slug": trend.slug,
        "name": trend.name,
        "category": trend.category,
        "data_status": trend.data_status,
        "analysis": analysis
    })
