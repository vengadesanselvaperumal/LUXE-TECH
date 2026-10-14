-- LUXE.TECH — Supabase PostgreSQL Schema
-- Migration: 001_initial_schema.sql

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. USERS
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    email TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    password_hash TEXT,
    role TEXT NOT NULL DEFAULT 'user',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2. TRENDS
CREATE TABLE IF NOT EXISTS trends (
    id TEXT PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    slug TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    season TEXT NOT NULL DEFAULT 'SS 2027',
    description TEXT NOT NULL,
    image_url TEXT,
    status TEXT NOT NULL DEFAULT 'emerging',
    confidence NUMERIC(5,2) NOT NULL DEFAULT 80.0,
    momentum NUMERIC(5,2) NOT NULL DEFAULT 25.0,
    velocity NUMERIC(5,2) NOT NULL DEFAULT 15.0,
    acceleration NUMERIC(5,2) NOT NULL DEFAULT 5.0,
    data_status TEXT NOT NULL DEFAULT 'demo',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 3. TREND_SIGNALS
CREATE TABLE IF NOT EXISTS trend_signals (
    id TEXT PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    trend_id TEXT NOT NULL REFERENCES trends(id) ON DELETE CASCADE,
    source TEXT NOT NULL CHECK (source IN ('runway', 'social', 'search', 'retail', 'culture')),
    signal_type TEXT NOT NULL,
    strength NUMERIC(5,2) NOT NULL,
    direction TEXT NOT NULL DEFAULT 'up',
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata_json TEXT NOT NULL DEFAULT '{}',
    data_status TEXT NOT NULL DEFAULT 'demo'
);

-- 4. TREND_DNA
CREATE TABLE IF NOT EXISTS trend_dna (
    id TEXT PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    trend_id TEXT NOT NULL REFERENCES trends(id) ON DELETE CASCADE UNIQUE,
    colors_json TEXT NOT NULL DEFAULT '[]',
    materials_json TEXT NOT NULL DEFAULT '[]',
    textures_json TEXT NOT NULL DEFAULT '[]',
    silhouettes_json TEXT NOT NULL DEFAULT '[]',
    patterns_json TEXT NOT NULL DEFAULT '[]',
    visual_description TEXT,
    ai_interpretation TEXT,
    data_status TEXT NOT NULL DEFAULT 'demo',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 5. IMAGES
CREATE TABLE IF NOT EXISTS images (
    id TEXT PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    trend_id TEXT REFERENCES trends(id) ON DELETE SET NULL,
    storage_path TEXT NOT NULL,
    public_url TEXT NOT NULL,
    width INTEGER NOT NULL,
    height INTEGER NOT NULL,
    dominant_colors_json TEXT NOT NULL DEFAULT '[]',
    contrast NUMERIC(6,3) NOT NULL DEFAULT 0.0,
    brightness NUMERIC(6,3) NOT NULL DEFAULT 0.0,
    saturation NUMERIC(6,3) NOT NULL DEFAULT 0.0,
    edge_density NUMERIC(6,3) NOT NULL DEFAULT 0.0,
    data_status TEXT NOT NULL DEFAULT 'demo',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 6. COLLECTIONS
CREATE TABLE IF NOT EXISTS collections (
    id TEXT PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    trend_id TEXT NOT NULL REFERENCES trends(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    color_palette_json TEXT NOT NULL DEFAULT '[]',
    materials_json TEXT NOT NULL DEFAULT '[]',
    textures_json TEXT NOT NULL DEFAULT '[]',
    silhouettes_json TEXT NOT NULL DEFAULT '[]',
    patterns_json TEXT NOT NULL DEFAULT '[]',
    product_opportunities_json TEXT NOT NULL DEFAULT '[]',
    data_status TEXT NOT NULL DEFAULT 'demo',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE trend_dna ADD COLUMN IF NOT EXISTS data_status TEXT NOT NULL DEFAULT 'demo';
ALTER TABLE images ADD COLUMN IF NOT EXISTS data_status TEXT NOT NULL DEFAULT 'demo';
ALTER TABLE collections ADD COLUMN IF NOT EXISTS data_status TEXT NOT NULL DEFAULT 'demo';

-- 7. PRODUCTS
CREATE TABLE IF NOT EXISTS products (
    id TEXT PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    trend_id TEXT REFERENCES trends(id) ON DELETE SET NULL,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    description TEXT NOT NULL,
    material TEXT NOT NULL,
    silhouette TEXT NOT NULL,
    color TEXT NOT NULL,
    target_consumer TEXT NOT NULL,
    opportunity_score NUMERIC(5,2) NOT NULL DEFAULT 75.0,
    ai_reasoning TEXT,
    data_status TEXT NOT NULL DEFAULT 'demo',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 8. RETAIL_SIGNALS
CREATE TABLE IF NOT EXISTS retail_signals (
    id TEXT PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    trend_id TEXT REFERENCES trends(id) ON DELETE SET NULL,
    region TEXT NOT NULL,
    category TEXT NOT NULL,
    demand NUMERIC(5,2) NOT NULL,
    growth NUMERIC(5,2) NOT NULL,
    consumer_signal TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    data_status TEXT NOT NULL DEFAULT 'demo'
);

-- 9. FORECASTS
CREATE TABLE IF NOT EXISTS forecasts (
    id TEXT PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    trend_id TEXT NOT NULL REFERENCES trends(id) ON DELETE CASCADE,
    model TEXT NOT NULL CHECK (model IN ('moving_average', 'simple_exponential_smoothing', 'holt_winters', 'linear_regression')),
    horizon TEXT NOT NULL DEFAULT '3_months',
    forecast_value NUMERIC(6,2) NOT NULL,
    confidence NUMERIC(5,2) NOT NULL,
    training_start TIMESTAMPTZ,
    training_end TIMESTAMPTZ,
    data_status TEXT NOT NULL DEFAULT 'demo',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 10. PROPHECY
CREATE TABLE IF NOT EXISTS prophecy (
    id TEXT PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    trend_id TEXT NOT NULL REFERENCES trends(id) ON DELETE CASCADE,
    stage TEXT NOT NULL CHECK (stage IN ('current', 'emerging', 'accelerating', 'mainstream', 'next')),
    forecast TEXT NOT NULL,
    evidence_json TEXT NOT NULL DEFAULT '[]',
    opportunity TEXT NOT NULL,
    risk TEXT NOT NULL,
    confidence NUMERIC(5,2) NOT NULL,
    data_status TEXT NOT NULL DEFAULT 'demo',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 11. SAVED_TRENDS
CREATE TABLE IF NOT EXISTS saved_trends (
    id TEXT PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    trend_id TEXT NOT NULL REFERENCES trends(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(user_id, trend_id)
);

ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash TEXT;

-- INDEXES
CREATE INDEX IF NOT EXISTS idx_trends_slug ON trends(slug);
CREATE INDEX IF NOT EXISTS idx_trends_category ON trends(category);
CREATE INDEX IF NOT EXISTS idx_signals_trend ON trend_signals(trend_id);
CREATE INDEX IF NOT EXISTS idx_products_trend ON products(trend_id);
CREATE INDEX IF NOT EXISTS idx_forecasts_trend ON forecasts(trend_id);
CREATE INDEX IF NOT EXISTS idx_prophecy_trend ON prophecy(trend_id);
CREATE INDEX IF NOT EXISTS idx_retail_trend ON retail_signals(trend_id);
CREATE INDEX IF NOT EXISTS idx_images_trend ON images(trend_id);
CREATE INDEX IF NOT EXISTS idx_saved_trends_user ON saved_trends(user_id);
CREATE INDEX IF NOT EXISTS idx_saved_trends_trend ON saved_trends(trend_id);

-- ROW LEVEL SECURITY (RLS)
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE saved_trends ENABLE ROW LEVEL SECURITY;
ALTER TABLE trends ENABLE ROW LEVEL SECURITY;
ALTER TABLE trend_signals ENABLE ROW LEVEL SECURITY;
ALTER TABLE trend_dna ENABLE ROW LEVEL SECURITY;
ALTER TABLE images ENABLE ROW LEVEL SECURITY;
ALTER TABLE collections ENABLE ROW LEVEL SECURITY;
ALTER TABLE products ENABLE ROW LEVEL SECURITY;
ALTER TABLE retail_signals ENABLE ROW LEVEL SECURITY;
ALTER TABLE forecasts ENABLE ROW LEVEL SECURITY;
ALTER TABLE prophecy ENABLE ROW LEVEL SECURITY;

-- Read-only public intelligence. The server connects with a private PostgreSQL
-- role; anon/authenticated clients receive no table write grants here.
DO $policies$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'trends' AND policyname = 'Public read trends') THEN
        CREATE POLICY "Public read trends" ON trends FOR SELECT USING (true);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'trend_signals' AND policyname = 'Public read signals') THEN
        CREATE POLICY "Public read signals" ON trend_signals FOR SELECT USING (true);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'trend_dna' AND policyname = 'Public read trend_dna') THEN
        CREATE POLICY "Public read trend_dna" ON trend_dna FOR SELECT USING (true);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'images' AND policyname = 'Public read images') THEN
        CREATE POLICY "Public read images" ON images FOR SELECT USING (true);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'collections' AND policyname = 'Public read collections') THEN
        CREATE POLICY "Public read collections" ON collections FOR SELECT USING (true);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'products' AND policyname = 'Public read products') THEN
        CREATE POLICY "Public read products" ON products FOR SELECT USING (true);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'retail_signals' AND policyname = 'Public read retail_signals') THEN
        CREATE POLICY "Public read retail_signals" ON retail_signals FOR SELECT USING (true);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'forecasts' AND policyname = 'Public read forecasts') THEN
        CREATE POLICY "Public read forecasts" ON forecasts FOR SELECT USING (true);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'prophecy' AND policyname = 'Public read prophecy') THEN
        CREATE POLICY "Public read prophecy" ON prophecy FOR SELECT USING (true);
    END IF;
