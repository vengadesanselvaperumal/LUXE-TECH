from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from app.schemas.common import DataStatus


class RetailSignalBase(BaseModel):
    trend_id: Optional[str] = None
    region: str
    category: str
    demand: float
    growth: float
    consumer_signal: str
    timestamp: Optional[datetime] = None
    data_status: DataStatus = DataStatus.DEMO


class RetailSignalResponse(RetailSignalBase):
    id: str


class RetailMarketOverview(BaseModel):
    signal_records: int = 0
    retailers: Optional[int] = None
    assortment_growth: Optional[float] = None
    discount_frequency: Optional[float] = None
    data_status: DataStatus = DataStatus.DEMO


class RetailDashboardResponse(BaseModel):
    market: RetailMarketOverview = Field(default_factory=RetailMarketOverview)
    regions: List[Dict[str, Any]] = Field(default_factory=list)
    categories: List[Dict[str, Any]] = Field(default_factory=list)
    signals: List[RetailSignalResponse] = Field(default_factory=list)
    data_status: DataStatus = DataStatus.DEMO
