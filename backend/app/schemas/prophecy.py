from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from app.schemas.common import DataStatus


class ProphecyStageItem(BaseModel):
    stage: str  # current, emerging, accelerating, mainstream, next
    forecast: str
    evidence: List[str] = Field(default_factory=list)
    opportunity: str
    risk: str
    confidence: float
    data_status: DataStatus = DataStatus.AI_GENERATED


class ProphecyResponse(BaseModel):
    id: Optional[str] = None
    trend_id: str
    current_stage: str
    timeline: List[ProphecyStageItem] = Field(default_factory=list)
    scenario_analysis: Dict[str, Any] = Field(default_factory=dict)
    data_status: DataStatus = DataStatus.AI_GENERATED
    created_at: Optional[datetime] = None


class ProphecyGenerateRequest(BaseModel):
    trend_id: str
    custom_context: Optional[str] = None
