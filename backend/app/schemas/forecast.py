from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from app.schemas.common import DataStatus


class ModelResult(BaseModel):
    name: str
    mae: float
    rmse: float
    mape: float
    forecast_values: List[float]
    backtest_accuracy: float


class ForecastGenerateRequest(BaseModel):
    trend_id: str
    horizon: str = "3_months"  # 1_month, 3_months, 6_months
    models: Optional[List[str]] = None


class ForecastResponse(BaseModel):
    id: Optional[str] = None
    trend_id: str
    selected_model: str
    horizon: str
    forecast_value: float
    backtest_accuracy: float
    training_start: Optional[datetime] = None
    training_end: Optional[datetime] = None
    backtest_period: str = "Last 6 Months"
    historical_points: List[Dict[str, Any]] = Field(default_factory=list)
    projected_points: List[Dict[str, Any]] = Field(default_factory=list)
    model_evaluations: List[ModelResult] = Field(default_factory=list)
    data_status: DataStatus = DataStatus.FORECAST
