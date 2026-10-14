from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from app.database import RetailSignal


class RetailEngine:
    @classmethod
    def get_dashboard_metrics(cls, db: Session, trend_id: Optional[str] = None) -> Dict[str, Any]:
        if trend_id:
            return {
                "market": {
                    "signal_records": 0,
                    "retailers": None,
                    "assortment_growth": None,
                    "discount_frequency": None,
                    "data_status": "insufficient_data",
                },
                "regions": [],
                "categories": [],
                "signals": [],
                "data_status": "insufficient_data",
                "message": (
                    "Retail signal records have no source identity or source URL, so they cannot "
                    "be independently verified and are excluded."
                ),
            }

        query = db.query(RetailSignal)
        signals = query.all()

        if not signals:
            return {
                "market": {
                    "signal_records": 0,
                    "retailers": None,
                    "assortment_growth": None,
                    "discount_frequency": None,
                    "data_status": "insufficient_data",
                },
                "regions": [],
                "categories": [],
                "signals": [],
                "data_status": "insufficient_data",
                "message": "No retail signals recorded.",
            }

        # Aggregate by region
        by_region: Dict[str, List[RetailSignal]] = {}
        for s in signals:
            by_region.setdefault(s.region, []).append(s)

        regions_data = []
        for reg, reg_signals in sorted(by_region.items()):
            avg_demand = round(sum(s.demand for s in reg_signals) / len(reg_signals), 1)
            avg_growth = round(sum(s.growth for s in reg_signals) / len(reg_signals), 1)
            regions_data.append({
                "region": reg,
                "demand": avg_demand,
                "growth": avg_growth,
                "signal_count": len(reg_signals),
                "data_status": "demo",
            })

        # Aggregate by category
        by_category: Dict[str, List[RetailSignal]] = {}
        for s in signals:
            by_category.setdefault(s.category, []).append(s)

        categories_data = []
        for cat, cat_signals in sorted(by_category.items()):
            avg_demand = round(sum(s.demand for s in cat_signals) / len(cat_signals), 1)
            avg_growth = round(sum(s.growth for s in cat_signals) / len(cat_signals), 1)
            categories_data.append({
                "category": cat,
                "demand": avg_demand,
                "growth": avg_growth,
                "signal_count": len(cat_signals),
                "data_status": "demo",
            })

        # Individual signal records
        signals_data = [
            {
                "id": s.id,
                "trend_id": s.trend_id,
                "region": s.region,
                "category": s.category,
                "demand": s.demand,
                "growth": s.growth,
                "consumer_signal": s.consumer_signal,
                "timestamp": s.timestamp.isoformat() if s.timestamp else None,
                "data_status": s.data_status,
            }
            for s in signals[:20]
        ]

        total_demand = round(sum(s.demand for s in signals) / len(signals), 1)
        total_growth = round(sum(s.growth for s in signals) / len(signals), 1)

        return {
            "market": {
                "signal_records": len(signals),
                "average_demand": total_demand,
                "average_growth": total_growth,
                "data_status": "demo",
            },
            "regions": regions_data,
            "categories": categories_data,
            "signals": signals_data,
            "data_status": "demo",
            "message": "Retail benchmark data is for demonstration and strategic planning purposes.",
        }


retail_engine = RetailEngine()
