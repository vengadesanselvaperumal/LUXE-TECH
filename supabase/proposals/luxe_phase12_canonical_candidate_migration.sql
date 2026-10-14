-- ============================================================================
-- LUXE.TECH — Phase 12 Canonical Initial Schema Candidate Migration
-- Location: supabase/proposals/luxe_phase12_canonical_candidate_migration.sql
-- Status: PROPOSAL / CANDIDATE ONLY (Un-applied, Offline Review Only)
--
-- DO NOT MOVE INTO supabase/migrations/ OR APPLY WITHOUT EXPLICIT APPROVAL.
--
-- This candidate defines the fresh-install schema baseline for LUXE.TECH,
-- achieving 100% parity with backend SQLAlchemy models (11 tables, 113 columns,
-- 12 indexes, foreign key cascading, and table-level Row Level Security).
--
-- GOVERNANCE & SAFETY RULES:
-- 1. No DROP TABLE or destructive DDL commands.
-- 2. Fresh-install only: Migration 002 (legacy schema alignment) is excluded.
-- 3. Row Level Security is ENABLED on all 11 tables.
-- 4. No public policies or PostgREST grants are defined (fail-closed security).
-- 5. No remote database roles, storage buckets, or storage policies created here.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. USERS
-- ----------------------------------------------------------------------------
-- STRATEGY ON users.password_hash NULLABILITY:
-- Kept nullable (VARCHAR NULL) during initial table creation to support initial
-- database bootstrap and legacy/demo seed routines where analyst@luxe.tech is
-- provisioned prior to credential assignment.
-- PRODUCTION HARDENING REQUIREMENT:
-- Once the administrative analyst account is populated with a PBKDF2 salt/hash,
-- execute:
--   UPDATE public.users SET password_hash = '<salted_hash>' WHERE password_hash IS NULL;
--   ALTER TABLE public.users ALTER COLUMN password_hash SET NOT NULL;
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
-- 2. TRENDS (Core fashion trend intelligence catalog)
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
-- 3. TREND_SIGNALS (Multi-source market signals across 5 channels)
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
-- 4. TREND_DNA (Visual, material, and palette DNA profile)
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
-- 5. IMAGES (Computer vision extraction & image asset catalog)
-- ----------------------------------------------------------------------------
-- DOCUMENTED DECISION ON images.user_id OWNERSHIP:
-- Current SQLAlchemy ImageRecord model has 13 columns (excluding user_id).
-- In Phase 11, exploratory upload ownership was hardened at the application &
-- storage level: uploads are namespaced by user identity in storage paths
-- (storage_path = '{user_id}/{uuid}_{filename}') and verified during serving.
-- To maintain exact parity with the running backend without premature model
-- drift, the initial baseline table matches Base.metadata exactly.
-- STAGED UPGRADE FOR RELATIONAL USER ATTRIBUTION (Planned Migration Step):
--   ALTER TABLE public.images ADD COLUMN user_id VARCHAR REFERENCES public.users(id) ON DELETE SET NULL;
--   CREATE INDEX ix_images_user_id ON public.images (user_id);
-- (To be applied concurrently with the SQLAlchemy ImageRecord model update).
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
-- 6. COLLECTIONS (Editorial design capsules synthesized for trends)
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
-- 7. PRODUCTS (Commercial product opportunities derived from trends)
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
-- 8. RETAIL_SIGNALS (Geographic and categorical retail velocity metrics)
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
-- 9. FORECASTS (Statistical time-series forecasts & backtest accuracy)
-- ----------------------------------------------------------------------------
-- NOTE ON 'confidence' COLUMN:
-- Column is named 'confidence' in the database schema to preserve exact
-- historical parity, but is mapped in SQLAlchemy as 'backtest_accuracy'.
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
-- 10. PROPHECY (5-stage predictive trajectory timeline)
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
-- 11. SAVED_TRENDS (User personal bookmarks / isolated per user)
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
-- ROW LEVEL SECURITY ENFORCEMENT
-- ============================================================================
-- All application tables must have Row Level Security enabled.
-- Under PostgreSQL / Supabase, enabling RLS with NO policies ensures that
-- unprivileged direct access (e.g. via PostgREST anon or authenticated roles)
-- is completely rejected (fail-closed behavior).
-- The backend connects using a dedicated runtime role (see security design).
-- ============================================================================
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

-- No public policies, anonymous grants, or storage bucket definitions are
-- included in this schema candidate. Those require explicit separate approval.

