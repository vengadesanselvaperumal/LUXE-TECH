from datetime import datetime
from typing import Any, Dict, List, Optional, cast
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import Trend, get_db
from app.schemas.common import ApiResponse
from app.services.observations import get_verified_signal_observations

router = APIRouter(prefix="/signals", tags=["signals"])


def _isoformat_if_present(value: Any) -> Optional[str]:
    timestamp = cast(Optional[datetime], value)
    return timestamp.isoformat() if timestamp is not None else None


import time

_signals_live_cache: Optional[Dict[str, Any]] = None
_signals_live_cache_time: float = 0.0
SIGNALS_LIVE_CACHE_TTL = 30.0


@router.get("/live", response_model=ApiResponse[Dict[str, Any]])
def get_live_signals(db: Session = Depends(get_db)):
    global _signals_live_cache, _signals_live_cache_time
    now = time.monotonic()
    if _signals_live_cache is not None and (now - _signals_live_cache_time) < SIGNALS_LIVE_CACHE_TTL:
        return ApiResponse.ok(_signals_live_cache)

    observations, signals = get_verified_signal_observations(db)
    if not signals:
        empty_data = {
            "runway": None,
            "social": None,
            "search": None,
            "retail": None,
            "culture": None,
            "data_status": "insufficient_data",
            "last_updated": None,
            "last_fetched_at": None,
            "observation_count": 0,
        }
        _signals_live_cache = empty_data
        _signals_live_cache_time = now
        return ApiResponse.ok(empty_data)

    source_buckets: Dict[str, List[float]] = {}
    for s in signals:
        source_buckets.setdefault(cast(str, s.source), []).append(cast(float, s.strength))

    result: Dict[str, Any] = {
        source: round(sum(values) / len(values), 1) if (values := source_buckets.get(source)) else None
        for source in ("runway", "social", "search", "retail", "culture")
    }
    result.update({
        "data_status": "observed",
        "last_updated": max(item["timestamp"] for item in observations),
        "last_fetched_at": max(item["fetched_at"] for item in observations),
        "observation_count": len(observations),
    })
    _signals_live_cache = result
    _signals_live_cache_time = now
    return ApiResponse.ok(result)


@router.get("/{trend_id}", response_model=ApiResponse[List[Dict[str, Any]]])
def get_signals_for_trend(trend_id: str, db: Session = Depends(get_db)):
    trend = db.query(Trend).filter((Trend.id == trend_id) | (Trend.slug == trend_id)).first()
    if not trend:
        return ApiResponse.fail(code="TREND_NOT_FOUND", message=f"Trend '{trend_id}' not found.", status_code=404)

    _, signals = get_verified_signal_observations(db, cast(str, trend.id))

    return ApiResponse.ok([
        {
            "id": s.id,
            "trend_id": cast(str, s.trend_id),
            "source": cast(str, s.source),
            "signal_type": cast(str, s.signal_type),
            "strength": cast(float, s.strength),
            "direction": cast(str, s.direction),
            "timestamp": _isoformat_if_present(s.timestamp),
            "metadata": s.signal_metadata,
            "data_status": cast(str, s.data_status),
        }
        for s in signals
    ])
