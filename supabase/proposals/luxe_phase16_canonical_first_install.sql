-- ============================================================================
-- LUXE.TECH — Phase 16 Canonical First-Install Application Schema
-- Location: supabase/proposals/luxe_phase16_canonical_first_install.sql
-- Status: REVIEWED PROPOSAL (Offline Review Only — Not Deployed)
--
-- TARGET: Dedicated LUXE.TECH Supabase Project (SQL Editor First Install)
--
-- GOVERNANCE & SAFETY INVARIANTS:
-- 1. NO destructive commands: zero DROP TABLE, TRUNCATE, or CASCADE statements.
-- 2. Fresh-install only: Migration 002 (legacy schema alignment) is excluded.
-- 3. Row Level Security is ENABLED on all 11 application tables.
-- 4. PostgREST fail-closed: REVOKE ALL from anon and authenticated roles.
-- 5. Least-Privilege Runtime: Role luxe_app_user is provisioned with
--    NOSUPERUSER, NOCREATEDB, NOREPLICATION, and NOBYPASSRLS.
-- 6. Explicit Runtime Policies: One policy per table granted to luxe_app_user.
-- 7. Storage bucket creation is SEPARATED from table creation.
-- 8. Relational images.user_id is deferred (matches 13-column ImageRecord).
-- ============================================================================

BEGIN;

-- ============================================================================
-- 1. RUNTIME DATABASE ROLE PROVISIONING
-- ============================================================================
-- Creates the least-privilege backend runtime role if it does not already exist.
-- IMPORTANT: Prior to execution in production, replace 'REPLACE_WITH_STRONG_PASSWORD'
-- with a high-entropy secret string.
-- ============================================================================
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'luxe_app_user') THEN
        CREATE ROLE luxe_app_user WITH
            LOGIN
            PASSWORD 'REPLACE_WITH_STRONG_PASSWORD'
            NOSUPERUSER
            NOCREATEDB
            NOREPLICATION
            NOBYPASSRLS;
    END IF;
END
$$;

-- Grant schema-level usage to runtime role
GRANT USAGE ON SCHEMA public TO luxe_app_user;

-- ============================================================================
-- 2. CORE APPLICATION TABLES (DEPENDENCY ORDER)
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 2.1 USERS (Application accounts & profile data)
-- ----------------------------------------------------------------------------
-- Note on password_hash: Kept nullable initially to support bootstrap and demo
-- seed account. Enforce NOT NULL in production after credentials are set.
-- ----------------------------------------------------------------------------
CREATE TABLE public.users (
    id VARCHAR PRIMARY KEY,
    email VARCHAR NOT NULL,
    name VARCHAR NOT NULL,
    password_hash VARCHAR,
    role VARCHAR NOT NULL DEFAULT 'user',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);
CREATE UNIQUE INDEX ix_users_email ON public.users (email);

-- ----------------------------------------------------------------------------
-- 2.2 TRENDS (Core fashion trend intelligence catalog)
-- ----------------------------------------------------------------------------
CREATE TABLE public.trends (
    id VARCHAR PRIMARY KEY,
    slug VARCHAR NOT NULL,
    name VARCHAR NOT NULL,
    category VARCHAR NOT NULL,
    season VARCHAR NOT NULL DEFAULT 'SS 2027',
    description TEXT NOT NULL,
    image_url VARCHAR,
    status VARCHAR NOT NULL DEFAULT 'emerging',
    confidence DOUBLE PRECISION NOT NULL DEFAULT 80.0,
    momentum DOUBLE PRECISION NOT NULL DEFAULT 25.0,
    velocity DOUBLE PRECISION NOT NULL DEFAULT 15.0,
    acceleration DOUBLE PRECISION NOT NULL DEFAULT 5.0,
    data_status VARCHAR NOT NULL DEFAULT 'demo',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);
CREATE UNIQUE INDEX ix_trends_slug ON public.trends (slug);
CREATE INDEX ix_trends_category ON public.trends (category);

-- ----------------------------------------------------------------------------
-- 2.3 TREND_SIGNALS (Multi-channel market data points)
-- ----------------------------------------------------------------------------
CREATE TABLE public.trend_signals (
    id VARCHAR PRIMARY KEY,
    trend_id VARCHAR NOT NULL REFERENCES public.trends(id) ON DELETE CASCADE,
    source VARCHAR NOT NULL,
    signal_type VARCHAR NOT NULL,
    strength DOUBLE PRECISION NOT NULL,
    direction VARCHAR NOT NULL DEFAULT 'up',
    timestamp TIMESTAMPTZ DEFAULT now(),
    metadata_json TEXT DEFAULT '{}',
    data_status VARCHAR NOT NULL DEFAULT 'demo'
);
CREATE INDEX ix_trend_signals_trend_id ON public.trend_signals (trend_id);

