from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, cast
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from app.database import TrendSignal


def get_verified_signal_observations(
    db: Session, trend_id: Optional[str] = None
) -> Tuple[List[Dict[str, Any]], List[TrendSignal]]:
    query = db.query(TrendSignal).filter(
        TrendSignal.data_status == "observed",
        TrendSignal.timestamp.is_not(None),
    )
    if trend_id is not None:
        query = query.filter(TrendSignal.trend_id == trend_id)
    signals = query.order_by(TrendSignal.timestamp.asc()).all()
    observations: List[Dict[str, Any]] = []
    verified_signals: List[TrendSignal] = []
    for signal in signals:
        timestamp = cast(Optional[datetime], signal.timestamp)
        if timestamp is None:
            continue
        metadata = signal.signal_metadata
        if signal.signal_type == "news_derived" or metadata.get("signal_kind") == "news_derived":
            continue
        source_name = metadata.get("source_name")
        fetched_at = metadata.get("fetched_at")
        source_url = metadata.get("source_url")
        if not isinstance(fetched_at, str):
            continue
        try:
            fetched_datetime = datetime.fromisoformat(fetched_at.replace("Z", "+00:00"))
        except ValueError:
            continue
        if fetched_datetime.tzinfo is None:
            continue
        parsed_source_url = urlparse(source_url) if isinstance(source_url, str) else None
        is_user_upload = (
            source_name == "user_upload"
            and metadata.get("quality") == "user_upload"
        )
        is_publisher_source = (
            isinstance(source_name, str)
            and bool(source_name.strip())
            and parsed_source_url is not None
            and parsed_source_url.scheme == "https"
            and bool(parsed_source_url.hostname)
        )
        if not fetched_at or not (is_user_upload or is_publisher_source):
            continue
        observations.append({
            "strength": cast(float, signal.strength),
            "timestamp": timestamp.isoformat(),
            "source": cast(str, signal.source),
            "source_name": source_name,
            "source_url": source_url,
            "fetched_at": fetched_at,
        })
        verified_signals.append(signal)
    return observations, verified_signals
