import json
import uuid
from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import Collection, Trend, TrendDNA, TrendSignal, get_db
from app.schemas.common import ApiResponse
from app.services.gemini_service import gemini_service
from app.utils.rate_limit import rate_limit_dependency
from app.utils.security import get_current_user, get_privileged_user

router = APIRouter(prefix="/collections", tags=["collections"])


class GenerateCollectionRequest(BaseModel):
    trend_id: str


@router.get("/{trend_id}", response_model=ApiResponse[Dict[str, Any]])
def get_collection_for_trend(trend_id: str, db: Session = Depends(get_db)):
    trend = db.query(Trend).filter((Trend.id == trend_id) | (Trend.slug == trend_id)).first()
    if not trend:
        raise HTTPException(status_code=404, detail=f"Trend '{trend_id}' not found.")

    collection = db.query(Collection).filter(Collection.trend_id == trend.id).first()
    if not collection:
        raise HTTPException(
            status_code=404,
            detail=f"Collection for trend '{trend.name}' has not been generated yet."
        )

    return ApiResponse.ok({
        "id": collection.id,
        "trend_id": collection.trend_id,
        "name": collection.name,
        "description": collection.description,
        "color_palette": json.loads(collection.color_palette_json or "[]"),
        "materials": json.loads(collection.materials_json or "[]"),
        "textures": json.loads(collection.textures_json or "[]"),
        "silhouettes": json.loads(collection.silhouettes_json or "[]"),
        "patterns": json.loads(collection.patterns_json or "[]"),
        "product_opportunities": json.loads(collection.product_opportunities_json or "[]"),
        "created_at": collection.created_at.isoformat() if collection.created_at else None,
        "data_status": collection.data_status
    })


@router.post(
    "/generate",
    response_model=ApiResponse[Dict[str, Any]],
    dependencies=[Depends(rate_limit_dependency(max_requests=10, window_seconds=60, scope="collection_generate"))]
)
async def generate_collection(
    req: GenerateCollectionRequest,
    current_user: Dict[str, Any] = Depends(get_privileged_user),
    db: Session = Depends(get_db)
):
    trend = db.query(Trend).filter((Trend.id == req.trend_id) | (Trend.slug == req.trend_id)).first()
    if not trend:
        return ApiResponse.fail(code="TREND_NOT_FOUND", message=f"Trend '{req.trend_id}' not found.", status_code=404)

    signals = db.query(TrendSignal).filter(TrendSignal.trend_id == trend.id).all()
    signal_dict = {s.source: float(s.strength) for s in signals}

    analysis = await gemini_service.analyze_trend(trend.name, trend.category, trend.season, signal_dict)
    visual_dna = analysis.get("visual_dna", {})

    collection = db.query(Collection).filter(Collection.trend_id == trend.id).first()
    if not collection:
        collection = Collection(id=str(uuid.uuid4()), trend_id=trend.id, name=f"{trend.name} Capsule", description="")
        db.add(collection)

    collection.name = f"{trend.name} Collection"
    collection.description = analysis.get("summary", "")
    collection.color_palette_json = json.dumps(visual_dna.get("colors", []))
    collection.materials_json = json.dumps(visual_dna.get("materials", []))
    collection.textures_json = json.dumps(visual_dna.get("textures", []))
    collection.silhouettes_json = json.dumps(visual_dna.get("silhouettes", []))
    collection.patterns_json = json.dumps(visual_dna.get("patterns", []))
    collection.product_opportunities_json = json.dumps(analysis.get("product_opportunities", []))
    collection.data_status = analysis.get("data_status", "demo")

    db.commit()

    return ApiResponse.ok({
        "id": collection.id,
        "trend_id": collection.trend_id,
        "name": collection.name,
        "description": collection.description,
        "color_palette": visual_dna.get("colors", []),
        "materials": visual_dna.get("materials", []),
        "textures": visual_dna.get("textures", []),
        "silhouettes": visual_dna.get("silhouettes", []),
        "patterns": visual_dna.get("patterns", []),
        "product_opportunities": analysis.get("product_opportunities", []),
        "data_status": collection.data_status
    })
