from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from app.schemas.common import DataStatus


class SignalItem(BaseModel):
    id: Optional[str] = None
    trend_id: Optional[str] = None
    source: str
    signal_type: str
    strength: float
    direction: str = "up"
    timestamp: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    data_status: DataStatus = DataStatus.DEMO


class TrendDNAItem(BaseModel):
    id: Optional[str] = None
    trend_id: Optional[str] = None
    colors: List[Any] = Field(default_factory=list)
    materials: List[str] = Field(default_factory=list)
    textures: List[str] = Field(default_factory=list)
    silhouettes: List[str] = Field(default_factory=list)
    patterns: List[str] = Field(default_factory=list)
    visual_description: Optional[str] = None
    ai_interpretation: Optional[str] = None


class TrendBase(BaseModel):
    slug: str
    name: str
    category: str
    season: Optional[str] = None
    description: str
    image_url: Optional[str] = None
    status: str = "emerging"
    confidence: Optional[float] = None
    momentum: Optional[float] = None
    velocity: Optional[float] = None
    acceleration: Optional[float] = None
    data_status: DataStatus = DataStatus.DEMO


class TrendCreate(TrendBase):
    pass


class TrendResponse(TrendBase):
    id: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class TrendDetailResponse(TrendResponse):
    signals: List[SignalItem] = Field(default_factory=list)
    dna: Optional[TrendDNAItem] = None
    cross_source_agreement: Optional[float] = None
    trend_score: Optional[float] = None


class LiveSignalsResponse(BaseModel):
    runway: Optional[float] = None
    social: Optional[float] = None
    search: Optional[float] = None
    retail: Optional[float] = None
    culture: Optional[float] = None
    data_status: DataStatus = DataStatus.OBSERVED
    last_updated: datetime = Field(default_factory=datetime.utcnow)
