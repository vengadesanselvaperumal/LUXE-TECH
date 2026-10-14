-- LOCAL REVIEW PROPOSAL ONLY. This file is not a Supabase migration.
-- Do not move it into supabase/migrations or execute it without separate approval.
-- The CREATE TABLE statements intentionally fail if an object already exists.
-- This proposal contains no extension, role, grant, policy, bucket, or data changes.

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

CREATE TABLE public.saved_trends (
    id VARCHAR PRIMARY KEY,
    user_id VARCHAR NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    trend_id VARCHAR NOT NULL REFERENCES public.trends(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT now(),
    CONSTRAINT uq_saved_trends_user_trend UNIQUE (user_id, trend_id)
);
CREATE INDEX ix_saved_trends_user_id ON public.saved_trends (user_id);
CREATE INDEX ix_saved_trends_trend_id ON public.saved_trends (trend_id);

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

-- No policies or Supabase API grants are defined until the identity and
-- public-data decisions in PHASE_04_DATABASE_READINESS.md are approved.
