from typing import Any, Dict, List
from sqlalchemy import or_
from sqlalchemy.orm import Session
from app.database import Collection, Product, Prophecy, RetailSignal, Trend


class SearchEngine:
    @classmethod
    def search_all(cls, db: Session, query: str) -> Dict[str, List[Dict[str, Any]]]:
        if not query or len(query.strip()) < 2:
            return {"trends": [], "products": [], "collections": [], "retail": [], "prophecy": []}

        pattern = f"%{query.strip()}%"

        # 1. Trends
        trends = db.query(Trend).filter(
            Trend.data_status == "observed",
            or_(Trend.name.ilike(pattern), Trend.category.ilike(pattern), Trend.description.ilike(pattern))
        ).limit(6).all()

        # 2. Products
        products = db.query(Product).filter(
            Product.data_status == "observed",
            or_(Product.name.ilike(pattern), Product.category.ilike(pattern), Product.material.ilike(pattern), Product.color.ilike(pattern))
        ).limit(6).all()

        # 3. Collections
        collections = db.query(Collection).filter(
            Collection.data_status == "observed",
            or_(Collection.name.ilike(pattern), Collection.description.ilike(pattern))
        ).limit(6).all()

        # 4. Retail
        retail = db.query(RetailSignal).filter(
            RetailSignal.data_status == "observed",
            or_(RetailSignal.region.ilike(pattern), RetailSignal.category.ilike(pattern), RetailSignal.consumer_signal.ilike(pattern))
        ).limit(6).all()

        # 5. Prophecy
        prophecies = db.query(Prophecy).filter(
            Prophecy.data_status == "ai_generated",
            or_(Prophecy.stage.ilike(pattern), Prophecy.forecast.ilike(pattern), Prophecy.opportunity.ilike(pattern))
        ).limit(6).all()

        return {
            "trends": [
                {
                    "type": "TREND",
                    "id": t.id,
                    "slug": t.slug,
                    "name": t.name,
                    "category": t.category,
                    "path": f"/trend/{t.slug}",
                    "data_status": t.data_status,
                }
                for t in trends
            ],
            "products": [
                {
                    "type": "PRODUCT",
                    "id": p.id,
                    "trend_id": p.trend_id,
                    "name": p.name,
                    "category": p.category,
                    "material": p.material,
                    "path": f"/product",
                    "data_status": p.data_status,
                }
                for p in products
            ],
            "collections": [
                {
                    "type": "COLLECTION",
                    "id": c.id,
                    "trend_id": c.trend_id,
                    "name": c.name,
                    "path": f"/trend",
                }
                for c in collections
            ],
            "retail": [
                {
                    "type": "RETAIL",
                    "id": r.id,
                    "trend_id": r.trend_id,
                    "name": f"{r.region} - {r.category}",
                    "demand": r.demand,
                    "path": f"/retail",
                    "data_status": r.data_status,
                }
                for r in retail
            ],
            "prophecy": [
                {
                    "type": "PROPHECY",
                    "id": pr.id,
                    "trend_id": pr.trend_id,
                    "name": f"{pr.stage.upper()}: {pr.forecast[:45]}...",
                    "path": f"/prophecy",
                    "data_status": pr.data_status,
                }
                for pr in prophecies
            ],
        }


search_engine = SearchEngine()
