import asyncio

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.database import Base, Trend
from app.routers.prophecy import get_prophecy


def test_prophecy_does_not_claim_a_stage_without_verified_evidence():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    try:
        with Session(engine) as db:
            db.add(
                Trend(
                    id="audit-trend",
                    slug="audit-trend",
                    name="Audit trend",
                    category="Fashion",
                    description="Isolated test fixture.",
                    status="emerging",
                    data_status="demo",
                )
            )
            db.commit()

            response = asyncio.run(get_prophecy("audit-trend", db))

            assert response.data is not None
            assert response.data["current_stage"] is None
            assert response.data["timeline"] == []
            assert response.data["status"] == "insufficient_data"
            assert "0 verified observations" in response.data["message"]
    finally:
        Base.metadata.drop_all(bind=engine)
        engine.dispose()
