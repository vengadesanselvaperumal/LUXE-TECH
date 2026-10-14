from typing import Any, Dict, cast
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import Forecast, Trend, get_db
from app.schemas.common import ApiResponse
from app.services.forecast_engine import forecast_engine
from app.services.observations import get_verified_signal_observations
from app.utils.rate_limit import rate_limit_dependency
from app.utils.security import get_privileged_user

router = APIRouter(prefix="/forecast", tags=["forecasts"])


@router.get("/{trend_id}", response_model=ApiResponse[Dict[str, Any]])
def get_forecast(
    trend_id: str,
    horizon: str = Query("3_months", description="1_month, 3_months, or 6_months"),
    db: Session = Depends(get_db)
):
    trend = db.query(Trend).filter((Trend.id == trend_id) | (Trend.slug == trend_id)).first()
    if not trend:
        return ApiResponse.fail(code="TREND_NOT_FOUND", message=f"Trend '{trend_id}' not found.", status_code=404)

    # Fetch historical observations
    trend_id_value = cast(str, trend.id)
    observations, _ = get_verified_signal_observations(db, trend_id_value)

    result = forecast_engine.generate_forecast(observations=observations, horizon=horizon, trend_id=trend_id_value)

    if result.get("status") == "insufficient_data":
        result_message = result.get("message", "Insufficient historical signal observations to compute models.")
        return ApiResponse.ok({
            "status": "insufficient_data",
            "message": (
                f"{result_message} Forecasts use only timestamped observed signals with "
                "source name, fetch timestamp, and source URL or user-upload provenance."
            ),
            "trend_id": trend_id_value,
            "data_status": "insufficient_data"
        })

    return ApiResponse.ok(result)


@router.post(
    "/{trend_id}",
    response_model=ApiResponse[Dict[str, Any]],
    dependencies=[Depends(rate_limit_dependency(max_requests=10, window_seconds=60, scope="forecast_backtest"))]
)
def trigger_forecast_backtest(
    trend_id: str,
    horizon: str = Query("3_months"),
    current_user: Dict[str, Any] = Depends(get_privileged_user),
    db: Session = Depends(get_db)
):
    trend = db.query(Trend).filter((Trend.id == trend_id) | (Trend.slug == trend_id)).first()
    if not trend:
        return ApiResponse.fail(code="TREND_NOT_FOUND", message=f"Trend '{trend_id}' not found.", status_code=404)

    trend_id_value = cast(str, trend.id)
    observations, verified_signals = get_verified_signal_observations(db, trend_id_value)

    result = forecast_engine.generate_forecast(observations=observations, horizon=horizon, trend_id=trend_id_value)

    if result.get("status") == "insufficient_data":
        return ApiResponse.ok({
            "status": "insufficient_data",
            "message": (
                f"{result.get('message', 'Insufficient historical signal observations to compute models.')} "
                "Forecasts use only timestamped observed signals with source name, fetch timestamp, "
                "and source URL or user-upload provenance."
            ),
            "data_status": "insufficient_data"
        })

    # Save best model forecast into database
    existing_f = db.query(Forecast).filter(Forecast.trend_id == trend.id).first()
    if not existing_f:
        existing_f = Forecast(
            trend_id=trend_id_value,
            model=result["selected_model"],
            forecast_value=result["forecast_value"],
            backtest_accuracy=result["backtest_accuracy"],
            training_start=verified_signals[0].timestamp,
            training_end=verified_signals[-1].timestamp,
            data_status="forecast",
        )
        db.add(existing_f)
    else:
        existing_f.model = result["selected_model"]
        existing_f.forecast_value = result["forecast_value"]
        existing_f.backtest_accuracy = result["backtest_accuracy"]
        setattr(existing_f, "horizon", horizon)
        setattr(existing_f, "training_start", verified_signals[0].timestamp)
        setattr(existing_f, "training_end", verified_signals[-1].timestamp)
        setattr(existing_f, "data_status", "forecast")

    db.commit()

    return ApiResponse.ok(result)
