from enum import Enum
from typing import Any, Dict, Generic, Optional, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")


class DataStatus(str, Enum):
    OBSERVED = "observed"
    DERIVED = "derived"
    FORECAST = "forecast"
    AI_GENERATED = "ai_generated"
    DEMO = "demo"
    INSUFFICIENT_DATA = "insufficient_data"


class ApiError(BaseModel):
    code: str
    message: str
    details: Optional[Any] = None


class ApiResponse(BaseModel, Generic[T]):
    success: bool = True
    data: Optional[T] = None
    error: Optional[ApiError] = None
    meta: Dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def ok(cls, data: T, meta: Optional[Dict[str, Any]] = None):
        return cls(success=True, data=data, error=None, meta=meta or {})

    @classmethod
    def fail(cls, code: str, message: str, status_code: int = 400, details: Optional[Any] = None):
        return cls(
            success=False,
            data=None,
            error=ApiError(code=code, message=message, details=details),
            meta={"http_status": status_code}
        )
