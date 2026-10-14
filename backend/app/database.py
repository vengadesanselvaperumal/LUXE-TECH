import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, cast
from sqlalchemy import create_engine, Boolean, Column, String, Float, Integer, Text, DateTime, ForeignKey, Index, UniqueConstraint, func, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from app.config import get_settings

import logging
import os
from pathlib import Path

logger = logging.getLogger("luxe_tech.database")
settings = get_settings()

db_url = settings.DATABASE_URL
connect_args = {}
if db_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
    # Extract file path after sqlite:///
    raw_path = db_url.replace("sqlite:///", "")
    # If running from inside backend and path is ./backend/..., strip leading backend/
    if (raw_path.startswith("./backend/") or raw_path.startswith("backend/")) and Path("app").exists():
        raw_path = raw_path.replace("./backend/", "").replace("backend/", "")
        db_url = f"sqlite:///{raw_path}"
    
    db_file = Path(raw_path)
    if db_file.parent and str(db_file.parent) != ".":
        db_file.parent.mkdir(parents=True, exist_ok=True)

engine_kwargs: Dict[str, Any] = {"pool_pre_ping": True}
if not db_url.startswith("sqlite"):
    engine_kwargs.update({
        "pool_size": 10,
        "max_overflow": 20,
        "pool_recycle": 1800,
        "pool_timeout": 15,
    })

engine = create_engine(db_url, connect_args=connect_args, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def now_utc():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=False)
    password_hash = Column(String, nullable=True)
    role = Column(String, nullable=False, default="user", server_default=text("'user'"))
    created_at = Column(DateTime(timezone=True), default=now_utc, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), default=now_utc, onupdate=now_utc, server_default=func.now())

    saved_trends = relationship("SavedTrend", back_populates="user", cascade="all, delete-orphan")


class Trend(Base):
    __tablename__ = "trends"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    slug = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=False)
    category = Column(String, nullable=False, index=True)
    season = Column(String, nullable=True)
    description = Column(Text, nullable=False)
    image_url = Column(String, nullable=True)
    status = Column(String, nullable=False, default="emerging", server_default=text("'emerging'"))
    confidence = Column(Float, nullable=True)
    momentum = Column(Float, nullable=True)
    velocity = Column(Float, nullable=True)
    acceleration = Column(Float, nullable=True)
    data_status = Column(String, nullable=False, default="demo", server_default=text("'demo'"))
    created_at = Column(DateTime(timezone=True), default=now_utc, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), default=now_utc, onupdate=now_utc, server_default=func.now())

    signals = relationship("TrendSignal", back_populates="trend", cascade="all, delete-orphan")
    dna = relationship("TrendDNA", back_populates="trend", uselist=False, cascade="all, delete-orphan")
    collections = relationship("Collection", back_populates="trend", cascade="all, delete-orphan")
    products = relationship("Product", back_populates="trend")
    retail_signals = relationship("RetailSignal", back_populates="trend")
    forecasts = relationship("Forecast", back_populates="trend", cascade="all, delete-orphan")
    prophecies = relationship("Prophecy", back_populates="trend", cascade="all, delete-orphan")
    images = relationship("ImageRecord", back_populates="trend")


class TrendSignal(Base):
    __tablename__ = "trend_signals"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    trend_id = Column(String, ForeignKey("trends.id", ondelete="CASCADE"), nullable=False, index=True)
    source = Column(String, nullable=False)  # runway, social, search, retail, culture
    signal_type = Column(String, nullable=False)
    strength = Column(Float, nullable=False)
    direction = Column(String, nullable=False, default="up", server_default=text("'up'"))
    timestamp = Column(DateTime(timezone=True), default=now_utc, server_default=func.now())
    metadata_json = Column(Text, default="{}", server_default=text("'{}'"))  # Stored as JSON string
    data_status = Column(String, nullable=False, default="demo", server_default=text("'demo'"))

    trend = relationship("Trend", back_populates="signals")

    @property
    def signal_metadata(self) -> Dict[str, Any]:
        metadata = cast(str, self.metadata_json)
        if not metadata:
            return {}
        try:
            return json.loads(metadata)
        except Exception:
            return {}

    @signal_metadata.setter
    def signal_metadata(self, value: Dict[str, Any]):
        self.metadata_json = json.dumps(value)


