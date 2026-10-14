from typing import Any, Dict, List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import RetailSignal, Trend, get_db
from app.schemas.common import ApiResponse
from app.services.retail_engine import retail_engine

router = APIRouter(prefix="/retail", tags=["retail"])


@router.get("", response_model=ApiResponse[Dict[str, Any]])
def get_retail_overview(db: Session = Depends(get_db)):
    metrics = retail_engine.get_dashboard_metrics(db=db)
    return ApiResponse.ok(metrics)


@router.get("/trend/{trend_id}", response_model=ApiResponse[Dict[str, Any]])
def get_retail_for_trend(trend_id: str, db: Session = Depends(get_db)):
    trend = db.query(Trend).filter((Trend.id == trend_id) | (Trend.slug == trend_id)).first()
    if not trend:
        return ApiResponse.fail(code="TREND_NOT_FOUND", message=f"Trend '{trend_id}' not found.", status_code=404)

    metrics = retail_engine.get_dashboard_metrics(db=db, trend_id=trend.id)
    return ApiResponse.ok(metrics)


@router.get("/regions", response_model=ApiResponse[List[Dict[str, Any]]])
def get_retail_regions(db: Session = Depends(get_db)):
    metrics = retail_engine.get_dashboard_metrics(db=db)
    return ApiResponse.ok(metrics.get("regions", []))


@router.get("/categories", response_model=ApiResponse[List[Dict[str, Any]]])
def get_retail_categories(db: Session = Depends(get_db)):
    metrics = retail_engine.get_dashboard_metrics(db=db)
    return ApiResponse.ok(metrics.get("categories", []))
