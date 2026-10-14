import json
import uuid
from typing import Any, Dict, cast
from sqlalchemy.orm import Session
from app.database import Forecast, Prophecy, Trend
from app.services.gemini_service import gemini_service
from app.services.forecast_engine import ForecastEngine
from app.services.observations import get_verified_signal_observations


class ProphecyEngine:
    @classmethod
    async def generate_for_trend(cls, db: Session, trend_id: str) -> Dict[str, Any]:
        trend = db.query(Trend).filter(Trend.id == trend_id).first()
        if not trend:
            return {}

        trend_id_value = cast(str, trend.id)
        observations, signals = get_verified_signal_observations(db, trend_id_value)
        if len(observations) < ForecastEngine.MIN_OBSERVATIONS_REQUIRED:
            return {
                "trend_id": trend_id_value,
                "timeline": [],
                "status": "insufficient_data",
                "message": (
                    "At least six timestamped, source-attributed observations are required "
                    "before generating a scenario."
                ),
                "data_status": "insufficient_data",
            }

        signal_dict = {
            cast(str, signal.source): cast(float, signal.strength)
            for signal in signals
        }

        latest_forecast = db.query(Forecast).filter(Forecast.trend_id == trend_id_value).order_by(Forecast.created_at.desc()).first()
        forecast_val = cast(float, latest_forecast.forecast_value) if latest_forecast else None
        if latest_forecast is None or cast(str, latest_forecast.data_status) != "forecast":
            return {
                "trend_id": trend_id_value,
                "timeline": [],
                "status": "insufficient_data",
                "message": "A forecast backtested against verified observations is required before scenario generation.",
                "data_status": "insufficient_data",
            }

        # Generate stages via Gemini or local engine
        stages = await gemini_service.generate_prophecy(
            trend_name=cast(str, trend.name),
            signals=signal_dict,
            forecast_value=forecast_val
        )
        if not gemini_service.is_available or any(
            stage.get("data_status") != "ai_generated" for stage in stages
        ):
            return {
                "trend_id": trend_id_value,
                "timeline": [],
                "status": "provider_unavailable",
                "message": (
                    "Verified observations are available, but no valid AI scenario was returned. "
                    "No demo scenario was saved."
                ),
                "data_status": "insufficient_data",
            }

        # Store in database
        db.query(Prophecy).filter(Prophecy.trend_id == trend_id_value).delete()
        persisted_records = []
        for stage_item in stages:
            rec = Prophecy(
                id=str(uuid.uuid4()),
                trend_id=trend_id_value,
                stage=stage_item["stage"],
                forecast=stage_item["forecast"],
                evidence_json=json.dumps(stage_item.get("evidence", [])),
                opportunity=stage_item["opportunity"],
                risk=stage_item["risk"],
                confidence=None,
                data_status=stage_item.get("data_status", "demo")
            )
            db.add(rec)
            persisted_records.append(rec)

        db.commit()

        current_stage = cast(str, trend.status) or "emerging"
        overall_status = (
            "ai_generated" if all(item.get("data_status") == "ai_generated" for item in stages)
            else "demo"
        )
        return {
            "trend_id": trend_id_value,
            "current_stage": current_stage,
            "timeline": stages,
            "scenario_analysis": {
                "forecast_index": forecast_val,
                "recommended_horizon": "6-12 Months"
            },
            "data_status": overall_status
        }


prophecy_engine = ProphecyEngine()