class TrendDNA(Base):
    __tablename__ = "trend_dna"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    trend_id = Column(String, ForeignKey("trends.id", ondelete="CASCADE"), nullable=False, unique=True)
    colors_json = Column(Text, default="[]", server_default=text("'[]'"))
    materials_json = Column(Text, default="[]", server_default=text("'[]'"))
    textures_json = Column(Text, default="[]", server_default=text("'[]'"))
    silhouettes_json = Column(Text, default="[]", server_default=text("'[]'"))
    patterns_json = Column(Text, default="[]", server_default=text("'[]'"))
    visual_description = Column(Text, nullable=True)
    ai_interpretation = Column(Text, nullable=True)
    data_status = Column(String, nullable=False, default="demo", server_default=text("'demo'"))
    created_at = Column(DateTime(timezone=True), default=now_utc, server_default=func.now())

    trend = relationship("Trend", back_populates="dna")

    def to_dict(self) -> Dict[str, Any]:
        colors_json = cast(str, self.colors_json)
        materials_json = cast(str, self.materials_json)
        textures_json = cast(str, self.textures_json)
        silhouettes_json = cast(str, self.silhouettes_json)
        patterns_json = cast(str, self.patterns_json)
        created_at = cast(Optional[datetime], self.created_at)
        return {
            "id": self.id,
            "trend_id": self.trend_id,
            "colors": json.loads(colors_json or "[]"),
            "materials": json.loads(materials_json or "[]"),
            "textures": json.loads(textures_json or "[]"),
            "silhouettes": json.loads(silhouettes_json or "[]"),
            "patterns": json.loads(patterns_json or "[]"),
            "visual_description": self.visual_description,
            "ai_interpretation": self.ai_interpretation,
            "data_status": self.data_status,
            "created_at": created_at.isoformat() if created_at is not None else None,
        }


class ImageRecord(Base):
    __tablename__ = "images"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    trend_id = Column(String, ForeignKey("trends.id", ondelete="SET NULL"), nullable=True, index=True)
    storage_path = Column(String, nullable=False)
    public_url = Column(String, nullable=False)
    width = Column(Integer, nullable=False)
    height = Column(Integer, nullable=False)
    dominant_colors_json = Column(Text, default="[]", server_default=text("'[]'"))
    contrast = Column(Float, nullable=False, default=0.0, server_default=text("0.0"))
    brightness = Column(Float, nullable=False, default=0.0, server_default=text("0.0"))
    saturation = Column(Float, nullable=False, default=0.0, server_default=text("0.0"))
    edge_density = Column(Float, nullable=False, default=0.0, server_default=text("0.0"))
    data_status = Column(String, nullable=False, default="demo", server_default=text("'demo'"))
    created_at = Column(DateTime(timezone=True), default=now_utc, server_default=func.now())

    trend = relationship("Trend", back_populates="images")

    @property
    def dominant_colors(self) -> List[Dict[str, Any]]:
        colors_json = cast(str, self.dominant_colors_json)
        try:
            return json.loads(colors_json) if colors_json else []
        except Exception:
            return []