END
$policies$;

GRANT SELECT ON trends, trend_signals, trend_dna, images, collections, products, retail_signals, forecasts, prophecy TO anon, authenticated;

-- Storage Buckets Configuration (Run in Supabase SQL editor or storage API)
INSERT INTO storage.buckets (id, name, public) VALUES ('trend-images', 'trend-images', true) ON CONFLICT (id) DO NOTHING;
INSERT INTO storage.buckets (id, name, public) VALUES ('user-uploads', 'user-uploads', false) ON CONFLICT (id) DO NOTHING;
INSERT INTO storage.buckets (id, name, public) VALUES ('collections', 'collections', true) ON CONFLICT (id) DO NOTHING;

-- No storage.objects policies grant anon/authenticated writes or private reads.
-- The backend uses its server-only service role; user-uploads remains private.
DO $bucket_privacy$
BEGIN
    IF EXISTS (SELECT 1 FROM storage.buckets WHERE id = 'trend-images' AND public IS DISTINCT FROM true) THEN
        RAISE EXCEPTION 'trend-images must be explicitly reviewed as public before continuing';
    END IF;
    IF EXISTS (SELECT 1 FROM storage.buckets WHERE id = 'user-uploads' AND public IS DISTINCT FROM false) THEN
        RAISE EXCEPTION 'user-uploads must remain private; review its bucket setting before continuing';
    END IF;
    IF EXISTS (SELECT 1 FROM storage.buckets WHERE id = 'collections' AND public IS DISTINCT FROM true) THEN
        RAISE EXCEPTION 'collections is configured as public for shareable moodboards; review its bucket setting before continuing';
    END IF;
END
$bucket_privacy$;
