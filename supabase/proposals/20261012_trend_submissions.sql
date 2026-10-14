-- PROPOSAL ONLY — do not execute until reviewed against the target Supabase project.
-- Adds private, account-owned user-reported fashion observations. The FastAPI
-- runtime performs authorization; PostgREST anon/authenticated roles receive no access.

CREATE TABLE IF NOT EXISTS public.trend_submissions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    platform TEXT NOT NULL CHECK (platform IN ('instagram', 'youtube', 'tiktok', 'pinterest', 'other')),
    source_url TEXT NOT NULL,
    normalized_source_url TEXT NOT NULL UNIQUE,
    observation TEXT NOT NULL CHECK (char_length(observation) BETWEEN 5 AND 500),
    product_type TEXT NOT NULL CHECK (char_length(product_type) BETWEEN 1 AND 120),
    category TEXT,
    color TEXT,
    material TEXT,
    silhouette TEXT,
    observed_at TIMESTAMPTZ,
    explanation TEXT CHECK (explanation IS NULL OR char_length(explanation) <= 2000),
    image_storage_path TEXT,
    rights_confirmed BOOLEAN NOT NULL DEFAULT FALSE,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'reviewed', 'accepted', 'rejected')),
    review_note TEXT CHECK (review_note IS NULL OR char_length(review_note) <= 2000),
    submitted_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_trend_submissions_user_created
    ON public.trend_submissions (user_id, submitted_at DESC);

ALTER TABLE public.trend_submissions ENABLE ROW LEVEL SECURITY;

-- Requires the existing least-privilege backend runtime role.
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.trend_submissions TO luxe_app_user;

CREATE POLICY app_runtime_all ON public.trend_submissions
    FOR ALL
    TO luxe_app_user
    USING (true)
    WITH CHECK (true);

REVOKE ALL ON public.trend_submissions FROM anon, authenticated;
