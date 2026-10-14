from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from app.database import Trend, TrendDNA
from app.services.gemini_service import gemini_service


class ProductEngine:
    @classmethod
    async def generate_for_trend(
        cls,
        db: Session,
        trend_id: str,
        category: Optional[str] = None,
        target_consumer: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        trend = db.query(Trend).filter(Trend.id == trend_id).first()
        if not trend:
            return []

        dna_record = db.query(TrendDNA).filter(TrendDNA.trend_id == trend_id).first()
        visual_dna = dna_record.to_dict() if dna_record else {}

        consumer = target_consumer or "Not specified"

        concepts = await gemini_service.generate_product_opportunities(
            trend_name=trend.name,
            visual_dna=visual_dna,
            target_consumer=consumer
        )

        return [
            {
                "trend_id": trend.id,
                "name": item["name"],
                "category": category or item.get("category", "Ready-to-Wear"),
                "description": item["description"],
                "material": item["material"],
                "silhouette": item["silhouette"],
                "color": (
                    item["color"].get("hex", "")
                    if isinstance(item["color"], dict)
                    else str(item["color"])
                ),
                "target_consumer": item["target_consumer"],
                "design_rationale": item["design_rationale"],
                "data_status": "ai_generated_concept",
            }
            for item in concepts
        ]


product_engine = ProductEngine()
