from typing import Any, Dict, List
import numpy as np


class TrendEngine:
    """Compute a weighted mean only from finite, known-channel observations."""

    CHANNEL_WEIGHTS = {
        "runway": 0.25,
        "social": 0.25,
        "search": 0.20,
        "retail": 0.15,
        "culture": 0.15,
    }

    @classmethod
    def compute_metrics(cls, signals: List[Dict[str, Any]]) -> Dict[str, Any]:
        channel_values: Dict[str, List[float]] = {}
        for signal in signals:
            source = str(signal.get("source", "")).lower()
            strength = signal.get("strength")
            if source not in cls.CHANNEL_WEIGHTS or isinstance(strength, bool):
                continue
            try:
                value = float(strength)
            except (TypeError, ValueError):
                continue
            if not np.isfinite(value):
                continue
            channel_values.setdefault(source, []).append(value)

        if not channel_values:
            return {
                "trend_score": None,
                "momentum": None,
                "velocity": None,
                "acceleration": None,
                "confidence": None,
                "cross_source_agreement": None,
                "data_status": "insufficient_data",
            }

        channel_avgs = {
            src: float(np.mean(vals)) for src, vals in channel_values.items()
        }
        weighted_sum = 0.0
        total_weight = 0.0
        for src, weight in cls.CHANNEL_WEIGHTS.items():
            if src in channel_avgs:
                weighted_sum += channel_avgs[src] * weight
                total_weight += weight

        trend_score = round(weighted_sum / total_weight, 1) if total_weight > 0 else None

        return {
            "trend_score": trend_score,
            "momentum": None,
            "velocity": None,
            "acceleration": None,
            "persistence": None,
            "source_diversity": None,
            "confidence": None,
            "cross_source_agreement": None,
            "data_status": "derived",
        }


trend_engine = TrendEngine()
