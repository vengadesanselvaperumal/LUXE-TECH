from typing import Any, Dict, List, Optional, cast
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import Product, Trend, get_db
from app.schemas.common import ApiResponse
from app.schemas.product import ProductGenerateRequest
from app.services.product_engine import product_engine
from app.utils.rate_limit import rate_limit_dependency
from app.utils.security import get_privileged_user

router = APIRouter(prefix="/products", tags=["products"])


@router.get("", response_model=ApiResponse[List[Dict[str, Any]]])
def list_products(
    category: Optional[str] = Query(None),
    include_demo: bool = Query(False),
    limit: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_db),
):
    if not include_demo:
        # The current products table has no source attribution fields. Do not
        # expose legacy rows as source-verified product observations.
        return ApiResponse.ok([])

    query = db.query(Product)
    if category:
        query = query.filter(Product.category.ilike(f"%{category}%"))
    products = query.limit(limit).all()
    items = [
        {
            "id": p.id,
            "trend_id": p.trend_id,
            "name": p.name,
            "category": p.category,
            "description": p.description,
            "material": p.material,
            "silhouette": p.silhouette,
            "color": p.color,
            "target_consumer": p.target_consumer,
            "opportunity_score": p.opportunity_score if p.data_status == "observed" else None,
            "ai_reasoning": p.ai_reasoning,
            "data_status": p.data_status,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }
        for p in products
    ]
    return ApiResponse.ok(items)


@router.get("/{product_id}", response_model=ApiResponse[Dict[str, Any]])
def get_product(product_id: str):
    return ApiResponse.fail(code="PRODUCT_NOT_FOUND", message="No source-attributed product observations are available.", status_code=404)


@router.get("/trend/{trend_id}", response_model=ApiResponse[List[Dict[str, Any]]])
def get_products_by_trend(trend_id: str, include_demo: bool = Query(False), db: Session = Depends(get_db)):
    trend = db.query(Trend).filter((Trend.id == trend_id) | (Trend.slug == trend_id)).first()
    if not trend:
        return ApiResponse.fail(code="TREND_NOT_FOUND", message=f"Trend '{trend_id}' not found.", status_code=404)

    if not include_demo:
        return ApiResponse.ok([])

    products = db.query(Product).filter(Product.trend_id == trend.id).all()
    items = [
        {
            "id": p.id,
            "trend_id": p.trend_id,
            "name": p.name,
            "category": p.category,
            "description": p.description,
            "material": p.material,
            "silhouette": p.silhouette,
            "color": p.color,
            "target_consumer": p.target_consumer,
            "opportunity_score": p.opportunity_score if p.data_status == "observed" else None,
            "ai_reasoning": p.ai_reasoning,
            "data_status": p.data_status,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }
        for p in products
    ]
    return ApiResponse.ok(items)


@router.post(
    "/generate",
    response_model=ApiResponse[List[Dict[str, Any]]],
    dependencies=[Depends(rate_limit_dependency(max_requests=10, window_seconds=60, scope="product_generate"))]
)
async def generate_products(
    req: ProductGenerateRequest,
    _current_user: Dict[str, Any] = Depends(get_privileged_user),
    db: Session = Depends(get_db)
):
    trend = db.query(Trend).filter(
        (Trend.id == req.trend_id) | (Trend.slug == req.trend_id),
        Trend.data_status == "observed",
    ).first()
    if not trend:
        return ApiResponse.fail(code="TREND_NOT_FOUND", message=f"Trend '{req.trend_id}' not found.", status_code=404)

    generated = await product_engine.generate_for_trend(
        db=db,
        trend_id=cast(str, trend.id),
        category=req.category,
        target_consumer=req.target_consumer
    )

    return ApiResponse.ok(generated)
