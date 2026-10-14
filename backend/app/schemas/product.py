from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from app.schemas.common import DataStatus


class ProductBase(BaseModel):
    trend_id: Optional[str] = None
    name: str
    category: str
    description: str
    material: str
    silhouette: str
    color: str
    target_consumer: str
    opportunity_score: float = 75.0
    ai_reasoning: Optional[str] = None
    data_status: DataStatus = DataStatus.DEMO


class ProductCreate(ProductBase):
    pass


class ProductResponse(ProductBase):
    id: str
    created_at: Optional[datetime] = None


class ProductGenerateRequest(BaseModel):
    trend_id: str
    category: Optional[str] = None
    target_consumer: Optional[str] = None
