from typing import Any, Dict
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.common import ApiResponse
from app.services.search_engine import search_engine

router = APIRouter(prefix="/search", tags=["search"])


@router.get("", response_model=ApiResponse[Dict[str, Any]])
def search(q: str = Query("", description="Search query string"), db: Session = Depends(get_db)):
    results = search_engine.search_all(db=db, query=q)
    return ApiResponse.ok(results)