class Collection(Base):
    __tablename__ = "collections"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    trend_id = Column(String, ForeignKey("trends.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    color_palette_json = Column(Text, default="[]", server_default=text("'[]'"))
    materials_json = Column(Text, default="[]", server_default=text("'[]'"))
    textures_json = Column(Text, default="[]", server_default=text("'[]'"))
    silhouettes_json = Column(Text, default="[]", server_default=text("'[]'"))
    patterns_json = Column(Text, default="[]", server_default=text("'[]'"))
    product_opportunities_json = Column(Text, default="[]", server_default=text("'[]'"))
    data_status = Column(String, nullable=False, default="demo", server_default=text("'demo'"))
    created_at = Column(DateTime(timezone=True), default=now_utc, server_default=func.now())

    trend = relationship("Trend", back_populates="collections")


class Product(Base):
    __tablename__ = "products"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    trend_id = Column(String, ForeignKey("trends.id", ondelete="SET NULL"), nullable=True, index=True)
    name = Column(String, nullable=False)
    category = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    material = Column(String, nullable=False)
    silhouette = Column(String, nullable=False)
    color = Column(String, nullable=False)
    target_consumer = Column(String, nullable=False)
    opportunity_score = Column(Float, nullable=False, default=75.0, server_default=text("75.0"))
    ai_reasoning = Column(Text, nullable=True)
    data_status = Column(String, nullable=False, default="demo", server_default=text("'demo'"))
    created_at = Column(DateTime(timezone=True), default=now_utc, server_default=func.now())

    trend = relationship("Trend", back_populates="products")


class RetailSignal(Base):
    __tablename__ = "retail_signals"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    trend_id = Column(String, ForeignKey("trends.id", ondelete="SET NULL"), nullable=True, index=True)
    region = Column(String, nullable=False)
    category = Column(String, nullable=False)
    demand = Column(Float, nullable=False)
    growth = Column(Float, nullable=False)
    consumer_signal = Column(Text, nullable=False)
    timestamp = Column(DateTime(timezone=True), default=now_utc, server_default=func.now())
    data_status = Column(String, nullable=False, default="demo", server_default=text("'demo'"))

    trend = relationship("Trend", back_populates="retail_signals")


class Forecast(Base):
    __tablename__ = "forecasts"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    trend_id = Column(String, ForeignKey("trends.id", ondelete="CASCADE"), nullable=False, index=True)
    model = Column(String, nullable=False)  # moving_average, simple_exponential_smoothing, holt_winters, linear_regression
    horizon = Column(String, nullable=False, default="3_months", server_default=text("'3_months'"))
    forecast_value = Column(Float, nullable=False)
    backtest_accuracy = Column("confidence", Float, nullable=True)
    training_start = Column(DateTime(timezone=True), nullable=True)
    training_end = Column(DateTime(timezone=True), nullable=True)
    data_status = Column(String, nullable=False, default="demo", server_default=text("'demo'"))
    created_at = Column(DateTime(timezone=True), default=now_utc, server_default=func.now())

    trend = relationship("Trend", back_populates="forecasts")


class Prophecy(Base):
    __tablename__ = "prophecy"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    trend_id = Column(String, ForeignKey("trends.id", ondelete="CASCADE"), nullable=False, index=True)
    stage = Column(String, nullable=False)  # current, emerging, accelerating, mainstream, next
    forecast = Column(Text, nullable=False)
    evidence_json = Column(Text, default="[]", server_default=text("'[]'"))
    opportunity = Column(Text, nullable=False)
    risk = Column(Text, nullable=False)
    confidence = Column(Float, nullable=True)
    data_status = Column(String, nullable=False, default="demo", server_default=text("'demo'"))
    created_at = Column(DateTime(timezone=True), default=now_utc, server_default=func.now())

    trend = relationship("Trend", back_populates="prophecies")


class SavedTrend(Base):
    __tablename__ = "saved_trends"
    __table_args__ = (UniqueConstraint("user_id", "trend_id", name="uq_saved_trends_user_trend"),)

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    trend_id = Column(String, ForeignKey("trends.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=now_utc, server_default=func.now())

    user = relationship("User", back_populates="saved_trends")
    trend = relationship("Trend")


class TrendSubmission(Base):
    __tablename__ = "trend_submissions"
    __table_args__ = (
        UniqueConstraint("normalized_source_url", name="uq_trend_submissions_normalized_source_url"),
        Index("idx_trend_submissions_user_created", "user_id", "submitted_at"),
    )

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    platform = Column(String, nullable=False)
    source_url = Column(Text, nullable=False)
    normalized_source_url = Column(Text, nullable=False)
    observation = Column(Text, nullable=False)
    product_type = Column(String, nullable=False)
    category = Column(String, nullable=True)
    color = Column(String, nullable=True)
    material = Column(String, nullable=True)
    silhouette = Column(String, nullable=True)
    observed_at = Column(DateTime(timezone=True), nullable=True)
    explanation = Column(Text, nullable=True)
    image_storage_path = Column(Text, nullable=True)
    rights_confirmed = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    status = Column(String, nullable=False, default="pending", server_default=text("'pending'"))
    review_note = Column(Text, nullable=True)
    submitted_at = Column(DateTime(timezone=True), default=now_utc, server_default=func.now())


def init_db():
    if engine.dialect.name != "sqlite":
        inspector = inspect(engine)
        existing_tables = set(inspector.get_table_names())
        core_tables = {
            table_name for table_name in Base.metadata.tables
            if table_name != "trend_submissions"
        }
        missing_tables = core_tables - existing_tables
        target_tables = list(core_tables & existing_tables)
        existing_columns_by_table: Dict[str, set] = {}
        if target_tables:
            try:
                with engine.connect() as conn:
                    col_rows = conn.execute(
                        text("""
                            SELECT table_name, column_name 
                            FROM information_schema.columns 
                            WHERE table_schema = 'public' 
                              AND table_name = ANY(:tables)
                        """),
                        {"tables": target_tables}
                    ).fetchall()
                    for t_name, c_name in col_rows:
                        existing_columns_by_table.setdefault(t_name, set()).add(c_name)
            except Exception:
                for table_name in target_tables:
                    existing_columns_by_table[table_name] = {
                        item["name"] for item in inspector.get_columns(table_name)
                    }

        missing_columns = {
            table_name: sorted(
                column.name
                for column in table.columns
                if column.name not in existing_columns_by_table.get(table_name, set())
            )
            for table_name, table in Base.metadata.tables.items()
            if table_name in target_tables
        }
        missing_columns = {
            table_name: columns
            for table_name, columns in missing_columns.items()
            if columns
        }
        if missing_tables or missing_columns:
            details = []
            if missing_tables:
                details.append(f"missing tables: {', '.join(sorted(missing_tables))}")
            if missing_columns:
                details.append(
                    "missing columns: "
                    + "; ".join(
                        f"{table_name} ({', '.join(columns)})"
                        for table_name, columns in sorted(missing_columns.items())
                    )
                )
            raise RuntimeError(
                "PostgreSQL schema is incomplete; no tables were created or changed. "
                "Apply and verify the reviewed Supabase migrations first ("
                + " | ".join(details)
                + ")."
            )
        if "trend_submissions" not in existing_tables:
            logger.info("Extension table 'trend_submissions' pending migration; will activate upon migration.")
        return

    Base.metadata.create_all(bind=engine)
    with engine.begin() as connection:
        tables = set(inspect(connection).get_table_names())
        for table in ("users", "trend_dna", "images", "collections"):
            if table not in tables:
                continue
            columns = {column["name"] for column in inspect(connection).get_columns(table)}
            new_column = "password_hash" if table == "users" else "data_status"
            if new_column not in columns:
                column_type = "VARCHAR" if table == "users" else "VARCHAR NOT NULL DEFAULT 'demo'"
                connection.exec_driver_sql(
                    f"ALTER TABLE {table} ADD COLUMN {new_column} {column_type}"
                )


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