-- ----------------------------------------------------------------------------
-- 2.4 TREND_DNA (Visual, material, and palette DNA profile)
-- ----------------------------------------------------------------------------
CREATE TABLE public.trend_dna (
    id VARCHAR PRIMARY KEY,
    trend_id VARCHAR NOT NULL UNIQUE REFERENCES public.trends(id) ON DELETE CASCADE,
    colors_json TEXT DEFAULT '[]',
    materials_json TEXT DEFAULT '[]',
    textures_json TEXT DEFAULT '[]',
    silhouettes_json TEXT DEFAULT '[]',
    patterns_json TEXT DEFAULT '[]',
    visual_description TEXT,
    ai_interpretation TEXT,
    data_status VARCHAR NOT NULL DEFAULT 'demo',
    created_at TIMESTAMPTZ DEFAULT now()
);

-- ----------------------------------------------------------------------------
-- 2.5 IMAGES (Computer vision extraction & image asset catalog)
-- ----------------------------------------------------------------------------
-- Exactly matches 13 columns of SQLAlchemy ImageRecord. User attribution
-- is namespaced in storage_path ('{user_id}/{uuid}_{filename}').
-- Relational user_id addition is deferred to a future coordinated migration.
-- ----------------------------------------------------------------------------
CREATE TABLE public.images (
    id VARCHAR PRIMARY KEY,
    trend_id VARCHAR REFERENCES public.trends(id) ON DELETE SET NULL,
    storage_path VARCHAR NOT NULL,
    public_url VARCHAR NOT NULL,
    width INTEGER NOT NULL,
    height INTEGER NOT NULL,
    dominant_colors_json TEXT DEFAULT '[]',
    contrast DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    brightness DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    saturation DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    edge_density DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    data_status VARCHAR NOT NULL DEFAULT 'demo',
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX ix_images_trend_id ON public.images (trend_id);

-- ----------------------------------------------------------------------------
-- 2.6 COLLECTIONS (Editorial design capsules synthesized for trends)
-- ----------------------------------------------------------------------------
CREATE TABLE public.collections (
    id VARCHAR PRIMARY KEY,
    trend_id VARCHAR NOT NULL REFERENCES public.trends(id) ON DELETE CASCADE,
    name VARCHAR NOT NULL,
    description TEXT NOT NULL,
    color_palette_json TEXT DEFAULT '[]',
    materials_json TEXT DEFAULT '[]',
    textures_json TEXT DEFAULT '[]',
    silhouettes_json TEXT DEFAULT '[]',
    patterns_json TEXT DEFAULT '[]',
    product_opportunities_json TEXT DEFAULT '[]',
    data_status VARCHAR NOT NULL DEFAULT 'demo',
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX ix_collections_trend_id ON public.collections (trend_id);

-- ----------------------------------------------------------------------------
-- 2.7 PRODUCTS (Commercial product opportunities derived from trends)
-- ----------------------------------------------------------------------------
CREATE TABLE public.products (
    id VARCHAR PRIMARY KEY,
    trend_id VARCHAR REFERENCES public.trends(id) ON DELETE SET NULL,
    name VARCHAR NOT NULL,
    category VARCHAR NOT NULL,
    description TEXT NOT NULL,
    material VARCHAR NOT NULL,
    silhouette VARCHAR NOT NULL,
    color VARCHAR NOT NULL,
    target_consumer VARCHAR NOT NULL,
    opportunity_score DOUBLE PRECISION NOT NULL DEFAULT 75.0,
    ai_reasoning TEXT,
    data_status VARCHAR NOT NULL DEFAULT 'demo',
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX ix_products_trend_id ON public.products (trend_id);

-- ----------------------------------------------------------------------------
-- 2.8 RETAIL_SIGNALS (Geographic and categorical retail velocity metrics)
-- ----------------------------------------------------------------------------
CREATE TABLE public.retail_signals (
    id VARCHAR PRIMARY KEY,
    trend_id VARCHAR REFERENCES public.trends(id) ON DELETE SET NULL,
    region VARCHAR NOT NULL,
    category VARCHAR NOT NULL,
    demand DOUBLE PRECISION NOT NULL,
    growth DOUBLE PRECISION NOT NULL,
    consumer_signal TEXT NOT NULL,
    timestamp TIMESTAMPTZ DEFAULT now(),
    data_status VARCHAR NOT NULL DEFAULT 'demo'
);
CREATE INDEX ix_retail_signals_trend_id ON public.retail_signals (trend_id);

-- ----------------------------------------------------------------------------
-- 2.9 FORECASTS (Statistical time-series forecasts & backtest accuracy)
-- ----------------------------------------------------------------------------
-- Column named 'confidence' matches SQLAlchemy mapping:
-- backtest_accuracy = Column("confidence", Float, nullable=False)
-- ----------------------------------------------------------------------------
CREATE TABLE public.forecasts (
    id VARCHAR PRIMARY KEY,
    trend_id VARCHAR NOT NULL REFERENCES public.trends(id) ON DELETE CASCADE,
    model VARCHAR NOT NULL,
    horizon VARCHAR NOT NULL DEFAULT '3_months',
    forecast_value DOUBLE PRECISION NOT NULL,
    confidence DOUBLE PRECISION NOT NULL,
    training_start TIMESTAMPTZ,
    training_end TIMESTAMPTZ,
    data_status VARCHAR NOT NULL DEFAULT 'demo',
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX ix_forecasts_trend_id ON public.forecasts (trend_id);

-- ----------------------------------------------------------------------------
-- 2.10 PROPHECY (5-stage predictive trajectory timeline)
-- ----------------------------------------------------------------------------
CREATE TABLE public.prophecy (
    id VARCHAR PRIMARY KEY,
    trend_id VARCHAR NOT NULL REFERENCES public.trends(id) ON DELETE CASCADE,
    stage VARCHAR NOT NULL,
    forecast TEXT NOT NULL,
    evidence_json TEXT DEFAULT '[]',
    opportunity TEXT NOT NULL,
    risk TEXT NOT NULL,
    confidence DOUBLE PRECISION NOT NULL,
    data_status VARCHAR NOT NULL DEFAULT 'demo',
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX ix_prophecy_trend_id ON public.prophecy (trend_id);

-- ----------------------------------------------------------------------------
-- 2.11 SAVED_TRENDS (User personal bookmarks / isolated per user)
-- ----------------------------------------------------------------------------
CREATE TABLE public.saved_trends (
    id VARCHAR PRIMARY KEY,
    user_id VARCHAR NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    trend_id VARCHAR NOT NULL REFERENCES public.trends(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT now(),
    CONSTRAINT uq_saved_trends_user_trend UNIQUE (user_id, trend_id)
);
CREATE INDEX ix_saved_trends_user_id ON public.saved_trends (user_id);
CREATE INDEX ix_saved_trends_trend_id ON public.saved_trends (trend_id);

-- ============================================================================
-- 3. PERMISSIONS & POSTGREST FAIL-CLOSED ENFORCEMENT
-- ============================================================================

-- Grant standard DML operations to the backend runtime role (narrowly scoped to LUXE.TECH tables)
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE
    public.users,
    public.trends,
    public.trend_signals,
    public.trend_dna,
    public.images,
    public.collections,
    public.products,
    public.retail_signals,
    public.forecasts,
    public.prophecy,
    public.saved_trends
TO luxe_app_user;

-- Explicitly revoke access from public PostgREST roles (narrowly scoped to LUXE.TECH tables)
REVOKE ALL ON TABLE
    public.users,
    public.trends,
    public.trend_signals,
    public.trend_dna,
    public.images,
    public.collections,
    public.products,
    public.retail_signals,
    public.forecasts,
    public.prophecy,
    public.saved_trends
FROM anon, authenticated;

-- ============================================================================
-- 4. ROW LEVEL SECURITY ENFORCEMENT & RUNTIME POLICIES
-- ============================================================================

-- 4.1 Enable Row Level Security on all 11 tables
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.trends ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.trend_signals ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.trend_dna ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.images ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.collections ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.products ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.retail_signals ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.forecasts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.prophecy ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.saved_trends ENABLE ROW LEVEL SECURITY;

-- 4.2 Explicit Application Runtime Policies (Option 1 Resolution)
-- These policies grant backend queries from luxe_app_user full access,
-- while external PostgREST calls remain 100% blocked by default-deny.
CREATE POLICY app_runtime_all ON public.users FOR ALL TO luxe_app_user USING (true) WITH CHECK (true);
CREATE POLICY app_runtime_all ON public.trends FOR ALL TO luxe_app_user USING (true) WITH CHECK (true);
CREATE POLICY app_runtime_all ON public.trend_signals FOR ALL TO luxe_app_user USING (true) WITH CHECK (true);
CREATE POLICY app_runtime_all ON public.trend_dna FOR ALL TO luxe_app_user USING (true) WITH CHECK (true);
CREATE POLICY app_runtime_all ON public.images FOR ALL TO luxe_app_user USING (true) WITH CHECK (true);
CREATE POLICY app_runtime_all ON public.collections FOR ALL TO luxe_app_user USING (true) WITH CHECK (true);
CREATE POLICY app_runtime_all ON public.products FOR ALL TO luxe_app_user USING (true) WITH CHECK (true);
CREATE POLICY app_runtime_all ON public.retail_signals FOR ALL TO luxe_app_user USING (true) WITH CHECK (true);
CREATE POLICY app_runtime_all ON public.forecasts FOR ALL TO luxe_app_user USING (true) WITH CHECK (true);
CREATE POLICY app_runtime_all ON public.prophecy FOR ALL TO luxe_app_user USING (true) WITH CHECK (true);
CREATE POLICY app_runtime_all ON public.saved_trends FOR ALL TO luxe_app_user USING (true) WITH CHECK (true);

COMMIT;

