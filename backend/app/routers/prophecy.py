import json
from typing import Any, Dict, cast
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import Forecast, Prophecy, Trend, get_db
from app.schemas.common import ApiResponse
from app.services.forecast_engine import ForecastEngine
from app.services.observations import get_verified_signal_observations
from app.services.prophecy_engine import prophecy_engine
from app.utils.rate_limit import rate_limit_dependency
from app.utils.security import get_privileged_user

router = APIRouter(prefix="/prophecy", tags=["prophecy"])


@router.get("/{trend_id}", response_model=ApiResponse[Dict[str, Any]])
async def get_prophecy(trend_id: str, db: Session = Depends(get_db)):
    trend = db.query(Trend).filter((Trend.id == trend_id) | (Trend.slug == trend_id)).first()
    if not trend:
        raise HTTPException(status_code=404, detail=f"Trend '{trend_id}' not found.")

    trend_id_value = cast(str, trend.id)
    observations, _ = get_verified_signal_observations(db, trend_id_value)
    latest_forecast = (
        db.query(Forecast)
        .filter(Forecast.trend_id == trend_id_value)
        .order_by(Forecast.created_at.desc())
        .first()
    )
    prophecies = (
        db.query(Prophecy)
        .filter(
            Prophecy.trend_id == trend_id_value,
            Prophecy.data_status == "ai_generated",
        )
        .all()
    )
    if len(observations) < ForecastEngine.MIN_OBSERVATIONS_REQUIRED:
        message = (
            f"Found {len(observations)} verified observations; "
            f"{ForecastEngine.MIN_OBSERVATIONS_REQUIRED} are required."
        )
    elif latest_forecast is None or cast(str, latest_forecast.data_status) != "forecast":
        message = "No forecast backtested against verified observations is available."
    elif not prophecies:
        message = "Verified evidence is available, but no validated AI scenario has been generated."
    else:
        message = ""
    if message:
        return ApiResponse.ok({
            "trend_id": trend_id_value,
            "current_stage": None,
            "timeline": [],
            "status": "insufficient_data",
            "message": message,
            "data_status": "insufficient_data",
        })

    timeline = [
        {
            "stage": pr.stage,
            "forecast": pr.forecast,
            "evidence": json.loads(cast(str, pr.evidence_json) or "[]"),
            "opportunity": pr.opportunity,
            "risk": pr.risk,
            "confidence": pr.confidence,
            "data_status": pr.data_status,
        }
        for pr in prophecies
    ]

    return ApiResponse.ok({
        "trend_id": trend_id_value,
        "current_stage": trend.status or "emerging",
        "timeline": timeline,
        "scenario_analysis": {
            "momentum": trend.momentum,
            "velocity": trend.velocity,
            "confidence": trend.confidence,
            "recommended_horizon": "6-12 Months"
        },
        "data_status": (
            "ai_generated" if all(pr.data_status == "ai_generated" for pr in prophecies)
            else "demo"
        )
    })


@router.post(
    "/{trend_id}",
    response_model=ApiResponse[Dict[str, Any]],
    dependencies=[Depends(rate_limit_dependency(max_requests=10, window_seconds=60, scope="prophecy_generate"))]
)
async def generate_prophecy(
    trend_id: str,
    _current_user: Dict[str, Any] = Depends(get_privileged_user),
    db: Session = Depends(get_db)
):
    trend = db.query(Trend).filter((Trend.id == trend_id) | (Trend.slug == trend_id)).first()
    if not trend:
        return ApiResponse.fail(code="TREND_NOT_FOUND", message=f"Trend '{trend_id}' not found.", status_code=404)

    res = await prophecy_engine.generate_for_trend(db=db, trend_id=cast(str, trend.id))
    return ApiResponse.ok(res)
